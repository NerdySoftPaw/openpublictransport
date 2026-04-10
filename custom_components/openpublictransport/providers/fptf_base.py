"""Base provider for FPTF (Friendly Public Transport Format) APIs.

Used by transport.rest endpoints (BVG, DB, and potentially others).
These APIs return JSON in FPTF format with no authentication required.

Subclasses only need to define:
- provider_id, provider_name
- API_BASE url
- PRODUCT_MAPPING for transport type conversion
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)


class FPTFBaseProvider(BaseProvider):
    """Base class for FPTF-based providers (transport.rest APIs)."""

    API_BASE: str = ""
    PRODUCT_MAPPING: Dict[str, str] = {}
    DEFAULT_TRANSPORT_TYPE: str = "train"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departures from FPTF REST API."""
        if not station_id:
            _LOGGER.warning("%s provider requires a station_id", self.provider_name)
            return None

        url = f"{self.API_BASE}/stops/{station_id}/departures?results={departures_limit}&duration=120"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict) or "departures" not in data:
                        _LOGGER.warning("%s API unexpected response format", self.provider_name)
                        return {"stopEvents": []}
                    return {"stopEvents": data["departures"]}
                else:
                    _LOGGER.warning("%s API returned status %s", self.provider_name, response.status)
        except aiohttp.ClientError as e:
            _LOGGER.warning("%s API request failed: %s", self.provider_name, e)
        except Exception as e:
            _LOGGER.warning("%s API error: %s", self.provider_name, e)

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
            transport_type = self.PRODUCT_MAPPING.get(product, self.DEFAULT_TRANSPORT_TYPE)

            destination_info = stop.get("destination", {})
            destination = destination_info.get("name", stop.get("direction", "Unknown"))

            platform = stop.get("platform") or ""
            planned_platform = stop.get("plannedPlatform") or ""
            platform_changed = bool(platform and planned_platform and platform != planned_platform)

            time_diff = when_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            is_realtime = stop.get("prognosisType") is not None

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
            _LOGGER.debug("Error parsing %s departure: %s", self.provider_name, e)
            return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using FPTF REST API."""
        url = f"{self.API_BASE}/locations?query={quote(search_term, safe='')}&results=15"
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
                        if location.get("type") not in ("stop", "station"):
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
                    _LOGGER.error("%s API returned status %s", self.provider_name, response.status)
        except Exception as e:
            _LOGGER.error("Error searching %s stops: %s", self.provider_name, e)

        return []
