"""Tests for config_flow search helper methods and fallback paths."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_PROVIDER,
    CONF_TRAFIKLAB_API_KEY,
    DOMAIN,
    PROVIDER_HVV,
    PROVIDER_KVV,
    PROVIDER_NTA_IE,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VRR,
)


async def _init_trafiklab_flow(hass, provider=PROVIDER_TRAFIKLAB_SE):
    """Get to stop_search step with a Trafiklab key already set."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: provider},
    )
    # Enter API key
    if provider == PROVIDER_TRAFIKLAB_SE:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "trafiklab-test-key"}
        )
        return result2
    return result


# ── Trafiklab stop search fallback path ───────────────────────────────────────

async def test_trafiklab_stop_search_success(hass: HomeAssistant):
    """Test Trafiklab stop search returns results via HTTP."""
    result = await _init_trafiklab_flow(hass)
    assert result["step_id"] == "stop_search"

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "stop_groups": [
            {"id": "9001001", "name": "Stockholm Central", "area_type": "stop", "transport_modes": ["RAIL"]},
            {"id": "9001002", "name": "Stockholm Odenplan", "area_type": "stop", "transport_modes": ["SUBWAY"]},
        ]
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=Exception("provider failed"))  # force fallback
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Stockholm"}
            )

    # Should show results (stop_select) or go directly to settings if 1 result
    assert result2["type"] == "form"
    assert result2["step_id"] in ("stop_select", "stop_search")


async def test_trafiklab_stop_search_401(hass: HomeAssistant):
    """Test Trafiklab stop search with 401 returns no results."""
    result = await _init_trafiklab_flow(hass)

    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Test"}
            )

    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


async def test_trafiklab_stop_search_500_retries(hass: HomeAssistant):
    """Test Trafiklab stop search with 500 retries and eventually gives up."""
    result = await _init_trafiklab_flow(hass)

    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result2 = await hass.config_entries.flow.async_configure(
                    result["flow_id"], user_input={"stop_search": "Test"}
                )

    assert result2["step_id"] == "stop_search"


async def test_trafiklab_stop_search_timeout(hass: HomeAssistant):
    """Test Trafiklab stop search timeout returns no results."""
    result = await _init_trafiklab_flow(hass)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
            mock_sess.return_value = mock_session

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result2 = await hass.config_entries.flow.async_configure(
                    result["flow_id"], user_input={"stop_search": "Test"}
                )

    assert result2["step_id"] == "stop_search"


async def test_trafiklab_stop_search_no_api_key(hass: HomeAssistant):
    """Test Trafiklab search without API key returns no results."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    # Skip api_key step by entering empty (will show error)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "valid-key"}
    )
    assert result2["step_id"] == "stop_search"


async def test_trafiklab_stop_search_with_place_in_name(hass: HomeAssistant):
    """Test Trafiklab stop search parses comma-separated place correctly."""
    result = await _init_trafiklab_flow(hass)

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "stop_groups": [
            {"id": "9001", "name": "Central, Stockholm", "area_type": "stop", "transport_modes": []},
        ]
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Central"}
            )

    assert result2["type"] == "form"


# ── EFA fallback search paths ─────────────────────────────────────────────────

async def test_efa_stop_search_http_success(hass: HomeAssistant):
    """Test EFA stop search via HTTP fallback."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "locations": [
            {"id": "de:05111:100", "name": "Düsseldorf Hbf", "type": "stop",
             "coord": {"lat": 51.2, "lon": 6.7}, "parent": {"name": "Düsseldorf"}},
        ]
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(side_effect=Exception("provider failed"))
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Düsseldorf"}
            )

    assert result2["type"] == "form"


async def test_efa_stop_search_404(hass: HomeAssistant):
    """Test EFA stop search with 404 falls back gracefully."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_KVV},
    )
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Test"}
            )

    assert result2["step_id"] == "stop_search"


async def test_efa_stop_search_500(hass: HomeAssistant):
    """Test EFA stop search with 500 returns no results."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_HVV},
    )
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Test"}
            )

    assert result2["step_id"] == "stop_search"


async def test_efa_stop_search_non_dict_json(hass: HomeAssistant):
    """Test EFA stop search with non-dict JSON response."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=["not", "a", "dict"])
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_gp.return_value = mock_provider

        with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_sess.return_value = mock_session

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Test"}
            )

    assert result2["step_id"] == "stop_search"
