"""Additional sensor.py coverage tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from openpublictransport.models import UnifiedDeparture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_VRR,
)
from custom_components.openpublictransport.sensor import (
    MultiProviderSensor,
    PublicTransportDataUpdateCoordinator,
)


def _make_departure(line="U79", delay=0, transport_type="tram", minutes=5):
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    return UnifiedDeparture(
        line=line,
        destination="Duisburg",
        departure_time="10:05",
        planned_time="10:00",
        delay=delay,
        platform="2",
        transportation_type=transport_type,
        is_realtime=True,
        minutes_until_departure=minutes,
        departure_time_obj=now,
    )


def _make_mock_coordinator(stops=None):
    coordinator = MagicMock()
    coordinator.data = {"stopEvents": stops or [{"raw": "data"}]}
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


def _make_entry(extra=None):
    data = {
        CONF_PROVIDER: PROVIDER_VRR,
        "place_dm": "Düsseldorf",
        "name_dm": "Hauptbahnhof",
        CONF_STATION_ID: "12345",
        CONF_DEPARTURES: 10,
        CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
        CONF_SCAN_INTERVAL: 60,
    }
    if extra:
        data.update(extra)
    return MockConfigEntry(domain=DOMAIN, data=data)


# ── _process_departure_data ────────────────────────────────────────────────────

def test_process_departure_data_invalid_response(hass: HomeAssistant):
    """Test _process_departure_data with non-dict returns early."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass
    sensor._process_departure_data("not a dict")
    assert sensor._state is None


def test_process_departure_data_invalid_stop_events(hass: HomeAssistant):
    """Test _process_departure_data with non-list stopEvents returns early."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass
    sensor._process_departure_data({"stopEvents": "not a list"})
    assert sensor._state is None


def test_process_departure_data_empty_stops(hass: HomeAssistant):
    """Test _process_departure_data with empty stopEvents sets 'No departures'."""
    coordinator = _make_mock_coordinator(stops=[])
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass
    sensor._process_departure_data({"stopEvents": []})
    assert sensor._state == "No departures"
    assert sensor._attributes["total_departures"] == 0


def test_process_departure_data_with_line_filter(hass: HomeAssistant):
    """Test _process_departure_data filters by line."""
    coordinator = _make_mock_coordinator()
    coordinator.data = {"stopEvents": [{}]}
    coordinator.provider_instance.parse_departure.return_value = _make_departure(line="U79")
    entry = _make_entry({CONF_LINE_FILTER: "bus 10"})
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass
    sensor._line_filter = {"bus 10"}
    sensor._process_departure_data({"stopEvents": [{}]})
    assert sensor._attributes.get("departures", []) == []


def test_process_departure_data_with_favorite_lines(hass: HomeAssistant):
    """Test _process_departure_data sorts favorites first."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    dep_u79 = UnifiedDeparture(
        line="U79", destination="X", departure_time="10:05",
        planned_time="10:00", delay=0, platform="", transportation_type="tram",
        is_realtime=True, minutes_until_departure=5,
        departure_time_obj=datetime(2025, 1, 15, 10, 5, tzinfo=timezone.utc),
    )
    dep_bus = UnifiedDeparture(
        line="Bus 10", destination="Y", departure_time="10:02",
        planned_time="10:02", delay=0, platform="", transportation_type="bus",
        is_realtime=True, minutes_until_departure=2,
        departure_time_obj=datetime(2025, 1, 15, 10, 2, tzinfo=timezone.utc),
    )
    coordinator = _make_mock_coordinator()
    coordinator.data = {"stopEvents": [{}, {}]}
    coordinator.provider_instance.parse_departure.side_effect = [dep_u79, dep_bus]
    entry = _make_entry({CONF_FAVORITE_LINES: "u79"})
    sensor = MultiProviderSensor(coordinator, entry, ["tram", "bus"])
    sensor.hass = hass
    sensor._favorite_lines = {"u79"}
    sensor._process_departure_data({"stopEvents": [{}, {}]})
    deps = sensor._attributes.get("departures", [])
    assert len(deps) >= 1
    assert deps[0]["line"] == "U79"


def test_process_departure_data_with_walking_time(hass: HomeAssistant):
    """Test _process_departure_data filters by walking time."""
    close_dep = _make_departure(minutes=1)  # 1 min — below walking time
    far_dep = _make_departure(line="Bus", minutes=10)

    coordinator = _make_mock_coordinator()
    coordinator.data = {"stopEvents": [{}, {}]}
    coordinator.provider_instance.parse_departure.side_effect = [close_dep, far_dep]
    entry = _make_entry({CONF_WALKING_TIME: 5})
    sensor = MultiProviderSensor(coordinator, entry, ["tram", "bus"])
    sensor.hass = hass
    sensor._walking_time = 5
    sensor._process_departure_data({"stopEvents": [{}, {}]})
    deps = sensor._attributes.get("departures", [])
    # Only far departure should remain
    assert len(deps) == 1
    assert deps[0]["line"] == "Bus"


# ── _async_update_listener ────────────────────────────────────────────────────

async def test_async_update_listener_updates_settings(hass: HomeAssistant):
    """Test _async_update_listener updates sensor settings from options."""
    coordinator = _make_mock_coordinator()
    coordinator.async_request_refresh = AsyncMock()
    entry = _make_entry()
    entry.add_to_hass(hass)
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    # Create a mock options entry
    new_entry = MagicMock()
    new_entry.options = {
        CONF_TRANSPORTATION_TYPES: ["bus", "train"],
        CONF_USE_PROVIDER_LOGO: True,
        CONF_WALKING_TIME: 3,
        CONF_FAVORITE_LINES: "U79, Bus 10",
        CONF_DEPARTURES: 15,
        CONF_SCAN_INTERVAL: 120,
    }
    new_entry.data = {}

    await sensor._async_update_listener(hass, new_entry)

    assert "bus" in sensor.transportation_types
    assert sensor._use_provider_logo is True
    assert sensor._walking_time == 3
    assert "u79" in sensor._favorite_lines
    coordinator.async_request_refresh.assert_called_once()


async def test_async_update_listener_empty_favorite_lines(hass: HomeAssistant):
    """Test _async_update_listener with empty favorite lines."""
    coordinator = _make_mock_coordinator()
    coordinator.async_request_refresh = AsyncMock()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass

    new_entry = MagicMock()
    new_entry.options = {
        CONF_TRANSPORTATION_TYPES: ["bus"],
        CONF_USE_PROVIDER_LOGO: False,
        CONF_WALKING_TIME: 0,
        CONF_FAVORITE_LINES: "",
        CONF_DEPARTURES: 10,
        CONF_SCAN_INTERVAL: 60,
    }
    new_entry.data = {}

    await sensor._async_update_listener(hass, new_entry)
    assert sensor._favorite_lines == set()
