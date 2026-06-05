"""Base class for all public transport providers."""

import aiohttp
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

from ..data_models import UnifiedDeparture


class BaseProvider(ABC):
    """Abstract base class for all public transport providers."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: Optional[str] = None,
        api_key_secondary: Optional[str] = None,
        custom_url: Optional[str] = None,
    ):
        self.session = session
        self.api_key = api_key
        self.api_key_secondary = api_key_secondary
        self.custom_url = custom_url

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return the provider identifier (e.g., 'vrr', 'kvv')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the human-readable provider name."""
        pass

    @property
    def requires_api_key(self) -> bool:
        """Return True if this provider requires an API key."""
        return False

    @abstractmethod
    async def fetch_departures(
        self,
        station_id: Optional[str],
        place_dm: str,
        name_dm: str,
        departures_limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch departure data from the provider's API."""
        pass

    @abstractmethod
    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from the provider's API response."""
        pass

    @abstractmethod
    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops/stations."""
        pass

    def get_timezone(self) -> str:
        """Return the timezone for this provider (e.g., 'Europe/Berlin')."""
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        """Return the transportation type mapping for this provider."""
        return {}

    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        pass
