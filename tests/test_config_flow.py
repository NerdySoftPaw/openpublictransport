"""Tests for OpenPublicTransport config flow with simplified 2-step flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_NTA_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_PROVIDER,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_TRAFIKLAB_API_KEY,
    CONF_TRANSPORTATION_TYPES,
    CONF_VBN_API_KEY,
    DOMAIN,
    PROVIDER_NTA_IE,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VRR,
)

_SETTINGS = {
    CONF_DEPARTURES: 10,
    CONF_TRANSPORTATION_TYPES: ["bus", "train"],
    CONF_SCAN_INTERVAL: 60,
}

_SINGLE_STOP = [{"id": "de:05111:5650", "name": "Hauptbahnhof", "type": "stop", "place": "Düsseldorf"}]
_TWO_STOPS = [
    {"id": "de:05111:5650", "name": "Hauptbahnhof", "type": "stop", "place": "Düsseldorf"},
    {"id": "de:05111:5651", "name": "Stadtmitte", "type": "stop", "place": "Düsseldorf"},
]


@pytest.fixture
def mock_stopfinder_stops():
    return _TWO_STOPS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _init_flow(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def _select_provider(hass, flow_id, provider=PROVIDER_VRR, entry_type="departures"):
    return await hass.config_entries.flow.async_configure(
        flow_id, user_input={"entry_type": entry_type, CONF_PROVIDER: provider}
    )


# ---------------------------------------------------------------------------
# Existing tests
# ---------------------------------------------------------------------------

async def test_user_step_provider_selection(hass: HomeAssistant):
    """Test initial step - provider selection."""
    result = await _init_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_full_flow_simplified(hass: HomeAssistant):
    """Test complete simplified 2-step flow with single stop result."""
    with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True):
        result = await _init_flow(hass)
        result = await _select_provider(hass, result["flow_id"])
        assert result["step_id"] == "stop_search"

        with (
            patch(
                "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
                return_value=_SINGLE_STOP,
            ),
            patch(
                "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
                new_callable=AsyncMock,
            ),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
            )
            assert result["step_id"] == "settings"

            result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_SETTINGS)
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert "Düsseldorf" in result["title"]
            assert result["data"][CONF_PROVIDER] == PROVIDER_VRR


async def test_stop_select_with_multiple_results(hass: HomeAssistant, mock_stopfinder_stops):
    """Test stop selection when multiple results are returned."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"])

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=mock_stopfinder_stops,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "stop_select"


async def test_stop_search_no_results(hass: HomeAssistant):
    """Test stop search when no results are returned."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"])

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "NonexistentStation"}
        )
        assert result["step_id"] == "stop_search"
        assert result["errors"]["stop_search"] == "no_results"


async def test_empty_stop_search(hass: HomeAssistant):
    """Test empty stop search."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"stop_search": ""}
    )
    assert result["step_id"] == "stop_search"
    assert result["errors"]["stop_search"] == "empty_search"


async def test_options_flow(hass: HomeAssistant, mock_config_entry):
    """Test options flow."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_DEPARTURES: 15, CONF_TRANSPORTATION_TYPES: ["train", "tram"], CONF_SCAN_INTERVAL: 120},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEPARTURES] == 15
    assert result["data"][CONF_SCAN_INTERVAL] == 120


async def test_api_key_provider_trip_routes_to_trip_search(hass: HomeAssistant):
    """After entering an API key with entry_type=trip, flow must go to trip_search."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_RMV, entry_type="trip")
    assert result["step_id"] == "api_key"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_RMV_API_KEY: "test-api-key-123"}
    )
    assert result["step_id"] == "trip_search"


async def test_api_key_provider_departures_routes_to_stop_search(hass: HomeAssistant):
    """After entering an API key with entry_type=departures, flow must go to stop_search."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_RMV)
    assert result["step_id"] == "api_key"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_RMV_API_KEY: "test-api-key-123"}
    )
    assert result["step_id"] == "stop_search"


def test_parse_stopfinder_response():
    """Test parsing stopfinder API response."""
    from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow

    flow = OpenPublicTransportConfigFlow()
    flow._provider = PROVIDER_VRR

    data = {
        "locations": [
            {"id": "de:05111:5650", "name": "Hauptbahnhof", "type": "stop", "parent": {"name": "Düsseldorf"}}
        ]
    }
    result = flow._parse_stopfinder_response(data, search_type="stop", search_term="Hauptbahnhof")
    assert len(result) == 1
    assert result[0]["id"] == "de:05111:5650"
    assert result[0]["name"] == "Hauptbahnhof"
    assert result[0]["place"] == "Düsseldorf"


# ---------------------------------------------------------------------------
# New tests — Task 8
# ---------------------------------------------------------------------------

async def test_stop_select_search_again(hass: HomeAssistant):
    """Selecting __search_again__ from stop_select returns to stop_search."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"])

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=_TWO_STOPS,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
        )
        assert result["step_id"] == "stop_select"

    # User requests a new search
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"stop": "__search_again__"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "stop_search"


async def test_duplicate_entry_abort(hass: HomeAssistant):
    """Creating a second entry with the same provider+station aborts as already_configured."""
    with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True):
        with (
            patch(
                "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
                return_value=_SINGLE_STOP,
            ),
            patch(
                "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
                new_callable=AsyncMock,
            ),
        ):
            # First entry
            result = await _init_flow(hass)
            result = await _select_provider(hass, result["flow_id"])
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
            )
            result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_SETTINGS)
            assert result["type"] == FlowResultType.CREATE_ENTRY

            # Second entry — same stop
            result = await _init_flow(hass)
            result = await _select_provider(hass, result["flow_id"])
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
            )
            result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_SETTINGS)
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "already_configured"


async def test_stop_search_api_error(hass: HomeAssistant):
    """When _search_stops raises an exception, show api_error."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"])

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        side_effect=Exception("network error"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
        )
        assert result["step_id"] == "stop_search"
        assert result["errors"]["stop_search"] == "api_error"


async def test_otp_custom_url_flow(hass: HomeAssistant):
    """OTP Custom provider asks for URL first, then proceeds to stop_search."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_OTP_CUSTOM)
    assert result["step_id"] == "otp_custom_url"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OTP_BASE_URL: "http://192.168.1.10:8080/otp/routers/default"}
    )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_api_key_flow(hass: HomeAssistant):
    """Trafiklab requires API key → stop_search → settings → entry created."""
    with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True):
        result = await _init_flow(hass)
        result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_TRAFIKLAB_SE)
        assert result["step_id"] == "api_key"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "tl-test-key"}
        )
        assert result["step_id"] == "stop_search"

        with (
            patch(
                "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
                return_value=_SINGLE_STOP,
            ),
            patch(
                "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
                new_callable=AsyncMock,
            ),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
            )
            assert result["step_id"] == "settings"

            result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_SETTINGS)
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_TRAFIKLAB_API_KEY] == "tl-test-key"


async def test_vbn_otp_api_key_flow(hass: HomeAssistant):
    """VBN OTP requires API key → stop_search."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_VBN_OTP)
    assert result["step_id"] == "api_key"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_VBN_API_KEY: "vbn-test-key"}
    )
    assert result["step_id"] == "stop_search"


async def test_nta_api_key_flow(hass: HomeAssistant):
    """NTA requires primary+optional secondary key, then shows manual stop ID field."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_NTA_IE)
    assert result["step_id"] == "api_key"

    # NTA has primary + secondary key fields
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-primary-key"},
    )
    # NTA skips stop search (no GTFS Static) → goes to stop_search with manual ID input
    assert result["step_id"] == "stop_search"


async def test_trip_flow_happy_path(hass: HomeAssistant):
    """Trip flow: origin search → destination search → settings → entry created."""
    result = await _init_flow(hass)
    result = await _select_provider(hass, result["flow_id"], provider=PROVIDER_VRR, entry_type="trip")
    assert result["step_id"] == "trip_search"

    origin_stop = [{"id": "de:05111:5650", "name": "Hauptbahnhof", "place": "Düsseldorf"}]
    dest_stop = [{"id": "de:05315:1001", "name": "Hbf", "place": "Köln"}]

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=origin_stop,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
        )
        assert result["step_id"] == "trip_search"

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=dest_stop,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf Köln"}
        )
        assert result["step_id"] == "trip_settings"

    # Mock both the first refresh (trip coordinator) and platform setup to avoid threads
    with (
        patch(
            "custom_components.openpublictransport.trip_sensor.TripDataUpdateCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_SCAN_INTERVAL: 120}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert "Hauptbahnhof" in result["title"]
        assert "Hbf" in result["title"]


async def test_multi_stop_flow(hass: HomeAssistant):
    """Multi-stop flow: show form → submit 2 entities → entry created."""
    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"entry_type": "multi_stop", CONF_PROVIDER: PROVIDER_VRR}
    )
    assert result["step_id"] == "multi_stop"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "My Combined Stop", "entities": "sensor.vrr_hbf, sensor.vrr_stadtmitte"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "Multi-Stop" in result["title"]


async def test_multi_stop_requires_two_entities(hass: HomeAssistant):
    """Multi-stop flow rejects less than 2 entities."""
    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"entry_type": "multi_stop", CONF_PROVIDER: PROVIDER_VRR}
    )
    assert result["step_id"] == "multi_stop"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Only One", "entities": "sensor.vrr_hbf"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["entities"] == "min_two_entities"
