"""Unified data models for all public transport providers.

This module defines standardized data structures that all providers
(VRR, KVV, HVV, Trafiklab) map their API responses to.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class UnifiedTransportType(str, Enum):
    """Unified transportation types across all providers."""

    BUS = "bus"
    TRAM = "tram"
    SUBWAY = "subway"
    TRAIN = "train"
    FERRY = "ferry"
    TAXI = "taxi"
    ON_DEMAND = "on_demand"
    UNKNOWN = "unknown"


@dataclass
class UnifiedDeparture:
    """Unified departure data structure for Home Assistant.

    All providers map their API responses to this structure,
    ensuring consistent data format in Home Assistant.
    """

    line: str
    destination: str
    departure_time: str  # HH:MM format
    planned_time: str  # HH:MM format
    delay: int  # minutes
    platform: Optional[str]
    transportation_type: str
    is_realtime: bool
    minutes_until_departure: int
    departure_time_obj: datetime  # For internal sorting
    description: Optional[str] = None  # Optional line description
    agency: Optional[str] = None  # Optional agency/operator name (for GTFS)

    def to_dict(self) -> dict:
        """Convert to dictionary for Home Assistant attributes."""
        result = {
            "line": self.line,
            "destination": self.destination,
            "departure_time": self.departure_time,
            "planned_time": self.planned_time,
            "delay": self.delay,
            "platform": self.platform,
            "transportation_type": self.transportation_type,
            "is_realtime": self.is_realtime,
            "minutes_until_departure": self.minutes_until_departure,
        }
        if self.description:
            result["description"] = self.description
        if self.agency:
            result["agency"] = self.agency
        return result


@dataclass
class UnifiedStop:
    """Unified stop data structure for stop search results.

    All providers map their stop search results to this structure.
    """

    id: str
    name: str
    place: Optional[str] = None  # City/place name
    area_type: Optional[str] = None  # e.g., "META_STOP", "stop", "station"
    transport_modes: Optional[list[str]] = None  # Available transport modes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for config flow."""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
        }
        if self.place:
            result["place"] = self.place
        if self.area_type:
            result["area_type"] = self.area_type
        if self.transport_modes is not None:
            result["transport_modes"] = self.transport_modes
        return result
