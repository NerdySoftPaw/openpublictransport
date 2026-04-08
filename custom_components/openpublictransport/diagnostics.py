"""Diagnostics support for Open Public Transport integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

TO_REDACT = {
    "station_id",
    "place_dm",
    "name_dm",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    # Get coordinator from hass.data
    coordinator = None

    # First try to get from entity registry
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    for entity in entities:
        if entity.platform == DOMAIN:
            entity_obj = hass.data.get("entity_components", {}).get("sensor")
            if entity_obj:
                for ent in entity_obj.entities:
                    if ent.unique_id == entity.unique_id:
                        coordinator = ent.coordinator
                        break

    # Fallback: try to get coordinator directly from hass.data (useful for tests)
    if not coordinator:
        coordinator_key = f"{entry.entry_id}_coordinator"
        coordinator = hass.data.get(DOMAIN, {}).get(coordinator_key)

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
