"""Regression: the API key entered in the config flow must be persisted in the
entry data for Rejseplanen + National Rail.

Behind the v2026.6.15/.16 "API key required" failures: the settings step built
the entry data without writing the key for these two providers, so it was never
stored and never reached the provider at runtime.
"""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import (
    CONF_NATIONAL_RAIL_API_KEY,
    CONF_PROVIDER,
    CONF_REJSEPLANEN_API_KEY,
    CONF_SCAN_INTERVAL,
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
async def test_api_key_persisted_in_entry_data(hass: HomeAssistant, provider, conf_key):
    """Entering the key in the flow stores it under the provider's CONF_*_API_KEY."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: provider},
    )
    assert result["step_id"] == "api_key"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={conf_key: "the-secret-key"}
    )
    assert result2["step_id"] == "stop_search"

    one_stop = [{"id": "8600626", "name": "København H", "place": ""}]
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.search_stops = AsyncMock(return_value=one_stop)
        mock_gp.return_value = mock_provider
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input={"stop_search": "København"}
        )

    # A single search result may auto-select (→ settings) or show stop_select.
    if result3["step_id"] == "stop_select":
        result3 = await hass.config_entries.flow.async_configure(
            result3["flow_id"], user_input={"stop": "8600626"}
        )
    assert result3["step_id"] == "settings"

    with patch.object(OpenPublicTransportConfigFlow, "_async_store_credential", new_callable=AsyncMock):
        result4 = await hass.config_entries.flow.async_configure(
            result3["flow_id"], user_input={CONF_SCAN_INTERVAL: 60}
        )

    assert result4["type"] == "create_entry"
    assert result4["data"].get(conf_key) == "the-secret-key"
