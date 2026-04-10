"""Base provider for TRIAS (VDV 431-2) protocol APIs.

TRIAS is an XML-based, POST-only protocol standardized by VDV.
Used by various German and European transit agencies.

Subclasses only need to define:
- provider_id, provider_name
- trias_base_url (the TRIAS endpoint)
- requestor_ref (identifier for the requesting application)
- get_transport_type_mapping() for mode conversion
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)

# TRIAS XML namespace
NS = {
    "trias": "http://www.vdv.de/trias",
    "siri": "http://www.siri.org.uk/siri",
}


def _find(element: Optional[ET.Element], path: str) -> Optional[ET.Element]:
    """Find element using TRIAS namespace."""
    if element is None:
        return None
    return element.find(path, NS)


def _findall(element: Optional[ET.Element], path: str) -> List[ET.Element]:
    """Find all elements using TRIAS namespace."""
    if element is None:
        return []
    return element.findall(path, NS)


def _text(element: Optional[ET.Element], path: str, default: str = "") -> str:
    """Get text content of a child element."""
    if element is None:
        return default
    child = element.find(path, NS)
    return child.text if child is not None and child.text else default


# TRIAS PtMode → our transport type (default mapping, can be overridden)
DEFAULT_MODE_MAPPING = {
    "rail": "train",
    "urbanRail": "train",
    "metro": "subway",
    "underground": "subway",
    "tram": "tram",
    "bus": "bus",
    "coach": "bus",
    "water": "ferry",
    "telecabin": "tram",
    "funicular": "train",
    "taxi": "taxi",
}


class TRIASBaseProvider(BaseProvider):
    """Base class for TRIAS-based providers."""

    trias_base_url: str = ""
    requestor_ref: str = "openpublictransport"
    trias_version: str = "1.1"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_mode_mapping(self) -> Dict[str, str]:
        """Return PtMode → transport type mapping. Override for custom mappings."""
        return DEFAULT_MODE_MAPPING

    def _build_stop_event_request(self, stop_id: str, limit: int) -> str:
        """Build TRIAS StopEventRequest XML."""
        now = datetime.now(ZoneInfo(self.get_timezone())).isoformat()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Trias version="{self.trias_version}" xmlns="http://www.vdv.de/trias"
       xmlns:siri="http://www.siri.org.uk/siri">
  <ServiceRequest>
    <siri:RequestTimestamp>{now}</siri:RequestTimestamp>
    <siri:RequestorRef>{self.requestor_ref}</siri:RequestorRef>
    <RequestPayload>
      <StopEventRequest>
        <Location>
          <LocationRef>
            <StopPointRef>{stop_id}</StopPointRef>
          </LocationRef>
          <DepArrTime>{now}</DepArrTime>
        </Location>
        <Params>
          <NumberOfResults>{limit}</NumberOfResults>
          <StopEventType>departure</StopEventType>
          <IncludePreviousCalls>false</IncludePreviousCalls>
          <IncludeOnwardCalls>false</IncludeOnwardCalls>
          <IncludeRealtimeData>true</IncludeRealtimeData>
        </Params>
      </StopEventRequest>
    </RequestPayload>
  </ServiceRequest>
</Trias>"""

    def _build_location_request(self, search_term: str) -> str:
        """Build TRIAS LocationInformationRequest XML."""
        now = datetime.now(ZoneInfo(self.get_timezone())).isoformat()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Trias version="{self.trias_version}" xmlns="http://www.vdv.de/trias"
       xmlns:siri="http://www.siri.org.uk/siri">
  <ServiceRequest>
    <siri:RequestTimestamp>{now}</siri:RequestTimestamp>
    <siri:RequestorRef>{self.requestor_ref}</siri:RequestorRef>
    <RequestPayload>
      <LocationInformationRequest>
        <InitialInput>
          <LocationName>{search_term}</LocationName>
        </InitialInput>
        <Restrictions>
          <Type>stop</Type>
          <NumberOfResults>15</NumberOfResults>
        </Restrictions>
      </LocationInformationRequest>
    </RequestPayload>
  </ServiceRequest>
</Trias>"""

    async def _post_trias(self, xml_body: str) -> Optional[ET.Element]:
        """Send POST request to TRIAS endpoint and parse XML response."""
        session = async_get_clientsession(self.hass)
        headers = {"Content-Type": "text/xml; charset=utf-8"}

        try:
            async with session.post(
                self.trias_base_url,
                data=xml_body.encode("utf-8"),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    return ET.fromstring(text)
                else:
                    _LOGGER.warning("%s TRIAS API returned status %s", self.provider_name, response.status)
        except aiohttp.ClientError as e:
            _LOGGER.warning("%s TRIAS API request failed: %s", self.provider_name, e)
        except ET.ParseError as e:
            _LOGGER.warning("%s TRIAS XML parse error: %s", self.provider_name, e)
        except Exception as e:
            _LOGGER.warning("%s TRIAS error: %s", self.provider_name, e)

        return None

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departures via TRIAS StopEventRequest."""
        if not station_id:
            _LOGGER.warning("%s provider requires a station_id", self.provider_name)
            return None

        xml_body = self._build_stop_event_request(station_id, departures_limit)
        root = await self._post_trias(xml_body)
        if root is None:
            return None

        # Extract StopEventResult elements
        results = root.findall(".//trias:StopEventResult", NS)

        if not results:
            # Try alternative path (some TRIAS implementations nest differently)
            results = root.findall(
                ".//trias:ServiceDelivery/trias:DeliveryPayload/trias:StopEventResponse/trias:StopEventResult",
                NS,
            )

        if not results:
            _LOGGER.debug("%s: No StopEventResult elements found", self.provider_name)
            return {"stopEvents": []}

        # Convert XML elements to dicts for parse_departure
        stop_events = []
        for result in results:
            stop_event = _find(result, "trias:StopEvent")
            if stop_event is not None:
                stop_events.append(self._stop_event_to_dict(stop_event))

        return {"stopEvents": stop_events}

    def _stop_event_to_dict(self, stop_event: ET.Element) -> Dict[str, Any]:
        """Convert a TRIAS StopEvent XML element to a dict."""
        # This/CallAtStop contains time and platform info
        call = _find(stop_event, "trias:ThisCall/trias:CallAtStop")

        # Service section contains line and destination info
        service = _find(stop_event, "trias:Service")

        # Times
        timetabled = _text(call, "trias:ServiceDeparture/trias:TimetabledTime")
        estimated = _text(call, "trias:ServiceDeparture/trias:EstimatedTime")

        # Platform
        platform_text = _text(call, "trias:PlannedBay/trias:Text")
        estimated_platform = _text(call, "trias:EstimatedBay/trias:Text")

        # Line info
        line_name = _text(service, "trias:PublishedLineName/trias:Text")
        mode = _text(service, "trias:Mode/trias:PtMode")
        submode = (
            _text(service, "trias:Mode/trias:RailSubmode")
            or _text(service, "trias:Mode/trias:BusSubmode")
            or _text(service, "trias:Mode/trias:TramSubmode")
            or _text(service, "trias:Mode/trias:MetroSubmode")
        )

        # Destination
        destination = _text(service, "trias:DestinationText/trias:Text")
        if not destination:
            dest_stop = _find(service, "trias:DestinationStopPointRef")
            destination = _text(dest_stop, "trias:StopPointName/trias:Text")

        # Operator
        operator = _text(service, "trias:OperatorRef")

        # Realtime flag
        is_realtime = bool(estimated)

        return {
            "timetabledTime": timetabled,
            "estimatedTime": estimated,
            "platform": estimated_platform or platform_text,
            "plannedPlatform": platform_text,
            "lineName": line_name,
            "mode": mode,
            "submode": submode,
            "destination": destination,
            "operator": operator,
            "isRealtime": is_realtime,
        }

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a TRIAS departure dict into UnifiedDeparture."""
        try:
            timetabled_str = stop.get("timetabledTime", "")
            estimated_str = stop.get("estimatedTime", "")

            if not timetabled_str:
                return None

            planned = dt_util.parse_datetime(timetabled_str)
            if not planned:
                return None

            planned_local = planned.astimezone(tz)

            if estimated_str:
                when = dt_util.parse_datetime(estimated_str)
                when_local = when.astimezone(tz) if when else planned_local
            else:
                when_local = planned_local

            delay_seconds = (when_local - planned_local).total_seconds()
            delay_minutes = max(0, int(delay_seconds / 60))

            mode = stop.get("mode", "")
            mode_mapping = self.get_mode_mapping()
            transport_type = mode_mapping.get(mode, "unknown")

            platform = stop.get("platform", "")
            planned_platform = stop.get("plannedPlatform", "")
            platform_changed = bool(platform and planned_platform and platform != planned_platform)

            time_diff = when_local - now
            minutes_until = max(0, int(time_diff.total_seconds() / 60))

            return UnifiedDeparture(
                line=stop.get("lineName", ""),
                destination=stop.get("destination", "Unknown"),
                departure_time=when_local.strftime("%H:%M"),
                planned_time=planned_local.strftime("%H:%M"),
                delay=delay_minutes,
                platform=platform,
                transportation_type=transport_type,
                is_realtime=stop.get("isRealtime", False),
                minutes_until_departure=minutes_until,
                departure_time_obj=when_local,
                description=None,
                agency=stop.get("operator"),
                notices=None,
                planned_platform=planned_platform if platform_changed else None,
                platform_changed=platform_changed,
            )
        except Exception as e:
            _LOGGER.debug("Error parsing %s TRIAS departure: %s", self.provider_name, e)
            return None

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops via TRIAS LocationInformationRequest."""
        xml_body = self._build_location_request(search_term)
        root = await self._post_trias(xml_body)
        if root is None:
            return []

        results = root.findall(".//trias:LocationResult", NS)
        if not results:
            results = root.findall(".//trias:LocationInformationResponse/trias:LocationResult", NS)

        stops = []
        for result in results:
            location = _find(result, "trias:Location")
            if location is None:
                continue

            stop_point = _find(location, "trias:StopPoint")
            if stop_point is None:
                continue

            stop_id = _text(stop_point, "trias:StopPointRef")
            name = _text(stop_point, "trias:StopPointName/trias:Text")
            place = _text(location, "trias:LocationName/trias:Text")

            if not stop_id or not name:
                continue

            stops.append(
                {
                    "id": stop_id,
                    "name": name,
                    "place": place,
                    "area_type": "stop",
                }
            )

        return stops
