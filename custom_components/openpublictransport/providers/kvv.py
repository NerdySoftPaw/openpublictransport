"""KVV (Karlsruher Verkehrsverbund) provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import KVV_TRANSPORTATION_TYPES, PROVIDER_KVV
from .efa_base import EFABaseProvider


class KVVProvider(EFABaseProvider):
    """KVV (Karlsruher Verkehrsverbund) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_KVV

    @property
    def provider_name(self) -> str:
        return "KVV (Karlsruhe)"

    @property
    def dm_base_url(self) -> str:
        return "https://projekte.kvv-efa.de/sl3-alone/XSLT_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://projekte.kvv-efa.de/sl3-alone/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return KVV_TRANSPORTATION_TYPES

    def get_platform_fn(self) -> Callable[[Dict[str, Any]], str]:
        return lambda s: s.get("location", {}).get("disassembledName") or s.get("platformName", "")

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: s.get("isRealtimeControlled", False)
