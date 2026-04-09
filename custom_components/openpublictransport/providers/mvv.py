"""MVV (Münchner Verkehrs- und Tarifverbund) provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import PROVIDER_MVV
from .efa_base import EFABaseProvider


class MVVProvider(EFABaseProvider):
    """MVV (München) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_MVV

    @property
    def provider_name(self) -> str:
        return "MVV (München)"

    @property
    def dm_base_url(self) -> str:
        return "https://efa.mvv-muenchen.de/ng/XML_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://efa.mvv-muenchen.de/ng/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return {
            0: "train",  # Fernverkehr (ICE, IC, EC)
            1: "train",  # S-Bahn
            2: "subway",  # U-Bahn
            3: "subway",  # U-Bahn variant
            4: "tram",  # Tram
            5: "bus",  # Stadtbus
            6: "bus",  # Regionalbus
            7: "bus",  # Schnellbus
            8: "bus",  # Nachtbus
            9: "ferry",  # Fähre
            10: "taxi",  # Rufbus/Taxi
            13: "train",  # Regionalzug (RE/RB)
        }

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: est != plan if est and plan else False
