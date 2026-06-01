"""Application credentials platform for Open Public Transport.

API keys are stored as ClientCredential(client_id=api_key, client_secret=secondary_key_or_empty).
This lets users manage all provider API keys centrally under HA's Application Credentials UI
instead of re-entering them for every sensor entry.
"""

from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow


class _ApiKeyImplementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Wraps a provider API key in HA's OAuth2 credential storage.

    No actual OAuth2 flow is performed — client_id IS the API key.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        auth_domain: str,
        credential: ClientCredential,
    ) -> None:
        super().__init__(
            hass,
            auth_domain,
            credential.client_id,
            credential.client_secret,
            "http://localhost/not_used",
            "http://localhost/not_used",
        )
        self._display_name = credential.name or auth_domain

    @property
    def name(self) -> str:
        return self._display_name


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> _ApiKeyImplementation:
    """Return auth implementation for API key credentials."""
    return _ApiKeyImplementation(hass, auth_domain, credential)


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Hint text shown in the Application Credentials dialog."""
    return {
        "description": (
            "Enter your provider API key as **Client ID**. "
            "For NTA Ireland (two-key setup) enter the secondary key as **Client Secret**. "
            "Leave Client Secret empty for all other providers."
        )
    }
