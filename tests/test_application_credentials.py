"""Tests for application_credentials.py."""

import pytest
from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant

from custom_components.openpublictransport.application_credentials import (
    _ApiKeyImplementation,
    async_get_auth_implementation,
    async_get_description_placeholders,
)


async def test_async_get_auth_implementation(hass: HomeAssistant):
    """Test that async_get_auth_implementation returns an _ApiKeyImplementation."""
    credential = ClientCredential(client_id="test-api-key", client_secret="", name="Test Provider")
    impl = await async_get_auth_implementation(hass, "openpublictransport.vrr", credential)
    assert isinstance(impl, _ApiKeyImplementation)


async def test_api_key_implementation_name(hass: HomeAssistant):
    """Test that name returns credential name."""
    credential = ClientCredential(client_id="key", client_secret="", name="My Provider")
    impl = _ApiKeyImplementation(hass, "openpublictransport.vrr", credential)
    assert impl.name == "My Provider"


async def test_api_key_implementation_name_fallback(hass: HomeAssistant):
    """Test that name falls back to auth_domain when credential name is empty."""
    credential = ClientCredential(client_id="key", client_secret="", name="")
    impl = _ApiKeyImplementation(hass, "openpublictransport.vrr", credential)
    assert impl.name == "openpublictransport.vrr"


async def test_async_get_description_placeholders(hass: HomeAssistant):
    """Test description placeholders are returned."""
    result = await async_get_description_placeholders(hass)
    assert "description" in result
    assert "Client ID" in result["description"]
