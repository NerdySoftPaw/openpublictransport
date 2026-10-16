"""Integration wiring for the German regional providers added in 2026.10.0."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.const import CONF_PROVIDER, DOMAIN, PROVIDERS
from custom_components.openpublictransport.trip import supports_trip_planning

NEW_PROVIDERS = ["vmv", "gvh", "nahsh", "insa", "vmt", "saarvv"]


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
def test_provider_is_known(provider):
    assert provider in PROVIDERS


async def test_providers_are_offered_in_the_config_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    field = next(f for f in result["data_schema"].schema if str(f) == CONF_PROVIDER)
    options = {o["value"] for o in result["data_schema"].schema[field].config["options"]}
    assert set(NEW_PROVIDERS) <= options


@pytest.mark.parametrize("provider, can_plan", [
    ("vmv", True), ("gvh", True), ("nahsh", True), ("insa", True), ("vmt", True), ("saarvv", True),
    ("tpg_ch", True), ("irishrail_ie", True), ("bart_us", True), ("dart_us", True), ("oebb", False),
])
def test_trip_planning_capability(provider, can_plan):
    assert supports_trip_planning(provider) is can_plan


@pytest.mark.parametrize("provider, title", [
    ("nahsh", "NAH.SH"), ("saarvv", "saarVV"), ("irishrail_ie", "Irish Rail"), ("avv_augsburg", "AVV"),
    ("vrr", "VRR"), ("unknown_provider", "UNKNOWN_PROVIDER"),
])
def test_entry_titles_use_the_display_name(provider, title):
    from custom_components.openpublictransport.config_flow import _provider_short_name

    assert _provider_short_name(provider) == title


def _hafas_leg(line, dep, arr, dep_planned=None, mode="transit", cancelled=False):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Europe/Berlin")
    at = lambda hhmm: datetime(2026, 10, 16, int(hhmm[:2]), int(hhmm[2:]), tzinfo=tz)  # noqa: E731
    return {
        "mode": mode, "origin": f"{line} from", "destination": f"{line} to", "line": line, "product": "Zug",
        "transport_type": "train" if mode == "transit" else "walk", "platform": "4", "cancelled": cancelled,
        "departure_planned": at(dep_planned or dep), "departure": at(dep),
        "arrival_planned": at(arr), "arrival": at(arr),
    }


async def test_parse_hafas_trips_into_unified_journeys(hass: HomeAssistant):
    from custom_components.openpublictransport.trip import _parse_hafas_trips

    await hass.config.async_set_time_zone("Europe/Berlin")
    trips = [
        {"duration_minutes": 53, "transfers": 1, "legs": [
            _hafas_leg("RE1", "2008", "2033", dep_planned="1952"),
            _hafas_leg("", "2033", "2037", mode="walk"),
            _hafas_leg("5", "2035", "2045"),
        ]},
        {"duration_minutes": 40, "transfers": 0, "legs": [_hafas_leg("RB", "2100", "2140", cancelled=True)]},
    ]

    journeys = _parse_hafas_trips(trips)

    assert len(journeys) == 1  # the cancelled connection is dropped
    journey = journeys[0]
    assert (journey["departure"], journey["arrival"]) == ("20:08", "20:45")
    assert journey["duration_minutes"] == 53
    assert journey["transfers"] == 1
    assert [leg["line"] for leg in journey["legs"]] == ["RE1", "5"]  # walks are not legs
    assert journey["legs"][0]["delay"] == 16
    assert journey["legs"][0]["departure_planned"] == "19:52"
    # 20:33 arrival, 20:35 departure: a 2-minute transfer is high risk
    assert (journey["connection_feasible"], journey["transfer_risk"], journey["min_transfer_time"]) == (True, "high", 2)
    assert journey["departure_timestamp"].startswith("2026-10-16T20:08")
    assert "_departure_s" not in journey["legs"][0]


async def test_plan_trip_dispatches_to_hafas_trip_search(hass: HomeAssistant):
    from unittest.mock import AsyncMock, MagicMock, patch

    from custom_components.openpublictransport.trip import async_plan_trip

    provider = MagicMock()
    provider.search_trips = AsyncMock(return_value=[{"duration_minutes": 10, "transfers": 0,
                                                     "legs": [_hafas_leg("RE83", "1943", "2052")]}])
    with patch("custom_components.openpublictransport.trip.async_get_clientsession"), \
            patch("openpublictransport.get_provider", return_value=provider):
        journeys = await async_plan_trip(hass, "nahsh", "Kiel", "", "Lübeck", "", origin_id="A=1@L=1@", dest_id="A=1@L=2@")
        missing_ids = await async_plan_trip(hass, "nahsh", "Kiel", "", "Lübeck", "")

    provider.search_trips.assert_awaited_once()
    assert provider.search_trips.call_args.args == ("A=1@L=1@", "A=1@L=2@")
    assert journeys[0]["legs"][0]["line"] == "RE83"
    assert missing_ids is None
