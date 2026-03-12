"""Tests for token blacklist TTL eviction (A-TD-016).

Covers:
- Lazy eviction triggers when memory store exceeds high-water mark
- Eviction during add() and is_blacklisted() paths
- High-water mark threshold behavior
"""

import time

import pytest

from app.core.token_blacklist import (
    _EVICTION_HIGH_WATER,
    TokenBlacklist,
    _memory_blacklist,
)


@pytest.fixture(autouse=True)
def clean_memory_blacklist():
    """Clear in-memory blacklist before and after each test."""
    _memory_blacklist.clear()
    yield
    _memory_blacklist.clear()


@pytest.fixture
def blacklist(monkeypatch):
    """Create a fresh TokenBlacklist instance (no Redis)."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "REDIS_URL", "")
    bl = TokenBlacklist()
    bl._redis = None
    return bl


def test_eviction_high_water_mark_is_reasonable():
    """High-water mark should be a positive integer (default 1000)."""
    assert _EVICTION_HIGH_WATER > 0
    assert _EVICTION_HIGH_WATER == 1000


def test_maybe_evict_does_nothing_below_threshold(blacklist):
    """_maybe_evict should not run cleanup when below high-water mark."""
    # Add a few expired entries below the threshold
    now = time.time()
    _memory_blacklist["expired-1"] = now - 10
    _memory_blacklist["expired-2"] = now - 5
    _memory_blacklist["active-1"] = now + 300

    # _maybe_evict should not clean up because we're well below the threshold
    blacklist._maybe_evict()

    # Expired entries should still be present (not swept yet)
    assert "expired-1" in _memory_blacklist
    assert "expired-2" in _memory_blacklist
    assert "active-1" in _memory_blacklist


def test_maybe_evict_runs_above_threshold(blacklist):
    """_maybe_evict should run cleanup when above high-water mark."""
    now = time.time()

    # Fill the store above the high-water mark with expired entries
    for i in range(_EVICTION_HIGH_WATER + 10):
        _memory_blacklist[f"token-{i}"] = now - 1  # All expired

    # Add one active entry
    _memory_blacklist["active"] = now + 300

    assert len(_memory_blacklist) > _EVICTION_HIGH_WATER

    blacklist._maybe_evict()

    # All expired entries should have been evicted
    assert len(_memory_blacklist) == 1
    assert "active" in _memory_blacklist


@pytest.mark.asyncio
async def test_eviction_during_add(blacklist):
    """Adding a token should trigger eviction when above high-water mark."""
    now = time.time()

    # Fill store above threshold with expired entries
    for i in range(_EVICTION_HIGH_WATER + 5):
        _memory_blacklist[f"expired-{i}"] = now - 1

    # Add a new token -- this should trigger eviction first
    await blacklist.add("new-token", expires_in=300)

    # Expired entries should have been cleaned, only new-token remains
    assert "new-token" in _memory_blacklist
    assert len(_memory_blacklist) == 1


@pytest.mark.asyncio
async def test_eviction_during_is_blacklisted(blacklist):
    """Checking a token should trigger eviction when above high-water mark."""
    now = time.time()

    # Fill store above threshold with expired entries
    for i in range(_EVICTION_HIGH_WATER + 5):
        _memory_blacklist[f"expired-{i}"] = now - 1

    # Add one active entry that we'll check
    _memory_blacklist["active-token"] = now + 300

    # Checking should trigger eviction
    result = await blacklist.is_blacklisted("active-token")

    assert result is True
    # Expired entries should have been cleaned
    assert len(_memory_blacklist) == 1
    assert "active-token" in _memory_blacklist


@pytest.mark.asyncio
async def test_eviction_preserves_active_entries(blacklist):
    """Eviction should only remove expired entries, keeping active ones."""
    now = time.time()

    # Mix of expired and active entries above threshold
    for i in range(_EVICTION_HIGH_WATER):
        _memory_blacklist[f"expired-{i}"] = now - 1

    active_count = 50
    for i in range(active_count):
        _memory_blacklist[f"active-{i}"] = now + 300

    blacklist._maybe_evict()

    assert len(_memory_blacklist) == active_count
    for i in range(active_count):
        assert f"active-{i}" in _memory_blacklist


@pytest.mark.asyncio
async def test_user_revocation_check_triggers_eviction(blacklist):
    """User revocation check via _check_memory_blacklist should trigger eviction."""
    now = time.time()

    # Fill above threshold
    for i in range(_EVICTION_HIGH_WATER + 5):
        _memory_blacklist[f"expired-{i}"] = now - 1

    # Add a user revocation that's still active
    _memory_blacklist["user_revoked:user-42"] = now + 300

    # is_user_revoked calls _check_memory_blacklist which calls _maybe_evict
    result = await blacklist.is_user_revoked("user-42")

    assert result is True
    # Expired entries should have been cleaned
    assert len(_memory_blacklist) == 1
