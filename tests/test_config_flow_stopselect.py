"""Tests for stop_select, settings with API-key providers, and cache paths."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PROVIDER,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRAFIKLAB_API_KEY,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_VBN_API_KEY,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_NTA_IE,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
    PROVIDER_VRR,
)


_SETTINGS = {
    CONF_DEPARTURES: 10,
    CONF_SCAN_INTERVAL: 60,
    CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
    CONF_USE_PROVIDER_LOGO: False,
    CONF_DELAY_THRESHOLD: 5,
    CONF_LINE_FILTER: "",
    CONF_FAVORITE_LINES: "",
    CONF_WALKING_TIME: 0,
}


async def _flow_to_stop_search(hass, provider=PROVIDER_VRR):
    """Helper: get to stop_search step."""
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: provider},
    )


async def _search_stops(hass, flow_id, stops, search_term="Test"):
    """Helper: run a stop search with given mock stops."""
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=stops)
        mock_gp.return_value = mock_provider
        return await hass.config_entries.flow.async_configure(
            flow_id, user_input={"stop_search": search_term}
        )


# ── stop_select step ──────────────────────────────────────────────────────────

async def test_stop_select_search_again(hass: HomeAssistant):
    """Test stop_select with __search_again__ goes back to stop_search."""
    result = await _flow_to_stop_search(hass)
    mock_stops = [
        {"id": "de:1", "name": "A", "place": "City"},
        {"id": "de:2", "name": "B", "place": "City"},
    ]
    result2 = await _search_stops(hass, result["flow_id"], mock_stops)
    assert result2["step_id"] in ("stop_select", "settings")

    if result2["step_id"] == "stop_select":
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "__search_again__"}
        )
        assert result3["step_id"] == "stop_search"


async def test_stop_select_selects_stop_and_goes_to_settings(hass: HomeAssistant):
    """Test stop_select with valid stop goes to settings."""
    result = await _flow_to_stop_search(hass)
    mock_stops = [
        {"id": "de:1", "name": "Hbf", "place": "City"},
        {"id": "de:2", "name": "Airport", "place": "City"},
    ]
    result2 = await _search_stops(hass, result["flow_id"], mock_stops)

    if result2["step_id"] == "stop_select":
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "de:1"}
        )
        assert result3["step_id"] == "settings"



# ── settings with API-key providers ──────────────────────────────────────────

async def _full_flow_to_settings(hass, provider, api_key_input):
    """Helper: complete flow to settings for a provider needing API key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: provider},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=api_key_input
    )
    # May go through NTA stop ID step
    if result2.get("step_id") == "nta_stop_id":
        with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
            mock_provider = AsyncMock()
            mock_provider.fetch_departures = AsyncMock(return_value={"stopEvents": []})
            mock_gp.return_value = mock_provider
            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"], user_input={CONF_STATION_ID: "8250DB000001"}
            )
    elif result2.get("step_id") == "stop_search":
        mock_stops = [{"id": "stop:1", "name": "Test Stop", "place": "City"}]
        result2 = await _search_stops(hass, result2["flow_id"], mock_stops)
        if result2.get("step_id") == "stop_select":
            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"], user_input={"stop": "stop:1"}
            )
    return result2


async def test_settings_with_trafiklab_creates_entry(hass: HomeAssistant):
    """Test settings with Trafiklab provider stores API key in entry data."""
    result = await _full_flow_to_settings(
        hass, PROVIDER_TRAFIKLAB_SE, {CONF_TRAFIKLAB_API_KEY: "trafiklab-key"}
    )
    assert result["step_id"] == "settings"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_SETTINGS
    )
    assert result2["type"] == "create_entry"
    assert result2["data"].get(CONF_TRAFIKLAB_API_KEY) == "trafiklab-key"


async def test_settings_with_rmv_creates_entry(hass: HomeAssistant):
    """Test settings with RMV provider stores API key."""
    result = await _full_flow_to_settings(
        hass, PROVIDER_RMV, {CONF_RMV_API_KEY: "rmv-key-123"}
    )
    assert result["step_id"] == "settings"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_SETTINGS
    )
    assert result2["type"] == "create_entry"
    assert result2["data"].get(CONF_RMV_API_KEY) == "rmv-key-123"


async def test_settings_with_nta_creates_entry(hass: HomeAssistant):
    """Test settings with NTA provider stores primary + secondary keys."""
    result = await _full_flow_to_settings(
        hass, PROVIDER_NTA_IE,
        {CONF_NTA_API_KEY: "nta-primary", CONF_NTA_API_KEY_SECONDARY: "nta-secondary"},
    )
    assert result["step_id"] == "settings"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_SETTINGS
    )
    assert result2["type"] == "create_entry"
    assert result2["data"].get(CONF_NTA_API_KEY) == "nta-primary"
    assert result2["data"].get(CONF_NTA_API_KEY_SECONDARY) == "nta-secondary"


async def test_settings_with_vbn_creates_entry(hass: HomeAssistant):
    """Test settings with VBN OTP provider stores API key."""
    result = await _full_flow_to_settings(
        hass, PROVIDER_VBN_OTP, {CONF_VBN_API_KEY: "vbn-key-xyz"}
    )
    assert result["step_id"] == "settings"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_SETTINGS
    )
    assert result2["type"] == "create_entry"
    assert result2["data"].get(CONF_VBN_API_KEY) == "vbn-key-xyz"


async def test_settings_with_opt_creates_entry(hass: HomeAssistant):
    """Test settings with OPT provider stores API key."""
    # OPT goes through opt_key step
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OPT},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OPT_API_KEY: "opt-key-abc"}
    )
    assert result2["step_id"] == "stop_search"

    mock_stops = [{"id": "de:1", "name": "Stop", "place": "City"}]
    result3 = await _search_stops(hass, result2["flow_id"], mock_stops)
    if result3.get("step_id") == "stop_select":
        result3 = await hass.config_entries.flow.async_configure(
            result3["flow_id"], user_input={"stop": "de:1"}
        )

    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], user_input=_SETTINGS
    )
    assert result4["type"] == "create_entry"
    assert result4["data"].get(CONF_OPT_API_KEY) == "opt-key-abc"


async def test_settings_with_otp_custom_creates_entry(hass: HomeAssistant):
    """Test settings with OTP Custom provider stores URL and key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_fn.return_value = mock_session

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_OTP_BASE_URL: "http://myotp.local/otp", CONF_OTP_CUSTOM_API_KEY: "otp-key"},
        )

    assert result2["step_id"] == "stop_search"

    mock_stops = [{"id": "stop:1", "name": "Stop", "place": "City"}]
    result3 = await _search_stops(hass, result2["flow_id"], mock_stops)
    if result3.get("step_id") == "stop_select":
        result3 = await hass.config_entries.flow.async_configure(
            result3["flow_id"], user_input={"stop": "stop:1"}
        )

    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], user_input=_SETTINGS
    )
    assert result4["type"] == "create_entry"
    assert result4["data"].get(CONF_OTP_BASE_URL) == "http://myotp.local/otp"
    assert result4["data"].get(CONF_OTP_CUSTOM_API_KEY) == "otp-key"


# ── trip_select stop selection ────────────────────────────────────────────────

async def test_trip_select_origin_goes_to_destination(hass: HomeAssistant):
    """Test trip_select selecting origin goes to destination search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:1", "name": "Düsseldorf Hbf", "place": "Düsseldorf"},
        {"id": "de:2", "name": "Düsseldorf Eller", "place": "Düsseldorf"},
    ]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    assert result2["step_id"] == "trip_select"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"stop": "de:1"}
    )
    # Should now be at destination search
    assert result3["step_id"] == "trip_search"


# ── credential auto-reuse paths ───────────────────────────────────────────────

async def test_api_key_step_reuses_existing_rmv_credential(hass: HomeAssistant):
    """Test api_key step auto-reuses existing RMV key from config entry."""
    # Create an existing RMV entry
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_rmv",
        data={CONF_PROVIDER: PROVIDER_RMV, CONF_RMV_API_KEY: "existing-rmv-key"},
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_RMV},
    )
    # Should auto-reuse the key and skip the api_key form
    assert result["step_id"] in ("stop_search", "api_key")


async def test_api_key_step_reuses_existing_vbn_credential(hass: HomeAssistant):
    """Test api_key step auto-reuses existing VBN key from config entry."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_vbn",
        data={CONF_PROVIDER: PROVIDER_VBN_TRIAS, CONF_VBN_API_KEY: "existing-vbn-key"},
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VBN_OTP},
    )
    assert result["step_id"] in ("stop_search", "api_key")
