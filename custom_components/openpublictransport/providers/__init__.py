"""Provider registry and factory."""

from typing import Dict, Optional, Type

from homeassistant.core import HomeAssistant

from ..const import (
    PROVIDER_AVV_AUGSBURG,
    PROVIDER_BEG,
    PROVIDER_BSVG,
    PROVIDER_BVG,
    PROVIDER_DB,
    PROVIDER_DING,
    PROVIDER_HVV,
    PROVIDER_KVV,
    PROVIDER_MVV,
    PROVIDER_NTA_IE,
    PROVIDER_NVBW,
    PROVIDER_NWL,
    PROVIDER_OEBB,
    PROVIDER_RMV,
    PROVIDER_RVV,
    PROVIDER_SBB,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_TRANSITOUS,
    PROVIDER_VAGFR,
    PROVIDER_VGN,
    PROVIDER_VRN,
    PROVIDER_VRR,
    PROVIDER_VVO,
    PROVIDER_VVS,
)
from .avv import AVVProvider
from .base import BaseProvider
from .beg import BEGProvider
from .bsvg import BSVGProvider
from .bvg import BVGProvider
from .db import DBProvider
from .ding import DINGProvider
from .hvv import HVVProvider
from .kvv import KVVProvider
from .mvv import MVVProvider
from .nta import NTAProvider
from .nvbw import NVBWProvider
from .nwl import NWLProvider
from .oebb import OeBBProvider
from .rmv import RMVProvider
from .rvv import RVVProvider
from .sbb import SBBProvider
from .trafiklab import TrafiklabProvider
from .transitous import TransitousProvider
from .vagfr import VAGFRProvider
from .vgn import VGNProvider
from .vrn import VRNProvider
from .vrr import VRRProvider
from .vvo import VVOProvider
from .vvs import VVSProvider

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
register_provider(PROVIDER_BVG, BVGProvider)
register_provider(PROVIDER_MVV, MVVProvider)
register_provider(PROVIDER_VVS, VVSProvider)
register_provider(PROVIDER_VGN, VGNProvider)
register_provider(PROVIDER_VAGFR, VAGFRProvider)
register_provider(PROVIDER_RMV, RMVProvider)
register_provider(PROVIDER_TRAFIKLAB_SE, TrafiklabProvider)
register_provider(PROVIDER_NTA_IE, NTAProvider)
register_provider(PROVIDER_VRN, VRNProvider)
register_provider(PROVIDER_VVO, VVOProvider)
register_provider(PROVIDER_DING, DINGProvider)
register_provider(PROVIDER_AVV_AUGSBURG, AVVProvider)
register_provider(PROVIDER_RVV, RVVProvider)
register_provider(PROVIDER_BSVG, BSVGProvider)
register_provider(PROVIDER_NWL, NWLProvider)
register_provider(PROVIDER_NVBW, NVBWProvider)
register_provider(PROVIDER_BEG, BEGProvider)
register_provider(PROVIDER_SBB, SBBProvider)
register_provider(PROVIDER_OEBB, OeBBProvider)
register_provider(PROVIDER_TRANSITOUS, TransitousProvider)
register_provider(PROVIDER_DB, DBProvider)
