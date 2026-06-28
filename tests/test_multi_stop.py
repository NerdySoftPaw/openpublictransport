"""Tests for multi_stop.py."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import DOMAIN
from custom_components.openpublictransport.multi_stop import (
    CONF_IS_MULTI_STOP,
    CONF_MULTI_STOP_NAME,
    CONF_SOURCE_ENTITIES,
    MultiStopSensor,
    async_setup_entry,
)


def _make_entry(is_multi_stop=True, source_entities=None, name="Multi-Stop"):
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_multi_stop_id",
        data={
            CONF_IS_MULTI_STOP: is_multi_stop,
            CONF_SOURCE_ENTITIES: source_entities if source_entities is not None else ["sensor.vrr_stop1", "sensor.vrr_stop2"],
            CONF_MULTI_STOP_NAME: name,
        },
    )


async def test_async_setup_entry_creates_sensor(hass: HomeAssistant):
    """Test that setup creates a MultiStopSensor."""
    entry = _make_entry()
    entry.add_to_hass(hass)
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 1
    assert isinstance(added[0], MultiStopSensor)


async def test_async_setup_entry_skips_non_multi_stop(hass: HomeAssistant):
    """Test that non-multi-stop entries are skipped."""
    entry = _make_entry(is_multi_stop=False)
    entry.add_to_hass(hass)
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


async def test_async_setup_entry_skips_empty_sources(hass: HomeAssistant):
    """Test that empty source_entities list is skipped."""
    entry = _make_entry(source_entities=[])
    entry.add_to_hass(hass)
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


def test_multi_stop_sensor_init(hass: HomeAssistant):
    """Test MultiStopSensor unique_id and device_info."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1", "sensor.s2"], "My Stops")
    assert sensor._attr_unique_id == "multi_stop_test_multi_stop_id"
    assert sensor._attr_device_info is not None


def test_update_from_sources_no_states(hass: HomeAssistant):
    """Test _update_from_sources with no states returns empty list."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1"], "Test")
    sensor._update_from_sources()
    assert sensor._departures == []


def test_update_from_sources_merges_departures(hass: HomeAssistant):
    """Test that departures from multiple sources are merged and sorted."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1", "sensor.s2"], "Test")

    hass.states.async_set("sensor.s1", "10:05", {
        "departures": [{"minutes_until_departure": 5, "line": "U79"}],
        "station_name": "Stop A",
    })
    hass.states.async_set("sensor.s2", "10:02", {
        "departures": [{"minutes_until_departure": 2, "line": "Bus 10"}],
        "station_name": "Stop B",
    })

    sensor._update_from_sources()

    assert len(sensor._departures) == 2
    assert sensor._departures[0]["line"] == "Bus 10"  # sorted by minutes
    assert sensor._departures[0]["source_station"] == "Stop B"
    assert sensor._departures[1]["line"] == "U79"


def test_native_value_no_departures(hass: HomeAssistant):
    """Test native_value returns 'No departures' when empty."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1"], "Test")
    sensor._departures = []
    assert sensor.native_value == "No departures"


def test_native_value_with_departure(hass: HomeAssistant):
    """Test native_value returns next departure time."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1"], "Test")
    sensor._departures = [{"departure_time": "10:05", "minutes_until_departure": 5}]
    assert sensor.native_value == "10:05"


def test_extra_state_attributes_no_departures_attr(hass: HomeAssistant):
    """Test extra_state_attributes when _departures not yet set."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1"], "Test")
    attrs = sensor.extra_state_attributes
    assert attrs == {}


def test_extra_state_attributes_with_data(hass: HomeAssistant):
    """Test extra_state_attributes returns correct structure."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1", "sensor.s2"], "Test")
    sensor._departures = [
        {"departure_time": "10:05", "minutes_until_departure": 5},
        {"departure_time": "10:10", "minutes_until_departure": 10},
    ]
    attrs = sensor.extra_state_attributes
    assert attrs["total_departures"] == 2
    assert attrs["source_count"] == 2
    assert attrs["next_departure_minutes"] == 5
    assert len(attrs["departures"]) == 2


def test_update_from_sources_skips_non_dict_departures(hass: HomeAssistant):
    """Test that non-dict items in departures list are skipped."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.s1"], "Test")
    hass.states.async_set("sensor.s1", "10:05", {
        "departures": ["not a dict", {"minutes_until_departure": 5, "line": "U79"}],
        "station_name": "Stop A",
    })
    sensor._update_from_sources()
    assert len(sensor._departures) == 1


def test_update_from_sources_missing_state(hass: HomeAssistant):
    """Test that missing state is skipped gracefully."""
    entry = _make_entry()
    sensor = MultiStopSensor(hass, entry, ["sensor.nonexistent"], "Test")
    sensor._update_from_sources()
    assert sensor._departures == []
