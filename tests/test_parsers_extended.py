"""Extended tests for parsers.py — covering the uncovered branches."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.parsers import parse_departure_generic

_TZ = ZoneInfo("Europe/Berlin")
_NOW = datetime(2025, 1, 15, 10, 0, tzinfo=_TZ)

_TYPE_FN = lambda t: "bus"
_PLATFORM_FN = lambda s: s.get("platform", {}).get("name", "") if isinstance(s.get("platform"), dict) else ""
_REALTIME_FN = lambda s, est, pln: est != pln if est and pln else False


def _base_stop(**overrides):
    stop = {
        "departureTimePlanned": "2025-01-15T10:05:00+01:00",
        "departureTimeEstimated": "2025-01-15T10:10:00+01:00",
        "transportation": {
            "number": "U79",
            "destination": {"name": "Duisburg Hbf"},
            "description": "U-Bahn",
            "product": {"class": 4},
        },
        "platform": {"name": "2"},
    }
    stop.update(overrides)
    return stop


def test_parse_non_dict_stop():
    """Test that non-dict stop returns None."""
    result = parse_departure_generic("not a dict", _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is None


def test_parse_missing_planned_time():
    """Test that missing departureTimePlanned returns None."""
    stop = _base_stop()
    del stop["departureTimePlanned"]
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is None


def test_parse_non_string_planned_time():
    """Test that non-string departureTimePlanned returns None."""
    stop = _base_stop(departureTimePlanned=12345)
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is None


def test_parse_invalid_planned_time_string():
    """Test that unparseable time string returns None."""
    stop = _base_stop(departureTimePlanned="not-a-date")
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is None


def test_parse_valid_stop():
    """Test that valid stop parses correctly."""
    result = parse_departure_generic(_base_stop(), _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert result.line == "U79"
    assert result.destination == "Duisburg Hbf"
    assert result.delay == 5


def test_parse_no_estimated_time_uses_planned():
    """Test that missing estimated time uses planned time (0 delay)."""
    stop = _base_stop()
    del stop["departureTimeEstimated"]
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert result.delay == 0


def test_parse_invalid_transportation_falls_back():
    """Test that invalid transportation dict falls back gracefully."""
    stop = _base_stop(transportation="not a dict")
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert result.line == ""
    assert result.destination == "Unknown"


def test_parse_with_infos_notices():
    """Test that infos are extracted as notices."""
    stop = _base_stop()
    stop["infos"] = [
        {"subtitle": "Service disruption"},
        {"title": "Delay warning"},
        {"content": "Bus replacement"},
    ]
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert "Service disruption" in result.notices
    assert "Delay warning" in result.notices
    assert "Bus replacement" in result.notices


def test_parse_with_hints_notices():
    """Test that hints are extracted as notices."""
    stop = _base_stop()
    stop["hints"] = [{"content": "Use rear entrance"}, {"text": "Next stop change"}]
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert "Use rear entrance" in result.notices


def test_parse_with_platform_change():
    """Test that platform change is detected."""
    stop = _base_stop()
    stop["plannedPlatformName"] = "1"
    stop["platform"] = {"name": "3"}
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert result.platform_changed is True
    assert result.planned_platform == "1"


def test_parse_with_agency():
    """Test that agency field is extracted."""
    stop = _base_stop()
    stop["agency"] = "VRR GmbH"
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert result.agency == "VRR GmbH"


def test_parse_exception_returns_none():
    """Test that exceptions in parse return None."""
    def bad_type_fn(t):
        raise RuntimeError("oops")

    result = parse_departure_generic(_base_stop(), _TZ, _NOW, bad_type_fn, _PLATFORM_FN, _REALTIME_FN)
    assert result is None


def test_parse_invalid_destination_obj():
    """Test that invalid destination object is handled."""
    stop = _base_stop()
    stop["transportation"]["destination"] = "not a dict"
    result = parse_departure_generic(stop, _TZ, _NOW, _TYPE_FN, _PLATFORM_FN, _REALTIME_FN)
    assert result is not None
    assert result.destination == "Unknown"
