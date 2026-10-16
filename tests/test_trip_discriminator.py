"""Tests for adding the same trip route twice with a different arrival time.

The wizard used to abort with `already_configured` on the second entry,
because the unique ID was just f"{provider}_trip_{origin}_{dest}" with no
regard for the target arrival — which blocked the exact use case arrival
times were built for: one trip entry per child, each arriving by a different
first-lesson time. A trip with a target arrival now gets a stable
discriminator derived from that arrival config, mirroring issue #55's fix for
departure entries.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_ARRIVAL_OFFSET,
    CONF_ARRIVAL_TIME,
    CONF_ARRIVAL_TIME_ENTITY,
    CONF_ENTRY_LABEL,
    CONF_ENTRY_SUFFIX,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    PROVIDER_VRR,
)
from custom_components.openpublictransport.filters import (
    current_trip_arrival,
    trip_arrival_discriminator,
    trip_arrival_label,
)
from custom_components.openpublictransport.trip_sensor import (
    CONF_IS_TRIP,
    CONF_TRIP_DESTINATION,
    CONF_TRIP_DESTINATION_CITY,
    CONF_TRIP_ORIGIN,
    CONF_TRIP_ORIGIN_CITY,
    CONF_TRIP_PROVIDER,
    TripDataUpdateCoordinator,
    trip_device_name,
    trip_entity_key,
)

ORIGIN_ID = "de:05111:5650"
DEST_ID = "de:05315:1001"
ORIGIN_STOP = {"id": ORIGIN_ID, "name": "Hauptbahnhof", "place": "Düsseldorf"}
DEST_STOP = {"id": DEST_ID, "name": "Hbf", "place": "Köln"}


async def _run_trip_flow(hass: HomeAssistant, trip_settings: dict):
    """Drive the trip flow from provider selection to entry creation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=[ORIGIN_STOP],
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
        )

    with patch(
        "custom_components.openpublictransport.config_flow.OpenPublicTransportConfigFlow._search_stops",
        return_value=[DEST_STOP],
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Hbf Köln"}
        )

    assert result["step_id"] == "trip_settings"

    with (
        patch.object(TripDataUpdateCoordinator, "async_config_entry_first_refresh", new_callable=AsyncMock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", return_value=True),
    ):
        return await hass.config_entries.flow.async_configure(result["flow_id"], user_input=trip_settings)


def _settings(**overrides) -> dict:
    base = {CONF_SCAN_INTERVAL: 120, CONF_ARRIVAL_TIME: "", CONF_ARRIVAL_OFFSET: 15}
    base.update(overrides)
    return base


# ── the reported scenario ─────────────────────────────────────────────────────


async def test_same_route_twice_with_different_arrival_times_both_succeed(hass: HomeAssistant):
    """One trip entry per child, each arriving by a different lesson time."""
    child1 = await _run_trip_flow(hass, _settings(**{CONF_ARRIVAL_TIME: "07:45"}))
    assert child1["type"] == "create_entry"

    child2 = await _run_trip_flow(hass, _settings(**{CONF_ARRIVAL_TIME: "08:15"}))
    assert child2["type"] == "create_entry"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert entries[0].unique_id != entries[1].unique_id
    # Both are still recognisably the same route
    for entry in entries:
        assert entry.unique_id.startswith(f"{PROVIDER_VRR}_trip_{ORIGIN_ID}_{DEST_ID}")


async def test_titles_distinguish_the_two_trip_entries(hass: HomeAssistant):
    """An arrival-targeted entry says what it is targeting."""
    result = await _run_trip_flow(hass, _settings(**{CONF_ARRIVAL_TIME: "07:45"}))

    assert "(arrive 07:45)" in result["title"]
    assert result["data"][CONF_ENTRY_LABEL] == "arrive 07:45"


async def test_same_route_same_arrival_time_still_aborts(hass: HomeAssistant):
    """Two truly identical trip entries are still a duplicate."""
    first = await _run_trip_flow(hass, _settings(**{CONF_ARRIVAL_TIME: "07:45"}))
    assert first["type"] == "create_entry"

    second = await _run_trip_flow(hass, _settings(**{CONF_ARRIVAL_TIME: "07:45"}))
    assert second["type"] == "abort"
    assert second["reason"] == "already_configured"


async def test_unarrived_duplicate_still_aborts(hass: HomeAssistant):
    """Without a target arrival there is nothing to tell two trips apart."""
    first = await _run_trip_flow(hass, _settings())
    assert first["type"] == "create_entry"

    second = await _run_trip_flow(hass, _settings())
    assert second["type"] == "abort"
    assert second["reason"] == "already_configured"


async def test_unarrived_entry_keeps_the_legacy_unique_id(hass: HomeAssistant):
    """No target arrival → no discriminator, so the ID format is untouched."""
    result = await _run_trip_flow(hass, _settings())

    assert result["type"] == "create_entry"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == f"{PROVIDER_VRR}_trip_{ORIGIN_ID}_{DEST_ID}"
    assert CONF_ENTRY_SUFFIX not in result["data"]
    assert CONF_ENTRY_LABEL not in result["data"]


async def test_same_route_different_arrival_time_entities_both_succeed(hass: HomeAssistant):
    """arrival_time_entity also discriminates, not just the static arrival_time."""
    child1 = await _run_trip_flow(
        hass, _settings(**{CONF_ARRIVAL_TIME_ENTITY: "input_datetime.child1_lesson_start"})
    )
    assert child1["type"] == "create_entry"

    child2 = await _run_trip_flow(
        hass, _settings(**{CONF_ARRIVAL_TIME_ENTITY: "input_datetime.child2_lesson_start"})
    )
    assert child2["type"] == "create_entry"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert entries[0].unique_id != entries[1].unique_id


# ── trip_entity_key / trip_device_name ────────────────────────────────────────


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.provider = PROVIDER_VRR
    coordinator.origin = "Hauptbahnhof"
    coordinator.origin_city = "Düsseldorf"
    coordinator.destination = "Hbf"
    coordinator.destination_city = "Köln"
    return coordinator


def _trip_entry(hass: HomeAssistant, **extra) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_TRIP_PROVIDER: PROVIDER_VRR,
            CONF_TRIP_ORIGIN: "Hauptbahnhof",
            CONF_TRIP_ORIGIN_CITY: "Düsseldorf",
            CONF_TRIP_DESTINATION: "Hbf",
            CONF_TRIP_DESTINATION_CITY: "Köln",
            CONF_IS_TRIP: True,
            **extra,
        },
    )
    entry.add_to_hass(hass)
    return entry


def test_trip_entity_key_unchanged_for_pre_existing_entries(hass: HomeAssistant):
    """A trip entry without a discriminator keeps the byte-identical legacy key."""
    entry = _trip_entry(hass)

    assert trip_entity_key(_coordinator(), entry) == "vrr_trip_düsseldorf_hauptbahnhof_köln_hbf"
    assert trip_device_name(_coordinator(), entry) == "Hauptbahnhof, Düsseldorf → Hbf, Köln"


def test_trip_entity_key_without_a_config_entry(hass: HomeAssistant):
    """Callers that pass no entry still get the legacy key."""
    assert trip_entity_key(_coordinator()) == "vrr_trip_düsseldorf_hauptbahnhof_köln_hbf"


def test_trip_entity_key_appends_the_discriminator(hass: HomeAssistant):
    """A trip entry with a target arrival gets its own key, so two do not collide."""
    entry = _trip_entry(
        hass,
        **{CONF_ARRIVAL_TIME: "07:45", CONF_ENTRY_SUFFIX: "abc12345", CONF_ENTRY_LABEL: "arrive 07:45"},
    )

    assert trip_entity_key(_coordinator(), entry) == "vrr_trip_düsseldorf_hauptbahnhof_köln_hbf_abc12345"
    assert trip_device_name(_coordinator(), entry) == "Hauptbahnhof, Düsseldorf → Hbf, Köln (arrive 07:45)"


def test_trip_device_name_tracks_current_arrival_not_frozen_suffix(hass: HomeAssistant):
    """Changing the arrival time under Options updates the label, not the ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_TRIP_PROVIDER: PROVIDER_VRR,
            CONF_TRIP_ORIGIN: "Hauptbahnhof",
            CONF_TRIP_ORIGIN_CITY: "Düsseldorf",
            CONF_TRIP_DESTINATION: "Hbf",
            CONF_TRIP_DESTINATION_CITY: "Köln",
            CONF_IS_TRIP: True,
            CONF_ARRIVAL_TIME: "07:45",
            CONF_ENTRY_SUFFIX: "abc12345",
            CONF_ENTRY_LABEL: "arrive 07:45",
        },
        options={CONF_ARRIVAL_TIME: "08:15"},
    )
    entry.add_to_hass(hass)

    assert trip_device_name(_coordinator(), entry) == "Hauptbahnhof, Düsseldorf → Hbf, Köln (arrive 08:15)"
    assert trip_entity_key(_coordinator(), entry) == "vrr_trip_düsseldorf_hauptbahnhof_köln_hbf_abc12345"


def test_trip_entries_without_discriminator_are_not_renamed(hass: HomeAssistant):
    """Trip entries that existed before arrival times keep their exact name."""
    entry = _trip_entry(hass, **{CONF_ARRIVAL_TIME: "07:45"})

    assert trip_device_name(_coordinator(), entry) == "Hauptbahnhof, Düsseldorf → Hbf, Köln"


# ── the discriminator itself ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source",
    [
        {},
        {CONF_ARRIVAL_TIME: "", CONF_ARRIVAL_TIME_ENTITY: ""},
        {CONF_SCAN_INTERVAL: 300},
    ],
)
def test_no_discriminator_without_an_arrival_config(source):
    assert trip_arrival_discriminator(source) == ""
    assert trip_arrival_label(source) == ""


def test_discriminator_is_stable_and_short():
    first = trip_arrival_discriminator({CONF_ARRIVAL_TIME: "07:45"})
    second = trip_arrival_discriminator({CONF_ARRIVAL_TIME: "07:45"})

    assert first == second
    assert len(first) == 8
    assert first.isalnum()


def test_discriminator_ignores_case():
    assert trip_arrival_discriminator(
        {CONF_ARRIVAL_TIME_ENTITY: "input_datetime.Child1"}
    ) == trip_arrival_discriminator({CONF_ARRIVAL_TIME_ENTITY: "input_datetime.child1"})


def test_discriminator_differs_per_arrival_time():
    assert trip_arrival_discriminator({CONF_ARRIVAL_TIME: "07:45"}) != trip_arrival_discriminator(
        {CONF_ARRIVAL_TIME: "08:15"}
    )


def test_discriminator_differs_per_arrival_entity():
    assert trip_arrival_discriminator(
        {CONF_ARRIVAL_TIME_ENTITY: "input_datetime.child1"}
    ) != trip_arrival_discriminator({CONF_ARRIVAL_TIME_ENTITY: "input_datetime.child2"})


def test_label_prefers_entity_over_static_time():
    label = trip_arrival_label(
        {CONF_ARRIVAL_TIME: "07:45", CONF_ARRIVAL_TIME_ENTITY: "input_datetime.child1"}
    )
    assert label == "→ input_datetime.child1"


def test_current_trip_arrival_options_win_over_data():
    entry = MagicMock()
    entry.data = {CONF_ARRIVAL_TIME: "07:45"}
    entry.options = {CONF_ARRIVAL_TIME: "08:15"}

    assert current_trip_arrival(entry)[CONF_ARRIVAL_TIME] == "08:15"
