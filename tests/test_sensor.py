"""Tests for OpenPublicTransport sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.openpublictransport.const import API_RATE_LIMIT_PER_DAY, DOMAIN, PROVIDER_VRR
from custom_components.openpublictransport.sensor import (
    MultiProviderSensor,
    PublicTransportDataUpdateCoordinator,
    async_setup_entry,
)


async def test_coordinator_update(hass: HomeAssistant, mock_api_response):
    """Test coordinator data update."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
    )

    with patch.object(coordinator, "_fetch_departures", return_value=mock_api_response):
        await coordinator.async_refresh()

        assert coordinator.data == mock_api_response
        assert coordinator.last_update_success is True


async def test_coordinator_rate_limit(hass: HomeAssistant):
    """Test rate limiting in coordinator."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
    )

    # Simulate hitting rate limit
    coordinator._api_calls_today = API_RATE_LIMIT_PER_DAY

    with patch.object(coordinator, "_fetch_departures") as mock_fetch:
        # Should not call API when rate limited
        assert coordinator._check_rate_limit() is False

        # With existing data, should return it
        coordinator.data = {"stopEvents": []}
        result = await coordinator._async_update_data()
        assert result == {"stopEvents": []}
        mock_fetch.assert_not_called()


async def test_coordinator_api_error(hass: HomeAssistant):
    """Test coordinator handling API errors."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
    )

    with patch.object(coordinator, "_fetch_departures", side_effect=Exception("API Error")):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_sensor_state(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test sensor state updates."""
    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    mock_coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)
    sensor = MultiProviderSensor(
        mock_coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Mock datetime to have consistent time
    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2025-01-15T09:55:00Z")

        # Call _process_departure_data directly instead of _handle_coordinator_update
        # to avoid needing hass to be set
        sensor._process_departure_data(mock_coordinator.data)

        # Verify state is set to next departure time
        assert sensor._state is not None
        assert isinstance(sensor._attributes, dict)
        assert "departures" in sensor._attributes
        assert "total_departures" in sensor._attributes


async def test_sensor_icon(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test sensor icon changes based on transport type."""
    sensor = MultiProviderSensor(
        mock_coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Set attributes with different transportation types
    sensor._attributes = {
        "departures": [
            {"transportation_type": "bus", "line": "721"},
            {"transportation_type": "train", "line": "RE1"},
        ]
    }

    # Icon should reflect first departure type
    icon = sensor.icon
    assert icon == "mdi:bus-clock"

    # Change first departure to train
    sensor._attributes["departures"][0]["transportation_type"] = "train"
    icon = sensor.icon
    assert icon == "mdi:train"


async def test_sensor_no_departures(hass: HomeAssistant, mock_config_entry):
    """Test sensor with no departures."""
    coordinator = MagicMock()
    coordinator.data = {"stopEvents": []}
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None
    coordinator.departures_limit = 10

    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    sensor = MultiProviderSensor(
        coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Call _process_departure_data directly to avoid needing hass
    sensor._process_departure_data(coordinator.data)

    assert sensor._state == "No departures"
    assert sensor._attributes["total_departures"] == 0
    assert sensor._attributes["departures"] == []


async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_api_response):
    """Test sensor platform setup."""
    # mock_config_entry already added to hass in fixture

    # Initialize hass.data[DOMAIN] as __init__.py would do
    hass.data.setdefault(DOMAIN, {})

    with (
        patch(
            "custom_components.openpublictransport.sensor.PublicTransportDataUpdateCoordinator._fetch_departures",
            return_value=mock_api_response,
        ),
        patch(
            "custom_components.openpublictransport.sensor.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        ),
    ):
        entities = []

        def mock_add_entities(new_entities):
            """Mock add entities - synchronous callback."""
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        assert len(entities) == 1
        assert isinstance(entities[0], MultiProviderSensor)


async def test_sensor_transportation_type_filtering(hass: HomeAssistant, mock_config_entry):
    """Test filtering departures by transportation type."""
    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:00:00Z",
                "transportation": {
                    "number": "U79",
                    "destination": {"name": "Duisburg"},
                    "description": "Tram",
                    "product": {"class": 4, "name": "Tram"},
                },
                "platform": {"name": "2"},
                "realtimeStatus": ["MONITORED"],
            },
            {
                "departureTimePlanned": "2025-01-15T10:05:00Z",
                "departureTimeEstimated": "2025-01-15T10:05:00Z",
                "transportation": {
                    "number": "721",
                    "destination": {"name": "Krefeld"},
                    "description": "Bus",
                    "product": {"class": 5, "name": "Bus"},
                },
                "platform": {"name": "5"},
                "realtimeStatus": ["MONITORED"],
            },
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None
    coordinator.departures_limit = 10

    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    # Only allow trams
    sensor = MultiProviderSensor(coordinator, mock_config_entry, ["tram"])

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2025-01-15T09:55:00Z")
        # Call _process_departure_data directly to avoid needing hass
        sensor._process_departure_data(coordinator.data)

    # Should only have tram departures
    departures = sensor._attributes.get("departures", [])
    assert len(departures) == 1
    assert departures[0]["transportation_type"] == "tram"
