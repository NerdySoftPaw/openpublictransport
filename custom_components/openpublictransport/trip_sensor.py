"""Trip sensor for Open Public Transport integration.

Polls for route options from A to B and shows the next best connection.
Created via the plan_trip config flow.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .trip import async_plan_trip

_LOGGER = logging.getLogger(__name__)

CONF_TRIP_ORIGIN = "trip_origin"
CONF_TRIP_ORIGIN_CITY = "trip_origin_city"
CONF_TRIP_DESTINATION = "trip_destination"
CONF_TRIP_DESTINATION_CITY = "trip_destination_city"
CONF_TRIP_PROVIDER = "trip_provider"
CONF_IS_TRIP = "is_trip"


class TripDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for trip planning data."""

    def __init__(
        self,
        hass: HomeAssistant,
        provider: str,
        origin: str,
        origin_city: str,
        destination: str,
        destination_city: str,
        scan_interval: int = 120,
    ):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Trip {origin} → {destination}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.provider = provider
        self.origin = origin
        self.origin_city = origin_city
        self.destination = destination
        self.destination_city = destination_city

    async def _async_update_data(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch trip data."""
        return await async_plan_trip(
            self.hass,
            self.provider,
            self.origin,
            self.origin_city,
            self.destination,
            self.destination_city,
        )


async def async_setup_trip_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up a trip sensor from a config entry."""
    provider = config_entry.data[CONF_TRIP_PROVIDER]
    origin = config_entry.data[CONF_TRIP_ORIGIN]
    origin_city = config_entry.data[CONF_TRIP_ORIGIN_CITY]
    destination = config_entry.data[CONF_TRIP_DESTINATION]
    destination_city = config_entry.data[CONF_TRIP_DESTINATION_CITY]
    scan_interval = config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = TripDataUpdateCoordinator(
        hass, provider, origin, origin_city, destination, destination_city, scan_interval
    )

    coordinator_key = f"{config_entry.entry_id}_trip_coordinator"
    hass.data.setdefault(DOMAIN, {})[coordinator_key] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up trip sensor platform."""
    if not config_entry.data.get(CONF_IS_TRIP):
        return

    coordinator_key = f"{config_entry.entry_id}_trip_coordinator"
    coordinator = hass.data.get(DOMAIN, {}).get(coordinator_key)
    if not coordinator:
        return

    async_add_entities([TripSensor(coordinator, config_entry)])


class TripSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the next best trip from A to B."""

    def __init__(
        self,
        coordinator: TripDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        """Initialize."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_icon = "mdi:routes"

        origin = coordinator.origin
        origin_city = coordinator.origin_city
        dest = coordinator.destination
        dest_city = coordinator.destination_city
        provider = coordinator.provider

        self._attr_unique_id = f"{provider}_trip_{origin_city}_{origin}_{dest_city}_{dest}".lower().replace(" ", "_")
        self._attr_name = f"{provider.upper()} {origin}, {origin_city} → {dest}, {dest_city}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=f"{origin}, {origin_city} → {dest}, {dest_city}",
            manufacturer=f"{provider.upper()} Public Transport",
            model="Trip Planner",
        )

    @property
    def native_value(self) -> str | None:
        """Return the next trip as state."""
        journeys = self.coordinator.data
        if not journeys:
            return "No connections"

        j = journeys[0]
        dep = j.get("departure", "")
        arr = j.get("arrival", "")
        dur = j.get("duration_minutes", 0)
        transfers = j.get("transfers", 0)

        if dep and arr:
            return f"{dep} → {arr} ({dur} min, {transfers} transfers)"
        return "No connections"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return trip details as attributes."""
        journeys = self.coordinator.data
        if not journeys:
            return {}

        best = journeys[0]
        attrs = {
            "departure": best.get("departure"),
            "arrival": best.get("arrival"),
            "duration_minutes": best.get("duration_minutes"),
            "transfers": best.get("transfers"),
            "connection_feasible": best.get("connection_feasible"),
            "transfer_risk": best.get("transfer_risk"),
            "min_transfer_time": best.get("min_transfer_time"),
            "legs": best.get("legs", []),
            "alternative_journeys": len(journeys) - 1,
            "origin": f"{self.coordinator.origin}, {self.coordinator.origin_city}",
            "destination": f"{self.coordinator.destination}, {self.coordinator.destination_city}",
        }

        # All journey options
        if len(journeys) > 1:
            attrs["next_journeys"] = [
                {
                    "departure": j.get("departure"),
                    "arrival": j.get("arrival"),
                    "duration_minutes": j.get("duration_minutes"),
                    "transfers": j.get("transfers"),
                    "transfer_risk": j.get("transfer_risk"),
                }
                for j in journeys[1:4]  # Next 3 alternatives
            ]

        return attrs
