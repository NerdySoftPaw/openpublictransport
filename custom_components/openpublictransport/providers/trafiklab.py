"""Trafiklab (Sweden) provider implementation."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from aiohttp import ClientConnectorError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import API_BASE_URL_TRAFIKLAB, PROVIDER_TRAFIKLAB_SE, TRAFIKLAB_TRANSPORTATION_TYPES
from ..data_models import UnifiedDeparture
from ..parsers import parse_departure_generic
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)


class TrafiklabProvider(BaseProvider):
    """Trafiklab (Sweden) provider."""

    @property
    def provider_id(self) -> str:
        """Return the provider identifier."""
        return PROVIDER_TRAFIKLAB_SE

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name."""
        return "Trafiklab (Sweden)"

    @property
    def requires_api_key(self) -> bool:
        """Return True if this provider requires an API key."""
        return True

    def get_timezone(self) -> str:
        """Return the timezone for Trafiklab."""
        return "Europe/Stockholm"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departure data from Trafiklab API."""
        if not self.api_key:
            _LOGGER.error("Trafiklab API key is required")
            return None

        if not station_id:
            _LOGGER.error("Trafiklab requires a station ID")
            return None

        url = f"{API_BASE_URL_TRAFIKLAB}/departures/{station_id}"
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
                            if not isinstance(json_data, dict):
                                _LOGGER.warning("Trafiklab API returned non-dict response: %s", type(json_data))
                                return None

                            if "departures" not in json_data:
                                _LOGGER.debug("Trafiklab API response missing 'departures' field")
                                return {"stopEvents": []}

                            # Convert Trafiklab format to our expected format
                            departures = json_data.get("departures", [])
                            _LOGGER.debug("Trafiklab API returned %d departures", len(departures))
                            stop_events = []

                            # Get Stockholm timezone offset once
                            stockholm_tz = dt_util.get_time_zone("Europe/Stockholm")
                            offset_formatted = "+01:00"  # Default to CET
                            if stockholm_tz:
                                now_stockholm = datetime.now(stockholm_tz)
                                offset = now_stockholm.strftime("%z")
                                offset_formatted = f"{offset[:3]}:{offset[3:]}"  # +0100 -> +01:00

                            for dep in departures:
                                if not isinstance(dep, dict):
                                    continue

                                scheduled_time = dep.get("scheduled")
                                realtime_time = dep.get("realtime")
                                route = dep.get("route") or {}
                                platform_data = dep.get("scheduled_platform") or dep.get("realtime_platform") or {}
                                transport_mode = route.get("transport_mode", "BUS") if route else "BUS"

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
                                        "product": {"class": 0},
                                    },
                                    "platform": {"name": platform_data.get("designation", "") if platform_data else ""},
                                    "realtimeStatus": ["MONITORED"] if dep.get("is_realtime") else [],
                                    "transportMode": transport_mode,
                                }
                                stop_events.append(stop_event)

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
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
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
            except ClientConnectorError as e:
                _LOGGER.warning("Trafiklab API connection error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
            except Exception as e:
                _LOGGER.warning("Attempt %d/%d failed: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from Trafiklab API response."""
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

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using Trafiklab API."""
        if not self.api_key:
            _LOGGER.error("Trafiklab API key is required for stop search")
            return []

        encoded_search = quote(search_term, safe="")
        url = f"{API_BASE_URL_TRAFIKLAB}/stops/name/{encoded_search}"
        params = {"key": self.api_key}
        session = async_get_clientsession(self.hass)

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.error("Invalid JSON response from Trafiklab API: %s", e)
                            if attempt < max_retries:
                                await asyncio.sleep(2**attempt)
                                continue
                            return []

                        if not isinstance(data, dict):
                            _LOGGER.error("Trafiklab API returned non-dict response: %s", type(data))
                            if attempt < max_retries:
                                await asyncio.sleep(2**attempt)
                                continue
                            return []

                        stop_groups = data.get("stop_groups", [])
                        results = []

                        for stop_group in stop_groups:
                            if not isinstance(stop_group, dict):
                                continue

                            stops = stop_group.get("stops", [])
                            place = None
                            if stops and isinstance(stops[0], dict):
                                stop_name = stop_group.get("name", "")
                                place = stop_name.split(",")[-1].strip() if "," in stop_name else None

                            result = {
                                "id": stop_group.get("id", ""),
                                "name": stop_group.get("name", ""),
                                "place": place or "",
                                "area_type": stop_group.get("area_type", ""),
                                "transport_modes": stop_group.get("transport_modes", []),
                            }
                            results.append(result)

                        return results
                    elif response.status == 401:
                        _LOGGER.error("Trafiklab API authentication failed (401) - check API key")
                        return []
                    elif response.status == 404:
                        _LOGGER.warning("Trafiklab API endpoint not found (404)")
                        return []
                    elif response.status >= 500:
                        _LOGGER.warning(
                            "Trafiklab API server error (status %s) on attempt %d/%d",
                            response.status,
                            attempt,
                            max_retries,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
                    else:
                        _LOGGER.warning(
                            "Trafiklab API returned status %s on attempt %d/%d", response.status, attempt, max_retries
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(2**attempt)
                            continue
            except asyncio.TimeoutError:
                _LOGGER.error("Trafiklab API request timeout")
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
            except Exception as e:
                _LOGGER.error("Error searching stops: %s", e, exc_info=True)
                if attempt < max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return []
