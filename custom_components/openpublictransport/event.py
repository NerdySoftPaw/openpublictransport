"""Event platform for Open Public Transport integration.

Fires events when new disruption notices are detected, enabling
automations like notifications when a line is disrupted.
"""

import logging
from typing import Any

from homeassistant.components.event import EventEntity
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
    """Set up event entity from a config entry."""
    coordinator_key = f"{config_entry.entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)

    if not coordinator:
        return

    async_add_entities([DisruptionEventEntity(coordinator, config_entry)])


class DisruptionEventEntity(CoordinatorEntity, EventEntity):
    """Event entity that fires when new disruption notices appear."""

    _attr_event_types = ["disruption", "platform_change", "info"]

    def __init__(
        self,
        coordinator: PublicTransportDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        """Initialize the event entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._previous_notices: set[str] = set()

        provider = coordinator.provider
        station_id = coordinator.station_id
        place_dm = coordinator.place_dm
        name_dm = coordinator.name_dm
        station_key = station_id or f"{place_dm}_{name_dm}".lower().replace(" ", "_")

        self._attr_unique_id = f"{provider}_{station_key}_disruptions"
        self._attr_name = f"{provider.upper()} {place_dm} - {name_dm} Disruptions"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{provider}_{station_key}")},
            suggested_area=place_dm,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data — fire events for new notices."""
        if not self.coordinator.data:
            self.async_write_ha_state()
            return

        provider_instance = self.coordinator.provider_instance
        if not provider_instance:
            self.async_write_ha_state()
            return

        stop_events = self.coordinator.data.get("stopEvents", [])
        tz = dt_util.get_time_zone(provider_instance.get_timezone())
        now = dt_util.now()

        current_notices: set[str] = set()
        platform_changes: list[dict[str, Any]] = []

        for stop in stop_events:
            dep = provider_instance.parse_departure(stop, tz, now)
            if not dep:
                continue

            # Collect notices
            if dep.notices:
                for notice in dep.notices:
                    current_notices.add(notice)

            # Collect platform changes
            if dep.platform_changed:
                platform_changes.append(
                    {
                        "line": dep.line,
                        "destination": dep.destination,
                        "old_platform": dep.planned_platform,
                        "new_platform": dep.platform,
                    }
                )

        # Fire events for NEW notices only
        new_notices = current_notices - self._previous_notices
        for notice in new_notices:
            self._trigger_event(
                "disruption",
                {"message": notice},
            )

        # Fire events for platform changes
        for change in platform_changes:
            self._trigger_event(
                "platform_change",
                change,
            )

        self._previous_notices = current_notices
        self.async_write_ha_state()
