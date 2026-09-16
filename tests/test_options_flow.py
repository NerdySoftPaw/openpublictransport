"""Tests for the OptionsFlowHandler."""

from unittest.mock import AsyncMock, patch

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


# ── options flow on a Trip Planner entry (issue #87) ──────────────────────────

def _make_trip_entry():
    """A Trip Planner entry as the config flow creates it."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Dortmund Aplerbeck → Dortmund Reinoldikirche",
        data={
            "is_trip": True,
            "trip_provider": PROVIDER_VRR,
            "trip_origin": "Aplerbeck",
            "trip_origin_city": "Dortmund",
            "trip_destination": "Reinoldikirche",
            "trip_destination_city": "Dortmund",
            CONF_SCAN_INTERVAL: 120,
        },
    )


def _journey(departure, *legs):
    return {
        "departure": departure,
        "arrival": "18:00",
        "duration_minutes": 25,
        "transfers": len(legs) - 1,
        "departure_timestamp": None,
        "legs": [{"line": line, "product": product, "transport_type": t} for line, product, t in legs],
    }


TRIP_ENTITY_ID = "sensor.aplerbeck_dortmund_reinoldikirche_dortmund"

# One connection on the wanted lines, one that sneaks in a bus — the shape of the
# board the reporter saw.
TRIP_BOARD = [
    _journey("17:30", ("U47", "U-Bahn", "subway"), ("U43", "U-Bahn", "subway")),
    _journey("17:40", ("425", "Bus", "bus"), ("U42", "U-Bahn", "subway")),
]


async def _setup_trip_entry(hass, entry):
    """Set the entry up the way HA does, with the provider call mocked out."""
    entry.add_to_hass(hass)
    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=TRIP_BOARD,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry.runtime_data


async def test_options_flow_offers_the_filters_on_a_trip_entry(hass: HomeAssistant):
    """The dialog a user opens on a trip device carries both filter fields."""
    entry = _make_trip_entry()
    await _setup_trip_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    schema_keys = {str(key) for key in result["data_schema"].schema}
    assert CONF_LINE_FILTER in schema_keys
    assert CONF_TRANSPORTATION_TYPES in schema_keys


async def test_trip_filters_applied_after_submitting_the_options_dialog(hass: HomeAssistant):
    """Submitting the dialog filters the trip sensor without a restart (#87)."""
    entry = _make_trip_entry()
    coordinator = await _setup_trip_entry(hass, entry)

    # Unfiltered: the sensor shows the first connection the provider offered
    assert coordinator.data == TRIP_BOARD
    assert hass.states.get(TRIP_ENTITY_ID).state.startswith("17:30")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=TRIP_BOARD,
    ):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_DEPARTURES: 10,
                CONF_SCAN_INTERVAL: 120,
                CONF_TRANSPORTATION_TYPES: ["tram", "subway", "train"],  # Bus deselected
                CONF_USE_PROVIDER_LOGO: False,
                CONF_DELAY_THRESHOLD: 5,
                CONF_LINE_FILTER: "U43, U47",
                CONF_DESTINATION_FILTER: "",
                CONF_PLATFORM_FILTER: "",
                CONF_FAVORITE_LINES: "",
                CONF_WALKING_TIME: 0,
            },
        )
        await hass.async_block_till_done()

    assert coordinator.line_filter == {"u43", "u47"}
    assert coordinator.transport_types == {"tram", "subway", "train"}
    # The bus connection is gone; the U43/U47 one survived
    assert coordinator.data == [TRIP_BOARD[0]]
    assert hass.states.get(TRIP_ENTITY_ID).state.startswith("17:30")


async def test_trip_sensor_reports_no_connections_when_filters_exclude_everything(hass: HomeAssistant):
    """Filtering away every connection reads as "No connections", not a stale one."""
    entry = _make_trip_entry()
    coordinator = await _setup_trip_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.openpublictransport.trip_sensor.async_plan_trip",
        new_callable=AsyncMock, return_value=TRIP_BOARD,
    ):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_DEPARTURES: 10,
                CONF_SCAN_INTERVAL: 120,
                CONF_TRANSPORTATION_TYPES: ["bus", "tram", "subway", "train"],
                CONF_USE_PROVIDER_LOGO: False,
                CONF_DELAY_THRESHOLD: 5,
                CONF_LINE_FILTER: "U99",
                CONF_DESTINATION_FILTER: "",
                CONF_PLATFORM_FILTER: "",
                CONF_FAVORITE_LINES: "",
                CONF_WALKING_TIME: 0,
            },
        )
        await hass.async_block_till_done()

    assert coordinator.data == []
    assert hass.states.get(TRIP_ENTITY_ID).state == "No connections"
