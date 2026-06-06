"""Tests for the calendar platform."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from openpublictransport.models import UnifiedDeparture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.calendar import (
    DepartureCalendar,
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


def _make_departure(
    line="U79",
    destination="Duisburg Hbf",
    delay=0,
    transport_type="tram",
    platform="2",
    notices=None,
    platform_changed=False,
) -> UnifiedDeparture:
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    return UnifiedDeparture(
        line=line,
        destination=destination,
        departure_time=now.strftime("%H:%M"),
        planned_time=now.strftime("%H:%M"),
        delay=delay,
        platform=platform,
        transportation_type=transport_type,
        is_realtime=True,
        minutes_until_departure=5,
        departure_time_obj=now,
        notices=notices,
        platform_changed=platform_changed,
    )


def _make_coordinator(transport_types=None):
    coordinator = MagicMock()
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


def _make_config_entry(transport_types=None):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_STATION_ID: "12345",
            CONF_DEPARTURES: 10,
            CONF_TRANSPORTATION_TYPES: transport_types or ["bus", "train", "tram"],
            CONF_SCAN_INTERVAL: 60,
        },
    )


async def test_async_setup_entry(hass: HomeAssistant):
    """Test setup adds a DepartureCalendar entity."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert isinstance(added[0], DepartureCalendar)


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test setup does nothing when coordinator is missing."""
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


def test_calendar_unique_id_and_name():
    """Test unique_id and name are set correctly."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)

    assert cal._attr_unique_id == "vrr_12345_calendar"
    assert cal._attr_name == "Schedule"


def test_calendar_unique_id_without_station_id():
    """Test unique_id when station_id is None."""
    coordinator = _make_coordinator()
    coordinator.station_id = None
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)

    assert "düsseldorf_hauptbahnhof" in cal._attr_unique_id


def test_calendar_event_property_empty():
    """Test event property returns None when no events."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)

    assert cal.event is None


def test_handle_coordinator_update_populates_events(hass: HomeAssistant):
    """Test _handle_coordinator_update populates events from coordinator data."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert len(cal._events) == 1
    assert cal._events[0].summary == "U79 → Duisburg Hbf"
    assert cal.event is not None


def test_handle_coordinator_update_no_data(hass: HomeAssistant):
    """Test _handle_coordinator_update with no coordinator data."""
    coordinator = _make_coordinator()
    coordinator.data = None
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert cal._events == []


def test_handle_coordinator_update_no_provider(hass: HomeAssistant):
    """Test _handle_coordinator_update with no provider instance."""
    coordinator = _make_coordinator()
    coordinator.provider_instance = None
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert cal._events == []


def test_handle_coordinator_update_with_delay(hass: HomeAssistant):
    """Test event description includes delay info."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(delay=5)
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert len(cal._events) == 1
    assert "Delay: +5 min" in (cal._events[0].description or "")


def test_handle_coordinator_update_with_notices(hass: HomeAssistant):
    """Test event description includes notices."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(
        notices=["Track change", "Bus replacement"]
    )
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert "Track change" in (cal._events[0].description or "")


def test_handle_coordinator_update_filters_transport_type(hass: HomeAssistant):
    """Test that wrong transport types are filtered out."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(transport_type="ferry")
    entry = _make_config_entry(transport_types=["bus", "train"])  # ferry excluded
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert cal._events == []


def test_handle_coordinator_update_skips_none_departures(hass: HomeAssistant):
    """Test that None departures are skipped."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = None
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert cal._events == []


def test_handle_coordinator_update_events_sorted(hass: HomeAssistant):
    """Test that events are sorted by start time."""
    dep1 = _make_departure(line="U79")
    dep1.departure_time_obj = datetime(2025, 1, 15, 10, 10, tzinfo=timezone.utc)
    dep2 = _make_departure(line="721")
    dep2.departure_time_obj = datetime(2025, 1, 15, 10, 5, tzinfo=timezone.utc)

    coordinator = _make_coordinator()
    coordinator.data = {"stopEvents": [{}, {}]}
    coordinator.provider_instance.parse_departure.side_effect = [dep1, dep2]
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass

    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    assert len(cal._events) == 2
    assert cal._events[0].summary == "721 → Duisburg Hbf"
    assert cal._events[1].summary == "U79 → Duisburg Hbf"


async def test_async_get_events_filters_by_date_range(hass: HomeAssistant):
    """Test async_get_events returns only events in range."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)
    cal.hass = hass
    cal.async_write_ha_state = MagicMock()
    cal._handle_coordinator_update()

    start = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
    end = datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc)
    events = await cal.async_get_events(hass, start, end)
    assert len(events) == 1

    start_future = datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc)
    end_future = datetime(2025, 1, 16, 1, 0, tzinfo=timezone.utc)
    events_empty = await cal.async_get_events(hass, start_future, end_future)
    assert events_empty == []


def test_calendar_with_agency_name(hass: HomeAssistant):
    """Test device_info uses agency_name when set."""
    coordinator = _make_coordinator()
    coordinator.agency_name = "VRR"
    entry = _make_config_entry()
    cal = DepartureCalendar(coordinator, entry)

    assert cal._attr_device_info is not None
