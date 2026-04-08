"""Tests for OpenPublicTransport binary sensor platform."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.binary_sensor import PublicTransportDelayBinarySensor, async_setup_entry
from custom_components.openpublictransport.const import DOMAIN, PROVIDER_VRR


async def test_binary_sensor_no_delays(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test binary sensor with no delays."""
    # Create coordinator with on-time departures
    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:00:00Z",
            }
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None

    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    binary_sensor = PublicTransportDelayBinarySensor(
        coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Call _process_delay_data directly to avoid needing hass
    binary_sensor._process_delay_data(coordinator.data)

    # Should be OFF (no problem) when on time
    assert binary_sensor._attr_is_on is False
    assert binary_sensor._attributes["max_delay"] == 0
    assert binary_sensor._attributes["on_time_departures"] == 1


async def test_binary_sensor_with_delays(hass: HomeAssistant, mock_config_entry):
    """Test binary sensor with delays."""
    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:10:00Z",  # 10 min delay
            },
            {
                "departureTimePlanned": "2025-01-15T10:05:00Z",
                "departureTimeEstimated": "2025-01-15T10:07:00Z",  # 2 min delay
            },
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None

    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    binary_sensor = PublicTransportDelayBinarySensor(
        coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Call _process_delay_data directly to avoid needing hass
    binary_sensor._process_delay_data(coordinator.data)

    # Should be ON (problem) when delays > 5 minutes
    assert binary_sensor._attr_is_on is True
    assert binary_sensor._attributes["max_delay"] == 10
    assert binary_sensor._attributes["delayed_departures"] == 2
    assert binary_sensor._attributes["average_delay"] == 6.0


async def test_binary_sensor_delay_threshold(hass: HomeAssistant, mock_config_entry):
    """Test binary sensor delay threshold (5 minutes)."""
    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:04:00Z",  # 4 min delay
            }
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None

    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    binary_sensor = PublicTransportDelayBinarySensor(
        coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Call _process_delay_data directly to avoid needing hass
    binary_sensor._process_delay_data(coordinator.data)

    # Should be OFF when delay <= 5 minutes
    assert binary_sensor._attr_is_on is False
    assert binary_sensor._attributes["max_delay"] == 4


async def test_binary_sensor_icon(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test binary sensor icon changes based on state."""
    binary_sensor = PublicTransportDelayBinarySensor(
        mock_coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # No delay - check icon
    binary_sensor._attr_is_on = False
    assert binary_sensor.icon == "mdi:check-circle"

    # With delay - alert icon
    binary_sensor._attr_is_on = True
    assert binary_sensor.icon == "mdi:alert-circle"


async def test_binary_sensor_no_departures(hass: HomeAssistant, mock_config_entry):
    """Test binary sensor with no departures."""
    coordinator = MagicMock()
    coordinator.data = {"stopEvents": []}
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None

    # Test with provider instance
    from custom_components.openpublictransport.providers import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    binary_sensor = PublicTransportDelayBinarySensor(
        coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Call _process_delay_data directly to avoid needing hass
    binary_sensor._process_delay_data(coordinator.data)

    assert binary_sensor._attr_is_on is False
    assert binary_sensor._attributes["total_departures"] == 0


async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """Test binary sensor platform setup."""
    # mock_config_entry already added to hass in fixture

    # Store coordinator in hass.data
    hass.data[DOMAIN] = {f"{mock_config_entry.entry_id}_coordinator": mock_coordinator}

    entities = []

    def mock_add_entities(new_entities):
        """Mock add entities - synchronous callback."""
        entities.extend(new_entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert len(entities) == 1
    assert isinstance(entities[0], PublicTransportDelayBinarySensor)
