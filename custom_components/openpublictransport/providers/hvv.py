"""HVV (Hamburger Verkehrsverbund) provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import HVV_TRANSPORTATION_TYPES, PROVIDER_HVV
from .efa_base import EFABaseProvider


class HVVProvider(EFABaseProvider):
    """HVV (Hamburger Verkehrsverbund) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_HVV

    @property
    def provider_name(self) -> str:
        return "HVV (Hamburg)"

    @property
    def dm_base_url(self) -> str:
        return "https://hvv.efa.de/efa/XML_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://hvv.efa.de/efa/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return HVV_TRANSPORTATION_TYPES

    def get_platform_fn(self) -> Callable[[Dict[str, Any]], str]:
        return lambda s: (
            s.get("location", {}).get("properties", {}).get("platform") or s.get("location", {}).get("platformName", "")
        )

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: est != plan if est and plan else False
