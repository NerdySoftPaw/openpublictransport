"""Tests for trip_sensor.py."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from openpublictransport import ApiError, ApiTimeoutError, AuthenticationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VBN_API_KEY,
    CONF_WALKING_TIME,
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


def _make_trip_entry(provider="vrr", is_trip=True, extra_data=None, options=None):
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
    return MockConfigEntry(domain=DOMAIN, entry_id="trip_test", data=data, options=options or {})


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


# ── API failures make the entity unavailable (issue #88) ──────────────────────
#
# This coordinator had no exception handling at all: an outage left the entity
# "available", quietly serving its last known connection.


async def test_api_error_fails_the_update(hass: HomeAssistant):
    coordinator = _make_trip_coordinator(hass)

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, side_effect=ApiError("vrr", 503),
    ):
        with pytest.raises(UpdateFailed) as excinfo:
            await coordinator._async_update_data()

    assert "503" in str(excinfo.value)


async def test_connection_error_fails_the_update(hass: HomeAssistant):
    coordinator = _make_trip_coordinator(hass)

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, side_effect=ApiTimeoutError("timed out"),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_auth_error_triggers_reauth(hass: HomeAssistant):
    coordinator = _make_trip_coordinator(hass)

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, side_effect=AuthenticationError("vrr", 401),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


# ── departed connections are dropped (issue #72) ──────────────────────────────

def _journey_at(minutes_from_now, transfers=0):
    """A journey departing `minutes_from_now` (negative = already gone)."""
    departure = dt_util.now() + timedelta(minutes=minutes_from_now)
    return {
        "departure": departure.strftime("%H:%M"),
        "arrival": (departure + timedelta(minutes=28)).strftime("%H:%M"),
        "departure_timestamp": departure.isoformat(),
        "arrival_timestamp": (departure + timedelta(minutes=28)).isoformat(),
        "duration_minutes": 28,
        "transfers": transfers,
        "legs": [],
    }


async def test_coordinator_drops_already_departed_journeys(hass: HomeAssistant):
    """Connections whose departure has passed never reach the sensor (issue #72).

    EFA anchors the requested time on the first vehicle departure and back-dates
    the walk to the platform, so its first journey is regularly already running.
    """
    coordinator = _make_trip_coordinator(hass)
    journeys = [_journey_at(-8), _journey_at(-1), _journey_at(2), _journey_at(12)]

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=journeys,
    ):
        result = await coordinator._async_update_data()

    assert [j["departure"] for j in result] == [journeys[2]["departure"], journeys[3]["departure"]]


async def test_coordinator_keeps_journeys_without_timestamp(hass: HomeAssistant):
    """A journey we cannot date is kept — better unrated than an empty sensor."""
    coordinator = _make_trip_coordinator(hass)
    journeys = [{"departure": "10:00", "arrival": "11:30", "duration_minutes": 90}]

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=journeys,
    ):
        result = await coordinator._async_update_data()

    assert result == journeys


async def test_walking_time_shifts_the_requested_departure(hass: HomeAssistant):
    """With a walking time set, the query starts that many minutes from now.

    The user in issue #72 raised the walking time to 30 min and nothing changed,
    because the trip planner ignored the option entirely.
    """
    coordinator = _make_trip_coordinator(hass)
    coordinator.walking_time = 30

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=[_journey_at(10), _journey_at(45)],
    ) as mock_plan:
        result = await coordinator._async_update_data()

    requested = mock_plan.call_args.kwargs["departure_time"]
    assert 29 <= (requested - dt_util.now()).total_seconds() / 60 <= 30
    # A connection in 10 min is unreachable when the stop is a 30 min walk away
    assert len(result) == 1


async def test_without_walking_time_the_provider_keeps_its_own_clock(hass: HomeAssistant):
    """No walking time → no pinned departure, so a live server anchors on now."""
    coordinator = _make_trip_coordinator(hass)

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=[],
    ) as mock_plan:
        await coordinator._async_update_data()

    assert mock_plan.call_args.kwargs["departure_time"] is None


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


def test_trip_sensor_exposes_countdown_and_timestamps(hass: HomeAssistant):
    """Attributes carry full timestamps and a countdown, for both best and alternatives.

    A card can only tell a connection that is still ahead from one that has left
    if it gets more than an HH:MM string (issue #72).
    """
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = [_journey_at(7), _journey_at(17)]
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    attrs = sensor.extra_state_attributes
    assert attrs["in_minutes"] == 6  # 6:5x remaining, truncated
    assert dt_util.parse_datetime(attrs["departure_timestamp"]) is not None
    assert dt_util.parse_datetime(attrs["arrival_timestamp"]) is not None
    assert attrs["next_journeys"][0]["in_minutes"] == 16
    assert attrs["next_journeys"][0]["departure_timestamp"] is not None


def test_trip_sensor_countdown_is_none_without_timestamp(hass: HomeAssistant):
    """A journey without a timestamp reports no countdown instead of guessing."""
    coordinator = _make_trip_coordinator(hass)
    coordinator.data = [{"departure": "10:00", "arrival": "11:30", "duration_minutes": 90, "transfers": 0}]
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    assert sensor.extra_state_attributes["in_minutes"] is None


async def test_options_update_applies_walking_time_and_interval(hass: HomeAssistant):
    """Changing the options takes effect without a restart (issue #72)."""
    coordinator = _mock_trip_coordinator(data=[])
    coordinator.async_request_refresh = AsyncMock()
    entry = _make_trip_entry()
    sensor = TripSensor(coordinator, entry)

    updated_entry = _make_trip_entry(options={CONF_WALKING_TIME: 30, CONF_SCAN_INTERVAL: 300})

    await sensor._async_update_listener(hass, updated_entry)

    assert coordinator.walking_time == 30
    assert coordinator.update_interval == timedelta(seconds=300)
    coordinator.async_request_refresh.assert_awaited_once()


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


# ── line / transport-type filters (issue #87) ─────────────────────────────────

def _journey(*legs, departure="10:00"):
    """Build a parsed journey out of (line, transport_type) pairs."""
    return {
        "departure": departure,
        "arrival": "10:30",
        "legs": [{"line": line, "transport_type": transport_type} for line, transport_type in legs],
    }


def _filtering_coordinator(hass, line_filter=None, transport_types=None):
    return TripDataUpdateCoordinator(
        hass,
        provider="vrr",
        origin="Dortmund Hbf",
        origin_city="Dortmund",
        destination="Dortmund Stadtgarten",
        destination_city="Dortmund",
        scan_interval=120,
        line_filter=line_filter,
        transport_types=transport_types,
    )


async def test_unfiltered_coordinator_keeps_every_journey(hass: HomeAssistant):
    """Without filters the journey list is passed through untouched."""
    coordinator = _filtering_coordinator(hass)
    journeys = [_journey(("U43", "subway")), _journey(("400", "bus"))]

    assert coordinator._apply_filters(journeys) == journeys


async def test_line_filter_drops_journey_using_another_line(hass: HomeAssistant):
    """The bus 400 connection disappears once only U43/U47 are wanted."""
    coordinator = _filtering_coordinator(hass, line_filter={"u43", "u47"})
    wanted = _journey(("U43", "subway"))
    journeys = [wanted, _journey(("400", "bus"))]

    assert coordinator._apply_filters(journeys) == [wanted]


async def test_line_filter_rejects_journey_with_one_bad_leg(hass: HomeAssistant):
    """One disallowed leg removes the whole connection, not just that leg."""
    coordinator = _filtering_coordinator(hass, line_filter={"u43"})
    journeys = [_journey(("U43", "subway"), ("400", "bus"))]

    assert coordinator._apply_filters(journeys) == []


async def test_line_filter_ignores_walking_legs(hass: HomeAssistant):
    """A walk carries no line and must not fail the filter."""
    coordinator = _filtering_coordinator(hass, line_filter={"u43"})
    journey = _journey(("", "walk"), ("U43", "subway"))

    assert coordinator._apply_filters([journey]) == [journey]


async def test_transport_type_filter_drops_deselected_type(hass: HomeAssistant):
    """Deselecting 'bus' on the device removes bus connections."""
    coordinator = _filtering_coordinator(hass, transport_types={"subway", "tram", "train"})
    wanted = _journey(("U43", "subway"))
    journeys = [wanted, _journey(("400", "bus"))]

    assert coordinator._apply_filters(journeys) == [wanted]


async def test_transport_type_filter_keeps_types_the_form_never_offered(hass: HomeAssistant):
    """A ferry leg survives the default selection, which cannot deselect it."""
    coordinator = _filtering_coordinator(hass, transport_types={"bus", "tram", "subway", "train"})
    journey = _journey(("F1", "ferry"))

    assert coordinator._apply_filters([journey]) == [journey]


async def test_unknown_transport_type_is_not_filtered(hass: HomeAssistant):
    """An untypable leg is kept rather than hidden on a guess."""
    coordinator = _filtering_coordinator(hass, transport_types={"subway"})
    journey = _journey(("X1", "unknown"))

    assert coordinator._apply_filters([journey]) == [journey]


async def test_filters_applied_to_fetched_data(hass: HomeAssistant):
    """The coordinator filters what the provider returns, not just in isolation."""
    coordinator = _filtering_coordinator(hass, line_filter={"u43"})
    fetched = [_journey(("U43", "subway")), _journey(("400", "bus"))]

    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=fetched,
    ):
        result = await coordinator._async_update_data()

    assert [leg["line"] for journey in result for leg in journey["legs"]] == ["U43"]


async def test_setup_reads_filters_from_entry_options(hass: HomeAssistant):
    """A trip device's configured filters reach the coordinator (issue #87)."""
    entry = _make_trip_entry(options={"line_filter": "U43, U47", "transportation_types": ["subway", "tram"]})
    entry.add_to_hass(hass)

    with patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock):
        with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
            await async_setup_trip_entry(hass, entry)

    coordinator = entry.runtime_data
    assert coordinator.line_filter == {"u43", "u47"}
    assert coordinator.transport_types == {"subway", "tram"}


async def test_options_update_refreshes_filters(hass: HomeAssistant):
    """Editing the filters takes effect without a restart."""
    coordinator = _filtering_coordinator(hass)
    entry = _make_trip_entry(options={"line_filter": "U47", "transportation_types": ["subway"]})
    sensor = TripSensor(coordinator, entry)
    coordinator.async_request_refresh = AsyncMock()

    await sensor._async_update_listener(hass, entry)

    assert coordinator.line_filter == {"u47"}
    assert coordinator.transport_types == {"subway"}
