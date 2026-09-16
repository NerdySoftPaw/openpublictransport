"""Trip sensor for Open Public Transport integration.

Polls for route options from A to B and shows the next best connection.
Created via the plan_trip config flow.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from openpublictransport import (
    ApiConnectionError,
    ApiError,
    ApiTimeoutError,
    AuthenticationError,
    OpenPublicTransportError,
)

from .const import (
    CONF_LINE_FILTER,
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_TRANSPORTATION_TYPES,
    CONF_VBN_API_KEY,
    CONF_WALKING_TIME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WALKING_TIME,
    DOMAIN,
    TRANSPORTATION_TYPES,
)
from .sensor import _RESTORE_SKIP_ATTRS
from .trip import async_plan_trip

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)

CONF_TRIP_ORIGIN = "trip_origin"
CONF_TRIP_ORIGIN_CITY = "trip_origin_city"
CONF_TRIP_DESTINATION = "trip_destination"
CONF_TRIP_DESTINATION_CITY = "trip_destination_city"
CONF_TRIP_PROVIDER = "trip_provider"
CONF_IS_TRIP = "is_trip"

# Legs that are not a vehicle ride carry no line and no selectable transport
# type, so neither filter has anything to say about them.
_NON_VEHICLE_LEG_TYPES = frozenset({"walk", "bicycle", ""})


def _trip_line_filter(config_entry: ConfigEntry) -> set[str]:
    """Return the entry's line filter, lowercased; empty means "every line"."""
    raw = config_entry.options.get(CONF_LINE_FILTER, config_entry.data.get(CONF_LINE_FILTER, ""))
    return {line.strip().lower() for line in str(raw or "").split(",") if line.strip()}


def _trip_transport_types(config_entry: ConfigEntry) -> set[str]:
    """Return the transport types the entry allows.

    Restricted to the types the options flow can actually deselect: a journey on
    a ferry or a taxi must not disappear just because those are absent from a
    four-checkbox form that never offered them.
    """
    configured = config_entry.options.get(
        CONF_TRANSPORTATION_TYPES,
        config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES)),
    )
    return set(configured or TRANSPORTATION_TYPES) & set(TRANSPORTATION_TYPES)


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
        origin_id: Optional[str] = None,
        dest_id: Optional[str] = None,
        api_key: Optional[str] = None,
        custom_url: Optional[str] = None,
        walking_time: int = DEFAULT_WALKING_TIME,
        line_filter: Optional[set[str]] = None,
        transport_types: Optional[set[str]] = None,
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
        self.origin_id = origin_id
        self.dest_id = dest_id
        self.api_key = api_key
        self.custom_url = custom_url
        self.walking_time = walking_time
        # The same filters the departure board applies, honoured for trips too:
        # they were configurable on a trip device but changed nothing (issue #87).
        self.line_filter = line_filter or set()
        self.transport_types = transport_types if transport_types is not None else set(TRANSPORTATION_TYPES)
        # Mirrors PublicTransportDataUpdateCoordinator so diagnostics can report
        # it for trip entries too (issue #58).
        self.last_update_success_time: Optional[datetime] = None

    async def _async_update_data(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch trip data."""
        # Ask for connections the traveller can still reach: with a walking time
        # configured, the first one that counts leaves that many minutes from now.
        # Without one, pass None so the provider anchors on its own clock.
        earliest = dt_util.now() + timedelta(minutes=self.walking_time) if self.walking_time else None

        try:
            data = await async_plan_trip(
                self.hass,
                self.provider,
                self.origin,
                self.origin_city,
                self.destination,
                self.destination_city,
                departure_time=earliest,
                origin_id=self.origin_id,
                dest_id=self.dest_id,
                api_key=self.api_key,
                custom_url=self.custom_url,
            )
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            # Without this the entity stayed "available" through an outage,
            # silently serving its last known connection (#88).
            raise UpdateFailed(f"{self.provider}: HTTP {err.status}") from err
        except (ApiTimeoutError, ApiConnectionError) as err:
            raise UpdateFailed(f"{self.provider}: unreachable ({err})") from err
        except OpenPublicTransportError as err:
            raise UpdateFailed(f"{self.provider}: {err}") from err
        if data is not None:
            # `None` is a failed or unsupported lookup; an empty list is a
            # successful query that simply found no connection (EFA's
            # _parse_journeys returns [] for an empty board). Both leave
            # last_update_success True, so only the former must skip the stamp.
            self.last_update_success_time = dt_util.now()
            data = self._drop_departed(data)
            data = self._apply_filters(data)
        return data

    def _apply_filters(self, journeys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Drop connections that use a line or transport type the entry excludes.

        A trip is only wanted if *every* vehicle on it is wanted, so one
        disallowed leg removes the whole connection — a journey that ends on the
        400 bus is not a U43 journey. A leg whose transport type could not be
        resolved is left alone: filtering on a guess would hide connections the
        provider did describe correctly.
        """
        if not self.line_filter and self.transport_types >= set(TRANSPORTATION_TYPES):
            return journeys

        kept = [journey for journey in journeys if self._journey_allowed(journey)]
        if len(kept) < len(journeys):
            _LOGGER.debug(
                "Trip %s → %s: %s of %s connection(s) filtered out (lines=%s, types=%s)",
                self.origin,
                self.destination,
                len(journeys) - len(kept),
                len(journeys),
                sorted(self.line_filter) or "all",
                sorted(self.transport_types),
            )
        return kept

    def _journey_allowed(self, journey: Dict[str, Any]) -> bool:
        """Return True when every vehicle leg of a journey passes both filters."""
        for leg in journey.get("legs", []):
            transport_type = str(leg.get("transport_type") or "").lower()
            if transport_type in _NON_VEHICLE_LEG_TYPES:
                continue
            if transport_type in TRANSPORTATION_TYPES and transport_type not in self.transport_types:
                return False
            line = str(leg.get("line") or "").strip().lower()
            if self.line_filter and line and line not in self.line_filter:
                return False
        return True

    def _drop_departed(self, journeys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Drop connections that have already left.

        EFA anchors the requested time on the first *vehicle* departure and
        back-dates the walk to the platform, so its first journey has regularly
        already started — which is what put a past connection into the sensor
        state in issue #72. A journey whose departure cannot be parsed is kept:
        better an unrated connection than an empty sensor.
        """
        cutoff = dt_util.now() + timedelta(minutes=self.walking_time)
        reachable = [
            journey
            for journey in journeys
            if (departure := dt_util.parse_datetime(journey.get("departure_timestamp") or "")) is None
            or departure >= cutoff
        ]
        if len(reachable) < len(journeys):
            _LOGGER.debug(
                "Trip %s → %s: dropped %s connection(s) departing before %s",
                self.origin,
                self.destination,
                len(journeys) - len(reachable),
                cutoff.isoformat(),
            )
        return reachable


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
    origin_id = config_entry.data.get("trip_origin_id")
    dest_id = config_entry.data.get("trip_destination_id")
    # Options win over data — both are configurable after setup via the options flow
    scan_interval = config_entry.options.get(
        CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    walking_time = config_entry.options.get(
        CONF_WALKING_TIME, config_entry.data.get(CONF_WALKING_TIME, DEFAULT_WALKING_TIME)
    )

    # Resolve API key and custom URL based on provider
    if provider == "vbn_otp":
        api_key = config_entry.data.get(CONF_VBN_API_KEY)
        custom_url = None
    elif provider == "openpublictransport":
        api_key = config_entry.data.get(CONF_OPT_API_KEY)
        custom_url = None
    elif provider == "otp_custom":
        api_key = config_entry.data.get(CONF_OTP_CUSTOM_API_KEY)
        custom_url = config_entry.data.get(CONF_OTP_BASE_URL)
    else:
        api_key = None
        custom_url = None

    coordinator = TripDataUpdateCoordinator(
        hass,
        provider,
        origin,
        origin_city,
        destination,
        destination_city,
        scan_interval,
        origin_id=origin_id,
        dest_id=dest_id,
        api_key=api_key,
        custom_url=custom_url,
        walking_time=walking_time,
        line_filter=_trip_line_filter(config_entry),
        transport_types=_trip_transport_types(config_entry),
    )

    config_entry.runtime_data = coordinator

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

    coordinator = config_entry.runtime_data
    if not coordinator:
        return

    async_add_entities([TripSensor(coordinator, config_entry)])


class TripSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Sensor showing the next best trip from A to B."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TripDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        """Initialize."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_icon = "mdi:routes"
        self._restored_state: str | None = None
        self._restored_attributes: dict[str, Any] = {}

        origin = coordinator.origin
        origin_city = coordinator.origin_city
        dest = coordinator.destination
        dest_city = coordinator.destination_city
        provider = coordinator.provider

        self._attr_unique_id = f"{provider}_trip_{origin_city}_{origin}_{dest_city}_{dest}".lower().replace(" ", "_")
        self._attr_name = None  # device name IS the entity name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=f"{origin}, {origin_city} → {dest}, {dest_city}",
            manufacturer=f"{provider.upper()} Public Transport",
            model="Trip Planner",
        )

        # Listen to options updates — without this a changed walking time or
        # scan interval only took effect after a restart.
        self._config_entry.async_on_unload(self._config_entry.add_update_listener(self._async_update_listener))

    async def _async_update_listener(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Handle options update."""
        self.coordinator.walking_time = config_entry.options.get(
            CONF_WALKING_TIME,
            config_entry.data.get(CONF_WALKING_TIME, DEFAULT_WALKING_TIME),
        )
        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        self.coordinator.update_interval = timedelta(seconds=scan_interval)
        self.coordinator.line_filter = _trip_line_filter(config_entry)
        self.coordinator.transport_types = _trip_transport_types(config_entry)

        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Restore the last trip so the sensor isn't blank right after a restart.

        Only used while the coordinator has no data yet (``data is None``); a
        valid empty result (``[]``) still shows "No connections" rather than a
        stale connection.
        """
        await super().async_added_to_hass()
        if self.coordinator.data is not None:
            return
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._restored_state = last_state.state
            self._restored_attributes = {
                key: value for key, value in last_state.attributes.items() if key not in _RESTORE_SKIP_ATTRS
            }
            self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the next trip as state."""
        journeys = self.coordinator.data
        if journeys is None and self._restored_state is not None:
            return self._restored_state
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
        if journeys is None and self._restored_attributes:
            return self._restored_attributes
        if not journeys:
            return {}

        best = journeys[0]
        attrs = {
            "departure": best.get("departure"),
            "arrival": best.get("arrival"),
            "departure_timestamp": best.get("departure_timestamp"),
            "arrival_timestamp": best.get("arrival_timestamp"),
            "in_minutes": _minutes_until(best),
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
                    "departure_timestamp": j.get("departure_timestamp"),
                    "arrival_timestamp": j.get("arrival_timestamp"),
                    "in_minutes": _minutes_until(j),
                    "duration_minutes": j.get("duration_minutes"),
                    "transfers": j.get("transfers"),
                    "transfer_risk": j.get("transfer_risk"),
                }
                for j in journeys[1:4]  # Next 3 alternatives
            ]

        return attrs


def _minutes_until(journey: Dict[str, Any]) -> Optional[int]:
    """Minutes from now until a journey departs (None when it has no timestamp).

    Counts down to the start of the journey — including an initial walk to the
    platform, because that is when the traveller has to set off. Rounds down, so
    a departure that has just passed reads as ``-1`` rather than a hopeful ``0``.
    """
    departure = dt_util.parse_datetime(journey.get("departure_timestamp") or "")
    if departure is None:
        return None
    return int((departure - dt_util.now()).total_seconds() // 60)
