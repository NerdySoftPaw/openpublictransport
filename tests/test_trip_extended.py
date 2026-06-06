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


# ── _async_plan_trip_otp2_graphql ─────────────────────────────────────────────

async def test_otp2_graphql_no_coordinates(hass: HomeAssistant):
    """Test OTP2 GraphQL returns None when stop coordinates unavailable."""
    provider = MagicMock()
    provider._graphql = AsyncMock(return_value=None)

    result = await _async_plan_trip_otp2_graphql(
        "stop:1", "stop:2", None, provider
    )
    assert result is None


async def test_otp2_graphql_coordinates_returned(hass: HomeAssistant):
    """Test OTP2 GraphQL returns itineraries when coords available."""
    from_data = {"data": {"stop": {"lat": 51.2, "lon": 6.7, "name": "A"}}}
    to_data = {"data": {"stop": {"lat": 50.9, "lon": 6.9, "name": "B"}}}
    plan_data = {"data": {"plan": {"itineraries": [_make_otp_itinerary()]}}}

    provider = MagicMock()
    provider._graphql = AsyncMock(side_effect=[from_data, to_data, plan_data])

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is not None
    assert len(result) == 1


async def test_otp2_graphql_plan_query_none(hass: HomeAssistant):
    """Test OTP2 GraphQL returns None when plan query fails."""
    from_data = {"data": {"stop": {"lat": 51.2, "lon": 6.7, "name": "A"}}}
    to_data = {"data": {"stop": {"lat": 50.9, "lon": 6.9, "name": "B"}}}

    provider = MagicMock()
    provider._graphql = AsyncMock(side_effect=[from_data, to_data, None])

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is None


async def test_otp2_graphql_no_itineraries(hass: HomeAssistant):
    """Test OTP2 GraphQL returns None when no itineraries."""
    from_data = {"data": {"stop": {"lat": 51.2, "lon": 6.7, "name": "A"}}}
    to_data = {"data": {"stop": {"lat": 50.9, "lon": 6.9, "name": "B"}}}
    plan_data = {"data": {"plan": {"itineraries": []}}}

    provider = MagicMock()
    provider._graphql = AsyncMock(side_effect=[from_data, to_data, plan_data])

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is None


async def test_otp2_graphql_with_graphql_errors(hass: HomeAssistant):
    """Test OTP2 GraphQL logs errors but returns itineraries if available."""
    from_data = {"data": {"stop": {"lat": 51.2, "lon": 6.7, "name": "A"}}}
    to_data = {"data": {"stop": {"lat": 50.9, "lon": 6.9, "name": "B"}}}
    plan_data = {
        "errors": [{"message": "Some warning"}],
        "data": {"plan": {"itineraries": [_make_otp_itinerary()]}},
    }

    provider = MagicMock()
    provider._graphql = AsyncMock(side_effect=[from_data, to_data, plan_data])

    result = await _async_plan_trip_otp2_graphql("stop:1", "stop:2", None, provider)
    assert result is not None


async def test_otp2_graphql_pipe_separated_stop_id(hass: HomeAssistant):
    """Test OTP2 GraphQL handles pipe-separated compound stop IDs."""
    from_data = {"data": {"stop": {"lat": 51.2, "lon": 6.7, "name": "A"}}}
    to_data = {"data": {"stop": {"lat": 50.9, "lon": 6.9, "name": "B"}}}
    plan_data = {"data": {"plan": {"itineraries": [_make_otp_itinerary()]}}}

    provider = MagicMock()
    provider._graphql = AsyncMock(side_effect=[from_data, to_data, plan_data])

    # Pipe-separated stop IDs — should use only the first part
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
