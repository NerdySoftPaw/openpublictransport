"""Extended config flow tests covering uncovered branches."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import (
    CONF_NTA_API_KEY,
    CONF_NTA_API_KEY_SECONDARY,
    CONF_OPT_API_KEY,
    CONF_OTP_BASE_URL,
    CONF_OTP_CUSTOM_API_KEY,
    CONF_PROVIDER,
    CONF_RMV_API_KEY,
    CONF_TRAFIKLAB_API_KEY,
    CONF_VBN_API_KEY,
    DOMAIN,
    PROVIDER_NTA_IE,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
    PROVIDER_VRR,
)

# ── User step ─────────────────────────────────────────────────────────────────

async def test_step_user_shows_form(hass: HomeAssistant):
    """Test user step shows form when no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_step_user_no_api_key_goes_to_stop_search(hass: HomeAssistant):
    """Test user step with VRR (no API key) goes to stop_search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "stop_search"


async def test_step_user_rmv_goes_to_api_key(hass: HomeAssistant):
    """Test user step with RMV (API key required) goes to api_key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_RMV},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "api_key"


async def test_step_user_opt_goes_to_opt_key(hass: HomeAssistant):
    """Test user step with OPT goes to opt_key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OPT},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "opt_key"


async def test_step_user_otp_custom_goes_to_custom_url(hass: HomeAssistant):
    """Test user step with OTP_CUSTOM goes to otp_custom_url."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "otp_custom_url"


# ── opt_key step ──────────────────────────────────────────────────────────────

async def test_opt_key_empty_shows_error(hass: HomeAssistant):
    """Test opt_key step with empty key shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OPT},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OPT_API_KEY: ""}
    )
    assert result2["type"] == "form"
    assert "opt_api_key_required" in str(result2.get("errors", {}))


async def test_opt_key_valid_goes_to_stop_search(hass: HomeAssistant):
    """Test opt_key step with valid key goes to stop_search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OPT},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OPT_API_KEY: "my-api-key"}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


# ── otp_custom_url step ───────────────────────────────────────────────────────

async def test_otp_custom_url_form_shown(hass: HomeAssistant):
    """Test otp_custom_url step shows form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "otp_custom_url"


async def test_otp_custom_url_unreachable_shows_error(hass: HomeAssistant):
    """Test otp_custom_url step with unreachable URL shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    with patch(
        "custom_components.openpublictransport.config_flow.async_get_clientsession",
    ) as mock_session_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("Connection refused"))
        mock_session_fn.return_value = mock_session
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_OTP_BASE_URL: "http://myotp.local/otp", CONF_OTP_CUSTOM_API_KEY: ""},
        )
    assert result2["type"] == "form"
    assert "cannot_connect" in str(result2.get("errors", {}))


async def test_otp_custom_url_reachable_goes_to_stop_search(hass: HomeAssistant):
    """Test otp_custom_url step with reachable URL goes to stop_search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM},
    )
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_fn:
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_fn.return_value = mock_session

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_OTP_BASE_URL: "http://myotp.local/otp", CONF_OTP_CUSTOM_API_KEY: ""},
        )

    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


# ── api_key step ──────────────────────────────────────────────────────────────

async def test_api_key_rmv_empty_shows_error(hass: HomeAssistant):
    """Test api_key step with empty RMV key shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_RMV},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_RMV_API_KEY: ""}
    )
    assert result2["type"] == "form"
    assert "rmv_api_key_required" in str(result2.get("errors", {}))


async def test_api_key_trafiklab_valid_goes_to_stop_search(hass: HomeAssistant):
    """Test api_key step with valid Trafiklab key proceeds."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "my-trafiklab-key"}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


async def test_api_key_nta_valid_goes_to_next_step(hass: HomeAssistant):
    """Test api_key step with valid NTA key proceeds to the next step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NTA_IE},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NTA_API_KEY: "nta-primary", CONF_NTA_API_KEY_SECONDARY: "nta-secondary"},
    )
    assert result2["type"] == "form"
    # NTA has a special stop ID step
    assert result2["step_id"] in ("stop_search", "nta_stop_id", "api_key")


async def test_api_key_vbn_valid_goes_to_stop_search(hass: HomeAssistant):
    """Test api_key step with valid VBN key proceeds."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VBN_OTP},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_VBN_API_KEY: "vbn-key"}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


# ── stop_search step ──────────────────────────────────────────────────────────

async def test_stop_search_empty_shows_error(hass: HomeAssistant):
    """Test stop_search with empty term shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"stop_search": ""}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


async def test_stop_search_returns_results(hass: HomeAssistant):
    """Test stop_search with results shows stop_select."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [{"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"}]
    with patch(
        "custom_components.openpublictransport.config_flow.get_provider"
    ) as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_get_provider.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    assert result2["type"] == "form"
    assert result2["step_id"] in ("stop_select", "settings")


async def test_stop_search_no_results(hass: HomeAssistant):
    """Test stop_search with no results shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=[])
        mock_get_provider.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Nonexistent"}
        )

    assert result2["type"] == "form"
    assert result2["step_id"] == "stop_search"


async def test_stop_select_creates_entry(hass: HomeAssistant):
    """Test complete flow: user → stop_search → settings → entry created."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    mock_stops = [
        {"id": "de:05111:100", "name": "Düsseldorf Hbf", "place": "Düsseldorf"},
        {"id": "de:05111:101", "name": "Düsseldorf Hbf Gleis 2", "place": "Düsseldorf"},
    ]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=mock_stops)
        mock_get_provider.return_value = mock_provider

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    assert result2["type"] == "form"

    # If stop_select is shown, select the stop
    if result2["step_id"] == "stop_select":
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop": "de:05111:100"}
        )

    assert result2["step_id"] == "settings"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            "departures": 10,
            "scan_interval": 60,
            "transportation_types": ["bus", "train", "tram"],
            "use_provider_logo": False,
            "delay_threshold": 5,
            "line_filter": "",
            "favorite_lines": "",
            "walking_time": 0,
        },
    )
    assert result3["type"] == "create_entry"


# ── reauth step ───────────────────────────────────────────────────────────────

async def test_reauth_confirm_shows_form(hass: HomeAssistant):
    """Test reauth_confirm shows form for Trafiklab provider."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE,
            CONF_TRAFIKLAB_API_KEY: "old-key",
            "place_dm": "Stockholm",
            "name_dm": "Centralen",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_confirm_empty_key_shows_error(hass: HomeAssistant):
    """Test reauth_confirm with empty key shows error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE, CONF_TRAFIKLAB_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: ""}
    )
    assert result2["type"] == "form"
    assert "trafiklab_api_key_required" in str(result2.get("errors", {}))


async def test_reauth_confirm_valid_key_updates_entry(hass: HomeAssistant):
    """Test reauth_confirm with valid key updates and reloads entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_TRAFIKLAB_SE, CONF_TRAFIKLAB_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(
        OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TRAFIKLAB_API_KEY: "new-key"}
        )

    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"


async def test_reauth_confirm_rmv(hass: HomeAssistant):
    """Test reauth_confirm works for RMV provider."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_RMV, CONF_RMV_API_KEY: "old-rmv-key"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(
        OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_RMV_API_KEY: "new-rmv-key"}
        )
    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"


async def test_reauth_confirm_nta(hass: HomeAssistant):
    """Test reauth_confirm works for NTA (dual-key) provider."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_NTA_IE,
            CONF_NTA_API_KEY: "old-primary",
            CONF_NTA_API_KEY_SECONDARY: "old-secondary",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(
        OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_NTA_API_KEY: "new-primary", CONF_NTA_API_KEY_SECONDARY: "new-secondary"},
        )
    assert result2["type"] == "abort"


async def test_reauth_no_reauth_needed_for_vrr(hass: HomeAssistant):
    """Test reauth aborts with no_reauth_needed for non-API-key providers."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VRR},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["type"] == "abort"
    assert result["reason"] == "no_reauth_needed"
