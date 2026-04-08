"""Provider registry and factory."""

from typing import Dict, Optional, Type

from homeassistant.core import HomeAssistant

from ..const import PROVIDER_HVV, PROVIDER_KVV, PROVIDER_NTA_IE, PROVIDER_TRAFIKLAB_SE, PROVIDER_VRR
from .base import BaseProvider
from .hvv import HVVProvider
from .kvv import KVVProvider
from .nta import NTAProvider
from .trafiklab import TrafiklabProvider
from .vrr import VRRProvider

_PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {}


def register_provider(provider_id: str, provider_class: Type[BaseProvider]) -> None:
    """Register a provider class."""
    _PROVIDER_REGISTRY[provider_id] = provider_class


def get_provider(
    provider_id: Optional[str],
    hass: HomeAssistant,
    api_key: Optional[str] = None,
    api_key_secondary: Optional[str] = None,
) -> Optional[BaseProvider]:
    """Get a provider instance by ID."""
    if provider_id is None:
        return None
    provider_class = _PROVIDER_REGISTRY.get(provider_id)
    if provider_class:
        return provider_class(hass, api_key=api_key, api_key_secondary=api_key_secondary)
    return None


def get_all_provider_ids() -> list[str]:
    """Get all registered provider IDs."""
    return list(_PROVIDER_REGISTRY.keys())


# Register all providers
register_provider(PROVIDER_VRR, VRRProvider)
register_provider(PROVIDER_KVV, KVVProvider)
register_provider(PROVIDER_HVV, HVVProvider)
register_provider(PROVIDER_TRAFIKLAB_SE, TrafiklabProvider)
register_provider(PROVIDER_NTA_IE, NTAProvider)
