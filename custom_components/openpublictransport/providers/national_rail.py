"""National Rail (UK) provider using OpenLDBWS SOAP API.

Stop search uses the Overpass API (OSM) to find UK railway stations with
ref:crs tags, returning the 3-letter CRS code used by OpenLDBWS.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import PROVIDER_NATIONAL_RAIL
from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

_ENDPOINT = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx"
_SOAP_ACTION = "http://thalesgroup.com/RTTI/2017-10-01/ldb/GetDepartureBoard"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# UK bounding box (lat_min, lon_min, lat_max, lon_max)
_UK_BBOX = "49,-11,62,2"

_SOAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ldb="http://thalesgroup.com/RTTI/2017-10-01/ldb/"
               xmlns:tok="http://thalesgroup.com/RTTI/2013-11-28/Token/types">
  <soap:Header>
    <tok:AccessToken>
      <tok:TokenValue>{api_key}</tok:TokenValue>
    </tok:AccessToken>
  </soap:Header>
  <soap:Body>
    <ldb:GetDepartureBoardRequest>
      <ldb:numRows>{num_rows}</ldb:numRows>
      <ldb:crs>{crs}</ldb:crs>
    </ldb:GetDepartureBoardRequest>
  </soap:Body>
</soap:Envelope>"""


def _strip_namespaces(xml_string: str) -> str:
    """Remove XML namespace prefixes and declarations for simpler parsing."""
    xml_string = re.sub(r' xmlns[^=]*="[^"]*"', "", xml_string)
    xml_string = re.sub(r"<([a-zA-Z]+):", "<", xml_string)
    xml_string = re.sub(r"</([a-zA-Z]+):", "</", xml_string)
    return xml_string


def _text(el: Optional[ET.Element], tag: str, default: str = "") -> str:
    """Get text of a direct child element."""
    if el is None:
        return default
    child = el.find(tag)
    return child.text if child is not None and child.text else default


class NationalRailProvider(BaseProvider):
    """National Rail (UK) provider via OpenLDBWS."""

    def __init__(
        self,
        hass,
        api_key: Optional[str] = None,
        api_key_secondary: Optional[str] = None,
        custom_url: Optional[str] = None,
    ):
        super().__init__(hass, api_key=api_key)

    @property
    def provider_id(self) -> str:
        return PROVIDER_NATIONAL_RAIL

    @property
    def provider_name(self) -> str:
        return "National Rail (UK)"

    @property
    def requires_api_key(self) -> bool:
        return True

    def get_timezone(self) -> str:
        return "Europe/London"

    def get_transport_type_mapping(self) -> Dict:
        return {}

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: Optional[str],
        name_dm: Optional[str],
        departures_limit: int,
    ) -> Optional[Dict]:
        """Fetch departures via OpenLDBWS SOAP for a given CRS code."""
        if not self.api_key or not station_id:
            return None

        crs = station_id.strip().upper()
        body = _SOAP_TEMPLATE.format(
            api_key=self.api_key,
            num_rows=min(departures_limit, 150),
            crs=crs,
        )

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                _ENDPOINT,
                data=body.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": _SOAP_ACTION,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("%s: HTTP %s for CRS %s", self.provider_name, resp.status, crs)
                    return None
                text = await resp.text()
        except Exception as exc:
            _LOGGER.warning("%s: request failed: %s", self.provider_name, exc)
            return None

        try:
            root = ET.fromstring(_strip_namespaces(text))
        except ET.ParseError as exc:
            _LOGGER.warning("%s: XML parse error: %s", self.provider_name, exc)
            return None

        services = root.findall(".//service")
        if not services:
            return {"stopEvents": []}

        tz = ZoneInfo(self.get_timezone())
        now = dt_util.now().astimezone(tz)
        board_date = now.date()

        stop_events = []
        for svc in services:
            event = self._service_to_dict(svc, board_date, tz, now)
            if event:
                stop_events.append(event)

        return {"stopEvents": stop_events}

    def _service_to_dict(
        self,
        svc: ET.Element,
        board_date: Any,
        tz: ZoneInfo,
        now: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Convert an XML service element to a plain dict."""
        std = _text(svc, "std")
        if not std:
            return None

        etd = _text(svc, "etd")
        platform = _text(svc, "platform") or None
        operator_name = _text(svc, "operator")
        operator_code = _text(svc, "operatorCode")
        is_cancelled = _text(svc, "isCancelled") == "true"
        delay_reason = _text(svc, "delayReason")
        cancel_reason = _text(svc, "cancelReason")

        # Extract destination name (first location in destination list)
        destination = ""
        dest_el = svc.find(".//destination")
        if dest_el is not None:
            loc = dest_el.find("location")
            if loc is not None:
                destination = _text(loc, "locationName")
        if not destination:
            destination = "Unknown"

        return {
            "std": std,
            "etd": etd,
            "platform": platform,
            "operator": operator_name,
            "operatorCode": operator_code,
            "isCancelled": is_cancelled,
            "delayReason": delay_reason,
            "cancelReason": cancel_reason,
            "destination": destination,
            "boardDate": board_date.isoformat(),
        }

    def parse_departure(
        self,
        stop: Dict[str, Any],
        tz: Any,
        now: datetime,
    ) -> Optional[UnifiedDeparture]:
        """Map a service dict to UnifiedDeparture."""
        std = stop.get("std", "")
        etd = stop.get("etd", "")
        if not std:
            return None

        try:
            board_date_str = stop.get("boardDate", "")
            from datetime import date as date_cls

            board_date = date_cls.fromisoformat(board_date_str) if board_date_str else datetime.now(tz).date()
        except ValueError:
            board_date = datetime.now(tz).date()

        def _parse_hhmm(hhmm: str) -> Optional[datetime]:
            try:
                h, m = map(int, hhmm.strip().split(":"))
                dt = datetime(board_date.year, board_date.month, board_date.day, h, m, tzinfo=tz)
                # Midnight crossover: if more than 1h in the past, assume next day
                if (now - dt).total_seconds() > 3600:
                    dt += timedelta(days=1)
                return dt
            except (ValueError, TypeError):
                return None

        planned_dt = _parse_hhmm(std)
        if planned_dt is None:
            return None

        is_cancelled = stop.get("isCancelled", False)
        notices: List[str] = []
        if stop.get("delayReason"):
            notices.append(stop["delayReason"])
        if stop.get("cancelReason"):
            notices.append(stop["cancelReason"])

        delay = 0
        is_realtime = False
        actual_dt = planned_dt

        if is_cancelled:
            notices.insert(0, "Cancelled / Zug fällt aus")
            is_realtime = True
        elif etd == "On time":
            is_realtime = True
        elif etd == "Delayed":
            is_realtime = True
            notices.insert(0, "Delayed / Verspätet")
        elif etd and ":" in etd:
            actual_dt_parsed = _parse_hhmm(etd)
            if actual_dt_parsed:
                actual_dt = actual_dt_parsed
                delay = max(0, int((actual_dt - planned_dt).total_seconds() / 60))
                is_realtime = True

        minutes_until = max(0, int((actual_dt - now).total_seconds() / 60))

        # Use operator code as line badge (e.g. "GR" for LNER, "GW" for GWR)
        line = stop.get("operatorCode", "") or stop.get("operator", "")

        return UnifiedDeparture(
            line=line,
            destination=stop.get("destination", ""),
            departure_time=actual_dt.strftime("%H:%M"),
            planned_time=std,
            delay=delay,
            platform=stop.get("platform"),
            transportation_type="train",
            is_realtime=is_realtime,
            minutes_until_departure=minutes_until,
            departure_time_obj=actual_dt,
            agency=stop.get("operator") or None,
            notices=notices if notices else None,
        )

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Find UK railway stations with CRS codes via Overpass API (OSM)."""
        # Escape for Overpass regex
        escaped = re.sub(r"[.*+?^${}()|[\]\\]", r"\\\g<0>", search_term)

        query = f"""[out:json][timeout:15];
(
  node["railway"="station"]["ref:crs"]["name"~"{escaped}",i]({_UK_BBOX});
  node["railway"="station"]["ref:crs"]["official_name"~"{escaped}",i]({_UK_BBOX});
  node["railway"="station"]["ref:crs"]["alt_name"~"{escaped}",i]({_UK_BBOX});
);
out 10;"""

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                _OVERPASS_URL,
                data={"data": query},
                headers={
                    "User-Agent": "openpublictransport-homeassistant/1.0 (github.com/NerdySoftPaw/openpublictransport)"
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("%s: Overpass HTTP %s", self.provider_name, resp.status)
                    return []
                data = await resp.json(content_type=None)
        except Exception as exc:
            _LOGGER.warning("%s: stop search failed: %s", self.provider_name, exc)
            return []

        results = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            crs = tags.get("ref:crs", "").strip().upper()
            name = tags.get("name") or tags.get("official_name", "")
            if not crs or len(crs) != 3 or not name:
                continue
            operator = tags.get("operator") or tags.get("network", "")
            results.append(
                {
                    "id": crs,
                    "name": name,
                    "place": operator,
                    "area_type": "stop",
                }
            )

        return results[:10]
