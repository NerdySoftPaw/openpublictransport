"""Tests for the statistics platform."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from openpublictransport.models import UnifiedDeparture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_VRR,
)
from custom_components.openpublictransport.statistics import (
    PunctualitySensor,
    async_setup_entry,
)


def _make_departure(line="U79", delay=0) -> UnifiedDeparture:
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    return UnifiedDeparture(
        line=line,
        destination="Duisburg Hbf",
        departure_time="10:00",
        planned_time="10:00",
        delay=delay,
        platform="2",
        transportation_type="tram",
        is_realtime=True,
        minutes_until_departure=5,
        departure_time_obj=now,
    )


def _make_coordinator():
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.hass.async_create_task = MagicMock()
    coordinator.data = {"stopEvents": [{"raw": "data"}]}
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = "12345"
    coordinator.agency_name = ""
    provider_instance = MagicMock()
    provider_instance.get_timezone.return_value = "Europe/Berlin"
    provider_instance.parse_departure.return_value = _make_departure()
    coordinator.provider_instance = provider_instance
    return coordinator


def _make_config_entry(is_trip=False):
    data = {
        CONF_PROVIDER: PROVIDER_VRR,
        "place_dm": "Düsseldorf",
        "name_dm": "Hauptbahnhof",
        CONF_STATION_ID: "12345",
        CONF_DEPARTURES: 10,
        CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
        CONF_SCAN_INTERVAL: 60,
    }
    if is_trip:
        data["is_trip"] = True
    return MockConfigEntry(domain=DOMAIN, data=data)


async def test_async_setup_entry(hass: HomeAssistant):
    """Test setup adds a PunctualitySensor."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert isinstance(added[0], PunctualitySensor)


async def test_async_setup_entry_skips_trip(hass: HomeAssistant):
    """Test setup skips trip entries."""
    coordinator = _make_coordinator()
    entry = _make_config_entry(is_trip=True)
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test setup does nothing when coordinator is missing."""
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


def test_sensor_init():
    """Test unique_id, name, unit."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)

    assert sensor._attr_unique_id == "vrr_12345_statistics"
    assert sensor._attr_name == "Punctuality"
    assert sensor._attr_native_unit_of_measurement == "%"


def test_native_value_no_data():
    """Test native_value is None when no departures tracked."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)

    assert sensor.native_value is None


def test_native_value_all_on_time():
    """Test 100% punctuality."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor._total_departures = 10
    sensor._on_time_departures = 10

    assert sensor.native_value == 100.0


def test_native_value_half_on_time():
    """Test 50% punctuality."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor._total_departures = 10
    sensor._on_time_departures = 5

    assert sensor.native_value == 50.0


def test_extra_state_attributes_empty():
    """Test attributes when no data tracked."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)

    attrs = sensor.extra_state_attributes
    assert attrs["total_tracked"] == 0
    assert attrs["on_time_tracked"] == 0
    assert attrs["lines"] == {}


def test_handle_coordinator_update_tracks_departure(hass: HomeAssistant):
    """Test that a departure is tracked."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()

    assert sensor._total_departures == 1
    assert sensor._on_time_departures == 1  # delay=0 is on time
    assert "U79" in sensor._line_stats


def test_handle_coordinator_update_tracks_delayed(hass: HomeAssistant):
    """Test that a delayed departure is tracked correctly."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(delay=10)
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()

    assert sensor._total_departures == 1
    assert sensor._on_time_departures == 0
    assert sensor._line_stats["U79"]["total_delay"] == 10


def test_handle_coordinator_update_deduplicates(hass: HomeAssistant):
    """Test that the same departure is not counted twice."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()

    assert sensor._total_departures == 1


def test_handle_coordinator_update_no_data(hass: HomeAssistant):
    """Test that no data does not crash."""
    coordinator = _make_coordinator()
    coordinator.data = None
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    assert sensor._total_departures == 0


def test_handle_coordinator_update_no_provider(hass: HomeAssistant):
    """Test that missing provider does not crash."""
    coordinator = _make_coordinator()
    coordinator.provider_instance = None
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    assert sensor._total_departures == 0


def test_handle_coordinator_update_skips_none_departure(hass: HomeAssistant):
    """Test that None departure is skipped."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = None
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    assert sensor._total_departures == 0


def test_extra_state_attributes_with_data(hass: HomeAssistant):
    """Test attributes after tracking some departures."""
    coordinator = _make_coordinator()
    coordinator.data = {"stopEvents": [{}, {}]}
    dep1 = _make_departure(line="U79", delay=0)
    dep2 = _make_departure(line="U79", delay=5)
    dep2.planned_time = "10:05"  # different key
    coordinator.provider_instance.parse_departure.side_effect = [dep1, dep2]
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()

    attrs = sensor.extra_state_attributes
    assert attrs["total_tracked"] == 2
    assert "U79" in attrs["lines"]
    assert attrs["lines"]["U79"]["total"] == 2


async def test_async_added_to_hass_loads_stored_data(hass: HomeAssistant):
    """Test that stored data is loaded on startup."""
    coordinator = _make_coordinator()
    coordinator.hass = hass
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    stored_data = {
        "total": 50,
        "on_time": 45,
        "lines": {"U79": {"total": 50, "on_time": 45, "total_delay": 100}},
        "seen": ["U79_Duisburg Hbf_10:00"],
    }

    with patch.object(sensor._store, "async_load", new=AsyncMock(return_value=stored_data)):
        with patch.object(sensor, "async_write_ha_state"):
            await sensor.async_added_to_hass()

    assert sensor._total_departures == 50
    assert sensor._on_time_departures == 45
    assert "U79" in sensor._line_stats


async def test_async_added_to_hass_no_stored_data(hass: HomeAssistant):
    """Test that missing stored data is handled gracefully."""
    coordinator = _make_coordinator()
    coordinator.hass = hass
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    with patch.object(sensor._store, "async_load", new=AsyncMock(return_value=None)):
        with patch.object(sensor, "async_write_ha_state"):
            await sensor.async_added_to_hass()

    assert sensor._total_departures == 0


def test_seen_departures_pruning(hass: HomeAssistant):
    """Test that seen departures set is pruned when too large."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass
    sensor._seen_departures = {f"key_{i}" for i in range(501)}

    dep = _make_departure(line="NEW", delay=0)
    coordinator.provider_instance.parse_departure.return_value = dep
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()

    assert len(sensor._seen_departures) <= 251


def test_delay_within_threshold_is_on_time(hass: HomeAssistant):
    """Test that delay <= 2 min is counted as on time."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(delay=2)
    entry = _make_config_entry()
    sensor = PunctualitySensor(coordinator, entry)
    sensor.hass = hass

    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()

    assert sensor._on_time_departures == 1
