"""Tests for OpenPublicTransport sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.openpublictransport.const import API_RATE_LIMIT_PER_DAY, DOMAIN, PROVIDER_VRR
from custom_components.openpublictransport.sensor import (
    MultiProviderSensor,
    PublicTransportDataUpdateCoordinator,
    async_setup_entry,
)


async def test_coordinator_update(hass: HomeAssistant, mock_api_response):
    """Test coordinator data update."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
    )

    with patch.object(coordinator, "_fetch_departures", return_value=mock_api_response):
        await coordinator.async_refresh()

        assert coordinator.data == mock_api_response
        assert coordinator.last_update_success is True


async def test_coordinator_rate_limit(hass: HomeAssistant):
    """Test rate limiting in coordinator."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
    )

    # Simulate hitting rate limit
    coordinator._api_calls_today = API_RATE_LIMIT_PER_DAY

    with patch.object(coordinator, "_fetch_departures") as mock_fetch:
        # Should not call API when rate limited
        assert coordinator._check_rate_limit() is False

        # With existing data, should return it
        coordinator.data = {"stopEvents": []}
        result = await coordinator._async_update_data()
        assert result == {"stopEvents": []}
        mock_fetch.assert_not_called()


async def test_coordinator_api_error(hass: HomeAssistant):
    """Test coordinator handling API errors."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
    )

    with patch.object(coordinator, "_fetch_departures", side_effect=Exception("API Error")):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_sensor_state(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test sensor state updates."""
    # Test with provider instance
    from openpublictransport import get_provider

    mock_coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)
    sensor = MultiProviderSensor(
        mock_coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Mock datetime to have consistent time
    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2025-01-15T09:55:00Z")

        # Call _process_departure_data directly instead of _handle_coordinator_update
        # to avoid needing hass to be set
        sensor._process_departure_data(mock_coordinator.data)

        # Verify state is set to next departure time
        assert sensor._state is not None
        assert isinstance(sensor._attributes, dict)
        assert "departures" in sensor._attributes
        assert "total_departures" in sensor._attributes


async def test_sensor_icon(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test sensor icon changes based on transport type."""
    sensor = MultiProviderSensor(
        mock_coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Set attributes with different transportation types
    sensor._attributes = {
        "departures": [
            {"transportation_type": "bus", "line": "721"},
            {"transportation_type": "train", "line": "RE1"},
        ]
    }

    # Icon should reflect first departure type
    icon = sensor.icon
    assert icon == "mdi:bus-clock"

    # Change first departure to train
    sensor._attributes["departures"][0]["transportation_type"] = "train"
    icon = sensor.icon
    assert icon == "mdi:train"


async def test_sensor_no_departures(hass: HomeAssistant, mock_config_entry):
    """Test sensor with no departures."""
    coordinator = MagicMock()
    coordinator.data = {"stopEvents": []}
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None
    coordinator.departures_limit = 10

    # Test with provider instance
    from openpublictransport import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    sensor = MultiProviderSensor(
        coordinator,
        mock_config_entry,
        ["bus", "train", "tram"],
    )

    # Call _process_departure_data directly to avoid needing hass
    sensor._process_departure_data(coordinator.data)

    assert sensor._state == "No departures"
    assert sensor._attributes["total_departures"] == 0
    assert sensor._attributes["departures"] == []


async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_api_response):
    """Test sensor platform setup."""
    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        provider="vrr",
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=10,
        scan_interval=60,
        config_entry=mock_config_entry,
    )
    mock_config_entry.runtime_data = coordinator

    with patch.object(coordinator, "_fetch_departures", return_value=mock_api_response):
        entities = []

        def mock_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        assert len(entities) == 2  # MultiProviderSensor + PunctualitySensor
        assert isinstance(entities[0], MultiProviderSensor)


async def test_sensor_transportation_type_filtering(hass: HomeAssistant, mock_config_entry):
    """Test filtering departures by transportation type."""
    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:00:00Z",
                "transportation": {
                    "number": "U79",
                    "destination": {"name": "Duisburg"},
                    "description": "Tram",
                    "product": {"class": 4, "name": "Tram"},
                },
                "platform": {"name": "2"},
                "realtimeStatus": ["MONITORED"],
            },
            {
                "departureTimePlanned": "2025-01-15T10:05:00Z",
                "departureTimeEstimated": "2025-01-15T10:05:00Z",
                "transportation": {
                    "number": "721",
                    "destination": {"name": "Krefeld"},
                    "description": "Bus",
                    "product": {"class": 5, "name": "Bus"},
                },
                "platform": {"name": "5"},
                "realtimeStatus": ["MONITORED"],
            },
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None
    coordinator.departures_limit = 10

    # Test with provider instance
    from openpublictransport import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    # Only allow trams
    sensor = MultiProviderSensor(coordinator, mock_config_entry, ["tram"])

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2025-01-15T09:55:00Z")
        # Call _process_departure_data directly to avoid needing hass
        sensor._process_departure_data(coordinator.data)

    # Should only have tram departures
    departures = sensor._attributes.get("departures", [])
    assert len(departures) == 1
    assert departures[0]["transportation_type"] == "tram"


async def test_sensor_destination_filtering(hass: HomeAssistant):
    """Test filtering departures by destination (case-insensitive substring)."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.openpublictransport.const import (
        CONF_DESTINATION_FILTER,
        CONF_PROVIDER,
        CONF_STATION_ID,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Station",
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_STATION_ID: None,
        },
        options={CONF_DESTINATION_FILTER: "duisburg"},
        unique_id="vrr_dest_filter",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "departureTimePlanned": "2025-01-15T10:00:00Z",
                "departureTimeEstimated": "2025-01-15T10:00:00Z",
                "transportation": {
                    "number": "U79",
                    "destination": {"name": "Duisburg Hbf"},
                    "description": "Tram",
                    "product": {"class": 4, "name": "Tram"},
                },
                "platform": {"name": "2"},
                "realtimeStatus": ["MONITORED"],
            },
            {
                "departureTimePlanned": "2025-01-15T10:05:00Z",
                "departureTimeEstimated": "2025-01-15T10:05:00Z",
                "transportation": {
                    "number": "721",
                    "destination": {"name": "Krefeld"},
                    "description": "Bus",
                    "product": {"class": 5, "name": "Bus"},
                },
                "platform": {"name": "5"},
                "realtimeStatus": ["MONITORED"],
            },
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VRR
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.station_id = None
    coordinator.departures_limit = 10

    from openpublictransport import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)

    sensor = MultiProviderSensor(coordinator, entry, ["bus", "tram"])

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2025-01-15T09:55:00Z")
        sensor._process_departure_data(coordinator.data)

    # Only the "Duisburg Hbf" departure matches the "duisburg" substring filter
    departures = sensor._attributes.get("departures", [])
    assert len(departures) == 1
    assert departures[0]["destination"] == "Duisburg Hbf"


async def test_sensor_exposes_efa_platform(hass: HomeAssistant):
    """EFA departures reach HA with their platform filled in (issue #56).

    The track lives at location.properties.platform in EFA's RapidJSON. Needs
    python-openpublictransport >= 0.1.15.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.openpublictransport.const import CONF_PROVIDER, CONF_STATION_ID, PROVIDER_VVS

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="VVS Stuttgart - Vaihingen",
        data={
            CONF_PROVIDER: PROVIDER_VVS,
            "place_dm": "Stuttgart",
            "name_dm": "Vaihingen",
            CONF_STATION_ID: "de:08111:6002",
        },
        unique_id="vvs_platform",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.data = {
        "stopEvents": [
            {
                "location": {
                    "id": "de:08111:6002:1:3",
                    "name": "Vaihingen",
                    "disassembledName": "Gleis 3",
                    "type": "platform",
                    "pointType": "TRACK",
                    "properties": {
                        "stopId": "5006002",
                        "platform": "3",
                        "platformName": "Gleis 3",
                        "plannedPlatformName": "Gleis 3",
                    },
                },
                "departureTimePlanned": "2026-07-18T18:25:00Z",
                "departureTimeEstimated": "2026-07-18T18:26:00Z",
                "isRealtimeControlled": True,
                "transportation": {
                    "number": "S1",
                    "destination": {"name": "Plochingen"},
                    "description": "Herrenberg - Stuttgart - Plochingen",
                    "product": {"class": 1, "name": "S-Bahn"},
                },
            }
        ]
    }
    coordinator.last_update_success = True
    coordinator.provider = PROVIDER_VVS
    coordinator.place_dm = "Stuttgart"
    coordinator.name_dm = "Vaihingen"
    coordinator.station_id = "de:08111:6002"
    coordinator.departures_limit = 10

    from openpublictransport import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VVS, hass)

    sensor = MultiProviderSensor(coordinator, entry, ["train"])

    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2026-07-18T18:08:00Z")
        sensor._process_departure_data(coordinator.data)

    departures = sensor._attributes.get("departures", [])
    assert len(departures) == 1
    # Technical value, not the "Gleis 3" label
    assert departures[0]["platform"] == "3"
    assert departures[0]["platform_name"] == "Gleis 3"
    # "3" vs "Gleis 3" is the same platform, not a change
    assert "platform_changed" not in departures[0]


# ── restore state across restart ──────────────────────────────────────────────
# Regression: after a restart the push-style sensor showed `unknown` until the
# next poll. It should now populate on add — from fresh coordinator data if
# present, else from the last persisted state.

from homeassistant.core import State
from pytest_homeassistant_custom_component.common import mock_restore_cache

from openpublictransport import get_provider


def _build_sensor(hass, coordinator, mock_config_entry, entity_id="sensor.opt_test"):
    coordinator.agency_name = "VRR"
    sensor = MultiProviderSensor(coordinator, mock_config_entry, ["bus", "train", "tram"])
    sensor.hass = hass
    sensor.entity_id = entity_id
    sensor.async_write_ha_state = MagicMock()
    return sensor


async def test_sensor_hydrates_on_add_from_coordinator(hass, mock_coordinator, mock_config_entry):
    """With fresh coordinator data present, state is set immediately on add
    (no waiting for the next poll)."""
    mock_coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)
    sensor = _build_sensor(hass, mock_coordinator, mock_config_entry)

    await sensor.async_added_to_hass()

    assert sensor.state is not None          # was None (unknown) before the fix
    assert isinstance(sensor.extra_state_attributes, dict)
    assert "total_departures" in sensor.extra_state_attributes


async def test_sensor_restores_last_state_when_no_data(hass, mock_coordinator, mock_config_entry):
    """With no coordinator data yet, the last persisted state/attributes are restored."""
    mock_coordinator.data = None
    entity_id = "sensor.opt_restore"
    mock_restore_cache(
        hass,
        (State(entity_id, "14:37", {"departures": [{"line": "U1"}], "total_departures": 3, "friendly_name": "X"}),),
    )
    sensor = _build_sensor(hass, mock_coordinator, mock_config_entry, entity_id)

    await sensor.async_added_to_hass()

    assert sensor.state == "14:37"
    assert sensor.extra_state_attributes["total_departures"] == 3
    assert "friendly_name" not in sensor.extra_state_attributes   # HA-managed key dropped

    # A subsequent coordinator update overwrites the restored value.
    mock_coordinator.data = {"stopEvents": []}
    sensor._handle_coordinator_update()
    assert sensor.state == "No departures"
