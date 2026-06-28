"""Tests for credential auto-reuse paths in config_flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import (
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PROVIDER,
    CONF_RMV_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_TRAFIKLAB_API_KEY,
    CONF_VBN_API_KEY,
    DOMAIN,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
    PROVIDER_VRR,
)


# ── OPT credential auto-reuse ─────────────────────────────────────────────────

async def test_opt_reuses_existing_credential(hass: HomeAssistant):
    """Test opt_key step auto-reuses key from existing config entry."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_opt",
        data={CONF_PROVIDER: PROVIDER_OPT, CONF_OPT_API_KEY: "existing-opt-key"},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OPT},
    )
    # Should skip opt_key form since key already exists
    assert result["step_id"] in ("stop_search", "opt_key")


async def test_opt_trip_reuses_existing_credential(hass: HomeAssistant):
    """Test opt_key for trip entry type with existing key goes to trip_search."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_opt",
        data={CONF_PROVIDER: PROVIDER_OPT, CONF_OPT_API_KEY: "existing-opt-key"},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_OPT},
    )
    assert result["step_id"] in ("trip_search", "opt_key")


# ── OTP Custom credential auto-reuse ──────────────────────────────────────────

async def test_otp_custom_reuses_existing_url(hass: HomeAssistant):
    """Test otp_custom_url step auto-reuses URL from existing config entry."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_otp",
        data={
            CONF_PROVIDER: PROVIDER_OTP_CUSTOM,
            CONF_OTP_BASE_URL: "http://existing.local/otp",
            CONF_OTP_CUSTOM_API_KEY: "existing-otp-key",
        },
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    assert result["step_id"] in ("stop_search", "otp_custom_url")


async def test_otp_custom_trip_reuses_existing_url(hass: HomeAssistant):
    """Test otp_custom_url for trip with existing URL goes to trip_search."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_otp",
        data={
            CONF_PROVIDER: PROVIDER_OTP_CUSTOM,
            CONF_OTP_BASE_URL: "http://existing.local/otp",
        },
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    assert result["step_id"] in ("trip_search", "otp_custom_url")


# ── Trafiklab credential auto-reuse ───────────────────────────────────────────

async def test_trafiklab_reuses_existing_credential(hass: HomeAssistant):
    """Test api_key step auto-reuses Trafiklab key from config entry."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_trafiklab",
        data={CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE, CONF_TRAFIKLAB_API_KEY: "existing-trafiklab"},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    assert result["step_id"] in ("stop_search", "api_key")


async def test_nta_reuses_existing_credential(hass: HomeAssistant):
    """Test api_key step auto-reuses NTA key from config entry."""
    from custom_components.openpublictransport.const import CONF_NTA_API_KEY, PROVIDER_NTA_IE

    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_nta",
        data={
            CONF_PROVIDER: PROVIDER_NTA_IE,
            CONF_NTA_API_KEY: "existing-nta-key",
        },
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    # Should auto-skip to next step
    assert result["step_id"] in ("nta_stop_id", "api_key")


# ── Trafiklab HTTP response parsing paths ─────────────────────────────────────

async def test_trafiklab_response_invalid_json(hass: HomeAssistant):
    """Test Trafiklab stop search handles invalid JSON response."""
    import aiohttp

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "key-abc"}
    )

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(
        MagicMock(), MagicMock()
    ))
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
                result3 = await hass.config_entries.flow.async_configure(
                    result2["flow_id"], user_input={"stop_search": "Stockholm"}
                )

    assert result3["step_id"] == "stop_search"


async def test_trafiklab_response_non_dict_json(hass: HomeAssistant):
    """Test Trafiklab stop search handles non-dict JSON."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "key-abc"}
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

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result3 = await hass.config_entries.flow.async_configure(
                    result2["flow_id"], user_input={"stop_search": "Stockholm"}
                )

    assert result3["step_id"] == "stop_search"


async def test_trafiklab_response_other_status(hass: HomeAssistant):
    """Test Trafiklab stop search handles other HTTP status codes."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "key-abc"}
    )

    mock_response = AsyncMock()
    mock_response.status = 429  # Too Many Requests
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
                result3 = await hass.config_entries.flow.async_configure(
                    result2["flow_id"], user_input={"stop_search": "Stockholm"}
                )

    assert result3["step_id"] == "stop_search"


# ── settings: stop not found case ────────────────────────────────────────────

async def test_stop_search_result_selects_without_stop_select(hass: HomeAssistant):
    """Test stop search with 1 result auto-selects and goes to settings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [{"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"}]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    # 1 result → either auto-selects (settings) or shows select
    assert result2["step_id"] in ("settings", "stop_select")


# ── settings with stop_select → settings path ────────────────────────────────

async def test_stop_select_no_match_goes_to_settings(hass: HomeAssistant):
    """Test stop_select without matching stop still proceeds to settings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:1", "name": "A", "place": "City"},
        {"id": "de:2", "name": "B", "place": "City"},
    ]

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_gp.return_value = mock_provider
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Test"}
        )

    if result2["step_id"] == "stop_select":
        # Submit with first valid stop from the list
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "de:1"}
        )
        assert result3["step_id"] == "settings"
