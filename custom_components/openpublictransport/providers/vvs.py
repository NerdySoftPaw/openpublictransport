"""VVS (Verkehrs- und Tarifverbund Stuttgart) provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import PROVIDER_VVS
from .efa_base import EFABaseProvider


class VVSProvider(EFABaseProvider):
    """VVS (Stuttgart) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_VVS

    @property
    def provider_name(self) -> str:
        return "VVS (Stuttgart)"

    @property
    def dm_base_url(self) -> str:
        return "https://www3.vvs.de/mngvvs/XML_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://www3.vvs.de/mngvvs/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return {
            0: "train",  # Fernverkehr (ICE, IC, EC)
            1: "train",  # S-Bahn
            2: "subway",  # Stadtbahn (SSB)
            3: "subway",  # Stadtbahn variant
            4: "tram",  # Tram
            5: "bus",  # Stadtbus
            6: "bus",  # Regionalbus
            7: "bus",  # Schnellbus
            8: "bus",  # Nachtbus
            9: "ferry",  # Fähre
            10: "taxi",  # Rufbus
            13: "train",  # Regionalzug (RE/RB)
        }

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: est != plan if est and plan else False
