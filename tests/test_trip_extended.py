"""Extended trip.py tests — OTP2 GraphQL and OTP REST paths."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.trip import (
    _async_plan_trip_otp,
    _async_plan_trip_otp2_graphql,
    async_plan_trip,
)


def _make_otp_itinerary(dep_ms=1705312200000, dur_s=3600, transfers=0):
    return {
        "duration": dur_s,
        "numberOfTransfers": transfers,
        "legs": [
            {
                "transitLeg": True,
                "startTime": dep_ms,
                "endTime": dep_ms + dur_s * 1000,
                "departureDelay": 0,
                "arrivalDelay": 0,
                "mode": "RAIL",
                "from": {"name": "A"},
                "to": {"name": "B"},
                "trip": {"route": {"shortName": "ICE 1"}},
                "duration": dur_s,
            }
        ],
    }


# ── _async_plan_trip_otp2_graphql (planConnection) ────────────────────────────

def _make_pc_node(transfers=0):
    """A planConnection node with one transit leg."""
    return {
        "duration": 3600,
        "numberOfTransfers": transfers,
        "legs": [
            {
                "transitLeg": True,
                "mode": "RAIL",
                "duration": 3600,
                "from": {"name": "A"},
                "to": {"name": "B"},
                "start": {
                    "scheduledTime": "2026-01-15T10:00:00+01:00",
                    "estimated": {"time": "2026-01-15T10:00:00+01:00", "delay": 0},
                },
                "end": {
                    "scheduledTime": "2026-01-15T11:00:00+01:00",
                    "estimated": {"time": "2026-01-15T11:00:00+01:00", "delay": 0},
                },
                "trip": {"route": {"shortName": "ICE 1"}},
                "route": {"shortName": "ICE 1"},
            }
        ],
    }


def _make_pc_two_leg():
    """A planConnection node with two transit legs and a 4-minute transfer."""
    return {
        "duration": 5400,
        "numberOfTransfers": 1,
        "legs": [
            {
                "transitLeg": True, "mode": "RAIL", "duration": 1800,
                "from": {"name": "A"}, "to": {"name": "B"},
                "start": {"scheduledTime": "2026-01-15T10:00:00+01:00"},
                "end": {"scheduledTime": "2026-01-15T10:30:00+01:00"},
                "route": {"shortName": "RE1"},
            },
            {
                "transitLeg": True, "mode": "BUS", "duration": 1800,
                "from": {"name": "B"}, "to": {"name": "C"},
                "start": {"scheduledTime": "2026-01-15T10:34:00+01:00"},
                "end": {"scheduledTime": "2026-01-15T11:04:00+01:00"},
                "route": {"shortName": "42"},
            },
        ],
    }


def _pc_response(nodes):
    return {"data": {"planConnection": {"edges": [{"node": n} for n in nodes]}}}


async def test_otp2_graphql_no_response(hass: HomeAssistant):
    """planConnection returns None when the request fails."""
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=None)

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is None


async def test_otp2_graphql_itineraries_returned(hass: HomeAssistant):
    """planConnection returns parsed journeys when edges are present."""
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=_pc_response([_make_pc_node()]))

    # departure_time set → exercises the dateTime clause branch too
    result = await _async_plan_trip_otp2_graphql(
        "stop:1", "stop:2", datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc), provider
    )
    assert result is not None
    assert len(result) == 1
    assert result[0]["legs"][0]["line"] == "ICE 1"


async def test_otp2_graphql_no_edges(hass: HomeAssistant):
    """planConnection returns None when there are no edges."""
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=_pc_response([]))

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is None


async def test_otp2_graphql_with_graphql_errors(hass: HomeAssistant):
    """planConnection logs errors but still returns edges if present."""
    resp = _pc_response([_make_pc_node()])
    resp["errors"] = [{"message": "Some warning"}]
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=resp)

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is not None


async def test_otp2_graphql_multileg_transfer(hass: HomeAssistant):
    """Two-leg journey computes transfers and transfer risk."""
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=_pc_response([_make_pc_two_leg()]))

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is not None
    assert result[0]["transfers"] == 1
    assert len(result[0]["legs"]) == 2
    assert result[0]["transfer_risk"] == "medium"  # 4-minute gap


async def test_otp2_graphql_pipe_separated_stop_id(hass: HomeAssistant):
    """Compound pipe-separated stop IDs use only the first platform."""
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=_pc_response([_make_pc_node()]))

    result = await _async_plan_trip_otp2_graphql(
        "stop:1|platform:A", "stop:2|platform:B", None, provider
    )
    assert result is not None


# ── _async_plan_trip_otp ──────────────────────────────────────────────────────

async def test_otp_rest_no_stop_data(hass: HomeAssistant):
    """Test OTP REST returns None when stop data unavailable."""
    provider = MagicMock()
    provider.otp_base_url = "http://otp.local"
    provider._get = AsyncMock(return_value=None)

    result = await _async_plan_trip_otp(hass, "stop:1", "stop:2", None, provider)
    assert result is None


async def test_otp_rest_no_itineraries(hass: HomeAssistant):
    """Test OTP REST returns None when no itineraries."""
    origin_stop = {"lat": 51.2, "lon": 6.7}
    dest_stop = {"lat": 50.9, "lon": 6.9}

    provider = MagicMock()
    provider.otp_base_url = "http://otp.local"
    provider._get = AsyncMock(side_effect=[
        origin_stop, dest_stop,
        {"plan": {"itineraries": []}},
    ])

    result = await _async_plan_trip_otp(hass, "stop:1", "stop:2", None, provider)
    assert result is None


async def test_otp_rest_with_itineraries(hass: HomeAssistant):
    """Test OTP REST returns parsed itineraries."""
    origin_stop = {"lat": 51.2, "lon": 6.7}
    dest_stop = {"lat": 50.9, "lon": 6.9}

    provider = MagicMock()
    provider.otp_base_url = "http://otp.local"
    provider._get = AsyncMock(side_effect=[
        origin_stop, dest_stop,
        {"plan": {"itineraries": [_make_otp_itinerary()]}},
    ])

    result = await _async_plan_trip_otp(hass, "stop:1", "stop:2", None, provider)
    assert result is not None
    assert len(result) == 1


async def test_otp_rest_plan_data_none(hass: HomeAssistant):
    """Test OTP REST returns None when plan request fails."""
    origin_stop = {"lat": 51.2, "lon": 6.7}
    dest_stop = {"lat": 50.9, "lon": 6.9}

    provider = MagicMock()
    provider.otp_base_url = "http://otp.local"
    provider._get = AsyncMock(side_effect=[origin_stop, dest_stop, None])

    result = await _async_plan_trip_otp(hass, "stop:1", "stop:2", None, provider)
    assert result is None


# ── async_plan_trip with OTP2/VBN providers ───────────────────────────────────

async def test_plan_trip_otp2_with_ids(hass: HomeAssistant):
    """Test async_plan_trip dispatches to OTP2 path when stop IDs provided."""
    from_data = {"data": {"stop": {"lat": 51.2, "lon": 6.7, "name": "A"}}}
    to_data = {"data": {"stop": {"lat": 50.9, "lon": 6.9, "name": "B"}}}
    plan_data = {"data": {"plan": {"itineraries": [_make_otp_itinerary()]}}}

    mock_provider = MagicMock()
    mock_provider._graphql = AsyncMock(side_effect=[from_data, to_data, plan_data])

    with patch("openpublictransport.get_provider", return_value=mock_provider):
        with patch("custom_components.openpublictransport.trip.async_get_clientsession"):
            result = await async_plan_trip(
                hass, "openpublictransport", "A", "City", "B", "City",
                origin_id="stop:1", dest_id="stop:2",
            )

    assert result is not None


async def test_plan_trip_vbn_with_ids(hass: HomeAssistant):
    """Test async_plan_trip dispatches to VBN OTP path when stop IDs provided."""
    origin_stop = {"lat": 53.0, "lon": 8.8}
    dest_stop = {"lat": 52.5, "lon": 9.0}

    mock_provider = MagicMock()
    mock_provider.otp_base_url = "http://vbn.local"
    mock_provider._get = AsyncMock(side_effect=[
        origin_stop, dest_stop,
        {"plan": {"itineraries": [_make_otp_itinerary()]}},
    ])

    with patch("openpublictransport.get_provider", return_value=mock_provider):
        with patch("custom_components.openpublictransport.trip.async_get_clientsession"):
            result = await async_plan_trip(
                hass, "vbn_otp", "A", "Bremen", "B", "Hannover",
                origin_id="stop:1", dest_id="stop:2",
            )

    assert result is not None
