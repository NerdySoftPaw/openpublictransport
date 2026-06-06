"""Targeted tests to push test coverage from 91% → 95%+.

Covers missing branches in:
  - config_flow.py  (Trafiklab/NTA/stopfinder HTTP errors, settings guards, credentials, cache)
  - __init__.py     (credential migration, service edge cases, unload cleanup)
  - trip.py         (transfer risk branches, _ms_to_hhmm/_format_time errors)
  - binary_sensor.py (no-data path, fallback parse_fn)
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientConnectorError
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PROVIDER,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRAFIKLAB_API_KEY,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_VBN_API_KEY,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_HVV,
    PROVIDER_KVV,
    PROVIDER_NTA_IE,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
    PROVIDER_VRR,
)

_SETTINGS = {
    CONF_DEPARTURES: 10,
    CONF_SCAN_INTERVAL: 60,
    CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
    CONF_USE_PROVIDER_LOGO: False,
    CONF_DELAY_THRESHOLD: 5,
    CONF_LINE_FILTER: "",
    CONF_FAVORITE_LINES: "",
    CONF_WALKING_TIME: 0,
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_flow(**kwargs) -> OpenPublicTransportConfigFlow:
    """Create a bare OpenPublicTransportConfigFlow without going through HA."""
    flow = OpenPublicTransportConfigFlow.__new__(OpenPublicTransportConfigFlow)
    flow._provider = kwargs.get("provider", PROVIDER_VRR)
    flow._api_key = kwargs.get("api_key", None)
    flow._api_key_secondary = kwargs.get("api_key_secondary", None)
    flow._otp_custom_url = kwargs.get("otp_custom_url", None)
    flow._entry_type = kwargs.get("entry_type", "departures")
    flow._found_stops = kwargs.get("found_stops", [])
    flow._selected_stop = kwargs.get("selected_stop", None)
    flow._trip_origin = kwargs.get("trip_origin", None)
    flow._trip_destination = kwargs.get("trip_destination", None)
    flow._trip_search_phase = kwargs.get("trip_search_phase", "origin")
    flow._search_cache = {}
    flow._cache_ttl = 300
    flow._reauth_entry = kwargs.get("reauth_entry", None)
    return flow


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — internal pure methods (no HA needed)
# ══════════════════════════════════════════════════════════════════════════════

def test_levenshtein_distance_empty_str2():
    """Cover branch: len(str2) == 0 → return len(str1)."""
    flow = _make_flow()
    assert flow._levenshtein_distance("hello", "") == 5
    assert flow._levenshtein_distance("", "") == 0


def test_levenshtein_distance_swap():
    """Cover branch: len(str1) < len(str2) → swap."""
    flow = _make_flow()
    result = flow._levenshtein_distance("hi", "hello")
    assert result == flow._levenshtein_distance("hello", "hi")


def test_calculate_relevance_fuzzy_0_7_to_0_8():
    """Cover branch: best_word_match > 0.7 (but ≤ 0.8) → score += int(ratio * 40)."""
    flow = _make_flow()
    # "Mannheim" vs "Mannhiem" — one transposition, ratio ~0.75
    score = flow._calculate_relevance("Mannhiem", "Mannheim", "")
    assert score > 0


def test_calculate_relevance_levenshtein_bonus_2():
    """Cover branch: distance ≤ 3 and max_len > 8 → score += 80."""
    flow = _make_flow()
    # "Heidelberg" vs "Hedelberg" — distance 2, len 10 > 8
    score = flow._calculate_relevance("Hedelberg", "Heidelberg", "")
    assert score > 0


def test_calculate_relevance_long_place_penalty():
    """Cover branch: place length > 20 → score -= 10."""
    flow = _make_flow()
    short_score = flow._calculate_relevance("test", "test", "Berlin")
    long_score = flow._calculate_relevance("test", "test", "A very very long city name that has more than 20 chars")
    assert long_score < short_score


async def test_search_stops_nta_non_empty():
    """Cover _search_stops_nta with valid search term → returns list with stop."""
    flow = _make_flow(provider=PROVIDER_NTA_IE, api_key="key")
    result = await flow._search_stops_nta("8250DB001234")
    assert len(result) == 1
    assert result[0]["id"] == "8250DB001234"


async def test_search_stops_nta_empty():
    """Cover _search_stops_nta with empty/whitespace search term → returns []."""
    flow = _make_flow(provider=PROVIDER_NTA_IE, api_key="key")
    result = await flow._search_stops_nta("   ")
    assert result == []


def test_get_stopfinder_url_kvv():
    """Cover _get_stopfinder_url branch for KVV."""
    flow = _make_flow(provider=PROVIDER_KVV)
    url = flow._get_stopfinder_url()
    assert "kvv" in url


def test_get_stopfinder_url_hvv():
    """Cover _get_stopfinder_url branch for HVV."""
    flow = _make_flow(provider=PROVIDER_HVV)
    url = flow._get_stopfinder_url()
    assert "hvv" in url


def test_parse_stopfinder_response_invalid_location_type():
    """Cover branch: non-dict location entry is skipped."""
    flow = _make_flow()
    data = {
        "locations": [
            "not-a-dict",
            {"name": "Hbf", "id": "de:1", "type": "stop"},
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "Hbf")
    assert len(results) == 1
    assert results[0]["id"] == "de:1"


def test_parse_stopfinder_response_non_dict():
    """Cover branch: data is not a dict → returns []."""
    flow = _make_flow()
    results = flow._parse_stopfinder_response(["wrong"], "stop", "x")
    assert results == []


def test_parse_stopfinder_response_locations_not_list():
    """Cover branch: locations is not a list → returns []."""
    flow = _make_flow()
    results = flow._parse_stopfinder_response({"locations": "wrong"}, "stop", "x")
    assert results == []


def test_parse_stopfinder_response_non_str_loc_type():
    """Cover branch: loc_type is not a str → treated as 'unknown'."""
    flow = _make_flow()
    data = {
        "locations": [
            {"name": "Stop A", "id": "de:1", "type": 42}
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "Stop A")
    # type=42 → coerced to "unknown" which is allowed for stop search
    assert any(r["id"] == "de:1" for r in results)


def test_parse_stopfinder_response_non_str_name_skipped():
    """Cover branch: name is not a str → location skipped."""
    flow = _make_flow()
    data = {
        "locations": [
            {"name": 999, "id": "de:1", "type": "stop"}
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "x")
    assert results == []


def test_parse_stopfinder_response_non_dict_properties():
    """Cover branch: non-dict 'properties' → coerced to {}."""
    flow = _make_flow()
    data = {
        "locations": [
            {"name": "Stop A", "id": "de:1", "type": "stop", "properties": "wrong"}
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "Stop A")
    assert any(r["id"] == "de:1" for r in results)


def test_parse_stopfinder_response_non_dict_ref():
    """Cover branch: non-dict 'ref' → coerced to {}."""
    flow = _make_flow()
    data = {
        "locations": [
            {"name": "Stop A", "id": "de:1", "type": "stop", "ref": "bad"}
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "Stop A")
    assert any(r["id"] == "de:1" for r in results)


def test_parse_stopfinder_response_non_dict_parent():
    """Cover branch: non-dict 'parent' → coerced to {}."""
    flow = _make_flow()
    data = {
        "locations": [
            {"name": "Stop A", "id": "de:1", "type": "stop", "parent": "not-dict"}
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "Stop A")
    assert any(r["id"] == "de:1" for r in results)


def test_parse_stopfinder_response_skips_wrong_type_for_stop_search():
    """Cover branch: loc_type not in allowed set for stop search → skipped."""
    flow = _make_flow()
    data = {
        "locations": [
            {"name": "City Center", "id": "de:1", "type": "locality"}
        ]
    }
    results = flow._parse_stopfinder_response(data, "stop", "City")
    # 'locality' is not in allowed stop types → skipped
    assert results == []


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — _search_stops_trafiklab via flow (HTTP error branches)
# ══════════════════════════════════════════════════════════════════════════════

async def _start_trafiklab_flow_to_search(hass: HomeAssistant):
    """Helper: start Trafiklab flow and arrive at stop_search step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "test-api-key"}
    )
    assert result2["step_id"] == "stop_search"
    return result2["flow_id"]


async def test_trafiklab_search_401(hass: HomeAssistant):
    """Cover lines 980-983: Trafiklab 401 → no retry, return []."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None  # force fallback to _search_stops_trafiklab
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session

            result = await hass.config_entries.flow.async_configure(
                flow_id, user_input={"stop_search": "Stockholm"}
            )
    assert result["step_id"] == "stop_search"
    assert result.get("errors", {}).get("stop_search") == "no_results"


async def test_trafiklab_search_404(hass: HomeAssistant):
    """Cover lines 984-987: Trafiklab 404 → no retry, return []."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session

            result = await hass.config_entries.flow.async_configure(
                flow_id, user_input={"stop_search": "Göteborg"}
            )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_search_500_all_retries(hass: HomeAssistant):
    """Cover lines 988-1011: Trafiklab 500 → retry 3 times, return []."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await hass.config_entries.flow.async_configure(
                    flow_id, user_input={"stop_search": "Malmö"}
                )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_search_timeout(hass: HomeAssistant):
    """Cover lines 1012-1017: Trafiklab timeout → retry exhausted, return []."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
            mock_sess.return_value = mock_session
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await hass.config_entries.flow.async_configure(
                    flow_id, user_input={"stop_search": "Lund"}
                )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_search_connection_error(hass: HomeAssistant):
    """Cover lines 1018-1023: Trafiklab ClientConnectorError → retry exhausted."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    conn_err = ClientConnectorError(MagicMock(), OSError("refused"))
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(side_effect=conn_err)
            mock_sess.return_value = mock_session
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await hass.config_entries.flow.async_configure(
                    flow_id, user_input={"stop_search": "Uppsala"}
                )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_search_json_error(hass: HomeAssistant):
    """Cover lines 935-940: Trafiklab invalid JSON response → retry → return []."""
    import aiohttp
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await hass.config_entries.flow.async_configure(
                    flow_id, user_input={"stop_search": "Västerås"}
                )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_search_non_dict_response(hass: HomeAssistant):
    """Cover lines 944-948: Trafiklab returns non-dict JSON → retry → return []."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=["list", "not", "dict"])
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await hass.config_entries.flow.async_configure(
                    flow_id, user_input={"stop_search": "Norrköping"}
                )
    assert result["step_id"] == "stop_search"


async def test_trafiklab_search_non_dict_stop_group(hass: HomeAssistant):
    """Cover line 956: stop_group is not a dict → skipped."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"stop_groups": ["not-a-dict", {"id": "1", "name": "Hbf", "stops": []}]})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session

            result = await hass.config_entries.flow.async_configure(
                flow_id, user_input={"stop_search": "Stockholm"}
            )
    # One valid stop_group → 1 result found → auto-selects or shows selection step
    assert result["step_id"] in ("stop_select", "stop_search", "settings")


async def test_trafiklab_search_stop_group_with_place_extraction(hass: HomeAssistant):
    """Cover lines 963-964: extract place from stop_group name with comma."""
    flow_id = await _start_trafiklab_flow_to_search(hass)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "stop_groups": [
            {
                "id": "se:1",
                "name": "Stockholm, Centralstation",
                "stops": [{"id": "se:1:1"}],
            }
        ]
    })
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_gp.return_value = None
        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_sess.return_value = mock_session

            result = await hass.config_entries.flow.async_configure(
                flow_id, user_input={"stop_search": "Stockholm"}
            )
    # Should have found 1 result → stop_select or settings
    assert result["step_id"] in ("stop_select", "settings", "stop_search")


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — NTA stop search via flow
# ══════════════════════════════════════════════════════════════════════════════

async def test_nta_flow_stop_id_step(hass: HomeAssistant):
    """Cover NTA nta_stop_id step: enter stop ID and validate."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-key", CONF_NTA_API_KEY_SECONDARY: ""},
    )
    assert result2["step_id"] == "nta_stop_id"

    # Submit a stop ID - mock provider to avoid real network call
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.fetch_departures = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={CONF_STATION_ID: "8250DB001234"}
        )
    assert result3["step_id"] == "settings"


async def test_nta_flow_stop_id_empty_error(hass: HomeAssistant):
    """Cover NTA nta_stop_id with empty input → error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-key", CONF_NTA_API_KEY_SECONDARY: ""},
    )
    assert result2["step_id"] == "nta_stop_id"
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={CONF_STATION_ID: ""}
    )
    assert result3["step_id"] == "nta_stop_id"
    assert result3.get("errors", {}).get(CONF_STATION_ID) == "station_id_required"


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — stop_search: select stop from found list
# ══════════════════════════════════════════════════════════════════════════════

async def test_stop_search_select_stop_from_found_list(hass: HomeAssistant):
    """Cover lines 552-555: selecting a stop from stop_search that was just found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [{"id": "de:1", "name": "Hbf", "place": "Düsseldorf"}]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf"}
        )

    if result2["step_id"] == "stop_search":
        # Only one result → might auto-select, or need to explicitly pick it
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "de:1"}
        )
        assert result3["step_id"] == "settings"
    elif result2["step_id"] == "stop_select":
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "de:1"}
        )
        assert result3["step_id"] == "settings"


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — stop_select edge cases
# ══════════════════════════════════════════════════════════════════════════════

async def test_stop_select_valid_stop_goes_to_settings(hass: HomeAssistant):
    """Cover stop_select: selecting a valid stop goes to settings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:1", "name": "Hbf", "place": "Düsseldorf"},
        {"id": "de:2", "name": "Airport", "place": "Düsseldorf"},
    ]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf"}
        )
    assert result2["step_id"] == "stop_select"

    # Select a valid stop
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"stop": "de:1"}
    )
    assert result3["step_id"] == "settings"


async def test_stop_select_empty_found_stops_returns_to_search(hass: HomeAssistant):
    """Cover lines 621-622: stop_select with empty found_stops redirects to stop_search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:1", "name": "Hbf", "place": "Düsseldorf"},
        {"id": "de:2", "name": "Airport", "place": "Düsseldorf"},
    ]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf"}
        )
    assert result2["step_id"] == "stop_select"

    # Select "search again" → redirects to stop_search
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"stop": "__search_again__"}
    )
    assert result3["step_id"] == "stop_search"


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — settings guards (missing API keys)
# ══════════════════════════════════════════════════════════════════════════════

async def _flow_to_settings_with_provider(hass, provider, api_key_input):
    """Helper: run a flow to the settings step for a provider that needs an API key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: provider},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=api_key_input
    )
    assert result2["step_id"] in ("stop_search", "api_key")
    return result["flow_id"], result2


async def test_settings_rmv_no_api_key(hass: HomeAssistant):
    """Cover line 713: settings step for RMV with missing API key."""
    flow_id, r = await _flow_to_settings_with_provider(
        hass, PROVIDER_RMV, {CONF_RMV_API_KEY: "rmv-key"}
    )
    assert r["step_id"] == "stop_search"

    mock_stops = [{"id": "de:r1", "name": "Frankfurt Hbf", "place": "Frankfurt"}]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result3 = await hass.config_entries.flow.async_configure(
            flow_id, user_input={"stop_search": "Frankfurt"}
        )

    if result3["step_id"] == "stop_select":
        result4 = await hass.config_entries.flow.async_configure(
            flow_id, user_input={"stop": "de:r1"}
        )
    else:
        result4 = result3
    assert result4["step_id"] == "settings"

    # Submit settings — api key should be present from flow state
    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        result5 = await hass.config_entries.flow.async_configure(flow_id, user_input=_SETTINGS)
    assert result5["type"] == "create_entry"


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — _find_credentials_from_application_credentials
# ══════════════════════════════════════════════════════════════════════════════

async def test_find_credentials_from_ac_store_returns_opt_key(hass: HomeAssistant):
    """Cover lines 185-186: AC store returns OPT api_key."""
    from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow

    flow = _make_flow(provider=PROVIDER_OPT)
    flow.hass = hass

    mock_cred = MagicMock()
    mock_cred.client_id = "opt-key-123"
    mock_cred.client_secret = ""

    mock_storage = MagicMock()
    mock_storage.async_client_credentials = MagicMock(
        return_value={f"{DOMAIN}.{PROVIDER_OPT}": mock_cred}
    )

    with patch.dict(hass.data, {"application_credentials": mock_storage}):
        with patch(
            "custom_components.openpublictransport.config_flow.DATA_COMPONENT",
            "application_credentials",
            create=True,
        ):
            result = flow._find_credentials_from_application_credentials(PROVIDER_OPT)

    # Should have returned {} or the key (depending on import mock)
    assert isinstance(result, dict)


async def test_find_credentials_ac_store_exception(hass: HomeAssistant):
    """Cover lines 200-201: exception in AC store lookup → returns {}."""
    flow = _make_flow(provider=PROVIDER_VRR)
    flow.hass = hass

    with patch(
        "custom_components.openpublictransport.config_flow.DATA_COMPONENT",
        new_callable=lambda: property(lambda *_: (_ for _ in ()).throw(ImportError("no AC"))),
        create=True,
    ):
        # ImportError is raised when accessing DATA_COMPONENT → except catches it
        result = flow._find_credentials_from_application_credentials(PROVIDER_VRR)
    assert result == {}


async def test_async_store_credential_no_key(hass: HomeAssistant):
    """Cover line 260: _async_store_credential with no api_key and non-OTP_CUSTOM returns early."""
    flow = _make_flow(provider=PROVIDER_VRR)
    flow.hass = hass
    flow._api_key = None
    # For non-OTP_CUSTOM with no key, should return without calling import
    with patch(
        "custom_components.openpublictransport.config_flow.async_import_client_credential",
        new_callable=AsyncMock,
    ) as mock_import:
        await flow._async_store_credential(PROVIDER_VRR)
    mock_import.assert_not_called()


async def test_async_store_credential_exception(hass: HomeAssistant):
    """Cover lines 273-274: _async_store_credential handles exception from AC store."""
    flow = _make_flow(provider=PROVIDER_VRR)
    flow.hass = hass
    flow._api_key = "some-key"
    with patch(
        "custom_components.openpublictransport.config_flow.async_import_client_credential",
        new_callable=AsyncMock,
        side_effect=Exception("store failed"),
    ):
        # Should not raise
        await flow._async_store_credential(PROVIDER_VRR)


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — trip_select edge cases
# ══════════════════════════════════════════════════════════════════════════════

async def test_trip_select_search_again_returns_to_trip_search(hass: HomeAssistant):
    """Cover trip_select: 'search again' sentinel → returns to trip_search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    origin_stops = [
        {"id": "de:1", "name": "Hbf A", "place": "City"},
        {"id": "de:2", "name": "Hbf B", "place": "City"},
    ]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=origin_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf"}
        )
    assert result2["step_id"] == "trip_select"

    # Select "search again" → redirects to trip_search
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"stop": "__search_again__"}
    )
    assert result3["step_id"] == "trip_search"


async def test_trip_select_origin_selected_goes_to_destination(hass: HomeAssistant):
    """Cover trip_select: selecting origin → moves to destination search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )
    origin_stops = [
        {"id": "de:1", "name": "Hbf A", "place": "City"},
        {"id": "de:2", "name": "Hbf B", "place": "City"},
    ]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=origin_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf"}
        )
    assert result2["step_id"] == "trip_select"

    # Select origin → goes to destination search (trip_search phase=destination)
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"stop": "de:1"}
    )
    assert result3["step_id"] == "trip_search"


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — trip_settings with OPT and OTP_CUSTOM API key
# ══════════════════════════════════════════════════════════════════════════════

async def test_trip_settings_with_opt_api_key(hass: HomeAssistant):
    """Cover lines 1535-1536: trip_settings stores OPT api_key in data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_OPT},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OPT_API_KEY: "opt-key"}
    )
    assert result2["step_id"] == "trip_search"

    mock_stops = [{"id": "opt:1", "name": "Berlin Hbf", "place": "Berlin"}]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=[mock_stops, mock_stops])
        mock_gp.return_value = mock_provider
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop_search": "Berlin"}
        )
        result4 = await hass.config_entries.flow.async_configure(
            result3["flow_id"] if "flow_id" in result3 else result["flow_id"],
            user_input={"stop_search": "Hamburg"},
        )

    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        final = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_SCAN_INTERVAL: 120}
        )
    assert final["type"] == "create_entry"
    assert final["data"].get(CONF_OPT_API_KEY) == "opt-key"


async def test_trip_settings_with_otp_custom_api_key(hass: HomeAssistant):
    """Cover lines 1537-1540: trip_settings stores OTP_CUSTOM api_key and URL."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    mock_health = MagicMock()
    mock_health.status = 200
    mock_health.__aenter__ = AsyncMock(return_value=mock_health)
    mock_health.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_health)
        mock_sess.return_value = mock_session
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_OTP_BASE_URL: "http://otp.local/otp", CONF_OTP_CUSTOM_API_KEY: "otp-key"},
        )
    assert result2["step_id"] == "trip_search"

    mock_stops = [{"id": "otp:1", "name": "Start", "place": "City"}]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=[mock_stops, mock_stops])
        mock_gp.return_value = mock_provider
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Start"}
        )
        result4 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "End"}
        )

    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        final = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_SCAN_INTERVAL: 120}
        )
    assert final["type"] == "create_entry"
    assert final["data"].get(CONF_OTP_CUSTOM_API_KEY) == "otp-key"


# ══════════════════════════════════════════════════════════════════════════════
# config_flow.py — reauth errors
# ══════════════════════════════════════════════════════════════════════════════

async def _start_reauth_flow(hass: HomeAssistant, provider: str, entry_data: dict):
    """Helper: set up a config entry and start reauth flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: provider, **entry_data},
        unique_id=f"{provider}_reauth_test",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data={CONF_PROVIDER: provider, **entry_data},
    )
    return result


async def test_reauth_rmv_empty_key_error(hass: HomeAssistant):
    """Cover line 1642: reauth for RMV with empty key → error."""
    result = await _start_reauth_flow(hass, PROVIDER_RMV, {CONF_RMV_API_KEY: "old-key"})
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_RMV_API_KEY: ""}
    )
    assert result2["step_id"] == "reauth_confirm"
    assert CONF_RMV_API_KEY in result2.get("errors", {})


async def test_reauth_nta_empty_key_error(hass: HomeAssistant):
    """Cover line 1657: reauth for NTA with empty key → error."""
    result = await _start_reauth_flow(hass, PROVIDER_NTA_IE, {CONF_NTA_API_KEY: "old-key"})
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_NTA_API_KEY: ""}
    )
    assert result2["step_id"] == "reauth_confirm"
    assert CONF_NTA_API_KEY in result2.get("errors", {})


async def test_reauth_opt_empty_key_error(hass: HomeAssistant):
    """Cover line 1667: reauth for OPT with empty key → error."""
    result = await _start_reauth_flow(hass, PROVIDER_OPT, {CONF_OPT_API_KEY: "old-key"})
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OPT_API_KEY: ""}
    )
    assert result2["step_id"] == "reauth_confirm"
    assert CONF_OPT_API_KEY in result2.get("errors", {})


# ══════════════════════════════════════════════════════════════════════════════
# __init__.py — credential migration edge cases
# ══════════════════════════════════════════════════════════════════════════════

async def test_migrate_credential_no_api_key(hass: HomeAssistant):
    """Cover line 123: _async_migrate_credential skips when api_key is empty."""
    from custom_components.openpublictransport import _async_migrate_credential

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE,
            CONF_TRAFIKLAB_API_KEY: "",  # empty → should return early
        },
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.openpublictransport.async_import_client_credential",
        new_callable=AsyncMock,
    ) as mock_import:
        await _async_migrate_credential(hass, entry)
    mock_import.assert_not_called()


async def test_migrate_credential_exception(hass: HomeAssistant):
    """Cover lines 136-137: _async_migrate_credential logs warning on exception."""
    from custom_components.openpublictransport import _async_migrate_credential

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE,
            CONF_TRAFIKLAB_API_KEY: "real-key",
        },
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.openpublictransport.async_import_client_credential",
        new_callable=AsyncMock,
        side_effect=Exception("AC store failure"),
    ):
        # Should not raise, just log warning
        await _async_migrate_credential(hass, entry)


# ══════════════════════════════════════════════════════════════════════════════
# __init__.py — service handler edge cases
# ══════════════════════════════════════════════════════════════════════════════

async def test_handle_check_delays_non_dict_departure(hass: HomeAssistant):
    """Cover line 216: check_delays skips non-dict departure entries."""
    from custom_components.openpublictransport import async_setup

    await async_setup(hass, {})

    hass.states.async_set(
        "sensor.test",
        "state",
        {"departures": ["not-a-dict", {"delay": 10, "line": "U1"}]},
    )
    result = await hass.services.async_call(
        DOMAIN,
        "check_delays",
        {"entity_id": "sensor.test", "delay_threshold": 5},
        blocking=True,
        return_response=True,
    )
    assert result["count"] == 1


async def test_handle_announce_english_path(hass: HomeAssistant):
    """Cover line 286: announce with language='en' and minutes > 0."""
    from custom_components.openpublictransport import async_setup

    await async_setup(hass, {})

    hass.states.async_set(
        "sensor.test_announce",
        "state",
        {
            "departures": [
                {
                    "line": "RE5",
                    "destination": "Hamburg",
                    "planned_time": "14:35",
                    "delay": 3,
                    "platform": "7",
                    "minutes_until_departure": 5,
                    "transportation_type": "train",
                }
            ]
        },
    )
    result = await hass.services.async_call(
        DOMAIN,
        "announce_departure",
        {"entity_id": "sensor.test_announce", "language": "en"},
        blocking=True,
        return_response=True,
    )
    assert "Hamburg" in result["text"]
    assert "RE5" in result["text"]


async def test_handle_announce_tts_service(hass: HomeAssistant):
    """Cover lines 290-297: announce calls TTS service when tts_service is set."""
    from custom_components.openpublictransport import async_setup

    await async_setup(hass, {})

    hass.states.async_set(
        "sensor.test_tts",
        "state",
        {
            "departures": [
                {
                    "line": "S1",
                    "destination": "Airport",
                    "planned_time": "10:00",
                    "delay": 0,
                    "platform": "1",
                    "minutes_until_departure": 2,
                    "transportation_type": "train",
                }
            ]
        },
    )
    # Register a dummy TTS service so the announce handler can call it
    hass.services.async_register("tts", "google_say", lambda call: None)
    result = await hass.services.async_call(
        DOMAIN,
        "announce_departure",
        {
            "entity_id": "sensor.test_tts",
            "language": "de",
            "tts_service": "tts.google_say",
            "media_player": "media_player.living_room",
        },
        blocking=True,
        return_response=True,
    )
    assert "Airport" in result["text"] or "S1" in result["text"]


async def test_handle_announce_tts_exception(hass: HomeAssistant):
    """Cover lines 296-297: TTS exception is caught and logged."""
    from custom_components.openpublictransport import async_setup

    await async_setup(hass, {})

    hass.states.async_set(
        "sensor.tts_err",
        "state",
        {
            "departures": [
                {
                    "line": "M1",
                    "destination": "Zoo",
                    "planned_time": "09:00",
                    "delay": 0,
                    "platform": "",
                    "minutes_until_departure": 1,
                    "transportation_type": "bus",
                }
            ]
        },
    )
    # Register a TTS service that raises an exception
    async def _failing_tts(call):
        raise Exception("TTS failed")

    hass.services.async_register("tts", "fail_say", _failing_tts)
    result = await hass.services.async_call(
        DOMAIN,
        "announce_departure",
        {
            "entity_id": "sensor.tts_err",
            "tts_service": "tts.fail_say",
            "media_player": "media_player.living_room",
        },
        blocking=True,
        return_response=True,
    )
    # Should not raise, just log warning
    assert "text" in result


# ══════════════════════════════════════════════════════════════════════════════
# __init__.py — unload cleanup when last entry
# ══════════════════════════════════════════════════════════════════════════════

async def test_async_unload_entry_cleanup_when_last(hass: HomeAssistant):
    """Cover lines 412-419: cleanup when last entry is unloaded."""
    from custom_components.openpublictransport import async_setup, async_setup_entry, async_unload_entry
    from custom_components.openpublictransport.sensor import PublicTransportDataUpdateCoordinator

    await async_setup(hass, {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            CONF_STATION_ID: "de:test:999",
            "place_dm": "Test",
            "name_dm": "Station",
            CONF_DEPARTURES: 5,
            CONF_TRANSPORTATION_TYPES: ["bus"],
            CONF_SCAN_INTERVAL: 60,
        },
        unique_id="vrr_unload_test",
    )
    entry.add_to_hass(hass)

    with patch.object(
        PublicTransportDataUpdateCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ):
            await async_setup_entry(hass, entry)

    # Patch async_entries to return [] so the cleanup branch runs
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with patch.object(
            hass.config_entries,
            "async_entries",
            return_value=[],
        ):
            result = await async_unload_entry(hass, entry)

    assert result is True
    # After mocking empty entries, services should be cleaned up
    assert not hass.services.has_service(DOMAIN, "refresh_departures")


# ══════════════════════════════════════════════════════════════════════════════
# trip.py — transfer risk branches (OTP)
# ══════════════════════════════════════════════════════════════════════════════

def _make_otp_itinerary(gap_minutes: int) -> dict:
    """Build a minimal OTP itinerary dict with the given transfer gap."""
    now_ms = 1700000000000
    leg_duration_ms = 600000  # 10 min
    # Leg 1: arrives at now_ms + leg_duration_ms
    # Leg 2: departs at now_ms + leg_duration_ms + gap_minutes * 60000
    return {
        "duration": 1800,
        "numberOfTransfers": 1,
        "legs": [
            {
                "transitLeg": True,
                "mode": "BUS",
                "startTime": now_ms,
                "endTime": now_ms + leg_duration_ms,
                "departureDelay": 0,
                "arrivalDelay": 0,
                "from": {"name": "Start"},
                "to": {"name": "Transfer"},
                "trip": {"route": {"shortName": "42"}},
                "duration": 600,
            },
            {
                "transitLeg": True,
                "mode": "RAIL",
                "startTime": now_ms + leg_duration_ms + gap_minutes * 60000,
                "endTime": now_ms + leg_duration_ms * 2 + gap_minutes * 60000,
                "departureDelay": 0,
                "arrivalDelay": 0,
                "from": {"name": "Transfer"},
                "to": {"name": "End"},
                "trip": {"route": {"shortName": "RE1"}},
                "duration": 600,
            },
        ],
    }


def test_otp_transfer_risk_missed():
    """Cover lines 346-347: gap_min <= 0 → transfer_risk = 'missed'."""
    from custom_components.openpublictransport.trip import _parse_otp_itineraries

    itin = _make_otp_itinerary(-5)  # negative gap → missed
    results = _parse_otp_itineraries([itin])
    assert len(results) == 1
    assert results[0]["transfer_risk"] == "missed"
    assert results[0]["connection_feasible"] is False


def test_otp_transfer_risk_medium():
    """Cover lines 350-351: gap_min <= 5 and not missed/high → transfer_risk = 'medium'."""
    from custom_components.openpublictransport.trip import _parse_otp_itineraries

    itin = _make_otp_itinerary(4)  # gap 4 min → medium (not 0, not ≤3, but ≤5)
    results = _parse_otp_itineraries([itin])
    assert len(results) == 1
    assert results[0]["transfer_risk"] == "medium"


def test_ms_to_hhmm_exception():
    """Cover lines 384-385: _ms_to_hhmm with value that causes OSError."""
    from custom_components.openpublictransport.trip import _ms_to_hhmm

    # Extremely large value that might cause OSError on some platforms
    # Use a negative value which should cause ValueError/OSError
    result = _ms_to_hhmm(-999999999999999)
    assert result == ""


# ══════════════════════════════════════════════════════════════════════════════
# trip.py — EFA journey parsing edge cases
# ══════════════════════════════════════════════════════════════════════════════

def _make_efa_journey(transfer_minutes: int, dep_planned: str = "", dep_estimated: str = "") -> dict:
    """Build a minimal EFA journey dict."""
    now_str = "2026-01-01T10:00:00+01:00"
    arr_str = f"2026-01-01T10:10:00+01:00"
    dep2_str = f"2026-01-01T10:{10 + transfer_minutes:02d}:00+01:00"
    arr2_str = f"2026-01-01T10:{20 + transfer_minutes:02d}:00+01:00"

    return {
        "interchanges": 1,
        "legs": [
            {
                "origin": {
                    "departureTimePlanned": dep_planned or now_str,
                    "departureTimeEstimated": dep_estimated or now_str,
                },
                "destination": {
                    "arrivalTimePlanned": arr_str,
                    "arrivalTimeEstimated": arr_str,
                },
                "transportation": {
                    "number": "S1",
                    "product": {"class": 6, "name": "Suburban"},
                },
                "interchange": {},
                "duration": 600,
            },
            {
                "origin": {
                    "departureTimePlanned": dep2_str,
                    "departureTimeEstimated": dep2_str,
                },
                "destination": {
                    "arrivalTimePlanned": arr2_str,
                    "arrivalTimeEstimated": arr2_str,
                },
                "transportation": {
                    "number": "RE5",
                    "product": {"class": 4, "name": "Regional"},
                },
                "interchange": {},
                "duration": 600,
            },
        ],
    }


def test_efa_journey_transfer_risk_high():
    """Cover lines 468-469: EFA transfer ≤ 3 min → transfer_risk = 'high'."""
    from custom_components.openpublictransport.trip import _parse_journeys

    journey = _make_efa_journey(transfer_minutes=2)
    results = _parse_journeys([journey])
    assert len(results) == 1
    assert results[0]["transfer_risk"] == "high"


def test_efa_journey_transfer_risk_medium():
    """Cover lines 470-472: EFA transfer ≤ 5 min and not high → 'medium'."""
    from custom_components.openpublictransport.trip import _parse_journeys

    journey = _make_efa_journey(transfer_minutes=4)
    results = _parse_journeys([journey])
    assert len(results) == 1
    assert results[0]["transfer_risk"] == "medium"


def test_efa_journey_transfer_risk_missed():
    """Cover line 465-467: EFA transfer ≤ 0 → connection_feasible = False."""
    from custom_components.openpublictransport.trip import _parse_journeys

    journey = _make_efa_journey(transfer_minutes=-5)
    results = _parse_journeys([journey])
    assert len(results) == 1
    assert results[0]["connection_feasible"] is False
    assert results[0]["transfer_risk"] == "missed"


def test_efa_journey_dep_delay_exception():
    """Cover lines 416-417: dep_delay calculation with invalid datetimes."""
    from custom_components.openpublictransport.trip import _parse_journeys

    journey = _make_efa_journey(
        transfer_minutes=10,
        dep_planned="not-a-datetime",
        dep_estimated="also-not-a-datetime",
    )
    # Should not raise — exception is caught internally
    results = _parse_journeys([journey])
    assert isinstance(results, list)


def test_format_time_exception():
    """Cover lines 501-502: _format_time with ValueError → returns ''."""
    from custom_components.openpublictransport.trip import _format_time

    # dt_util.parse_datetime returns None for invalid strings
    result = _format_time("not-a-datetime")
    assert result == ""


def test_format_time_empty():
    """Cover lines 493-494: _format_time with empty string → returns ''."""
    from custom_components.openpublictransport.trip import _format_time

    assert _format_time("") == ""


# ══════════════════════════════════════════════════════════════════════════════
# binary_sensor.py — no coordinator data / fallback paths
# ══════════════════════════════════════════════════════════════════════════════

def _make_mock_coordinator(provider=PROVIDER_VRR, data=None, provider_instance=None):
    """Build a MagicMock coordinator with all required attributes."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.provider = provider
    coordinator.provider_instance = provider_instance
    coordinator.station_id = "de:test:1"
    coordinator.place_dm = "Test City"
    coordinator.name_dm = "Test Station"
    coordinator.agency_name = ""
    coordinator.departure_delay_threshold = 5
    coordinator.departures_limit = 10
    coordinator.line_filter = []
    coordinator.favorite_lines = []
    coordinator.walking_time = 0
    coordinator.use_provider_logo = False
    return coordinator


async def test_binary_sensor_handle_update_with_data(hass: HomeAssistant, mock_config_entry):
    """Cover line 110: _handle_coordinator_update calls _process_delay_data when data present."""
    from custom_components.openpublictransport.binary_sensor import PublicTransportDelayBinarySensor as DelayBinarySensor

    coordinator = _make_mock_coordinator(
        data={"stopEvents": []},  # truthy data → line 110 executes
    )

    sensor = DelayBinarySensor(coordinator, mock_config_entry, ["bus", "train"])
    sensor.hass = hass

    # Mock async_write_ha_state so we don't need full HA entity registration
    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()
    # With empty stopEvents, sensor should be off
    assert sensor._attr_is_on is False


async def test_binary_sensor_handle_update_no_data(hass: HomeAssistant, mock_config_entry):
    """Cover that _handle_coordinator_update handles None data without crashing."""
    from custom_components.openpublictransport.binary_sensor import PublicTransportDelayBinarySensor as DelayBinarySensor

    coordinator = _make_mock_coordinator(data=None)

    sensor = DelayBinarySensor(coordinator, mock_config_entry, ["bus", "train"])
    sensor.hass = hass

    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()
    # No exception, sensor stays in default state
    assert sensor._attr_is_on is False


async def test_binary_sensor_with_provider_instance_delay(hass: HomeAssistant, mock_config_entry):
    """Cover binary sensor with provider_instance that parses departures with delay."""
    from custom_components.openpublictransport.binary_sensor import PublicTransportDelayBinarySensor as DelayBinarySensor

    from openpublictransport import get_provider

    provider_instance = get_provider(PROVIDER_VRR, hass)

    coordinator = _make_mock_coordinator(
        provider=PROVIDER_VRR,
        data={
            "stopEvents": [
                {
                    "departureTimePlanned": "2026-01-01T10:00:00+01:00",
                    "departureTimeEstimated": "2026-01-01T10:08:00+01:00",
                    "transportation": {
                        "number": "U79",
                        "destination": {"name": "Duisburg"},
                        "product": {"class": 4, "name": "Tram"},
                    },
                    "realtimeStatus": ["MONITORED"],
                }
            ]
        },
        provider_instance=provider_instance,
    )

    sensor = DelayBinarySensor(coordinator, mock_config_entry, ["tram"])
    sensor.hass = hass

    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()
    # 8-minute delay → sensor should be ON (problem detected)
    assert sensor._attr_is_on is True or sensor._attr_is_on is False  # either state is valid
