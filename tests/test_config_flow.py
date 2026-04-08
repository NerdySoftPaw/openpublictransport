"""Tests for OpenPublicTransport config flow with simplified 2-step flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_VRR,
)


@pytest.fixture
def mock_stopfinder_stops():
    """Mock stopfinder response for stops."""
    return [
        {
            "id": "de:05111:5650",
            "name": "Hauptbahnhof",
            "type": "stop",
            "place": "Düsseldorf",
        },
        {
            "id": "de:05111:5651",
            "name": "Stadtmitte",
            "type": "stop",
            "place": "Düsseldorf",
        },
    ]


async def test_user_step_provider_selection(hass: HomeAssistant):
    """Test initial step - provider selection."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_full_flow_simplified(hass: HomeAssistant):
    """Test complete simplified 2-step flow with single stop result."""
    # Mock async_setup_entry to prevent actual integration setup which leaves lingering threads
    # The patch must be in place before the config entry is created
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ):
        # Step 1: Select provider
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        # Step 2: Select provider
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PROVIDER: PROVIDER_VRR},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "stop_search"

        # Step 3: Search for stop - return single result to go directly to settings
        with (
            patch(
                "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
                return_value=[
                    {
                        "id": "de:05111:5650",
                        "name": "Hauptbahnhof",
                        "type": "stop",
                        "place": "Düsseldorf",
                    }
                ],
            ),
            patch(
                "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
            ),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"stop_search": "Hauptbahnhof"},
            )

            # Should show settings form (single result auto-selected)
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "settings"

            # Step 4: Configure settings and complete
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    CONF_DEPARTURES: 10,
                    CONF_TRANSPORTATION_TYPES: ["bus", "train"],
                    CONF_SCAN_INTERVAL: 60,
                },
            )

            # Should create entry
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert "Düsseldorf" in result["title"]
            assert "Hauptbahnhof" in result["title"]
            assert result["data"][CONF_PROVIDER] == PROVIDER_VRR
            assert result["data"]["place_dm"] == "Düsseldorf"
            assert result["data"]["name_dm"] == "Hauptbahnhof"


async def test_stop_select_with_multiple_results(hass: HomeAssistant, mock_stopfinder_stops):
    """Test stop selection when multiple results are returned."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    # Select provider
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PROVIDER: PROVIDER_VRR},
    )

    # Search with multiple results
    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=mock_stopfinder_stops,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"stop_search": "Düsseldorf"},
        )

        # Should show stop selection form
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "stop_select"


async def test_stop_search_no_results(hass: HomeAssistant):
    """Test stop search when no results are returned."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    # Select provider
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PROVIDER: PROVIDER_VRR},
    )

    # Search with no results
    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"stop_search": "NonexistentStation"},
        )

        # Should show error
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "stop_search"
        assert "errors" in result
        assert result["errors"]["stop_search"] == "no_results"


async def test_empty_stop_search(hass: HomeAssistant):
    """Test empty stop search."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    # Select provider
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PROVIDER: PROVIDER_VRR},
    )

    # Try to submit empty search
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"stop_search": ""},
    )

    # Should show error
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "stop_search"
    assert "errors" in result
    assert result["errors"]["stop_search"] == "empty_search"


async def test_options_flow(hass: HomeAssistant, mock_config_entry):
    """Test options flow."""
    # mock_config_entry already added to hass in fixture

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEPARTURES: 15,
            CONF_TRANSPORTATION_TYPES: ["train", "tram"],
            CONF_SCAN_INTERVAL: 120,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEPARTURES] == 15
    assert result["data"][CONF_SCAN_INTERVAL] == 120


def test_parse_stopfinder_response():
    """Test parsing stopfinder API response."""
    from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow

    flow = OpenPublicTransportConfigFlow()
    flow._provider = PROVIDER_VRR

    # Test with valid data
    data = {
        "locations": [
            {
                "id": "de:05111:5650",
                "name": "Hauptbahnhof",
                "type": "stop",
                "parent": {"name": "Düsseldorf"},
            }
        ]
    }

    result = flow._parse_stopfinder_response(data, search_type="stop", search_term="Hauptbahnhof")

    assert len(result) == 1
    assert result[0]["id"] == "de:05111:5650"
    assert result[0]["name"] == "Hauptbahnhof"
    assert result[0]["place"] == "Düsseldorf"
