"""Via stop with an optional dwell time in trip planning (issue #110)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.trip import (
    TripOptionNotSupportedError,
    _async_plan_trip_otp2_graphql,
    _join_halves,
    _pair_halves,
    async_plan_trip,
    via_support,
)
from custom_components.openpublictransport.filters import trip_via_discriminator


def _efa_leg(origin, dest, dep, arr, line="RE1"):
    return {
        "origin": {"name": origin, "departureTimePlanned": dep},
        "destination": {"name": dest, "arrivalTimePlanned": arr},
        "transportation": {"number": line, "product": {"name": "RE", "class": 1}},
        "duration": 600,
    }


def _efa_answer(*journeys):
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"journeys": [{"legs": legs, "interchanges": 0} for legs in journeys]})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def test_via_support():
    assert via_support("vrr") == (True, True)
    assert via_support("nahsh") == (True, True)
    assert via_support("otp_custom") == (True, True)
    assert via_support("vbn_otp") == (False, False)
    assert via_support("sbb") == (False, False)


async def test_unsupported_via_is_refused_not_ignored(hass: HomeAssistant):
    with pytest.raises(TripOptionNotSupportedError) as err:
        await async_plan_trip(hass, "vbn_otp", "A", "", "B", "", origin_id="1", dest_id="2", via_id="3")
    assert err.value.option == "via"


async def test_dwell_without_via_is_an_error(hass: HomeAssistant):
    with pytest.raises(ValueError):
        await async_plan_trip(hass, "vrr", "A", "", "B", "", via_dwell_minutes=30)


async def test_efa_via_goes_into_the_request(hass: HomeAssistant):
    """Without a stay, EFA routes through the via itself: one request."""
    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as session_fn:
        session = MagicMock()
        session.get = MagicMock(
            return_value=_efa_answer([_efa_leg("A", "C", "2026-11-05T08:00:00Z", "2026-11-05T08:40:00Z")])
        )
        session_fn.return_value = session
        journeys = await async_plan_trip(
            hass, "vrr", "", "", "", "", origin_id="de:1", dest_id="de:2", via_id="de:05124:11376"
        )
    assert session.get.call_count == 1
    url = session.get.call_args.args[0]
    assert "type_via=stop&name_via=de%3A05124%3A11376" in url
    assert "dwellTime" not in url
    assert journeys and journeys[0]["legs"][0]["line"] == "RE1"


async def test_efa_via_by_name(hass: HomeAssistant):
    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as session_fn:
        session = MagicMock()
        session.get = MagicMock(return_value=_efa_answer())
        session_fn.return_value = session
        await async_plan_trip(hass, "vrr", "A", "X", "B", "X", via_name="Duisburg Hbf", via_place="Duisburg")
    url = session.get.call_args.args[0]
    assert "type_via=any&name_via=Duisburg%20Hbf&place_via=Duisburg" in url


async def test_efa_dwell_is_built_from_two_requests(hass: HomeAssistant):
    """A stay at the via: origin → via, then via → destination from arrival + stay."""
    first = _efa_answer(
        [_efa_leg("A", "V", "2026-11-05T08:00:00Z", "2026-11-05T08:20:00Z", "S1")],
        [_efa_leg("A", "V", "2026-11-05T08:10:00Z", "2026-11-05T08:30:00Z", "S1")],
    )
    second = _efa_answer(
        [_efa_leg("V", "B", "2026-11-05T09:05:00Z", "2026-11-05T09:30:00Z", "RE2")],
        [_efa_leg("V", "B", "2026-11-05T09:20:00Z", "2026-11-05T09:45:00Z", "RE2")],
    )
    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as session_fn:
        session = MagicMock()
        session.get = MagicMock(side_effect=[first, second])
        session_fn.return_value = session
        journeys = await async_plan_trip(
            hass, "vrr", "", "", "", "", origin_id="de:1", dest_id="de:2", via_id="de:9", via_name="V",
            via_dwell_minutes=30,
        )

    urls = [c.args[0] for c in session.get.call_args_list]
    assert "name_destination=de%3A9" in urls[0] and "name_via" not in urls[0]
    assert "name_origin=de%3A9" in urls[1]
    # Second half searched from the earliest arrival (08:20Z) + 30 min, in network time (09:50 CET)
    assert "itdTime=0950" in urls[1]

    # Both first halves can only make the 09:05 → the later one (08:10) is kept,
    # and nothing pairs with 09:20 because no first half is left for it.
    assert len(journeys) == 1
    journey = journeys[0]
    assert [leg["line"] for leg in journey["legs"]] == ["S1", "RE2"]
    assert journey["via"] == "V"
    assert journey["via_dwell_minutes"] == 35
    assert journey["legs"][0]["via_stay"] is True
    assert journey["transfers"] == 1
    assert journey["duration_minutes"] == 80
    assert len(journey["id"]) == 12


def _half(dep, arr):
    return {"departure_timestamp": dep, "arrival_timestamp": arr, "legs": [{"line": "X"}], "transfers": 0}


def test_pair_halves_arrive_by_takes_the_latest_first_half():
    from datetime import timedelta

    first = [_half("2026-11-05T08:00:00+00:00", "2026-11-05T08:20:00+00:00"),
             _half("2026-11-05T08:30:00+00:00", "2026-11-05T08:50:00+00:00")]
    second = [_half("2026-11-05T09:30:00+00:00", "2026-11-05T10:00:00+00:00")]
    pairs = _pair_halves(first, second, timedelta(minutes=30), forward=False)
    assert len(pairs) == 1
    assert pairs[0][0]["arrival_timestamp"].startswith("2026-11-05T08:50")


def test_join_halves_keeps_the_worst_risk():
    a = {**_half("2026-11-05T08:00:00+00:00", "2026-11-05T08:20:00+00:00"), "transfer_risk": "high",
         "min_transfer_time": 2}
    b = {**_half("2026-11-05T09:00:00+00:00", "2026-11-05T09:30:00+00:00"), "transfer_risk": "low"}
    joined = _join_halves(a, b, "V")
    assert joined["transfer_risk"] == "high"
    assert joined["min_transfer_time"] == 2
    assert joined["via_dwell_minutes"] == 40


async def test_hafas_passes_via_and_dwell(hass: HomeAssistant):
    async def search_trips(origin, dest, departure_time=None, arrival_time=None, via_id=None, via_dwell_minutes=None):
        search_trips.call = (origin, dest, via_id, via_dwell_minutes)
        return []

    provider = MagicMock()
    provider.search_trips = search_trips
    with patch("custom_components.openpublictransport.trip.async_get_clientsession"), patch(
        "openpublictransport.get_provider", return_value=provider
    ):
        await async_plan_trip(
            hass, "nahsh", "", "", "", "", origin_id="A=1@L=1@", dest_id="A=1@L=2@", via_id="A=1@L=3@",
            via_dwell_minutes=30,
        )
    assert search_trips.call == ("A=1@L=1@", "A=1@L=2@", "A=1@L=3@", 30)


async def test_hafas_with_an_old_library_says_so(hass: HomeAssistant):
    async def search_trips(origin, dest, departure_time=None, arrival_time=None):
        return []

    provider = MagicMock()
    provider.search_trips = search_trips
    with patch("custom_components.openpublictransport.trip.async_get_clientsession"), patch(
        "openpublictransport.get_provider", return_value=provider
    ):
        with pytest.raises(TripOptionNotSupportedError, match="0.3.4"):
            await async_plan_trip(hass, "nahsh", "", "", "", "", origin_id="A", dest_id="B", via_id="C")


async def test_otp2_via_clause_with_minimum_wait():
    provider = MagicMock()
    provider._graphql = AsyncMock(
        side_effect=[{"data": {"stop": None}}] * 3 + [{"data": {"planConnection": {"edges": []}}}]
    )
    await _async_plan_trip_otp2_graphql("s:1", "s:2", None, provider, via_id="s:3", via_dwell_minutes=20)
    query = provider._graphql.call_args_list[-1].args[0]
    assert 'via: [{ visit: { stopLocationIds: ["s:3"], minimumWaitTime: "PT20M" } }]' in query


async def test_otp2_without_via_support_is_refused():
    provider = MagicMock()
    provider._graphql = AsyncMock(
        side_effect=[{"data": {"stop": None}}] * 3 + [{"errors": [{"message": "Unknown argument 'via'"}]}]
    )
    with pytest.raises(TripOptionNotSupportedError):
        await _async_plan_trip_otp2_graphql("s:1", "s:2", None, provider, via_id="s:3")


def test_via_discriminator():
    assert trip_via_discriminator({}) == ""
    a = trip_via_discriminator({"trip_via_id": "de:9", "trip_via_dwell_minutes": 30})
    b = trip_via_discriminator({"trip_via_id": "de:9", "trip_via_dwell_minutes": 0})
    assert a and b and a != b


# ── Config flow ───────────────────────────────────────────────────────────────

_SEARCH = "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops"


async def _to_via_step(hass):
    from custom_components.openpublictransport.const import CONF_PROVIDER, DOMAIN, PROVIDER_VRR

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR}
    )
    with patch(_SEARCH, return_value=[{"id": "de:1", "name": "Hbf", "place": "Düsseldorf"}]):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"stop_search": "a"})
    with patch(_SEARCH, return_value=[{"id": "de:2", "name": "Hbf", "place": "Essen"}]):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"stop_search": "b"})
    assert result["step_id"] == "trip_via"
    return result


async def test_flow_via_with_dwell_creates_its_own_entry(hass: HomeAssistant):
    from custom_components.openpublictransport.const import CONF_ENTRY_SUFFIX, CONF_SCAN_INTERVAL
    from custom_components.openpublictransport.trip_sensor import TripDataUpdateCoordinator

    result = await _to_via_step(hass)
    with patch(_SEARCH, return_value=[{"id": "de:9", "name": "Wuppertal Hbf", "place": "Wuppertal"}]):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"via_search": "Wuppertal", "via_dwell_minutes": 30}
        )
    assert result["step_id"] == "trip_settings"
    with (
        patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_SCAN_INTERVAL: 120})

    assert result["type"] == "create_entry"
    data = result["data"]
    assert (data["trip_via"], data["trip_via_id"], data["trip_via_dwell_minutes"]) == ("Wuppertal Hbf", "de:9", 30)
    assert data[CONF_ENTRY_SUFFIX] == trip_via_discriminator(data)
    assert result["title"].endswith("via Wuppertal Hbf (30 min)")
    assert result["result"].unique_id == f"vrr_trip_de:1_de:2_{data[CONF_ENTRY_SUFFIX]}"


async def test_flow_dwell_without_via_is_rejected(hass: HomeAssistant):
    result = await _to_via_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"via_search": "", "via_dwell_minutes": 15}
    )
    assert result["step_id"] == "trip_via"
    assert result["errors"] == {"via_dwell_minutes": "via_dwell_needs_via"}


async def test_flow_via_choice_from_several_stops(hass: HomeAssistant):
    result = await _to_via_step(hass)
    stops = [{"id": "de:9", "name": "Wuppertal Hbf", "place": "W"}, {"id": "de:8", "name": "Wuppertal Ost", "place": "W"}]
    with patch(_SEARCH, return_value=stops):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"via_search": "Wupp"})
    assert result["step_id"] == "trip_select"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"stop": "de:8"})
    assert result["step_id"] == "trip_settings"
