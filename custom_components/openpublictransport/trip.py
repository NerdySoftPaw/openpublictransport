"""Trip planner for Open Public Transport integration.

Provides both a service (on-demand) and a sensor (polling) for
route planning from A to B with connections and transfers.
"""

import logging
from datetime import datetime
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
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip from origin to destination using EFA API.

    Uses stop IDs when available (more reliable), falls back to name+place search.
    Returns a list of journey options, each with legs and transfer info.
    """
    base_url = EFA_TRIP_ENDPOINTS.get(provider)
    if not base_url:
        _LOGGER.warning("Trip planning not supported for provider: %s", provider)
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
