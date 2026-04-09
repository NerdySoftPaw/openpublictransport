"""SBB (Swiss Federal Railways) provider implementation.

Uses the Swiss public transport API at transport.opendata.ch.
No API key required. Covers all Swiss public transport.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import PROVIDER_SBB
from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://transport.opendata.ch/v1"

CATEGORY_MAPPING = {
    "ICE": "train",
    "IC": "train",
    "IR": "train",
    "EC": "train",
    "RE": "train",
    "S": "train",
    "TGV": "train",
    "RJ": "train",
    "T": "tram",
    "B": "bus",
    "NFB": "bus",
    "BUS": "bus",
    "BAT": "ferry",
    "FAE": "ferry",
    "M": "subway",
    "FUN": "train",
}


class SBBProvider(BaseProvider):
    """SBB (Swiss Federal Railways) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_SBB

    @property
    def provider_name(self) -> str:
        return "SBB (Schweiz)"

    def get_timezone(self) -> str:
        return "Europe/Zurich"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departures from Swiss transport API."""
        if station_id:
            url = f"{API_BASE}/stationboard?id={station_id}&limit={departures_limit}"
        else:
            station_name = f"{name_dm}, {place_dm}" if place_dm else name_dm
            url = f"{API_BASE}/stationboard?station={quote(station_name, safe='')}&limit={departures_limit}"

        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        return None
                    stationboard = data.get("stationboard", [])
                    return {"stopEvents": stationboard}
                else:
                    _LOGGER.warning("SBB API returned status %s", response.status)
        except aiohttp.ClientError as e:
            _LOGGER.warning("SBB API request failed: %s", e)
        except Exception as e:
            _LOGGER.warning("SBB API error: %s", e)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single Swiss transport departure."""
        try:
            stop_info = stop.get("stop", {})
            dep_str = stop_info.get("departure")
            if not dep_str:
                return None

            dep_dt = dt_util.parse_datetime(dep_str)
            if not dep_dt:
                return None

            dep_local = dep_dt.astimezone(tz)
            delay_min = stop_info.get("delay") or 0

            # Planned time = actual - delay
            from datetime import timedelta

            planned_local = dep_local - timedelta(minutes=delay_min)

            category = stop.get("category", "")
            number = stop.get("number", "")
            line = f"{category}{number}"

            transport_type = CATEGORY_MAPPING.get(category, "unknown")
            destination = stop.get("to", "Unknown")
            platform = stop_info.get("platform", "")

            time_diff = dep_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            is_realtime = stop_info.get("prognosis", {}).get("departure") is not None

            # Platform change
            prognosis_platform = stop_info.get("prognosis", {}).get("platform")
            platform_changed = bool(prognosis_platform and platform and prognosis_platform != platform)
            planned_platform = platform if platform_changed else None
            if prognosis_platform:
                platform = prognosis_platform

            return UnifiedDeparture(
                line=line,
                destination=destination,
                departure_time=dep_local.strftime("%H:%M"),
                planned_time=planned_local.strftime("%H:%M"),
                delay=delay_min,
                platform=platform,
                transportation_type=transport_type,
                is_realtime=is_realtime,
                minutes_until_departure=minutes_until,
                departure_time_obj=dep_local,
                description=stop.get("operator", ""),
                notices=None,
                planned_platform=planned_platform,
                platform_changed=platform_changed,
            )
        except Exception as e:
            _LOGGER.debug("Error parsing SBB departure: %s", e)
            return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using Swiss transport API."""
        url = f"{API_BASE}/locations?query={quote(search_term, safe='')}&type=station"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    stations = data.get("stations", [])
                    results = []
                    for station in stations:
                        if not isinstance(station, dict) or not station.get("id"):
                            continue
                        name = station.get("name", "")
                        results.append(
                            {
                                "id": str(station.get("id", "")),
                                "name": name,
                                "place": "",
                                "area_type": "stop",
                            }
                        )
                    return results
                else:
                    _LOGGER.error("SBB API returned status %s", response.status)
        except Exception as e:
            _LOGGER.error("Error searching SBB stops: %s", e)

        return []
