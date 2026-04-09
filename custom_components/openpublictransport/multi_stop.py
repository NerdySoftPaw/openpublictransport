"""Multi-stop sensor for Open Public Transport integration.

Combines departures from multiple stops into a single sorted view.
Created via config flow by selecting existing departure sensors.
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


async def async_setup_multi_stop_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up a multi-stop sensor from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
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
        self._unsub_listeners: list = []

        self._attr_unique_id = f"multi_stop_{config_entry.entry_id}"
        self._attr_name = name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"multi_stop_{config_entry.entry_id}")},
            name=name,
            manufacturer="Open Public Transport",
            model="Multi-Stop Monitor",
        )

    async def async_added_to_hass(self) -> None:
        """Start listening to source entity changes."""

        @callback
        def _state_changed(event) -> None:
            self._update_from_sources()
            self.async_write_ha_state()

        for entity_id in self._source_entities:
            self._unsub_listeners.append(async_track_state_change_event(self.hass, entity_id, _state_changed))

        # Initial update
        self._update_from_sources()

    async def async_will_remove_from_hass(self) -> None:
        """Remove listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    def _update_from_sources(self) -> None:
        """Merge departures from all source entities."""
        all_departures = []

        for entity_id in self._source_entities:
            state = self.hass.states.get(entity_id)
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

        # Sort by minutes_until_departure
        all_departures.sort(key=lambda d: d.get("minutes_until_departure", 999))

        self._departures = all_departures

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
