"""Tests for the multi-stop departure board camera (issue #100)."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

try:
    from custom_components.openpublictransport.camera import (
        DepartureBoardCamera,
        MultiStopBoardCamera,
        async_setup_entry,
    )
except ImportError:
    pytest.skip("camera platform requires turbojpeg", allow_module_level=True)
from custom_components.openpublictransport.const import DOMAIN
from custom_components.openpublictransport.multi_stop import (
    CONF_IS_MULTI_STOP,
    CONF_MULTI_STOP_NAME,
    CONF_SOURCE_ENTITIES,
    MULTI_STOP_PLATFORMS,
    async_setup_multi_stop_entry,
)

SOURCES = ["sensor.vrr_stop1", "sensor.vrr_stop2"]


def _make_entry(source_entities=None, name="My Stops"):
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_multi_stop_id",
        title=name,
        data={
            CONF_IS_MULTI_STOP: True,
            CONF_SOURCE_ENTITIES: SOURCES if source_entities is None else source_entities,
            CONF_MULTI_STOP_NAME: name,
        },
    )


def _dep(line, minutes, time="10:05", delay=0, platform="1"):
    return {
        "line": line,
        "destination": f"Dest {line}",
        "departure_time": time,
        "planned_time": time,
        "delay": delay,
        "platform": platform,
        "is_realtime": True,
        "minutes_until_departure": minutes,
    }


def _set_sources(hass: HomeAssistant):
    hass.states.async_set(
        "sensor.vrr_stop1",
        "10:05",
        {"departures": [_dep("U79", 5)], "station_name": "Stop A"},
    )
    hass.states.async_set(
        "sensor.vrr_stop2",
        "10:02",
        {"departures": [_dep("Bus 10", 2, "10:02", delay=3)], "station_name": "Stop B"},
    )


async def test_multi_stop_forwards_camera_platform(hass: HomeAssistant):
    """The multi-stop entry forwards both sensor and camera platforms."""
    entry = _make_entry()
    entry.add_to_hass(hass)
    with patch.object(hass.config_entries, "async_forward_entry_setups") as forward:
        assert await async_setup_multi_stop_entry(hass, entry)
    forward.assert_called_once_with(entry, MULTI_STOP_PLATFORMS)
    assert "camera" in MULTI_STOP_PLATFORMS
    assert "sensor" in MULTI_STOP_PLATFORMS


async def test_setup_entry_creates_multi_stop_camera(hass: HomeAssistant):
    """The camera platform creates a MultiStopBoardCamera for multi-stop entries."""
    entry = _make_entry()
    entry.add_to_hass(hass)
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    cam = added[0]
    assert isinstance(cam, MultiStopBoardCamera)
    assert not isinstance(cam, DepartureBoardCamera)
    assert cam.unique_id == "multi_stop_test_multi_stop_id_board"
    assert cam._attr_translation_key == "board"
    assert cam._attr_is_streaming is False
    assert cam._title == "My Stops"
    assert (DOMAIN, "multi_stop_test_multi_stop_id") in cam.device_info["identifiers"]


async def test_setup_entry_multi_stop_without_sources(hass: HomeAssistant):
    """No camera is created when the multi-stop entry has no source entities."""
    entry = _make_entry(source_entities=[])
    entry.add_to_hass(hass)
    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


async def test_title_falls_back_to_entry_title(hass: HomeAssistant):
    """Without a stored multi-stop name the entry title is used."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Entry Title",
        data={CONF_IS_MULTI_STOP: True, CONF_SOURCE_ENTITIES: SOURCES},
    )
    cam = MultiStopBoardCamera(entry, SOURCES)
    assert cam._title == "Entry Title"


async def test_image_rendered_from_merged_departures(hass: HomeAssistant):
    """The image is rendered from the merged, sorted departures of all sources."""
    _set_sources(hass)
    entry = _make_entry()
    cam = MultiStopBoardCamera(entry, SOURCES)
    cam.hass = hass

    with patch(
        "custom_components.openpublictransport.camera.render_departure_board",
        return_value=b"\x89PNGfake",
    ) as render:
        cam._update_from_sources()

    title, departures, _now = render.call_args.args
    assert title == "My Stops"
    assert [d["line"] for d in departures] == ["Bus 10", "U79"]
    assert departures[0]["source_station"] == "Stop B"
    assert await cam.async_camera_image() == b"\x89PNGfake"


async def test_image_renders_real_png(hass: HomeAssistant):
    """The real renderer produces PNG bytes for merged departures and for no data."""
    entry = _make_entry()
    cam = MultiStopBoardCamera(entry, SOURCES)
    cam.hass = hass

    assert await cam.async_camera_image() is None

    cam._update_from_sources()  # no source states yet -> empty board
    empty = await cam.async_camera_image()
    assert empty[:4] == b"\x89PNG"

    _set_sources(hass)
    cam._update_from_sources()
    image = await cam.async_camera_image()
    assert image[:4] == b"\x89PNG"
    assert image != empty


async def test_camera_updates_on_source_state_change(hass: HomeAssistant):
    """Adding the camera to HA renders it and re-renders on source changes."""
    _set_sources(hass)
    entry = _make_entry()
    entry.add_to_hass(hass)
    cam = MultiStopBoardCamera(entry, SOURCES)
    cam.hass = hass
    cam.entity_id = "camera.my_stops_board"
    cam.async_write_ha_state = MagicMock()

    await cam.async_added_to_hass()
    first = await cam.async_camera_image()
    assert first[:4] == b"\x89PNG"

    hass.states.async_set(
        "sensor.vrr_stop1",
        "10:01",
        {"departures": [_dep("S1", 1, "10:01"), _dep("S2", 7, "10:07")], "station_name": "Stop A"},
    )
    await hass.async_block_till_done()

    assert cam.async_write_ha_state.called
    second = await cam.async_camera_image()
    assert second[:4] == b"\x89PNG"
    assert second != first

    await cam.async_will_remove_from_hass()


async def test_full_setup_registers_camera_entity(hass: HomeAssistant):
    """Setting up a multi-stop config entry registers sensor and (disabled) camera entities."""
    _set_sources(hass)
    entry = _make_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    camera_id = registry.async_get_entity_id("camera", DOMAIN, "multi_stop_test_multi_stop_id_board")
    sensor_id = registry.async_get_entity_id("sensor", DOMAIN, "multi_stop_test_multi_stop_id")
    assert camera_id is not None
    assert sensor_id is not None
    # Same default as the per-station board camera: user enables it on demand
    assert registry.async_get(camera_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
