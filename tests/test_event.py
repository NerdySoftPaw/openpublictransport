"""Tests for the event platform."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

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
from custom_components.openpublictransport.event import (
    DisruptionEventEntity,
    async_setup_entry,
)


def _make_departure(
    line="U79",
    notices=None,
    platform_changed=False,
    platform="2",
    planned_platform="1",
) -> UnifiedDeparture:
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    return UnifiedDeparture(
        line=line,
        destination="Duisburg Hbf",
        departure_time="10:00",
        planned_time="10:00",
        delay=0,
        platform=platform,
        transportation_type="tram",
        is_realtime=True,
        minutes_until_departure=5,
        departure_time_obj=now,
        notices=notices,
        platform_changed=platform_changed,
        planned_platform=planned_platform if platform_changed else None,
    )


def _make_coordinator():
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


def _make_config_entry():
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
    """Test setup adds a DisruptionEventEntity."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert isinstance(added[0], DisruptionEventEntity)


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test setup does nothing when coordinator is missing."""
    entry = _make_config_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


def test_event_entity_init():
    """Test unique_id, name and event_types are set correctly."""
    coordinator = _make_coordinator()
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)

    assert entity._attr_unique_id == "vrr_12345_disruptions"
    assert entity._attr_translation_key == "disruptions"
    assert "disruption" in entity._attr_event_types
    assert "platform_change" in entity._attr_event_types
    assert "info" in entity._attr_event_types


def test_event_entity_init_without_station_id():
    """Test unique_id when station_id is None."""
    coordinator = _make_coordinator()
    coordinator.station_id = None
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)

    assert "düsseldorf_hauptbahnhof" in entity._attr_unique_id


def test_handle_coordinator_update_no_data(hass: HomeAssistant):
    """Test update does nothing when no data."""
    coordinator = _make_coordinator()
    coordinator.data = None
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()
    assert entity._previous_notices == set()


def test_handle_coordinator_update_no_provider(hass: HomeAssistant):
    """Test update does nothing when no provider instance."""
    coordinator = _make_coordinator()
    coordinator.provider_instance = None
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()
    assert entity._previous_notices == set()


def test_handle_coordinator_update_fires_new_notice(hass: HomeAssistant):
    """Test that new notices trigger events."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(
        notices=["Service disruption on line U79"]
    )
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass

    fired_events = []
    entity._trigger_event = lambda event_type, data: fired_events.append((event_type, data))

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()

    assert any(e[0] == "disruption" for e in fired_events)
    assert "Service disruption on line U79" in entity._previous_notices


def test_handle_coordinator_update_no_duplicate_notices(hass: HomeAssistant):
    """Test that known notices don't fire again."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(
        notices=["Existing notice"]
    )
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass
    entity._previous_notices = {"Existing notice"}

    fired_events = []
    entity._trigger_event = lambda event_type, data: fired_events.append((event_type, data))

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()

    assert fired_events == []


def test_handle_coordinator_update_fires_platform_change(hass: HomeAssistant):
    """Test that platform changes trigger platform_change events."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = _make_departure(
        platform_changed=True, platform="3", planned_platform="1"
    )
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass

    fired_events = []
    entity._trigger_event = lambda event_type, data: fired_events.append((event_type, data))

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()

    platform_events = [e for e in fired_events if e[0] == "platform_change"]
    assert len(platform_events) == 1
    assert platform_events[0][1]["new_platform"] == "3"
    assert platform_events[0][1]["old_platform"] == "1"


def test_handle_coordinator_update_skips_none_departure(hass: HomeAssistant):
    """Test that None departures are skipped."""
    coordinator = _make_coordinator()
    coordinator.provider_instance.parse_departure.return_value = None
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass

    fired_events = []
    entity._trigger_event = lambda event_type, data: fired_events.append((event_type, data))

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()
    assert fired_events == []


def test_handle_coordinator_update_multiple_stops(hass: HomeAssistant):
    """Test with multiple stops and different notices."""
    coordinator = _make_coordinator()
    coordinator.data = {"stopEvents": [{}, {}, {}]}
    dep1 = _make_departure(notices=["Notice A"])
    dep2 = _make_departure(notices=["Notice B"])
    dep3 = _make_departure()  # no notices
    coordinator.provider_instance.parse_departure.side_effect = [dep1, dep2, dep3]
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)
    entity.hass = hass

    fired_events = []
    entity._trigger_event = lambda event_type, data: fired_events.append((event_type, data))

    entity.async_write_ha_state = MagicMock()
    entity._handle_coordinator_update()

    assert len(fired_events) == 2
    assert {"Notice A", "Notice B"} == entity._previous_notices


def test_event_entity_with_agency_name():
    """Test device_info uses agency_name when set."""
    coordinator = _make_coordinator()
    coordinator.agency_name = "VRR"
    entry = _make_config_entry()
    entity = DisruptionEventEntity(coordinator, entry)

    assert entity._attr_device_info is not None
