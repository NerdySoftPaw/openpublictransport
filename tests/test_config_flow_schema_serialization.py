"""Every form schema must survive the serialization HA does before rendering.

A config-flow form is turned into JSON for the frontend, and a schema value that
the serializer does not understand — a bare validator function such as `cv.url`
— makes the whole step fail with HTTP 500. The step is then unreachable in every
client, while tests that only drive the flow object never notice: they read the
schema, they never serialize it.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.helpers.config_validation as cv
import pytest
from homeassistant.core import HomeAssistant
from probatio.codecs.fields import to_field_list

from custom_components.openpublictransport.const import (
    CONF_OTP_BASE_URL,
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_VRR,
)


def _assert_serializable(result):
    """Fail with the offending step named, the way the 500 never did."""
    schema = result.get("data_schema")
    if schema is None:
        return
    try:
        to_field_list(schema, custom_serializer=cv.custom_serializer)
    except Exception as err:  # noqa: BLE001 — surfaced as a test failure
        pytest.fail(f"step {result.get('step_id')!r} has an unserializable schema: {err}")


async def _init(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    _assert_serializable(result)
    return result


@pytest.mark.parametrize(
    ("provider", "expected_step"),
    [
        (PROVIDER_VRR, "stop_search"),
        (PROVIDER_OTP_CUSTOM, "otp_custom_url"),
        (PROVIDER_RMV, "api_key"),
        (PROVIDER_TRAFIKLAB_SE, "api_key"),
    ],
)
async def test_first_step_per_provider_is_serializable(hass: HomeAssistant, provider, expected_step):
    result = await _init(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"entry_type": "departures", CONF_PROVIDER: provider}
    )

    assert result["step_id"] == expected_step
    _assert_serializable(result)


async def test_otp_custom_url_step_renders(hass: HomeAssistant):
    """The regression itself: this step used to raise on serialization."""
    result = await _init(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM}
    )

    fields = to_field_list(result["data_schema"], custom_serializer=cv.custom_serializer)
    url_field = next(f for f in fields if f["name"] == CONF_OTP_BASE_URL)

    assert url_field["required"] is True
    assert url_field["selector"]["text"]["type"] == "url"


@pytest.mark.parametrize("bad_url", ["", "   ", "not-a-url", "ftp://example.org", "http://"])
async def test_otp_custom_url_rejects_unusable_input(hass: HomeAssistant, bad_url):
    """Validation moved out of the schema, so it has to still reject bad input."""
    result = await _init(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_OTP_BASE_URL: bad_url}
    )

    assert result["step_id"] == "otp_custom_url"
    assert result["errors"][CONF_OTP_BASE_URL] == "otp_url_required"
    _assert_serializable(result)


async def test_otp_custom_url_accepts_a_reachable_instance(hass: HomeAssistant):
    result = await _init(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"entry_type": "departures", CONF_PROVIDER: PROVIDER_OTP_CUSTOM}
    )

    healthy = MagicMock()
    healthy.status = 200
    healthy.__aenter__ = AsyncMock(return_value=healthy)
    healthy.__aexit__ = AsyncMock(return_value=False)

    with patch("custom_components.openpublictransport.config_flow.async_get_clientsession") as mock_sess:
        session = MagicMock()
        session.get = MagicMock(return_value=healthy)
        mock_sess.return_value = session

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_OTP_BASE_URL: "http://192.168.1.10:8080/otp/routers/default"}
        )

    assert result["step_id"] == "stop_search"
    _assert_serializable(result)
