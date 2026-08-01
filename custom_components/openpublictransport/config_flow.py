"""Config flow for Open Public Transport integration with autocomplete support."""

import asyncio
import hashlib
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientConnectorError
from homeassistant import config_entries
from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from openpublictransport import get_provider, get_provider_class

from .const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_DESTINATION_FILTER,
    CONF_ENTRY_LABEL,
    CONF_ENTRY_SUFFIX,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PLATFORM_FILTER,
    CONF_PROVIDER,
    CONF_REJSEPLANEN_API_KEY,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRAFIKLAB_API_KEY,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_VBN_API_KEY,
    CONF_WALKING_TIME,
    DEFAULT_DELAY_THRESHOLD,
    DEFAULT_DEPARTURES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WALKING_TIME,
    DOMAIN,
    PROVIDER_HVV,
    PROVIDER_KVV,
    PROVIDER_NATIONAL_RAIL,
    PROVIDER_NTA_IE,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_REJSEPLANEN,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
    PROVIDER_VRR,
    TRANSPORTATION_TYPES,
)

_LOGGER = logging.getLogger(__name__)

# Filters that make one entry for a station distinct from another (issue #55),
# paired with how each reads in the entry title and device name.
_DISCRIMINATING_FILTERS = (
    (CONF_LINE_FILTER, "{}"),
    (CONF_DESTINATION_FILTER, "→ {}"),
    (CONF_PLATFORM_FILTER, "Pl. {}"),
)


def _filter_values(user_input: Dict[str, Any], key: str) -> List[str]:
    """Split one comma-separated filter field into its trimmed values."""
    return [value.strip() for value in str(user_input.get(key) or "").split(",") if value.strip()]


def _filter_discriminator(user_input: Dict[str, Any]) -> str:
    """Return a stable short id for this entry's filter set, "" when unfiltered.

    Order- and case-insensitive, so "S1, S2" and "s2,s1" are recognised as the
    same configuration and the second one is rejected as already_configured.

    Frozen into ``entry.data`` at creation: entity unique IDs are built on it,
    so it must not move when the filters are later edited under Options.
    """
    canonical = {
        key: sorted({value.casefold() for value in _filter_values(user_input, key)})
        for key, _ in _DISCRIMINATING_FILTERS
    }
    if not any(canonical.values()):
        return ""

    fingerprint = "|".join(f"{key}={','.join(values)}" for key, values in sorted(canonical.items()))
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:8]


def _filter_label(user_input: Dict[str, Any]) -> str:
    """Return a short human-readable form of the filters, "" when unfiltered."""
    bits = []
    for key, template in _DISCRIMINATING_FILTERS:
        values = _filter_values(user_input, key)
        if values:
            bits.append(template.format(", ".join(values)))
    return " ".join(bits)


class OpenPublicTransportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Open Public Transport integration with autocomplete."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._entry_type: str = "departures"  # "departures" or "trip"
        self._provider: Optional[str] = None
        self._selected_stop: Optional[Dict[str, Any]] = None
        self._api_key: Optional[str] = None  # For Trafiklab or NTA (Primary)
        self._api_key_secondary: Optional[str] = None  # For NTA (Secondary, optional)
        self._otp_custom_url: Optional[str] = None  # For otp_custom provider
        # Trip planning fields
        self._trip_origin: Optional[Dict[str, Any]] = None
        self._trip_destination: Optional[Dict[str, Any]] = None
        self._trip_search_phase: str = "origin"  # "origin" or "destination"

        # Temp stop results — instance variable instead of hass.data to avoid cross-flow leaks
        self._found_stops: list[dict] = []

        # Reconfigure support
        self._reconfiguring: bool = False
        self._reconfigure_entry: Optional[config_entries.ConfigEntry] = None

        # API response cache to avoid duplicate requests
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: int = 300  # Cache TTL in seconds (5 minutes)

    @staticmethod
    def _provider_selector() -> SelectSelector:
        """Return alphabetically sorted provider dropdown."""
        options = [
            {"value": "avv_augsburg", "label": "AVV — Augsburg"},
            {"value": "bart_us", "label": "BART — USA (San Francisco)"},
            {"value": "beg", "label": "BEG — Bayern"},
            {"value": "bsvg", "label": "BSVG — Braunschweig"},
            {"value": "bvg", "label": "BVG — Berlin / Brandenburg"},
            {"value": "dart_us", "label": "DART — USA (Des Moines)"},
            {"value": "db", "label": "DB — Deutsche Bahn (Community API)"},
            {"value": "ding", "label": "DING — Ulm / Donau-Iller"},
            {"value": "entur_no", "label": "Entur — Norwegen"},
            {"value": "hvv", "label": "HVV — Hamburg"},
            {"value": "irishrail_ie", "label": "Irish Rail — Irland"},
            {"value": "kvv", "label": "KVV — Karlsruhe"},
            {"value": "mobiliteit_lu", "label": "mobilitéit.lu — Luxemburg"},
            {"value": "mvv", "label": "MVV — München"},
            {"value": "national_rail", "label": "National Rail — Großbritannien (API Key)"},
            {"value": "ns_nl", "label": "NS — Niederlande"},
            {"value": "nta_ie", "label": "NTA — Irland (API Key)"},
            {"value": "nvbw", "label": "NVBW — Baden-Württemberg"},
            {"value": "nwl", "label": "NWL — Westfalen-Lippe"},
            {"value": "oebb", "label": "ÖBB — Österreich"},
            {"value": "rejseplanen", "label": "Rejseplanen — Dänemark (API Key)"},
            {"value": "rmv", "label": "RMV — Frankfurt / Rhein-Main (API Key)"},
            {"value": "rvv", "label": "RVV — Regensburg"},
            {"value": "sbb", "label": "SBB — Schweiz"},
            {"value": "tpg_ch", "label": "TPG — Schweiz (Genf)"},
            {"value": "trafiklab_se", "label": "Trafiklab — Schweden (API Key)"},
            {
                "value": "openpublictransport",
                "label": "openpublictransport.net (Deutschlandweit, API Key)",
            },
            {"value": "otp_custom", "label": "OTP2 — Eigene Instanz (URL + optionaler API Key)"},
            {"value": "transitous", "label": "Transitous — Weltweit (Community, Beta)"},
            {"value": "vagfr", "label": "VAG — Freiburg"},
            {"value": "vbn_otp", "label": "VBN — Bremen / Niedersachsen — OTP (API Key)"},
            {"value": "vbn_trias", "label": "VBN — Bremen / Niedersachsen — TRIAS (API Key)"},
            {"value": "vgn", "label": "VGN — Nürnberg"},
            {"value": "vrn", "label": "VRN — Rhein-Neckar"},
            {"value": "vrr", "label": "VRR — Rhein-Ruhr (NRW)"},
            {"value": "vvo", "label": "VVO — Dresden"},
            {"value": "vvs", "label": "VVS — Stuttgart"},
        ]
        return SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN))

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step - select entry type and provider."""
        if user_input is not None:
            self._entry_type = user_input.get("entry_type", "departures")

            if self._entry_type == "multi_stop":
                return await self.async_step_multi_stop()

            self._provider = user_input[CONF_PROVIDER]

            if self._provider == PROVIDER_OTP_CUSTOM:
                return await self.async_step_otp_custom_url()

            if self._provider == PROVIDER_OPT:
                return await self.async_step_opt_key()

            provider_class = get_provider_class(self._provider)
            if provider_class and provider_class(None).requires_api_key:  # type: ignore[arg-type]
                return await self.async_step_api_key()

            if self._entry_type == "trip":
                self._trip_search_phase = "origin"
                return await self.async_step_trip_search()

            return await self.async_step_stop_search()

        entry_type_options = {
            "departures": "Abfahrtsanzeige / Departure Monitor",
            "trip": "Verbindungssuche / Trip Planner (A → B)",
            "multi_stop": "Multi-Stop / Mehrere Haltestellen kombinieren",
        }

        schema = vol.Schema(
            {
                vol.Required("entry_type", default="departures"): vol.In(entry_type_options),
                vol.Required(CONF_PROVIDER, default=PROVIDER_VRR): self._provider_selector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    def _find_credentials_from_application_credentials(self, provider: str) -> dict:
        """Return API key for a provider from HA's Application Credentials store."""
        try:
            from homeassistant.components.application_credentials import DATA_COMPONENT

            storage = self.hass.data.get(DATA_COMPONENT)
            if not storage:
                return {}
            all_creds = storage.async_client_credentials(DOMAIN)
            auth_domain = f"{DOMAIN}.{provider}"
            if auth_domain not in all_creds:
                return {}
            credential = all_creds[auth_domain]
            api_key = credential.client_id
            secondary_key = credential.client_secret
            if not api_key:
                return {}
            if provider == PROVIDER_OPT:
                return {CONF_OPT_API_KEY: api_key}
            if provider == PROVIDER_OTP_CUSTOM:
                return {CONF_OTP_CUSTOM_API_KEY: api_key}
            if provider == PROVIDER_TRAFIKLAB_SE:
                return {CONF_TRAFIKLAB_API_KEY: api_key}
            if provider == PROVIDER_RMV:
                return {CONF_RMV_API_KEY: api_key}
            if provider == PROVIDER_NATIONAL_RAIL:
                return {CONF_NATIONAL_RAIL_API_KEY: api_key}
            if provider == PROVIDER_REJSEPLANEN:
                return {CONF_REJSEPLANEN_API_KEY: api_key}
            if provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
                return {CONF_VBN_API_KEY: api_key}
            if provider == PROVIDER_NTA_IE:
                result = {CONF_NTA_API_KEY: api_key}
                if secondary_key:
                    result[CONF_NTA_API_KEY_SECONDARY] = secondary_key
                return result
        except Exception as exc:
            _LOGGER.debug("Could not read from application_credentials: %s", exc)
        return {}

    def _find_existing_credentials(self, provider: str) -> dict:
        """Return stored credentials — checks Application Credentials store first, then config entries."""
        # Prefer central Application Credentials store
        result = self._find_credentials_from_application_credentials(provider)

        # For otp_custom also grab the URL from existing config entries (URLs are not credentials)
        if provider == PROVIDER_OTP_CUSTOM and CONF_OTP_BASE_URL not in result:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                ep = entry.data.get(CONF_PROVIDER) or entry.data.get("trip_provider")
                if ep == provider and CONF_OTP_BASE_URL in entry.data:
                    result[CONF_OTP_BASE_URL] = entry.data[CONF_OTP_BASE_URL]
                    break

        if result:
            return result

        # Fall back to searching existing config entries (legacy / first-run)
        key_map: Dict[str, list] = {
            PROVIDER_OPT: [CONF_OPT_API_KEY],
            PROVIDER_OTP_CUSTOM: [CONF_OTP_CUSTOM_API_KEY, CONF_OTP_BASE_URL],
            PROVIDER_VBN_OTP: [CONF_VBN_API_KEY],
            PROVIDER_VBN_TRIAS: [CONF_VBN_API_KEY],
            PROVIDER_TRAFIKLAB_SE: [CONF_TRAFIKLAB_API_KEY],
            PROVIDER_NTA_IE: [CONF_NTA_API_KEY, CONF_NTA_API_KEY_SECONDARY],
            PROVIDER_RMV: [CONF_RMV_API_KEY],
            PROVIDER_NATIONAL_RAIL: [CONF_NATIONAL_RAIL_API_KEY],
            PROVIDER_REJSEPLANEN: [CONF_REJSEPLANEN_API_KEY],
        }
        keys = key_map.get(provider, [])
        if not keys:
            return {}
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            ep = entry.data.get(CONF_PROVIDER) or entry.data.get("trip_provider")
            if ep == provider:
                found = {k: entry.data[k] for k in keys if k in entry.data}
                if found:
                    return found
        return {}

    _PROVIDER_CREDENTIAL_NAMES: Dict[str, str] = {
        PROVIDER_OPT: "openpublictransport.net (Deutschlandweit)",
        PROVIDER_OTP_CUSTOM: "OTP2 Eigene Instanz",
        PROVIDER_TRAFIKLAB_SE: "Trafiklab (Schweden)",
        PROVIDER_RMV: "RMV (Rhein-Main)",
        PROVIDER_VBN_OTP: "VBN (Bremen/Niedersachsen) — OTP",
        PROVIDER_VBN_TRIAS: "VBN (Bremen/Niedersachsen) — TRIAS",
        PROVIDER_NTA_IE: "NTA (Irland)",
        PROVIDER_NATIONAL_RAIL: "National Rail (Großbritannien)",
        PROVIDER_REJSEPLANEN: "Rejseplanen (Dänemark)",
    }

    async def _async_store_credential(self, provider: str) -> None:
        """Persist the current API key in HA's Application Credentials store."""
        if not self._api_key and provider != PROVIDER_OTP_CUSTOM:
            return
        secondary = ""
        key = self._api_key or ""
        if provider == PROVIDER_NTA_IE:
            secondary = self._api_key_secondary or ""
        if not key:
            return
        name = self._PROVIDER_CREDENTIAL_NAMES.get(provider, f"{provider.upper()} API Key")
        try:
            await async_import_client_credential(
                self.hass,
                DOMAIN,
                ClientCredential(
                    client_id=key,
                    client_secret=secondary,
                    name=name,
                ),
                auth_domain=f"{DOMAIN}.{provider}",
            )
        except Exception as exc:
            _LOGGER.debug("Could not store credential in application_credentials: %s", exc)

    async def async_step_opt_key(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Required API key step for the openpublictransport community server."""
        # Auto-reuse key from an existing entry for this provider
        if user_input is None and not self._api_key:
            creds = self._find_existing_credentials(PROVIDER_OPT)
            if creds.get(CONF_OPT_API_KEY):
                self._api_key = creds[CONF_OPT_API_KEY]
                if self._entry_type == "trip":
                    self._trip_search_phase = "origin"
                    return await self.async_step_trip_search()
                return await self.async_step_stop_search()

        errors: Dict[str, str] = {}
        if user_input is not None:
            key = user_input.get(CONF_OPT_API_KEY, "").strip()
            if not key:
                errors[CONF_OPT_API_KEY] = "opt_api_key_required"
            else:
                self._api_key = key
                if self._entry_type == "trip":
                    self._trip_search_phase = "origin"
                    return await self.async_step_trip_search()
                return await self.async_step_stop_search()

        schema = vol.Schema({vol.Required(CONF_OPT_API_KEY): str})
        return self.async_show_form(
            step_id="opt_key",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": (
                    "API key for api.openpublictransport.net — required. "
                    "Request a free key at openpublictransport.net/api-key."
                )
            },
        )

    async def async_step_otp_custom_url(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """URL + optional API key for a user-provided OTP2 instance."""
        # Auto-reuse URL + key from an existing entry
        if user_input is None and not self._otp_custom_url:
            creds = self._find_existing_credentials(PROVIDER_OTP_CUSTOM)
            if creds.get(CONF_OTP_BASE_URL):
                self._otp_custom_url = creds[CONF_OTP_BASE_URL]
                self._api_key = creds.get(CONF_OTP_CUSTOM_API_KEY) or None
                if self._entry_type == "trip":
                    self._trip_search_phase = "origin"
                    return await self.async_step_trip_search()
                return await self.async_step_stop_search()

        errors: Dict[str, str] = {}
        if user_input is not None:
            url = user_input.get(CONF_OTP_BASE_URL, "").strip()
            if not url:
                errors[CONF_OTP_BASE_URL] = "otp_url_required"
            else:
                api_key = user_input.get(CONF_OTP_CUSTOM_API_KEY, "").strip() or None
                # Health-check: verify the OTP instance is reachable before proceeding
                try:
                    session = async_get_clientsession(self.hass)
                    headers = {"Accept": "application/json"}
                    if api_key:
                        headers["X-API-Key"] = api_key
                    health_url = f"{url.rstrip('/')}/index"
                    async with session.get(
                        health_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status not in (200, 204):
                            errors[CONF_OTP_BASE_URL] = "cannot_connect"
                except Exception:
                    errors[CONF_OTP_BASE_URL] = "cannot_connect"

                if not errors:
                    self._otp_custom_url = url
                    self._api_key = api_key
                    if self._entry_type == "trip":
                        self._trip_search_phase = "origin"
                        return await self.async_step_trip_search()
                    return await self.async_step_stop_search()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_OTP_BASE_URL,
                    description={"suggested_value": "http://192.168.1.10:8080/otp/routers/default"},
                ): cv.url,
                vol.Optional(CONF_OTP_CUSTOM_API_KEY): str,
            }
        )
        return self.async_show_form(
            step_id="otp_custom_url",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": (
                    "Base URL of your OTP2 instance up to and including the router path, "
                    "e.g. http://192.168.1.10:8080/otp/routers/default. "
                    "Leave API key empty if your server runs without auth."
                )
            },
        )

    async def async_step_api_key(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle API key input for providers that require it."""
        errors = {}

        provider_class = get_provider_class(self._provider)
        if not provider_class or not provider_class(None).requires_api_key:  # type: ignore[arg-type]
            # Should not happen, but handle gracefully
            return await self.async_step_stop_search()

        # Auto-reuse credentials from an existing entry for this provider
        if user_input is None and not self._api_key:
            creds = self._find_existing_credentials(self._provider or "")
            if self._provider == PROVIDER_TRAFIKLAB_SE and creds.get(CONF_TRAFIKLAB_API_KEY):
                self._api_key = creds[CONF_TRAFIKLAB_API_KEY]
                return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_RMV and creds.get(CONF_RMV_API_KEY):
                self._api_key = creds[CONF_RMV_API_KEY]
                return await self._async_next_step_after_api_key()
            elif self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS) and creds.get(CONF_VBN_API_KEY):
                self._api_key = creds[CONF_VBN_API_KEY]
                return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_NTA_IE and creds.get(CONF_NTA_API_KEY):
                self._api_key = creds[CONF_NTA_API_KEY]
                self._api_key_secondary = creds.get(CONF_NTA_API_KEY_SECONDARY)
                return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_NATIONAL_RAIL and creds.get(CONF_NATIONAL_RAIL_API_KEY):
                self._api_key = creds[CONF_NATIONAL_RAIL_API_KEY]
                return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_REJSEPLANEN and creds.get(CONF_REJSEPLANEN_API_KEY):
                self._api_key = creds[CONF_REJSEPLANEN_API_KEY]
                return await self._async_next_step_after_api_key()

        if user_input is not None:
            if self._provider == PROVIDER_TRAFIKLAB_SE:
                api_key = user_input.get(CONF_TRAFIKLAB_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_TRAFIKLAB_API_KEY] = "trafiklab_api_key_required"
                else:
                    self._api_key = api_key
                    return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_NTA_IE:
                api_key = user_input.get(CONF_NTA_API_KEY, "").strip()
                api_key_secondary = user_input.get(CONF_NTA_API_KEY_SECONDARY, "").strip()
                if not api_key:
                    errors[CONF_NTA_API_KEY] = "nta_api_key_required"
                else:
                    self._api_key = api_key
                    self._api_key_secondary = api_key_secondary if api_key_secondary else None
                    return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_RMV:
                api_key = user_input.get(CONF_RMV_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_RMV_API_KEY] = "rmv_api_key_required"
                else:
                    self._api_key = api_key
                    return await self._async_next_step_after_api_key()
            elif self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
                api_key = user_input.get(CONF_VBN_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_VBN_API_KEY] = "vbn_api_key_required"
                else:
                    self._api_key = api_key
                    return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_NATIONAL_RAIL:
                api_key = user_input.get(CONF_NATIONAL_RAIL_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_NATIONAL_RAIL_API_KEY] = "national_rail_api_key_required"
                else:
                    self._api_key = api_key
                    return await self._async_next_step_after_api_key()
            elif self._provider == PROVIDER_REJSEPLANEN:
                api_key = user_input.get(CONF_REJSEPLANEN_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_REJSEPLANEN_API_KEY] = "rejseplanen_api_key_required"
                else:
                    self._api_key = api_key
                    return await self._async_next_step_after_api_key()

        # Show appropriate schema based on provider
        if self._provider == PROVIDER_TRAFIKLAB_SE:
            schema = vol.Schema(
                {
                    vol.Required(CONF_TRAFIKLAB_API_KEY): str,
                }
            )
            description = "Trafiklab API key is required. Get one at trafiklab.se"
        elif self._provider == PROVIDER_RMV:
            schema = vol.Schema(
                {
                    vol.Required(CONF_RMV_API_KEY): str,
                }
            )
            description = "RMV API key is required. Request one at opendata.rmv.de"
        elif self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
            schema = vol.Schema(
                {
                    vol.Required(CONF_VBN_API_KEY): str,
                }
            )
            description = "VBN API key is required. Request a free key at api@vbn.de"
        elif self._provider == PROVIDER_NATIONAL_RAIL:
            schema = vol.Schema({vol.Required(CONF_NATIONAL_RAIL_API_KEY): str})
            description = (
                "National Rail API key required. Register for free at opendata.nationalrail.co.uk (100k calls/month)."
            )
        elif self._provider == PROVIDER_REJSEPLANEN:
            schema = vol.Schema({vol.Required(CONF_REJSEPLANEN_API_KEY): str})
            description = "Rejseplanen API key required. Register for free at labs.rejseplanen.dk (50k calls/month, non-commercial)."
        else:  # NTA
            schema = vol.Schema(
                {
                    vol.Required(CONF_NTA_API_KEY): str,
                    vol.Optional(CONF_NTA_API_KEY_SECONDARY): str,
                }
            )
            description = "NTA Primary API key is required. Secondary key is optional (used as fallback if Primary fails). Get both keys at developer.nationaltransport.ie"

        return self.async_show_form(
            step_id="api_key",
            data_schema=schema,
            errors=errors,
            description_placeholders={"info": description},
        )

    async def _async_next_step_after_api_key(self) -> FlowResult:
        """Route to trip search or stop search depending on entry_type."""
        if self._entry_type == "trip":
            self._trip_search_phase = "origin"
            return await self.async_step_trip_search()
        if self._provider == PROVIDER_NTA_IE:
            return await self.async_step_nta_stop_id()
        return await self.async_step_stop_search()

    async def async_step_nta_stop_id(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """NTA: accept manual stop ID and validate connectivity before proceeding."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            station_id = user_input.get(CONF_STATION_ID, "").strip()
            if not station_id:
                errors[CONF_STATION_ID] = "station_id_required"
            else:
                # Validate: attempt a minimal GTFS-RT fetch to confirm key + reachability
                try:
                    session = async_get_clientsession(self.hass)
                    provider_instance = get_provider(
                        PROVIDER_NTA_IE,
                        session,
                        api_key=self._api_key,
                        api_key_secondary=self._api_key_secondary,
                    )
                    if provider_instance:
                        await provider_instance.fetch_departures(station_id, "", station_id, 1)
                except Exception:
                    errors["base"] = "cannot_connect"

                if not errors:
                    self._selected_stop = {"id": station_id, "name": station_id, "place": ""}
                    return await self.async_step_settings()

        schema = vol.Schema({vol.Required(CONF_STATION_ID): str})
        return self.async_show_form(
            step_id="nta_stop_id",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": (
                    "NTA stop IDs look like 8250DB002011. "
                    "Find your stop ID at developer.nationaltransport.ie or in the GTFS Static feed."
                )
            },
        )

    async def async_step_stop_search(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle combined stop search and selection step.

        Shows a search field. After searching, shows the results as a dropdown
        together with the search field so the user can refine or select.
        """
        # Validate API key for providers that need it
        if (
            self._provider in (PROVIDER_TRAFIKLAB_SE, PROVIDER_RMV, PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS)
            and not self._api_key
        ):
            return await self.async_step_api_key()
        if self._provider == PROVIDER_NTA_IE and not self._api_key:
            return self.async_show_form(
                step_id="api_key",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NTA_API_KEY): str,
                        vol.Optional(CONF_NTA_API_KEY_SECONDARY): str,
                    }
                ),
                errors={"base": "api_key_required"},
            )
        errors = {}

        if user_input is not None:
            # User selected a stop from dropdown
            selected_id = user_input.get("stop")
            if selected_id:
                for stop in self._found_stops:
                    if isinstance(stop, dict) and stop.get("id") == selected_id:
                        self._selected_stop = stop
                        return await self.async_step_settings()

            # User entered a search term
            search_term = user_input.get("stop_search", "").strip()
            if not search_term:
                errors["stop_search"] = "empty_search"
            else:
                try:
                    stops = await self._search_stops(search_term)
                except Exception as exc:
                    _LOGGER.error("Stop search raised exception: %s", exc)
                    stops = None

                if not isinstance(stops, list):
                    cache_key = self._get_cache_key(self._provider, search_term, "stop")
                    self._search_cache.pop(cache_key, None)
                    self._found_stops = []
                    errors["stop_search"] = "api_error"
                elif not stops:
                    errors["stop_search"] = "no_results"
                elif len(stops) == 1:
                    self._selected_stop = stops[0]
                    return await self.async_step_settings()
                else:
                    # Store results and show selection step
                    self._found_stops = stops
                    self._last_search_term = search_term
                    return await self.async_step_stop_select()

        schema = vol.Schema(
            {
                vol.Required("stop_search"): str,
            }
        )

        return self.async_show_form(
            step_id="stop_search",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "provider": self._provider.upper() if self._provider else "",
            },
        )

    async def async_step_stop_select(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Let user select from search results or refine the search."""
        if user_input is not None:
            # User selected a stop
            selected_id = user_input.get("stop")
            if selected_id == "__search_again__":
                # User wants to search again
                self._found_stops = []
                return await self.async_step_stop_search()

            if selected_id:
                for stop in self._found_stops:
                    if isinstance(stop, dict) and stop.get("id") == selected_id:
                        self._selected_stop = stop
                        return await self.async_step_settings()

            return await self.async_step_settings()

        # Load stops from temporary storage
        stops = self._found_stops

        if not isinstance(stops, list) or not stops:
            self._found_stops = []
            return await self.async_step_stop_search()

        # Build dropdown: "Haltestellenname, Ort" format
        stop_options = {"__search_again__": "🔍 Neue Suche / New search..."}
        for stop in stops:
            if isinstance(stop, dict) and "id" in stop and "name" in stop:
                name = stop["name"]
                place = stop.get("place", "")
                if place and place not in name:
                    stop_options[stop["id"]] = f"{name}, {place}"
                else:
                    stop_options[stop["id"]] = name

        schema = vol.Schema(
            {
                vol.Required("stop"): vol.In(stop_options),
            }
        )

        search_term = getattr(self, "_last_search_term", "")
        return self.async_show_form(
            step_id="stop_select",
            data_schema=schema,
            description_placeholders={
                "count": str(len(stops)),
                "search_term": search_term,
            },
        )

    async def async_step_settings(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle settings step - departures, transport types, scan interval."""
        # Define schema first (needed for error handling)
        schema = vol.Schema(
            {
                vol.Optional(CONF_DEPARTURES, default=DEFAULT_DEPARTURES): vol.All(int, vol.Range(min=1, max=20)),
                vol.Optional(CONF_TRANSPORTATION_TYPES, default=list(TRANSPORTATION_TYPES.keys())): cv.multi_select(
                    TRANSPORTATION_TYPES
                ),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    int, vol.Range(min=10, max=3600)
                ),
                vol.Optional(CONF_USE_PROVIDER_LOGO, default=False): bool,
                vol.Optional(CONF_DELAY_THRESHOLD, default=DEFAULT_DELAY_THRESHOLD): vol.All(
                    int, vol.Range(min=1, max=30)
                ),
                vol.Optional(CONF_LINE_FILTER, default=""): str,
                vol.Optional(CONF_DESTINATION_FILTER, default=""): str,
                vol.Optional(CONF_PLATFORM_FILTER, default=""): str,
                vol.Optional(CONF_FAVORITE_LINES, default=""): str,
                vol.Optional(CONF_WALKING_TIME, default=0): vol.All(int, vol.Range(min=0, max=30)),
            }
        )

        if user_input is not None:
            # Validate that we have a selected stop
            if self._selected_stop is None:
                return self.async_abort(reason="no_stop_selected")

            # Combine all collected data
            data = {
                CONF_PROVIDER: self._provider,
                CONF_STATION_ID: self._selected_stop.get("id"),
                "place_dm": self._selected_stop.get("place", ""),
                "name_dm": self._selected_stop.get("name", ""),
                "agency_name": self._selected_stop.get("agency", ""),
                CONF_DEPARTURES: user_input[CONF_DEPARTURES],
                CONF_TRANSPORTATION_TYPES: user_input[CONF_TRANSPORTATION_TYPES],
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                CONF_USE_PROVIDER_LOGO: user_input.get(CONF_USE_PROVIDER_LOGO, False),
                # These are offered by the settings form but used to be dropped
                # on save, so a filter set during setup silently did nothing
                # until it was entered again under Options.
                CONF_DELAY_THRESHOLD: user_input.get(CONF_DELAY_THRESHOLD, DEFAULT_DELAY_THRESHOLD),
                CONF_LINE_FILTER: user_input.get(CONF_LINE_FILTER, "").strip(),
                CONF_DESTINATION_FILTER: user_input.get(CONF_DESTINATION_FILTER, "").strip(),
                CONF_PLATFORM_FILTER: user_input.get(CONF_PLATFORM_FILTER, "").strip(),
                CONF_FAVORITE_LINES: user_input.get(CONF_FAVORITE_LINES, "").strip(),
                CONF_WALKING_TIME: user_input.get(CONF_WALKING_TIME, DEFAULT_WALKING_TIME),
            }
            # Add API key for Trafiklab or NTA (required)
            if self._provider == PROVIDER_TRAFIKLAB_SE:
                if not self._api_key:
                    # This shouldn't happen if flow is correct, but validate anyway
                    return self.async_show_form(
                        step_id="settings",
                        data_schema=schema,
                        errors={"base": "trafiklab_api_key_required"},
                    )
                data[CONF_TRAFIKLAB_API_KEY] = self._api_key
            elif self._provider == PROVIDER_NTA_IE:
                if not self._api_key:
                    # This shouldn't happen if flow is correct, but validate anyway
                    return self.async_show_form(
                        step_id="settings",
                        data_schema=schema,
                        errors={"base": "nta_api_key_required"},
                    )
                data[CONF_NTA_API_KEY] = self._api_key
                if self._api_key_secondary:
                    data[CONF_NTA_API_KEY_SECONDARY] = self._api_key_secondary
            elif self._provider == PROVIDER_RMV:
                if not self._api_key:
                    return self.async_show_form(
                        step_id="settings",
                        data_schema=schema,
                        errors={"base": "rmv_api_key_required"},
                    )
                data[CONF_RMV_API_KEY] = self._api_key
            elif self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
                if not self._api_key:
                    return self.async_show_form(
                        step_id="settings",
                        data_schema=schema,
                        errors={"base": "vbn_api_key_required"},
                    )
                data[CONF_VBN_API_KEY] = self._api_key
            elif self._provider == PROVIDER_NATIONAL_RAIL:
                if not self._api_key:
                    return self.async_show_form(
                        step_id="settings",
                        data_schema=schema,
                        errors={"base": "national_rail_api_key_required"},
                    )
                data[CONF_NATIONAL_RAIL_API_KEY] = self._api_key
            elif self._provider == PROVIDER_REJSEPLANEN:
                if not self._api_key:
                    return self.async_show_form(
                        step_id="settings",
                        data_schema=schema,
                        errors={"base": "rejseplanen_api_key_required"},
                    )
                data[CONF_REJSEPLANEN_API_KEY] = self._api_key
            elif self._provider == PROVIDER_OPT:
                if self._api_key:
                    data[CONF_OPT_API_KEY] = self._api_key
            elif self._provider == PROVIDER_OTP_CUSTOM:
                if self._otp_custom_url:
                    data[CONF_OTP_BASE_URL] = self._otp_custom_url
                if self._api_key:
                    data[CONF_OTP_CUSTOM_API_KEY] = self._api_key

            # Persist API key in Application Credentials store
            if self._provider:
                await self._async_store_credential(self._provider)

            # Create title (self._selected_stop validated above)
            place = self._selected_stop.get("place", "")
            name = self._selected_stop.get("name", "")
            title = f"{(self._provider or '').upper()} {place} - {name}".strip()

            # A filtered entry says what it is filtered to, both in its title and
            # in the device name, so two entries for one station are tellable
            # apart at a glance (issue #55).
            label = _filter_label(user_input)
            if label:
                title = f"{title} ({label})"

            self._found_stops = []

            if self._reconfiguring and self._reconfigure_entry:
                # Reconfigure only moves the entry to a different stop. Carry the
                # existing discriminator over untouched — regenerating it here
                # would rename every entity of the entry.
                for key in (CONF_ENTRY_SUFFIX, CONF_ENTRY_LABEL):
                    existing = self._reconfigure_entry.data.get(key)
                    if existing:
                        data[key] = existing
                return self.async_update_reload_and_abort(
                    self._reconfigure_entry,
                    title=title,
                    data=data,
                    reason="reconfigure_successful",
                )

            # Create unique ID (self._selected_stop validated above).
            #
            # An unfiltered entry keeps the historical f"{provider}_{stop_id}",
            # so nothing that already exists is renamed. A filtered entry gets a
            # stable suffix derived from its filters, which is what allows the
            # same station to be added twice for two directions — and still
            # aborts as already_configured when the filters are identical.
            unique_id = f"{self._provider}_{self._selected_stop['id']}"
            suffix = _filter_discriminator(user_input)
            if suffix:
                unique_id = f"{unique_id}_{suffix}"
                data[CONF_ENTRY_SUFFIX] = suffix
                data[CONF_ENTRY_LABEL] = label

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=title, data=data)

        stop_name = self._selected_stop.get("name", "Unknown") if self._selected_stop else "Unknown"

        return self.async_show_form(
            step_id="settings", data_schema=schema, description_placeholders={"stop": stop_name}
        )

    async def _search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops/stations using STOPFINDER API with caching.

        Args:
            search_term: Search term for stops

        Returns:
            List of stop dictionaries
        """
        # Check cache first
        cache_key = self._get_cache_key(self._provider, search_term, "stop")
        cached_results = self._get_from_cache(cache_key)

        if cached_results is not None:
            # Double-check that cached results is a list (defensive programming)
            if not isinstance(cached_results, list):
                _LOGGER.warning(
                    "Cache returned invalid type %s, expected list. Clearing cache entry.", type(cached_results)
                )
                self._search_cache.pop(cache_key, None)
            else:
                _LOGGER.debug("Returning %d cached results for: %s", len(cached_results), search_term)
                return cached_results

        # Cache miss - fetch from API
        _LOGGER.debug("Cache miss, fetching from API for: %s", search_term)

        # Use provider instance for stop search if available
        provider_instance = get_provider(
            self._provider,
            async_get_clientsession(self.hass),
            api_key=self._api_key,
            api_key_secondary=self._api_key_secondary,
            custom_url=self._otp_custom_url,
        )
        if provider_instance:
            try:
                results = await provider_instance.search_stops(search_term)
                # Store in cache
                self._store_in_cache(cache_key, results)
                return results
            except Exception as e:
                _LOGGER.error("Error searching stops with provider: %s", e, exc_info=True)

        # Fallback to old implementation
        if self._provider == PROVIDER_TRAFIKLAB_SE:
            return await self._search_stops_trafiklab(search_term)
        if self._provider == PROVIDER_NTA_IE:
            return await self._search_stops_nta(search_term)

        api_url = self._get_stopfinder_url()

        # URL-encode the search term to handle special characters (spaces, umlauts, etc.)
        encoded_search = quote(search_term, safe="")

        params = (
            f"outputFormat=RapidJSON&"
            f"locationServerActive=1&"
            f"type_sf=stop&"
            f"name_sf={encoded_search}&"
            f"SpEncId=0"
        )

        url = f"{api_url}?{params}"
        _LOGGER.debug("VRR/KVV/HVV stop search URL: %s", url)
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                    except (ValueError, aiohttp.ContentTypeError) as e:
                        _LOGGER.error("Invalid JSON response from API: %s", e)
                        return []

                    # Validate response type
                    if not isinstance(data, dict):
                        _LOGGER.error("API returned non-dict response: %s", type(data))
                        return []

                    _LOGGER.debug(
                        "API response type: %s, locations count: %s", type(data), len(data.get("locations", []))
                    )

                    result = self._parse_stopfinder_response(data, search_type="stop", search_term=search_term)

                    # Ensure we always return a list
                    if not isinstance(result, list):
                        _LOGGER.error("_parse_stopfinder_response returned %s instead of list", type(result))
                        return []

                    # Store in cache before returning
                    self._store_in_cache(cache_key, result)

                    return result
                elif response.status == 404:
                    _LOGGER.error("API endpoint not found (404)")
                elif response.status >= 500:
                    _LOGGER.error("API server error (status %s)", response.status)
                else:
                    _LOGGER.error("API returned status %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API request timeout after 10 seconds")
        except Exception as e:
            _LOGGER.error("Error searching stops: %s", e, exc_info=True)

        return []

    async def _search_stops_nta(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops - NTA requires direct stop_id input.

        Args:
            search_term: Search term (treated as stop_id for NTA)

        Returns:
            List with single stop if valid stop_id format
        """
        # NTA doesn't have a stop search API without GTFS Static
        # User needs to enter the stop_id directly
        # If the search term looks like a stop_id, return it as a result
        search_term = search_term.strip()
        if search_term:
            # Return the search term as a potential stop_id
            return [
                {
                    "id": search_term,
                    "name": f"Stop {search_term}",
                    "place": "Ireland",
                    "area_type": "",
                    "transport_modes": [],
                }
            ]
        return []

    def _get_stopfinder_url(self) -> str:
        """Get the STOPFINDER API URL based on provider."""
        if self._provider == PROVIDER_VRR:
            return "https://openservice-test.vrr.de/static03/XML_STOPFINDER_REQUEST"
        elif self._provider == PROVIDER_KVV:
            return "https://projekte.kvv-efa.de/sl3-alone/XML_STOPFINDER_REQUEST"
        elif self._provider == PROVIDER_HVV:
            # HVV uses the same efa.de domain as the departure API
            return "https://hvv.efa.de/efa/XML_STOPFINDER_REQUEST"
        else:
            return "https://openservice-test.vrr.de/static03/XML_STOPFINDER_REQUEST"

    async def _search_stops_trafiklab(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using Trafiklab Stop Lookup API.

        Args:
            search_term: Search term for stops

        Returns:
            List of stop dictionaries
        """
        if not self._api_key:
            _LOGGER.error("Trafiklab API key is required for stop search")
            return []

        # URL encode the search term to handle special characters
        encoded_search = quote(search_term, safe="")
        url = f"https://realtime-api.trafiklab.se/v1/stops/name/{encoded_search}"
        params = {"key": self._api_key}
        session = async_get_clientsession(self.hass)

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.error("Invalid JSON response from Trafiklab API: %s", e)
                            if attempt < max_retries:
                                await asyncio.sleep(2**attempt)
                                continue
                            return []

                        # Validate response type
                        if not isinstance(data, dict):
                            _LOGGER.error("Trafiklab API returned non-dict response: %s", type(data))
                            if attempt < max_retries:
                                await asyncio.sleep(2**attempt)
                                continue
                            return []

                        # Parse Trafiklab response
                        stop_groups = data.get("stop_groups", [])
                        results = []

                        for stop_group in stop_groups:
                            if not isinstance(stop_group, dict):
                                continue

                            # Get the first stop's place if available
                            stops = stop_group.get("stops", [])
                            place = None
                            if stops and isinstance(stops[0], dict):
                                # Try to extract place from stop name or use area name
                                stop_name = stop_group.get("name", "")
                                place = stop_name.split(",")[-1].strip() if "," in stop_name else None

                            result = {
                                "id": stop_group.get("id", ""),
                                "name": stop_group.get("name", ""),
                                "place": place or "",
                                "area_type": stop_group.get("area_type", ""),
                                "transport_modes": stop_group.get("transport_modes", []),
                            }
                            results.append(result)

                        # Store in cache only on success
                        cache_key = self._get_cache_key(self._provider, search_term, "stop")
                        self._store_in_cache(cache_key, results)

                        return results
                    elif response.status == 401:
                        _LOGGER.error("Trafiklab API authentication failed (401) - check API key")
                        # Don't retry on auth errors
                        return []
                    elif response.status == 404:
                        _LOGGER.warning("Trafiklab API endpoint not found (404) - stop may not exist")
                        # Don't retry on 404
                        return []
                    elif response.status >= 500:
                        _LOGGER.warning(
                            "Trafiklab API server error (status %s) on attempt %d/%d",
                            response.status,
                            attempt,
                            max_retries,
                        )
                        # Retry on server errors
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
                        _LOGGER.error(
                            "Trafiklab API server error (status %s) after %d attempts. "
                            "The Trafiklab service may be temporarily unavailable.",
                            response.status,
                            max_retries,
                        )
                    else:
                        _LOGGER.warning(
                            "Trafiklab API returned status %s on attempt %d/%d", response.status, attempt, max_retries
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
            except asyncio.TimeoutError:
                _LOGGER.warning("Trafiklab API request timeout on attempt %d/%d", attempt, max_retries)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                _LOGGER.error("Trafiklab API request timeout after %d attempts", max_retries)
            except ClientConnectorError as e:
                _LOGGER.warning("Trafiklab API connection error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                _LOGGER.error("Trafiklab API connection failed after %d attempts: %s", max_retries, e)
            except Exception as e:
                _LOGGER.error(
                    "Error searching Trafiklab stops on attempt %d/%d: %s", attempt, max_retries, e, exc_info=True
                )
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return []

    def _parse_stopfinder_response(
        self, data: Dict[str, Any], search_type: str = "stop", search_term: str = ""
    ) -> List[Dict[str, Any]]:
        """Parse STOPFINDER API response."""
        results = []

        try:
            # Validate that data is a dictionary
            if not isinstance(data, dict):
                _LOGGER.error("Invalid API response: expected dict, got %s", type(data))
                return []

            locations = data.get("locations", [])

            # Validate that locations is a list
            if not isinstance(locations, list):
                _LOGGER.error("Invalid locations in API response: expected list, got %s", type(locations))
                return []

            _LOGGER.debug("STOPFINDER returned %d locations for '%s'", len(locations), search_term)

            # Extract potential city/place names from search term for filtering
            search_lower = search_term.lower()

            for location in locations:
                # Skip non-dict entries
                if not isinstance(location, dict):
                    _LOGGER.debug("Skipping non-dict location entry: %s", location)
                    continue
                # Get basic info with validation
                loc_type = location.get("type", "unknown")
                if not isinstance(loc_type, str):
                    loc_type = "unknown"

                # Debug log all locations and their types
                _LOGGER.debug(
                    "Location: name='%s', type='%s', parent='%s'",
                    location.get("name", "?"),
                    loc_type,
                    location.get("parent", {}).get("name", "?") if isinstance(location.get("parent"), dict) else "?",
                )

                name = location.get("name", "")
                if not isinstance(name, str):
                    _LOGGER.debug("Skipping location with invalid name: %s", location)
                    continue

                # Skip entries with empty names
                if not name.strip():
                    _LOGGER.debug("Skipping location with empty name")
                    continue

                # For VRR/KVV/HVV, the ID might be in different fields
                properties = location.get("properties", {})
                if not isinstance(properties, dict):
                    properties = {}

                ref = location.get("ref", {})
                if not isinstance(ref, dict):
                    ref = {}

                loc_id = (
                    location.get("id")
                    or location.get("stateless")
                    or properties.get("stopId")
                    or str(ref.get("id", ""))
                )

                # Validate that we have an ID
                if not loc_id:
                    _LOGGER.debug("Skipping location without valid ID: %s", name)
                    continue

                # Get place/city info with validation
                parent = location.get("parent", {})
                if not isinstance(parent, dict):
                    parent = {}
                place = parent.get("name", "")

                if not place:
                    # Try to extract from disassembledName
                    disassembled = location.get("disassembledName", "")
                    if isinstance(disassembled, str) and disassembled:
                        place = disassembled.split(",")[0] if "," in disassembled else ""

                # Filter based on search type
                if search_type == "location":
                    # For location search, prefer localities and places
                    if loc_type in ["locality", "place", "poi"]:
                        results.append(
                            {
                                "id": loc_id,
                                "name": name,
                                "type": loc_type,
                                "place": place,
                                "relevance": self._calculate_relevance(search_lower, name.lower(), place.lower()),
                            }
                        )
                elif search_type == "stop":
                    # For stop search, accept stops, stations, platforms, and any type
                    # Some APIs use different type names, so be permissive
                    if loc_type in ["stop", "station", "platform", "poi", "any", "unknown"]:
                        results.append(
                            {
                                "id": loc_id,
                                "name": name,
                                "type": loc_type,
                                "place": place,
                                "relevance": self._calculate_relevance(search_lower, name.lower(), place.lower()),
                            }
                        )
                    else:
                        _LOGGER.debug("Skipping location with type '%s': %s", loc_type, name)

            # Sort by relevance (higher is better)
            results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

            # Remove relevance score before returning (not needed in UI)
            for result in results:
                result.pop("relevance", None)

            # Limit results to top 10
            results = results[:10]

        except Exception as e:
            _LOGGER.error("Error parsing stopfinder response: %s", e, exc_info=True)

        return results

    def _get_cache_key(self, provider: Optional[str], search_term: str, search_type: str = "stop") -> str:
        """Generate cache key for search request.

        Args:
            provider: Provider name (vrr, kvv, hvv)
            search_term: Search term
            search_type: Type of search (stop, location)

        Returns:
            Cache key string
        """
        # Normalize search term for consistent caching
        normalized_term = self._normalize_umlauts(search_term.lower().strip())
        return f"{provider or ''}:{search_type}:{normalized_term}"

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results if still valid.

        Args:
            cache_key: Cache key

        Returns:
            Cached results or None if expired/not found
        """
        if cache_key not in self._search_cache:
            return None

        cache_entry = self._search_cache[cache_key]
        cached_time = cache_entry.get("timestamp")
        cached_results = cache_entry.get("results")

        # Check if cache is still valid
        if cached_time and cached_results is not None:
            # Validate that cached results is a list
            if not isinstance(cached_results, list):
                _LOGGER.warning(
                    "Invalid cache entry: expected list, got %s. Removing from cache.", type(cached_results)
                )
                del self._search_cache[cache_key]
                return None

            age = (datetime.now() - cached_time).total_seconds()
            if age < self._cache_ttl:
                _LOGGER.debug("Cache hit for key: %s (age: %.1fs)", cache_key, age)
                return cached_results
            else:
                _LOGGER.debug("Cache expired for key: %s (age: %.1fs)", cache_key, age)
                # Remove expired entry
                del self._search_cache[cache_key]

        return None

    def _store_in_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Store search results in cache.

        Args:
            cache_key: Cache key
            results: Search results to cache
        """
        self._search_cache[cache_key] = {
            "timestamp": datetime.now(),
            "results": results,
        }
        _LOGGER.debug("Stored %d results in cache for key: %s", len(results), cache_key)

        # Limit cache size (keep only last 20 searches)
        if len(self._search_cache) > 20:
            # Remove oldest entry
            oldest_key = min(self._search_cache.keys(), key=lambda k: self._search_cache[k]["timestamp"])
            del self._search_cache[oldest_key]
            _LOGGER.debug("Cache size limit reached, removed oldest entry: %s", oldest_key)

    def _normalize_umlauts(self, text: str) -> str:
        """Normalize German umlauts for better matching.

        Converts: ä→ae, ö→oe, ü→ue, ß→ss
        """
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
            "Ä": "Ae",
            "Ö": "Oe",
            "Ü": "Ue",
        }
        for umlaut, replacement in replacements.items():
            text = text.replace(umlaut, replacement)
        return text

    def _fuzzy_match_ratio(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match ratio between two strings.

        Uses SequenceMatcher to calculate similarity ratio (0.0 to 1.0).
        Higher values indicate better matches.

        Args:
            str1: First string to compare
            str2: Second string to compare

        Returns:
            Similarity ratio between 0.0 (no match) and 1.0 (perfect match)
        """
        # Convert to lowercase for case-insensitive matching
        str1_lower = str1.lower()
        str2_lower = str2.lower()

        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, str1_lower, str2_lower).ratio()

    def _levenshtein_distance(self, str1: str, str2: str) -> int:
        """Calculate Levenshtein distance between two strings.

        The Levenshtein distance is the minimum number of single-character edits
        (insertions, deletions, or substitutions) required to change one string
        into the other.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Edit distance as integer (0 = identical strings)
        """
        if len(str1) < len(str2):
            return self._levenshtein_distance(str2, str1)

        if len(str2) == 0:
            return len(str1)

        # Create array with distances
        previous_row: list[int] = list(range(len(str2) + 1))
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _calculate_relevance(self, search_term: str, name: str, place: str) -> int:
        """Calculate relevance score for a search result.

        Higher score = more relevant result. Includes fuzzy matching for typo tolerance.

        Args:
            search_term: User's search input
            name: Name of the location/stop
            place: City/place name

        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0
        search_words = search_term.split()

        # Normalize umlauts for better matching
        search_term_norm = self._normalize_umlauts(search_term)
        name_norm = self._normalize_umlauts(name)
        place_norm = self._normalize_umlauts(place)
        search_words_norm = search_term_norm.split()

        # === Exact matching bonuses ===

        # Bonus if place name is in search term (with umlaut normalization)
        if place:
            # Check both original and normalized versions
            place_match = any(word in place for word in search_words)
            place_norm_match = any(word in place_norm for word in search_words_norm)
            if place_match or place_norm_match:
                score += 100
            # Check if place is a word in search
            if place in search_words or place_norm in search_words_norm:
                score += 200

        # Bonus for exact name match (both versions)
        if name == search_term or name_norm == search_term_norm:
            score += 300

        # Bonus for name starting with search term (both versions)
        if name.startswith(search_term) or name_norm.startswith(search_term_norm):
            score += 150

        # Bonus for each matching word in name
        name_words = name.split()
        name_words_norm = name_norm.split()
        for i, search_word in enumerate(search_words):
            if len(search_word) > 2:  # Only consider words longer than 2 chars
                search_word_norm = search_words_norm[i] if i < len(search_words_norm) else search_word
                for j, name_word in enumerate(name_words):
                    name_word_norm = name_words_norm[j] if j < len(name_words_norm) else name_word
                    # Check both original and normalized
                    if search_word in name_word or search_word_norm in name_word_norm:
                        score += 50

        # === Fuzzy matching bonuses ===

        # Fuzzy match on full strings (for typos)
        fuzzy_ratio = self._fuzzy_match_ratio(search_term_norm, name_norm)
        if fuzzy_ratio > 0.8:  # High similarity (e.g., "Dusseldorf" vs "Düsseldorf")
            score += int(fuzzy_ratio * 200)  # Up to +200 points
        elif fuzzy_ratio > 0.6:  # Medium similarity (e.g., minor typos)
            score += int(fuzzy_ratio * 100)  # Up to +100 points

        # Fuzzy match on individual words (better for multi-word searches)
        for search_word in search_words:
            if len(search_word) > 3:  # Only for meaningful words
                search_word_norm = self._normalize_umlauts(search_word.lower())
                best_word_match = 0.0

                # Find best matching word in name
                for name_word in name_words:
                    name_word_norm = self._normalize_umlauts(name_word.lower())
                    word_ratio = self._fuzzy_match_ratio(search_word_norm, name_word_norm)

                    if word_ratio > best_word_match:
                        best_word_match = word_ratio

                # Bonus for good word matches (typo tolerance)
                if best_word_match > 0.8:
                    score += int(best_word_match * 75)  # Up to +75 per word
                elif best_word_match > 0.7:
                    score += int(best_word_match * 40)  # Up to +40 per word

        # Levenshtein distance bonus for very similar strings (catches small typos)
        if len(search_term_norm) > 3 and len(name_norm) > 3:
            distance = self._levenshtein_distance(search_term_norm, name_norm)
            max_len = max(len(search_term_norm), len(name_norm))

            # If distance is small relative to string length, give bonus
            if distance <= 2 and max_len > 5:  # 1-2 character difference
                score += 120
            elif distance <= 3 and max_len > 8:  # 2-3 character difference
                score += 80

        # === Penalties ===

        # Penalty for very long place names (likely less specific)
        if place and len(place) > 20:
            score -= 10

        return score

    async def async_step_trip_search(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle trip stop search (used for both origin and destination)."""
        errors = {}
        phase = self._trip_search_phase  # "origin" or "destination"

        if user_input is not None:
            search_term = user_input.get("stop_search", "").strip()
            if not search_term:
                errors["stop_search"] = "empty_search"
            else:
                stops = await self._search_stops(search_term)
                if not stops:
                    errors["stop_search"] = "no_results"
                elif len(stops) == 1:
                    if phase == "origin":
                        self._trip_origin = stops[0]
                        self._trip_search_phase = "destination"
                        return await self.async_step_trip_search()
                    else:
                        self._trip_destination = stops[0]
                        return await self.async_step_trip_settings()
                else:
                    self._found_stops = stops
                    self._last_search_term = search_term
                    return await self.async_step_trip_select()

        if phase == "origin":
            title = "Starthaltestelle / Origin"
            desc = "Gib die Starthaltestelle ein.\nFormat: **Haltestelle, Ort**"
        else:
            origin_name = self._trip_origin.get("name", "") if self._trip_origin else ""
            title = "Zielhaltestelle / Destination"
            desc = f"Start: **{origin_name}**\nGib die Zielhaltestelle ein.\nFormat: **Haltestelle, Ort**"

        schema = vol.Schema({vol.Required("stop_search"): str})
        return self.async_show_form(
            step_id="trip_search",
            data_schema=schema,
            errors=errors,
            description_placeholders={"title": title, "desc": desc},
        )

    async def async_step_trip_select(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Select a stop for trip planning."""
        if user_input is not None:
            selected_id = user_input.get("stop")
            if selected_id == "__search_again__":
                self._found_stops = []
                return await self.async_step_trip_search()

            if selected_id:
                for stop in self._found_stops:
                    if isinstance(stop, dict) and stop.get("id") == selected_id:
                        if self._trip_search_phase == "origin":
                            self._trip_origin = stop
                            self._trip_search_phase = "destination"
                            self._found_stops = []
                            return await self.async_step_trip_search()
                        else:
                            self._trip_destination = stop
                            self._found_stops = []
                            return await self.async_step_trip_settings()

            return await self.async_step_trip_search()

        stops = self._found_stops
        if not isinstance(stops, list) or not stops:
            return await self.async_step_trip_search()

        stop_options = {"__search_again__": "🔍 Neue Suche / New search..."}
        for stop in stops:
            if isinstance(stop, dict) and "id" in stop and "name" in stop:
                name = stop["name"]
                place = stop.get("place", "")
                if place and place not in name:
                    stop_options[stop["id"]] = f"{name}, {place}"
                else:
                    stop_options[stop["id"]] = name

        schema = vol.Schema({vol.Required("stop"): vol.In(stop_options)})
        search_term = getattr(self, "_last_search_term", "")
        phase_label = "Start" if self._trip_search_phase == "origin" else "Ziel"
        return self.async_show_form(
            step_id="trip_select",
            data_schema=schema,
            description_placeholders={"count": str(len(stops)), "search_term": search_term, "phase": phase_label},
        )

    async def async_step_trip_settings(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle trip settings."""
        from .trip_sensor import (
            CONF_IS_TRIP,
            CONF_TRIP_DESTINATION,
            CONF_TRIP_DESTINATION_CITY,
            CONF_TRIP_ORIGIN,
            CONF_TRIP_ORIGIN_CITY,
            CONF_TRIP_PROVIDER,
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=120): vol.All(int, vol.Range(min=60, max=3600)),
            }
        )

        if user_input is not None:
            origin = self._trip_origin or {}
            dest = self._trip_destination or {}

            data = {
                CONF_IS_TRIP: True,
                CONF_TRIP_PROVIDER: self._provider,
                CONF_TRIP_ORIGIN: origin.get("name", ""),
                CONF_TRIP_ORIGIN_CITY: origin.get("place", ""),
                "trip_origin_id": origin.get("id", ""),
                CONF_TRIP_DESTINATION: dest.get("name", ""),
                CONF_TRIP_DESTINATION_CITY: dest.get("place", ""),
                "trip_destination_id": dest.get("id", ""),
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 120),
            }

            # Persist API key for providers that require one
            if self._api_key:
                if self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
                    data[CONF_VBN_API_KEY] = self._api_key
                elif self._provider == PROVIDER_OPT:
                    data[CONF_OPT_API_KEY] = self._api_key
                elif self._provider == PROVIDER_OTP_CUSTOM:
                    data[CONF_OTP_CUSTOM_API_KEY] = self._api_key
                    if self._otp_custom_url:
                        data[CONF_OTP_BASE_URL] = self._otp_custom_url

            # Persist API key in Application Credentials store
            if self._provider:
                await self._async_store_credential(self._provider)

            unique_id = f"{self._provider}_trip_{origin.get('id', '')}_{dest.get('id', '')}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            title = f"{(self._provider or '').upper()} {origin.get('name', '')} → {dest.get('name', '')}"

            self._found_stops = []
            return self.async_create_entry(title=title, data=data)

        origin_name = self._trip_origin.get("name", "") if self._trip_origin else ""
        dest_name = self._trip_destination.get("name", "") if self._trip_destination else ""

        return self.async_show_form(
            step_id="trip_settings",
            data_schema=schema,
            description_placeholders={"origin": origin_name, "destination": dest_name},
        )

    async def async_step_multi_stop(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configure a multi-stop sensor by selecting existing entities."""
        from .multi_stop import CONF_IS_MULTI_STOP, CONF_MULTI_STOP_NAME, CONF_SOURCE_ENTITIES

        if user_input is not None:
            name = user_input.get("name", "Multi-Stop")
            entities_str = user_input.get("entities", "")
            entities = [e.strip() for e in entities_str.split(",") if e.strip()]

            if len(entities) < 2:
                return self.async_show_form(
                    step_id="multi_stop",
                    data_schema=vol.Schema(
                        {
                            vol.Required("name", default=name): str,
                            vol.Required("entities", default=entities_str): str,
                        }
                    ),
                    errors={"entities": "min_two_entities"},
                )

            data = {
                CONF_IS_MULTI_STOP: True,
                CONF_MULTI_STOP_NAME: name,
                CONF_SOURCE_ENTITIES: entities,
            }

            unique_id = f"multi_stop_{'_'.join(sorted(entities))}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=f"Multi-Stop: {name}", data=data)

        # Get existing departure sensors for hint
        existing = [
            eid
            for eid in self.hass.states.async_entity_ids("sensor")
            if self.hass.states.get(eid) and self.hass.states.get(eid).attributes.get("departures") is not None
        ]
        hint = ", ".join(existing[:3]) if existing else "sensor.vrr_..."

        schema = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("entities"): str,
            }
        )

        return self.async_show_form(
            step_id="multi_stop",
            data_schema=schema,
            description_placeholders={"hint": hint},
        )

    async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle reconfiguration — let the user change the monitored stop."""
        self._reconfiguring = True
        self._reconfigure_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if self._reconfigure_entry:
            self._provider = self._reconfigure_entry.data.get(CONF_PROVIDER)
        return await self.async_step_stop_search(user_input)

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Handle re-authentication when an API key expires or is rotated."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._provider = entry_data.get(CONF_PROVIDER) or entry_data.get("trip_provider")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Show re-authentication form and update credentials on submit."""
        errors: Dict[str, str] = {}
        entry = self._reauth_entry

        if user_input is not None:
            new_data = dict(entry.data)

            if self._provider == PROVIDER_TRAFIKLAB_SE:
                api_key = user_input.get(CONF_TRAFIKLAB_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_TRAFIKLAB_API_KEY] = "trafiklab_api_key_required"
                else:
                    new_data[CONF_TRAFIKLAB_API_KEY] = api_key
                    self._api_key = api_key
            elif self._provider == PROVIDER_RMV:
                api_key = user_input.get(CONF_RMV_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_RMV_API_KEY] = "rmv_api_key_required"
                else:
                    new_data[CONF_RMV_API_KEY] = api_key
                    self._api_key = api_key
            elif self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
                api_key = user_input.get(CONF_VBN_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_VBN_API_KEY] = "vbn_api_key_required"
                else:
                    new_data[CONF_VBN_API_KEY] = api_key
                    self._api_key = api_key
            elif self._provider == PROVIDER_NTA_IE:
                api_key = user_input.get(CONF_NTA_API_KEY, "").strip()
                secondary = user_input.get(CONF_NTA_API_KEY_SECONDARY, "").strip()
                if not api_key:
                    errors[CONF_NTA_API_KEY] = "nta_api_key_required"
                else:
                    new_data[CONF_NTA_API_KEY] = api_key
                    if secondary:
                        new_data[CONF_NTA_API_KEY_SECONDARY] = secondary
                    self._api_key = api_key
                    self._api_key_secondary = secondary or None
            elif self._provider == PROVIDER_OPT:
                api_key = user_input.get(CONF_OPT_API_KEY, "").strip()
                if not api_key:
                    errors[CONF_OPT_API_KEY] = "opt_api_key_required"
                else:
                    new_data[CONF_OPT_API_KEY] = api_key
                    self._api_key = api_key
            elif self._provider == PROVIDER_OTP_CUSTOM:
                api_key = user_input.get(CONF_OTP_CUSTOM_API_KEY, "").strip()
                base_url = user_input.get(CONF_OTP_BASE_URL, "").strip()
                if base_url:
                    new_data[CONF_OTP_BASE_URL] = base_url
                if api_key:
                    new_data[CONF_OTP_CUSTOM_API_KEY] = api_key
                self._api_key = api_key or None

            if not errors:
                if self._api_key:
                    await self._async_store_credential(self._provider)
                return self.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                    reason="reauth_successful",
                )

        # Build provider-specific schema pre-filled with current key
        if self._provider == PROVIDER_TRAFIKLAB_SE:
            schema = vol.Schema(
                {vol.Required(CONF_TRAFIKLAB_API_KEY, default=entry.data.get(CONF_TRAFIKLAB_API_KEY, "")): str}
            )
            description = "Trafiklab API key expired or invalid. Get a new one at trafiklab.se."
        elif self._provider == PROVIDER_RMV:
            schema = vol.Schema({vol.Required(CONF_RMV_API_KEY, default=entry.data.get(CONF_RMV_API_KEY, "")): str})
            description = "RMV API key expired or invalid. Request a new one at opendata.rmv.de."
        elif self._provider in (PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS):
            schema = vol.Schema({vol.Required(CONF_VBN_API_KEY, default=entry.data.get(CONF_VBN_API_KEY, "")): str})
            description = "VBN API key expired or invalid. Request a new key at api@vbn.de."
        elif self._provider == PROVIDER_NTA_IE:
            schema = vol.Schema(
                {
                    vol.Required(CONF_NTA_API_KEY, default=entry.data.get(CONF_NTA_API_KEY, "")): str,
                    vol.Optional(
                        CONF_NTA_API_KEY_SECONDARY, default=entry.data.get(CONF_NTA_API_KEY_SECONDARY, "")
                    ): str,
                }
            )
            description = "NTA API key expired or invalid. Get new keys at developer.nationaltransport.ie."
        elif self._provider == PROVIDER_OPT:
            schema = vol.Schema({vol.Required(CONF_OPT_API_KEY, default=entry.data.get(CONF_OPT_API_KEY, "")): str})
            description = "openpublictransport.net API key expired or invalid. Request a new key at openpublictransport.net/api-key."
        elif self._provider == PROVIDER_OTP_CUSTOM:
            schema = vol.Schema(
                {
                    vol.Required(CONF_OTP_BASE_URL, default=entry.data.get(CONF_OTP_BASE_URL, "")): str,
                    vol.Optional(CONF_OTP_CUSTOM_API_KEY, default=entry.data.get(CONF_OTP_CUSTOM_API_KEY, "")): str,
                }
            )
            description = "OTP2 server URL or API key changed. Enter the new values."
        else:
            return self.async_abort(reason="no_reauth_needed")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"info": description},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OpenPublicTransportOptionsFlowHandler(config_entry)


class OpenPublicTransportOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle VRR options."""

    def __init__(self, config_entry=None):
        """Initialize options flow.

        Note: In Home Assistant 2025.12+, config_entry is a read-only property
        set automatically by the framework. For older versions, we need to
        set it manually.
        """
        # Try to set config_entry for older HA versions (pre-2025.12)
        # In newer versions this will be ignored as it's a read-only property
        try:
            self.config_entry = config_entry
        except AttributeError:
            # HA 2025.12+ - config_entry is set automatically by the framework
            pass

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values from options or fall back to data
        current_departures = self.config_entry.options.get(
            CONF_DEPARTURES, self.config_entry.data.get(CONF_DEPARTURES, DEFAULT_DEPARTURES)
        )
        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_transport_types = self.config_entry.options.get(
            CONF_TRANSPORTATION_TYPES,
            self.config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES.keys())),
        )
        current_use_logo = self.config_entry.options.get(
            CONF_USE_PROVIDER_LOGO,
            self.config_entry.data.get(CONF_USE_PROVIDER_LOGO, False),
        )
        current_delay_threshold = self.config_entry.options.get(
            CONF_DELAY_THRESHOLD,
            self.config_entry.data.get(CONF_DELAY_THRESHOLD, DEFAULT_DELAY_THRESHOLD),
        )
        current_line_filter = self.config_entry.options.get(
            CONF_LINE_FILTER,
            self.config_entry.data.get(CONF_LINE_FILTER, ""),
        )
        current_destination_filter = self.config_entry.options.get(
            CONF_DESTINATION_FILTER,
            self.config_entry.data.get(CONF_DESTINATION_FILTER, ""),
        )
        current_platform_filter = self.config_entry.options.get(
            CONF_PLATFORM_FILTER,
            self.config_entry.data.get(CONF_PLATFORM_FILTER, ""),
        )
        current_walking_time = self.config_entry.options.get(
            CONF_WALKING_TIME,
            self.config_entry.data.get(CONF_WALKING_TIME, 0),
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_DEPARTURES, default=current_departures): vol.All(int, vol.Range(min=1, max=20)),
                vol.Optional(CONF_SCAN_INTERVAL, default=current_scan_interval): vol.All(
                    int, vol.Range(min=30, max=3600)
                ),
                vol.Optional(CONF_TRANSPORTATION_TYPES, default=current_transport_types): cv.multi_select(
                    TRANSPORTATION_TYPES
                ),
                vol.Optional(CONF_USE_PROVIDER_LOGO, default=current_use_logo): bool,
                vol.Optional(CONF_DELAY_THRESHOLD, default=current_delay_threshold): vol.All(
                    int, vol.Range(min=1, max=30)
                ),
                vol.Optional(CONF_LINE_FILTER, default=current_line_filter): str,
                vol.Optional(CONF_DESTINATION_FILTER, default=current_destination_filter): str,
                vol.Optional(CONF_PLATFORM_FILTER, default=current_platform_filter): str,
                vol.Optional(
                    CONF_FAVORITE_LINES,
                    default=self.config_entry.options.get(
                        CONF_FAVORITE_LINES, self.config_entry.data.get(CONF_FAVORITE_LINES, "")
                    ),
                ): str,
                vol.Optional(CONF_WALKING_TIME, default=current_walking_time): vol.All(int, vol.Range(min=0, max=30)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
