"""Base class for EFA (Electronic Fahrplan-Auskunft) providers.

EFA is used by VRR, KVV, HVV, MVV and many other German transit authorities.
This base class implements the shared XML_DM_REQUEST and XML_STOPFINDER_REQUEST logic.
"""

import asyncio
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..data_models import UnifiedDeparture
from ..parsers import parse_departure_generic
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)


class EFABaseProvider(BaseProvider):
    """Base class for all EFA-based providers (VRR, KVV, HVV, MVV, etc.).

    Subclasses only need to define:
    - provider_id, provider_name
    - dm_base_url: URL for XML_DM_REQUEST
    - sf_base_url: URL for XML_STOPFINDER_REQUEST
    - get_transport_type_mapping(): transport class → type mapping
    - get_platform_fn(): how to extract platform from stop event
    - get_realtime_fn(): how to detect realtime data
    """

    @property
    @abstractmethod
    def dm_base_url(self) -> str:
        """Return the base URL for departure monitor requests."""

    @property
    @abstractmethod
    def sf_base_url(self) -> str:
        """Return the base URL for stop finder requests."""

    def get_platform_fn(self) -> Callable[[Dict[str, Any]], str]:
        """Return function to extract platform from stop event.

        Override in subclasses for provider-specific platform extraction.
        """
        return lambda s: s.get("platform", {}).get("name") or s.get("platformName", "")

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        """Return function to detect realtime data.

        Override in subclasses for provider-specific realtime detection.
        """
        return lambda s, est, plan: "MONITORED" in s.get("realtimeStatus", [])

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departure data from EFA API."""
        if station_id:
            params = (
                f"outputFormat=RapidJSON&"
                f"stateless=1&"
                f"type_dm=any&"
                f"name_dm={station_id}&"
                f"mode=direct&"
                f"useRealtime=1&"
                f"limit={departures_limit}"
            )
        else:
            params = (
                f"outputFormat=RapidJSON&"
                f"place_dm={place_dm}&"
                f"type_dm=stop&"
                f"name_dm={name_dm}&"
                f"mode=direct&"
                f"useRealtime=1&"
                f"limit={departures_limit}"
            )

        url = f"{self.dm_base_url}?{params}"
        session = async_get_clientsession(self.hass)
        name = self.provider_name

        headers = {"User-Agent": f"Mozilla/5.0 (compatible; HomeAssistant {self.provider_id.upper()} Integration)"}

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            json_data = await response.json()
                            if not isinstance(json_data, dict):
                                _LOGGER.warning("%s API returned non-dict response: %s", name, type(json_data))
                                return None

                            if "stopEvents" not in json_data:
                                _LOGGER.debug("%s API response missing 'stopEvents' field", name)
                                return {"stopEvents": []}

                            return json_data
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.warning("%s API returned invalid JSON: %s", name, e)
                            return None
                        except Exception as e:
                            _LOGGER.warning("%s API JSON parsing failed: %s", name, e)
                            return None
                    elif response.status == 404:
                        _LOGGER.warning("%s API endpoint not found (404)", name)
                        return None
                    elif response.status >= 500:
                        _LOGGER.warning("%s API server error (status %s)", name, response.status)
                    else:
                        _LOGGER.warning("%s API returned status %s", name, response.status)

            except asyncio.TimeoutError:
                _LOGGER.warning("%s API timeout on attempt %s", name, attempt)
            except Exception as e:
                _LOGGER.warning("%s attempt %s failed: %s", name, attempt, e)

            if attempt < max_retries:
                await asyncio.sleep(2**attempt)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from EFA API response."""
        type_mapping = self.get_transport_type_mapping()

        def determine_transport_type(transportation: Dict[str, Any]) -> str:
            product = transportation.get("product", {})
            product_class = product.get("class", 0)
            transport_type = type_mapping.get(product_class, "unknown")
            if transport_type == "unknown":
                _LOGGER.debug(
                    "Unknown transport class %s for line %s",
                    product_class,
                    transportation.get("number", "unknown"),
                )
            return transport_type

        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=determine_transport_type,
            get_platform_fn=self.get_platform_fn(),
            get_realtime_fn=self.get_realtime_fn(),
        )

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using EFA Stopfinder API.

        Supports "stop, city" format — if a comma is present, the part before
        is used as stop name and the part after as place filter for better results.
        """
        # Split "Holthausen, Düsseldorf" into name + place
        if "," in search_term:
            parts = search_term.split(",", 1)
            stop_name = parts[0].strip()
            place_name = parts[1].strip()
            params = (
                f"outputFormat=RapidJSON&"
                f"locationServerActive=1&"
                f"type_sf=any&"
                f"name_sf={quote(stop_name, safe='')}&"
                f"place_sf={quote(place_name, safe='')}&"
                f"SpEncId=0"
            )
        else:
            params = (
                f"outputFormat=RapidJSON&"
                f"locationServerActive=1&"
                f"type_sf=stop&"
                f"name_sf={quote(search_term, safe='')}&"
                f"SpEncId=0"
            )

        url = f"{self.sf_base_url}?{params}"
        session = async_get_clientsession(self.hass)
        name = self.provider_name

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                    except (ValueError, aiohttp.ContentTypeError) as e:
                        _LOGGER.error("Invalid JSON response from %s API: %s", name, e)
                        return []

                    if not isinstance(data, dict):
                        _LOGGER.error("%s API returned non-dict response: %s", name, type(data))
                        return []

                    locations = data.get("locations", [])
                    results = []

                    for location in locations:
                        if not isinstance(location, dict):
                            continue

                        disassembled_name = location.get("disassembledName", "")
                        place = ""
                        if "," in disassembled_name:
                            parts = disassembled_name.rsplit(",", 1)
                            place = parts[-1].strip() if len(parts) > 1 else ""

                        results.append(
                            {
                                "id": location.get("id", ""),
                                "name": location.get("name", ""),
                                "place": place,
                                "area_type": location.get("type", ""),
                            }
                        )

                    return results
                else:
                    _LOGGER.error("%s API returned status %s", name, response.status)
        except Exception as e:
            _LOGGER.error("Error searching %s stops: %s", name, e, exc_info=True)

        return []
