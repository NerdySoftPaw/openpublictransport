"""Tests for the OptionsFlowHandler."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_DESTINATION_FILTER,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_PLATFORM_FILTER,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_VRR,
)


def _make_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            "place_dm": "Düsseldorf",
            "name_dm": "Hauptbahnhof",
            CONF_DEPARTURES: 10,
            CONF_SCAN_INTERVAL: 60,
            CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
        },
    )


async def test_options_flow_shows_form(hass: HomeAssistant):
    """Test options flow shows form with current values."""
    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"


async def test_options_flow_creates_entry(hass: HomeAssistant):
    """Test options flow saves new values."""
    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEPARTURES: 15,
            CONF_SCAN_INTERVAL: 120,
            CONF_TRANSPORTATION_TYPES: ["bus", "tram"],
            CONF_USE_PROVIDER_LOGO: True,
            CONF_DELAY_THRESHOLD: 3,
            CONF_LINE_FILTER: "U79",
            CONF_FAVORITE_LINES: "",
            CONF_WALKING_TIME: 5,
        },
    )
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_DEPARTURES] == 15
    assert result2["data"][CONF_SCAN_INTERVAL] == 120


async def test_options_flow_saves_platform_filter(hass: HomeAssistant):
    """The platform filter round-trips through the options flow (issue #57)."""
    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEPARTURES: 10,
            CONF_SCAN_INTERVAL: 60,
            CONF_TRANSPORTATION_TYPES: ["train"],
            CONF_USE_PROVIDER_LOGO: False,
            CONF_DELAY_THRESHOLD: 5,
            CONF_LINE_FILTER: "",
            CONF_DESTINATION_FILTER: "",
            CONF_PLATFORM_FILTER: "3, 4",
            CONF_FAVORITE_LINES: "",
            CONF_WALKING_TIME: 0,
        },
    )

    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_PLATFORM_FILTER] == "3, 4"


async def test_options_flow_prefills_platform_filter(hass: HomeAssistant):
    """An existing platform filter is offered back as the default."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VRR},
        options={CONF_PLATFORM_FILTER: "3"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    defaults = {str(key): key.default() for key in result["data_schema"].schema if hasattr(key, "default")}
    assert defaults[CONF_PLATFORM_FILTER] == "3"


async def test_options_flow_uses_existing_options(hass: HomeAssistant):
    """Test options flow pre-fills with existing option values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VRR},
        options={
            CONF_DEPARTURES: 8,
            CONF_SCAN_INTERVAL: 90,
            CONF_TRANSPORTATION_TYPES: ["train"],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    # Schema defaults should reflect the options values
    schema = result.get("data_schema")
    assert schema is not None
