"""Diagnostics support for Open Public Transport integration."""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_OPT_API_KEY,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_REJSEPLANEN_API_KEY,
    CONF_RMV_API_KEY,
    CONF_TRAFIKLAB_API_KEY,
    CONF_VBN_API_KEY,
)

TO_REDACT = {
    "station_id",
    "place_dm",
    "name_dm",
    # Trip planner entries
    "trip_origin",
    "trip_origin_city",
    "trip_origin_id",
    "trip_destination",
    "trip_destination_city",
    "trip_destination_id",
    # Credentials — these normally live in the Application Credentials store,
    # but older entries and the reconfigure path can still carry them in data.
    CONF_TRAFIKLAB_API_KEY,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_RMV_API_KEY,
    CONF_VBN_API_KEY,
    CONF_OPT_API_KEY,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_REJSEPLANEN_API_KEY,
}


def _entry_type(entry: ConfigEntry) -> str:
    """Return which of the three entry flavours this config entry is."""
    if entry.data.get("is_trip"):
        return "trip"
    if entry.data.get("is_multi_stop"):
        return "multi_stop"
    return "departure_monitor"


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = getattr(entry, "runtime_data", None)

    diagnostics_data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "entry_type": _entry_type(entry),
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
    }

    if coordinator:
        diagnostics_data["coordinator"] = _coordinator_diagnostics(coordinator)

        last_response = _last_response_diagnostics(coordinator)
        if last_response is not None:
            diagnostics_data["last_api_response"] = last_response

    return diagnostics_data


def _coordinator_diagnostics(coordinator: Any) -> dict[str, Any]:
    """Describe a coordinator without assuming which flavour it is.

    The departure monitor (`PublicTransportDataUpdateCoordinator`) and the trip
    planner (`TripDataUpdateCoordinator`) do not share a shape — the trip
    coordinator has no API-call budget and no departure limit — so every
    flavour-specific attribute is read defensively (issue #58).
    """
    data: dict[str, Any] = {
        "coordinator_type": type(coordinator).__name__,
        "provider": getattr(coordinator, "provider", None),
        "last_update_success": getattr(coordinator, "last_update_success", None),
        "last_update_success_time": _isoformat(getattr(coordinator, "last_update_success_time", None)),
        "update_interval": str(getattr(coordinator, "update_interval", None)),
    }

    for key, attr in (
        ("api_calls_today", "_api_calls_today"),
        ("departures_limit", "departures_limit"),
    ):
        value = getattr(coordinator, attr, None)
        if value is not None:
            data[key] = value

    last_api_reset = getattr(coordinator, "_last_api_reset", None)
    if last_api_reset is not None:
        data["last_api_reset"] = _isoformat(last_api_reset)

    return data


def _last_response_diagnostics(coordinator: Any) -> Optional[dict[str, Any]]:
    """Summarise the coordinator's last payload, whatever shape it has."""
    data = getattr(coordinator, "data", None)

    # Departure monitor: {"stopEvents": [...]}
    if isinstance(data, dict):
        stop_events = data.get("stopEvents", [])
        if not isinstance(stop_events, list):
            stop_events = []
        return {
            "stop_events_count": len(stop_events),
            "sample_event": _anonymize_stop_event(stop_events[0]) if stop_events else None,
        }

    # Trip planner: a list of journey dicts
    if isinstance(data, list):
        return {
            "journey_count": len(data),
            "sample_journey": _anonymize_journey(data[0]) if data else None,
        }

    return None


def _isoformat(value: Any) -> Optional[str]:
    """Return ``value.isoformat()`` when value is datetime-like, else None."""
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else None


def _anonymize_stop_event(event: Any) -> Optional[dict[str, Any]]:
    """Anonymize a stop event for diagnostics."""
    if not isinstance(event, dict):
        return None

    transportation = event.get("transportation")
    if not isinstance(transportation, dict):
        transportation = {}
    product = transportation.get("product")
    if not isinstance(product, dict):
        product = {}

    return {
        "has_departure_time_planned": "departureTimePlanned" in event,
        "has_departure_time_estimated": "departureTimeEstimated" in event,
        "transportation": {
            "product_class": product.get("class"),
            "product_name": product.get("name"),
        },
        "realtime_status": event.get("realtimeStatus", []),
        "is_realtime_controlled": event.get("isRealtimeControlled"),
    }


def _anonymize_journey(journey: Any) -> Optional[dict[str, Any]]:
    """Anonymize a trip-planner journey for diagnostics.

    Keeps the structure that matters when debugging a trip — leg count,
    products, transfer assessment — and drops the stop names.
    """
    if not isinstance(journey, dict):
        return None

    legs = journey.get("legs")
    if not isinstance(legs, list):
        legs = []

    return {
        "leg_count": len(legs),
        "leg_products": [leg.get("product") for leg in legs if isinstance(leg, dict)],
        "has_departure": bool(journey.get("departure")),
        "has_arrival": bool(journey.get("arrival")),
        "duration_minutes": journey.get("duration_minutes"),
        "transfers": journey.get("transfers"),
        "connection_feasible": journey.get("connection_feasible"),
        "transfer_risk": journey.get("transfer_risk"),
        "min_transfer_time": journey.get("min_transfer_time"),
    }
