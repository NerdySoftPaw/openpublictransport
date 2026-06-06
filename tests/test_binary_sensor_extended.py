"""Extended tests for binary_sensor.py — covering uncovered branches."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from openpublictransport.models import UnifiedDeparture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.binary_sensor import (
    PublicTransportDelayBinarySensor,
    async_setup_entry,
)
from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_VRR,
)


def _make_coordinator():
    coordinator = MagicMock()
    coordinator.data = {"stopEvents": []}
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = "12345"
    coordinator.agency_name = ""
    provider_instance = MagicMock()
    provider_instance.get_timezone.return_value = "Europe/Berlin"
    provider_instance.parse_departure.return_value = None
    coordinator.provider_instance = provider_instance
    return coordinator


def _make_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_STATION_ID: "12345",
            CONF_DEPARTURES: 10,
            CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
            CONF_SCAN_INTERVAL: 60,
        },
    )


async def test_async_setup_entry(hass: HomeAssistant):
    """Test setup creates entity."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 1
    assert isinstance(added[0], PublicTransportDelayBinarySensor)


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test setup does nothing when coordinator is missing."""
    entry = _make_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


def test_available_reflects_coordinator(hass: HomeAssistant):
    """Test available property follows coordinator success."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram", "bus"])
    assert sensor.available is True
    coordinator.last_update_success = False
    assert sensor.available is False


def test_icon_no_delay():
    """Test icon is check-circle when no delays."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor._attr_is_on = False
    assert sensor.icon == "mdi:check-circle"


def test_icon_with_delay():
    """Test icon is alert-circle when delays present."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor._attr_is_on = True
    assert sensor.icon == "mdi:alert-circle"


def test_extra_state_attributes():
    """Test extra_state_attributes returns _attributes dict."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor._attributes = {"delayed_departures": 2}
    assert sensor.extra_state_attributes == {"delayed_departures": 2}


def test_handle_coordinator_update_no_data(hass: HomeAssistant):
    """Test update with no data doesn't crash."""
    coordinator = _make_coordinator()
    coordinator.data = None
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    sensor.async_write_ha_state.assert_called_once()


def test_process_delay_data_with_parsed_departures(hass: HomeAssistant):
    """Test _process_delay_data uses parsed departures when available via hass.data."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    # Simulate parsed departures already available via hass entity_components
    mock_sensor_entity = MagicMock()
    mock_sensor_entity.coordinator = coordinator
    mock_sensor_entity._attributes = {
        "departures": [
            {"delay": 10, "line": "U79"},
            {"delay": 0, "line": "Bus 1"},
        ]
    }
    mock_sensor_components = MagicMock()
    mock_sensor_components.entities = [mock_sensor_entity]
    hass.data["entity_components"] = {"sensor": mock_sensor_components}

    sensor._process_delay_data({"stopEvents": []})

    assert sensor._attr_is_on is True
    assert sensor._attributes["delayed_departures"] == 1
    assert sensor._attributes["on_time_departures"] == 1
    assert sensor._attributes["max_delay"] == 10


def test_process_delay_data_all_on_time(hass: HomeAssistant):
    """Test _process_delay_data with all on-time departures."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    mock_sensor_entity = MagicMock()
    mock_sensor_entity.coordinator = coordinator
    mock_sensor_entity._attributes = {
        "departures": [
            {"delay": 0, "line": "U79"},
            {"delay": 0, "line": "Bus 1"},
        ]
    }
    mock_sensor_components = MagicMock()
    mock_sensor_components.entities = [mock_sensor_entity]
    hass.data["entity_components"] = {"sensor": mock_sensor_components}

    sensor._process_delay_data({"stopEvents": []})

    assert sensor._attr_is_on is False


def test_process_delay_data_fallback_with_provider(hass: HomeAssistant):
    """Test _process_delay_data falls back to provider parsing."""
    coordinator = _make_coordinator()
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    dep = UnifiedDeparture(
        line="U79", destination="X", departure_time="10:05",
        planned_time="10:00", delay=10, platform="2",
        transportation_type="tram", is_realtime=True,
        minutes_until_departure=5, departure_time_obj=now,
    )
    coordinator.provider_instance.parse_departure.return_value = dep
    coordinator.data = {"stopEvents": [{"raw": "data"}]}
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    sensor._process_delay_data(coordinator.data)

    assert sensor._attr_is_on is True


def test_process_delay_data_empty_stop_events(hass: HomeAssistant):
    """Test _process_delay_data with empty stop events."""
    coordinator = _make_coordinator()
    coordinator.data = {"stopEvents": []}
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    sensor._process_delay_data({"stopEvents": []})
    assert sensor._attr_is_on is False


def test_process_delay_data_with_non_dict_departure(hass: HomeAssistant):
    """Test _process_delay_data skips non-dict items in parsed departures."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    sensor = PublicTransportDelayBinarySensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    mock_sensor_entity = MagicMock()
    mock_sensor_entity.coordinator = coordinator
    mock_sensor_entity._attributes = {"departures": ["not a dict", {"delay": 10, "line": "U79"}]}
    mock_sensor_components = MagicMock()
    mock_sensor_components.entities = [mock_sensor_entity]
    hass.data["entity_components"] = {"sensor": mock_sensor_components}

    sensor._process_delay_data({"stopEvents": []})
    assert sensor._attr_is_on is True
    assert sensor._attributes["delayed_departures"] == 1
