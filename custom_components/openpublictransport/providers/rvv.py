"""RVV (Regensburger Verkehrsverbund) provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import PROVIDER_RVV
from .efa_base import EFABaseProvider


class RVVProvider(EFABaseProvider):
    """RVV (Regensburg) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_RVV

    @property
    def provider_name(self) -> str:
        return "RVV (Regensburg)"

    @property
    def dm_base_url(self) -> str:
        return "https://efa.rvv.de/efa/XML_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://efa.rvv.de/efa/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return {
            0: "train",  # High-speed trains (ICE, IC, EC)
            1: "train",  # Regional trains (RE, RB)
            5: "bus",  # City bus
            6: "bus",  # Regional bus
            7: "bus",  # Express bus
            8: "bus",  # Night bus
            13: "train",  # Regionalzug (RE)
        }

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: est != plan if est and plan else False
