"""DB (Deutsche Bahn) provider implementation.

Uses the v6.db.transport.rest API (FPTF format).
No API key required. Covers all DB stations nationwide (ICE, IC, RE, RB, S-Bahn).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import PROVIDER_DB
from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://v6.db.transport.rest"

# FPTF product → our transport type
PRODUCT_MAPPING = {
    "nationalExpress": "train",  # ICE
    "national": "train",  # IC/EC
    "regionalExpress": "train",  # RE
    "regional": "train",  # RB
    "suburban": "train",  # S-Bahn
    "subway": "subway",  # U-Bahn
    "tram": "tram",
    "bus": "bus",
    "ferry": "ferry",
    "taxi": "taxi",
}


class DBProvider(BaseProvider):
    """DB (Deutsche Bahn) provider using db-rest API."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_DB

    @property
    def provider_name(self) -> str:
        return "DB (Deutsche Bahn)"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departures from DB REST API."""
        if not station_id:
            _LOGGER.warning("DB provider requires a station_id")
            return None

        url = f"{API_BASE}/stops/{station_id}/departures?results={departures_limit}&duration=120"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict) or "departures" not in data:
                        _LOGGER.warning("DB API unexpected response format")
                        return {"stopEvents": []}
                    return {"stopEvents": data["departures"]}
                else:
                    _LOGGER.warning("DB API returned status %s", response.status)
        except aiohttp.ClientError as e:
            _LOGGER.warning("DB API request failed: %s", e)
        except Exception as e:
            _LOGGER.warning("DB API error: %s", e)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single FPTF departure."""
        try:
            when_str = stop.get("when") or stop.get("plannedWhen")
            planned_str = stop.get("plannedWhen")
            if not when_str or not planned_str:
                return None

            when = dt_util.parse_datetime(when_str)
            planned = dt_util.parse_datetime(planned_str)
            if not when or not planned:
                return None

            when_local = when.astimezone(tz)
            planned_local = planned.astimezone(tz)

            delay_seconds = stop.get("delay") or 0
            delay_minutes = int(delay_seconds / 60)

            line_info = stop.get("line", {})
            line_name = line_info.get("name", "")
            product = line_info.get("product", "")
            transport_type = PRODUCT_MAPPING.get(product, "unknown")

            destination_info = stop.get("destination", {})
            destination = destination_info.get("name", stop.get("direction", "Unknown"))

            platform = stop.get("platform") or ""
            planned_platform = stop.get("plannedPlatform") or ""
            platform_changed = bool(platform and planned_platform and platform != planned_platform)

            time_diff = when_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            is_realtime = stop.get("prognosisType") is not None

            # Extract notices from remarks
            notices = []
            for remark in stop.get("remarks", []):
                if isinstance(remark, dict) and remark.get("type") == "warning":
                    text = remark.get("text") or remark.get("summary", "")
                    if text:
                        notices.append(text)

            operator = line_info.get("operator", {})
            agency = operator.get("name") if isinstance(operator, dict) else None

            return UnifiedDeparture(
                line=line_name,
                destination=destination,
                departure_time=when_local.strftime("%H:%M"),
                planned_time=planned_local.strftime("%H:%M"),
                delay=delay_minutes,
                platform=platform,
                transportation_type=transport_type,
                is_realtime=is_realtime,
                minutes_until_departure=minutes_until,
                departure_time_obj=when_local,
                description=stop.get("direction"),
                agency=agency,
                notices=notices if notices else None,
                planned_platform=planned_platform if platform_changed else None,
                platform_changed=platform_changed,
            )
        except Exception as e:
            _LOGGER.debug("Error parsing DB departure: %s", e)
            return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using DB REST API."""
        url = f"{API_BASE}/locations?query={quote(search_term, safe='')}&results=15"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        return []

                    results = []
                    for location in data:
                        if not isinstance(location, dict):
                            continue
                        if location.get("type") != "stop":
                            continue

                        name = location.get("name", "")
                        place = ""
                        if "(" in name and name.endswith(")"):
                            place = name[name.rfind("(") + 1 : -1]

                        results.append(
                            {
                                "id": location.get("id", ""),
                                "name": name,
                                "place": place,
                                "area_type": "stop",
                            }
                        )
                    return results
                else:
                    _LOGGER.error("DB API returned status %s", response.status)
        except Exception as e:
            _LOGGER.error("Error searching DB stops: %s", e)

        return []
