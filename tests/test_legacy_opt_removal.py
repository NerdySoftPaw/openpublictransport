"""Tests for removing entries of the shut-down openpublictransport.net community server."""

import pytest
from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport import async_setup, async_setup_entry
from custom_components.openpublictransport.const import CONF_PROVIDER, DOMAIN, LEGACY_PROVIDER_OPT
from custom_components.openpublictransport.repairs import async_create_fix_flow


def _legacy_departure_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Düsseldorf Hbf",
        data={CONF_PROVIDER: LEGACY_PROVIDER_OPT, "station_id": "gtfsde:1", "opt_api_key": "old-key"},
    )
    entry.add_to_hass(hass)
    return entry


def _legacy_trip_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home → Work",
        data={"is_trip": True, "trip_provider": LEGACY_PROVIDER_OPT},
    )
    entry.add_to_hass(hass)
    return entry


async def test_legacy_entries_are_removed_with_their_entities(hass: HomeAssistant, mock_config_entry):
    """Entries of the community server are deleted on startup, other entries stay."""
    departure = _legacy_departure_entry(hass)
    trip = _legacy_trip_entry(hass)
    entity_registry = er.async_get(hass)
    legacy_entity = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "opt_legacy_sensor", config_entry=departure
    )
    kept_entity = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "vrr_kept_sensor", config_entry=mock_config_entry
    )

    assert await async_setup(hass, {}) is True
    await hass.async_block_till_done()

    remaining = {entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)}
    assert remaining == {mock_config_entry.entry_id}
    assert departure.entry_id not in remaining
    assert trip.entry_id not in remaining
    assert entity_registry.async_get(legacy_entity.entity_id) is None
    assert entity_registry.async_get(kept_entity.entity_id) is not None

    issue = ir.async_get(hass).async_get_issue(DOMAIN, "opt_provider_removed")
    assert issue is not None
    assert issue.is_fixable
    assert issue.is_persistent
    assert issue.translation_placeholders == {"entries": "Düsseldorf Hbf, Home → Work"}


async def test_no_issue_without_legacy_entries(hass: HomeAssistant, mock_config_entry):
    """Users without community-server entries see no repair notice."""
    assert await async_setup(hass, {}) is True

    assert hass.config_entries.async_entries(DOMAIN) == [mock_config_entry]
    assert ir.async_get(hass).async_get_issue(DOMAIN, "opt_provider_removed") is None


async def test_setup_entry_rejects_legacy_entry(hass: HomeAssistant):
    """A legacy entry that slips past the startup cleanup fails permanently."""
    entry = _legacy_departure_entry(hass)

    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)


async def test_fix_flow_is_a_confirmation(hass: HomeAssistant):
    """The removal notice is dismissed with a simple confirmation."""
    flow = await async_create_fix_flow(hass, "opt_provider_removed", None)

    assert isinstance(flow, ConfirmRepairFlow)
