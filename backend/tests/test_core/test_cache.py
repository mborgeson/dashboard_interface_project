"""Tests for CacheService in-memory fallback.

F-033: Tests the CacheService from app.core.cache including:
- In-memory fallback when Redis is unavailable
- TTL expiration
- get/set/delete operations
- Cleanup of expired entries
"""

import time
from unittest.mock import patch

import pytest

from app.core.cache import (
    CacheService,
    _memory_cache,
    make_cache_key,
    make_cache_key_from_params,
)


@pytest.fixture(autouse=True)
def clear_memory_cache():
    """Ensure a clean memory cache for each test."""
    _memory_cache.clear()
    yield
    _memory_cache.clear()


def _make_service() -> CacheService:
    """Create a CacheService that will use memory fallback (no Redis)."""
    svc = CacheService()
    # Mark init as attempted so it won't try to connect to Redis
    svc._init_attempted = True
    svc._redis = None
    return svc


# =============================================================================
# In-memory fallback (no Redis)
# =============================================================================


@pytest.mark.asyncio
async def test_memory_fallback_when_no_redis():
    """CacheService should use in-memory store when Redis is unavailable."""
    svc = _make_service()
    assert svc.is_redis_available is False

    await svc.set("test_key", {"value": 42})
    result = await svc.get("test_key")
    assert result == {"value": 42}


@pytest.mark.asyncio
async def test_ensure_redis_skips_when_no_url():
    """_ensure_redis should fall back to memory when REDIS_URL is empty."""
    svc = CacheService()
    with patch("app.core.cache.settings") as mock_settings:
        mock_settings.REDIS_URL = ""
        await svc._ensure_redis()
    assert svc._redis is None
    assert svc._init_attempted is True


# =============================================================================
# get / set / delete
# =============================================================================


@pytest.mark.asyncio
async def test_set_and_get():
    """Test basic set then get returns the stored value."""
    svc = _make_service()
    await svc.set("hello", "world", ttl=60)
    result = await svc.get("hello")
    assert result == "world"


@pytest.mark.asyncio
async def test_get_missing_key_returns_none():
    """Getting a key that was never set should return None."""
    svc = _make_service()
    result = await svc.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_set_overwrite():
    """Setting the same key twice should overwrite the previous value."""
    svc = _make_service()
    await svc.set("key", "first")
    await svc.set("key", "second")
    result = await svc.get("key")
    assert result == "second"


@pytest.mark.asyncio
async def test_delete():
    """Deleting a key should make it return None on get."""
    svc = _make_service()
    await svc.set("to_delete", {"data": True})
    await svc.delete("to_delete")
    result = await svc.get("to_delete")
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_key():
    """Deleting a key that doesn't exist should not raise."""
    svc = _make_service()
    await svc.delete("never_set")  # Should not raise


@pytest.mark.asyncio
async def test_set_complex_value():
    """Test that complex JSON-serializable objects round-trip correctly."""
    svc = _make_service()
    data = {"properties": [{"id": 1, "name": "Test"}], "total": 1}
    await svc.set("complex", data, ttl=60)
    result = await svc.get("complex")
    assert result == data


# =============================================================================
# TTL expiration
# =============================================================================


@pytest.mark.asyncio
async def test_ttl_expiration():
    """Entries should expire after TTL seconds.

    T-DEBT-014: Uses direct timestamp manipulation instead of time.sleep()
    to avoid slow, non-deterministic synchronization.
    """
    svc = _make_service()
    # Set with 60-second TTL
    await svc.set("expiring", "value", ttl=60)

    # Should exist immediately
    result = await svc.get("expiring")
    assert result == "value"

    # Directly set the expiry timestamp to the past instead of sleeping
    full_key = "dashboard:expiring"
    stored_value, _old_expiry = _memory_cache[full_key]
    _memory_cache[full_key] = (stored_value, time.time() - 1)

    # Should be gone now (expired)
    result = await svc.get("expiring")
    assert result is None


@pytest.mark.asyncio
async def test_ttl_not_expired():
    """Entries should still be available before TTL expires."""
    svc = _make_service()
    await svc.set("still_alive", "present", ttl=60)
    result = await svc.get("still_alive")
    assert result == "present"


# =============================================================================
# Cleanup of expired entries
# =============================================================================


def test_cleanup_memory_removes_expired():
    """cleanup_memory should remove all expired entries."""
    svc = _make_service()
    # Manually insert expired entries into the memory cache
    now = time.time()
    _memory_cache["dashboard:expired1"] = ('{"v":1}', now - 10)
    _memory_cache["dashboard:expired2"] = ('{"v":2}', now - 5)
    _memory_cache["dashboard:still_valid"] = ('{"v":3}', now + 300)

    removed = svc.cleanup_memory()
    assert removed == 2
    assert "dashboard:expired1" not in _memory_cache
    assert "dashboard:expired2" not in _memory_cache
    assert "dashboard:still_valid" in _memory_cache


def test_cleanup_memory_no_expired():
    """cleanup_memory should return 0 when nothing is expired."""
    svc = _make_service()
    _memory_cache["dashboard:alive"] = ('{"v":1}', time.time() + 300)

    removed = svc.cleanup_memory()
    assert removed == 0


# =============================================================================
# Invalidate pattern
# =============================================================================


@pytest.mark.asyncio
async def test_invalidate_pattern():
    """invalidate_pattern should delete matching keys from memory cache."""
    svc = _make_service()
    await svc.set("property_1", "a", ttl=60)
    await svc.set("property_2", "b", ttl=60)
    await svc.set("deal_1", "c", ttl=60)

    count = await svc.invalidate_pattern("property_*")
    assert count == 2

    # Property keys gone
    assert await svc.get("property_1") is None
    assert await svc.get("property_2") is None
    # Deal key still present
    assert await svc.get("deal_1") == "c"


# =============================================================================
# get_stats
# =============================================================================


@pytest.mark.asyncio
async def test_get_stats_memory_backend():
    """get_stats should report memory backend and entry count."""
    svc = _make_service()
    await svc.set("stat_key", "val", ttl=60)

    stats = await svc.get_stats()
    assert stats["backend"] == "memory"
    assert stats["memory_entries"] >= 1


# =============================================================================
# Helper functions
# =============================================================================


def test_make_cache_key():
    """make_cache_key should join parts with colons."""
    key = make_cache_key("property_list", "multifamily", "1")
    assert key == "property_list:multifamily:1"


def test_make_cache_key_filters_empty():
    """make_cache_key should skip empty parts."""
    key = make_cache_key("prefix", "", "suffix")
    assert key == "prefix:suffix"


def test_make_cache_key_from_params():
    """make_cache_key_from_params should produce deterministic keys."""
    key1 = make_cache_key_from_params("test", page=1, type="multifamily")
    key2 = make_cache_key_from_params("test", type="multifamily", page=1)
    assert key1 == key2
    assert key1.startswith("test:")


def test_make_cache_key_from_params_no_params():
    """make_cache_key_from_params with no params returns just the prefix."""
    key = make_cache_key_from_params("prefix")
    assert key == "prefix"


def test_make_cache_key_from_params_all_none():
    """make_cache_key_from_params with all None values returns just the prefix."""
    key = make_cache_key_from_params("prefix", a=None, b=None)
    assert key == "prefix"
