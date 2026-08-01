"""Tests for adding the same station twice with different filters (issue #55).

The wizard used to abort with `already_configured` on the second entry, because
the unique ID was just `f"{provider}_{stop_id}"`. A filtered entry now gets a
stable discriminator derived from its filters — and entries created before this
must keep their exact previous unique ID, since the entity registry is keyed on it.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.filters import filter_discriminator, filter_label
from custom_components.openpublictransport.const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_DESTINATION_FILTER,
    CONF_ENTRY_LABEL,
    CONF_ENTRY_SUFFIX,
    CONF_FAVORITE_LINES,
    CONF_LINE_FILTER,
    CONF_PLATFORM_FILTER,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_VRR,
)
from custom_components.openpublictransport.sensor import station_device_name, station_entity_key

STOP_ID = "de:05111:100"
STOPS = [{"id": STOP_ID, "name": "Düsseldorf Hbf", "place": "Düsseldorf"}]


def _settings(**overrides) -> dict:
    base = {
        CONF_DEPARTURES: 10,
        CONF_SCAN_INTERVAL: 60,
        CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram"],
        CONF_USE_PROVIDER_LOGO: False,
        CONF_DELAY_THRESHOLD: 5,
        CONF_LINE_FILTER: "",
        CONF_DESTINATION_FILTER: "",
        CONF_PLATFORM_FILTER: "",
        CONF_FAVORITE_LINES: "",
        CONF_WALKING_TIME: 0,
    }
    base.update(overrides)
    return base


async def _run_flow(hass: HomeAssistant, settings: dict):
    """Drive the departures flow from provider selection to the settings step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        provider = AsyncMock()
        provider.search_stops = AsyncMock(return_value=STOPS)
        mock_gp.return_value = provider
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Düsseldorf"}
        )

    if result["step_id"] == "stop_select":
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"stop": STOP_ID})

    assert result["step_id"] == "settings"
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input=settings)


# ── the reported scenario ─────────────────────────────────────────────────────


async def test_same_station_twice_with_different_destination_filters(hass: HomeAssistant):
    """Outbound and inbound badges for one S-Bahn station — the issue's use case."""
    outbound = await _run_flow(hass, _settings(**{CONF_DESTINATION_FILTER: "Duisburg"}))
    assert outbound["type"] == "create_entry"

    inbound = await _run_flow(hass, _settings(**{CONF_DESTINATION_FILTER: "Köln"}))
    assert inbound["type"] == "create_entry"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert entries[0].unique_id != entries[1].unique_id
    # Both are still recognisably the same station
    for entry in entries:
        assert entry.unique_id.startswith(f"{PROVIDER_VRR}_{STOP_ID}")


async def test_titles_and_device_names_distinguish_the_two_entries(hass: HomeAssistant):
    """A filtered entry says what it is filtered to."""
    result = await _run_flow(hass, _settings(**{CONF_LINE_FILTER: "S1", CONF_DESTINATION_FILTER: "Duisburg"}))

    assert result["title"] == "VRR Düsseldorf - Düsseldorf Hbf (S1 → Duisburg)"
    assert result["data"][CONF_ENTRY_LABEL] == "S1 → Duisburg"


async def test_same_station_twice_with_identical_filters_still_aborts(hass: HomeAssistant):
    """Two truly identical entries are still a duplicate."""
    first = await _run_flow(hass, _settings(**{CONF_DESTINATION_FILTER: "Duisburg"}))
    assert first["type"] == "create_entry"

    second = await _run_flow(hass, _settings(**{CONF_DESTINATION_FILTER: "Duisburg"}))
    assert second["type"] == "abort"
    assert second["reason"] == "already_configured"


async def test_filter_order_and_case_do_not_create_a_new_entry(hass: HomeAssistant):
    """"S1, S2" and "s2 , s1" are the same configuration."""
    first = await _run_flow(hass, _settings(**{CONF_LINE_FILTER: "S1, S2"}))
    assert first["type"] == "create_entry"

    second = await _run_flow(hass, _settings(**{CONF_LINE_FILTER: "s2 , s1"}))
    assert second["type"] == "abort"
    assert second["reason"] == "already_configured"


async def test_unfiltered_duplicate_still_aborts(hass: HomeAssistant):
    """Without filters there is nothing to tell the entries apart."""
    first = await _run_flow(hass, _settings())
    assert first["type"] == "create_entry"

    second = await _run_flow(hass, _settings())
    assert second["type"] == "abort"
    assert second["reason"] == "already_configured"


# ── backwards compatibility ───────────────────────────────────────────────────


async def test_unfiltered_entry_keeps_the_legacy_unique_id(hass: HomeAssistant):
    """No filters → no discriminator, so the ID format is untouched."""
    result = await _run_flow(hass, _settings())

    assert result["type"] == "create_entry"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == f"{PROVIDER_VRR}_{STOP_ID}"
    assert CONF_ENTRY_SUFFIX not in result["data"]
    assert CONF_ENTRY_LABEL not in result["data"]


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.provider = PROVIDER_VRR
    coordinator.station_id = STOP_ID
    coordinator.place_dm = "Düsseldorf"
    coordinator.name_dm = "Hauptbahnhof"
    coordinator.agency_name = "Rheinbahn"
    return coordinator


def _entry(hass: HomeAssistant, **extra) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_VRR, CONF_STATION_ID: STOP_ID, **extra},
    )
    entry.add_to_hass(hass)
    return entry


async def test_entity_key_unchanged_for_pre_existing_entries(hass: HomeAssistant):
    """An entry without a discriminator gets the byte-identical legacy key.

    CLAUDE.md pins f"{provider}_{station_id}" as stable — existing users'
    entity registries depend on it.
    """
    entry = _entry(hass)

    assert station_entity_key(_coordinator(), entry) == f"{PROVIDER_VRR}_{STOP_ID}"
    assert station_device_name(_coordinator(), entry) == "Rheinbahn - Hauptbahnhof"


async def test_entity_key_without_a_config_entry(hass: HomeAssistant):
    """Callers that pass no entry still get the legacy key."""
    assert station_entity_key(_coordinator()) == f"{PROVIDER_VRR}_{STOP_ID}"


async def test_entity_key_falls_back_to_place_and_name(hass: HomeAssistant):
    """Providers with no stop ID key on place+name, as before."""
    coordinator = _coordinator()
    coordinator.station_id = None

    assert station_entity_key(coordinator, _entry(hass)) == f"{PROVIDER_VRR}_düsseldorf_hauptbahnhof"


async def test_entity_key_appends_the_discriminator(hass: HomeAssistant):
    """A filtered entry gets its own key, so the two do not collide."""
    entry = _entry(
        hass,
        **{CONF_DESTINATION_FILTER: "Duisburg", CONF_ENTRY_SUFFIX: "abc12345", CONF_ENTRY_LABEL: "→ Duisburg"},
    )

    assert station_entity_key(_coordinator(), entry) == f"{PROVIDER_VRR}_{STOP_ID}_abc12345"
    assert station_device_name(_coordinator(), entry) == "Rheinbahn - Hauptbahnhof (→ Duisburg)"


# ── the device name tracks the filters, the unique ID does not ────────────────


async def test_editing_filters_renames_the_device_but_not_the_entities(hass: HomeAssistant):
    """Changing a filter under Options must update the label, not the IDs.

    The device would otherwise keep advertising the filter it was created
    with — "(→ Duisburg)" on an entry that now filters for Köln. Renaming a
    device is harmless because entity IDs are assigned once at creation;
    moving the unique-ID suffix would rename every entity of the entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            CONF_STATION_ID: STOP_ID,
            CONF_DESTINATION_FILTER: "Duisburg",
            CONF_ENTRY_SUFFIX: "abc12345",
            CONF_ENTRY_LABEL: "→ Duisburg",
        },
        options={CONF_DESTINATION_FILTER: "Köln"},
    )
    entry.add_to_hass(hass)

    assert station_device_name(_coordinator(), entry) == "Rheinbahn - Hauptbahnhof (→ Köln)"
    assert station_entity_key(_coordinator(), entry) == f"{PROVIDER_VRR}_{STOP_ID}_abc12345"


async def test_clearing_every_filter_falls_back_to_the_creation_label(hass: HomeAssistant):
    """An entry with a suffix stays labelled even if the filters are emptied.

    Dropping the label would make two same-station devices indistinguishable.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_VRR,
            CONF_STATION_ID: STOP_ID,
            CONF_DESTINATION_FILTER: "Duisburg",
            CONF_ENTRY_SUFFIX: "abc12345",
            CONF_ENTRY_LABEL: "→ Duisburg",
        },
        options={CONF_DESTINATION_FILTER: ""},
    )
    entry.add_to_hass(hass)

    assert station_device_name(_coordinator(), entry) == "Rheinbahn - Hauptbahnhof (→ Duisburg)"


async def test_filters_on_a_pre_existing_entry_do_not_rename_its_device(hass: HomeAssistant):
    """No discriminator means no label — upgrading must not rename anything.

    Plenty of existing entries have filters set under Options; they were
    created before #55 and carry no suffix, so their device name must stay
    exactly what it was.
    """
    entry = _entry(hass, **{CONF_DESTINATION_FILTER: "Duisburg"})

    assert station_device_name(_coordinator(), entry) == "Rheinbahn - Hauptbahnhof"


async def test_every_platform_derives_its_key_from_the_shared_helper(hass: HomeAssistant):
    """sensor, binary_sensor, calendar, camera, event and statistics stay in sync."""
    from custom_components.openpublictransport.binary_sensor import PublicTransportDelayBinarySensor
    from custom_components.openpublictransport.calendar import DepartureCalendar
    from custom_components.openpublictransport.event import DisruptionEventEntity
    from custom_components.openpublictransport.statistics import PunctualitySensor

    entry = _entry(hass, **{CONF_ENTRY_SUFFIX: "abc12345", CONF_ENTRY_LABEL: "→ Duisburg"})
    coordinator = _coordinator()
    coordinator.hass = hass
    expected = f"{PROVIDER_VRR}_{STOP_ID}_abc12345"

    assert PublicTransportDelayBinarySensor(coordinator, entry, ["bus"]).unique_id == f"{expected}_delays"
    assert DepartureCalendar(coordinator, entry).unique_id == f"{expected}_calendar"
    assert DisruptionEventEntity(coordinator, entry).unique_id == f"{expected}_disruptions"
    assert PunctualitySensor(coordinator, entry).unique_id == f"{expected}_statistics"


# ── the discriminator itself ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "user_input",
    [
        {},
        {CONF_LINE_FILTER: "", CONF_DESTINATION_FILTER: "", CONF_PLATFORM_FILTER: ""},
        {CONF_LINE_FILTER: "  ", CONF_DESTINATION_FILTER: ",", CONF_PLATFORM_FILTER: " , "},
        # Filters that do not discriminate between directions are ignored
        {CONF_FAVORITE_LINES: "S1", CONF_WALKING_TIME: 5, CONF_DEPARTURES: 20},
    ],
)
def test_no_discriminator_without_filters(user_input):
    assert filter_discriminator(user_input) == ""
    assert filter_label(user_input) == ""


def test_discriminator_is_stable_and_short():
    first = filter_discriminator({CONF_DESTINATION_FILTER: "Duisburg"})
    second = filter_discriminator({CONF_DESTINATION_FILTER: "Duisburg"})

    assert first == second
    assert len(first) == 8
    assert first.isalnum()


def test_discriminator_ignores_order_and_case():
    assert filter_discriminator({CONF_LINE_FILTER: "S1,S2"}) == filter_discriminator(
        {CONF_LINE_FILTER: " s2 , S1 "}
    )


def test_discriminator_differs_per_filter_field():
    """The same text in two different fields is two different configurations."""
    assert filter_discriminator({CONF_LINE_FILTER: "3"}) != filter_discriminator({CONF_PLATFORM_FILTER: "3"})


def test_label_covers_all_three_filters():
    label = filter_label(
        {CONF_LINE_FILTER: "S1", CONF_DESTINATION_FILTER: "Duisburg", CONF_PLATFORM_FILTER: "3"}
    )
    assert label == "S1 → Duisburg Pl. 3"
