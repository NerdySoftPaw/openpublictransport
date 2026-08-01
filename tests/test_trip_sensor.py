"""Tests for trip_sensor.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VBN_API_KEY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.openpublictransport.trip_sensor import (
    CONF_IS_TRIP,
    CONF_TRIP_DESTINATION,
    CONF_TRIP_DESTINATION_CITY,
    CONF_TRIP_ORIGIN,
    CONF_TRIP_ORIGIN_CITY,
    CONF_TRIP_PROVIDER,
    TripDataUpdateCoordinator,
    TripSensor,
    async_setup_entry,
    async_setup_trip_entry,
)


def _make_trip_coordinator(hass, provider="vrr"):
    return TripDataUpdateCoordinator(
        hass,
        provider=provider,
        origin="Düsseldorf Hbf",
        origin_city="Düsseldorf",
        destination="Köln Hbf",
        destination_city="Köln",
        scan_interval=120,
    )


def _make_trip_entry(provider="vrr", is_trip=True, extra_data=None):
    data = {
        CONF_TRIP_PROVIDER: provider,
        CONF_TRIP_ORIGIN: "Düsseldorf Hbf",
        CONF_TRIP_ORIGIN_CITY: "Düsseldorf",
        CONF_TRIP_DESTINATION: "Köln Hbf",
        CONF_TRIP_DESTINATION_CITY: "Köln",
        CONF_IS_TRIP: is_trip,
        CONF_SCAN_INTERVAL: 120,
    }
    if extra_data:
        data.update(extra_data)
    return MockConfigEntry(domain=DOMAIN, entry_id="trip_test", data=data)


# ── TripDataUpdateCoordinator ─────────────────────────────────────────────────

async def test_coordinator_init(hass: HomeAssistant):
    """Test coordinator initializes correctly."""
    coordinator = _make_trip_coordinator(hass)
    assert coordinator.provider == "vrr"
    assert coordinator.origin == "Düsseldorf Hbf"
    assert coordinator.destination == "Köln Hbf"


async def test_coordinator_async_update_data(hass: HomeAssistant):
    """Test coordinator calls async_plan_trip."""
    coordinator = _make_trip_coordinator(hass)
    mock_journeys = [{"departure": "10:00", "arrival": "11:30", "duration_minutes": 90}]

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=mock_journeys,
    ):
        result = await coordinator._async_update_data()

    assert result == mock_journeys
    assert coordinator.last_update_success_time is not None


async def test_empty_journey_list_still_counts_as_a_successful_update(hass: HomeAssistant):
    """[] is "no connection right now", not a failure (issue #58 review).

    EFA's _parse_journeys returns [] for an empty board. The coordinator
    reports last_update_success=True for it, so diagnostics must not show a
    null last_update_success_time alongside that.
    """
    coordinator = _make_trip_coordinator(hass)

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=[],
    ):
        result = await coordinator._async_update_data()

    assert result == []
    assert coordinator.last_update_success_time is not None


async def test_failed_lookup_does_not_stamp_a_success_time(hass: HomeAssistant):
    """None means the lookup failed or the provider is unsupported."""
    coordinator = _make_trip_coordinator(hass)

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=None,
    ):
        result = await coordinator._async_update_data()

    assert result is None
    assert coordinator.last_update_success_time is None


# ── async_setup_trip_entry ────────────────────────────────────────────────────

async def test_async_setup_trip_entry_vrr(hass: HomeAssistant):
    """Test trip entry setup for a basic provider."""
    entry = _make_trip_entry(provider="vrr")
    entry.add_to_hass(hass)

    with patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock):
        with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
            result = await async_setup_trip_entry(hass, entry)

    assert result is True
    assert entry.runtime_data is not None


async def test_async_setup_trip_entry_vbn_otp(hass: HomeAssistant):
    """Test trip entry uses VBN API key."""
    entry = _make_trip_entry(provider="vbn_otp", extra_data={CONF_VBN_API_KEY: "my-vbn-key"})
    entry.add_to_hass(hass)

    with patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock):
        with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
            await async_setup_trip_entry(hass, entry)

    assert entry.runtime_data.api_key == "my-vbn-key"


async def test_async_setup_trip_entry_opt(hass: HomeAssistant):
    """Test trip entry uses OPT API key."""
    entry = _make_trip_entry(provider="openpublictransport", extra_data={CONF_OPT_API_KEY: "opt-key"})
    entry.add_to_hass(hass)

    with patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock):
        with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
            await async_setup_trip_entry(hass, entry)

    assert entry.runtime_data.api_key == "opt-key"


async def test_async_setup_trip_entry_otp_custom(hass: HomeAssistant):
    """Test trip entry uses OTP custom URL and key."""
    entry = _make_trip_entry(
        provider="otp_custom",
        extra_data={CONF_OTP_CUSTOM_API_KEY: "custom-key", CONF_OTP_BASE_URL: "http://myotp.local"},
    )
    entry.add_to_hass(hass)

    with patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock):
        with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
            await async_setup_trip_entry(hass, entry)

    assert entry.runtime_data.api_key == "custom-key"
    assert entry.runtime_data.custom_url == "http://myotp.local"


# ── async_setup_entry ─────────────────────────────────────────────────────────

async def test_async_setup_entry_adds_sensor(hass: HomeAssistant):
    """Test async_setup_entry adds TripSensor."""
    coordinator = _make_trip_coordinator(hass)
    entry = _make_trip_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = coordinator

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert isinstance(added[0], TripSensor)


async def test_async_setup_entry_skips_non_trip(hass: HomeAssistant):
    """Test async_setup_entry skips non-trip entries."""
    entry = _make_trip_entry(is_trip=False)
    entry.add_to_hass(hass)

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


async def test_async_setup_entry_no_coordinator(hass: HomeAssistant):
    """Test async_setup_entry skips when no coordinator."""
    entry = _make_trip_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    added = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert added == []


# ── TripSensor ────────────────────────────────────────────────────────────────

def test_trip_sensor_init(hass: HomeAssistant):
    """Test TripSensor unique_id and device_info."""
    coordinator = _make_trip_coordinator(hass)
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    assert "vrr_trip" in sensor._attr_unique_id
    assert sensor._attr_icon == "mdi:routes"
    assert sensor._attr_device_info is not None


def test_trip_sensor_native_value_no_data(hass: HomeAssistant):
    """Test native_value returns 'No connections' when no data."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = None
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    assert sensor.native_value == "No connections"


def test_trip_sensor_native_value_empty_list(hass: HomeAssistant):
    """Test native_value returns 'No connections' when empty list."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = []
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    assert sensor.native_value == "No connections"


def test_trip_sensor_native_value_with_journey(hass: HomeAssistant):
    """Test native_value shows first journey."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = [{"departure": "10:00", "arrival": "11:30", "duration_minutes": 90, "transfers": 1}]
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    value = sensor.native_value
    assert "10:00" in value
    assert "11:30" in value
    assert "90 min" in value


def test_trip_sensor_native_value_no_dep_arr(hass: HomeAssistant):
    """Test native_value fallback when departure/arrival missing."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = [{"duration_minutes": 90, "transfers": 0}]
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    assert sensor.native_value == "No connections"


def test_trip_sensor_extra_attributes_no_data(hass: HomeAssistant):
    """Test extra_state_attributes returns empty dict when no data."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = None
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    assert sensor.extra_state_attributes == {}


def test_trip_sensor_extra_attributes_with_journey(hass: HomeAssistant):
    """Test extra_state_attributes with one journey."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = [{
        "departure": "10:00", "arrival": "11:30", "duration_minutes": 90,
        "transfers": 1, "legs": [], "connection_feasible": True,
        "transfer_risk": "low", "min_transfer_time": 5,
    }]
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    attrs = sensor.extra_state_attributes
    assert attrs["departure"] == "10:00"
    assert attrs["alternative_journeys"] == 0
    assert "origin" in attrs
    assert "destination" in attrs


def test_trip_sensor_extra_attributes_multiple_journeys(hass: HomeAssistant):
    """Test extra_state_attributes includes next_journeys for alternatives."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = [
        {"departure": "10:00", "arrival": "11:30", "duration_minutes": 90, "transfers": 1, "legs": []},
        {"departure": "10:15", "arrival": "11:45", "duration_minutes": 90, "transfers": 0},
        {"departure": "10:30", "arrival": "12:00", "duration_minutes": 90, "transfers": 2},
    ]
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    attrs = sensor.extra_state_attributes
    assert attrs["alternative_journeys"] == 2
    assert "next_journeys" in attrs
    assert len(attrs["next_journeys"]) == 2


# ── restore state across restart ──────────────────────────────────────────────

from homeassistant.core import State
from pytest_homeassistant_custom_component.common import mock_restore_cache


def _mock_trip_coordinator(data=None):
    """A MagicMock trip coordinator (no real refresh timer to leave lingering)."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.provider = "vrr"
    coordinator.origin = "Düsseldorf Hbf"
    coordinator.origin_city = "Düsseldorf"
    coordinator.destination = "Köln Hbf"
    coordinator.destination_city = "Köln"
    return coordinator


async def test_trip_sensor_restores_last_state_when_no_data(hass: HomeAssistant):
    """With coordinator.data None, native_value/attrs fall back to the restored trip."""
    coordinator = _mock_trip_coordinator(data=None)
    entry = _make_trip_entry()
    entity_id = "sensor.opt_trip_restore"
    mock_restore_cache(
        hass,
        (State(entity_id, "10:00 → 11:00 (60 min, 0 transfers)", {"transfers": 0, "duration_minutes": 60}),),
    )
    sensor = TripSensor(coordinator, entry)
    sensor.hass = hass
    sensor.entity_id = entity_id
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_added_to_hass()

    assert sensor.native_value == "10:00 → 11:00 (60 min, 0 transfers)"
    assert sensor.extra_state_attributes["duration_minutes"] == 60


async def test_trip_sensor_empty_result_not_stale(hass: HomeAssistant):
    """A valid empty result ([]) shows 'No connections', never the restored trip."""
    coordinator = _mock_trip_coordinator(data=None)
    entry = _make_trip_entry()
    entity_id = "sensor.opt_trip_empty"
    mock_restore_cache(
        hass,
        (State(entity_id, "10:00 → 11:00 (60 min, 0 transfers)", {"transfers": 0}),),
    )
    sensor = TripSensor(coordinator, entry)
    sensor.hass = hass
    sensor.entity_id = entity_id
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_added_to_hass()  # restores (data is None)
    coordinator.data = []  # valid empty result arrives
    assert sensor.native_value == "No connections"
    assert sensor.extra_state_attributes == {}
