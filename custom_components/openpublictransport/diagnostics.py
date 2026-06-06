"""Diagnostics support for Open Public Transport integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    "station_id",
    "place_dm",
    "name_dm",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = getattr(entry, "runtime_data", None)

    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
    }

    if coordinator:
        diagnostics_data["coordinator"] = {
            "provider": coordinator.provider,
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": (
                coordinator.last_update_success_time.isoformat() if coordinator.last_update_success_time else None
            ),
            "update_interval": str(coordinator.update_interval),
            "api_calls_today": coordinator._api_calls_today,
            "last_api_reset": coordinator._last_api_reset.isoformat(),
            "departures_limit": coordinator.departures_limit,
        }

        # Add sample of last data (anonymized)
        if coordinator.data:
            stop_events = coordinator.data.get("stopEvents", [])
            diagnostics_data["last_api_response"] = {
                "stop_events_count": len(stop_events),
                "sample_event": _anonymize_stop_event(stop_events[0]) if stop_events else None,
            }

    return diagnostics_data


def _anonymize_stop_event(event: dict[str, Any]) -> dict[str, Any]:
    """Anonymize a stop event for diagnostics."""
    return {
        "has_departure_time_planned": "departureTimePlanned" in event,
        "has_departure_time_estimated": "departureTimeEstimated" in event,
        "transportation": {
            "product_class": event.get("transportation", {}).get("product", {}).get("class"),
            "product_name": event.get("transportation", {}).get("product", {}).get("name"),
        },
        "realtime_status": event.get("realtimeStatus", []),
        "is_realtime_controlled": event.get("isRealtimeControlled"),
    }
