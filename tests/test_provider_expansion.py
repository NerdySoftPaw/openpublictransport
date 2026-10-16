"""Integration wiring for the provider expansion and the generic API key path."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import (
    CONF_API_KEY,
    CONF_PROVIDER,
    DOMAIN,
    GENERIC_API_KEY_PROVIDERS,
    PROVIDERS,
)
from custom_components.openpublictransport.trip import supports_trip_planning

NEW = [
    "vbn_hafas", "nvv", "vos", "vsn", "vao_at", "trimet_us", "irail_be", "sl_se", "ttc_ca",
    "hongkong", "wienerlinien_at", "tfl_uk", "tfnsw_au", "digitransit_fi", "golemio_cz",
]


@pytest.mark.parametrize("provider", NEW)
def test_provider_is_known(provider):
    assert provider in PROVIDERS


async def test_new_providers_in_the_dropdown(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    field = next(f for f in result["data_schema"].schema if str(f) == CONF_PROVIDER)
    options = result["data_schema"].schema[field].config["options"]
    assert set(NEW) <= {o["value"] for o in options}
    labels = [o["label"].casefold() for o in options]
    assert labels == sorted(labels)


@pytest.mark.parametrize("provider", ["vbn_hafas", "nvv", "vos", "vsn", "vao_at"])
def test_new_mgate_providers_plan_trips(provider):
    assert supports_trip_planning(provider)


@pytest.mark.parametrize("provider", ["irail_be", "sl_se", "ttc_ca", "hongkong", "wienerlinien_at", "tfl_uk"])
def test_other_new_providers_are_departure_monitors(provider):
    assert not supports_trip_planning(provider)


def test_generic_key_providers_require_a_key():
    from openpublictransport.providers import get_provider_class

    for provider in GENERIC_API_KEY_PROVIDERS:
        assert get_provider_class(provider)(None).requires_api_key, provider


@pytest.mark.parametrize("provider", sorted(GENERIC_API_KEY_PROVIDERS))
async def test_generic_api_key_step(hass: HomeAssistant, provider):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"entry_type": "departures", CONF_PROVIDER: provider}
    )
    assert result["step_id"] == "api_key"
    assert [str(f) for f in result["data_schema"].schema] == [CONF_API_KEY]
    assert result["description_placeholders"]["info"] == GENERIC_API_KEY_PROVIDERS[provider]

    empty = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_API_KEY: "  "})
    assert empty["errors"] == {CONF_API_KEY: "api_key_required"}

    ok = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_API_KEY: "secret"})
    assert ok["step_id"] == "stop_search"


async def test_generic_api_key_is_reused_from_an_existing_entry(hass: HomeAssistant):
    MockConfigEntry(domain=DOMAIN, data={CONF_PROVIDER: "golemio_cz", CONF_API_KEY: "existing"}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"entry_type": "departures", CONF_PROVIDER: "golemio_cz"}
    )
    assert result["step_id"] == "stop_search"


async def test_generic_api_key_reauth(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PROVIDER: "tfnsw_au", CONF_API_KEY: "old"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=entry.data
    )
    assert [str(f) for f in result["data_schema"].schema] == [CONF_API_KEY]
    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        done = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_API_KEY: "new"})
    assert done["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "new"


async def test_generic_api_key_reaches_the_coordinator(hass: HomeAssistant):
    from custom_components.openpublictransport import async_setup_entry

    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_PROVIDER: "digitransit_fi", CONF_API_KEY: "sub-key", "station_id": "HSL:1000001"}
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
        assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.api_key == "sub-key"


def test_generic_api_key_is_redacted_in_diagnostics():
    from custom_components.openpublictransport.diagnostics import TO_REDACT

    assert CONF_API_KEY in TO_REDACT
