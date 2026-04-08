"""Tests for provider modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.openpublictransport.const import PROVIDER_HVV, PROVIDER_KVV, PROVIDER_NTA_IE, PROVIDER_TRAFIKLAB_SE, PROVIDER_VRR
from custom_components.openpublictransport.providers import get_provider
from custom_components.openpublictransport.providers.hvv import HVVProvider
from custom_components.openpublictransport.providers.kvv import KVVProvider
from custom_components.openpublictransport.providers.nta import NTAProvider
from custom_components.openpublictransport.providers.trafiklab import TrafiklabProvider
from custom_components.openpublictransport.providers.vrr import VRRProvider


@pytest.fixture
def mock_hass():
    """Return a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    return hass


class TestProviderRegistry:
    """Test provider registry."""

    def test_get_provider_vrr(self, mock_hass):
        """Test getting VRR provider."""
        provider = get_provider(PROVIDER_VRR, mock_hass)
        assert provider is not None
        assert isinstance(provider, VRRProvider)
        assert provider.provider_id == PROVIDER_VRR

    def test_get_provider_kvv(self, mock_hass):
        """Test getting KVV provider."""
        provider = get_provider(PROVIDER_KVV, mock_hass)
        assert provider is not None
        assert isinstance(provider, KVVProvider)
        assert provider.provider_id == PROVIDER_KVV

    def test_get_provider_hvv(self, mock_hass):
        """Test getting HVV provider."""
        provider = get_provider(PROVIDER_HVV, mock_hass)
        assert provider is not None
        assert isinstance(provider, HVVProvider)
        assert provider.provider_id == PROVIDER_HVV

    def test_get_provider_trafiklab(self, mock_hass):
        """Test getting Trafiklab provider."""
        provider = get_provider(PROVIDER_TRAFIKLAB_SE, mock_hass, api_key="test_key")
        assert provider is not None
        assert isinstance(provider, TrafiklabProvider)
        assert provider.provider_id == PROVIDER_TRAFIKLAB_SE
        assert provider.requires_api_key is True

    def test_get_provider_nta(self, mock_hass):
        """Test getting NTA provider."""
        provider = get_provider(PROVIDER_NTA_IE, mock_hass, api_key="test_key")
        assert provider is not None
        assert isinstance(provider, NTAProvider)
        assert provider.provider_id == PROVIDER_NTA_IE
        assert provider.requires_api_key is True

    def test_get_provider_invalid(self, mock_hass):
        """Test getting invalid provider."""
        provider = get_provider("invalid_provider", mock_hass)
        assert provider is None


class TestVRRProvider:
    """Test VRR provider."""

    @pytest.fixture
    def provider(self, mock_hass):
        """Create VRR provider instance."""
        return VRRProvider(mock_hass)

    def test_provider_id(self, provider):
        """Test provider ID."""
        assert provider.provider_id == PROVIDER_VRR

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "VRR (NRW)"

    def test_timezone(self, provider):
        """Test timezone."""
        assert provider.get_timezone() == "Europe/Berlin"

    def test_requires_api_key(self, provider):
        """Test API key requirement."""
        assert provider.requires_api_key is False

    @pytest.mark.asyncio
    async def test_fetch_departures_success(self, provider, mock_hass):
        """Test successful departure fetch."""
        mock_response = {"stopEvents": [{"departureTimePlanned": "2025-01-15T10:00:00Z"}]}

        with patch("custom_components.openpublictransport.providers.vrr.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            result = await provider.fetch_departures("station123", "Düsseldorf", "Hauptbahnhof", 10)

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_fetch_departures_error(self, provider, mock_hass):
        """Test departure fetch with error."""
        with patch("custom_components.openpublictransport.providers.vrr.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 500

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            result = await provider.fetch_departures("station123", "Düsseldorf", "Hauptbahnhof", 10)

            assert result is None

    def test_parse_departure(self, provider):
        """Test departure parsing."""
        stop = {
            "departureTimePlanned": "2025-01-15T10:00:00+01:00",
            "departureTimeEstimated": "2025-01-15T10:05:00+01:00",
            "transportation": {
                "number": "U79",
                "destination": {"name": "Duisburg"},
                "product": {"class": 4},
            },
            "platform": {"name": "2"},
            "realtimeStatus": ["MONITORED"],
        }

        tz = dt_util.get_time_zone("Europe/Berlin")
        now = dt_util.parse_datetime("2025-01-15T09:55:00+01:00")

        departure = provider.parse_departure(stop, tz, now)

        assert departure is not None
        assert departure.line == "U79"
        assert departure.destination == "Duisburg"
        assert departure.delay == 5

    @pytest.mark.asyncio
    async def test_search_stops(self, provider, mock_hass):
        """Test stop search."""
        mock_response = {
            "locations": [{"id": "stop123", "name": "Hauptbahnhof", "disassembledName": "Hauptbahnhof, Düsseldorf"}]
        }

        with patch("custom_components.openpublictransport.providers.vrr.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            results = await provider.search_stops("Hauptbahnhof")

            assert len(results) == 1
            assert results[0]["id"] == "stop123"
            assert results[0]["name"] == "Hauptbahnhof"


class TestTrafiklabProvider:
    """Test Trafiklab provider."""

    @pytest.fixture
    def provider(self, mock_hass):
        """Create Trafiklab provider instance."""
        return TrafiklabProvider(mock_hass, api_key="test_key")

    def test_requires_api_key(self, provider):
        """Test API key requirement."""
        assert provider.requires_api_key is True

    def test_timezone(self, provider):
        """Test timezone."""
        assert provider.get_timezone() == "Europe/Stockholm"

    @pytest.mark.asyncio
    async def test_fetch_departures_success(self, provider, mock_hass):
        """Test successful departure fetch."""
        mock_response = {
            "departures": [
                {
                    "scheduled": "2025-01-15T10:00:00",
                    "realtime": "2025-01-15T10:05:00",
                    "route": {"designation": "123", "destination": {"name": "Stockholm"}},
                    "is_realtime": True,
                }
            ]
        }

        with patch("custom_components.openpublictransport.providers.trafiklab.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            result = await provider.fetch_departures("station123", "", "", 10)

            assert result is not None
            assert "stopEvents" in result
            assert len(result["stopEvents"]) == 1

    @pytest.mark.asyncio
    async def test_search_stops(self, provider, mock_hass):
        """Test stop search."""
        mock_response = {
            "stop_groups": [{"id": "stop123", "name": "Stockholm Central", "stops": [{"name": "Stockholm Central"}]}]
        }

        with patch("custom_components.openpublictransport.providers.trafiklab.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            results = await provider.search_stops("Stockholm")

            assert len(results) == 1
            assert results[0]["id"] == "stop123"


class TestKVVProvider:
    """Test KVV provider."""

    @pytest.fixture
    def provider(self, mock_hass):
        """Create KVV provider instance."""
        return KVVProvider(mock_hass)

    def test_provider_id(self, provider):
        """Test provider ID."""
        assert provider.provider_id == PROVIDER_KVV

    def test_timezone(self, provider):
        """Test timezone."""
        assert provider.get_timezone() == "Europe/Berlin"

    @pytest.mark.asyncio
    async def test_fetch_departures_success(self, provider, mock_hass):
        """Test successful departure fetch."""
        mock_response = {"stopEvents": [{"departureTimePlanned": "2025-01-15T10:00:00Z"}]}

        with patch("custom_components.openpublictransport.providers.kvv.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            result = await provider.fetch_departures("station123", "Karlsruhe", "Hauptbahnhof", 10)

            assert result == mock_response


class TestHVVProvider:
    """Test HVV provider."""

    @pytest.fixture
    def provider(self, mock_hass):
        """Create HVV provider instance."""
        return HVVProvider(mock_hass)

    def test_provider_id(self, provider):
        """Test provider ID."""
        assert provider.provider_id == PROVIDER_HVV

    def test_timezone(self, provider):
        """Test timezone."""
        assert provider.get_timezone() == "Europe/Berlin"

    @pytest.mark.asyncio
    async def test_fetch_departures_success(self, provider, mock_hass):
        """Test successful departure fetch."""
        mock_response = {"stopEvents": [{"departureTimePlanned": "2025-01-15T10:00:00Z"}]}

        with patch("custom_components.openpublictransport.providers.hvv.async_get_clientsession") as mock_session:
            mock_response_obj = MagicMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            result = await provider.fetch_departures("station123", "Hamburg", "Hauptbahnhof", 10)

            assert result == mock_response
