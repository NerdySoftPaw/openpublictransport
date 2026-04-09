"""RMV (Rhein-Main-Verkehrsverbund) provider implementation.

Uses the HAFAS REST API. Requires an API key from opendata.rmv.de.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import PROVIDER_RMV
from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://www.rmv.de/hapi"

# HAFAS catCode → our transport type
# catCode is a bitmask: 1=ICE, 2=IC, 4=IR/RE, 8=RB, 16=S-Bahn, 32=Bus, 64=Ferry, 128=U-Bahn, 256=Tram
PRODUCT_MAPPING = {
    "ICE": "train",
    "IC": "train",
    "EC": "train",
    "RE": "train",
    "RB": "train",
    "S": "train",
    "U": "subway",
    "Tram": "tram",
    "Bus": "bus",
    "AST": "bus",  # Anrufsammeltaxi
    "Fäh": "ferry",
}


def _determine_transport_type(product: Dict[str, Any]) -> str:
    """Determine transport type from HAFAS product."""
    cat_out = product.get("catOut", "").strip()
    cat_code = product.get("catCode")

    # Try catOut name first
    for key, transport_type in PRODUCT_MAPPING.items():
        if cat_out.startswith(key):
            return transport_type

    # Fallback to catCode bitmask
    if cat_code is not None:
        try:
            code = int(cat_code)
            if code in (1, 2):
                return "train"  # ICE/IC
            elif code in (4, 8):
                return "train"  # RE/RB
            elif code == 16:
                return "train"  # S-Bahn
            elif code == 32:
                return "bus"
            elif code == 64:
                return "ferry"
            elif code == 128:
                return "subway"
            elif code == 256:
                return "tram"
        except (ValueError, TypeError):
            pass

    return "unknown"


class RMVProvider(BaseProvider):
    """RMV (Frankfurt/Rhine-Main) provider using HAFAS REST API."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_RMV

    @property
    def provider_name(self) -> str:
        return "RMV (Frankfurt)"

    @property
    def requires_api_key(self) -> bool:
        return True

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departures from HAFAS REST API."""
        if not station_id:
            _LOGGER.warning("RMV provider requires a station_id")
            return None

        if not self.api_key:
            _LOGGER.error("RMV provider requires an API key")
            return None

        url = (
            f"{API_BASE}/departureBoard"
            f"?accessId={self.api_key}"
            f"&id={station_id}"
            f"&format=json"
            f"&duration=120"
            f"&maxJourneys={departures_limit}"
        )
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        return None

                    if "errorCode" in data:
                        _LOGGER.warning("RMV API error: %s", data.get("errorText", "unknown"))
                        return None

                    # Map HAFAS departures to our stopEvents format
                    departures = data.get("Departure", [])
                    if isinstance(departures, dict):
                        departures = [departures]
                    return {"stopEvents": departures}
                elif response.status == 401:
                    _LOGGER.error("RMV API: invalid API key")
                else:
                    _LOGGER.warning("RMV API returned status %s", response.status)
        except aiohttp.ClientError as e:
            _LOGGER.warning("RMV API request failed: %s", e)
        except Exception as e:
            _LOGGER.warning("RMV API error: %s", e)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single HAFAS departure."""
        try:
            # HAFAS uses date + time fields, not ISO timestamps
            date_str = stop.get("date")  # "2026-04-09"
            time_str = stop.get("time")  # "15:30:00"
            rt_date_str = stop.get("rtDate")
            rt_time_str = stop.get("rtTime")

            if not date_str or not time_str:
                return None

            # Parse planned time
            planned_dt_str = f"{date_str}T{time_str}"
            planned = dt_util.parse_datetime(planned_dt_str)
            if not planned:
                return None
            planned_local = planned.replace(tzinfo=tz) if planned.tzinfo is None else planned.astimezone(tz)

            # Parse realtime time (if available)
            if rt_date_str and rt_time_str:
                rt_dt_str = f"{rt_date_str}T{rt_time_str}"
                rt = dt_util.parse_datetime(rt_dt_str)
                if rt:
                    when_local = rt.replace(tzinfo=tz) if rt.tzinfo is None else rt.astimezone(tz)
                    is_realtime = True
                else:
                    when_local = planned_local
                    is_realtime = False
            else:
                when_local = planned_local
                is_realtime = False

            delay_minutes = int((when_local - planned_local).total_seconds() / 60)

            # Product info
            product = stop.get("ProductAtStop", stop.get("Product", {}))
            if isinstance(product, list):
                product = product[0] if product else {}
            line_name = product.get("line", product.get("name", ""))
            transport_type = _determine_transport_type(product)

            direction = stop.get("direction", "Unknown")
            platform = stop.get("track", "")

            # Detect platform change
            rt_track = stop.get("rtTrack", "")
            planned_track = platform
            platform_changed = bool(rt_track and planned_track and rt_track != planned_track)
            if rt_track:
                platform = rt_track

            time_diff = when_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            # Extract messages/notices
            notices = []
            for msg in stop.get("Messages", {}).get("Message", []):
                if isinstance(msg, dict):
                    text = msg.get("head", "") or msg.get("text", "")
                    if text:
                        notices.append(text)

            operator = product.get("operator", product.get("operatorName", ""))

            return UnifiedDeparture(
                line=line_name,
                destination=direction,
                departure_time=when_local.strftime("%H:%M"),
                planned_time=planned_local.strftime("%H:%M"),
                delay=delay_minutes,
                platform=platform,
                transportation_type=transport_type,
                is_realtime=is_realtime,
                minutes_until_departure=minutes_until,
                departure_time_obj=when_local,
                description=product.get("catOutL"),
                agency=operator if operator else None,
                notices=notices if notices else None,
                planned_platform=planned_track if platform_changed else None,
                platform_changed=platform_changed,
            )
        except Exception as e:
            _LOGGER.debug("Error parsing RMV departure: %s", e)
            return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using HAFAS location.name API."""
        if not self.api_key:
            _LOGGER.error("RMV provider requires an API key for stop search")
            return []

        url = (
            f"{API_BASE}/location.name"
            f"?accessId={self.api_key}"
            f"&input={quote(search_term, safe='')}"
            f"&format=json"
            f"&maxNo=15"
            f"&type=S"  # S = stops only
        )
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        return []

                    stop_locations = data.get("stopLocationOrCoordLocation", [])
                    results = []

                    for item in stop_locations:
                        if not isinstance(item, dict):
                            continue
                        loc = item.get("StopLocation", {})
                        if not loc:
                            continue

                        name = loc.get("name", "")
                        place = ""
                        if "," in name:
                            parts = name.split(",", 1)
                            place = parts[0].strip()

                        results.append(
                            {
                                "id": loc.get("extId", loc.get("id", "")),
                                "name": name,
                                "place": place,
                                "area_type": "stop",
                            }
                        )
                    return results
                else:
                    _LOGGER.error("RMV API returned status %s", response.status)
        except Exception as e:
            _LOGGER.error("Error searching RMV stops: %s", e)

        return []
