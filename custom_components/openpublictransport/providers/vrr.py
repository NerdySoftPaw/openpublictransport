"""VRR (Verkehrsverbund Rhein-Ruhr) provider implementation."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import API_BASE_URL_VRR, PROVIDER_VRR
from ..data_models import UnifiedDeparture
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)


class VRRProvider(BaseProvider):
    """VRR (Verkehrsverbund Rhein-Ruhr) provider."""

    @property
    def provider_id(self) -> str:
        """Return the provider identifier."""
        return PROVIDER_VRR

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name."""
        return "VRR (NRW)"

    def get_timezone(self) -> str:
        """Return the timezone for VRR."""
        return "Europe/Berlin"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departure data from VRR API."""
        base_url = API_BASE_URL_VRR

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

        url = f"{base_url}?{params}"
        session = async_get_clientsession(self.hass)

        headers = {"User-Agent": "Mozilla/5.0 (compatible; HomeAssistant VRR Integration)"}

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            json_data = await response.json()
                            if not isinstance(json_data, dict):
                                _LOGGER.warning("VRR API returned non-dict response: %s", type(json_data))
                                return None

                            if "stopEvents" not in json_data:
                                _LOGGER.debug("VRR API response missing 'stopEvents' field")
                                return {"stopEvents": []}

                            return json_data
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.warning("VRR API returned invalid JSON: %s", e)
                            return None
                        except Exception as e:
                            _LOGGER.warning("VRR API JSON parsing failed: %s", e)
                            return None
                    elif response.status == 404:
                        _LOGGER.warning("VRR API endpoint not found (404)")
                        return None
                    elif response.status >= 500:
                        _LOGGER.warning("VRR API server error (status %s)", response.status)
                    else:
                        _LOGGER.warning("VRR API returned status %s", response.status)

            except asyncio.TimeoutError:
                _LOGGER.warning("VRR API timeout on attempt %s", attempt)
            except Exception as e:
                _LOGGER.warning("Attempt %s failed: %s", attempt, e)

            if attempt < max_retries:
                await asyncio.sleep(2**attempt)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from VRR API response."""
        from ..parsers import parse_departure_generic

        def determine_transport_type(transportation: Dict[str, Any]) -> str:
            """Determine the transportation type from VRR API data."""
            product = transportation.get("product", {})
            product_class = product.get("class", 0)

            # Map VRR product classes to our types
            type_mapping = {
                0: "train",  # High-speed trains (ICE, IC, EC)
                1: "train",  # Regional trains (RE, RB)
                2: "subway",  # U-Bahn (subway/metro)
                3: "subway",  # U-Bahn variant
                4: "tram",  # Tram/Streetcar
                5: "bus",  # City bus
                6: "bus",  # Regional bus
                7: "bus",  # Express bus
                8: "bus",  # Night bus
                9: "ferry",  # Ferry/Ship
                10: "taxi",  # Taxi
                11: "bus",  # Other/Special transport
                13: "train",  # Regionalzug (RE)
                15: "train",  # InterCity (IC)
                16: "train",  # InterCityExpress (ICE)
            }

            transport_type = type_mapping.get(product_class, "unknown")

            if product_class not in type_mapping:
                _LOGGER.debug(
                    "Unknown transport class %s for line %s, defaulting to unknown",
                    product_class,
                    transportation.get("number", "unknown"),
                )

            return transport_type

        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=determine_transport_type,
            get_platform_fn=lambda s: (s.get("platform", {}).get("name") or s.get("platformName", "")),
            get_realtime_fn=lambda s, est, plan: "MONITORED" in s.get("realtimeStatus", []),
        )

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using VRR Stopfinder API."""
        from urllib.parse import quote

        api_url = "https://openservice-test.vrr.de/static03/XML_STOPFINDER_REQUEST"
        encoded_search = quote(search_term, safe="")

        params = (
            f"outputFormat=RapidJSON&"
            f"locationServerActive=1&"
            f"type_sf=stop&"
            f"name_sf={encoded_search}&"
            f"SpEncId=0"
        )

        url = f"{api_url}?{params}"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                    except (ValueError, aiohttp.ContentTypeError) as e:
                        _LOGGER.error("Invalid JSON response from VRR API: %s", e)
                        return []

                    if not isinstance(data, dict):
                        _LOGGER.error("VRR API returned non-dict response: %s", type(data))
                        return []

                    # Parse VRR stopfinder response (same format as KVV/HVV)
                    locations = data.get("locations", [])
                    results = []

                    for location in locations:
                        if not isinstance(location, dict):
                            continue

                        # Extract place from disassembledName if available
                        disassembled_name = location.get("disassembledName", "")
                        place = ""
                        if "," in disassembled_name:
                            parts = disassembled_name.rsplit(",", 1)
                            place = parts[-1].strip() if len(parts) > 1 else ""

                        result = {
                            "id": location.get("id", ""),
                            "name": location.get("name", ""),
                            "place": place,
                            "area_type": location.get("type", ""),
                        }
                        results.append(result)

                    return results
                else:
                    _LOGGER.error("VRR API returned status %s", response.status)
        except Exception as e:
            _LOGGER.error("Error searching stops: %s", e, exc_info=True)

        return []
