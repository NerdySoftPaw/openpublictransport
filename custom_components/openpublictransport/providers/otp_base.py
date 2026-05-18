"""Base provider for OpenTripPlanner (OTP) REST API.

Subclasses only need to define:
- provider_id, provider_name
- otp_base_url: router base URL, e.g. 'http://gtfsr.vbn.de/api/otp/routers/default'

Override _auth_headers() to add an API key.
Override get_timezone() if not Europe/Berlin.
Override get_mode_mapping() for custom GTFS mode conversions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

OTP_MODE_MAP: Dict[str, str] = {
    "BUS": "bus",
    "COACH": "bus",
    "RAIL": "train",
    "TRAM": "tram",
    "SUBWAY": "subway",
    "FERRY": "ferry",
    "GONDOLA": "tram",
    "FUNICULAR": "train",
    "CABLE_CAR": "tram",
}


class OTPBaseProvider(BaseProvider):
    """Base class for OpenTripPlanner REST API providers."""

    otp_base_url: str = ""

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_mode_mapping(self) -> Dict[str, str]:
        return OTP_MODE_MAP

    def _auth_headers(self) -> Dict[str, str]:
        """Request headers. Override in subclasses to add API key auth."""
        return {"Accept": "application/json"}

    def _index_url(self, path: str) -> str:
        return f"{self.otp_base_url}/index/{path}"

    async def _get(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        try:
            async with session.get(
                url,
                params=params or {},
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                _LOGGER.warning("%s OTP %s → HTTP %s", self.provider_name, url, resp.status)
        except aiohttp.ClientError as exc:
            _LOGGER.warning("%s OTP request failed: %s", self.provider_name, exc)
        except Exception as exc:
            _LOGGER.warning("%s OTP error: %s", self.provider_name, exc)
        return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search stops by name via OTP /index/stops?name=..."""
        session = async_get_clientsession(self.hass)
        data = await self._get(session, self._index_url("stops"), {"name": search_term})
        if not data:
            return []
        return [
            {
                "id": s["id"],
                "name": s.get("name", ""),
                "place": s.get("name", ""),
                "area_type": "stop",
            }
            for s in data
            if isinstance(s, dict) and "id" in s
        ]

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        if not station_id:
            return None

        encoded_id = quote(station_id, safe="")
        session = async_get_clientsession(self.hass)
        mode_mapping = self.get_mode_mapping()

        # 1. Routes at stop → line shortName + transport mode
        routes_data = await self._get(session, self._index_url(f"stops/{encoded_id}/routes"))
        route_map: Dict[str, Dict[str, str]] = {}
        if routes_data:
            for r in routes_data:
                if isinstance(r, dict) and "id" in r:
                    route_map[r["id"]] = {
                        "shortName": r.get("shortName") or r.get("longName", ""),
                        "mode": mode_mapping.get(r.get("mode", ""), "unknown"),
                    }

        # 2. Stoptimes (numberOfDepartures = per pattern, not total)
        stoptimes = await self._get(
            session,
            self._index_url(f"stops/{encoded_id}/stoptimes"),
            {
                "timeRange": 7200,
                "numberOfDepartures": max(departures_limit, 5),
                "omitNonPickups": True,
            },
        )
        if stoptimes is None:
            return None

        stop_events = []
        for group in stoptimes:
            if not isinstance(group, dict):
                continue
            pattern = group.get("pattern", {})
            for t in group.get("times", []):
                if not isinstance(t, dict):
                    continue
                trip = t.get("trip", {})
                route_id = trip.get("routeId", "")
                route_info = route_map.get(route_id, {})

                stop_events.append({
                    "routeName": route_info.get("shortName") or pattern.get("desc", ""),
                    "transportType": route_info.get("mode", "unknown"),
                    "serviceDay": t.get("serviceDay", 0),
                    "scheduledDeparture": t.get("scheduledDeparture", 0),
                    "realtimeDeparture": t.get("realtimeDeparture", 0),
                    "departureDelay": t.get("departureDelay", 0),
                    "realtime": t.get("realtime", False),
                    "headsign": t.get("headsign") or trip.get("tripHeadsign", ""),
                })

        stop_events.sort(key=lambda x: x["serviceDay"] + x["realtimeDeparture"])
        return {"stopEvents": stop_events[:departures_limit]}

    def parse_departure(
        self,
        stop: Dict[str, Any],
        tz: Union[ZoneInfo, Any],
        now: datetime,
    ) -> Optional[UnifiedDeparture]:
        try:
            service_day: int = stop["serviceDay"]
            planned = datetime.fromtimestamp(
                service_day + stop["scheduledDeparture"], tz=timezone.utc
            ).astimezone(tz)
            actual = datetime.fromtimestamp(
                service_day + stop["realtimeDeparture"], tz=timezone.utc
            ).astimezone(tz)

            delay_min = max(0, int(stop.get("departureDelay", 0) / 60))
            minutes_until = max(0, int((actual - now).total_seconds() / 60))

            return UnifiedDeparture(
                line=stop.get("routeName", ""),
                destination=stop.get("headsign", "Unknown"),
                departure_time=actual.strftime("%H:%M"),
                planned_time=planned.strftime("%H:%M"),
                delay=delay_min,
                platform="",
                transportation_type=stop.get("transportType", "unknown"),
                is_realtime=stop.get("realtime", False),
                minutes_until_departure=minutes_until,
                departure_time_obj=actual,
                description=None,
                agency=None,
                notices=None,
                planned_platform=None,
                platform_changed=False,
            )
        except Exception as exc:
            _LOGGER.debug("%s OTP parse_departure error: %s", self.provider_name, exc)
            return None
