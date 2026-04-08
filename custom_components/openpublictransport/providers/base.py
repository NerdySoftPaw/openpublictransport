"""Base class for all public transport providers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant

from ..data_models import UnifiedDeparture


class BaseProvider(ABC):
    """Abstract base class for all public transport providers."""

    def __init__(self, hass: HomeAssistant, api_key: Optional[str] = None, api_key_secondary: Optional[str] = None):
        """Initialize the provider.

        Args:
            hass: Home Assistant instance
            api_key: Primary API key (if required)
            api_key_secondary: Secondary API key (if required, e.g., for NTA)
        """
        self.hass = hass
        self.api_key = api_key
        self.api_key_secondary = api_key_secondary

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
        """Fetch departure data from the provider's API.

        Args:
            station_id: Station/stop ID (if available)
            place_dm: Place/city name
            name_dm: Stop name
            departures_limit: Maximum number of departures to fetch

        Returns:
            Dictionary with 'stopEvents' key containing list of departures, or None on error
        """
        pass

    @abstractmethod
    def parse_departure(
        self, stop: Dict[str, Any], tz: Union[ZoneInfo, Any], now: datetime
    ) -> Optional[UnifiedDeparture]:
        """Parse a single departure from the provider's API response.

        Args:
            stop: Stop event data from API
            tz: Timezone object
            now: Current datetime

        Returns:
            UnifiedDeparture object or None if parsing fails
        """
        pass

    @abstractmethod
    async def search_stops(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for stops/stations.

        Args:
            search_term: Search query

        Returns:
            List of stop dictionaries with 'id', 'name', and optionally 'place' keys
        """
        pass

    def get_timezone(self) -> str:
        """Return the timezone for this provider (e.g., 'Europe/Berlin')."""
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        """Return the transportation type mapping for this provider.

        Returns:
            Dictionary mapping provider-specific transport types to unified types
        """
        return {}

    async def cleanup(self) -> None:
        """Cleanup provider resources.

        This method is called when the provider is being unloaded.
        Override in subclasses to release resources like GTFS data references.

        Default implementation does nothing.
        """
        pass
