"""NTA (National Transport Authority, Ireland) provider implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

import aiohttp
from aiohttp import ClientConnectorError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import API_BASE_URL_NTA_GTFSR, NTA_TRANSPORTATION_TYPES, PROVIDER_NTA_IE
from ..data_models import UnifiedDeparture
from ..parsers import parse_departure_generic
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)


class NTAProvider(BaseProvider):
    """NTA (National Transport Authority, Ireland) provider."""

    def __init__(self, hass, api_key: Optional[str] = None, api_key_secondary: Optional[str] = None):
        """Initialize NTA provider."""
        super().__init__(hass, api_key=api_key, api_key_secondary=api_key_secondary)

    @property
    def provider_id(self) -> str:
        """Return the provider identifier."""
        return PROVIDER_NTA_IE

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name."""
        return "NTA (Ireland)"

    @property
    def requires_api_key(self) -> bool:
        """Return True if this provider requires an API key."""
        return True

    def get_timezone(self) -> str:
        """Return the timezone for NTA."""
        return "Europe/Dublin"

    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        pass

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departure data from NTA GTFS-RT API."""
        if not self.api_key:
            _LOGGER.error("NTA API key is required")
            return None

        if not station_id:
            _LOGGER.error("NTA requires a station ID (stop_id)")
            return None

        url = f"{API_BASE_URL_NTA_GTFSR}/v2/TripUpdates"
        params = {"format": "json"}
        session = async_get_clientsession(self.hass)

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant NTA Integration)",
            "x-api-key": self.api_key,
        }

        max_retries = 3
        current_api_key = self.api_key
        for attempt in range(1, max_retries + 1):
            try:
                headers["x-api-key"] = current_api_key

                async with session.get(
                    url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        try:
                            json_data = await response.json()

                            if not isinstance(json_data, dict):
                                _LOGGER.warning("NTA API returned non-dict response: %s", type(json_data))
                                return None

                            entities = json_data.get("entity", [])
                            if not isinstance(entities, list):
                                _LOGGER.debug("NTA API response missing or invalid 'entity' field")
                                return {"stopEvents": []}

                            entity_count = len(entities)
                            if entity_count == 0:
                                _LOGGER.debug("NTA API returned empty entities list")
                                return {"stopEvents": []}

                            _LOGGER.info(
                                "NTA API returned %d entities (processing for stop %s)", entity_count, station_id
                            )

                            # Filter entities for our stop_id and convert to stopEvents format
                            stop_events = []
                            target_stop_id = station_id
                            max_departures = departures_limit * 3
                            processed_entities = 0

                            for entity in entities:
                                if not isinstance(entity, dict):
                                    continue

                                trip_update = entity.get("trip_update")
                                if not isinstance(trip_update, dict):
                                    continue

                                stop_time_updates = trip_update.get("stop_time_update", [])
                                if not isinstance(stop_time_updates, list) or len(stop_time_updates) == 0:
                                    continue

                                # Early filter: check if any stop_time_update matches our stop_id
                                matching_stop_time = None
                                for stop_time_update in stop_time_updates:
                                    if not isinstance(stop_time_update, dict):
                                        continue
                                    stop_id = stop_time_update.get("stop_id")
                                    if stop_id == target_stop_id:
                                        matching_stop_time = stop_time_update
                                        break

                                if matching_stop_time is None:
                                    continue

                                trip = trip_update.get("trip", {})
                                if not isinstance(trip, dict):
                                    continue

                                stop_time_update = matching_stop_time

                                route_id = trip.get("route_id", "")
                                trip_id = trip.get("trip_id", "")
                                stop_id = stop_time_update.get("stop_id", target_stop_id)

                                # Extract route info from route_id (without GTFS Static)
                                # Route IDs in NTA often contain the route number
                                route_short_name = route_id.split("_")[0] if route_id else ""

                                # Default route type to bus (3) - can be improved later
                                route_type = 3
                                # Try to detect Luas (tram) from route_id
                                if route_short_name and route_short_name.lower() in ["red", "green", "luas"]:
                                    route_type = 0  # Tram/Light rail for Luas

                                # Get delay (in seconds)
                                departure = stop_time_update.get("departure", {})
                                arrival = stop_time_update.get("arrival", {})
                                delay_seconds = departure.get("delay") or arrival.get("delay") or 0

                                # Get scheduled time
                                schedule_relationship = stop_time_update.get("schedule_relationship", "SCHEDULED")
                                if schedule_relationship in ["CANCELED", "SKIPPED"]:
                                    continue

                                # Use route_id as destination placeholder (without GTFS Static)
                                destination = route_short_name or "Unknown"

                                # Calculate time from GTFS-RT data
                                now = dt_util.now()

                                departure_time = departure.get("time")
                                arrival_time = arrival.get("time")

                                if departure_time:
                                    try:
                                        planned_time = datetime.fromtimestamp(departure_time, tz=now.tzinfo)
                                        estimated_time = planned_time + timedelta(seconds=delay_seconds)
                                    except (ValueError, OSError):
                                        planned_time = now
                                        estimated_time = now + timedelta(seconds=delay_seconds)
                                elif arrival_time:
                                    try:
                                        planned_time = datetime.fromtimestamp(arrival_time, tz=now.tzinfo)
                                        estimated_time = planned_time + timedelta(seconds=delay_seconds)
                                    except (ValueError, OSError):
                                        planned_time = now
                                        estimated_time = now + timedelta(seconds=delay_seconds)
                                else:
                                    planned_time = now
                                    estimated_time = now + timedelta(seconds=delay_seconds)

                                # Format times
                                planned_time_str = planned_time.strftime("%Y-%m-%dT%H:%M:%S%z")
                                estimated_time_str = estimated_time.strftime("%Y-%m-%dT%H:%M:%S%z")

                                # Get platform
                                platform = (
                                    stop_time_update.get("platform_code") or stop_time_update.get("platform") or ""
                                )

                                stop_event = {
                                    "departureTimePlanned": planned_time_str,
                                    "departureTimeEstimated": estimated_time_str,
                                    "transportation": {
                                        "number": route_short_name,
                                        "description": "",
                                        "destination": {"name": destination},
                                        "product": {"class": route_type},
                                    },
                                    "platform": {"name": platform},
                                    "realtimeStatus": ["MONITORED"] if delay_seconds != 0 else [],
                                    "route_id": route_id,
                                    "trip_id": trip_id,
                                    "stop_id": stop_id,
                                    "delay_seconds": delay_seconds,
                                }
                                stop_events.append(stop_event)
                                processed_entities += 1

                                if len(stop_events) >= max_departures:
                                    break

                            _LOGGER.info(
                                "NTA: Processed %d/%d entities, found %d departures for stop %s",
                                processed_entities,
                                entity_count,
                                len(stop_events),
                                target_stop_id,
                            )
                            return {"stopEvents": stop_events}

                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.warning("NTA API returned invalid JSON: %s", e)
                            return None
                        except Exception as e:
                            _LOGGER.warning("NTA API JSON parsing failed: %s", e, exc_info=True)
                            return None
                    elif response.status == 404:
                        _LOGGER.warning("NTA API endpoint not found (404)")
                        return None
                    elif response.status == 401:
                        # Try Secondary Key as fallback if available
                        if self.api_key_secondary and current_api_key == self.api_key:
                            _LOGGER.info("NTA Primary API key failed (401), trying Secondary key...")
                            current_api_key = self.api_key_secondary
                            continue
                        _LOGGER.warning("NTA API authentication failed (401) - check API key(s)")
                        return None
                    elif response.status >= 500:
                        _LOGGER.warning(
                            "NTA API server error (status %s) on attempt %d/%d",
                            response.status,
                            attempt,
                            max_retries,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
                        return None
                    else:
                        _LOGGER.warning(
                            "NTA API returned status %s on attempt %d/%d", response.status, attempt, max_retries
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue

            except asyncio.TimeoutError:
                _LOGGER.warning("NTA API timeout on attempt %d/%d", attempt, max_retries)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
            except ClientConnectorError as e:
                _LOGGER.warning("NTA API connection error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
            except Exception as e:
                _LOGGER.warning("NTA API attempt %d/%d failed: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from NTA GTFS-RT API response."""
        transportation = stop.get("transportation", {})
        product = transportation.get("product", {})
        route_type = product.get("class", 3)
        transport_type = NTA_TRANSPORTATION_TYPES.get(route_type, "bus")

        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=lambda t: transport_type,
            get_platform_fn=lambda s: (
                s.get("platform", {}).get("name", "")
                if isinstance(s.get("platform"), dict)
                else str(s.get("platform", ""))
            ),
            get_realtime_fn=lambda s, est, plan: "MONITORED" in s.get("realtimeStatus", []),
        )

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops - not supported without GTFS Static.

        Users need to enter the stop_id directly.
        """
        _LOGGER.warning("NTA stop search is not available without GTFS Static data. Please enter the stop_id directly.")
        return []
