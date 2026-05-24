"""Generic OTP2 provider for user-hosted instances.

Users supply their own OTP2 base URL (e.g. http://192.168.1.10:8080/otp/routers/default)
and an optional X-API-Key.  Stop search and departure logic are identical to the
community server — this is a thin subclass that sets no default URL.
"""

from .otp import OTPProvider


class OTPCustomProvider(OTPProvider):
    """User-provided OTP2 instance with configurable URL and optional API key."""

    otp_base_url = ""  # always overridden by self.custom_url set via constructor

    @property
    def provider_id(self) -> str:
        return "otp_custom"

    @property
    def provider_name(self) -> str:
        return "Custom OTP Server"
