"""Tests for parser utilities."""

from homeassistant.util import dt as dt_util

from custom_components.openpublictransport.parsers import parse_departure_generic


def test_parse_departure_generic_success():
    """Test successful departure parsing."""
    stop = {
        "departureTimePlanned": "2025-01-15T10:00:00+01:00",
        "departureTimeEstimated": "2025-01-15T10:05:00+01:00",
        "transportation": {
            "number": "U79",
            "destination": {"name": "Duisburg"},
            "product": {"class": 4},
        },
        "platform": {"name": "2"},
        "realtimeStatus": ["MONITORED"],
    }

    tz = dt_util.get_time_zone("Europe/Berlin")
    now = dt_util.parse_datetime("2025-01-15T09:55:00+01:00")

    def get_transport_type(transportation):
        return "tram"

    def get_platform(stop):
        return stop.get("platform", {}).get("name", "")

    def get_realtime(stop, est, plan):
        return "MONITORED" in stop.get("realtimeStatus", [])

    departure = parse_departure_generic(stop, tz, now, get_transport_type, get_platform, get_realtime)

    assert departure is not None
    assert departure.line == "U79"
    assert departure.destination == "Duisburg"
    assert departure.delay == 5
    assert departure.platform == "2"
    assert departure.transportation_type == "tram"
    assert departure.is_realtime is True
    assert departure.minutes_until_departure == 10


def test_parse_departure_generic_missing_planned_time():
    """Test parsing with missing planned time."""
    stop = {
        "departureTimeEstimated": "2025-01-15T10:05:00+01:00",
        "transportation": {"number": "U79", "destination": {"name": "Duisburg"}},
    }

    tz = dt_util.get_time_zone("Europe/Berlin")
    now = dt_util.parse_datetime("2025-01-15T09:55:00+01:00")

    departure = parse_departure_generic(
        stop,
        tz,
        now,
        lambda t: "tram",
        lambda s: "",
        lambda s, est, plan: False,
    )

    assert departure is None


def test_parse_departure_generic_invalid_stop():
    """Test parsing with invalid stop data."""
    stop = "invalid"  # Not a dict

    tz = dt_util.get_time_zone("Europe/Berlin")
    now = dt_util.parse_datetime("2025-01-15T09:55:00+01:00")

    departure = parse_departure_generic(
        stop,
        tz,
        now,
        lambda t: "tram",
        lambda s: "",
        lambda s, est, plan: False,
    )

    assert departure is None


def test_parse_departure_generic_no_delay():
    """Test parsing with no delay."""
    stop = {
        "departureTimePlanned": "2025-01-15T10:00:00+01:00",
        "departureTimeEstimated": "2025-01-15T10:00:00+01:00",
        "transportation": {
            "number": "U79",
            "destination": {"name": "Duisburg"},
            "product": {"class": 4},
        },
        "platform": {"name": "2"},
        "realtimeStatus": [],
    }

    tz = dt_util.get_time_zone("Europe/Berlin")
    now = dt_util.parse_datetime("2025-01-15T09:55:00+01:00")

    departure = parse_departure_generic(
        stop,
        tz,
        now,
        lambda t: "tram",
        lambda s: s.get("platform", {}).get("name", ""),
        lambda s, est, plan: False,
    )

    assert departure is not None
    assert departure.delay == 0
    assert departure.is_realtime is False


def test_parse_departure_generic_with_agency():
    """Test parsing with agency information."""
    stop = {
        "departureTimePlanned": "2025-01-15T10:00:00+01:00",
        "departureTimeEstimated": "2025-01-15T10:00:00+01:00",
        "transportation": {
            "number": "U79",
            "destination": {"name": "Duisburg"},
            "product": {"class": 4},
        },
        "platform": {"name": "2"},
        "realtimeStatus": [],
        "agency": "Rheinbahn",
    }

    tz = dt_util.get_time_zone("Europe/Berlin")
    now = dt_util.parse_datetime("2025-01-15T09:55:00+01:00")

    departure = parse_departure_generic(
        stop,
        tz,
        now,
        lambda t: "tram",
        lambda s: s.get("platform", {}).get("name", ""),
        lambda s, est, plan: False,
    )

    assert departure is not None
    assert departure.agency == "Rheinbahn"


def test_parse_departure_generic_past_departure():
    """Test parsing with past departure time."""
    stop = {
        "departureTimePlanned": "2025-01-15T09:00:00+01:00",
        "departureTimeEstimated": "2025-01-15T09:00:00+01:00",
        "transportation": {
            "number": "U79",
            "destination": {"name": "Duisburg"},
            "product": {"class": 4},
        },
        "platform": {"name": "2"},
        "realtimeStatus": [],
    }

    tz = dt_util.get_time_zone("Europe/Berlin")
    now = dt_util.parse_datetime("2025-01-15T10:00:00+01:00")  # After departure

    departure = parse_departure_generic(
        stop,
        tz,
        now,
        lambda t: "tram",
        lambda s: s.get("platform", {}).get("name", ""),
        lambda s, est, plan: False,
    )

    assert departure is not None
    assert departure.minutes_until_departure == 0  # Should be 0 for past departures
