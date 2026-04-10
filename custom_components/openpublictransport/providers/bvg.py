"""BVG (Berliner Verkehrsbetriebe) provider implementation.

Uses the v6.vbb.transport.rest API (FPTF format).
No API key required.
"""

from ..const import PROVIDER_BVG
from .fptf_base import FPTFBaseProvider


class BVGProvider(FPTFBaseProvider):
    """BVG (Berlin) provider using VBB REST API."""

    API_BASE = "https://v6.vbb.transport.rest"

    PRODUCT_MAPPING = {
        "subway": "subway",
        "suburban": "train",
        "tram": "tram",
        "bus": "bus",
        "ferry": "ferry",
        "express": "train",
        "regional": "train",
    }

    @property
    def provider_id(self) -> str:
        return PROVIDER_BVG

    @property
    def provider_name(self) -> str:
        return "BVG (Berlin)"
