"""Regression tests for the issues fixed in 2026.10.2 (#92, #93, #98)."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DESTINATION_FILTER,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_PLATFORM_FILTER,
    CONF_PROVIDER,
    DOMAIN,
)
from custom_components.openpublictransport.filters import matches_filter, split_filter
from openpublictransport.parsers import normalize_platform

# -- #93: exclude with "!" ---------------------------------------------------------


def test_split_filter_separates_include_and_exclude():
    assert split_filter("U43, !U47 ,", str.lower) == (["u43"], ["u47"])
    assert split_filter("!Hauptbahnhof", str.lower) == ([], ["hauptbahnhof"])
    assert split_filter("", str.lower) == ([], [])
    assert split_filter("!, ! ", str.lower) == ([], [])


@pytest.mark.parametrize("destination, shown", [
    ("Düsseldorf Hauptbahnhof", False),
    ("Wuppertal Hbf", True),
])
def test_destination_exclude(destination, shown):
    include, exclude = split_filter("!Hauptbahnhof", str.lower)
    assert matches_filter(destination.lower(), include, exclude, substring=True) is shown


def test_include_and_exclude_combined():
    include, exclude = split_filter("Wuppertal, !Wuppertal-Vohwinkel", str.lower)
    assert matches_filter("wuppertal hbf", include, exclude, substring=True)
    assert not matches_filter("wuppertal-vohwinkel", include, exclude, substring=True)
    assert not matches_filter("essen hbf", include, exclude, substring=True)


def test_platform_exclude_uses_normalized_tracks():
    include, exclude = split_filter("!Gleis 3", normalize_platform)
    assert not matches_filter(normalize_platform("3"), include, exclude, substring=False)
    assert matches_filter(normalize_platform("4"), include, exclude, substring=False)


# -- #98: clearing a filter in the options removes it ---------------------------------


@pytest.mark.parametrize("key", [CONF_LINE_FILTER, CONF_DESTINATION_FILTER, CONF_PLATFORM_FILTER, CONF_FAVORITE_LINES])
async def test_clearing_a_text_filter_in_options_removes_it(hass: HomeAssistant, key):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: "vagfr", "station_id": "de:08311:1", key: "37"},
        options={key: "37"},
    )
    entry.add_to_hass(hass)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    field = next(f for f in form["data_schema"].schema if str(f) == key)
    assert field.description["suggested_value"] == "37"

    # The frontend omits a field the user emptied.
    await hass.config_entries.options.async_configure(form["flow_id"], user_input={})

    assert entry.options[key] == ""


# -- #101: CTA takes two optional keys, at least one required --------------------------


async def test_cta_key_step_accepts_either_key(hass: HomeAssistant):
    from custom_components.openpublictransport.const import CONF_API_KEY, CONF_API_KEY_SECONDARY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"entry_type": "departures", CONF_PROVIDER: "cta_us"}
    )
    assert result["step_id"] == "api_key"
    assert {str(f) for f in result["data_schema"].schema} == {CONF_API_KEY, CONF_API_KEY_SECONDARY}

    none = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={})
    assert none["errors"] == {"base": "api_key_required"}

    train_only = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY_SECONDARY: "train-key"}
    )
    assert train_only["step_id"] == "stop_search"


async def test_cta_second_key_reaches_the_coordinator(hass: HomeAssistant):
    from unittest.mock import AsyncMock, patch

    from custom_components.openpublictransport import async_setup_entry
    from custom_components.openpublictransport.const import CONF_API_KEY, CONF_API_KEY_SECONDARY

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: "cta_us", CONF_API_KEY: "bus", CONF_API_KEY_SECONDARY: "train", "station_id": "train:40380"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock):
        assert await async_setup_entry(hass, entry)
    assert (entry.runtime_data.api_key, entry.runtime_data.api_key_secondary) == ("bus", "train")


# -- unload only the platforms an entry type loaded ------------------------------------


@pytest.mark.parametrize("data, expected", [
    ({"is_multi_stop": True}, ["sensor", "camera"]),
    ({"is_trip": True}, ["sensor"]),
    ({CONF_PROVIDER: "vrr"}, ["sensor", "binary_sensor", "calendar", "event", "camera"]),
])
async def test_unload_matches_the_loaded_platforms(hass: HomeAssistant, data, expected):
    from unittest.mock import AsyncMock, patch

    from custom_components.openpublictransport import async_unload_entry

    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    with patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms", new_callable=AsyncMock) as unload:
        unload.return_value = True
        assert await async_unload_entry(hass, entry)
    assert unload.call_args.args[1] == expected
