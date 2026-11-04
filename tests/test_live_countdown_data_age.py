"""departure_timestamp and last_fetched for the card (card#17, card#18)."""

from datetime import datetime, timezone
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import DOMAIN, PROVIDER_VRR
from custom_components.openpublictransport.multi_stop import (
    CONF_IS_MULTI_STOP,
    CONF_MULTI_STOP_NAME,
    CONF_SOURCE_ENTITIES,
    MultiStopSensor,
    oldest_source_fetch,
)
from custom_components.openpublictransport.sensor import MultiProviderSensor


def _sensor(hass, coordinator, entry):
    from openpublictransport import get_provider

    coordinator.provider_instance = get_provider(PROVIDER_VRR, hass)
    return MultiProviderSensor(coordinator, entry, ["bus", "train", "tram"])


async def test_departures_carry_an_aware_timestamp(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Every departure has an ISO timestamp with an offset, matching its time."""
    sensor = _sensor(hass, mock_coordinator, mock_config_entry)
    with patch("custom_components.openpublictransport.sensor.dt_util.now") as mock_now:
        mock_now.return_value = dt_util.parse_datetime("2025-01-15T09:55:00Z")
        sensor._process_departure_data(mock_coordinator.data)

    departures = sensor._attributes["departures"]
    assert departures
    for dep in departures:
        stamp = datetime.fromisoformat(dep["departure_timestamp"])
        assert stamp.tzinfo is not None
        assert stamp.strftime("%H:%M") == dep["departure_time"]


async def test_last_fetched_is_the_coordinator_fetch_time(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """last_fetched is the last successful request, not the attribute rebuild."""
    fetched = datetime(2025, 1, 15, 9, 50, tzinfo=timezone.utc)
    mock_coordinator.last_update_success_time = fetched
    sensor = _sensor(hass, mock_coordinator, mock_config_entry)
    sensor._process_departure_data(mock_coordinator.data)
    assert sensor._attributes["last_fetched"] == fetched.isoformat()

    # No successful fetch yet: say so rather than inventing one.
    mock_coordinator.last_update_success_time = None
    sensor._process_departure_data({"stopEvents": []})
    assert sensor._attributes["last_fetched"] is None


def _set(hass, entity_id, fetched):
    attrs = {"departures": [], "station_name": entity_id}
    if fetched is not None:
        attrs["last_fetched"] = fetched
    hass.states.async_set(entity_id, "10:00", attrs)


async def test_multi_stop_reports_the_oldest_source(hass: HomeAssistant):
    """A combined board is as fresh as its stalest stop."""
    _set(hass, "sensor.a", "2025-01-15T09:58:00+00:00")
    _set(hass, "sensor.b", "2025-01-15T10:52:00+01:00")  # 09:52 UTC, the oldest
    assert oldest_source_fetch(hass, ["sensor.a", "sensor.b"]) == "2025-01-15T10:52:00+01:00"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_IS_MULTI_STOP: True, CONF_SOURCE_ENTITIES: ["sensor.a", "sensor.b"], CONF_MULTI_STOP_NAME: "X"},
    )
    sensor = MultiStopSensor(hass, entry, ["sensor.a", "sensor.b"], "X")
    sensor._update_from_sources()
    assert sensor.extra_state_attributes["last_fetched"] == "2025-01-15T10:52:00+01:00"


async def test_multi_stop_without_a_source_time_has_no_age(hass: HomeAssistant):
    """One source that cannot say when it fetched leaves the age unknown."""
    _set(hass, "sensor.a", "2025-01-15T09:58:00+00:00")
    _set(hass, "sensor.b", None)
    assert oldest_source_fetch(hass, ["sensor.a", "sensor.b"]) is None
    assert oldest_source_fetch(hass, ["sensor.a", "sensor.missing"]) is None
