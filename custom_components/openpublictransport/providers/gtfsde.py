"""Community OTP2 provider — api.openpublictransport.net (GTFS.DE data, Germany-wide)."""

from .otp import OTPProvider


class OPTProvider(OTPProvider):
    """Community server at api.openpublictransport.net."""

    otp_base_url = "https://api.openpublictransport.net/otp/routers/default"

    @property
    def provider_id(self) -> str:
        return "openpublictransport"

    @property
    def provider_name(self) -> str:
        return "Deutschland (api.openpublictransport.net)"
