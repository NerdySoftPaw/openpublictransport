"""Regression: API-key providers must pass their key to the coordinator at setup.

Rejseplanen and National Rail were added to the config flow but were missing
from the runtime api_key resolution in async_setup_entry, so the provider was
instantiated without a key ("API key required"). These tests guard that path.
"""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport import async_setup_entry
from custom_components.openpublictransport.const import (
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_PROVIDER,
    CONF_REJSEPLANEN_API_KEY,
    CONF_STATION_ID,
    DOMAIN,
    PROVIDER_NATIONAL_RAIL,
    PROVIDER_REJSEPLANEN,
)


@pytest.mark.parametrize(
    ("provider", "conf_key"),
    [
        (PROVIDER_REJSEPLANEN, CONF_REJSEPLANEN_API_KEY),
        (PROVIDER_NATIONAL_RAIL, CONF_NATIONAL_RAIL_API_KEY),
    ],
)
async def test_api_key_reaches_coordinator(hass: HomeAssistant, provider, conf_key):
    """The configured API key must be resolved and handed to the coordinator."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: provider,
            conf_key: "the-secret-key",
            "place_dm": "",
            "name_dm": "",
            CONF_STATION_ID: "8600626",
        },
        unique_id=f"{provider}_test",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.openpublictransport.PublicTransportDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        assert await async_setup_entry(hass, entry) is True

    assert entry.runtime_data is not None
    assert entry.runtime_data.api_key == "the-secret-key"
