"""Base provider for OpenTripPlanner (OTP) REST API."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp

from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_UA = "openpublictransport/1.0 (github.com/NerdySoftPaw/openpublictransport)"


def _nominatim_candidates(term: str) -> List[str]:
    """Return progressively simpler Nominatim queries for a search term."""
    candidates: List[str] = [term]

    if "," in term:
        parts = [p.strip() for p in term.split(",", 1)]
        swapped = " ".join(reversed(parts))
        if swapped not in candidates:
            candidates.append(swapped)

    words = term.replace(",", " ").split()
    if len(words) > 2:
        for i in range(len(words)):
            shorter = " ".join(w for j, w in enumerate(words) if j != i)
            if shorter not in candidates:
                candidates.append(shorter)

    return candidates


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
    stop_search_radius: int = 500

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_mode_mapping(self) -> Dict[str, str]:
        return OTP_MODE_MAP

    def _auth_headers(self) -> Dict[str, str]:
        """Request headers — override in subclasses to add API key auth."""
        return {"Accept": "application/json"}

    def _index_url(self, path: str) -> str:
        return f"{self.otp_base_url}/index/{path}"

    async def _get(
        self,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        try:
            async with self.session.get(
                url,
                params=params or {},
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 204:
                    return None
                _LOGGER.warning("%s OTP %s → HTTP %s", self.provider_name, url, resp.status)
        except aiohttp.ClientError as exc:
            _LOGGER.warning("%s OTP request failed: %s", self.provider_name, exc)
        except Exception as exc:
            _LOGGER.warning("%s OTP error: %s", self.provider_name, exc)
        return None

    async def _geocode(self, search_term: str) -> Optional[Tuple[float, float]]:
        """Resolve a stop name to (lat, lon) via Nominatim / OpenStreetMap."""
        for i, candidate in enumerate(_nominatim_candidates(search_term)):
            if i > 0:
                await asyncio.sleep(0.3)
            try:
                async with self.session.get(
                    _NOMINATIM_URL,
                    params={"q": candidate, "format": "json", "limit": 1, "countrycodes": "de"},
                    headers={"User-Agent": _NOMINATIM_UA, "Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        results = await resp.json(content_type=None)
                        if results:
                            if i > 0:
                                _LOGGER.debug(
                                    "%s: Nominatim hit on simplified query '%s'", self.provider_name, candidate
                                )
                            return float(results[0]["lat"]), float(results[0]["lon"])
            except Exception as exc:
                _LOGGER.debug("%s: Nominatim geocode error: %s", self.provider_name, exc)
        _LOGGER.warning("%s: Nominatim found nothing for '%s'", self.provider_name, search_term)
        return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search stops by geocoding the term, then finding nearby OTP stops."""
        coords = await self._geocode(search_term)
        if coords is None:
            _LOGGER.warning(
                "%s: could not geocode '%s' — check your search term",
                self.provider_name,
                search_term,
            )
            return []

        lat, lon = coords
        data = await self._get(
            self._index_url("stops"),
            {"lat": lat, "lon": lon, "radius": self.stop_search_radius},
        )
        if not data:
            return []

        return [
            {
                "id": s["id"],
                "name": s.get("name", ""),
                "place": s.get("name", ""),
                "area_type": "stop",
            }
            for s in sorted(data, key=lambda x: x.get("dist", 0))
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
        mode_mapping = self.get_mode_mapping()

        routes_data, alerts_data, stoptimes = await asyncio.gather(
            self._get(self._index_url(f"stops/{encoded_id}/routes")),
            self._get(self._index_url(f"stops/{encoded_id}/alerts")),
            self._get(
                self._index_url(f"stops/{encoded_id}/stoptimes"),
                {
                    "timeRange": 7200,
                    "numberOfDepartures": max(departures_limit, 5),
                    "omitNonPickups": "true",
                },
            ),
        )

        route_map: Dict[str, Dict[str, str]] = {}
        if routes_data:
            for r in routes_data:
                if isinstance(r, dict) and "id" in r and r["id"] not in route_map:
                    agency = r.get("agencyName") or (r["agency"]["name"] if isinstance(r.get("agency"), dict) else None)
                    route_map[r["id"]] = {
                        "shortName": r.get("shortName") or r.get("longName", ""),
                        "mode": mode_mapping.get(r.get("mode", ""), "unknown"),
                        "agency": agency or "",
                    }

        stop_notices: List[str] = []
        if alerts_data:
            seen: set = set()
            for alert in alerts_data:
                if not isinstance(alert, dict):
                    continue
                text = alert.get("alertHeaderText") or alert.get("alertDescriptionText") or ""
                if text and text not in seen:
                    stop_notices.append(text)
                    seen.add(text)
        if stoptimes is None:
            return None

        stop_events = []
        for group in stoptimes:
            if not isinstance(group, dict):
                continue
            pattern = group.get("pattern", {})
            route_id = pattern.get("routeId", "")
            route_info = route_map.get(route_id, {})

            for t in group.get("times", []):
                if not isinstance(t, dict):
                    continue
                stop_events.append(
                    {
                        "routeName": route_info.get("shortName") or pattern.get("desc", ""),
                        "transportType": route_info.get("mode", "unknown"),
                        "agency": route_info.get("agency", ""),
                        "notices": stop_notices or None,
                        "serviceDay": t.get("serviceDay", 0),
                        "scheduledDeparture": t.get("scheduledDeparture", 0),
                        "realtimeDeparture": t.get("realtimeDeparture", 0),
                        "departureDelay": t.get("departureDelay", 0),
                        "realtime": t.get("realtime", False),
                        "headsign": t.get("headsign", ""),
                    }
                )

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
            planned = datetime.fromtimestamp(service_day + stop["scheduledDeparture"], tz=timezone.utc).astimezone(tz)
            actual = datetime.fromtimestamp(service_day + stop["realtimeDeparture"], tz=timezone.utc).astimezone(tz)

            delay_min = max(0, int(stop.get("departureDelay", 0) / 60))
            minutes_until = max(0, int((actual - now).total_seconds() / 60))

            agency = stop.get("agency") or None
            notices = stop.get("notices") or None

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
                agency=agency,
                notices=notices,
                planned_platform=None,
                platform_changed=False,
                line_color=stop.get("lineColor") or None,
                line_text_color=stop.get("lineTextColor") or None,
            )
        except Exception as exc:
            _LOGGER.debug("%s OTP parse_departure error: %s", self.provider_name, exc)
            return None
