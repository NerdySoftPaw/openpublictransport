"""Deutsche Bahn provider implementation.

Uses the v6.db.transport.rest API (FPTF format).
No API key required.

NOTE: This API is a community-maintained proxy (by derhuerst).
It is free and open but not officially supported by Deutsche Bahn.
Availability is not guaranteed — the API may experience occasional downtime.
"""

from ..const import PROVIDER_DB
from .fptf_base import FPTFBaseProvider


class DBProvider(FPTFBaseProvider):
    """Deutsche Bahn provider using v6.db.transport.rest API."""

    API_BASE = "https://v6.db.transport.rest"

    PRODUCT_MAPPING = {
        "nationalExpress": "train",  # ICE
        "national": "train",  # IC/EC
        "regionalExpress": "train",  # RE
        "regional": "train",  # RB
        "suburban": "train",  # S-Bahn
        "subway": "subway",  # U-Bahn
        "tram": "tram",
        "bus": "bus",
        "ferry": "ferry",
        "taxi": "taxi",
    }

    @property
    def provider_id(self) -> str:
        return PROVIDER_DB

    @property
    def provider_name(self) -> str:
        return "DB (Deutsche Bahn)"
