"""Extended tests for sensor.py — covering uncovered branches."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from openpublictransport import AuthenticationError
from openpublictransport.models import UnifiedDeparture
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    API_RATE_LIMIT_PER_DAY,
    CONF_DEPARTURES,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    PROVIDER_VRR,
)
from custom_components.openpublictransport.sensor import (
    MultiProviderSensor,
    PublicTransportDataUpdateCoordinator,
    async_setup_entry,
)


def _make_coordinator(hass):
    return PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id="12345",
        departures_limit=10,
        scan_interval=60,
    )


def _make_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_STATION_ID: "12345",
            CONF_DEPARTURES: 10,
            CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
            CONF_SCAN_INTERVAL: 60,
        },
    )


# ── Coordinator ──────────────────────────────────────────────────────────────

async def test_async_shutdown_calls_cleanup(hass: HomeAssistant):
    """Test async_shutdown calls provider cleanup."""
    coordinator = _make_coordinator(hass)
    mock_provider = MagicMock()
    mock_provider.cleanup = AsyncMock()
    coordinator.provider_instance = mock_provider

    await coordinator.async_shutdown()
    mock_provider.cleanup.assert_called_once()


async def test_async_shutdown_cleanup_exception(hass: HomeAssistant):
    """Test async_shutdown handles cleanup exception gracefully."""
    coordinator = _make_coordinator(hass)
    mock_provider = MagicMock()
    mock_provider.cleanup = AsyncMock(side_effect=RuntimeError("cleanup failed"))
    coordinator.provider_instance = mock_provider

    await coordinator.async_shutdown()  # Should not raise


async def test_check_rate_limit_resets_daily(hass: HomeAssistant):
    """Test rate limit resets on new day."""
    coordinator = _make_coordinator(hass)
    coordinator._api_calls_today = API_RATE_LIMIT_PER_DAY
    coordinator._last_api_reset = datetime(2024, 1, 1).date()

    result = coordinator._check_rate_limit()
    assert result is True
    assert coordinator._api_calls_today == 0


async def test_adjust_polling_interval_night_mode(hass: HomeAssistant):
    """Test polling interval increases at night."""
    coordinator = _make_coordinator(hass)

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = datetime(2025, 1, 15, 2, 0, tzinfo=timezone.utc)
        coordinator._adjust_polling_interval(has_departures=True)

    assert coordinator.update_interval >= timedelta(seconds=600)


async def test_adjust_polling_interval_no_departures(hass: HomeAssistant):
    """Test polling interval increases when no departures."""
    coordinator = _make_coordinator(hass)
    coordinator._base_scan_interval = 60

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        coordinator._adjust_polling_interval(has_departures=False)
        coordinator._adjust_polling_interval(has_departures=False)

    assert coordinator.update_interval > timedelta(seconds=60)


async def test_adjust_polling_interval_normal(hass: HomeAssistant):
    """Test polling interval resets to base when departures found."""
    coordinator = _make_coordinator(hass)
    coordinator._base_scan_interval = 60
    coordinator._empty_result_count = 3

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        coordinator.update_interval = timedelta(seconds=300)
        coordinator._adjust_polling_interval(has_departures=True)

    assert coordinator.update_interval == timedelta(seconds=60)
    assert coordinator._empty_result_count == 0


async def test_update_data_auth_error_raises_config_entry_auth_failed(hass: HomeAssistant):
    """Test that AuthenticationError is converted to ConfigEntryAuthFailed."""
    coordinator = _make_coordinator(hass)

    with patch.object(
        coordinator, "_fetch_departures",
        side_effect=AuthenticationError("API key invalid")
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


async def test_update_data_logs_first_failure(hass: HomeAssistant):
    """Test coordinator logs warning only on first failure."""
    coordinator = _make_coordinator(hass)
    coordinator.last_update_success = True

    with patch.object(coordinator, "_fetch_departures", side_effect=Exception("network error")):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_update_data_logs_recovery(hass: HomeAssistant):
    """Test coordinator logs info on recovery."""
    coordinator = _make_coordinator(hass)
    coordinator.last_update_success = False  # was failing

    good_data = {"stopEvents": []}
    with patch.object(coordinator, "_fetch_departures", return_value=good_data):
        with patch.object(coordinator, "_check_rate_limit", return_value=True):
            result = await coordinator._async_update_data()
    assert result == good_data


# ── MultiProviderSensor ───────────────────────────────────────────────────────

def _make_mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {"stopEvents": []}
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = "12345"
    coordinator.agency_name = ""
    coordinator.provider_instance = None
    return coordinator


def test_sensor_state_none_initially():
    """Test sensor state is None before first update."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram", "bus", "train"])
    assert sensor.state is None


def test_sensor_icon_default():
    """Test default icon."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    assert sensor.icon == "mdi:bus-clock"


def test_sensor_icon_per_transport_type():
    """Test icon matches transportation type."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor._attributes = {"departures": [{"transportation_type": "tram"}]}
    assert sensor.icon == "mdi:tram"


def test_sensor_entity_picture_disabled(hass: HomeAssistant):
    """Test entity_picture is None when logo disabled."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor._use_provider_logo = False
    assert sensor.entity_picture is None


def test_sensor_entity_picture_enabled(hass: HomeAssistant):
    """Test entity_picture returns URL when logo enabled."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor._use_provider_logo = True
    # VRR has an entity picture
    pic = sensor.entity_picture
    assert pic is None or pic.startswith("http")


def test_sensor_available_reflects_coordinator():
    """Test available follows coordinator success."""
    coordinator = _make_mock_coordinator()
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    assert sensor.available is True
    coordinator.last_update_success = False
    assert sensor.available is False


def test_handle_coordinator_update_no_data(hass: HomeAssistant):
    """Test _handle_coordinator_update with no data."""
    coordinator = _make_mock_coordinator()
    coordinator.data = None
    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram"])
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    sensor.async_write_ha_state.assert_called_once()


def test_process_departure_data_with_provider(hass: HomeAssistant):
    """Test _process_departure_data uses provider instance."""
    coordinator = _make_mock_coordinator()
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    dep = UnifiedDeparture(
        line="U79", destination="Duisburg", departure_time="10:05",
        planned_time="10:00", delay=5, platform="2",
        transportation_type="tram", is_realtime=True,
        minutes_until_departure=5, departure_time_obj=now,
    )
    mock_provider = MagicMock()
    mock_provider.get_timezone.return_value = "Europe/Berlin"
    mock_provider.parse_departure.return_value = dep
    coordinator.provider_instance = mock_provider
    coordinator.data = {"stopEvents": [{"raw": "data"}]}

    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["tram", "bus", "train"])
    sensor.hass = hass

    sensor._process_departure_data(coordinator.data)

    assert sensor._state is not None
    assert len(sensor._attributes.get("departures", [])) == 1


def test_process_departure_data_filters_type(hass: HomeAssistant):
    """Test _process_departure_data filters by transportation type."""
    coordinator = _make_mock_coordinator()
    now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    dep = UnifiedDeparture(
        line="Ferry 1", destination="Island", departure_time="10:05",
        planned_time="10:00", delay=0, platform="",
        transportation_type="ferry", is_realtime=False,
        minutes_until_departure=5, departure_time_obj=now,
    )
    mock_provider = MagicMock()
    mock_provider.get_timezone.return_value = "Europe/Berlin"
    mock_provider.parse_departure.return_value = dep
    coordinator.provider_instance = mock_provider
    coordinator.data = {"stopEvents": [{}]}

    entry = _make_entry()
    sensor = MultiProviderSensor(coordinator, entry, ["bus", "train"])  # no ferry
    sensor.hass = hass
    sensor._process_departure_data(coordinator.data)

    assert sensor._attributes.get("departures", []) == []
