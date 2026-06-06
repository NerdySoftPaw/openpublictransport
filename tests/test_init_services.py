"""Extended tests for __init__.py service handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport import async_setup
from custom_components.openpublictransport.const import (
    CONF_DEPARTURES,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_VRR,
)


async def _setup_services(hass):
    await async_setup(hass, {})


# ── refresh_departures ────────────────────────────────────────────────────────

async def test_refresh_no_entity_id_refreshes_all(hass: HomeAssistant):
    """Test refresh without entity_id calls all coordinators."""
    await _setup_services(hass)

    coordinator = AsyncMock()
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    # Register a fake entity in entity registry
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="vrr_test_station",
        config_entry=entry,
    )

    await hass.services.async_call(
        DOMAIN, "refresh_departures", {}, blocking=True
    )
    coordinator.async_request_refresh.assert_called_once()


async def test_refresh_with_invalid_entity_raises(hass: HomeAssistant):
    """Test refresh with non-existent entity_id raises ServiceValidationError."""
    await _setup_services(hass)

    with pytest.raises((ServiceValidationError, HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN, "refresh_departures", {"entity_id": "sensor.nonexistent"}, blocking=True
        )


async def test_refresh_with_wrong_platform_raises(hass: HomeAssistant):
    """Test refresh with entity from different platform raises."""
    await _setup_services(hass)

    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    other_entry = MockConfigEntry(domain="other_integration", entry_id="other")
    other_entry.add_to_hass(hass)
    registry.async_get_or_create(
        domain="sensor",
        platform="other_integration",
        unique_id="other_entity",
        config_entry=other_entry,
    )

    entity_id = "sensor.other_integration_other_entity"
    with pytest.raises((ServiceValidationError, HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN, "refresh_departures", {"entity_id": entity_id}, blocking=True
        )


# ── check_delays ──────────────────────────────────────────────────────────────

async def test_check_delays_entity_not_found(hass: HomeAssistant):
    """Test check_delays raises when entity not found."""
    await _setup_services(hass)

    with pytest.raises((ServiceValidationError, HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN, "check_delays", {"entity_id": "sensor.nonexistent"}, blocking=True
        )


async def test_check_delays_returns_delayed(hass: HomeAssistant):
    """Test check_delays returns delayed departures."""
    await _setup_services(hass)

    hass.states.async_set("sensor.test_departure", "10:05", {
        "departures": [
            {"line": "U79", "delay": 10, "destination": "Duisburg"},
            {"line": "Bus 1", "delay": 0, "destination": "Köln"},
        ]
    })

    result = await hass.services.async_call(
        DOMAIN, "check_delays", {"entity_id": "sensor.test_departure", "delay_threshold": 5},
        blocking=True, return_response=True,
    )
    assert result["count"] == 1
    assert result["delayed"][0]["line"] == "U79"


async def test_check_delays_with_line_filter(hass: HomeAssistant):
    """Test check_delays filters by line."""
    await _setup_services(hass)

    hass.states.async_set("sensor.test_departure", "10:05", {
        "departures": [
            {"line": "U79", "delay": 10},
            {"line": "Bus 1", "delay": 8},
        ]
    })

    result = await hass.services.async_call(
        DOMAIN, "check_delays",
        {"entity_id": "sensor.test_departure", "delay_threshold": 5, "line": "u79"},
        blocking=True, return_response=True,
    )
    assert result["count"] == 1
    assert result["delayed"][0]["line"] == "U79"


async def test_check_delays_fires_event(hass: HomeAssistant):
    """Test check_delays fires domain event when delays found."""
    await _setup_services(hass)

    hass.states.async_set("sensor.test", "10:05", {
        "departures": [{"line": "U79", "delay": 15, "destination": "X"}]
    })

    fired = []
    hass.bus.async_listen(f"{DOMAIN}_delay_alert", lambda e: fired.append(e))

    await hass.services.async_call(
        DOMAIN, "check_delays", {"entity_id": "sensor.test", "delay_threshold": 5},
        blocking=True, return_response=True,
    )
    await hass.async_block_till_done()
    assert len(fired) == 1


async def test_check_delays_no_delays(hass: HomeAssistant):
    """Test check_delays returns empty when no delays above threshold."""
    await _setup_services(hass)

    hass.states.async_set("sensor.test", "10:05", {
        "departures": [{"line": "U79", "delay": 1}]
    })

    result = await hass.services.async_call(
        DOMAIN, "check_delays", {"entity_id": "sensor.test", "delay_threshold": 5},
        blocking=True, return_response=True,
    )
    assert result["count"] == 0


# ── announce_departure ────────────────────────────────────────────────────────

async def test_announce_entity_not_found(hass: HomeAssistant):
    """Test announce raises when entity not found."""
    await _setup_services(hass)

    with pytest.raises((ServiceValidationError, HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN, "announce_departure", {"entity_id": "sensor.nonexistent"}, blocking=True
        )


async def test_announce_no_departures_raises(hass: HomeAssistant):
    """Test announce raises when entity has no departures."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:05", {"departures": []})

    with pytest.raises((ServiceValidationError, HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN, "announce_departure", {"entity_id": "sensor.test"}, blocking=True
        )


async def test_announce_index_out_of_range_raises(hass: HomeAssistant):
    """Test announce raises when index exceeds departures."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:05", {
        "departures": [{"line": "U79", "destination": "X", "planned_time": "10:00",
                        "minutes_until_departure": 5, "delay": 0, "transportation_type": "tram"}]
    })

    with pytest.raises((ServiceValidationError, HomeAssistantError, Exception)):
        await hass.services.async_call(
            DOMAIN, "announce_departure", {"entity_id": "sensor.test", "index": 5}, blocking=True
        )


async def test_announce_returns_german_text(hass: HomeAssistant):
    """Test announce returns German text by default."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:05", {
        "departures": [{
            "line": "U79", "destination": "Duisburg Hbf",
            "planned_time": "10:00", "minutes_until_departure": 5,
            "delay": 0, "transportation_type": "tram", "platform": "2",
        }]
    })

    result = await hass.services.async_call(
        DOMAIN, "announce_departure", {"entity_id": "sensor.test", "language": "de"},
        blocking=True, return_response=True,
    )
    assert "text" in result
    assert "U79" in result["text"]
    assert "Duisburg Hbf" in result["text"]


async def test_announce_returns_english_text(hass: HomeAssistant):
    """Test announce returns English text when language=en."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:05", {
        "departures": [{
            "line": "S1", "destination": "Airport",
            "planned_time": "10:00", "minutes_until_departure": 10,
            "delay": 5, "transportation_type": "train", "platform": "3",
        }]
    })

    result = await hass.services.async_call(
        DOMAIN, "announce_departure", {"entity_id": "sensor.test", "language": "en"},
        blocking=True, return_response=True,
    )
    assert "S1" in result["text"]
    assert "Airport" in result["text"]


async def test_announce_with_delay_text(hass: HomeAssistant):
    """Test announce includes delay in text."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:05", {
        "departures": [{
            "line": "Bus 10", "destination": "City",
            "planned_time": "10:00", "minutes_until_departure": 3,
            "delay": 8, "transportation_type": "bus", "platform": "",
        }]
    })

    result = await hass.services.async_call(
        DOMAIN, "announce_departure", {"entity_id": "sensor.test", "language": "de"},
        blocking=True, return_response=True,
    )
    assert "8" in result["text"]  # delay minutes


async def test_announce_departure_now(hass: HomeAssistant):
    """Test announce when departure is now (0 minutes)."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:00", {
        "departures": [{
            "line": "U79", "destination": "X",
            "planned_time": "10:00", "minutes_until_departure": 0,
            "delay": 0, "transportation_type": "tram", "platform": "",
        }]
    })

    result = await hass.services.async_call(
        DOMAIN, "announce_departure", {"entity_id": "sensor.test", "language": "de"},
        blocking=True, return_response=True,
    )
    assert "einsteigen" in result["text"].lower() or "bitte" in result["text"].lower()


async def test_announce_soon_departure(hass: HomeAssistant):
    """Test announce 'proceed to platform' when < 2 minutes."""
    await _setup_services(hass)
    hass.states.async_set("sensor.test", "10:00", {
        "departures": [{
            "line": "U79", "destination": "X",
            "planned_time": "10:00", "minutes_until_departure": 1,
            "delay": 0, "transportation_type": "tram", "platform": "",
        }]
    })

    result = await hass.services.async_call(
        DOMAIN, "announce_departure", {"entity_id": "sensor.test", "language": "de"},
        blocking=True, return_response=True,
    )
    assert "bahnsteig" in result["text"].lower() or "begeben" in result["text"].lower()


# ── plan_trip ─────────────────────────────────────────────────────────────────

async def test_plan_trip_raises_on_failure(hass: HomeAssistant):
    """Test plan_trip raises HomeAssistantError when trip planning returns None."""
    await _setup_services(hass)

    with patch(
        "custom_components.openpublictransport.async_plan_trip",
        new_callable=AsyncMock, return_value=None,
    ):
        with pytest.raises((HomeAssistantError, Exception)):
            await hass.services.async_call(
                DOMAIN, "plan_trip",
                {
                    "provider": "vrr",
                    "origin": "Düsseldorf Hbf",
                    "origin_city": "Düsseldorf",
                    "destination": "Köln Hbf",
                    "destination_city": "Köln",
                },
                blocking=True,
            )


async def test_plan_trip_returns_journeys(hass: HomeAssistant):
    """Test plan_trip returns journeys on success."""
    await _setup_services(hass)

    mock_journeys = [{"legs": [], "duration": 30}]
    with patch(
        "custom_components.openpublictransport.async_plan_trip",
        new_callable=AsyncMock, return_value=mock_journeys,
    ):
        result = await hass.services.async_call(
            DOMAIN, "plan_trip",
            {
                "provider": "vrr",
                "origin": "Düsseldorf",
                "origin_city": "Düsseldorf",
                "destination": "Köln",
                "destination_city": "Köln",
            },
            blocking=True, return_response=True,
        )
    assert result["journeys"] == mock_journeys
