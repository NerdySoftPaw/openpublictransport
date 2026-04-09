"""Statistics tracking for departure punctuality.

Tracks delay statistics per line over time and exposes them as sensor attributes.
Uses coordinator data — no additional API calls needed.
"""

import logging
from collections import defaultdict
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .sensor import PublicTransportDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up statistics sensor."""
    if config_entry.data.get("is_trip"):
        return

    coordinator_key = f"{config_entry.entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)

    if not coordinator:
        return

    async_add_entities([PunctualitySensor(coordinator, config_entry)])


class PunctualitySensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking punctuality statistics per line."""

    _attr_icon = "mdi:chart-line"

    def __init__(
        self,
        coordinator: PublicTransportDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        """Initialize."""
        super().__init__(coordinator)
        self._config_entry = config_entry

        provider = coordinator.provider
        station_id = coordinator.station_id
        place_dm = coordinator.place_dm
        name_dm = coordinator.name_dm
        station_key = station_id or f"{place_dm}_{name_dm}".lower().replace(" ", "_")

        self._attr_unique_id = f"{provider}_{station_key}_statistics"
        self._attr_name = f"{provider.upper()} {place_dm} - {name_dm} Statistics"
        self._attr_native_unit_of_measurement = "%"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{provider}_{station_key}")},
            suggested_area=place_dm,
        )

        # Statistics storage
        self._total_departures = 0
        self._on_time_departures = 0
        self._line_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "on_time": 0, "total_delay": 0})
        self._seen_departures: set[str] = set()

    @property
    def native_value(self) -> float | None:
        """Return overall punctuality percentage."""
        if self._total_departures == 0:
            return None
        return round(self._on_time_departures / self._total_departures * 100, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-line statistics."""
        line_data = {}
        for line, stats in sorted(self._line_stats.items()):
            total = stats["total"]
            on_time = stats["on_time"]
            avg_delay = stats["total_delay"] / total if total > 0 else 0
            line_data[line] = {
                "total": total,
                "on_time": on_time,
                "punctuality": round(on_time / total * 100, 1) if total > 0 else 0,
                "average_delay": round(avg_delay, 1),
            }

        return {
            "total_tracked": self._total_departures,
            "on_time_tracked": self._on_time_departures,
            "lines": line_data,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Track statistics from coordinator data."""
        if not self.coordinator.data or not self.coordinator.provider_instance:
            self.async_write_ha_state()
            return

        provider_instance = self.coordinator.provider_instance
        stop_events = self.coordinator.data.get("stopEvents", [])
        tz = dt_util.get_time_zone(provider_instance.get_timezone())
        now = dt_util.now()

        for stop in stop_events:
            dep = provider_instance.parse_departure(stop, tz, now)
            if not dep:
                continue

            # Deduplicate: only count each departure once
            dep_key = f"{dep.line}_{dep.destination}_{dep.planned_time}"
            if dep_key in self._seen_departures:
                continue
            self._seen_departures.add(dep_key)

            # Keep set manageable
            if len(self._seen_departures) > 500:
                self._seen_departures = set(list(self._seen_departures)[-250:])

            self._total_departures += 1
            is_on_time = dep.delay <= 2  # Up to 2 min is considered on time

            if is_on_time:
                self._on_time_departures += 1

            line = dep.line or "unknown"
            self._line_stats[line]["total"] += 1
            if is_on_time:
                self._line_stats[line]["on_time"] += 1
            self._line_stats[line]["total_delay"] += dep.delay

        self.async_write_ha_state()
