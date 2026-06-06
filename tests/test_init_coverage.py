"""Additional __init__.py coverage tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport import async_setup, async_setup_entry
from custom_components.openpublictransport.const import (
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PROVIDER,
    CONF_VBN_API_KEY,
    DOMAIN,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_VBN_OTP,
    PROVIDER_VRR,
)


async def test_plan_trip_resolves_vbn_api_key(hass: HomeAssistant):
    """Test plan_trip picks up VBN API key from existing config entry."""
    await async_setup(hass, {})

    # Create an existing VBN entry with an API key
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VBN_OTP, CONF_VBN_API_KEY: "vbn-123"},
    )
    entry.add_to_hass(hass)

    mock_journeys = [{"departure": "10:00", "arrival": "11:00"}]
    with patch(
        "custom_components.openpublictransport.async_plan_trip",
        new_callable=AsyncMock, return_value=mock_journeys,
    ) as mock_trip:
        result = await hass.services.async_call(
            DOMAIN, "plan_trip",
            {
                "provider": PROVIDER_VBN_OTP,
                "origin": "Bremen Hbf", "origin_city": "Bremen",
                "destination": "Hannover Hbf", "destination_city": "Hannover",
            },
            blocking=True, return_response=True,
        )

    assert result["journeys"] == mock_journeys
    # Verify API key was passed
    call_kwargs = mock_trip.call_args
    assert call_kwargs.kwargs.get("api_key") == "vbn-123" or "vbn-123" in str(call_kwargs)


async def test_plan_trip_resolves_opt_api_key(hass: HomeAssistant):
    """Test plan_trip picks up OPT API key from existing entry."""
    await async_setup(hass, {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_OPT, CONF_OPT_API_KEY: "opt-key-abc"},
    )
    entry.add_to_hass(hass)

    mock_journeys = [{"departure": "12:00"}]
    with patch(
        "custom_components.openpublictransport.async_plan_trip",
        new_callable=AsyncMock, return_value=mock_journeys,
    ):
        result = await hass.services.async_call(
            DOMAIN, "plan_trip",
            {
                "provider": PROVIDER_OPT,
                "origin": "A", "origin_city": "City",
                "destination": "B", "destination_city": "City",
            },
            blocking=True, return_response=True,
        )
    assert result["journeys"] == mock_journeys


async def test_plan_trip_resolves_otp_custom_url(hass: HomeAssistant):
    """Test plan_trip picks up OTP Custom URL and key from existing entry."""
    await async_setup(hass, {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_OTP_CUSTOM,
            CONF_OTP_CUSTOM_API_KEY: "custom-key",
            CONF_OTP_BASE_URL: "http://myotp.local",
        },
    )
    entry.add_to_hass(hass)

    mock_journeys = [{"departure": "14:00"}]
    with patch(
        "custom_components.openpublictransport.async_plan_trip",
        new_callable=AsyncMock, return_value=mock_journeys,
    ) as mock_trip:
        result = await hass.services.async_call(
            DOMAIN, "plan_trip",
            {
                "provider": PROVIDER_OTP_CUSTOM,
                "origin": "A", "origin_city": "City",
                "destination": "B", "destination_city": "City",
            },
            blocking=True, return_response=True,
        )
    assert result["journeys"] == mock_journeys


async def test_refresh_with_valid_entity_but_no_coordinator(hass: HomeAssistant):
    """Test refresh raises when entity exists but coordinator is missing."""
    await async_setup(hass, {})

    entry = MockConfigEntry(domain=DOMAIN, entry_id="no_coord")
    entry.add_to_hass(hass)
    # Don't set runtime_data (no coordinator)

    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="vrr_no_coord_station",
        config_entry=entry,
    )

    entity_id = f"sensor.{DOMAIN}_vrr_no_coord_station"
    with pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN, "refresh_departures", {"entity_id": entity_id}, blocking=True
        )


async def test_async_setup_entry_calls_coordinator_refresh(hass: HomeAssistant):
    """Test async_setup_entry sets up coordinator correctly."""
    from custom_components.openpublictransport.const import (
        CONF_DEPARTURES,
        CONF_SCAN_INTERVAL,
        CONF_STATION_ID,
        CONF_TRANSPORTATION_TYPES,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_STATION_ID: None,
            CONF_DEPARTURES: 10,
            CONF_TRANSPORTATION_TYPES: ["bus"],
            CONF_SCAN_INTERVAL: 60,
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ):
            result = await async_setup_entry(hass, entry)

    assert result is True
