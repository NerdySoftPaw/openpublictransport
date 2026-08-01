"""Reconfigure must not silently reset the settings it does not ask about.

Reconfigure exists to move an entry to a different stop. It reuses the settings
step, whose schema was built with hardcoded defaults, so submitting it rewrote
`entry.data` with those defaults — quietly resetting departures, scan interval,
transport types and (since #57 started persisting them) every filter.
"""

from unittest.mock import AsyncMock, patch

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
    CONF_STATION_ID,
    CONF_TRANSPORTATION_TYPES,
    CONF_USE_PROVIDER_LOGO,
    CONF_WALKING_TIME,
    DOMAIN,
    PROVIDER_VRR,
)

NEW_STOP = [{"id": "de:05111:99", "name": "Bilk S", "place": "Düsseldorf"}]


def _configured_entry(hass: HomeAssistant, *, in_options: bool) -> MockConfigEntry:
    """An entry with non-default settings, stored where the given era put them.

    `in_options` models an entry configured through the options flow (every
    entry before #57 could only get filters that way); otherwise the values sit
    in `data`, where the setup wizard now persists them.
    """
    settings = {
        CONF_DEPARTURES: 15,
        CONF_SCAN_INTERVAL: 300,
        CONF_TRANSPORTATION_TYPES: ["train"],
        CONF_USE_PROVIDER_LOGO: True,
        CONF_DELAY_THRESHOLD: 12,
        CONF_LINE_FILTER: "S1, S6",
        CONF_DESTINATION_FILTER: "Duisburg",
        CONF_PLATFORM_FILTER: "3",
        CONF_FAVORITE_LINES: "S1",
        CONF_WALKING_TIME: 7,
    }
    base = {
        CONF_PROVIDER: PROVIDER_VRR,
        CONF_STATION_ID: "de:05111:21",
        "place_dm": "Düsseldorf",
        "name_dm": "Hauptbahnhof",
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=base if in_options else {**base, **settings},
        options=settings if in_options else {},
        unique_id=f"{PROVIDER_VRR}_de:05111:21",
    )
    entry.add_to_hass(hass)
    return entry


async def _reconfigure_to_new_stop(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    """Run the reconfigure flow through to the settings form and submit it as-is."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert result["step_id"] == "stop_search"

    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        provider = AsyncMock()
        provider.search_stops = AsyncMock(return_value=NEW_STOP)
        mock_gp.return_value = provider
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Bilk"}
        )

    if result["step_id"] == "stop_select":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop": "de:05111:99"}
        )

    assert result["step_id"] == "settings"

    # Submit whatever the form offers, which is what a user who only wants to
    # change the stop actually does.
    defaults = {str(key): key.default() for key in result["data_schema"].schema if hasattr(key, "default")}
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input=defaults)


async def test_reconfigure_preserves_settings_stored_in_data(hass: HomeAssistant):
    """Filters persisted by the setup wizard survive a stop change."""
    entry = _configured_entry(hass, in_options=False)

    result = await _reconfigure_to_new_stop(hass, entry)

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"

    # The stop moved …
    assert entry.data[CONF_STATION_ID] == "de:05111:99"
    assert entry.data["name_dm"] == "Bilk S"

    # … and nothing else did.
    assert entry.data[CONF_LINE_FILTER] == "S1, S6"
    assert entry.data[CONF_DESTINATION_FILTER] == "Duisburg"
    assert entry.data[CONF_PLATFORM_FILTER] == "3"
    assert entry.data[CONF_FAVORITE_LINES] == "S1"
    assert entry.data[CONF_DEPARTURES] == 15
    assert entry.data[CONF_SCAN_INTERVAL] == 300
    assert entry.data[CONF_TRANSPORTATION_TYPES] == ["train"]
    assert entry.data[CONF_USE_PROVIDER_LOGO] is True
    assert entry.data[CONF_DELAY_THRESHOLD] == 12
    assert entry.data[CONF_WALKING_TIME] == 7


async def test_reconfigure_preserves_settings_stored_in_options(hass: HomeAssistant):
    """The pre-#57 shape: settings live in options and must stay authoritative."""
    entry = _configured_entry(hass, in_options=True)

    await _reconfigure_to_new_stop(hass, entry)

    assert entry.data[CONF_STATION_ID] == "de:05111:99"

    # Options are never touched by the config flow …
    assert entry.options[CONF_LINE_FILTER] == "S1, S6"
    assert entry.options[CONF_DEPARTURES] == 15

    # … and the values written into data mirror them, so the entry reads the
    # same whichever source wins.
    assert entry.data[CONF_LINE_FILTER] == "S1, S6"
    assert entry.data[CONF_DEPARTURES] == 15


async def test_reconfigure_form_is_prefilled(hass: HomeAssistant):
    """The form shows the current values, so a user can see what they are changing."""
    entry = _configured_entry(hass, in_options=False)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        provider = AsyncMock()
        provider.search_stops = AsyncMock(return_value=NEW_STOP)
        mock_gp.return_value = provider
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Bilk"}
        )
    if result["step_id"] == "stop_select":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop": "de:05111:99"}
        )

    defaults = {str(key): key.default() for key in result["data_schema"].schema if hasattr(key, "default")}

    assert defaults[CONF_DEPARTURES] == 15
    assert defaults[CONF_SCAN_INTERVAL] == 300
    assert defaults[CONF_LINE_FILTER] == "S1, S6"
    assert defaults[CONF_PLATFORM_FILTER] == "3"
    assert defaults[CONF_TRANSPORTATION_TYPES] == ["train"]


async def test_fresh_setup_still_uses_plain_defaults(hass: HomeAssistant):
    """A normal (non-reconfigure) setup must not inherit another entry's settings."""
    _configured_entry(hass, in_options=False)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_VRR},
    )
    with patch("custom_components.openpublictransport.config_flow.get_provider") as mock_gp:
        provider = AsyncMock()
        provider.search_stops = AsyncMock(return_value=NEW_STOP)
        mock_gp.return_value = provider
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop_search": "Bilk"}
        )
    if result["step_id"] == "stop_select":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"stop": "de:05111:99"}
        )

    defaults = {str(key): key.default() for key in result["data_schema"].schema if hasattr(key, "default")}

    assert defaults[CONF_DEPARTURES] == 10
    assert defaults[CONF_SCAN_INTERVAL] == 60
    assert defaults[CONF_LINE_FILTER] == ""
    assert defaults[CONF_PLATFORM_FILTER] == ""
