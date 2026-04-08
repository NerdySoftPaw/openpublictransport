"""Tests for OpenPublicTransport diagnostics."""

from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.const import DOMAIN
from custom_components.openpublictransport.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """Test diagnostics output."""
    # mock_config_entry already added to hass in fixture

    # Store coordinator in hass.data
    hass.data[DOMAIN] = {f"{mock_config_entry.entry_id}_coordinator": mock_coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert "entry" in diagnostics
    assert "coordinator" in diagnostics
    assert diagnostics["entry"]["title"] == "Test Station"
    assert diagnostics["entry"]["data"]["provider"] == "vrr"
    # place_dm and name_dm should be redacted
    assert diagnostics["entry"]["data"]["place_dm"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["name_dm"] == "**REDACTED**"

    # Verify API stats are included
    assert "api_calls_today" in diagnostics["coordinator"]
    assert "last_update_success" in diagnostics["coordinator"]


async def test_diagnostics_no_coordinator(hass: HomeAssistant, mock_config_entry):
    """Test diagnostics when coordinator is not available."""
    # mock_config_entry already added to hass in fixture
    hass.data[DOMAIN] = {}

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # When no coordinator, the diagnostics should still have entry data but no coordinator
    assert "entry" in diagnostics
    assert "coordinator" not in diagnostics
