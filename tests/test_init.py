"""Tests for OpenPublicTransport integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport import async_setup, async_setup_entry, async_unload_entry
from custom_components.openpublictransport.const import DOMAIN


async def test_async_setup(hass: HomeAssistant):
    """Test the component setup."""
    assert await async_setup(hass, {}) is True


async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test setting up a config entry."""
    with patch(
        "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ):
            assert await async_setup_entry(hass, mock_config_entry) is True
            # Coordinator stored in runtime_data, not hass.data
            assert mock_config_entry.runtime_data is not None


async def test_async_unload_entry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test unloading a config entry."""
    mock_coordinator = MagicMock()
    mock_config_entry.runtime_data = mock_coordinator

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        assert await async_unload_entry(hass, mock_config_entry) is True
        # runtime_data is cleared automatically by HA; no hass.data coordinator entry
        assert f"{mock_config_entry.entry_id}_coordinator" not in hass.data.get(DOMAIN, {})


async def test_refresh_service(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test the refresh_departures service is registered in async_setup."""
    await async_setup(hass, {})

    with patch(
        "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ):
            await async_setup_entry(hass, mock_config_entry)
            assert hass.services.has_service(DOMAIN, "refresh_departures")
