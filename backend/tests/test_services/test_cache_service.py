"""
Tests for CacheService (backend/app/core/cache.py).

F-033: Covers memory fallback when Redis is unavailable, TTL expiration,
cache invalidation, and cleanup_memory() expired entry eviction.
"""

import time

import pytest

from app.core.cache import CacheService, _memory_cache, make_cache_key, make_cache_key_from_params


@pytest.fixture(autouse=True)
def _clear_memory_cache():
    """Ensure a clean memory cache for every test."""
    _memory_cache.clear()
    yield
    _memory_cache.clear()


def _make_service() -> CacheService:
    """Create a fresh CacheService with no Redis (memory fallback)."""
    svc = CacheService()
    # Mark init as attempted with no Redis available
    svc._init_attempted = True
    svc._redis = None
    return svc


# ---------------------------------------------------------------------------
# Memory fallback — basic get/set/delete
# ---------------------------------------------------------------------------


async def test_memory_fallback_set_and_get():
    """Values stored via set() should be retrievable via get()."""
    svc = _make_service()
    await svc.set("hello", {"foo": "bar"}, ttl=60)
    result = await svc.get("hello")
    assert result == {"foo": "bar"}


async def test_memory_fallback_get_miss():
    """get() returns None for a key that was never set."""
    svc = _make_service()
    result = await svc.get("nonexistent")
    assert result is None


async def test_memory_fallback_delete():
    """delete() removes a key from the memory cache."""
    svc = _make_service()
    await svc.set("del_me", "value", ttl=60)
    assert await svc.get("del_me") == "value"

    await svc.delete("del_me")
    assert await svc.get("del_me") is None


async def test_memory_fallback_delete_nonexistent():
    """delete() on a missing key should not raise."""
    svc = _make_service()
    await svc.delete("does_not_exist")  # should not raise


# ---------------------------------------------------------------------------
# TTL expiration
# ---------------------------------------------------------------------------


async def test_ttl_expiration():
    """Entries with a short TTL should expire and return None."""
    svc = _make_service()
    # Set with 1-second TTL
    await svc.set("expires_fast", "data", ttl=1)
    assert await svc.get("expires_fast") == "data"

    # Manually expire by backdating the entry
    full_key = "dashboard:expires_fast"
    raw, _ = _memory_cache[full_key]
    _memory_cache[full_key] = (raw, time.time() - 1)

    assert await svc.get("expires_fast") is None


async def test_non_expired_entry_still_accessible():
    """Entries with remaining TTL should be accessible."""
    svc = _make_service()
    await svc.set("still_alive", [1, 2, 3], ttl=3600)
    assert await svc.get("still_alive") == [1, 2, 3]


# ---------------------------------------------------------------------------
# Cache invalidation (pattern-based)
# ---------------------------------------------------------------------------


async def test_invalidate_pattern_trailing_wildcard():
    """invalidate_pattern('property_*') removes matching keys."""
    svc = _make_service()
    await svc.set("property_list", "a", ttl=60)
    await svc.set("property_dashboard:1", "b", ttl=60)
    await svc.set("deal_stats:30", "c", ttl=60)

    count = await svc.invalidate_pattern("property_*")
    assert count == 2
    assert await svc.get("property_list") is None
    assert await svc.get("property_dashboard:1") is None
    # Unrelated key should still be present
    assert await svc.get("deal_stats:30") == "c"


async def test_invalidate_pattern_no_matches():
    """invalidate_pattern with no matching keys returns 0."""
    svc = _make_service()
    await svc.set("keep_me", "yes", ttl=60)
    count = await svc.invalidate_pattern("zzz_*")
    assert count == 0
    assert await svc.get("keep_me") == "yes"


async def test_invalidate_properties():
    """invalidate_properties() removes property + portfolio + analytics keys."""
    svc = _make_service()
    await svc.set("property_list", "a", ttl=60)
    await svc.set("portfolio_summary", "b", ttl=60)
    await svc.set("analytics_dashboard", "c", ttl=60)
    await svc.set("deal_stats:7", "d", ttl=60)

    count = await svc.invalidate_properties()
    assert count >= 3
    assert await svc.get("property_list") is None
    assert await svc.get("portfolio_summary") is None
    assert await svc.get("analytics_dashboard") is None
    # Deal key should survive
    assert await svc.get("deal_stats:7") == "d"


async def test_invalidate_deals():
    """invalidate_deals() removes deal + analytics keys."""
    svc = _make_service()
    await svc.set("deal_stats:7", "a", ttl=60)
    await svc.set("deal_list", "b", ttl=60)
    await svc.set("analytics_dashboard", "c", ttl=60)
    await svc.set("property_list", "d", ttl=60)

    count = await svc.invalidate_deals()
    assert count >= 3
    assert await svc.get("deal_stats:7") is None
    assert await svc.get("deal_list") is None
    assert await svc.get("analytics_dashboard") is None
    # Property key should survive
    assert await svc.get("property_list") == "d"


# ---------------------------------------------------------------------------
# cleanup_memory() — expired entry eviction
# ---------------------------------------------------------------------------


def test_cleanup_memory_removes_expired():
    """cleanup_memory() evicts entries whose TTL has passed."""
    svc = _make_service()
    now = time.time()

    # Insert entries directly into the module-level dict
    _memory_cache["dashboard:expired1"] = ('{"x":1}', now - 10)
    _memory_cache["dashboard:expired2"] = ('{"x":2}', now - 1)
    _memory_cache["dashboard:alive"] = ('{"x":3}', now + 3600)

    removed = svc.cleanup_memory()
    assert removed == 2
    assert "dashboard:expired1" not in _memory_cache
    assert "dashboard:expired2" not in _memory_cache
    assert "dashboard:alive" in _memory_cache


def test_cleanup_memory_nothing_expired():
    """cleanup_memory() returns 0 when nothing is expired."""
    svc = _make_service()
    _memory_cache["dashboard:fresh"] = ('{"a":1}', time.time() + 9999)

    removed = svc.cleanup_memory()
    assert removed == 0


# ---------------------------------------------------------------------------
# get_stats()
# ---------------------------------------------------------------------------


async def test_get_stats_memory_backend():
    """get_stats() reports 'memory' backend when Redis is unavailable."""
    svc = _make_service()
    await svc.set("k1", "v1", ttl=60)
    await svc.set("k2", "v2", ttl=60)

    stats = await svc.get_stats()
    assert stats["backend"] == "memory"
    assert stats["memory_entries"] >= 2


async def test_is_redis_available_false():
    """is_redis_available returns False when Redis is not connected."""
    svc = _make_service()
    assert svc.is_redis_available is False


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def test_make_cache_key():
    """make_cache_key joins parts with colons."""
    assert make_cache_key("property_list", "multifamily", "1") == "property_list:multifamily:1"


def test_make_cache_key_filters_empty():
    """make_cache_key skips empty parts."""
    assert make_cache_key("prefix", "", "suffix") == "prefix:suffix"


def test_make_cache_key_from_params_no_params():
    """make_cache_key_from_params returns just the prefix when no params."""
    assert make_cache_key_from_params("property_list") == "property_list"


def test_make_cache_key_from_params_with_params():
    """make_cache_key_from_params produces a deterministic hash-suffixed key."""
    key1 = make_cache_key_from_params("list", page=1, type="multifamily")
    key2 = make_cache_key_from_params("list", type="multifamily", page=1)
    assert key1 == key2
    assert key1.startswith("list:")


def test_make_cache_key_from_params_skips_none():
    """None-valued params are filtered out."""
    key = make_cache_key_from_params("prefix", a=None, b=None)
    assert key == "prefix"


# ---------------------------------------------------------------------------
# Complex value serialization
# ---------------------------------------------------------------------------


async def test_complex_value_roundtrip():
    """Nested dicts and lists survive JSON serialization."""
    svc = _make_service()
    value = {
        "properties": [{"id": 1, "name": "Test"}],
        "total": 1,
        "nested": {"deep": True},
    }
    await svc.set("complex", value, ttl=60)
    result = await svc.get("complex")
    assert result == value
