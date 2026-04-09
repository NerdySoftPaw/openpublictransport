"""VAG Freiburg provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import PROVIDER_VAGFR
from .efa_base import EFABaseProvider


class VAGFRProvider(EFABaseProvider):
    """VAG (Freiburg) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_VAGFR

    @property
    def provider_name(self) -> str:
        return "VAG (Freiburg)"

    @property
    def dm_base_url(self) -> str:
        return "https://efa.vagfr.de/vagfr3/XML_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://efa.vagfr.de/vagfr3/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return {
            0: "train",  # Fernverkehr
            1: "train",  # S-Bahn
            4: "tram",  # Straßenbahn
            5: "bus",  # Stadtbus
            6: "bus",  # Regionalbus
            7: "bus",  # Schnellbus
            8: "bus",  # Nachtbus
            13: "train",  # Regionalzug (RE/RB)
        }

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: est != plan if est and plan else False
