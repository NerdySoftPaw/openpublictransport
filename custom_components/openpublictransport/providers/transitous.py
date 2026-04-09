"""Transitous (MOTIS2) provider implementation.

Uses the Transitous API (api.transitous.org) powered by MOTIS2.
No API key required. Covers public transport worldwide via GTFS data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import PROVIDER_TRANSITOUS
from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://api.transitous.org/api"
USER_AGENT = "OpenPublicTransport/1.0 (github.com/NerdySoftPaw/openpublictransport)"

MODE_MAPPING = {
    "HIGHSPEED_RAIL": "train",
    "LONG_DISTANCE": "train",
    "COACH": "bus",
    "NIGHT_RAIL": "train",
    "REGIONAL_FAST_RAIL": "train",
    "REGIONAL_RAIL": "train",
    "SUBURBAN": "train",
    "SUBWAY": "subway",
    "TRAM": "tram",
    "BUS": "bus",
    "FERRY": "ferry",
    "ODM": "bus",
    "FLEXIBLE": "bus",
    "FUNICULAR": "train",
    "GONDOLA": "train",
    "CABLE_CAR": "train",
    "MONORAIL": "train",
    "TROLLEYBUS": "bus",
}


class TransitousProvider(BaseProvider):
    """Transitous provider — worldwide public transport via MOTIS2."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_TRANSITOUS

    @property
    def provider_name(self) -> str:
        return "Transitous (Weltweit)"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departures from Transitous MOTIS2 API."""
        if not station_id:
            _LOGGER.warning("Transitous provider requires a station_id")
            return None

        url = f"{API_BASE}/v5/stoptimes?stopId={quote(station_id, safe='')}&n={departures_limit}"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        return None
                    return {"stopEvents": data.get("stopTimes", [])}
                else:
                    _LOGGER.warning("Transitous API returned status %s", response.status)
        except aiohttp.ClientError as e:
            _LOGGER.warning("Transitous API request failed: %s", e)
        except Exception as e:
            _LOGGER.warning("Transitous API error: %s", e)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single MOTIS2 stopTime."""
        try:
            place = stop.get("place", {})
            dep_str = place.get("departure") or place.get("scheduledDeparture")
            sched_str = place.get("scheduledDeparture")

            if not dep_str:
                return None

            dep_dt = dt_util.parse_datetime(dep_str)
            sched_dt = dt_util.parse_datetime(sched_str) if sched_str else dep_dt
            if not dep_dt or not sched_dt:
                return None

            # Use stop-specific timezone if available
            stop_tz_str = place.get("tz")
            if stop_tz_str:
                try:
                    stop_tz = ZoneInfo(stop_tz_str)
                except (KeyError, ValueError):
                    stop_tz = tz
            else:
                stop_tz = tz

            dep_local = dep_dt.astimezone(stop_tz)
            sched_local = sched_dt.astimezone(stop_tz)

            delay_minutes = int((dep_local - sched_local).total_seconds() / 60)

            mode = stop.get("mode", "")
            transport_type = MODE_MAPPING.get(mode, "unknown")

            line = stop.get("routeShortName") or stop.get("displayName", "")
            destination = stop.get("headsign", "Unknown")

            track = place.get("track", "")
            sched_track = place.get("scheduledTrack", "")
            platform_changed = bool(track and sched_track and track != sched_track)

            time_diff = dep_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            is_realtime = stop.get("realTime", False)
            is_cancelled = stop.get("cancelled", False) or stop.get("tripCancelled", False)

            # Build notices
            notices = []
            if is_cancelled:
                notices.append("Fällt aus / Cancelled")

            agency = stop.get("agencyName", "")

            return UnifiedDeparture(
                line=line,
                destination=destination,
                departure_time=dep_local.strftime("%H:%M"),
                planned_time=sched_local.strftime("%H:%M"),
                delay=delay_minutes,
                platform=track,
                transportation_type=transport_type,
                is_realtime=is_realtime,
                minutes_until_departure=minutes_until,
                departure_time_obj=dep_local,
                description=stop.get("routeLongName"),
                agency=agency if agency else None,
                notices=notices if notices else None,
                planned_platform=sched_track if platform_changed else None,
                platform_changed=platform_changed,
            )
        except Exception as e:
            _LOGGER.debug("Error parsing Transitous departure: %s", e)
            return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using Transitous geocode API."""
        url = f"{API_BASE}/v1/geocode?text={quote(search_term, safe='')}&type=STOP"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        return []

                    results = []
                    for location in data:
                        if not isinstance(location, dict):
                            continue
                        name = location.get("name", "")
                        results.append(
                            {
                                "id": location.get("id", ""),
                                "name": name,
                                "place": "",
                                "area_type": "stop",
                            }
                        )
                    return results
                else:
                    _LOGGER.error("Transitous API returned status %s", response.status)
        except Exception as e:
            _LOGGER.error("Error searching Transitous stops: %s", e)

        return []
