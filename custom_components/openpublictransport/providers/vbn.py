"""VBN (Verkehrsverbund Bremen/Niedersachsen) provider — TRIAS interface."""

from typing import Optional

from homeassistant.core import HomeAssistant

from ..const import PROVIDER_VBN
from .trias_base import TRIASBaseProvider


class VBNProvider(TRIASBaseProvider):
    """VBN provider using TRIAS API (https://fahrplaner.vbn.de/triasproxy/).

    API key is passed as RequestorRef in every TRIAS XML request.
    Request a free key at api@vbn.de (3,000 transactions/day for hobbyists).
    """

    trias_base_url = "https://fahrplaner.vbn.de/triasproxy/"

    def __init__(self, hass: HomeAssistant, api_key: Optional[str] = None, api_key_secondary: Optional[str] = None):
        super().__init__(hass, api_key, api_key_secondary)
        if api_key:
            self.requestor_ref = api_key

    @property
    def provider_id(self) -> str:
        return PROVIDER_VBN

    @property
    def provider_name(self) -> str:
        return "VBN (Bremen/Niedersachsen)"

    @property
    def requires_api_key(self) -> bool:
        return True
