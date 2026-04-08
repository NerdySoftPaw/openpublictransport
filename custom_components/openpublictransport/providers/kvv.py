"""KVV (Karlsruher Verkehrsverbund) provider implementation."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import API_BASE_URL_KVV, KVV_TRANSPORTATION_TYPES, PROVIDER_KVV
from ..data_models import UnifiedDeparture
from ..parsers import parse_departure_generic
from .base import BaseProvider

_LOGGER = logging.getLogger(__name__)


class KVVProvider(BaseProvider):
    """KVV (Karlsruher Verkehrsverbund) provider."""

    @property
    def provider_id(self) -> str:
        """Return the provider identifier."""
        return PROVIDER_KVV

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name."""
        return "KVV (Karlsruhe)"

    def get_timezone(self) -> str:
        """Return the timezone for KVV."""
        return "Europe/Berlin"

    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departure data from KVV API."""
        base_url = API_BASE_URL_KVV

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

        headers = {"User-Agent": "Mozilla/5.0 (compatible; HomeAssistant KVV Integration)"}

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            json_data = await response.json()
                            if not isinstance(json_data, dict):
                                _LOGGER.warning("KVV API returned non-dict response: %s", type(json_data))
                                return None

                            if "stopEvents" not in json_data:
                                _LOGGER.debug("KVV API response missing 'stopEvents' field")
                                return {"stopEvents": []}

                            return json_data
                        except (ValueError, aiohttp.ContentTypeError) as e:
                            _LOGGER.warning("KVV API returned invalid JSON: %s", e)
                            return None
                        except Exception as e:
                            _LOGGER.warning("KVV API JSON parsing failed: %s", e)
                            return None
                    elif response.status == 404:
                        _LOGGER.warning("KVV API endpoint not found (404)")
                        return None
                    elif response.status >= 500:
                        _LOGGER.warning("KVV API server error (status %s)", response.status)
                    else:
                        _LOGGER.warning("KVV API returned status %s", response.status)

            except asyncio.TimeoutError:
                _LOGGER.warning("KVV API timeout on attempt %s", attempt)
            except Exception as e:
                _LOGGER.warning("Attempt %s failed: %s", attempt, e)

            if attempt < max_retries:
                await asyncio.sleep(2**attempt)

        return None

    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from KVV API response."""
        return parse_departure_generic(
            stop,
            tz,
            now,
            get_transport_type_fn=lambda t: KVV_TRANSPORTATION_TYPES.get(
                t.get("product", {}).get("class", 0), "unknown"
            ),
            get_platform_fn=lambda s: (s.get("location", {}).get("disassembledName") or s.get("platformName", "")),
            get_realtime_fn=lambda s, est, plan: s.get("isRealtimeControlled", False),
        )

    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops using KVV Stopfinder API."""
        from urllib.parse import quote

        api_url = "https://projekte.kvv-efa.de/sl3-alone/XML_STOPFINDER_REQUEST"
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
                        _LOGGER.error("Invalid JSON response from KVV API: %s", e)
                        return []

                    if not isinstance(data, dict):
                        _LOGGER.error("KVV API returned non-dict response: %s", type(data))
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

                        result = {
                            "id": location.get("id", ""),
                            "name": location.get("name", ""),
                            "place": place,
                            "area_type": location.get("type", ""),
                        }
                        results.append(result)

                    return results
                else:
                    _LOGGER.error("KVV API returned status %s", response.status)
        except Exception as e:
            _LOGGER.error("Error searching stops: %s", e, exc_info=True)

        return []
