"""VBN (Verkehrsverbund Bremen/Niedersachsen) providers."""

import aiohttp
from typing import Dict, Optional

from ..const import PROVIDER_VBN_OTP, PROVIDER_VBN_TRIAS
from .otp_base import OTPBaseProvider
from .trias_base import TRIASBaseProvider


class VBNOTPProvider(OTPBaseProvider):
    """VBN via OpenTripPlanner REST API (http://gtfsr.vbn.de/api/)."""

    otp_base_url = "http://gtfsr.vbn.de/api/routers/default"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: Optional[str] = None,
        api_key_secondary: Optional[str] = None,
        custom_url: Optional[str] = None,
    ) -> None:
        super().__init__(session, api_key, api_key_secondary)

    @property
    def provider_id(self) -> str:
        return PROVIDER_VBN_OTP

    @property
    def provider_name(self) -> str:
        return "VBN OTP (Bremen/Niedersachsen)"

    @property
    def requires_api_key(self) -> bool:
        return True

    def _auth_headers(self) -> Dict[str, str]:
        h = super()._auth_headers()
        if self.api_key:
            h["Authorization"] = self.api_key
        return h


class VBNTriasProvider(TRIASBaseProvider):
    """VBN via TRIAS XML API (https://fahrplaner.vbn.de/triasproxy/)."""

    trias_base_url = "https://fahrplaner.vbn.de/triasproxy/"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: Optional[str] = None,
        api_key_secondary: Optional[str] = None,
        custom_url: Optional[str] = None,
    ) -> None:
        super().__init__(session, api_key, api_key_secondary)

    @property
    def provider_id(self) -> str:
        return PROVIDER_VBN_TRIAS

    @property
    def provider_name(self) -> str:
        return "VBN TRIAS (Bremen/Niedersachsen)"

    @property
    def requires_api_key(self) -> bool:
        return True

    def _extra_headers(self) -> Dict[str, str]:
        if self.api_key:
            return {"Authorization": self.api_key}
        return {}
