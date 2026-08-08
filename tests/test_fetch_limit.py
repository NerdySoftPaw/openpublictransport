"""Tests for the departures over-fetch behaviour (issues #43, #81).

When a line/destination/platform filter or a partial transportation type
selection is active, the coordinator must request a larger raw board from the
API so client-side filtering isn't starved before the list is truncated to the
user's display count.
"""

from unittest.mock import AsyncMock, MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DESTINATION_FILTER,
    CONF_LINE_FILTER,
    CONF_PLATFORM_FILTER,
    CONF_TRANSPORTATION_TYPES,
    DOMAIN,
    FILTERED_FETCH_LIMIT,
    PROVIDER_VRR,
    TRANSPORTATION_TYPES,
)
from custom_components.openpublictransport.sensor import (
    PublicTransportDataUpdateCoordinator,
)


def _coordinator(hass, entry=None, departures_limit=20):
    return PublicTransportDataUpdateCoordinator(
        hass,
        provider=PROVIDER_VRR,
        place_dm="Düsseldorf",
        name_dm="Hauptbahnhof",
        station_id=None,
        departures_limit=departures_limit,
        scan_interval=60,
        config_entry=entry,
    )


def _entry(hass, **options):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options)
    entry.add_to_hass(hass)
    return entry


async def test_no_config_entry_uses_display_limit(hass):
    coordinator = _coordinator(hass, entry=None, departures_limit=20)
    assert coordinator._compute_fetch_limit() == 20


async def test_no_filter_uses_display_limit(hass):
    entry = _entry(hass, **{CONF_LINE_FILTER: "", CONF_DESTINATION_FILTER: "", CONF_PLATFORM_FILTER: ""})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == 20


async def test_line_filter_triggers_overfetch(hass):
    entry = _entry(hass, **{CONF_LINE_FILTER: "U79,708"})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == FILTERED_FETCH_LIMIT


async def test_destination_filter_triggers_overfetch(hass):
    entry = _entry(hass, **{CONF_DESTINATION_FILTER: "Airport"})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == FILTERED_FETCH_LIMIT


async def test_platform_filter_triggers_overfetch(hass):
    entry = _entry(hass, **{CONF_PLATFORM_FILTER: "3"})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == FILTERED_FETCH_LIMIT


async def test_platform_filter_from_entry_data_triggers_overfetch(hass):
    """A filter stored in entry.data (set during setup) counts too."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PLATFORM_FILTER: "3"}, options={})
    entry.add_to_hass(hass)
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == FILTERED_FETCH_LIMIT


async def test_overfetch_never_below_display_limit(hass):
    """A display count above the over-fetch constant is preserved."""
    entry = _entry(hass, **{CONF_LINE_FILTER: "U79"})
    coordinator = _coordinator(hass, entry=entry, departures_limit=150)
    assert coordinator._compute_fetch_limit() == 150


async def test_transportation_type_subset_triggers_overfetch(hass):
    """A "trains only" board is starved by buses without the larger fetch (#81)."""
    entry = _entry(hass, **{CONF_TRANSPORTATION_TYPES: ["train"]})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == FILTERED_FETCH_LIMIT


async def test_transportation_type_subset_from_entry_data_triggers_overfetch(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_TRANSPORTATION_TYPES: ["train", "subway"]}, options={}
    )
    entry.add_to_hass(hass)
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == FILTERED_FETCH_LIMIT


async def test_all_transportation_types_uses_display_limit(hass):
    """Selecting every type filters nothing — no reason to over-fetch."""
    entry = _entry(hass, **{CONF_TRANSPORTATION_TYPES: list(TRANSPORTATION_TYPES)})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == 20


async def test_empty_transportation_types_uses_display_limit(hass):
    entry = _entry(hass, **{CONF_TRANSPORTATION_TYPES: []})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == 20


async def test_unknown_transportation_type_uses_display_limit(hass):
    """Unrecognised values must not silently trigger a 100-departure fetch."""
    entry = _entry(hass, **{CONF_TRANSPORTATION_TYPES: ["helicopter"]})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == 20


async def test_non_list_transportation_types_uses_display_limit(hass):
    """A malformed (non-list) option must not crash the coordinator."""
    entry = _entry(hass, **{CONF_TRANSPORTATION_TYPES: "train"})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)
    assert coordinator._compute_fetch_limit() == 20


async def test_transportation_type_overfetch_never_below_display_limit(hass):
    entry = _entry(hass, **{CONF_TRANSPORTATION_TYPES: ["train"]})
    coordinator = _coordinator(hass, entry=entry, departures_limit=150)
    assert coordinator._compute_fetch_limit() == 150


async def test_fetch_departures_passes_overfetch_limit(hass):
    """With a filter set, the API is queried with the larger board size."""
    entry = _entry(hass, **{CONF_LINE_FILTER: "U79"})
    coordinator = _coordinator(hass, entry=entry, departures_limit=20)

    provider = MagicMock()
    provider.fetch_departures = AsyncMock(return_value={"stopEvents": []})
    coordinator.provider_instance = provider  # pre-set so _ensure_provider is a no-op

    await coordinator._fetch_departures()

    _, _, _, limit = provider.fetch_departures.await_args.args
    assert limit == FILTERED_FETCH_LIMIT
