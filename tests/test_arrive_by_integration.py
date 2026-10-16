"""Arrive-by planning across providers and the trip options form (2026.10.3, #96)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_ARRIVAL_TIME,
    CONF_ARRIVAL_TIME_ENTITY,
    CONF_LINE_FILTER,
    CONF_PROVIDER,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
)
from custom_components.openpublictransport.trip import async_plan_trip
from custom_components.openpublictransport.trip_sensor import _latest_arrivals_first


def _journey(arrival: datetime) -> dict:
    return {"departure": "x", "arrival": "y", "arrival_timestamp": arrival.isoformat(), "legs": []}


def test_latest_arrival_that_makes_it_comes_first():
    target = dt_util.now().replace(hour=8, minute=0, second=0, microsecond=0)
    early = _journey(target - timedelta(minutes=10))
    latest = _journey(target - timedelta(minutes=2))
    too_late = _journey(target + timedelta(minutes=5))
    unknown = {"departure": "x", "arrival": "y", "legs": []}

    assert _latest_arrivals_first([early, too_late, unknown, latest], target) == [latest, early, unknown]


async def test_hafas_trip_search_gets_the_arrival_time(hass: HomeAssistant):
    provider = MagicMock()
    provider.search_trips = AsyncMock(return_value=[])
    target = dt_util.now() + timedelta(hours=2)
    with patch("custom_components.openpublictransport.trip.async_get_clientsession"), patch(
        "openpublictransport.get_provider", return_value=provider
    ):
        await async_plan_trip(
            hass, "nahsh", "Kiel", "", "Lübeck", "", origin_id="A=1@L=1@", dest_id="A=1@L=2@", arrival_time=target
        )

    assert provider.search_trips.call_args.kwargs["arrival_time"] == target


async def test_efa_arrive_by_uses_the_network_time_zone(hass: HomeAssistant):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"journeys": []})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as session_fn:
        session = MagicMock()
        session.get = MagicMock(return_value=response)
        session_fn.return_value = session
        # 05:45 UTC is 07:45 in Berlin (CEST)
        target = datetime(2026, 10, 16, 5, 45, tzinfo=dt_util.UTC)
        await async_plan_trip(
            hass, "vmv", "A", "", "B", "", origin_id="de:13003:1489", dest_id="de:13003:1500", arrival_time=target
        )

    url = session.get.call_args.args[0]
    assert "itdTripDateTimeDepArr=arr" in url
    assert "itdTime=0745" in url


def _trip_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "is_trip": True, "trip_provider": "vrr", CONF_PROVIDER: "vrr",
            "trip_origin": "A", "trip_origin_city": "C", "trip_destination": "B", "trip_destination_city": "C",
        },
        options={CONF_ARRIVAL_TIME: "07:45", CONF_ARRIVAL_TIME_ENTITY: "input_datetime.school", CONF_LINE_FILTER: "U79"},
    )


async def test_trip_options_offer_filters_and_clearable_arrival(hass: HomeAssistant):
    entry = _trip_entry()
    entry.add_to_hass(hass)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    fields = {str(f): f for f in form["data_schema"].schema}
    assert {CONF_TRANSPORTATION_TYPES, CONF_LINE_FILTER, CONF_ARRIVAL_TIME, CONF_ARRIVAL_TIME_ENTITY} <= set(fields)
    assert fields[CONF_ARRIVAL_TIME].description["suggested_value"] == "07:45"

    # The user empties every text field; the frontend leaves them out.
    await hass.config_entries.options.async_configure(form["flow_id"], user_input={})

    assert entry.options[CONF_ARRIVAL_TIME] == ""
    assert entry.options[CONF_ARRIVAL_TIME_ENTITY] == ""
    assert entry.options[CONF_LINE_FILTER] == ""
