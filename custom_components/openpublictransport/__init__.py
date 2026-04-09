import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DEPARTURES,
    CONF_NTA_API_KEY,
    CONF_PROVIDER,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRAFIKLAB_API_KEY,
    DEFAULT_DEPARTURES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PROVIDER_NTA_IE,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
)
from .sensor import PublicTransportDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH = "refresh_departures"

SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): str,
    }
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Open Public Transport component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Open Public Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator and do initial refresh before forwarding entry setups
    # This allows ConfigEntryNotReady to be raised before async_forward_entry_setups
    provider = entry.data.get(CONF_PROVIDER, "vrr")
    place_dm = entry.data.get("place_dm", "")
    name_dm = entry.data.get("name_dm", "")
    station_id = entry.data.get(CONF_STATION_ID)
    trafiklab_api_key = entry.data.get(CONF_TRAFIKLAB_API_KEY)  # For Trafiklab
    nta_api_key = entry.data.get(CONF_NTA_API_KEY)  # For NTA
    rmv_api_key = entry.data.get(CONF_RMV_API_KEY)  # For RMV

    # Use appropriate API key based on provider
    api_key = None
    if provider == PROVIDER_TRAFIKLAB_SE:
        api_key = trafiklab_api_key
    elif provider == PROVIDER_NTA_IE:
        api_key = nta_api_key
    elif provider == PROVIDER_RMV:
        api_key = rmv_api_key

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
    )

    # Store coordinator before first refresh
    coordinator_key = f"{entry.entry_id}_coordinator"
    hass.data[DOMAIN][coordinator_key] = coordinator

    # Do initial refresh - this can raise ConfigEntryNotReady
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        # Cleanup coordinator resources before removing from hass.data
        try:
            await coordinator.async_shutdown()
        except Exception as shutdown_err:
            _LOGGER.warning("Error during coordinator shutdown after failed setup: %s", shutdown_err)
        # Remove coordinator from hass.data if setup fails
        hass.data[DOMAIN].pop(coordinator_key, None)
        raise ConfigEntryNotReady(f"Failed to initialize public transport API: {err}") from err

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor", "calendar", "event"])

    # Register service for manual refresh
    async def handle_refresh(call: ServiceCall) -> None:
        """Handle the refresh service call."""
        entity_id = call.data.get("entity_id")

        if entity_id:
            # Refresh specific entity
            entity_registry = er.async_get(hass)
            entity_entry = entity_registry.async_get(entity_id)

            if entity_entry and entity_entry.platform == DOMAIN:
                # Get the entity and trigger refresh
                entity_obj = hass.data.get("entity_components", {}).get("sensor")
                if entity_obj:
                    for ent in entity_obj.entities:
                        if ent.entity_id == entity_id:
                            await ent.coordinator.async_request_refresh()
                            break
        else:
            # Refresh all entities
            entity_registry = er.async_get(hass)
            entities = [e for e in entity_registry.entities.values() if e.platform == DOMAIN]

            entity_obj = hass.data.get("entity_components", {}).get("sensor")
            if entity_obj:
                for entity_entry in entities:
                    for ent in entity_obj.entities:
                        if ent.entity_id == entity_entry.entity_id:
                            await ent.coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        handle_refresh,
        schema=SERVICE_REFRESH_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Open Public Transport config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor", "calendar", "event"]
    )

    # Remove coordinator from hass.data and call shutdown
    coordinator_key = f"{entry.entry_id}_coordinator"
    if coordinator_key in hass.data.get(DOMAIN, {}):
        coordinator = hass.data[DOMAIN].pop(coordinator_key)
        # Call coordinator shutdown to release GTFS resources
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

        # Clean up domain data
        hass.data.pop(DOMAIN, None)
        _LOGGER.info("Open Public Transport integration fully unloaded")

    return unload_ok
