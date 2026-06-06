"""Tests for the camera platform."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from openpublictransport.models import UnifiedDeparture
from pytest_homeassistant_custom_component.common import MockConfigEntry

try:
    from custom_components.openpublictransport.camera import (
        DepartureBoardCamera,
        _get_font,
        async_setup_entry,
        render_departure_board,
    )
except ImportError:
    pytest.skip("camera platform requires turbojpeg", allow_module_level=True)
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
    is_realtime=True,
) -> UnifiedDeparture:
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    dep = UnifiedDeparture(
        line=line,
        destination=destination,
        departure_time=now.strftime("%H:%M"),
        planned_time=now.strftime("%H:%M"),
        delay=delay,
        platform=platform,
        transportation_type=transport_type,
        is_realtime=is_realtime,
        minutes_until_departure=5,
        departure_time_obj=now,
    )
    return dep


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
    """Test setup adds a DepartureBoardCamera entity."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert isinstance(added[0], DepartureBoardCamera)


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test setup does nothing when coordinator is missing."""
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


def test_camera_init():
    """Test camera unique_id, name, and is_streaming."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)

    assert cam._attr_unique_id == "vrr_12345_board"
    assert cam._attr_translation_key == "board"
    assert cam._attr_is_streaming is False
    assert cam._image is None


def test_camera_init_without_station_id():
    """Test camera unique_id when station_id is None."""
    coordinator = _make_coordinator()
    coordinator.station_id = None
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)

    assert "düsseldorf_hauptbahnhof" in cam._attr_unique_id


def test_camera_station_name_with_place():
    """Test station name includes place_dm."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)

    assert "Düsseldorf" in cam._station_name
    assert "Hauptbahnhof" in cam._station_name


def test_camera_station_name_without_place():
    """Test station name when place_dm is empty."""
    coordinator = _make_coordinator()
    coordinator.place_dm = ""
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)

    assert cam._station_name == "Hauptbahnhof"


async def test_async_camera_image_returns_none_initially(hass: HomeAssistant):
    """Test camera image is None before first update."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass

    result = await cam.async_camera_image()
    assert result is None


def test_handle_coordinator_update_renders_image(hass: HomeAssistant):
    """Test that coordinator update renders a PNG image."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass

    cam.async_write_ha_state = MagicMock()
    cam._handle_coordinator_update()

    assert cam._image is not None
    assert cam._image[:4] == b"\x89PNG"  # PNG magic bytes


def test_handle_coordinator_update_no_data(hass: HomeAssistant):
    """Test that no data renders empty board."""
    coordinator = _make_coordinator()
    coordinator.data = None
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass

    cam.async_write_ha_state = MagicMock()
    cam._handle_coordinator_update()

    assert cam._image is not None
    assert cam._image[:4] == b"\x89PNG"


def test_handle_coordinator_update_no_provider(hass: HomeAssistant):
    """Test that no provider renders empty board."""
    coordinator = _make_coordinator()
    coordinator.provider_instance = None
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass

    cam.async_write_ha_state = MagicMock()
    cam._handle_coordinator_update()

    assert cam._image is not None
    assert cam._image[:4] == b"\x89PNG"


def test_handle_coordinator_update_filters_transport_type(hass: HomeAssistant):
    """Test that wrong transport types are filtered."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(transport_type="ferry")
    entry = _make_config_entry(transport_types=["bus", "train"])
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass

    cam.async_write_ha_state = MagicMock()
    cam._handle_coordinator_update()
    assert cam._image is not None  # Still renders, just empty board


def test_handle_coordinator_update_skips_none_departure(hass: HomeAssistant):
    """Test that None departures are skipped."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = None
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass

    cam.async_write_ha_state = MagicMock()
    cam._handle_coordinator_update()
    assert cam._image is not None


async def test_async_camera_image_returns_rendered_image(hass: HomeAssistant):
    """Test camera image after update."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)
    cam.hass = hass
    cam.async_write_ha_state = MagicMock()
    cam._handle_coordinator_update()

    result = await cam.async_camera_image()
    assert result is not None
    assert result[:4] == b"\x89PNG"


def test_render_departure_board_empty():
    """Test rendering empty departure board."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    result = render_departure_board("Test Station", [], now)

    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_render_departure_board_with_departures():
    """Test rendering board with departures."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    departures = [
        {
            "line": "U79",
            "destination": "Duisburg Hbf",
            "departure_time": "10:05",
            "planned_time": "10:00",
            "delay": 5,
            "platform": "2",
            "is_realtime": True,
        }
    ]
    result = render_departure_board("Düsseldorf Hbf", departures, now)

    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_render_departure_board_with_realtime_on_time():
    """Test rendering board with realtime on-time departure."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    departures = [
        {
            "line": "S1",
            "destination": "Airport",
            "departure_time": "10:00",
            "planned_time": "10:00",
            "delay": 0,
            "platform": "3",
            "is_realtime": True,
        }
    ]
    result = render_departure_board("Station", departures, now)
    assert result[:4] == b"\x89PNG"


def test_render_departure_board_max_rows():
    """Test that more than MAX_ROWS departures are truncated."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    departures = [
        {"line": f"L{i}", "destination": "X", "departure_time": "10:00",
         "planned_time": "10:00", "delay": 0, "platform": "", "is_realtime": False}
        for i in range(15)
    ]
    result = render_departure_board("Station", departures, now)
    assert result[:4] == b"\x89PNG"


def test_render_departure_board_long_destination():
    """Test that long destination names are truncated."""
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    departures = [
        {
            "line": "Bus",
            "destination": "A" * 50,
            "departure_time": "10:00",
            "planned_time": "10:00",
            "delay": 0,
            "platform": "",
            "is_realtime": False,
        }
    ]
    result = render_departure_board("Station", departures, now)
    assert result[:4] == b"\x89PNG"


def test_get_font_returns_font():
    """Test _get_font returns a usable font object."""
    font = _get_font(18)
    assert font is not None


def test_camera_with_agency_name():
    """Test device_info uses agency_name when set."""
    coordinator = _make_coordinator()
    coordinator.agency_name = "VRR"
    entry = _make_config_entry()
    cam = DepartureBoardCamera(coordinator, entry)

    assert cam._attr_device_info is not None
