import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_RATE_LIMIT_PER_DAY,
    CONF_DEPARTURES,
    CONF_LINE_FILTER,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRAFIKLAB_API_KEY,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    DEFAULT_DEPARTURES,
    DEFAULT_NAME,
    DEFAULT_PLACE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PROVIDER_ENTITY_PICTURES,
    PROVIDER_NTA_IE,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VRR,
    TRANSPORTATION_TYPES,
)
from .providers import get_provider

_LOGGER = logging.getLogger(__name__)
INTEGRATION_VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text()).get("version", "unknown")


class PublicTransportDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching public transport data from API."""

    def __init__(
        self,
        hass: HomeAssistant,
        provider: str,
        place_dm: str,
        name_dm: str,
        station_id: Optional[str],
        departures_limit: int,
        scan_interval: int,
        config_entry: Optional[ConfigEntry] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize."""
        self.provider = provider
        self.place_dm = place_dm
        self.name_dm = name_dm
        self.station_id = station_id
        self.departures_limit = departures_limit
        self._api_calls_today = 0
        self._last_api_reset = datetime.now().date()
        self.api_key = api_key  # For Trafiklab API or NTA API (Primary)
        self.api_key_secondary: Optional[str] = None  # For NTA API (Secondary, optional fallback)

        # Note: config_entry parameter was added in HA 2024.11+
        # We store it ourselves for compatibility with older versions
        self._config_entry = config_entry
        self._base_scan_interval = scan_interval
        self._empty_result_count = 0

        # Initialize provider instance
        self.provider_instance = get_provider(
            provider,
            hass,
            api_key=api_key,
            api_key_secondary=(
                config_entry.data.get(CONF_NTA_API_KEY_SECONDARY)
                if config_entry and provider == PROVIDER_NTA_IE
                else None
            ),
        )
        if not self.provider_instance:
            _LOGGER.error("Failed to initialize provider: %s", provider)

        # Get secondary key from config entry if available (only for NTA)
        if provider == PROVIDER_NTA_IE and config_entry:
            self.api_key_secondary = config_entry.data.get(CONF_NTA_API_KEY_SECONDARY)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{provider.upper()} {place_dm} - {name_dm}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and cleanup resources.

        This method should be called when the config entry is being unloaded
        to ensure proper cleanup of provider resources (e.g., GTFS data).
        """
        _LOGGER.debug("Shutting down coordinator for %s", self.provider)

        # Cleanup provider resources (including GTFS data reference)
        if self.provider_instance and hasattr(self.provider_instance, "cleanup"):
            try:
                await self.provider_instance.cleanup()
                _LOGGER.debug("Provider cleanup completed for %s", self.provider)
            except Exception as e:
                _LOGGER.warning("Error during provider cleanup for %s: %s", self.provider, e)

    def _check_rate_limit(self) -> bool:
        """Check if we're within API rate limits."""
        today = datetime.now().date()
        if today > self._last_api_reset:
            self._api_calls_today = 0
            self._last_api_reset = today
            # Clear rate limit repair issue when new day starts
            ir.async_delete_issue(self.hass, DOMAIN, f"rate_limit_{self.provider}")

        if self._api_calls_today >= API_RATE_LIMIT_PER_DAY:
            _LOGGER.warning("API rate limit approached, skipping update")
            # Create repair issue
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"rate_limit_{self.provider}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="rate_limit_reached",
                translation_placeholders={
                    "provider": self.provider.upper(),
                    "limit": str(API_RATE_LIMIT_PER_DAY),
                },
            )
            return False
        return True

    def _adjust_polling_interval(self, has_departures: bool) -> None:
        """Adjust polling interval based on time of day and results.

        - Night (1:00-4:30): poll every 10 minutes
        - Empty results: gradually increase interval (up to 5x base)
        - Normal: use configured base interval
        """
        now = dt_util.now()
        hour = now.hour

        # Night mode: 1:00 - 4:30 → very slow polling
        if 1 <= hour < 5 or (hour == 0 and now.minute >= 30):
            new_interval = max(self._base_scan_interval * 10, 600)
            self._empty_result_count = 0
        elif not has_departures:
            # No departures: gradually increase interval
            self._empty_result_count += 1
            multiplier = min(self._empty_result_count, 5)
            new_interval = self._base_scan_interval * multiplier
        else:
            # Normal: back to base interval
            self._empty_result_count = 0
            new_interval = self._base_scan_interval

        new_td = timedelta(seconds=new_interval)
        if self.update_interval != new_td:
            self.update_interval = new_td
            _LOGGER.debug("Adjusted polling interval to %ss for %s", new_interval, self.provider)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        if not self._check_rate_limit():
            # Return last known data instead of failing
            if self.data:
                return self.data
            raise UpdateFailed("API rate limit reached")

        try:
            data = await self._fetch_departures()
            if data and isinstance(data, dict):
                self._api_calls_today += 1
                # Clear API error repair issue on successful fetch
                ir.async_delete_issue(self.hass, DOMAIN, f"api_error_{self.provider}")
                # Adjust polling interval based on results
                has_departures = bool(data.get("stopEvents"))
                self._adjust_polling_interval(has_departures)
                return data
            else:
                # Create repair issue for invalid API response
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"api_error_{self.provider}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="api_error",
                    translation_placeholders={
                        "provider": self.provider.upper(),
                    },
                )
                raise UpdateFailed("Invalid or empty API response")
        except UpdateFailed:
            raise
        except Exception as err:
            # Create repair issue for API errors
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"api_error_{self.provider}",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="api_error",
                translation_placeholders={
                    "provider": self.provider.upper(),
                },
            )
            raise UpdateFailed(f"Error fetching data: {err}")

    async def _fetch_departures(self) -> Optional[Dict[str, Any]]:
        """Fetch departure data from the API."""
        if not self.provider_instance:
            raise UpdateFailed(f"No provider instance for {self.provider}")

        return await self.provider_instance.fetch_departures(
            self.station_id, self.place_dm, self.name_dm, self.departures_limit
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor from a config entry."""
    # Trip entries are handled by trip_sensor.py
    if config_entry.data.get("is_trip"):
        from .trip_sensor import async_setup_entry as trip_setup

        return await trip_setup(hass, config_entry, async_add_entities)
    # Reuse coordinator created in __init__.py
    coordinator_key = f"{config_entry.entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)

    if coordinator is None:
        # Fallback: create coordinator if not found (shouldn't happen in normal flow)
        provider = config_entry.data.get(CONF_PROVIDER, PROVIDER_VRR)
        place_dm = config_entry.data.get("place_dm", DEFAULT_PLACE)
        name_dm = config_entry.data.get("name_dm", DEFAULT_NAME)
        station_id = config_entry.data.get(CONF_STATION_ID)
        trafiklab_api_key = config_entry.data.get(CONF_TRAFIKLAB_API_KEY)
        nta_api_key = config_entry.data.get(CONF_NTA_API_KEY)

        # Use appropriate API key based on provider
        api_key = None
        if provider == PROVIDER_TRAFIKLAB_SE:
            api_key = trafiklab_api_key
        elif provider == PROVIDER_NTA_IE:
            api_key = nta_api_key

        departures = config_entry.options.get(
            CONF_DEPARTURES, config_entry.data.get(CONF_DEPARTURES, DEFAULT_DEPARTURES)
        )
        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        coordinator = PublicTransportDataUpdateCoordinator(
            hass,
            provider,
            place_dm,
            name_dm,
            station_id,
            departures,
            scan_interval,
            config_entry=config_entry,
            api_key=api_key,
        )
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][coordinator_key] = coordinator
        await coordinator.async_config_entry_first_refresh()

    # Use options if available, otherwise fall back to data
    transportation_types = config_entry.options.get(
        CONF_TRANSPORTATION_TYPES,
        config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES.keys())),
    )

    # Create sensor
    async_add_entities(
        [
            MultiProviderSensor(
                coordinator,
                config_entry,
                transportation_types,
            )
        ]
    )


class MultiProviderSensor(CoordinatorEntity, SensorEntity):
    """Sensor für VRR/KVV/HVV using DataUpdateCoordinator."""

    def __init__(
        self,
        coordinator: PublicTransportDataUpdateCoordinator,
        config_entry: ConfigEntry,
        transportation_types: List[str],
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self.transportation_types = transportation_types or list(TRANSPORTATION_TYPES.keys())
        self._state: str | None = None
        self._attributes: dict[str, Any] = {}

        # Get line filter from options/data
        line_filter_str = config_entry.options.get(CONF_LINE_FILTER, config_entry.data.get(CONF_LINE_FILTER, ""))
        self._line_filter: set[str] = (
            {line.strip().lower() for line in line_filter_str.split(",") if line.strip()} if line_filter_str else set()
        )

        # Get option for provider logo display
        self._use_provider_logo = config_entry.options.get(
            CONF_USE_PROVIDER_LOGO, config_entry.data.get(CONF_USE_PROVIDER_LOGO, False)
        )

        # Setup entity
        self._provider = coordinator.provider
        provider = self._provider
        station_id = coordinator.station_id
        place_dm = coordinator.place_dm
        name_dm = coordinator.name_dm

        station_key = station_id or f"{place_dm}_{name_dm}".lower().replace(" ", "_")
        self._attr_unique_id = f"{provider}_{station_key}"
        self._attr_name = f"{provider.upper()} {place_dm} - {name_dm}"

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{provider}_{station_key}")},
            name=f"{place_dm} - {name_dm}",
            manufacturer=f"{provider.upper()} Public Transport",
            model="Departure Monitor",
            sw_version=INTEGRATION_VERSION,
            configuration_url="https://github.com/NerdySoftPaw/openpublictransport",
            suggested_area=place_dm,
        )

        # Listen to options updates
        self._config_entry.async_on_unload(self._config_entry.add_update_listener(self._async_update_listener))

    @property
    def state(self):
        """Return the state, which is the departure time of the next departure."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return additional attributes, including all departures."""
        return self._attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def icon(self):
        """Return the icon to use in the frontend based on next departure."""
        # Icon mapping for different transportation types
        icon_mapping = {
            "bus": "mdi:bus-clock",
            "tram": "mdi:tram",
            "subway": "mdi:subway-variant",
            "train": "mdi:train",
            "ferry": "mdi:ferry",
            "taxi": "mdi:taxi",
            "on_demand": "mdi:bus-alert",
        }

        # Try to get the transportation type of the next departure
        departures = self._attributes.get("departures", [])
        if departures and len(departures) > 0:
            first_dep = departures[0]
            next_transport_type = first_dep.get("transportation_type", "bus") if isinstance(first_dep, dict) else "bus"
            return icon_mapping.get(next_transport_type, "mdi:bus-clock")

        return "mdi:bus-clock"  # Default icon

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture (provider logo) to use in the frontend.

        Note: When entity_picture is set, it takes precedence over the icon.
        To use icons instead, this returns None when use_provider_logo is False.
        """
        # Only return provider logo if the option is enabled
        if self._use_provider_logo:
            return PROVIDER_ENTITY_PICTURES.get(self._provider)
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            self._process_departure_data(self.coordinator.data)
        self.async_write_ha_state()

    async def _async_update_listener(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Handle options update."""
        # Update transportation types
        self.transportation_types = config_entry.options.get(
            CONF_TRANSPORTATION_TYPES,
            config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES.keys())),
        )

        # Update provider logo setting
        self._use_provider_logo = config_entry.options.get(
            CONF_USE_PROVIDER_LOGO,
            config_entry.data.get(CONF_USE_PROVIDER_LOGO, False),
        )

        # Update coordinator settings
        departures = config_entry.options.get(
            CONF_DEPARTURES, config_entry.data.get(CONF_DEPARTURES, DEFAULT_DEPARTURES)
        )
        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        # Update coordinator
        self.coordinator.departures_limit = departures
        self.coordinator.update_interval = timedelta(seconds=scan_interval)

        # Force refresh
        await self.coordinator.async_request_refresh()

    def _process_departure_data(self, data: Dict[str, Any]) -> None:
        """Process the departure data from the provider API.

        Parses raw API response, filters departures by configured transportation types,
        calculates statistics, and updates sensor state and attributes.

        Args:
            data: Raw API response containing stopEvents
        """
        # Validate response structure
        if not isinstance(data, dict):
            _LOGGER.error("Invalid API response: expected dict, got %s", type(data))
            return

        stop_events = data.get("stopEvents", [])

        # Validate stopEvents is a list
        if not isinstance(stop_events, list):
            _LOGGER.error("Invalid stopEvents in API response: expected list, got %s", type(stop_events))
            return

        # Cache frequently accessed values
        station_name = f"{self.coordinator.place_dm} - {self.coordinator.name_dm}"
        station_id = self.coordinator.station_id

        if not stop_events:
            self._state = "No departures"
            self._attributes = {
                "departures": [],
                "next_3_departures": [],
                "station_name": station_name,
                "last_updated": dt_util.utcnow().isoformat(),
                "next_departure_minutes": None,
                "station_id": station_id,
                "total_departures": 0,
                "delayed_count": 0,
                "on_time_count": 0,
                "average_delay": 0,
                "earliest_departure": None,
                "latest_departure": None,
            }
            return

        departures = []
        provider_instance = self.coordinator.provider_instance
        tz = dt_util.get_time_zone(provider_instance.get_timezone())
        now = dt_util.now()

        # Cache transportation_types to avoid repeated lookups
        transport_types_set = set(self.transportation_types)  # Set lookup is O(1) vs list O(n)

        for stop in stop_events:
            dep = provider_instance.parse_departure(stop, tz, now)
            # Filter by configured transportation types and line filter
            if dep and dep.transportation_type in transport_types_set:
                if not self._line_filter or dep.line.lower() in self._line_filter:
                    departures.append(dep)

        # Sort by departure time
        departures.sort(key=lambda x: x.departure_time_obj)

        # Limit to requested number
        departures_limit = self.coordinator.departures_limit
        departures = departures[:departures_limit]

        # Set state and attributes
        if departures:
            next_departure = departures[0]
            self._state = next_departure.departure_time
            next_minutes = next_departure.minutes_until_departure
        else:
            self._state = "No departures"
            next_minutes = None

        # Calculate statistics and convert to dicts in one pass
        clean_departures = []
        departure_times = []
        delayed_count = 0
        on_time_count = 0
        total_delay = 0

        for dep in departures:
            # Extract departure_time_obj for stats
            dep_time_obj = dep.departure_time_obj
            if dep_time_obj:
                departure_times.append(dep_time_obj)

            # Count delays
            delay = dep.delay
            if delay > 0:
                delayed_count += 1
                total_delay += delay
            else:
                on_time_count += 1

            # Convert UnifiedDeparture to dict for attributes
            clean_departures.append(dep.to_dict())

        # Next 3 departures (simplified)
        next_3_departures = clean_departures[:3]

        # Average delay
        average_delay = round(total_delay / delayed_count, 1) if delayed_count > 0 else 0

        # Earliest and latest departure times
        earliest_departure = None
        latest_departure = None
        if departure_times:
            earliest_departure = min(departure_times).strftime("%H:%M")
            latest_departure = max(departure_times).strftime("%H:%M")

        self._attributes = {
            "departures": clean_departures,
            "next_3_departures": next_3_departures,
            "station_name": station_name,
            "last_updated": dt_util.utcnow().isoformat(),
            "next_departure_minutes": next_minutes,
            "station_id": station_id,
            "total_departures": len(clean_departures),
            "delayed_count": delayed_count,
            "on_time_count": on_time_count,
            "average_delay": average_delay,
            "earliest_departure": earliest_departure,
            "latest_departure": latest_departure,
        }
