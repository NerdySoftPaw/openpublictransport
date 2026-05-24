"""Generic OTP2 provider base — used by the community server and custom instances.

Handles:
- GraphQL stop search with ß→ss and VRR/NRW city-prefix fallback
- Multi-platform compound stop IDs (pipe-separated)
- Parallel platform fetch + merge
- X-API-Key header when api_key is set
- custom_url override for self-hosted instances
"""

import asyncio
import logging
import math
import time
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .otp_base import OTPBaseProvider

_LOGGER = logging.getLogger(__name__)

# gtfs.de stores VRR/NRW stops with a city-prefix: "D-Elbruchstraße" not "Elbruchstraße"
_CITY_PREFIXES: Dict[str, str] = {
    "düsseldorf": "D-",
    "duesseldorf": "D-",
    "köln": "K-",
    "koeln": "K-",
    "cologne": "K-",
    "dortmund": "Do-",
    "essen": "E-",
    "duisburg": "DU-",
    "wuppertal": "W-",
    "bochum": "BO-",
    "bielefeld": "BI-",
    "münster": "MS-",
    "muenster": "MS-",
    "aachen": "AC-",
    "krefeld": "KR-",
    "mönchengladbach": "MG-",
    "moenchengladbach": "MG-",
    "oberhausen": "OB-",
    "hagen": "HA-",
    "hamm": "HAM-",
    "gelsenkirchen": "GE-",
    "mülheim": "MH-",
    "muelheim": "MH-",
    "leverkusen": "LEV-",
    "bonn": "BN-",
}

_GRAPHQL_STOP_SEARCH = '{ stops(name: "%s") { gtfsId name lat lon } }'


def _detect_city_prefix(search_term: str) -> Optional[str]:
    """If the search contains a known city name, return PREFIX + stop_part.

    Handles "Düsseldorf Elbruchstraße" and "Elbruchstraße, Düsseldorf" by
    removing the city word and prepending its gtfs.de prefix to the remainder.
    """
    words = search_term.strip().replace(",", " ").split()
    for i, word in enumerate(words):
        prefix = _CITY_PREFIXES.get(word.lower())
        if prefix:
            remaining = " ".join(w for j, w in enumerate(words) if j != i).strip()
            if remaining:
                return prefix + remaining
    return None


_MAX_PLATFORM_DISTANCE_M = 500


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon points."""
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _cluster_by_proximity(stops: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Union-find clustering: stops within _MAX_PLATFORM_DISTANCE_M form one cluster.

    Prevents stops from different cities that share a name (e.g. "Hauptbahnhof")
    from being merged into a single compound ID.
    """
    n = len(stops)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            si, sj = stops[i], stops[j]
            if si.get("lat") and si.get("lon") and sj.get("lat") and sj.get("lon"):
                if _haversine_m(si["lat"], si["lon"], sj["lat"], sj["lon"]) <= _MAX_PLATFORM_DISTANCE_M:
                    parent[find(i)] = find(j)

    groups: Dict[int, List[Dict[str, Any]]] = {}
    for i, stop in enumerate(stops):
        groups.setdefault(find(i), []).append(stop)
    return list(groups.values())


_GRAPHQL_STOPTIMES = """{
  stop(id: "%s") {
    name
    stoptimesWithoutPatterns(numberOfDepartures: %d, startTime: %d) {
      serviceDay
      scheduledDeparture
      realtimeDeparture
      departureDelay
      realtime
      headsign
      trip {
        route {
          shortName
          mode
          agency {
            name
          }
        }
      }
    }
  }
}"""


class OTPProvider(OTPBaseProvider):
    """Generic OTP2 provider — subclass and set otp_base_url, provider_id, provider_name."""

    otp_base_url: str = ""

    @property
    def _effective_base_url(self) -> str:
        return (self.custom_url or "").rstrip("/") or self.otp_base_url

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _graphql(self, query: str) -> Optional[Dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        url = f"{self._effective_base_url}/index/graphql"
        try:
            async with session.post(
                url,
                json={"query": query},
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                _LOGGER.warning("%s GraphQL → HTTP %s", self.provider_name, resp.status)
        except Exception as exc:
            _LOGGER.warning("%s GraphQL request failed: %s", self.provider_name, exc)
        return None

    def _raw_stops_from_body(self, body: Optional[Dict]) -> List[Dict[str, Any]]:
        return [
            s for s in (((body or {}).get("data") or {}).get("stops") or []) if isinstance(s, dict) and "gtfsId" in s
        ]

    def _group_by_name(self, raw_stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group platform stops into compound entries per physical station.

        First groups by name, then further splits by proximity so stops in
        different cities that share a name (e.g. "Hauptbahnhof") are not
        merged into a single compound ID.
        """
        by_name: Dict[str, List[Dict[str, Any]]] = {}
        for s in raw_stops:
            by_name.setdefault(s["name"], []).append(s)

        result = []
        for name, stops in by_name.items():
            for cluster in _cluster_by_proximity(stops):
                compound_id = "|".join(s["gtfsId"] for s in cluster)
                result.append({"id": compound_id, "name": name, "place": name, "area_type": "stop"})
        return result

    async def _search_one(self, term: str) -> List[Dict[str, Any]]:
        q = _GRAPHQL_STOP_SEARCH % term.replace('"', '\\"')
        return self._raw_stops_from_body(await self._graphql(q))

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search stops via OTP2 GraphQL with city-prefix fallback for VRR/NRW."""
        ss_term = search_term.replace("ß", "ss") if "ß" in search_term else None

        # Phase 1: bare name and ß→ss variant
        for term in filter(None, [search_term, ss_term]):
            raw = await self._search_one(term)
            if raw:
                return self._group_by_name(raw)[:20]

        # Phase 1b: city-word detection — "Düsseldorf Elbruchstraße" → "D-Elbruchstraße"
        detected = _detect_city_prefix(search_term)
        if detected:
            raw = await self._search_one(detected)
            if raw:
                return self._group_by_name(raw)[:20]
            detected_ss = detected.replace("ß", "ss") if "ß" in detected else None
            if detected_ss:
                raw = await self._search_one(detected_ss)
                if raw:
                    return self._group_by_name(raw)[:20]

        # Phase 2: all city prefixes in parallel
        prefixed = [p + search_term for p in _CITY_PREFIXES.values()]
        if ss_term:
            prefixed += [p + ss_term for p in _CITY_PREFIXES.values()]
        seen_terms: set = set()
        unique = [t for t in prefixed if not (t in seen_terms or seen_terms.add(t))]  # type: ignore[func-returns-value]

        bodies = await asyncio.gather(*[self._graphql(_GRAPHQL_STOP_SEARCH % t.replace('"', '\\"')) for t in unique])
        all_raw: List[Dict[str, Any]] = []
        seen_ids: set = set()
        for body in bodies:
            for stop in self._raw_stops_from_body(body):
                if stop["gtfsId"] not in seen_ids:
                    seen_ids.add(stop["gtfsId"])
                    all_raw.append(stop)
        if all_raw:
            return self._group_by_name(all_raw)[:20]

        # Phase 3: Nominatim + OTP radius search
        return await super().search_stops(search_term)

    def _stoptimes_to_events(self, stoptimes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mode_mapping = self.get_mode_mapping()
        return [
            {
                "routeName": ((st.get("trip") or {}).get("route") or {}).get("shortName", ""),
                "transportType": mode_mapping.get(
                    ((st.get("trip") or {}).get("route") or {}).get("mode", ""), "unknown"
                ),
                "agency": (((st.get("trip") or {}).get("route") or {}).get("agency") or {}).get("name", ""),
                "notices": None,
                "serviceDay": st.get("serviceDay", 0),
                "scheduledDeparture": st.get("scheduledDeparture", 0),
                "realtimeDeparture": st.get("realtimeDeparture", 0),
                "departureDelay": st.get("departureDelay", 0),
                "realtime": st.get("realtime", False),
                "headsign": st.get("headsign", ""),
            }
            for st in stoptimes
        ]

    async def _fetch_one_stop(self, gtfs_id: str, limit: int, start_epoch: int) -> List[Dict[str, Any]]:
        q = _GRAPHQL_STOPTIMES % (gtfs_id.replace('"', '\\"'), limit, start_epoch)
        body = await self._graphql(q)
        if body is None:
            return []
        stoptimes = (((body.get("data") or {}).get("stop")) or {}).get("stoptimesWithoutPatterns") or []
        return self._stoptimes_to_events(stoptimes)

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        if not station_id:
            return None

        gtfs_ids = station_id.split("|")
        start_epoch = int(time.time())

        if len(gtfs_ids) == 1:
            events = await self._fetch_one_stop(gtfs_ids[0], departures_limit, start_epoch)
        else:
            results = await asyncio.gather(
                *[self._fetch_one_stop(gid, departures_limit, start_epoch) for gid in gtfs_ids]
            )
            seen_keys: set = set()
            merged = []
            for batch in results:
                for ev in batch:
                    key = (ev["serviceDay"], ev["realtimeDeparture"], ev["routeName"], ev["headsign"])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        merged.append(ev)
            merged.sort(key=lambda x: x["serviceDay"] + x["realtimeDeparture"])
            events = merged[:departures_limit]

        return {"stopEvents": events}

    # parse_departure inherited from OTPBaseProvider: serviceDay + departure as UTC → correct local time
