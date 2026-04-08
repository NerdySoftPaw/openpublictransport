"""Binary sensor platform for Open Public Transport integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_HVV,
    PROVIDER_KVV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VRR,
    TRANSPORTATION_TYPES,
)
from .data_models import UnifiedDeparture
from .sensor import PublicTransportDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor from a config entry."""
    # Get coordinator from sensor setup
    # We need to get it from hass.data
    coordinator_key = f"{config_entry.entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)

    if not coordinator:
        return

    transportation_types = config_entry.options.get(
        CONF_TRANSPORTATION_TYPES, config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES.keys()))
    )

    async_add_entities([PublicTransportDelayBinarySensor(coordinator, config_entry, transportation_types)])


class PublicTransportDelayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for public transport delays."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: PublicTransportDataUpdateCoordinator,
        config_entry: ConfigEntry,
        transportation_types: list[str],
    ):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self.transportation_types = transportation_types
        self._attr_is_on = False
        self._attributes: dict[str, Any] = {}

        # Setup entity
        provider = coordinator.provider
        station_id = coordinator.station_id
        place_dm = coordinator.place_dm
        name_dm = coordinator.name_dm

        self._attr_unique_id = f"{provider}_{station_id or f'{place_dm}_{name_dm}'.lower().replace(' ', '_')}_delays"
        self._attr_name = f"{provider.upper()} {place_dm} - {name_dm} Delays"

        # Device info - same device as sensor
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{provider}_{station_id or f'{place_dm}_{name_dm}'.lower().replace(' ', '_')}")},
            suggested_area=place_dm,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self._attributes

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self._attr_is_on:
            return "mdi:alert-circle"
        return "mdi:check-circle"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            self._process_delay_data(self.coordinator.data)
        self.async_write_ha_state()

    def _process_delay_data(self, data: dict[str, Any]) -> None:
        """Process delay data using unified departure structure.

        Uses the already parsed departures from the sensor if available,
        otherwise falls back to parsing the raw data using the same unified model.
        """
        # Try to get already parsed departures from the sensor
        departures = None
        if self.hass and hasattr(self.hass, "data"):
            sensor_entities = self.hass.data.get("entity_components", {}).get("sensor")
            if sensor_entities:
                for entity in sensor_entities.entities:
                    if (
                        hasattr(entity, "coordinator")
                        and entity.coordinator == self.coordinator
                        and hasattr(entity, "_attributes")
                    ):
                        departures = entity._attributes.get("departures", [])
                        if departures:
                            break

        # If we have parsed departures, use them (unified model)
        if departures:
            delayed_count = 0
            on_time_count = 0
            total_delay = 0
            max_delay = 0
            delays = []

            for dep in departures:
                if not isinstance(dep, dict):
                    continue
                delay = dep.get("delay", 0)
                if delay > 0:
                    delayed_count += 1
                    total_delay += delay
                    delays.append(delay)
                    max_delay = max(max_delay, delay)
                else:
                    on_time_count += 1
        else:
            # Fallback: parse raw data using unified model (same as sensor)
            stop_events = data.get("stopEvents", [])
            if not stop_events:
                self._attr_is_on = False
                self._attributes = {
                    "delayed_departures": 0,
                    "on_time_departures": 0,
                    "average_delay": 0,
                    "max_delay": 0,
                    "total_departures": 0,
                }
                return

            # Use same parsing logic as sensor
            provider = self.coordinator.provider
            if provider == PROVIDER_TRAFIKLAB_SE:
                tz = dt_util.get_time_zone("Europe/Stockholm")
            else:
                tz = dt_util.get_time_zone("Europe/Berlin")
            now = dt_util.now()

            from .sensor import MultiProviderSensor

            temp_sensor = MultiProviderSensor(
                self.coordinator,
                self._config_entry,
                self.transportation_types,
            )

            # Initialize parse_fn with proper type
            parse_fn: Callable[[dict[str, Any], Any, datetime], UnifiedDeparture | None] | None = None

            # Use provider instance for parsing if available
            if self.coordinator.provider_instance:
                provider_instance = self.coordinator.provider_instance
                tz_provider = dt_util.get_time_zone(provider_instance.get_timezone())

                def _parse_with_provider(
                    stop: dict[str, Any], tz_param: Any, now_param: datetime
                ) -> UnifiedDeparture | None:
                    return provider_instance.parse_departure(stop, tz_provider, now_param)

                parse_fn = _parse_with_provider
            # Fallback to old implementation
            elif provider == PROVIDER_VRR:
                parse_fn = temp_sensor._parse_departure_vrr
            elif provider == PROVIDER_KVV:
                parse_fn = temp_sensor._parse_departure_kvv
            elif provider == PROVIDER_HVV:
                parse_fn = temp_sensor._parse_departure_hvv
            elif provider == PROVIDER_TRAFIKLAB_SE:
                parse_fn = temp_sensor._parse_departure_trafiklab

            delayed_count = 0
            on_time_count = 0
            total_delay = 0
            max_delay = 0
            delays = []

            if parse_fn is not None:
                transport_types_set = set(self.transportation_types)
                for stop in stop_events:
                    dep = parse_fn(stop, tz, now)
                    if dep and dep.transportation_type in transport_types_set:
                        delay = dep.delay
                        if delay > 0:
                            delayed_count += 1
                            total_delay += delay
                            delays.append(delay)
                            max_delay = max(max_delay, delay)
                        else:
                            on_time_count += 1

        total_departures = delayed_count + on_time_count
        average_delay = total_delay / delayed_count if delayed_count > 0 else 0

        # Set binary sensor state (on if any delays > 5 minutes)
        self._attr_is_on = max_delay > 5

        self._attributes = {
            "delayed_departures": delayed_count,
            "on_time_departures": on_time_count,
            "average_delay": round(average_delay, 1),
            "max_delay": max_delay,
            "total_departures": total_departures,
            "delays_list": delays[:10] if delays else [],  # First 10 delays
            "delay_threshold": 5,  # Minutes threshold for triggering
        }
