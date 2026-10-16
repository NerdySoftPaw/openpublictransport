"""Multi-stop monitor for Open Public Transport integration.

Combines departures from multiple stops into a single sorted view.
Created via config flow by selecting existing departure sensors.
Provides a combined sensor and a departure board camera (see camera.py).
"""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_IS_MULTI_STOP = "is_multi_stop"
CONF_SOURCE_ENTITIES = "source_entities"
CONF_MULTI_STOP_NAME = "multi_stop_name"

# Platforms set up for a multi-stop entry (sensor + departure board camera)
MULTI_STOP_PLATFORMS = ["sensor", "camera"]


def multi_stop_name(config_entry: ConfigEntry) -> str:
    """Return the user-given name of a multi-stop entry."""
    return config_entry.data.get(CONF_MULTI_STOP_NAME) or config_entry.title or "Multi-Stop"


def multi_stop_device_info(config_entry: ConfigEntry, name: str | None = None) -> DeviceInfo:
    """Return the device info shared by all entities of a multi-stop entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"multi_stop_{config_entry.entry_id}")},
        name=name or multi_stop_name(config_entry),
        manufacturer="Open Public Transport",
        model="Multi-Stop Monitor",
    )


def merge_source_departures(hass: HomeAssistant, source_entities: list[str]) -> list[dict[str, Any]]:
    """Merge the departures of all source sensors, sorted by minutes until departure."""
    all_departures: list[dict[str, Any]] = []

    for entity_id in source_entities:
        state = hass.states.get(entity_id)
        if not state:
            continue

        departures = state.attributes.get("departures", [])
        station_name = state.attributes.get("station_name", entity_id)

        for dep in departures:
            if isinstance(dep, dict):
                dep_copy = dict(dep)
                dep_copy["source_station"] = station_name
                dep_copy["source_entity"] = entity_id
                all_departures.append(dep_copy)

    all_departures.sort(key=lambda d: d.get("minutes_until_departure", 999))
    return all_departures


async def async_setup_multi_stop_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up a multi-stop entry (combined sensor + departure board camera)."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(config_entry, MULTI_STOP_PLATFORMS)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up multi-stop sensor platform."""
    if not config_entry.data.get(CONF_IS_MULTI_STOP):
        return

    source_entities = config_entry.data.get(CONF_SOURCE_ENTITIES, [])
    name = config_entry.data.get(CONF_MULTI_STOP_NAME, "Multi-Stop")

    if not source_entities:
        return

    async_add_entities([MultiStopSensor(hass, config_entry, source_entities, name)])


class MultiStopSensor(SensorEntity):
    """Sensor combining departures from multiple stops."""

    _attr_icon = "mdi:map-marker-multiple"
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        source_entities: list[str],
        name: str,
    ):
        """Initialize."""
        self.hass = hass
        self._config_entry = config_entry
        self._source_entities = source_entities
        self._attr_unique_id = f"multi_stop_{config_entry.entry_id}"
        self._attr_name = None  # device name IS the entity name
        self._attr_device_info = multi_stop_device_info(config_entry, name)

    async def async_added_to_hass(self) -> None:
        """Start listening to source entity changes."""

        @callback
        def _state_changed(event) -> None:
            self._update_from_sources()
            self.async_write_ha_state()

        self.async_on_remove(async_track_state_change_event(self.hass, self._source_entities, _state_changed))

        # Initial update
        self._update_from_sources()

    def _update_from_sources(self) -> None:
        """Merge departures from all source entities."""
        self._departures = merge_source_departures(self.hass, self._source_entities)

    @property
    def native_value(self) -> str | None:
        """Return next departure across all stops."""
        if not self._departures:
            return "No departures"
        dep = self._departures[0]
        return dep.get("departure_time", "")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return combined departures."""
        if not hasattr(self, "_departures"):
            return {}

        return {
            "departures": self._departures[:20],
            "source_entities": self._source_entities,
            "source_count": len(self._source_entities),
            "total_departures": len(self._departures),
            "next_departure_minutes": (
                self._departures[0].get("minutes_until_departure") if self._departures else None
            ),
        }
