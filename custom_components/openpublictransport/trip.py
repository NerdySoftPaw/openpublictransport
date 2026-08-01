"""Trip planner for Open Public Transport integration.

Provides both a service (on-demand) and a sensor (polling) for
route planning from A to B with connections and transfers.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# EFA Trip API base URLs (same as DM base URLs but different endpoint)
EFA_TRIP_ENDPOINTS = {
    "vrr": "https://openservice-test.vrr.de/static03/XML_TRIP_REQUEST2",
    "kvv": "https://projekte.kvv-efa.de/sl3-alone/XML_TRIP_REQUEST2",
    "hvv": "https://hvv.efa.de/efa/XML_TRIP_REQUEST2",
    "mvv": "https://efa.mvv-muenchen.de/ng/XML_TRIP_REQUEST2",
    "vvs": "https://www3.vvs.de/mngvvs/XML_TRIP_REQUEST2",
    "vgn": "https://efa.vgn.de/vgnExt_oeffi/XML_TRIP_REQUEST2",
    "vagfr": "https://efa.vagfr.de/vagfr3/XML_TRIP_REQUEST2",
    "vrn": "https://www.vrn.de/mngvrn/XML_TRIP_REQUEST2",
    "vvo": "https://efa.vvo-online.de/VMSSL3/XML_TRIP_REQUEST2",
    "ding": "https://www.ding.eu/ding3/XML_TRIP_REQUEST2",
    "avv_augsburg": "https://fahrtauskunft.avv-augsburg.de/efa/XML_TRIP_REQUEST2",
    "rvv": "https://efa.rvv.de/efa/XML_TRIP_REQUEST2",
    "bsvg": "https://bsvg.efa.de/bsvagstd/XML_TRIP_REQUEST2",
    "nwl": "https://westfalenfahrplan.de/nwl-efa/XML_TRIP_REQUEST2",
}

# OTP 2.x planConnection query — routes stop-to-stop via stopLocationId, so no
# coordinates and no street-network access/egress are needed (works on a
# transit-only graph). %s = origin id, dest id, optional dateTime clause.
_GRAPHQL_PLAN_CONNECTION = """{
  planConnection(
    origin:      { location: { stopLocation: { stopLocationId: "%s" } } }
    destination: { location: { stopLocation: { stopLocationId: "%s" } } }
    %s
    first: 3
  ) {
    edges { node {
      duration
      numberOfTransfers
      legs {
        mode
        transitLeg
        duration
        from { name }
        to   { name }
        start { scheduledTime estimated { time delay } }
        end   { scheduledTime estimated { time delay } }
        trip { route { shortName } }
        route { shortName }
      }
    } }
  }
}"""

# OTP GTFS mode → unified product name
_OTP_MODE_TO_PRODUCT = {
    "BUS": "bus",
    "COACH": "bus",
    "RAIL": "train",
    "TRAM": "tram",
    "SUBWAY": "subway",
    "FERRY": "ferry",
    "GONDOLA": "tram",
    "FUNICULAR": "train",
    "CABLE_CAR": "tram",
    "WALK": "walk",
}


async def async_plan_trip(
    hass: HomeAssistant,
    provider: str,
    origin_name: str,
    origin_place: str,
    dest_name: str,
    dest_place: str,
    departure_time: Optional[datetime] = None,
    origin_id: Optional[str] = None,
    dest_id: Optional[str] = None,
    api_key: Optional[str] = None,
    custom_url: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip from origin to destination.

    Dispatches to OTP2 GraphQL for otp_custom/openpublictransport,
    OTP REST for vbn_otp, EFA XML for all other supported providers.
    Uses stop IDs when available (more reliable), falls back to name+place search.
    Returns a list of journey options, each with legs and transfer info.
    """
    from openpublictransport import get_provider

    # OTP2 GraphQL providers (community server + custom instance)
    if provider in ("openpublictransport", "otp_custom"):
        if not origin_id or not dest_id:
            _LOGGER.warning("OTP2 trip planning requires stop IDs — search for stops first")
            return None
        session = async_get_clientsession(hass)
        provider_instance = get_provider(provider, session, api_key=api_key, custom_url=custom_url)
        return await _async_plan_trip_otp2_graphql(origin_id, dest_id, departure_time, provider_instance)

    # VBN OTP — legacy OTP REST plan endpoint
    if provider == "vbn_otp":
        if not origin_id or not dest_id:
            _LOGGER.warning("VBN OTP trip planning requires stop IDs — search for stops first")
            return None
        session = async_get_clientsession(hass)
        provider_instance = get_provider(provider, session, api_key=api_key)
        return await _async_plan_trip_otp(origin_id, dest_id, departure_time, provider_instance)

    # EFA providers
    base_url = EFA_TRIP_ENDPOINTS.get(provider)
    if not base_url:
        _LOGGER.debug("Trip planning not supported for provider: %s", provider)
        return None

    now = departure_time or dt_util.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M")

    # Use stop IDs if available (much more reliable than name search)
    if origin_id and dest_id:
        params = (
            f"outputFormat=RapidJSON"
            f"&type_origin=stop&name_origin={quote(origin_id, safe='')}"
            f"&type_destination=stop&name_destination={quote(dest_id, safe='')}"
            f"&itdDate={date_str}&itdTime={time_str}"
            f"&useRealtime=1"
        )
    else:
        params = (
            f"outputFormat=RapidJSON"
            f"&type_origin=any&name_origin={quote(origin_name, safe='')}"
            f"&place_origin={quote(origin_place, safe='')}"
            f"&type_destination=any&name_destination={quote(dest_name, safe='')}"
            f"&place_destination={quote(dest_place, safe='')}"
            f"&itdDate={date_str}&itdTime={time_str}"
            f"&useRealtime=1"
        )

    url = f"{base_url}?{params}"
    session = async_get_clientsession(hass)

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                _LOGGER.warning("Trip API returned status %s", response.status)
                return None

            data = await response.json()
            if not isinstance(data, dict):
                return None

            return _parse_journeys(data.get("journeys", []))

    except Exception as e:
        _LOGGER.warning("Trip planning failed: %s", e)
        return None


_GRAPHQL_PARENT = '{ stop(id: "%s") { parentStation { gtfsId } } }'


async def _resolve_station_id(provider_instance, stop_id: str) -> str:
    """Return a stop's parent-station id, or the stop id itself if it has none.

    A multi-platform station (e.g. a Hauptbahnhof) has one stop id per platform.
    Routing from the parent station lets OTP consider every platform; pinning an
    arbitrary single platform can yield a slower or wrong-direction journey.
    """
    body = await provider_instance._graphql(_GRAPHQL_PARENT % stop_id.replace('"', '\\"'))
    parent = (((body or {}).get("data") or {}).get("stop") or {}).get("parentStation") or {}
    return parent.get("gtfsId") or stop_id


async def _async_plan_trip_otp2_graphql(
    origin_id: str,
    dest_id: str,
    departure_time: Optional[datetime],
    provider_instance,
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip via the OTP2 planConnection query (community server + custom instances).

    Routes stop-to-stop using `stopLocationId`, so OTP takes the transit stops
    directly as origin/destination — no coordinates, no street-network
    access/egress. This is what lets the OTP graph be built transit-only (no
    OSM). Requires an OTP 2.x server exposing the planConnection API.
    """
    now = departure_time or dt_util.now()
    # Compound stop IDs are pipe-separated — use the first platform ID
    from_id = origin_id.split("|")[0]
    to_id = dest_id.split("|")[0]

    # Route from the parent station rather than a single platform, so OTP
    # considers every platform of a multi-platform station.
    from_id, to_id = await asyncio.gather(
        _resolve_station_id(provider_instance, from_id),
        _resolve_station_id(provider_instance, to_id),
    )

    # Only pin the departure time when the caller asked for one; otherwise let
    # OTP default to "now" (a live server tracks the clock better than we do).
    dt_clause = ""
    if departure_time is not None:
        dt_clause = 'dateTime: { earliestDeparture: "%s" }' % now.isoformat()

    query = _GRAPHQL_PLAN_CONNECTION % (
        from_id.replace('"', '\\"'),
        to_id.replace('"', '\\"'),
        dt_clause,
    )
    body = await provider_instance._graphql(query)
    if body is None:
        return None

    if body.get("errors"):
        _LOGGER.warning("OTP2 planConnection GraphQL errors: %s", body["errors"])

    edges = (((body.get("data") or {}).get("planConnection") or {}).get("edges")) or []
    if not edges:
        _LOGGER.warning("OTP2 planConnection: no itineraries for %s → %s", from_id, to_id)
        return None

    return _parse_otp_plan_connection([e["node"] for e in edges if e.get("node")])


async def _async_plan_trip_otp(
    origin_id: str,
    dest_id: str,
    departure_time: Optional[datetime],
    provider_instance,
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip using the OTP 2.x REST /plan endpoint."""
    now = departure_time or dt_util.now()
    base_url = provider_instance.otp_base_url

    # Resolve stop coordinates concurrently — OTP /plan needs lat,lon not stop IDs
    origin_stop, dest_stop = await asyncio.gather(
        provider_instance._get(f"{base_url}/index/stops/{quote(origin_id, safe='')}"),
        provider_instance._get(f"{base_url}/index/stops/{quote(dest_id, safe='')}"),
    )
    if not origin_stop or not dest_stop:
        _LOGGER.warning("VBN OTP trip: could not resolve stop coordinates for %s / %s", origin_id, dest_id)
        return None

    from_place = f"{origin_stop['lat']},{origin_stop['lon']}"
    to_place = f"{dest_stop['lat']},{dest_stop['lon']}"

    data = await provider_instance._get(
        f"{base_url}/plan",
        {
            "fromPlace": from_place,
            "toPlace": to_place,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "numItineraries": "3",
            "mode": "TRANSIT,WALK",
        },
    )
    if not data:
        return None

    itineraries = data.get("plan", {}).get("itineraries", [])
    if not itineraries:
        _LOGGER.debug("VBN OTP trip: no itineraries returned")
        return None

    return _parse_otp_itineraries(itineraries)


def _parse_otp_itineraries(itineraries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse OTP 2.x plan itineraries into the unified journey dict format."""
    results = []

    for itin in itineraries:
        transit_legs: List[Dict[str, Any]] = []
        # ms timestamps for transfer gap calculation
        leg_arrival_ms: List[int] = []
        leg_departure_ms: List[int] = []

        for leg in itin.get("legs", []):
            if not leg.get("transitLeg", False):
                # Walking/transfer leg — capture its times for gap calc but skip display
                if transit_legs:
                    # The walk connects the previous transit leg to the next one
                    leg_arrival_ms.append(leg.get("endTime", 0))
                continue

            start_ms: int = leg.get("startTime", 0)
            end_ms: int = leg.get("endTime", 0)
            dep_delay_s: int = leg.get("departureDelay", 0)
            arr_delay_s: int = leg.get("arrivalDelay", 0)

            # planned = actual minus delay
            planned_start_ms = start_ms - dep_delay_s * 1000
            planned_end_ms = end_ms - arr_delay_s * 1000

            dep_estimated = _ms_to_hhmm(start_ms)
            dep_planned = _ms_to_hhmm(planned_start_ms)
            arr_estimated = _ms_to_hhmm(end_ms)
            arr_planned = _ms_to_hhmm(planned_end_ms)

            delay_min = dep_delay_s // 60

            transit_legs.append(
                {
                    "origin": leg.get("from", {}).get("name", ""),
                    "destination": leg.get("to", {}).get("name", ""),
                    "line": (leg.get("trip") or {}).get("route", {}).get("shortName") or leg.get("route", ""),
                    "product": _OTP_MODE_TO_PRODUCT.get(leg.get("mode", ""), leg.get("mode", "").lower()),
                    "departure_planned": dep_planned,
                    "departure_estimated": dep_estimated,
                    "arrival_planned": arr_planned,
                    "arrival_estimated": arr_estimated,
                    "delay": delay_min,
                    "duration_minutes": round(leg.get("duration", 0) / 60),
                    "platform": "",
                    # Internal ms values for transfer gap calculation
                    "_arrival_ms": end_ms,
                    "_departure_ms": start_ms,
                }
            )
            leg_departure_ms.append(start_ms)
            leg_arrival_ms.append(end_ms)

        if not transit_legs:
            continue

        # Transfer risk from arrival of leg N to departure of leg N+1
        connection_feasible = True
        transfer_risk = "low"
        min_transfer_time: Optional[int] = None

        for i in range(len(transit_legs) - 1):
            arr_ms = transit_legs[i]["_arrival_ms"]
            dep_ms = transit_legs[i + 1]["_departure_ms"]
            gap_min = (dep_ms - arr_ms) // 60000
            if min_transfer_time is None or gap_min < min_transfer_time:
                min_transfer_time = gap_min
            if gap_min <= 0:
                connection_feasible = False
                transfer_risk = "missed"
            elif gap_min <= 3 and transfer_risk != "missed":
                transfer_risk = "high"
            elif gap_min <= 5 and transfer_risk not in ("missed", "high"):
                transfer_risk = "medium"

        # Strip internal keys before returning
        for leg in transit_legs:
            leg.pop("_arrival_ms", None)
            leg.pop("_departure_ms", None)

        first_dep = transit_legs[0].get("departure_estimated") or transit_legs[0].get("departure_planned", "")
        last_arr = transit_legs[-1].get("arrival_estimated") or transit_legs[-1].get("arrival_planned", "")

        results.append(
            {
                "departure": first_dep,
                "arrival": last_arr,
                "duration_minutes": round(itin.get("duration", 0) / 60),
                "transfers": itin.get("numberOfTransfers", itin.get("transfers", len(transit_legs) - 1)),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": transit_legs,
            }
        )

    return results


def _ms_to_hhmm(ms: int) -> str:
    """Convert OTP millisecond Unix timestamp to HH:MM in local time."""
    if not ms:
        return ""
    try:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return dt_util.as_local(dt).strftime("%H:%M")
    except (ValueError, OSError):
        return ""


def _iso_to_hhmm(iso: Optional[str]) -> str:
    """Convert an ISO-8601 datetime string to HH:MM in local time."""
    if not iso:
        return ""
    dt = dt_util.parse_datetime(iso)
    return dt_util.as_local(dt).strftime("%H:%M") if dt else ""


def _iso_to_epoch(iso: Optional[str]) -> float:
    """Convert an ISO-8601 datetime string to a Unix timestamp (seconds)."""
    if not iso:
        return 0.0
    dt = dt_util.parse_datetime(iso)
    return dt.timestamp() if dt else 0.0


_ISO_DURATION_RE = re.compile(
    r"^(?P<sign>-)?P(?:(?P<days>\d+)D)?T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?$",
    re.IGNORECASE,
)


def _duration_to_seconds(value: Any) -> int:
    """Coerce an OTP2 ``Duration`` value to whole seconds.

    OTP2's ``planConnection`` returns durations (leg/itinerary ``duration`` and
    realtime ``delay``) as the ``Duration`` scalar, serialised as an ISO-8601
    string like ``"PT3M"`` / ``"-PT90S"``. Older/other schemas return a plain
    number of seconds. Handle both (and ``None``) so a real-time delay no longer
    crashes the trip planner.
    """
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))  # plain numeric string (seconds)
    except ValueError:
        pass
    match = _ISO_DURATION_RE.match(text)
    if not match:
        return 0
    parts = match.groupdict()
    total = (
        int(parts["days"] or 0) * 86400
        + int(parts["h"] or 0) * 3600
        + int(parts["m"] or 0) * 60
        + int(float(parts["s"] or 0))
    )
    return -total if parts["sign"] else total


def _parse_otp_plan_connection(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse OTP2 planConnection nodes into the unified journey dict format."""
    results = []

    for node in nodes:
        transit_legs = []
        for leg in node.get("legs", []):
            if not leg.get("transitLeg", False):
                continue

            start = leg.get("start") or {}
            end = leg.get("end") or {}
            dep_planned = start.get("scheduledTime")
            dep_estimated = ((start.get("estimated") or {}).get("time")) or dep_planned
            arr_planned = end.get("scheduledTime")
            arr_estimated = ((end.get("estimated") or {}).get("time")) or arr_planned
            delay_s = (start.get("estimated") or {}).get("delay")
            route = (leg.get("trip") or {}).get("route") or leg.get("route") or {}

            transit_legs.append(
                {
                    "origin": (leg.get("from") or {}).get("name", ""),
                    "destination": (leg.get("to") or {}).get("name", ""),
                    "line": route.get("shortName") or "",
                    "product": _OTP_MODE_TO_PRODUCT.get(leg.get("mode", ""), (leg.get("mode") or "").lower()),
                    "departure_planned": _iso_to_hhmm(dep_planned),
                    "departure_estimated": _iso_to_hhmm(dep_estimated),
                    "arrival_planned": _iso_to_hhmm(arr_planned),
                    "arrival_estimated": _iso_to_hhmm(arr_estimated),
                    "delay": _duration_to_seconds(delay_s) // 60,
                    "duration_minutes": round(_duration_to_seconds(leg.get("duration")) / 60),
                    "platform": "",
                    # Internal epoch seconds for transfer-gap calculation
                    "_arrival_s": _iso_to_epoch(arr_estimated),
                    "_departure_s": _iso_to_epoch(dep_estimated),
                }
            )

        if not transit_legs:
            continue

        connection_feasible = True
        transfer_risk = "low"
        min_transfer_time: Optional[int] = None

        for i in range(len(transit_legs) - 1):
            gap_min = int((transit_legs[i + 1]["_departure_s"] - transit_legs[i]["_arrival_s"]) // 60)
            if min_transfer_time is None or gap_min < min_transfer_time:
                min_transfer_time = gap_min
            if gap_min <= 0:
                connection_feasible = False
                transfer_risk = "missed"
            elif gap_min <= 3 and transfer_risk != "missed":
                transfer_risk = "high"
            elif gap_min <= 5 and transfer_risk not in ("missed", "high"):
                transfer_risk = "medium"

        for leg in transit_legs:
            leg.pop("_arrival_s", None)
            leg.pop("_departure_s", None)

        first_dep = transit_legs[0].get("departure_estimated") or transit_legs[0].get("departure_planned", "")
        last_arr = transit_legs[-1].get("arrival_estimated") or transit_legs[-1].get("arrival_planned", "")

        results.append(
            {
                "departure": first_dep,
                "arrival": last_arr,
                "duration_minutes": round(_duration_to_seconds(node.get("duration")) / 60),
                "transfers": node.get("numberOfTransfers", len(transit_legs) - 1),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": transit_legs,
            }
        )

    return results


def _parse_journeys(journeys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse EFA journey data into a clean format."""
    results = []

    for journey in journeys:
        legs = []
        total_duration = 0

        for leg in journey.get("legs", []):
            origin = leg.get("origin", {})
            destination = leg.get("destination", {})
            transport = leg.get("transportation", {})
            product = transport.get("product", {})
            interchange = leg.get("interchange", {})

            dep_planned = origin.get("departureTimePlanned", "")
            dep_estimated = origin.get("departureTimeEstimated", "")
            arr_planned = destination.get("arrivalTimePlanned", "")
            arr_estimated = destination.get("arrivalTimeEstimated", "")

            # Calculate delay
            dep_delay = 0
            if dep_planned and dep_estimated:
                try:
                    p = dt_util.parse_datetime(dep_planned)
                    e = dt_util.parse_datetime(dep_estimated)
                    if p and e:
                        dep_delay = int((e - p).total_seconds() / 60)
                except (ValueError, TypeError):
                    pass

            duration = leg.get("duration", 0)
            total_duration += duration

            leg_data = {
                "origin": origin.get("name", ""),
                "destination": destination.get("name", ""),
                "line": transport.get("number", ""),
                "product": product.get("name", ""),
                "departure_planned": _format_time(dep_planned),
                "departure_estimated": _format_time(dep_estimated),
                "arrival_planned": _format_time(arr_planned),
                "arrival_estimated": _format_time(arr_estimated),
                "delay": dep_delay,
                "duration_minutes": round(duration / 60) if duration else 0,
                "platform": origin.get("platform", {}).get("name", ""),
            }

            # Add transfer info if present
            if interchange and interchange.get("desc"):
                leg_data["transfer"] = interchange.get("desc", "")

            legs.append(leg_data)

        if not legs:
            continue

        # Journey summary
        first_dep = legs[0].get("departure_estimated") or legs[0].get("departure_planned", "")
        last_arr = legs[-1].get("arrival_estimated") or legs[-1].get("arrival_planned", "")

        # Connection feasibility
        connection_feasible = True
        transfer_risk = "low"
        min_transfer_time = None

        for i in range(len(legs) - 1):
            arr = legs[i].get("arrival_estimated") or legs[i].get("arrival_planned", "")
            dep = legs[i + 1].get("departure_estimated") or legs[i + 1].get("departure_planned", "")
            if arr and dep:
                try:
                    arr_dt = dt_util.parse_datetime(f"2026-01-01T{arr}:00")
                    dep_dt = dt_util.parse_datetime(f"2026-01-01T{dep}:00")
                    if arr_dt and dep_dt:
                        transfer_mins = int((dep_dt - arr_dt).total_seconds() / 60)
                        if min_transfer_time is None or transfer_mins < min_transfer_time:
                            min_transfer_time = transfer_mins
                        if transfer_mins <= 0:
                            connection_feasible = False
                            transfer_risk = "missed"
                        elif transfer_mins <= 3:
                            transfer_risk = "high"
                        elif transfer_mins <= 5:
                            if transfer_risk != "high":
                                transfer_risk = "medium"
                except (ValueError, TypeError):
                    pass

        results.append(
            {
                "departure": first_dep,
                "arrival": last_arr,
                "duration_minutes": round(total_duration / 60) if total_duration else 0,
                "transfers": journey.get("interchanges", 0),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": legs,
            }
        )

    return results


def _format_time(iso_str: str) -> str:
    """Format ISO datetime string to HH:MM in local time."""
    if not iso_str:
        return ""
    try:
        dt = dt_util.parse_datetime(iso_str)
        if dt:
            local_dt = dt_util.as_local(dt)
            return local_dt.strftime("%H:%M")
    except (ValueError, TypeError):
        pass
    return ""
