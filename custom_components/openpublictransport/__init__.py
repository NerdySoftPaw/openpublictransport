import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DEPARTURES,
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PROVIDER,
    CONF_REJSEPLANEN_API_KEY,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRAFIKLAB_API_KEY,
    CONF_VBN_API_KEY,
    DEFAULT_DEPARTURES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PROVIDER_NATIONAL_RAIL,
    PROVIDER_NTA_IE,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_REJSEPLANEN,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
)
from .sensor import PublicTransportDataUpdateCoordinator
from .trip import async_plan_trip

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH = "refresh_departures"
SERVICE_PLAN_TRIP = "plan_trip"
SERVICE_CHECK_DELAYS = "check_delays"
SERVICE_ANNOUNCE = "announce_departure"

SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): str,
    }
)

SERVICE_PLAN_TRIP_SCHEMA = vol.Schema(
    {
        vol.Required("provider"): str,
        vol.Required("origin"): str,
        vol.Required("origin_city"): str,
        vol.Required("destination"): str,
        vol.Required("destination_city"): str,
    }
)

SERVICE_CHECK_DELAYS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Optional("delay_threshold", default=5): int,
        vol.Optional("line"): str,
    }
)

SERVICE_ANNOUNCE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Optional("index", default=0): int,
        vol.Optional("tts_service"): str,
        vol.Optional("media_player"): str,
        vol.Optional("language", default="de"): str,
    }
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_PROVIDER_CREDENTIAL_NAMES: dict[str, str] = {
    PROVIDER_OPT: "Germany Community Server (api.openpublictransport.net)",
    PROVIDER_OTP_CUSTOM: "OTP2 Custom Instance",
    PROVIDER_TRAFIKLAB_SE: "Trafiklab (Sweden)",
    PROVIDER_RMV: "RMV (Rhine-Main)",
    PROVIDER_VBN_OTP: "VBN (Bremen/Lower Saxony) — OTP",
    PROVIDER_VBN_TRIAS: "VBN (Bremen/Lower Saxony) — TRIAS",
    PROVIDER_NTA_IE: "NTA (Ireland)",
}


async def _async_migrate_credential(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate API key from a config entry into HA's Application Credentials store.

    Called for every existing entry on startup so that keys entered before this
    feature existed show up centrally under Application Credentials.
    The underlying async_import_item is idempotent — duplicate keys are silently skipped.
    """
    provider = entry.data.get(CONF_PROVIDER) or entry.data.get("trip_provider")
    if not provider:
        return

    key_map: dict[str, tuple[str, str]] = {
        # provider: (primary_conf_key, secondary_conf_key_or_empty)
        PROVIDER_OPT: (CONF_OPT_API_KEY, ""),
        PROVIDER_OTP_CUSTOM: (CONF_OTP_CUSTOM_API_KEY, ""),
        PROVIDER_TRAFIKLAB_SE: (CONF_TRAFIKLAB_API_KEY, ""),
        PROVIDER_RMV: (CONF_RMV_API_KEY, ""),
        PROVIDER_VBN_OTP: (CONF_VBN_API_KEY, ""),
        PROVIDER_VBN_TRIAS: (CONF_VBN_API_KEY, ""),
        PROVIDER_NTA_IE: (CONF_NTA_API_KEY, CONF_NTA_API_KEY_SECONDARY),
        PROVIDER_REJSEPLANEN: (CONF_REJSEPLANEN_API_KEY, ""),
        PROVIDER_NATIONAL_RAIL: (CONF_NATIONAL_RAIL_API_KEY, ""),
    }

    if provider not in key_map:
        return

    primary_key, secondary_key = key_map[provider]
    api_key = entry.data.get(primary_key, "")
    if not api_key:
        return

    secondary = entry.data.get(secondary_key, "") if secondary_key else ""
    name = _PROVIDER_CREDENTIAL_NAMES.get(provider, f"{provider.upper()} API Key")

    try:
        await async_import_client_credential(
            hass,
            DOMAIN,
            ClientCredential(client_id=api_key, client_secret=secondary, name=name),
            auth_domain=f"{DOMAIN}.{provider}",
        )
        _LOGGER.debug("Migrated %s credential to Application Credentials store", provider)
    except Exception as exc:
        _LOGGER.warning("Could not migrate credential for %s: %s", provider, exc)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Open Public Transport component."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle the refresh service call."""
        entity_id = call.data.get("entity_id")
        if entity_id:
            entity_registry = er.async_get(hass)
            entity_entry = entity_registry.async_get(entity_id)
            if not entity_entry or entity_entry.platform != DOMAIN:
                raise ServiceValidationError(f"Entity {entity_id} not found or not part of {DOMAIN}")
            entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
            coordinator = getattr(entry, "runtime_data", None) if entry else None
            if not coordinator:
                raise HomeAssistantError(f"No coordinator found for {entity_id}")
            await coordinator.async_request_refresh()
        else:
            entity_registry = er.async_get(hass)
            entities = [e for e in entity_registry.entities.values() if e.platform == DOMAIN]
            seen_entries: set[str] = set()
            for entity_entry in entities:
                entry_id = entity_entry.config_entry_id
                if entry_id and entry_id not in seen_entries:
                    seen_entries.add(entry_id)
                    entry = hass.config_entries.async_get_entry(entry_id)
                    coordinator = getattr(entry, "runtime_data", None) if entry else None
                    if coordinator:
                        await coordinator.async_request_refresh()

    async def handle_plan_trip(call: ServiceCall) -> dict:
        """Handle the plan_trip service call."""
        provider = call.data["provider"]
        origin = call.data["origin"]
        origin_city = call.data["origin_city"]
        destination = call.data["destination"]
        destination_city = call.data["destination_city"]
        api_key = None
        custom_url = None
        for existing in hass.config_entries.async_entries(DOMAIN):
            ep = existing.data.get(CONF_PROVIDER) or existing.data.get("trip_provider")
            if ep == provider:
                if provider == PROVIDER_VBN_OTP:
                    api_key = existing.data.get(CONF_VBN_API_KEY)
                elif provider == PROVIDER_OPT:
                    api_key = existing.data.get(CONF_OPT_API_KEY)
                elif provider == PROVIDER_OTP_CUSTOM:
                    api_key = existing.data.get(CONF_OTP_CUSTOM_API_KEY)
                    custom_url = existing.data.get(CONF_OTP_BASE_URL)
                break
        journeys = await async_plan_trip(
            hass,
            provider,
            origin,
            origin_city,
            destination,
            destination_city,
            api_key=api_key,
            custom_url=custom_url,
        )
        if journeys is None:
            raise HomeAssistantError(f"Trip planning failed for provider '{provider}' — check logs for details")
        return {"journeys": journeys}

    async def handle_check_delays(call: ServiceCall) -> dict:
        """Check delays and return delayed departures."""
        entity_id = call.data["entity_id"]
        threshold = call.data.get("delay_threshold", 5)
        line_filter = call.data.get("line", "").strip().lower()
        state_obj = hass.states.get(entity_id)
        if not state_obj:
            raise ServiceValidationError(f"Entity {entity_id} not found")
        departures = state_obj.attributes.get("departures", [])
        delayed = []
        for dep in departures:
            if not isinstance(dep, dict):
                continue
            delay = dep.get("delay", 0)
            line = dep.get("line", "")
            if delay >= threshold:
                if not line_filter or line.lower() == line_filter:
                    delayed.append(dep)
        if delayed:
            hass.bus.async_fire(
                f"{DOMAIN}_delay_alert",
                {
                    "entity_id": entity_id,
                    "delayed_count": len(delayed),
                    "max_delay": max(d.get("delay", 0) for d in delayed),
                    "lines": list({d.get("line", "") for d in delayed}),
                    "departures": delayed[:5],
                },
            )
        return {"delayed": delayed, "count": len(delayed)}

    async def handle_announce(call: ServiceCall) -> dict:
        """Generate and optionally speak a departure announcement."""
        entity_id = call.data["entity_id"]
        index = call.data.get("index", 0)
        tts_service = call.data.get("tts_service")
        media_player = call.data.get("media_player")
        language = call.data.get("language", "de")
        state_obj = hass.states.get(entity_id)
        if not state_obj:
            raise ServiceValidationError(f"Entity {entity_id} not found")
        departures = state_obj.attributes.get("departures", [])
        if not departures:
            raise ServiceValidationError(f"No departure data available for {entity_id}")
        if index >= len(departures):
            raise ServiceValidationError(f"Index {index} out of range — only {len(departures)} departure(s) available")
        dep = departures[index]
        line = dep.get("line", "")
        destination = dep.get("destination", "")
        planned_time = dep.get("planned_time", "")
        minutes = dep.get("minutes_until_departure", 0)
        platform = dep.get("platform", "")
        delay = dep.get("delay", 0)
        transport_type = dep.get("transportation_type", "")
        if language == "de":
            type_name = {"train": "Zug", "subway": "U-Bahn", "tram": "Straßenbahn", "bus": "Bus", "ferry": "Fähre"}.get(
                transport_type, ""
            )
            text = "Achtung, eine Durchsage. "
            text += f"{type_name} {line}" if type_name else f"Linie {line}"
            text += f" Richtung {destination}"
            if planned_time:
                text += f", planmäßige Abfahrt {planned_time} Uhr"
            if delay > 0:
                text += f", hat heute circa {delay} Minuten Verspätung"
            if platform:
                text += f", Abfahrt von Gleis {platform}"
            if minutes <= 0:
                text += ". Bitte einsteigen, Türen schließen selbsttätig."
            elif minutes <= 2:
                text += ". Bitte begeben Sie sich zum Bahnsteig."
            else:
                text += f". Abfahrt in {minutes} Minuten."
        else:
            text = f"Attention please. {line} to {destination}"
            if planned_time:
                text += f", scheduled departure {planned_time}"
            if delay > 0:
                text += f", is delayed by approximately {delay} minutes"
            if platform:
                text += f", departing from platform {platform}"
            if minutes <= 0:
                text += ". Please board now."
            else:
                text += f". Departing in {minutes} minutes."
        if tts_service and media_player:
            try:
                service_parts = tts_service.split(".", 1)
                if len(service_parts) == 2:
                    await hass.services.async_call(
                        service_parts[0], service_parts[1], {"entity_id": media_player, "message": text}
                    )
            except Exception as e:
                _LOGGER.warning("Failed to call TTS service: %s", e)
        return {"text": text}

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh, schema=SERVICE_REFRESH_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PLAN_TRIP, handle_plan_trip, schema=SERVICE_PLAN_TRIP_SCHEMA, supports_response=True
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CHECK_DELAYS, handle_check_delays, schema=SERVICE_CHECK_DELAYS_SCHEMA, supports_response=True
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ANNOUNCE, handle_announce, schema=SERVICE_ANNOUNCE_SCHEMA, supports_response=True
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Open Public Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Migrate any API key stored in this entry to the Application Credentials store.
    # Safe for new entries (no key → no-op) and idempotent for existing ones.
    await _async_migrate_credential(hass, entry)

    # Check if this is a multi-stop entry
    if entry.data.get("is_multi_stop"):
        from .multi_stop import async_setup_multi_stop_entry

        return await async_setup_multi_stop_entry(hass, entry)

    # Check if this is a trip entry
    if entry.data.get("is_trip"):
        from .trip_sensor import async_setup_trip_entry

        return await async_setup_trip_entry(hass, entry)

    # Create coordinator and do initial refresh before forwarding entry setups
    # This allows ConfigEntryNotReady to be raised before async_forward_entry_setups
    provider = entry.data.get(CONF_PROVIDER, "vrr")
    place_dm = entry.data.get("place_dm", "")
    name_dm = entry.data.get("name_dm", "")
    station_id = entry.data.get(CONF_STATION_ID)
    trafiklab_api_key = entry.data.get(CONF_TRAFIKLAB_API_KEY)  # For Trafiklab
    nta_api_key = entry.data.get(CONF_NTA_API_KEY)  # For NTA
    rmv_api_key = entry.data.get(CONF_RMV_API_KEY)  # For RMV
    vbn_api_key = entry.data.get(CONF_VBN_API_KEY)  # For VBN (OTP + TRIAS)
    opt_api_key = entry.data.get(CONF_OPT_API_KEY)  # For community OTP server
    otp_custom_api_key = entry.data.get(CONF_OTP_CUSTOM_API_KEY)  # For custom OTP instance
    rejseplanen_api_key = entry.data.get(CONF_REJSEPLANEN_API_KEY)  # For Rejseplanen (DK)
    national_rail_api_key = entry.data.get(CONF_NATIONAL_RAIL_API_KEY)  # For National Rail (UK)
    otp_custom_url = entry.data.get(CONF_OTP_BASE_URL)  # For custom OTP instance

    # Use appropriate API key (and URL) based on provider
    api_key = None
    custom_url = None
    if provider == PROVIDER_TRAFIKLAB_SE:
        api_key = trafiklab_api_key
    elif provider == PROVIDER_NTA_IE:
        api_key = nta_api_key
    elif provider == PROVIDER_RMV:
        api_key = rmv_api_key
    elif provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
        api_key = vbn_api_key
    elif provider == PROVIDER_OPT:
        api_key = opt_api_key
    elif provider == PROVIDER_OTP_CUSTOM:
        api_key = otp_custom_api_key
        custom_url = otp_custom_url
    elif provider == PROVIDER_REJSEPLANEN:
        api_key = rejseplanen_api_key
    elif provider == PROVIDER_NATIONAL_RAIL:
        api_key = national_rail_api_key

    departures = entry.options.get(CONF_DEPARTURES, entry.data.get(CONF_DEPARTURES, DEFAULT_DEPARTURES))
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider,
        place_dm,
        name_dm,
        station_id,
        departures,
        scan_interval,
        config_entry=entry,
        api_key=api_key,
        custom_url=custom_url,
    )

    entry.runtime_data = coordinator

    # Raises ConfigEntryNotReady on failure → HA retries automatically.
    # OTP providers may be slow to start; HA's retry logic handles that gracefully.
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor", "calendar", "event", "camera"]
    )

    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of stale devices not associated with the current config."""
    provider = config_entry.data.get(CONF_PROVIDER, "")
    station_id = config_entry.data.get(CONF_STATION_ID)
    place_dm = config_entry.data.get("place_dm", "")
    name_dm = config_entry.data.get("name_dm", "")
    station_key = station_id or f"{place_dm}_{name_dm}".lower().replace(" ", "_")
    current_identifier = (DOMAIN, f"{provider}_{station_key}")
    return current_identifier not in device_entry.identifiers


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Open Public Transport config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor", "calendar", "event", "camera"]
    )

    # Shutdown coordinator resources (e.g. GTFS data); runtime_data is auto-cleared by HA
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator and hasattr(coordinator, "async_shutdown"):
        try:
            await coordinator.async_shutdown()
            _LOGGER.debug("Coordinator shutdown completed for entry: %s", entry.entry_id)
        except Exception as e:
            _LOGGER.warning("Error during coordinator shutdown: %s", e)

    # Unregister services and cleanup if no more entries
    if not hass.config_entries.async_entries(DOMAIN):
        # Remove services
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
        hass.services.async_remove(DOMAIN, SERVICE_PLAN_TRIP)
        hass.services.async_remove(DOMAIN, SERVICE_CHECK_DELAYS)
        hass.services.async_remove(DOMAIN, SERVICE_ANNOUNCE)

        # Clean up domain data
        hass.data.pop(DOMAIN, None)
        _LOGGER.info("Open Public Transport integration fully unloaded")

    return unload_ok
