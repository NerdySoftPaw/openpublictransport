"""Tests for OpenPublicTransport diagnostics."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import DOMAIN
from custom_components.openpublictransport.diagnostics import async_get_config_entry_diagnostics
from custom_components.openpublictransport.trip_sensor import TripDataUpdateCoordinator


async def test_diagnostics(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """Test diagnostics output."""
    # mock_config_entry already added to hass in fixture

    # Store coordinator in hass.data
    mock_config_entry.runtime_data = mock_coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert "entry" in diagnostics
    assert "coordinator" in diagnostics
    assert diagnostics["entry"]["title"] == "Test Station"
    assert diagnostics["entry"]["entry_type"] == "departure_monitor"
    assert diagnostics["entry"]["data"]["provider"] == "vrr"
    # place_dm and name_dm should be redacted
    assert diagnostics["entry"]["data"]["place_dm"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["name_dm"] == "**REDACTED**"

    # Verify API stats are included
    assert "api_calls_today" in diagnostics["coordinator"]
    assert "last_update_success" in diagnostics["coordinator"]
    assert "last_update_success_time" in diagnostics["coordinator"]
    assert diagnostics["coordinator"]["last_update_success_time"] is None

    # Departure-monitor payload is summarised, not dumped
    assert diagnostics["last_api_response"]["stop_events_count"] == len(mock_coordinator.data["stopEvents"])
    assert diagnostics["last_api_response"]["sample_event"]["has_departure_time_planned"] is True


async def test_diagnostics_no_coordinator(hass: HomeAssistant, mock_config_entry):
    """Test diagnostics when coordinator is not available."""
    # mock_config_entry already added to hass in fixture
    hass.data[DOMAIN] = {}

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # When no coordinator, the diagnostics should still have entry data but no coordinator
    assert "entry" in diagnostics
    assert "coordinator" not in diagnostics


def _trip_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a trip-planner config entry added to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="KVV Karlsruhe → Ettlingen",
        data={
            "is_trip": True,
            "trip_provider": "kvv",
            "trip_origin": "Hauptbahnhof",
            "trip_origin_city": "Karlsruhe",
            "trip_origin_id": "de:08212:1",
            "trip_destination": "Stadtbahnhof",
            "trip_destination_city": "Ettlingen",
            "trip_destination_id": "de:08215:2",
            "scan_interval": 120,
        },
        unique_id="kvv_trip_test",
    )
    entry.add_to_hass(hass)
    return entry


def _journey() -> dict:
    """Return a journey in the shape async_plan_trip produces."""
    return {
        "departure": "10:05",
        "arrival": "10:32",
        "duration_minutes": 27,
        "transfers": 1,
        "connection_feasible": True,
        "transfer_risk": "low",
        "min_transfer_time": 6,
        "legs": [
            {"origin": "Hauptbahnhof", "destination": "Marktplatz", "line": "S1", "product": "tram"},
            {"origin": "Marktplatz", "destination": "Stadtbahnhof", "line": "S2", "product": "train"},
        ],
    }


async def test_diagnostics_trip_entry(hass: HomeAssistant):
    """Trip entries produce diagnostics instead of raising AttributeError (issue #58).

    TripDataUpdateCoordinator has no _api_calls_today / _last_api_reset /
    departures_limit, and its data is a list of journeys rather than a
    {"stopEvents": [...]} dict.
    """
    entry = _trip_entry(hass)

    coordinator = TripDataUpdateCoordinator(
        hass,
        "kvv",
        "Hauptbahnhof",
        "Karlsruhe",
        "Stadtbahnhof",
        "Ettlingen",
        scan_interval=120,
        origin_id="de:08212:1",
        dest_id="de:08215:2",
    )
    coordinator.data = [_journey()]
    coordinator.last_update_success_time = datetime(2026, 7, 20, 15, 55, tzinfo=timezone.utc)
    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["entry_type"] == "trip"
    # Origin/destination are stop names — they must not leak
    assert diagnostics["entry"]["data"]["trip_origin"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["trip_destination"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["trip_origin_id"] == "**REDACTED**"

    coord = diagnostics["coordinator"]
    assert coord["coordinator_type"] == "TripDataUpdateCoordinator"
    assert coord["provider"] == "kvv"
    assert coord["last_update_success_time"] == "2026-07-20T15:55:00+00:00"
    # Departure-monitor-only fields are simply absent, not fatal
    assert "api_calls_today" not in coord
    assert "departures_limit" not in coord
    assert "last_api_reset" not in coord

    response = diagnostics["last_api_response"]
    assert response["journey_count"] == 1
    assert response["sample_journey"]["leg_count"] == 2
    assert response["sample_journey"]["leg_products"] == ["tram", "train"]
    assert response["sample_journey"]["transfer_risk"] == "low"
    # Stop names must not survive anonymisation
    assert "Hauptbahnhof" not in str(response)


async def test_diagnostics_trip_entry_without_data(hass: HomeAssistant):
    """A trip coordinator that never produced a journey still yields diagnostics."""
    entry = _trip_entry(hass)

    coordinator = TripDataUpdateCoordinator(
        hass,
        "vbn_otp",
        "Bremen Hbf",
        "Bremen",
        "Oldenburg Hbf",
        "Oldenburg",
    )
    coordinator.data = None
    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["coordinator"]["last_update_success_time"] is None
    assert "last_api_response" not in diagnostics


async def test_diagnostics_multi_stop_entry(hass: HomeAssistant):
    """Multi-stop entries have no coordinator at all."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Stop",
        data={
            "is_multi_stop": True,
            "source_entities": ["sensor.a", "sensor.b"],
            "multi_stop_name": "Zuhause",
        },
        unique_id="multi_stop_test",
    )
    entry.add_to_hass(hass)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["entry_type"] == "multi_stop"
    assert "coordinator" not in diagnostics


async def test_diagnostics_redacts_api_keys(hass: HomeAssistant):
    """API keys left in entry.data by older entries must be redacted."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="VBN",
        data={
            "provider": "vbn_otp",
            "station_id": "1:000009013845",
            "vbn_api_key": "super-secret",
        },
        unique_id="vbn_otp_test",
    )
    entry.add_to_hass(hass)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"]["vbn_api_key"] == "**REDACTED**"
    assert "super-secret" not in str(diagnostics)


async def test_coordinator_diagnostics_tolerates_partial_coordinator(hass: HomeAssistant, mock_config_entry):
    """A coordinator missing every optional attribute must not raise."""
    coordinator = MagicMock(spec=["provider", "last_update_success", "update_interval", "data"])
    coordinator.provider = "vrr"
    coordinator.last_update_success = False
    coordinator.update_interval = timedelta(seconds=60)
    coordinator.data = None
    mock_config_entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["coordinator"]["last_update_success"] is False
    assert diagnostics["coordinator"]["last_update_success_time"] is None
    assert diagnostics["coordinator"]["update_interval"] == "0:01:00"
    assert "last_api_response" not in diagnostics


async def test_missing_update_interval_is_null_not_the_string_none(hass: HomeAssistant, mock_config_entry):
    """A missing interval stays JSON null, like every other absent field."""
    coordinator = MagicMock(spec=["provider", "last_update_success", "data"])
    coordinator.provider = "vrr"
    coordinator.last_update_success = True
    coordinator.data = None
    mock_config_entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["coordinator"]["update_interval"] is None
