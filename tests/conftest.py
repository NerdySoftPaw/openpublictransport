"""Fixtures for OpenPublicTransport integration tests."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Import config_flow to ensure handlers are registered
import custom_components.openpublictransport.config_flow  # noqa: F401
from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_VRR,
)


@pytest.fixture
def mock_config_entry(hass):
    """Return a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Station",
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_STATION_ID: None,
            CONF_DEPARTURES: 10,
            CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
            CONF_SCAN_INTERVAL: 60,
        },
        unique_id="vrr_test_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_api_response():
    """Return a mock API response."""
    return {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:05:00Z",
                "transportation": {
                    "number": "U79",
                    "destination": {"name": "Duisburg Hbf"},
                    "description": "U-Bahn nach Duisburg",
                    "product": {"class": 4, "name": "Tram"},
                },
                "platform": {"name": "2"},
                "realtimeStatus": ["MONITORED"],
            },
            {
                "departureTimePlanned": "2025-01-15T10:10:00Z",
                "departureTimeEstimated": "2025-01-15T10:10:00Z",
                "transportation": {
                    "number": "721",
                    "destination": {"name": "Krefeld"},
                    "description": "Bus nach Krefeld",
                    "product": {"class": 5, "name": "Bus"},
                },
                "platform": {"name": "5"},
                "realtimeStatus": ["MONITORED"],
            },
        ]
    }


@pytest.fixture
def mock_coordinator(mock_api_response):
    """Return a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_api_response
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None
    coordinator.departures_limit = 10
    # provider_instance will be set in individual tests as needed
    return coordinator


@pytest.fixture
async def hass_with_integration(hass: HomeAssistant):
    """Set up the integration."""
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return hass


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass, enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield
