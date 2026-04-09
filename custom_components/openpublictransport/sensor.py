import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

import aiohttp
from aiohttp import ClientConnectorError
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL_HVV,
    API_BASE_URL_KVV,
    API_BASE_URL_NTA_GTFSR,
    API_BASE_URL_TRAFIKLAB,
    API_BASE_URL_VRR,
    API_RATE_LIMIT_PER_DAY,
    CONF_DEPARTURES,
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
    HVV_TRANSPORTATION_TYPES,
    KVV_TRANSPORTATION_TYPES,
    NTA_TRANSPORTATION_TYPES,
    PROVIDER_ENTITY_PICTURES,
    PROVIDER_HVV,
    PROVIDER_KVV,
    PROVIDER_NTA_IE,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VRR,
    TRAFIKLAB_TRANSPORTATION_TYPES,
    TRANSPORTATION_TYPES,
)
from .data_models import UnifiedDeparture
from .parsers import parse_departure_generic
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
        if self.provider_instance:
            return await self.provider_instance.fetch_departures(
                self.station_id, self.place_dm, self.name_dm, self.departures_limit
            )

        # Fallback to old implementation if provider not found
        _LOGGER.warning("Provider instance not found, using fallback for %s", self.provider)
        if self.provider == PROVIDER_VRR:
            base_url = API_BASE_URL_VRR
        elif self.provider == PROVIDER_KVV:
            base_url = API_BASE_URL_KVV
        elif self.provider == PROVIDER_HVV:
            base_url = API_BASE_URL_HVV
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        if self.station_id:
            params = (
                f"outputFormat=RapidJSON&"
                f"stateless=1&"
                f"type_dm=any&"
                f"name_dm={self.station_id}&"
                f"mode=direct&"
                f"useRealtime=1&"
                f"limit={self.departures_limit}"
            )
        else:
            params = (
                f"outputFormat=RapidJSON&"
                f"place_dm={self.place_dm}&"
                f"type_dm=stop&"
                f"name_dm={self.name_dm}&"
                f"mode=direct&"
                f"useRealtime=1&"
                f"limit={self.departures_limit}"
            )

        url = f"{base_url}?{params}"
        session = async_get_clientsession(self.hass)

        headers = {"User-Agent": f"Mozilla/5.0 (compatible; HomeAssistant {self.provider.upper()} Integration)"}

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            json_data = await response.json()
                            # Validate response structure
                            if not isinstance(json_data, dict):
                                _LOGGER.warning(
                                    "%s API returned non-dict response: %s", self.provider.upper(), type(json_data)
                                )
                                return None

                            # Validate that response contains expected data
                            if "stopEvents" not in json_data:
                                _LOGGER.debug("%s API response missing 'stopEvents' field", self.provider.upper())
                                # Return empty structure instead of None to avoid errors
                                return {"stopEvents": []}

                            return json_data
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.warning("%s API returned invalid JSON: %s", self.provider.upper(), e)
                            return None
                        except Exception as e:
                            _LOGGER.warning("%s API JSON parsing failed: %s", self.provider.upper(), e)
                            return None
                    elif response.status == 404:
                        _LOGGER.warning("%s API endpoint not found (404)", self.provider.upper())
                        return None
                    elif response.status >= 500:
                        _LOGGER.warning("%s API server error (status %s)", self.provider.upper(), response.status)
                    else:
                        _LOGGER.warning("%s API returned status %s", self.provider.upper(), response.status)

            except asyncio.TimeoutError:
                _LOGGER.warning("%s API timeout on attempt %s", self.provider.upper(), attempt)
            except Exception as e:
                _LOGGER.warning("Attempt %s failed: %s", attempt, e)

            if attempt < max_retries:
                await asyncio.sleep(2**attempt)

        return None

    async def _fetch_departures_trafiklab(self) -> Optional[Dict[str, Any]]:
        """Fetch departure data from Trafiklab API."""
        if not self.api_key:
            _LOGGER.error("Trafiklab API key is required")
            return None

        if not self.station_id:
            _LOGGER.error("Trafiklab requires a station ID")
            return None

        url = f"{API_BASE_URL_TRAFIKLAB}/departures/{self.station_id}"
        params = {"key": self.api_key}
        session = async_get_clientsession(self.hass)

        headers = {"User-Agent": "Mozilla/5.0 (compatible; HomeAssistant Trafiklab Integration)"}

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(
                    url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        try:
                            json_data = await response.json()
                            # Validate response structure
                            if not isinstance(json_data, dict):
                                _LOGGER.warning("Trafiklab API returned non-dict response: %s", type(json_data))
                                return None

                            # Trafiklab API returns "departures" not "stopEvents"
                            # We'll normalize it to match our expected structure
                            if "departures" not in json_data:
                                _LOGGER.debug("Trafiklab API response missing 'departures' field")
                                return {"stopEvents": []}

                            # Convert Trafiklab format to our expected format
                            departures = json_data.get("departures", [])
                            _LOGGER.debug("Trafiklab API returned %d departures", len(departures))
                            stop_events = []

                            # Get Stockholm timezone offset once (not for each departure)
                            stockholm_tz = dt_util.get_time_zone("Europe/Stockholm")
                            offset_formatted = "+01:00"  # Default to CET
                            if stockholm_tz:
                                now_stockholm = datetime.now(stockholm_tz)
                                offset = now_stockholm.strftime("%z")
                                offset_formatted = f"{offset[:3]}:{offset[3:]}"  # +0100 -> +01:00

                            for dep in departures:
                                # Skip invalid entries
                                if not isinstance(dep, dict):
                                    continue

                                # Map Trafiklab structure to our stopEvents format
                                # Trafiklab uses: scheduled, realtime, route.designation, route.destination.name
                                scheduled_time = dep.get("scheduled")
                                realtime_time = dep.get("realtime")
                                route = dep.get("route") or {}  # Handle None
                                platform_data = dep.get("scheduled_platform") or dep.get("realtime_platform") or {}
                                transport_mode = route.get("transport_mode", "BUS") if route else "BUS"

                                # Get destination safely (handle None)
                                destination_obj = route.get("destination") if route else None
                                destination_name = (
                                    destination_obj.get("name", "Unknown")
                                    if isinstance(destination_obj, dict)
                                    else "Unknown"
                                )

                                # Trafiklab returns time without timezone, it's in local Swedish time
                                if scheduled_time and "+" not in scheduled_time and "Z" not in scheduled_time:
                                    scheduled_time = f"{scheduled_time}{offset_formatted}"
                                if realtime_time and "+" not in realtime_time and "Z" not in realtime_time:
                                    realtime_time = f"{realtime_time}{offset_formatted}"

                                stop_event = {
                                    "departureTimePlanned": scheduled_time,
                                    "departureTimeEstimated": realtime_time or scheduled_time,
                                    "transportation": {
                                        "number": route.get("designation", "") if route else "",
                                        "description": (
                                            (route.get("name") or route.get("direction", "")) if route else ""
                                        ),
                                        "destination": {"name": destination_name},
                                        "product": {"class": 0},  # Will be mapped from transportMode
                                    },
                                    "platform": {"name": platform_data.get("designation", "") if platform_data else ""},
                                    "realtimeStatus": ["MONITORED"] if dep.get("is_realtime") else [],
                                    "transportMode": transport_mode,  # Trafiklab specific (TRAIN, BUS, etc.)
                                }
                                stop_events.append(stop_event)
                                _LOGGER.debug(
                                    "Trafiklab departure: Line %s to %s at %s (mode: %s)",
                                    route.get("designation") if route else "?",
                                    destination_name,
                                    scheduled_time,
                                    transport_mode,
                                )

                            return {"stopEvents": stop_events}
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.warning("Trafiklab API returned invalid JSON: %s", e)
                            return None
                        except Exception as e:
                            _LOGGER.warning("Trafiklab API JSON parsing failed: %s", e)
                            return None
                    elif response.status == 404:
                        _LOGGER.warning("Trafiklab API endpoint not found (404)")
                        return None
                    elif response.status == 401:
                        _LOGGER.warning("Trafiklab API authentication failed (401) - check API key")
                        return None
                    elif response.status >= 500:
                        _LOGGER.warning(
                            "Trafiklab API server error (status %s) on attempt %d/%d",
                            response.status,
                            attempt,
                            max_retries,
                        )
                        # Retry on server errors
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
                        _LOGGER.error(
                            "Trafiklab API server error (status %s) after %d attempts. "
                            "The Trafiklab service may be temporarily unavailable. Please try again later.",
                            response.status,
                            max_retries,
                        )
                        return None
                    else:
                        _LOGGER.warning(
                            "Trafiklab API returned status %s on attempt %d/%d", response.status, attempt, max_retries
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue

            except asyncio.TimeoutError:
                _LOGGER.warning("Trafiklab API timeout on attempt %d/%d", attempt, max_retries)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                _LOGGER.error("Trafiklab API request timeout after %d attempts", max_retries)
            except ClientConnectorError as e:
                _LOGGER.warning("Trafiklab API connection error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                _LOGGER.error("Trafiklab API connection failed after %d attempts: %s", max_retries, e)
            except Exception as e:
                _LOGGER.warning("Attempt %d/%d failed: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return None

    async def _fetch_departures_nta(self) -> Optional[Dict[str, Any]]:
        """Fetch departure data from NTA GTFS-RT API."""
        if not self.api_key:
            _LOGGER.error("NTA API key is required")
            return None

        if not self.station_id:
            _LOGGER.error("NTA requires a station ID (stop_id)")
            return None

        url = f"{API_BASE_URL_NTA_GTFSR}/v2/TripUpdates"
        params = {"format": "json"}
        session = async_get_clientsession(self.hass)

        # Use Primary Key in header (preferred method)
        # If Primary Key fails, Secondary Key can be used as fallback
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant NTA Integration)",
            "x-api-key": self.api_key,
        }

        max_retries = 3
        current_api_key = self.api_key
        for attempt in range(1, max_retries + 1):
            try:
                # Update header with current API key (Primary or Secondary as fallback)
                headers["x-api-key"] = current_api_key

                async with session.get(
                    url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        try:
                            # Stream JSON parsing for large responses (more memory efficient)
                            json_data = await response.json()

                            # Validate response structure early
                            if not isinstance(json_data, dict):
                                _LOGGER.warning("NTA API returned non-dict response: %s", type(json_data))
                                return None

                            # GTFS-RT structure: {header: {...}, entity: [...]}
                            entities = json_data.get("entity", [])
                            if not isinstance(entities, list):
                                _LOGGER.debug("NTA API response missing or invalid 'entity' field")
                                return {"stopEvents": []}

                            entity_count = len(entities)
                            if entity_count == 0:
                                _LOGGER.debug("NTA API returned empty entities list")
                                return {"stopEvents": []}

                            _LOGGER.info(
                                "NTA API returned %d entities (processing for stop %s)", entity_count, self.station_id
                            )

                            # Filter entities for our stop_id and convert to stopEvents format
                            stop_events = []
                            target_stop_id = self.station_id
                            max_departures = self.departures_limit * 3  # Get more than needed for filtering

                            # Early exit optimization: check if stop_time_updates contain our stop_id
                            # before processing the entire entity
                            processed_entities = 0
                            for entity in entities:
                                if not isinstance(entity, dict):
                                    continue

                                trip_update = entity.get("trip_update")
                                if not isinstance(trip_update, dict):
                                    continue

                                # Quick check: does this entity have stop_time_updates for our stop?
                                stop_time_updates = trip_update.get("stop_time_update", [])
                                if not isinstance(stop_time_updates, list) or len(stop_time_updates) == 0:
                                    continue

                                # Early filter: check if any stop_time_update matches our stop_id
                                # before processing trip info (saves CPU)
                                matching_stop_time = None
                                for stop_time_update in stop_time_updates:
                                    if not isinstance(stop_time_update, dict):
                                        continue
                                    stop_id = stop_time_update.get("stop_id")
                                    if stop_id == target_stop_id:
                                        matching_stop_time = stop_time_update
                                        break  # Found match, no need to check more

                                # Skip this entity if no matching stop_time_update found
                                if matching_stop_time is None:
                                    continue

                                # Only process trip info if we have a matching stop
                                trip = trip_update.get("trip", {})
                                if not isinstance(trip, dict):
                                    continue

                                # Use the matching stop_time_update we already found
                                stop_time_update = matching_stop_time

                                # Found a departure for our stop
                                route_id = trip.get("route_id", "")
                                trip_id = trip.get("trip_id", "")
                                stop_id = stop_time_update.get(
                                    "stop_id", target_stop_id
                                )  # Use stop_id from update if available

                                # Extract route info from route_id (without GTFS Static)
                                route_short_name = route_id.split("_")[0] if route_id else ""
                                route_type = 3  # Default to bus
                                # Try to detect Luas (tram) from route_id
                                if route_short_name and route_short_name.lower() in ["red", "green", "luas"]:
                                    route_type = 0  # Tram/Light rail for Luas

                                # Get delay (in seconds)
                                departure = stop_time_update.get("departure", {})
                                arrival = stop_time_update.get("arrival", {})
                                delay_seconds = departure.get("delay") or arrival.get("delay") or 0

                                # Get scheduled time
                                schedule_relationship = stop_time_update.get("schedule_relationship", "SCHEDULED")

                                # Skip canceled trips
                                if schedule_relationship in ["CANCELED", "SKIPPED"]:
                                    continue

                                # Use route_short_name as destination placeholder (without GTFS Static)
                                destination = route_short_name or "Unknown"

                                # Calculate time from GTFS-RT data
                                now = dt_util.now()

                                # Get time from departure/arrival if available
                                departure_time = departure.get("time")
                                arrival_time = arrival.get("time")

                                if departure_time:
                                    # POSIX timestamp
                                    try:
                                        planned_time = datetime.fromtimestamp(departure_time, tz=now.tzinfo)
                                        estimated_time = planned_time + timedelta(seconds=delay_seconds)
                                    except (ValueError, OSError):
                                        # Fallback to current time + delay
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
                                    # No time field, estimate from delay
                                    planned_time = now
                                    estimated_time = now + timedelta(seconds=delay_seconds)

                                # Format times
                                planned_time_str = planned_time.strftime("%Y-%m-%dT%H:%M:%S%z")
                                estimated_time_str = estimated_time.strftime("%Y-%m-%dT%H:%M:%S%z")

                                # Map route_type to transport type for logging
                                transport_type_mapped = NTA_TRANSPORTATION_TYPES.get(route_type, "bus")
                                _LOGGER.debug(
                                    "NTA Departure: line=%s, destination=%s, route_type=%d -> transport_type=%s",
                                    route_short_name,
                                    destination,
                                    route_type,
                                    transport_type_mapped,
                                )

                                # Try to get platform from stop_time_update (GTFS-RT extension)
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

                                # Early exit if we have enough departures
                                if len(stop_events) >= max_departures:
                                    _LOGGER.debug(
                                        "NTA: Found %d departures (limit reached), stopping early",
                                        len(stop_events),
                                    )
                                    break

                                # Break outer loop if we have enough
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
                            continue  # Retry with Secondary key
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
                        _LOGGER.error(
                            "NTA API server error (status %s) after %d attempts",
                            response.status,
                            max_retries,
                        )
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
                _LOGGER.error("NTA API request timeout after %d attempts", max_retries)
            except ClientConnectorError as e:
                _LOGGER.warning("NTA API connection error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
                _LOGGER.error("NTA API connection failed after %d attempts: %s", max_retries, e)
            except Exception as e:
                _LOGGER.warning("NTA API attempt %d/%d failed: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VRR/KVV sensor from a config entry."""
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
        """Process the departure data from VRR/KVV/HVV API.

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
        # Use appropriate timezone based on provider
        provider = self.coordinator.provider
        if self.coordinator.provider_instance:
            tz = dt_util.get_time_zone(self.coordinator.provider_instance.get_timezone())
        elif provider == PROVIDER_TRAFIKLAB_SE:
            tz = dt_util.get_time_zone("Europe/Stockholm")
        elif provider == PROVIDER_NTA_IE:
            tz = dt_util.get_time_zone("Europe/Dublin")
        elif provider == PROVIDER_HVV:
            tz = dt_util.get_time_zone("Europe/Berlin")
        else:
            tz = dt_util.get_time_zone("Europe/Berlin")
        now = dt_util.now()

        # Cache transportation_types to avoid repeated lookups
        transport_types_set = set(self.transportation_types)  # Set lookup is O(1) vs list O(n)

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
        else:
            # Fallback to old implementation
            if provider == PROVIDER_VRR:
                parse_fn = self._parse_departure_vrr
            elif provider == PROVIDER_KVV:
                parse_fn = self._parse_departure_kvv
            elif provider == PROVIDER_HVV:
                parse_fn = self._parse_departure_hvv
            elif provider == PROVIDER_TRAFIKLAB_SE:
                parse_fn = self._parse_departure_trafiklab
            elif provider == PROVIDER_NTA_IE:
                parse_fn = self._parse_departure_nta

        if parse_fn is not None:
            for stop in stop_events:
                dep = parse_fn(stop, tz, now)
                # Filter by configured transportation types (set lookup is faster)
                if dep and dep.transportation_type in transport_types_set:
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

    def _parse_departure_generic(
        self,
        stop: Dict[str, Any],
        tz: Union[ZoneInfo, Any],
        now: datetime,
        get_transport_type_fn: Callable[[Dict[str, Any]], str],
        get_platform_fn: Callable[[Dict[str, Any]], str],
        get_realtime_fn: Callable[[Dict[str, Any], Optional[str], Optional[str]], bool],
    ) -> Optional[UnifiedDeparture]:
        """Generic parser for departure data - shared logic across all providers.

        Args:
            stop: Stop event data from API
            tz: Timezone object (provider-specific)
            now: Current datetime
            get_transport_type_fn: Function to determine transportation type
            get_platform_fn: Function to extract platform information
            get_realtime_fn: Function to check if realtime data is available

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        try:
            # Validate stop data structure
            if not isinstance(stop, dict):
                _LOGGER.debug("Invalid stop data: expected dict, got %s", type(stop))
                return None

            # Get times
            planned_time_str = stop.get("departureTimePlanned")
            estimated_time_str = stop.get("departureTimeEstimated")

            if not planned_time_str:
                _LOGGER.debug("Missing departureTimePlanned in stop data")
                return None

            # Validate time strings
            if not isinstance(planned_time_str, str):
                _LOGGER.debug("Invalid departureTimePlanned: expected str, got %s", type(planned_time_str))
                return None

            # Parse times
            planned_time = dt_util.parse_datetime(planned_time_str)
            estimated_time = dt_util.parse_datetime(estimated_time_str) if estimated_time_str else planned_time

            if not planned_time:
                _LOGGER.debug("Failed to parse departureTimePlanned: %s", planned_time_str)
                return None

            # Convert to local timezone with validation
            try:
                planned_local = planned_time.astimezone(tz)
                estimated_local = estimated_time.astimezone(tz) if estimated_time else planned_local
            except (ValueError, TypeError) as e:
                _LOGGER.debug("Failed to convert timezone: %s", e)
                return None

            # Calculate delay
            delay_minutes = int((estimated_local - planned_local).total_seconds() / 60)

            # Get transportation info with validation
            transportation = stop.get("transportation", {})
            if not isinstance(transportation, dict):
                _LOGGER.debug("Invalid transportation data: expected dict, got %s", type(transportation))
                transportation = {}

            destination_obj = transportation.get("destination", {})
            if not isinstance(destination_obj, dict):
                destination_obj = {}
            destination = destination_obj.get("name", "Unknown")

            line_number = str(transportation.get("number", ""))
            description = str(transportation.get("description", ""))
            agency = stop.get("agency")  # Agency name from GTFS (NTA)

            # Determine transportation type using provider-specific function
            transport_type = get_transport_type_fn(transportation)

            # Get platform/track info using provider-specific function
            platform = get_platform_fn(stop)

            # Calculate minutes until departure
            time_diff = estimated_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            # Determine if real-time data is available using provider-specific function
            is_realtime = get_realtime_fn(stop, estimated_time_str, planned_time_str)

            return UnifiedDeparture(
                line=line_number,
                destination=destination,
                departure_time=estimated_local.strftime("%H:%M"),
                planned_time=planned_local.strftime("%H:%M"),
                delay=delay_minutes,
                platform=platform,
                transportation_type=transport_type,
                is_realtime=is_realtime,
                minutes_until_departure=minutes_until,
                departure_time_obj=estimated_local,
                description=description if description else None,
                agency=agency if agency else None,
            )

        except Exception as e:
            _LOGGER.debug("Error parsing departure: %s", e)
            return None

    def _parse_departure_vrr(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from VRR API response.

        Args:
            stop: Stop event data from VRR API
            tz: Timezone object
            now: Current datetime

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=self._determine_transport_type_vrr,
            get_platform_fn=lambda s: (s.get("platform", {}).get("name") or s.get("platformName", "")),
            get_realtime_fn=lambda s, est, plan: "MONITORED" in s.get("realtimeStatus", []),
        )

    def _parse_departure_kvv(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from KVV API response.

        Args:
            stop: Stop event data from KVV API
            tz: Timezone object
            now: Current datetime

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=lambda t: KVV_TRANSPORTATION_TYPES.get(
                t.get("product", {}).get("class", 0), "unknown"
            ),
            get_platform_fn=lambda s: (s.get("location", {}).get("disassembledName") or s.get("platformName", "")),
            get_realtime_fn=lambda s, est, plan: s.get("isRealtimeControlled", False),
        )

    def _parse_departure_hvv(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from HVV API response.

        Args:
            stop: Stop event data from HVV API
            tz: Timezone object
            now: Current datetime

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=lambda t: HVV_TRANSPORTATION_TYPES.get(
                t.get("product", {}).get("class", 0), "unknown"
            ),
            get_platform_fn=lambda s: (
                s.get("location", {}).get("properties", {}).get("platform")
                or s.get("location", {}).get("platformName", "")
            ),
            get_realtime_fn=lambda s, est, plan: est != plan if est and plan else False,
        )

    def _parse_departure_trafiklab(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from Trafiklab API response.

        Args:
            stop: Stop event data from Trafiklab API (already normalized)
            tz: Timezone object (Europe/Stockholm)
            now: Current datetime

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        # Map transportMode to our transport type
        transport_mode = stop.get("transportMode", "BUS")
        transport_type = TRAFIKLAB_TRANSPORTATION_TYPES.get(transport_mode, "bus")

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
            get_realtime_fn=lambda s, est, plan: est != plan if est and plan else False,
        )

    def _parse_departure_nta(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from NTA GTFS-RT API response.

        Args:
            stop: Stop event data from NTA API (already normalized)
            tz: Timezone object (Europe/Dublin)
            now: Current datetime

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        # Get route_type from transportation.product.class
        transportation = stop.get("transportation", {})
        product = transportation.get("product", {})
        route_type = product.get("class", 3)  # Default to bus (3)

        # Map GTFS route_type to our transport type
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

    def _determine_transport_type_vrr(self, transportation: Dict[str, Any]) -> str:
        """Determine the transportation type from VRR API data."""
        product = transportation.get("product", {})
        product_class = product.get("class", 0)

        # Map VRR product classes to our types
        type_mapping = {
            0: "train",  # High-speed trains (ICE, IC, EC)
            1: "train",  # Regional trains (RE, RB)
            2: "subway",  # U-Bahn (subway/metro)
            3: "subway",  # U-Bahn variant
            4: "tram",  # Tram/Streetcar
            5: "bus",  # City bus
            6: "bus",  # Regional bus
            7: "bus",  # Express bus
            8: "bus",  # Night bus
            9: "ferry",  # Ferry/Ship
            10: "taxi",  # Taxi
            11: "bus",  # Other/Special transport
            13: "train",  # Regionalzug (RE)
            15: "train",  # InterCity (IC)
            16: "train",  # InterCityExpress (ICE)
        }

        transport_type = type_mapping.get(product_class, "unknown")

        if product_class not in type_mapping:
            _LOGGER.debug(
                "Unknown transport class %s for line %s, defaulting to unknown",
                product_class,
                transportation.get("number", "unknown"),
            )

        return transport_type
