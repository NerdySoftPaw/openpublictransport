"""Integration wiring for the German regional providers added in 2026.10.0."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.const import CONF_PROVIDER, DOMAIN, PROVIDERS
from custom_components.openpublictransport.trip import supports_trip_planning

NEW_PROVIDERS = ["vmv", "gvh", "nahsh", "insa", "vmt", "saarvv"]


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
def test_provider_is_known(provider):
    assert provider in PROVIDERS


async def test_providers_are_offered_in_the_config_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    field = next(f for f in result["data_schema"].schema if str(f) == CONF_PROVIDER)
    options = {o["value"] for o in result["data_schema"].schema[field].config["options"]}
    assert set(NEW_PROVIDERS) <= options


@pytest.mark.parametrize("provider, can_plan", [
    ("vmv", True), ("gvh", True), ("nahsh", False), ("insa", False), ("vmt", False), ("saarvv", False),
])
def test_trip_planning_capability(provider, can_plan):
    assert supports_trip_planning(provider) is can_plan


@pytest.mark.parametrize("provider, title", [
    ("nahsh", "NAH.SH"), ("saarvv", "saarVV"), ("irishrail_ie", "Irish Rail"), ("avv_augsburg", "AVV"),
    ("vrr", "VRR"), ("unknown_provider", "UNKNOWN_PROVIDER"),
])
def test_entry_titles_use_the_display_name(provider, title):
    from custom_components.openpublictransport.config_flow import _provider_short_name

    assert _provider_short_name(provider) == title
