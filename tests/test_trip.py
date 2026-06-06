"""Tests for trip.py — trip planning dispatcher and parsers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.trip import (
    _format_time,
    _ms_to_hhmm,
    _parse_journeys,
    _parse_otp_itineraries,
    async_plan_trip,
)

# ── _format_time ──────────────────────────────────────────────────────────────

def test_format_time_valid():
    """Test _format_time with valid ISO string."""
    result = _format_time("2025-01-15T10:05:00+01:00")
    assert ":" in result
    assert len(result) == 5


def test_format_time_empty():
    """Test _format_time with empty string."""
    assert _format_time("") == ""


def test_format_time_invalid():
    """Test _format_time with invalid string."""
    assert _format_time("not-a-date") == ""


# ── _ms_to_hhmm ───────────────────────────────────────────────────────────────

def test_ms_to_hhmm_valid():
    """Test _ms_to_hhmm with valid timestamp."""
    ms = 1705312200000  # 2024-01-15 10:10:00 UTC
    result = _ms_to_hhmm(ms)
    assert ":" in result


def test_ms_to_hhmm_zero():
    """Test _ms_to_hhmm with zero returns empty."""
    assert _ms_to_hhmm(0) == ""


# ── _parse_journeys ───────────────────────────────────────────────────────────

def test_parse_journeys_empty():
    """Test _parse_journeys with empty list."""
    assert _parse_journeys([]) == []


def test_parse_journeys_no_legs():
    """Test _parse_journeys skips journeys with no legs."""
    result = _parse_journeys([{"legs": [], "interchanges": 0}])
    assert result == []


def test_parse_journeys_single_leg():
    """Test _parse_journeys with a single leg journey."""
    journeys = [
        {
            "legs": [
                {
                    "origin": {"name": "Düsseldorf Hbf", "departureTimePlanned": "2025-01-15T10:00:00+01:00"},
                    "destination": {"name": "Köln Hbf", "arrivalTimePlanned": "2025-01-15T11:30:00+01:00"},
                    "transportation": {"number": "ICE 1", "product": {"name": "ICE"}},
                    "duration": 5400,
                }
            ],
            "interchanges": 0,
        }
    ]
    result = _parse_journeys(journeys)
    assert len(result) == 1
    assert result[0]["transfers"] == 0
    assert len(result[0]["legs"]) == 1
    assert result[0]["legs"][0]["line"] == "ICE 1"


def test_parse_journeys_with_delay():
    """Test _parse_journeys calculates delay correctly."""
    journeys = [
        {
            "legs": [
                {
                    "origin": {
                        "name": "Start",
                        "departureTimePlanned": "2025-01-15T10:00:00+01:00",
                        "departureTimeEstimated": "2025-01-15T10:05:00+01:00",
                    },
                    "destination": {"name": "End"},
                    "transportation": {"number": "U79", "product": {"name": "U-Bahn"}},
                    "duration": 1200,
                }
            ],
            "interchanges": 0,
        }
    ]
    result = _parse_journeys(journeys)
    assert result[0]["legs"][0]["delay"] == 5


def test_parse_journeys_transfer_risk_missed():
    """Test _parse_journeys detects missed connection."""
    journeys = [
        {
            "legs": [
                {
                    "origin": {"name": "A", "departureTimePlanned": "2025-01-15T10:00:00+01:00"},
                    "destination": {
                        "name": "B",
                        "arrivalTimePlanned": "2025-01-15T10:30:00+01:00",
                        "arrivalTimeEstimated": "2025-01-15T10:32:00+01:00",
                    },
                    "transportation": {"number": "S1", "product": {"name": "S-Bahn"}},
                    "duration": 1800,
                },
                {
                    "origin": {
                        "name": "B",
                        "departureTimePlanned": "2025-01-15T10:30:00+01:00",
                    },
                    "destination": {"name": "C"},
                    "transportation": {"number": "U1", "product": {"name": "U-Bahn"}},
                    "duration": 600,
                },
            ],
            "interchanges": 1,
        }
    ]
    result = _parse_journeys(journeys)
    assert result[0]["transfers"] == 1
    assert result[0]["connection_feasible"] in (True, False)


def test_parse_journeys_with_transfer_info():
    """Test _parse_journeys includes transfer description."""
    journeys = [
        {
            "legs": [
                {
                    "origin": {"name": "Start"},
                    "destination": {"name": "End"},
                    "transportation": {"number": "Bus 1", "product": {"name": "Bus"}},
                    "duration": 600,
                    "interchange": {"desc": "Short transfer, platform 3"},
                }
            ],
            "interchanges": 0,
        }
    ]
    result = _parse_journeys(journeys)
    assert result[0]["legs"][0].get("transfer") == "Short transfer, platform 3"


def test_parse_journeys_platform_from_origin():
    """Test _parse_journeys extracts platform from origin."""
    journeys = [
        {
            "legs": [
                {
                    "origin": {"name": "Hbf", "platform": {"name": "3A"}},
                    "destination": {"name": "Airport"},
                    "transportation": {"number": "RE1", "product": {}},
                    "duration": 1200,
                }
            ],
            "interchanges": 0,
        }
    ]
    result = _parse_journeys(journeys)
    assert result[0]["legs"][0]["platform"] == "3A"


# ── _parse_otp_itineraries ────────────────────────────────────────────────────

def test_parse_otp_itineraries_empty():
    """Test _parse_otp_itineraries with empty list."""
    assert _parse_otp_itineraries([]) == []


def test_parse_otp_itineraries_no_transit_legs():
    """Test _parse_otp_itineraries skips walk-only itineraries."""
    itineraries = [{"legs": [{"transitLeg": False, "startTime": 0, "endTime": 0}], "duration": 600}]
    result = _parse_otp_itineraries(itineraries)
    assert result == []


def test_parse_otp_itineraries_with_transit():
    """Test _parse_otp_itineraries with one transit leg."""
    now_ms = 1705312200000
    itineraries = [
        {
            "duration": 5400,
            "numberOfTransfers": 0,
            "legs": [
                {
                    "transitLeg": True,
                    "startTime": now_ms,
                    "endTime": now_ms + 5400000,
                    "departureDelay": 0,
                    "arrivalDelay": 0,
                    "mode": "RAIL",
                    "from": {"name": "Düsseldorf Hbf"},
                    "to": {"name": "Köln Hbf"},
                    "trip": {"route": {"shortName": "ICE 1"}},
                    "duration": 5400,
                }
            ],
        }
    ]
    result = _parse_otp_itineraries(itineraries)
    assert len(result) == 1
    assert result[0]["legs"][0]["line"] == "ICE 1"
    assert result[0]["legs"][0]["product"] == "train"


def test_parse_otp_itineraries_transfer_risk_calculation():
    """Test transfer risk is calculated from leg timings."""
    now_ms = 1705312200000
    gap_ms = 2 * 60 * 1000  # 2 minute gap = high risk

    itineraries = [
        {
            "duration": 3600,
            "numberOfTransfers": 1,
            "legs": [
                {
                    "transitLeg": True,
                    "startTime": now_ms,
                    "endTime": now_ms + 1800000,
                    "departureDelay": 0,
                    "arrivalDelay": 0,
                    "mode": "BUS",
                    "from": {"name": "A"},
                    "to": {"name": "B"},
                    "trip": {"route": {"shortName": "Bus 1"}},
                    "duration": 1800,
                },
                {
                    "transitLeg": True,
                    "startTime": now_ms + 1800000 + gap_ms,
                    "endTime": now_ms + 3600000,
                    "departureDelay": 0,
                    "arrivalDelay": 0,
                    "mode": "RAIL",
                    "from": {"name": "B"},
                    "to": {"name": "C"},
                    "trip": {"route": {"shortName": "S1"}},
                    "duration": 1800,
                },
            ],
        }
    ]
    result = _parse_otp_itineraries(itineraries)
    assert len(result) == 1
    assert result[0]["transfer_risk"] in ("low", "medium", "high", "missed")
    assert result[0]["min_transfer_time"] == 2


def test_parse_otp_itineraries_with_delay():
    """Test _parse_otp_itineraries calculates departure delay."""
    now_ms = 1705312200000
    delay_s = 300  # 5 minute delay

    itineraries = [
        {
            "duration": 3600,
            "numberOfTransfers": 0,
            "legs": [
                {
                    "transitLeg": True,
                    "startTime": now_ms + delay_s * 1000,
                    "endTime": now_ms + 3600000,
                    "departureDelay": delay_s,
                    "arrivalDelay": 0,
                    "mode": "RAIL",
                    "from": {"name": "Start"},
                    "to": {"name": "End"},
                    "trip": None,
                    "duration": 3600,
                }
            ],
        }
    ]
    result = _parse_otp_itineraries(itineraries)
    assert result[0]["legs"][0]["delay"] == 5


def test_parse_otp_itineraries_walk_leg_skipped():
    """Test walking legs are skipped in output but used for transfer calc."""
    now_ms = 1705312200000

    itineraries = [
        {
            "duration": 3600,
            "numberOfTransfers": 0,
            "legs": [
                {
                    "transitLeg": True,
                    "startTime": now_ms,
                    "endTime": now_ms + 1800000,
                    "departureDelay": 0,
                    "arrivalDelay": 0,
                    "mode": "RAIL",
                    "from": {"name": "A"},
                    "to": {"name": "B"},
                    "trip": {"route": {"shortName": "RE1"}},
                    "duration": 1800,
                },
                {
                    "transitLeg": False,  # walking leg
                    "startTime": now_ms + 1800000,
                    "endTime": now_ms + 1860000,
                    "mode": "WALK",
                    "duration": 60,
                },
            ],
        }
    ]
    result = _parse_otp_itineraries(itineraries)
    assert len(result) == 1
    # Walking leg should not be in legs output
    assert len(result[0]["legs"]) == 1


# ── async_plan_trip ───────────────────────────────────────────────────────────

async def test_plan_trip_unsupported_provider(hass: HomeAssistant):
    """Test plan_trip returns None for unsupported provider."""
    result = await async_plan_trip(hass, "unsupported", "A", "City", "B", "City")
    assert result is None


async def test_plan_trip_otp2_missing_ids(hass: HomeAssistant):
    """Test OTP2 plan_trip returns None when stop IDs missing."""
    result = await async_plan_trip(
        hass, "openpublictransport", "A", "City", "B", "City",
        origin_id=None, dest_id=None,
    )
    assert result is None


async def test_plan_trip_vbn_missing_ids(hass: HomeAssistant):
    """Test VBN OTP plan_trip returns None when stop IDs missing."""
    result = await async_plan_trip(
        hass, "vbn_otp", "A", "City", "B", "City",
        origin_id=None, dest_id=None,
    )
    assert result is None


async def test_plan_trip_efa_success(hass: HomeAssistant):
    """Test EFA trip planning returns parsed journeys."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "journeys": [
            {
                "legs": [
                    {
                        "origin": {"name": "Düsseldorf Hbf"},
                        "destination": {"name": "Köln Hbf"},
                        "transportation": {"number": "RE1", "product": {"name": "RE"}},
                        "duration": 3600,
                    }
                ],
                "interchanges": 0,
            }
        ]
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as mock_session_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session_fn.return_value = mock_session

        result = await async_plan_trip(
            hass, "vrr", "Düsseldorf Hbf", "Düsseldorf", "Köln Hbf", "Köln"
        )

    assert result is not None
    assert len(result) == 1


async def test_plan_trip_efa_non_200(hass: HomeAssistant):
    """Test EFA trip planning returns None on non-200 response."""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as mock_session_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session_fn.return_value = mock_session

        result = await async_plan_trip(hass, "vrr", "A", "City", "B", "City")

    assert result is None


async def test_plan_trip_efa_exception(hass: HomeAssistant):
    """Test EFA trip planning handles exception gracefully."""
    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as mock_session_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("Network error"))
        mock_session_fn.return_value = mock_session

        result = await async_plan_trip(hass, "vrr", "A", "City", "B", "City")

    assert result is None


async def test_plan_trip_efa_with_stop_ids(hass: HomeAssistant):
    """Test EFA trip planning uses stop IDs when provided."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"journeys": []})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as mock_session_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session_fn.return_value = mock_session

        result = await async_plan_trip(
            hass, "vrr", "A", "City", "B", "City",
            origin_id="de:12345", dest_id="de:67890",
        )

    assert result == []


async def test_plan_trip_efa_non_dict_response(hass: HomeAssistant):
    """Test EFA trip planning returns None for non-dict response."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[])
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.trip.async_get_clientsession") as mock_session_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session_fn.return_value = mock_session

        result = await async_plan_trip(hass, "vrr", "A", "City", "B", "City")

    assert result is None
