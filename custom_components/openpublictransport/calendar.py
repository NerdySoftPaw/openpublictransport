"""Calendar platform for Open Public Transport integration.

Each departure becomes a calendar event, enabling:
- Visual departure schedule on HA calendar card
- Calendar-based automations and triggers
"""

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_TRANSPORTATION_TYPES, DOMAIN, TRANSPORTATION_TYPES
from .sensor import PublicTransportDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up calendar from a config entry."""
    coordinator_key = f"{config_entry.entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)

    if not coordinator:
        return

    async_add_entities([DepartureCalendar(coordinator, config_entry)])


class DepartureCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity showing departures as events."""

    def __init__(
        self,
        coordinator: PublicTransportDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._events: list[CalendarEvent] = []

        provider = coordinator.provider
        station_id = coordinator.station_id
        place_dm = coordinator.place_dm
        name_dm = coordinator.name_dm
        station_key = station_id or f"{place_dm}_{name_dm}".lower().replace(" ", "_")

        self._attr_unique_id = f"{provider}_{station_key}_calendar"
        self._attr_name = f"{provider.upper()} {place_dm} - {name_dm} Departures"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{provider}_{station_key}")},
            suggested_area=place_dm,
        )

        self._transportation_types = set(
            config_entry.options.get(
                CONF_TRANSPORTATION_TYPES,
                config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES.keys())),
            )
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if self._events:
            return self._events[0]
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events in a specific time range."""
        return [e for e in self._events if e.start >= start_date and e.start <= end_date]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._events = []

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

        for stop in stop_events:
            dep = provider_instance.parse_departure(stop, tz, now)
            if not dep or dep.transportation_type not in self._transportation_types:
                continue

            start = dep.departure_time_obj
            end = start + timedelta(minutes=1)

            summary = f"{dep.line} → {dep.destination}"
            description_parts = []
            if dep.platform:
                description_parts.append(f"Platform: {dep.platform}")
            if dep.delay > 0:
                description_parts.append(f"Delay: +{dep.delay} min")
            if dep.is_realtime:
                description_parts.append("Realtime")
            if dep.notices:
                description_parts.extend(dep.notices)

            self._events.append(
                CalendarEvent(
                    start=start,
                    end=end,
                    summary=summary,
                    description="\n".join(description_parts) if description_parts else None,
                )
            )

        self._events.sort(key=lambda e: e.start)
        self.async_write_ha_state()
