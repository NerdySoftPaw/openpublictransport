"""Trip planning capability: config flow guard + docs table (issue #80).

Only EFA providers with an XML_TRIP_REQUEST2 endpoint and the OTP providers can
plan trips. Picking any other provider used to create a trip sensor that never
returned a connection, and the documentation advertised providers (ÖBB, SBB)
that were never supported while omitting the OTP2 ones that are.
"""

import re
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.openpublictransport.const import (
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_OEBB,
    PROVIDER_VRR,
)
from custom_components.openpublictransport.trip import (
    EFA_TRIP_ENDPOINTS,
    TRIP_CAPABLE_PROVIDERS,
    supports_trip_planning,
)

DOCS_TRIP_PLANNER = Path(__file__).resolve().parents[1] / "docs" / "trip-planner.md"


def test_capability_set_covers_every_dispatch_branch():
    assert EFA_TRIP_ENDPOINTS.keys() <= TRIP_CAPABLE_PROVIDERS
    assert supports_trip_planning("openpublictransport")
    assert supports_trip_planning("otp_custom")
    assert supports_trip_planning("vbn_otp")
    assert not supports_trip_planning(PROVIDER_OEBB)
    assert not supports_trip_planning("sbb")
    assert not supports_trip_planning(None)


def test_docs_table_matches_capability_set():
    """The docs list exactly the providers the code can route (issue #80)."""
    documented = set(re.findall(r"^\|[^|]+\|\s*`([a-z0-9_]+)`\s*\|", DOCS_TRIP_PLANNER.read_text(), re.M))
    assert documented == set(TRIP_CAPABLE_PROVIDERS)


async def test_trip_entry_rejected_for_provider_without_routing(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_OEBB},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "trip_not_supported"}


async def test_departure_entry_still_allowed_for_same_provider(hass: HomeAssistant):
    """The guard must only block trip entries, not the departure monitor."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OEBB},
    )

    assert result["step_id"] == "stop_search"


async def test_trip_entry_allowed_for_efa_provider(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={"entry_type": "trip", CONF_PROVIDER: PROVIDER_VRR},
    )

    assert result["step_id"] == "trip_search"
