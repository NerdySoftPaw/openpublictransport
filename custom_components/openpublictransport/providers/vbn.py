"""VBN (Verkehrsverbund Bremen/Niedersachsen) provider.

Tries TRIAS first (https://fahrplaner.vbn.de/triasproxy/), falls back to
OpenTripPlanner REST API (http://gtfsr.vbn.de/api/).

Both APIs share the same API key, passed as 'Authorization: Bearer <key>'.
Request a free key at api@vbn.de — 3,000 transactions/day for non-commercial use.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import PROVIDER_VBN
from .trias_base import DEFAULT_MODE_MAPPING, TRIASBaseProvider

_LOGGER = logging.getLogger(__name__)

_OTP_BASE = "http://gtfsr.vbn.de/api/otp/routers/default/index"

# Map OTP GTFS route modes → TRIAS PtMode strings (so parse_departure works for both)
_OTP_TO_TRIAS_MODE: Dict[str, str] = {
    "BUS": "bus",
    "RAIL": "rail",
    "TRAM": "tram",
    "SUBWAY": "metro",
    "FERRY": "water",
    "GONDOLA": "tram",
    "FUNICULAR": "funicular",
    "CABLE_CAR": "telecabin",
    "COACH": "coach",
}

# Prefix used on stop IDs returned by OTP search so fetch_departures knows which API to use
_OTP_PREFIX = "OTP:"


class VBNProvider(TRIASBaseProvider):
    """VBN provider — TRIAS with Bearer auth, automatic OTP fallback.

    Stop IDs from OTP search are prefixed with 'OTP:' so the provider always
    calls the correct backend without requiring user interaction.
    """

    trias_base_url = "https://fahrplaner.vbn.de/triasproxy/"

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: Optional[str] = None,
        api_key_secondary: Optional[str] = None,
    ) -> None:
        super().__init__(hass, api_key, api_key_secondary)
        # Cached API preference: None = not yet determined, True = TRIAS, False = OTP
        self._use_trias: Optional[bool] = None

    @property
    def provider_id(self) -> str:
        return PROVIDER_VBN

    @property
    def provider_name(self) -> str:
        return "VBN (Bremen/Niedersachsen)"

    @property
    def requires_api_key(self) -> bool:
        return True

    # ── Auth ────────────────────────────────────────────────────────────────

    def _extra_headers(self) -> Dict[str, str]:
        """Add Bearer token to all TRIAS requests."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def get_mode_mapping(self) -> Dict[str, str]:
        """TRIAS PtMode + OTP GTFS mode → unified transport types."""
        return {
            **DEFAULT_MODE_MAPPING,
            # OTP GTFS modes (uppercase) — used when OTP fallback is active
            "BUS": "bus",
            "RAIL": "train",
            "TRAM": "tram",
            "SUBWAY": "subway",
            "FERRY": "ferry",
            "GONDOLA": "tram",
            "FUNICULAR": "train",
            "CABLE_CAR": "tram",
            "COACH": "bus",
        }

    # ── OTP helpers ─────────────────────────────────────────────────────────

    def _otp_headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _otp_get(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        try:
            async with session.get(
                url,
                params=params or {},
                headers=self._otp_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                _LOGGER.debug("VBN OTP %s → HTTP %s", url, resp.status)
        except aiohttp.ClientError as exc:
            _LOGGER.debug("VBN OTP request failed: %s", exc)
        except Exception as exc:
            _LOGGER.debug("VBN OTP error: %s", exc)
        return None

    async def _otp_search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        data = await self._otp_get(session, f"{_OTP_BASE}/stops", {"name": search_term})
        if not data:
            return []
        return [
            {
                "id": f"{_OTP_PREFIX}{s['id']}",
                "name": s.get("name", ""),
                "place": s.get("name", ""),
                "area_type": "stop",
            }
            for s in data
            if isinstance(s, dict) and "id" in s
        ]

    async def _otp_fetch_departures(
        self,
        station_id: str,
        limit: int,
    ) -> Optional[Dict[str, Any]]:
        otp_id = station_id.removeprefix(_OTP_PREFIX)
        encoded_id = quote(otp_id, safe="")
        session = async_get_clientsession(self.hass)

        # Fetch routes at stop to get line shortName + GTFS mode
        routes_data = await self._otp_get(session, f"{_OTP_BASE}/stops/{encoded_id}/routes")
        route_map: Dict[str, Dict[str, str]] = {}
        if routes_data:
            for r in routes_data:
                if isinstance(r, dict) and "id" in r:
                    route_map[r["id"]] = {
                        "shortName": r.get("shortName") or r.get("longName", ""),
                        "mode": _OTP_TO_TRIAS_MODE.get(r.get("mode", ""), "bus"),
                    }

        # Fetch stoptimes (numberOfDepartures is per-pattern, not total)
        stoptimes = await self._otp_get(
            session,
            f"{_OTP_BASE}/stops/{encoded_id}/stoptimes",
            {
                "timeRange": 7200,
                "numberOfDepartures": max(limit, 5),
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

                service_day: int = t.get("serviceDay", 0)
                scheduled: int = t.get("scheduledDeparture", 0)
                realtime_dep: int = t.get("realtimeDeparture", 0)
                is_realtime: bool = t.get("realtime", False)

                # Convert OTP timestamps to ISO strings so TRIASBaseProvider.parse_departure works
                planned_iso = datetime.fromtimestamp(
                    service_day + scheduled, tz=timezone.utc
                ).isoformat()
                estimated_iso = (
                    datetime.fromtimestamp(
                        service_day + realtime_dep, tz=timezone.utc
                    ).isoformat()
                    if is_realtime
                    else ""
                )

                stop_events.append({
                    "timetabledTime": planned_iso,
                    "estimatedTime": estimated_iso,
                    "platform": "",
                    "plannedPlatform": "",
                    "lineName": route_info.get("shortName") or pattern.get("desc", ""),
                    "mode": route_info.get("mode", "bus"),
                    "submode": "",
                    "destination": t.get("headsign") or trip.get("tripHeadsign", "Unknown"),
                    "operator": "",
                    "isRealtime": is_realtime,
                })

        stop_events.sort(key=lambda x: x["timetabledTime"])
        return {"stopEvents": stop_events[:limit]}

    # ── Public overrides ─────────────────────────────────────────────────────

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Try TRIAS, fall back to OTP if TRIAS is unavailable."""
        if self._use_trias is not False:
            results = await super().search_stops(search_term)
            if results:
                self._use_trias = True
                return results
            _LOGGER.info("VBN TRIAS search returned no results — switching to OTP")

        self._use_trias = False
        return await self._otp_search_stops(search_term)

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Try TRIAS or OTP based on stop ID prefix and cached preference."""
        if not station_id:
            return None

        # OTP IDs are tagged with prefix — always route to OTP
        if station_id.startswith(_OTP_PREFIX):
            return await self._otp_fetch_departures(station_id, departures_limit)

        # TRIAS IDs: try TRIAS, fall back to OTP on failure
        if self._use_trias is not False:
            result = await super().fetch_departures(
                station_id, place_dm, name_dm, departures_limit
            )
            if result is not None:
                self._use_trias = True
                return result
            _LOGGER.info("VBN TRIAS fetch failed — switching to OTP")

        self._use_trias = False
        return await self._otp_fetch_departures(station_id, departures_limit)
