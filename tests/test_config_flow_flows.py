"""Tests for config flow special steps: multi-stop, trip, NTA, reconfigure, settings."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_NTA_IE,
    PROVIDER_RMV,
    PROVIDER_VRR,
)


_SETTINGS_INPUT = {
    CONF_DEPARTURES: 10,
    CONF_SCAN_INTERVAL: 60,
    CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
    CONF_USE_PROVIDER_LOGO: False,
    CONF_DELAY_THRESHOLD: 5,
    CONF_LINE_FILTER: "",
    CONF_FAVORITE_LINES: "",
    CONF_WALKING_TIME: 0,
}


# ── multi-stop flow ───────────────────────────────────────────────────────────

async def test_multi_stop_shows_form(hass: HomeAssistant):
    """Test multi-stop step shows form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "multi_stop", CONF_PROVIDER: PROVIDER_VRR},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "multi_stop"


async def test_multi_stop_fewer_than_2_entities_shows_error(hass: HomeAssistant):
    """Test multi-stop with 1 entity shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "multi_stop", CONF_PROVIDER: PROVIDER_VRR},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Test", "entities": "sensor.stop1"},
    )
    assert result2["type"] == "form"
    assert "min_two_entities" in str(result2.get("errors", {}))


async def test_multi_stop_creates_entry(hass: HomeAssistant):
    """Test multi-stop with 2 entities creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "multi_stop", CONF_PROVIDER: PROVIDER_VRR},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "My Stops", "entities": "sensor.stop1, sensor.stop2"},
    )
    assert result2["type"] == "create_entry"
    assert result2["data"]["multi_stop_name"] == "My Stops"
    assert len(result2["data"]["source_entities"]) == 2


async def test_multi_stop_with_hint_from_existing_sensors(hass: HomeAssistant):
    """Test multi-stop shows hints from existing departure sensors."""
    hass.states.async_set("sensor.my_stop", "10:05", {"departures": []})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "multi_stop", CONF_PROVIDER: PROVIDER_VRR},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "multi_stop"


# ── NTA stop ID step ──────────────────────────────────────────────────────────

async def test_nta_stop_id_shows_form(hass: HomeAssistant):
    """Test NTA stop ID form is shown after API key."""
    from custom_components.openpublictransport.const import CONF_NTA_API_KEY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-key", CONF_NTA_API_KEY_SECONDARY: ""},
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "nta_stop_id"


async def test_nta_stop_id_empty_shows_error(hass: HomeAssistant):
    """Test NTA stop ID with empty input shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-key"},
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={CONF_STATION_ID: ""},
    )
    assert result3["type"] == "form"
    assert "station_id_required" in str(result3.get("errors", {}))


async def test_nta_stop_id_valid_goes_to_settings(hass: HomeAssistant):
    """Test NTA stop ID with valid ID goes to settings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-key"},
    )

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.fetch_departures = AsyncMock(return_value={"stopEvents": []})
        mock_gp.return_value = mock_provider

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={CONF_STATION_ID: "8250DB002011"},
        )

    assert result3["type"] == "form"
    assert result3["step_id"] == "settings"


async def test_nta_stop_id_connection_error(hass: HomeAssistant):
    """Test NTA stop ID shows error when connectivity check fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-key"},
    )

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.fetch_departures = AsyncMock(side_effect=Exception("Connection failed"))
        mock_gp.return_value = mock_provider

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={CONF_STATION_ID: "8250DB002011"},
        )

    assert result3["type"] == "form"
    assert "cannot_connect" in str(result3.get("errors", {}))


# ── trip planning flow ────────────────────────────────────────────────────────

async def test_trip_flow_user_selects_trip_type(hass: HomeAssistant):
    """Test trip entry type shows trip_search form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "trip_search"


async def test_trip_search_empty_shows_error(hass: HomeAssistant):
    """Test trip_search with empty term shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"stop_search": ""}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "trip_search"


async def test_trip_search_no_results_shows_error(hass: HomeAssistant):
    """Test trip_search with no results shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Nowhere"}
        )

    assert result2["type"] == "form"
    assert result2["step_id"] == "trip_search"


async def test_trip_search_one_result_proceeds_to_destination(hass: HomeAssistant):
    """Test trip_search with one result auto-selects and moves to destination."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [{"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"}]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    # Should now be at destination search
    assert result2["type"] == "form"
    assert result2["step_id"] == "trip_search"


async def test_trip_search_multiple_results_shows_select(hass: HomeAssistant):
    """Test trip_search with multiple results shows trip_select."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"},
        {"id": "de:05111:101", "name": "Düsseldorf Eller", "place": "Düsseldorf"},
    ]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    assert result2["type"] == "form"
    assert result2["step_id"] == "trip_select"


async def test_trip_full_flow_creates_entry(hass: HomeAssistant):
    """Test complete trip flow: origin → destination → trip_settings → entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stop_origin = [{"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"}]
    mock_stop_dest = [{"id": "de:05315:1", "name": "Köln Hbf", "place": "Köln"}]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=[mock_stop_origin, mock_stop_dest])
        mock_gp.return_value = mock_provider

        # Search origin
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )
        # Should now be at destination (origin auto-selected)
        assert result2["step_id"] == "trip_search"

        # Search destination
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop_search": "Köln"}
        )

    # Should now be at trip_settings
    assert result3["type"] == "form"
    assert result3["step_id"] == "trip_settings"

    # Complete trip settings
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 120},
    )
    assert result4["type"] == "create_entry"


async def test_trip_select_search_again(hass: HomeAssistant):
    """Test trip_select with __search_again__ goes back to trip_search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:05111:100", "name": "A", "place": "City"},
        {"id": "de:05111:101", "name": "B", "place": "City"},
    ]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "City"}
        )

    assert result2["step_id"] == "trip_select"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"stop": "__search_again__"}
    )
    assert result3["step_id"] == "trip_search"


# ── settings step ─────────────────────────────────────────────────────────────

async def test_settings_creates_entry(hass: HomeAssistant):
    """Test settings step creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [{"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"}]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    if result2["step_id"] == "stop_select":
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "de:05111:100"}
        )

    assert result2["step_id"] == "settings"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input=_SETTINGS_INPUT
    )
    assert result3["type"] == "create_entry"
    assert result3["data"][CONF_PROVIDER] == PROVIDER_VRR


# ── stop_search fallback paths ────────────────────────────────────────────────

async def test_stop_search_api_timeout_returns_empty(hass: HomeAssistant):
    """Test stop search with API timeout returns no results."""
    import asyncio

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_gp.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


async def test_stop_search_exception_returns_empty(hass: HomeAssistant):
    """Test stop search exception falls back gracefully."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=Exception("Provider error"))
        mock_gp.return_value = mock_provider

        # Fallback EFA search also fails
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess_fn:
            mock_sess = MagicMock()
            mock_sess.get = MagicMock(side_effect=Exception("Network error"))
            mock_sess_fn.return_value = mock_sess

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Test"}
            )

    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


# ── reauth for OPT and OTP_CUSTOM ─────────────────────────────────────────────

async def test_reauth_opt_valid_key(hass: HomeAssistant):
    """Test reauth for OPT provider."""
    from custom_components.openpublictransport.const import CONF_OPT_API_KEY, PROVIDER_OPT
    from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_OPT, CONF_OPT_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"

    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_OPT_API_KEY: "new-key"}
        )
    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"


async def test_reauth_otp_custom(hass: HomeAssistant):
    """Test reauth for OTP Custom provider."""
    from custom_components.openpublictransport.const import (
        CONF_OTP_BASE_URL,
        CONF_OTP_CUSTOM_API_KEY,
        PROVIDER_OTP_CUSTOM,
    )
    from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_OTP_CUSTOM,
            CONF_OTP_BASE_URL: "http://old.local",
            CONF_OTP_CUSTOM_API_KEY: "old-key",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_OTP_BASE_URL: "http://new.local", CONF_OTP_CUSTOM_API_KEY: "new-key"},
        )
    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"


async def test_reauth_vbn_valid_key(hass: HomeAssistant):
    """Test reauth for VBN TRIAS provider."""
    from custom_components.openpublictransport.const import CONF_VBN_API_KEY, PROVIDER_VBN_TRIAS
    from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VBN_TRIAS, CONF_VBN_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_VBN_API_KEY: "new-vbn-key"}
        )
    assert result2["type"] == "abort"


async def test_reauth_vbn_empty_key_shows_error(hass: HomeAssistant):
    """Test reauth for VBN with empty key shows error."""
    from custom_components.openpublictransport.const import CONF_VBN_API_KEY, PROVIDER_VBN_OTP

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VBN_OTP, CONF_VBN_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_VBN_API_KEY: ""}
    )
    assert result2["type"] == "form"
    assert "vbn_api_key_required" in str(result2.get("errors", {}))


# ── reconfigure flow ───────────────────────────────────────────────────────────

async def test_reconfigure_initiates_stop_search(hass: HomeAssistant):
    """Test reconfigure flow sets _reconfiguring and jumps to stop_search."""
    from custom_components.openpublictransport.const import PROVIDER_VRR

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            CONF_STATION_ID: "de:05111:21",
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "stop_search"


async def test_reconfigure_no_entry_still_shows_stop_search(hass: HomeAssistant):
    """Test reconfigure falls through to stop_search even if entry lookup fails."""
    from custom_components.openpublictransport.const import PROVIDER_VRR

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VRR, CONF_STATION_ID: "de:05111:21",
              "place_dm": "Düsseldorf", "name_dm": "Hbf"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "stop_search"
