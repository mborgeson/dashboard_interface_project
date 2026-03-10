"""Tests for token blacklist (in-memory fallback mode).

Covers:
- Adding and checking tokens
- Expiration handling
- User-level revocation
- Memory cleanup
- Stats reporting
"""

import time

import pytest

from app.core.token_blacklist import TokenBlacklist, _memory_blacklist


@pytest.fixture(autouse=True)
def clean_memory_blacklist():
    """Clear in-memory blacklist before and after each test."""
    _memory_blacklist.clear()
    yield
    _memory_blacklist.clear()


@pytest.fixture
def blacklist():
    """Create a fresh TokenBlacklist instance (no Redis)."""
    bl = TokenBlacklist()
    # Ensure no Redis connection
    bl._redis = None
    return bl


# =============================================================================
# Token Blacklisting
# =============================================================================


@pytest.mark.asyncio
async def test_add_and_check_blacklisted(blacklist):
    """Token should be blacklisted after adding it."""
    await blacklist.add("token-abc", expires_in=300)
    assert await blacklist.is_blacklisted("token-abc") is True


@pytest.mark.asyncio
async def test_non_blacklisted_token(blacklist):
    """Token not added should not be blacklisted."""
    assert await blacklist.is_blacklisted("token-xyz") is False


@pytest.mark.asyncio
async def test_empty_jti_not_blacklisted(blacklist):
    """Empty string JTI should return False without error."""
    await blacklist.add("")
    assert await blacklist.is_blacklisted("") is False


@pytest.mark.asyncio
async def test_expired_token_not_blacklisted(blacklist):
    """Token with expired TTL should not be blacklisted."""
    # Add with 0 second expiration (already expired)
    _memory_blacklist["token-expired"] = time.time() - 1
    assert await blacklist.is_blacklisted("token-expired") is False
    # Expired entry should be cleaned up
    assert "token-expired" not in _memory_blacklist


@pytest.mark.asyncio
async def test_remove_token(blacklist):
    """Removing a token should un-blacklist it."""
    await blacklist.add("token-remove", expires_in=300)
    assert await blacklist.is_blacklisted("token-remove") is True

    await blacklist.remove("token-remove")
    assert await blacklist.is_blacklisted("token-remove") is False


@pytest.mark.asyncio
async def test_remove_nonexistent_token(blacklist):
    """Removing a non-existent token should not raise."""
    await blacklist.remove("nonexistent")  # Should not raise


@pytest.mark.asyncio
async def test_remove_empty_jti(blacklist):
    """Removing empty JTI should not raise."""
    await blacklist.remove("")  # Should not raise


# =============================================================================
# User-Level Revocation
# =============================================================================


@pytest.mark.asyncio
async def test_revoke_user_tokens(blacklist):
    """After revoking, user should show as revoked."""
    await blacklist.revoke_user_tokens("user-42", expires_in=300)
    assert await blacklist.is_user_revoked("user-42") is True


@pytest.mark.asyncio
async def test_non_revoked_user(blacklist):
    """User with no revocation should not be flagged."""
    assert await blacklist.is_user_revoked("user-99") is False


@pytest.mark.asyncio
async def test_clear_user_revocation(blacklist):
    """Clearing revocation should allow user tokens again."""
    await blacklist.revoke_user_tokens("user-42", expires_in=300)
    assert await blacklist.is_user_revoked("user-42") is True

    await blacklist.clear_user_revocation("user-42")
    assert await blacklist.is_user_revoked("user-42") is False


@pytest.mark.asyncio
async def test_revoke_empty_user_id(blacklist):
    """Revoking with empty user_id should be a no-op."""
    await blacklist.revoke_user_tokens("")
    assert await blacklist.is_user_revoked("") is False


@pytest.mark.asyncio
async def test_clear_revocation_nonexistent(blacklist):
    """Clearing revocation for non-revoked user should not raise."""
    await blacklist.clear_user_revocation("nobody")  # Should not raise


# =============================================================================
# Memory Cleanup
# =============================================================================


@pytest.mark.asyncio
async def test_cleanup_memory_removes_expired(blacklist):
    """cleanup_memory should remove expired entries."""
    _memory_blacklist["expired-1"] = time.time() - 10
    _memory_blacklist["expired-2"] = time.time() - 5
    _memory_blacklist["active-1"] = time.time() + 300

    removed = blacklist.cleanup_memory()

    assert removed == 2
    assert "expired-1" not in _memory_blacklist
    assert "expired-2" not in _memory_blacklist
    assert "active-1" in _memory_blacklist


@pytest.mark.asyncio
async def test_cleanup_memory_nothing_expired(blacklist):
    """cleanup_memory with no expired entries returns 0."""
    _memory_blacklist["active"] = time.time() + 300
    removed = blacklist.cleanup_memory()
    assert removed == 0


# =============================================================================
# Stats
# =============================================================================


@pytest.mark.asyncio
async def test_get_stats_memory_backend(blacklist):
    """Stats should report memory backend and entry count."""
    await blacklist.add("token-1", expires_in=300)
    await blacklist.add("token-2", expires_in=300)

    stats = await blacklist.get_stats()

    assert stats["backend"] == "memory"
    assert stats["memory_entries"] == 2
    assert "redis_entries" not in stats


@pytest.mark.asyncio
async def test_is_redis_available(blacklist):
    """Without Redis configured, is_redis_available should be False."""
    assert blacklist.is_redis_available is False
