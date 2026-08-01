"""Tests for the HVV Geofox GTI provider wiring (issue #61).

GTI is the first provider that needs *two* mandatory credentials: the username
identifies the application and the password is the HMAC key every request is
signed with. Neither half is optional, unlike NTA's secondary key.
"""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openpublictransport.const import (
    CONF_DELAY_THRESHOLD,
    CONF_DEPARTURES,
    CONF_DESTINATION_FILTER,
    CONF_FAVORITE_LINES,
    CONF_HVV_GTI_PASSWORD,
    CONF_HVV_GTI_USER,
    CONF_LINE_FILTER,
    CONF_PLATFORM_FILTER,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_HVV,
    PROVIDER_HVV_GTI,
    PROVIDERS,
)
from custom_components.openpublictransport.sensor import PublicTransportDataUpdateCoordinator

STOPS = [{"id": "Master:80953", "name": "Hauptbahnhof", "place": "Hamburg"}]

SETTINGS = {
    CONF_DEPARTURES: 10,
    CONF_SCAN_INTERVAL: 60,
    CONF_TRANSPORTATION_TYPES: ["bus", "train", "tram", "subway"],
    CONF_USE_PROVIDER_LOGO: False,
    CONF_DELAY_THRESHOLD: 5,
    CONF_LINE_FILTER: "",
    CONF_DESTINATION_FILTER: "",
    CONF_PLATFORM_FILTER: "",
    CONF_FAVORITE_LINES: "",
    CONF_WALKING_TIME: 0,
}


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_HVV_GTI},
    )


def test_provider_is_offered_alongside_the_efa_one():
    """The keyless EFA provider must stay — its ID is load-bearing for existing entries."""
    assert PROVIDER_HVV_GTI in PROVIDERS
    assert PROVIDER_HVV in PROVIDERS


async def test_flow_asks_for_both_credentials(hass: HomeAssistant):
    result = await _start(hass)

    assert result["step_id"] == "api_key"
    keys = {str(key) for key in result["data_schema"].schema}
    assert keys == {CONF_HVV_GTI_USER, CONF_HVV_GTI_PASSWORD}


async def test_password_is_mandatory(hass: HomeAssistant):
    """Unlike NTA's secondary key, the GTI password is not optional."""
    result = await _start(hass)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HVV_GTI_USER: "myapp", CONF_HVV_GTI_PASSWORD: "  "}
    )

    assert result2["step_id"] == "api_key"
    assert result2["errors"] == {"base": "hvv_gti_credentials_required"}


async def test_username_is_mandatory(hass: HomeAssistant):
    result = await _start(hass)

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HVV_GTI_USER: "", CONF_HVV_GTI_PASSWORD: "s3cr3t"}
    )

    assert result2["errors"] == {"base": "hvv_gti_credentials_required"}


async def test_full_flow_stores_both_credentials(hass: HomeAssistant):
    result = await _start(hass)

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        provider = AsyncMock()
        provider.search_stops = AsyncMock(return_value=STOPS)
        mock_gp.return_value = provider

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HVV_GTI_USER: "myapp", CONF_HVV_GTI_PASSWORD: "s3cr3t"},
        )
        if result["step_id"] == "stop_search":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"stop_search": "Hauptbahnhof"}
            )

    if result["step_id"] == "stop_select":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop": "Master:80953"}
        )

    assert result["step_id"] == "settings"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=SETTINGS)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_PROVIDER] == PROVIDER_HVV_GTI
    assert result["data"][CONF_HVV_GTI_USER] == "myapp"
    assert result["data"][CONF_HVV_GTI_PASSWORD] == "s3cr3t"
    assert result["data"][CONF_STATION_ID] == "Master:80953"


async def test_coordinator_passes_the_password_to_the_provider(hass: HomeAssistant):
    """The password is the HMAC key — without it nothing can be signed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROVIDER: PROVIDER_HVV_GTI,
            CONF_STATION_ID: "Master:80953",
            "place_dm": "Hamburg",
            "name_dm": "Hauptbahnhof",
            CONF_HVV_GTI_USER: "myapp",
            CONF_HVV_GTI_PASSWORD: "s3cr3t",
        },
    )
    entry.add_to_hass(hass)

    coordinator = PublicTransportDataUpdateCoordinator(
        hass,
        PROVIDER_HVV_GTI,
        "Hamburg",
        "Hauptbahnhof",
        "Master:80953",
        10,
        60,
        config_entry=entry,
        api_key="myapp",
    )

    assert coordinator.api_key_secondary == "s3cr3t"

    with patch("custom_components.openpublictransport.sensor.get_provider") as mock_gp:
        coordinator._ensure_provider()

    assert mock_gp.call_args.kwargs["api_key"] == "myapp"
    assert mock_gp.call_args.kwargs["api_key_secondary"] == "s3cr3t"


async def test_efa_hvv_coordinator_has_no_secondary_key(hass: HomeAssistant):
    """The keyless provider is unaffected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROVIDER: PROVIDER_HVV, CONF_STATION_ID: "de:02000:1", "place_dm": "", "name_dm": "Hbf"},
    )
    entry.add_to_hass(hass)

    coordinator = PublicTransportDataUpdateCoordinator(
        hass, PROVIDER_HVV, "", "Hbf", "de:02000:1", 10, 60, config_entry=entry
    )

    assert coordinator.api_key_secondary is None


async def test_provider_resolves_from_the_library(hass: HomeAssistant):
    """The registry entry exists and reports that it needs a key."""
    from openpublictransport import get_provider

    provider = get_provider(PROVIDER_HVV_GTI, None, api_key="u", api_key_secondary="p")

    assert provider is not None
    assert provider.provider_id == PROVIDER_HVV_GTI
    assert provider.requires_api_key is True
