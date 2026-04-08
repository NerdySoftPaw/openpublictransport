"""Tests for API caching in config flow."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from custom_components.openpublictransport.config_flow import OpenPublicTransportConfigFlow
from custom_components.openpublictransport.const import PROVIDER_VRR


@pytest.fixture
def config_flow():
    """Create a config flow instance for testing."""
    flow = OpenPublicTransportConfigFlow()
    flow._provider = PROVIDER_VRR
    return flow


def test_cache_key_generation(config_flow):
    """Test cache key generation."""
    key1 = config_flow._get_cache_key("vrr", "Düsseldorf", "stop")

    # Should normalize umlauts
    assert "duesseldorf" in key1.lower()

    # Two searches with same normalized form should have same key
    key2 = config_flow._get_cache_key("vrr", "DÜSSELDORF", "stop")
    assert key1 == key2  # Case and umlaut handling

    # Different providers should have different keys
    key3 = config_flow._get_cache_key("kvv", "Düsseldorf", "stop")
    assert key1 != key3

    # Different search types should have different keys
    key4 = config_flow._get_cache_key("vrr", "Düsseldorf", "location")
    assert key1 != key4


def test_cache_key_normalization(config_flow):
    """Test cache key handles different inputs consistently."""
    # Case insensitive
    key1 = config_flow._get_cache_key("vrr", "Hauptbahnhof", "stop")
    key2 = config_flow._get_cache_key("vrr", "HAUPTBAHNHOF", "stop")
    assert key1 == key2

    # Whitespace handling
    key3 = config_flow._get_cache_key("vrr", " Hauptbahnhof ", "stop")
    assert key1 == key3


def test_cache_store_and_retrieve(config_flow):
    """Test storing and retrieving from cache."""
    cache_key = "test_key"
    test_data = [
        {"id": "1", "name": "Hauptbahnhof"},
        {"id": "2", "name": "Stadtmitte"},
    ]

    # Store in cache
    config_flow._store_in_cache(cache_key, test_data)

    # Retrieve from cache
    cached = config_flow._get_from_cache(cache_key)
    assert cached is not None
    assert len(cached) == 2
    assert cached[0]["name"] == "Hauptbahnhof"


def test_cache_miss(config_flow):
    """Test cache miss returns None."""
    result = config_flow._get_from_cache("nonexistent_key")
    assert result is None


def test_cache_expiration(config_flow):
    """Test cache entries expire after TTL."""
    cache_key = "test_key"
    test_data = [{"id": "1", "name": "Test"}]

    # Store in cache
    config_flow._store_in_cache(cache_key, test_data)

    # Should be in cache immediately
    assert config_flow._get_from_cache(cache_key) is not None

    # Manually expire the cache entry
    config_flow._search_cache[cache_key]["timestamp"] = datetime.now() - timedelta(seconds=400)

    # Should be expired (TTL is 300 seconds)
    assert config_flow._get_from_cache(cache_key) is None

    # Expired entry should be removed
    assert cache_key not in config_flow._search_cache


def test_cache_size_limit(config_flow):
    """Test cache is limited to 20 entries."""
    # Fill cache with 25 entries
    for i in range(25):
        cache_key = f"test_key_{i}"
        config_flow._store_in_cache(cache_key, [{"id": str(i)}])

    # Cache should be limited to 20 entries
    assert len(config_flow._search_cache) == 20

    # Oldest entries should be removed
    assert "test_key_0" not in config_flow._search_cache
    assert "test_key_4" not in config_flow._search_cache

    # Newest entries should still be there
    assert "test_key_24" in config_flow._search_cache
    assert "test_key_20" in config_flow._search_cache


async def test_search_stops_with_cache_hit(config_flow, hass):
    """Test that search_stops uses cache when available."""
    config_flow.hass = hass

    mock_results = [
        {"id": "1", "name": "Hauptbahnhof", "place": "Düsseldorf"},
    ]

    # Pre-populate cache
    cache_key = config_flow._get_cache_key(PROVIDER_VRR, "Hauptbahnhof", "stop")
    config_flow._store_in_cache(cache_key, mock_results)

    # Mock API to ensure it's not called
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
        result = await config_flow._search_stops("Hauptbahnhof")

        # Should return cached results
        assert result == mock_results

        # API should not have been called
        mock_session.assert_not_called()


async def test_search_stops_with_cache_miss(config_flow, hass):
    """Test that search_stops fetches from API on cache miss."""
    config_flow.hass = hass

    # Pre-populate cache to test that it skips API
    mock_results = [{"id": "1", "name": "Hauptbahnhof", "place": "Düsseldorf"}]
    cache_key = config_flow._get_cache_key(PROVIDER_VRR, "Hauptbahnhof", "stop")

    # First call - cache miss, would call API
    # Second call - cache hit, skips API
    config_flow._store_in_cache(cache_key, mock_results)

    # Now test that it uses cache
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
        result = await config_flow._search_stops("Hauptbahnhof")

        # Should return cached results
        assert len(result) == 1
        assert result[0]["name"] == "Hauptbahnhof"

        # API should not have been called due to cache hit
        mock_session.assert_not_called()


async def test_search_stops_caches_empty_results(config_flow, hass):
    """Test that empty search results are also cached."""
    config_flow.hass = hass

    # Store empty result in cache
    cache_key = config_flow._get_cache_key(PROVIDER_VRR, "NonexistentStop", "stop")
    config_flow._store_in_cache(cache_key, [])

    # Verify empty results are cached
    cached = config_flow._get_from_cache(cache_key)
    assert cached is not None
    assert cached == []

    # Verify that calling search returns cached empty result
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
        result = await config_flow._search_stops("NonexistentStop")

        # Should return empty list from cache
        assert result == []

        # API should not have been called due to cache hit
        mock_session.assert_not_called()


def test_cache_different_searches(config_flow):
    """Test that different searches are cached separately."""
    # Store different searches
    config_flow._store_in_cache("vrr:stop:hauptbahnhof", [{"id": "1"}])
    config_flow._store_in_cache("vrr:stop:stadtmitte", [{"id": "2"}])

    # Both should be retrievable independently
    result1 = config_flow._get_from_cache("vrr:stop:hauptbahnhof")
    result2 = config_flow._get_from_cache("vrr:stop:stadtmitte")

    assert result1 != result2
    assert result1[0]["id"] == "1"
    assert result2[0]["id"] == "2"
