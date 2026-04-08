"""Common parsing utilities for all providers."""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .data_models import UnifiedDeparture

_LOGGER = logging.getLogger(__name__)


def parse_departure_generic(
    stop: Dict[str, Any],
    tz: Union[ZoneInfo, Any],
    now: datetime,
    get_transport_type_fn: Callable[[Dict[str, Any]], str],
    get_platform_fn: Callable[[Dict[str, Any]], str],
    get_realtime_fn: Callable[[Dict[str, Any], Optional[str], Optional[str]], bool],
) -> Optional[UnifiedDeparture]:
    """Generic parser for departure data - shared logic across all providers.

    Args:
        stop: Stop event data from API
        tz: Timezone object (provider-specific)
        now: Current datetime
        get_transport_type_fn: Function to determine transportation type
        get_platform_fn: Function to extract platform information
        get_realtime_fn: Function to check if realtime data is available

    Returns:
        UnifiedDeparture object or None if parsing fails
    """
    try:
        # Validate stop data structure
        if not isinstance(stop, dict):
            _LOGGER.debug("Invalid stop data: expected dict, got %s", type(stop))
            return None

        # Get times
        planned_time_str = stop.get("departureTimePlanned")
        estimated_time_str = stop.get("departureTimeEstimated")

        if not planned_time_str:
            _LOGGER.debug("Missing departureTimePlanned in stop data")
            return None

        # Validate time strings
        if not isinstance(planned_time_str, str):
            _LOGGER.debug("Invalid departureTimePlanned: expected str, got %s", type(planned_time_str))
            return None

        # Parse times
        planned_time = dt_util.parse_datetime(planned_time_str)
        estimated_time = dt_util.parse_datetime(estimated_time_str) if estimated_time_str else planned_time

        if not planned_time:
            _LOGGER.debug("Failed to parse departureTimePlanned: %s", planned_time_str)
            return None

        # Convert to local timezone with validation
        try:
            planned_local = planned_time.astimezone(tz)
            estimated_local = estimated_time.astimezone(tz) if estimated_time else planned_local
        except (ValueError, TypeError) as e:
            _LOGGER.debug("Failed to convert timezone: %s", e)
            return None

        # Calculate delay
        delay_minutes = int((estimated_local - planned_local).total_seconds() / 60)

        # Get transportation info with validation
        transportation = stop.get("transportation", {})
        if not isinstance(transportation, dict):
            _LOGGER.debug("Invalid transportation data: expected dict, got %s", type(transportation))
            transportation = {}

        destination_obj = transportation.get("destination", {})
        if not isinstance(destination_obj, dict):
            destination_obj = {}
        destination = destination_obj.get("name", "Unknown")

        line_number = str(transportation.get("number", ""))
        description = str(transportation.get("description", ""))
        agency = stop.get("agency")  # Agency name from GTFS (NTA/GTFS-DE)

        # Determine transportation type using provider-specific function
        transport_type = get_transport_type_fn(transportation)

        # Get platform/track info using provider-specific function
        platform = get_platform_fn(stop)

        # Calculate minutes until departure
        time_diff = estimated_local - now
        minutes_until = max(0, int(time_diff.total_seconds() / 60))

        # Determine if real-time data is available using provider-specific function
        is_realtime = get_realtime_fn(stop, estimated_time_str, planned_time_str)

        return UnifiedDeparture(
            line=line_number,
            destination=destination,
            departure_time=estimated_local.strftime("%H:%M"),
            planned_time=planned_local.strftime("%H:%M"),
            delay=delay_minutes,
            platform=platform,
            transportation_type=transport_type,
            is_realtime=is_realtime,
            minutes_until_departure=minutes_until,
            departure_time_obj=estimated_local,
            description=description if description else None,
            agency=agency if agency else None,
        )

    except Exception as e:
        _LOGGER.debug("Error parsing departure: %s", e)
        return None
