"""VRR (Verkehrsverbund Rhein-Ruhr) provider implementation."""

from typing import Any, Callable, Dict, Optional

from ..const import PROVIDER_VRR
from .efa_base import EFABaseProvider


class VRRProvider(EFABaseProvider):
    """VRR (Verkehrsverbund Rhein-Ruhr) provider."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_VRR

    @property
    def provider_name(self) -> str:
        return "VRR (NRW)"

    @property
    def dm_base_url(self) -> str:
        return "https://openservice-test.vrr.de/static03/XML_DM_REQUEST"

    @property
    def sf_base_url(self) -> str:
        return "https://openservice-test.vrr.de/static03/XML_STOPFINDER_REQUEST"

    def get_timezone(self) -> str:
        return "Europe/Berlin"

    def get_transport_type_mapping(self) -> Dict[Any, str]:
        return {
            0: "train",  # High-speed trains (ICE, IC, EC)
            1: "train",  # Regional trains (RE, RB)
            2: "subway",  # U-Bahn
            3: "subway",  # U-Bahn variant
            4: "tram",  # Tram/Streetcar
            5: "bus",  # City bus
            6: "bus",  # Regional bus
            7: "bus",  # Express bus
            8: "bus",  # Night bus
            9: "ferry",  # Ferry/Ship
            10: "taxi",  # Taxi
            11: "bus",  # Other/Special transport
            13: "train",  # Regionalzug (RE)
            15: "train",  # InterCity (IC)
            16: "train",  # InterCityExpress (ICE)
        }

    def get_realtime_fn(self) -> Callable[[Dict[str, Any], Optional[str], Optional[str]], bool]:
        return lambda s, est, plan: "MONITORED" in s.get("realtimeStatus", [])
