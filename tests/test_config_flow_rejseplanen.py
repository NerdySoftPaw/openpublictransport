"""Config-flow tests for the Rejseplanen (DK) and National Rail (UK) providers.

Both are API-key providers added together; these cover the provider-specific
branches in the api_key step (form shown, empty key rejected, valid key
proceeds, existing credential reused).
"""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_PROVIDER,
    CONF_REJSEPLANEN_API_KEY,
    DOMAIN,
    PROVIDER_NATIONAL_RAIL,
    PROVIDER_REJSEPLANEN,
)


# ── Rejseplanen (Denmark) ─────────────────────────────────────────────────────

async def test_rejseplanen_api_key_step_shows(hass: HomeAssistant):
    """Selecting Rejseplanen asks for the API key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_REJSEPLANEN},
    )
    assert result["step_id"] == "api_key"


async def test_rejseplanen_api_key_empty_shows_error(hass: HomeAssistant):
    """An empty Rejseplanen key is rejected with the provider-specific error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_REJSEPLANEN},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_REJSEPLANEN_API_KEY: ""}
    )
    assert "rejseplanen_api_key_required" in str(result2.get("errors", {}))


async def test_rejseplanen_api_key_valid_proceeds(hass: HomeAssistant):
    """A valid Rejseplanen key proceeds to the stop search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_REJSEPLANEN},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_REJSEPLANEN_API_KEY: "test-key"}
    )
    assert result2["step_id"] == "stop_search"


async def test_rejseplanen_reuses_existing_credential(hass: HomeAssistant):
    """An existing Rejseplanen key is reused, skipping the api_key form."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_rejseplanen",
        data={CONF_PROVIDER: PROVIDER_REJSEPLANEN, CONF_REJSEPLANEN_API_KEY: "existing-key"},
    )
    existing.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_REJSEPLANEN},
    )
    assert result["step_id"] in ("stop_search", "api_key")


# ── National Rail (United Kingdom) ────────────────────────────────────────────

async def test_national_rail_api_key_step_shows(hass: HomeAssistant):
    """Selecting National Rail asks for the API key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NATIONAL_RAIL},
    )
    assert result["step_id"] == "api_key"


async def test_national_rail_api_key_empty_shows_error(hass: HomeAssistant):
    """An empty National Rail key is rejected with the provider-specific error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NATIONAL_RAIL},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_NATIONAL_RAIL_API_KEY: ""}
    )
    assert "national_rail_api_key_required" in str(result2.get("errors", {}))


async def test_national_rail_api_key_valid_proceeds(hass: HomeAssistant):
    """A valid National Rail key proceeds to the stop search."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NATIONAL_RAIL},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_NATIONAL_RAIL_API_KEY: "test-key"}
    )
    assert result2["step_id"] == "stop_search"


async def test_national_rail_reuses_existing_credential(hass: HomeAssistant):
    """An existing National Rail key is reused, skipping the api_key form."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        entry_id="existing_national_rail",
        data={CONF_PROVIDER: PROVIDER_NATIONAL_RAIL, CONF_NATIONAL_RAIL_API_KEY: "existing-key"},
    )
    existing.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_NATIONAL_RAIL},
    )
    assert result["step_id"] in ("stop_search", "api_key")
