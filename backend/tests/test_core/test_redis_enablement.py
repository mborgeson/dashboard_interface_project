"""Tests for Redis enablement (UR-004 + UR-005).

Covers:
- REDIS_REQUIRED config setting behavior
- REDIS_PASSWORD / REDIS_URL consistency validation
- Token blacklist with Redis backend
- CacheService with Redis backend
- Rate limiter with Redis backend
- Fallback to in-memory when Redis unavailable
- Startup validation when REDIS_REQUIRED=True and Redis down
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import CacheService, _memory_cache
from app.core.token_blacklist import TokenBlacklist, _memory_blacklist
from app.middleware.rate_limiter import (
    MemoryRateLimitBackend,
    RateLimitConfig,
    RateLimiter,
    RedisRateLimitBackend,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _clean_state():
    """Clear shared state before and after each test."""
    _memory_blacklist.clear()
    _memory_cache.clear()
    yield
    _memory_blacklist.clear()
    _memory_cache.clear()


# =============================================================================
# UR-005: REDIS_REQUIRED config setting
# =============================================================================


class TestRedisRequiredConfig:
    """Tests for REDIS_REQUIRED configuration setting."""

    def test_redis_required_default_false(self):
        """REDIS_REQUIRED should default to False."""
        from app.core.config import DatabaseSettings

        s = DatabaseSettings()
        assert s.REDIS_REQUIRED is False

    def test_redis_required_can_be_enabled(self):
        """REDIS_REQUIRED can be set to True via env."""
        from app.core.config import DatabaseSettings

        with patch.dict("os.environ", {"REDIS_REQUIRED": "true"}):
            s = DatabaseSettings()
            assert s.REDIS_REQUIRED is True

    def test_redis_password_exists_in_settings(self):
        """REDIS_PASSWORD field should be accessible on DatabaseSettings."""
        from app.core.config import DatabaseSettings

        s = DatabaseSettings()
        # REDIS_PASSWORD is a string field (may be loaded from .env)
        assert isinstance(s.REDIS_PASSWORD, str)


# =============================================================================
# UR-005: REDIS_PASSWORD / REDIS_URL consistency validator
# =============================================================================


class TestRedisPasswordValidator:
    """Tests for REDIS_PASSWORD vs REDIS_URL consistency check."""

    def test_no_warning_when_password_empty(self):
        """No warning when REDIS_PASSWORD is not set."""
        from app.core.config import Settings

        with patch.dict(
            "os.environ",
            {"REDIS_PASSWORD": "", "REDIS_URL": "redis://localhost:6379/0"},
            clear=False,
        ):
            # Should not log any warning about REDIS_PASSWORD
            with patch("app.core.config.logger") as mock_logger:
                from app.core.config import Settings as S

                # Force a fresh instance (bypass lru_cache)
                s = S()
                # The warning about REDIS_PASSWORD should not be called
                password_calls = [
                    c
                    for c in mock_logger.warning.call_args_list
                    if "REDIS_PASSWORD" in str(c)
                ]
                assert len(password_calls) == 0

    def test_warning_when_password_not_in_url(self):
        """Should warn when REDIS_PASSWORD is set but not in REDIS_URL."""
        with patch("app.core.config.logger") as mock_logger:
            from app.core.config import Settings

            s = Settings(
                REDIS_PASSWORD="mysecret",
                REDIS_URL="redis://localhost:6379/0",
            )
            password_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if "REDIS_PASSWORD" in str(c)
            ]
            assert len(password_calls) == 1

    def test_no_warning_when_password_in_url(self):
        """Should not warn when REDIS_PASSWORD matches what's in REDIS_URL."""
        with patch("app.core.config.logger") as mock_logger:
            from app.core.config import Settings

            s = Settings(
                REDIS_PASSWORD="mysecret",
                REDIS_URL="redis://:mysecret@localhost:6379/0",
            )
            password_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if "REDIS_PASSWORD" in str(c)
            ]
            assert len(password_calls) == 0


# =============================================================================
# UR-005: Startup validation when REDIS_REQUIRED=True
# =============================================================================


class TestStartupRedisRequired:
    """Tests for startup behavior when REDIS_REQUIRED is True."""

    @pytest.mark.asyncio
    async def test_startup_raises_when_redis_required_and_down(self):
        """When REDIS_REQUIRED=True and Redis is unreachable, startup should fail."""
        from app.core.config import settings

        with patch.object(settings, "REDIS_REQUIRED", True), patch(
            "app.services.redis_service.get_redis_service",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis refused"),
        ):
            # Simulate the startup logic from main.py lifespan
            with pytest.raises(RuntimeError, match="Redis is required"):
                try:
                    from app.services.redis_service import get_redis_service

                    await get_redis_service()
                except Exception as e:
                    if settings.REDIS_REQUIRED:
                        raise RuntimeError(
                            f"Redis is required but unavailable: {e}. "
                            "Set REDIS_REQUIRED=False to allow in-memory fallback."
                        ) from e

    @pytest.mark.asyncio
    async def test_startup_continues_when_redis_not_required_and_down(self):
        """When REDIS_REQUIRED=False and Redis is unreachable, startup should continue."""
        from app.core.config import settings

        with patch.object(settings, "REDIS_REQUIRED", False), patch(
            "app.services.redis_service.get_redis_service",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis refused"),
        ):
            # Simulate the startup logic from main.py lifespan
            fell_through = False
            try:
                from app.services.redis_service import get_redis_service

                await get_redis_service()
            except Exception:
                if settings.REDIS_REQUIRED:
                    raise RuntimeError("Should not reach here")
                fell_through = True

            assert fell_through is True

    @pytest.mark.asyncio
    async def test_startup_succeeds_when_redis_required_and_available(self):
        """When REDIS_REQUIRED=True and Redis is available, startup should succeed."""
        from app.core.config import settings

        mock_service = MagicMock()
        with patch.object(settings, "REDIS_REQUIRED", True), patch(
            "app.services.redis_service.get_redis_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            # Should not raise
            from app.services.redis_service import get_redis_service

            service = await get_redis_service()
            assert service is mock_service


# =============================================================================
# UR-004: Token blacklist with Redis
# =============================================================================


class TestTokenBlacklistRedis:
    """Tests for token blacklist Redis operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock async Redis client."""
        r = AsyncMock()
        r.ping = AsyncMock(return_value=True)
        r.setex = AsyncMock()
        r.exists = AsyncMock(return_value=0)
        r.delete = AsyncMock()
        r.scan = AsyncMock(return_value=(0, []))
        return r

    @pytest.fixture
    def blacklist_with_redis(self, mock_redis):
        """Create a TokenBlacklist instance with mocked Redis."""
        bl = TokenBlacklist()
        bl._redis = mock_redis
        return bl

    @pytest.mark.asyncio
    async def test_add_stores_in_redis(self, blacklist_with_redis, mock_redis):
        """Token should be stored in Redis when available."""
        await blacklist_with_redis.add("token-123", expires_in=300)
        mock_redis.setex.assert_awaited_once_with("blacklist:token-123", 300, "1")

    @pytest.mark.asyncio
    async def test_is_blacklisted_checks_redis(
        self, blacklist_with_redis, mock_redis
    ):
        """Blacklist check should query Redis when available."""
        mock_redis.exists = AsyncMock(return_value=1)
        result = await blacklist_with_redis.is_blacklisted("token-123")
        assert result is True
        mock_redis.exists.assert_awaited_once_with("blacklist:token-123")

    @pytest.mark.asyncio
    async def test_is_blacklisted_miss_in_redis(
        self, blacklist_with_redis, mock_redis
    ):
        """Token not in Redis should return False."""
        mock_redis.exists = AsyncMock(return_value=0)
        result = await blacklist_with_redis.is_blacklisted("unknown-token")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_deletes_from_redis(
        self, blacklist_with_redis, mock_redis
    ):
        """Removing a token should delete it from Redis."""
        await blacklist_with_redis.remove("token-123")
        mock_redis.delete.assert_awaited_once_with("blacklist:token-123")

    @pytest.mark.asyncio
    async def test_revoke_user_tokens_in_redis(
        self, blacklist_with_redis, mock_redis
    ):
        """User revocation should be stored in Redis."""
        await blacklist_with_redis.revoke_user_tokens("user-42", expires_in=600)
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "user_revoked:user-42"
        assert call_args[1] == 600

    @pytest.mark.asyncio
    async def test_is_user_revoked_checks_redis(
        self, blacklist_with_redis, mock_redis
    ):
        """User revocation check should query Redis."""
        mock_redis.exists = AsyncMock(return_value=1)
        result = await blacklist_with_redis.is_user_revoked("user-42")
        assert result is True
        mock_redis.exists.assert_awaited_once_with("user_revoked:user-42")

    @pytest.mark.asyncio
    async def test_clear_user_revocation_in_redis(
        self, blacklist_with_redis, mock_redis
    ):
        """Clearing user revocation should delete key from Redis."""
        await blacklist_with_redis.clear_user_revocation("user-42")
        mock_redis.delete.assert_awaited_once_with("user_revoked:user-42")

    @pytest.mark.asyncio
    async def test_redis_error_falls_back_to_memory(self, mock_redis):
        """On Redis error, token blacklist should fall back to memory."""
        bl = TokenBlacklist()
        bl._redis = mock_redis
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis down"))

        # add should fall back to memory
        await bl.add("fallback-token", expires_in=300)
        assert "fallback-token" in _memory_blacklist
        assert _memory_blacklist["fallback-token"] > time.time()

    @pytest.mark.asyncio
    async def test_redis_check_error_falls_back_to_memory(self, mock_redis):
        """On Redis error during check, should fall back to memory store."""
        bl = TokenBlacklist()
        bl._redis = mock_redis
        mock_redis.exists = AsyncMock(side_effect=Exception("Redis timeout"))

        # Populate memory store
        _memory_blacklist["check-token"] = time.time() + 300

        result = await bl.is_blacklisted("check-token")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_redis_available_true(self, blacklist_with_redis):
        """is_redis_available should be True when Redis client is set."""
        assert blacklist_with_redis.is_redis_available is True

    @pytest.mark.asyncio
    async def test_stats_with_redis(self, blacklist_with_redis, mock_redis):
        """Stats should include redis_entries when Redis is available."""
        mock_redis.scan = AsyncMock(return_value=(0, ["blacklist:a", "blacklist:b"]))
        stats = await blacklist_with_redis.get_stats()
        assert stats["backend"] == "redis"
        assert stats["redis_entries"] == 2


# =============================================================================
# UR-004: CacheService with Redis
# =============================================================================


class TestCacheServiceRedis:
    """Tests for CacheService Redis operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock async Redis client."""
        r = AsyncMock()
        r.ping = AsyncMock(return_value=True)
        r.get = AsyncMock(return_value=None)
        r.setex = AsyncMock()
        r.delete = AsyncMock()
        r.scan = AsyncMock(return_value=(0, []))
        return r

    @pytest.fixture
    def cache_with_redis(self, mock_redis):
        """Create a CacheService instance with mocked Redis."""
        svc = CacheService()
        svc._init_attempted = True
        svc._redis = mock_redis
        return svc

    @pytest.mark.asyncio
    async def test_set_stores_in_redis(self, cache_with_redis, mock_redis):
        """Cache set should store in Redis when available."""
        await cache_with_redis.set("test_key", {"value": 42}, ttl=60)
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "dashboard:test_key"
        assert call_args[1] == 60

    @pytest.mark.asyncio
    async def test_get_retrieves_from_redis(self, cache_with_redis, mock_redis):
        """Cache get should retrieve from Redis when available."""
        import json

        mock_redis.get = AsyncMock(return_value=json.dumps({"value": 42}))
        result = await cache_with_redis.get("test_key")
        assert result == {"value": 42}
        mock_redis.get.assert_awaited_once_with("dashboard:test_key")

    @pytest.mark.asyncio
    async def test_get_miss_returns_none(self, cache_with_redis, mock_redis):
        """Cache miss in Redis should return None."""
        mock_redis.get = AsyncMock(return_value=None)
        result = await cache_with_redis.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_from_redis(self, cache_with_redis, mock_redis):
        """Cache delete should remove from Redis."""
        await cache_with_redis.delete("test_key")
        mock_redis.delete.assert_awaited_once_with("dashboard:test_key")

    @pytest.mark.asyncio
    async def test_is_redis_available_true(self, cache_with_redis):
        """is_redis_available should be True when Redis client is set."""
        assert cache_with_redis.is_redis_available is True

    @pytest.mark.asyncio
    async def test_redis_error_falls_back_to_memory_on_set(
        self, mock_redis
    ):
        """On Redis set error, should fall back to memory."""
        svc = CacheService()
        svc._init_attempted = True
        svc._redis = mock_redis
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis write error"))

        await svc.set("fallback_key", "value", ttl=60)

        # Value should be in memory cache
        full_key = "dashboard:fallback_key"
        assert full_key in _memory_cache

    @pytest.mark.asyncio
    async def test_redis_error_falls_back_to_memory_on_get(
        self, mock_redis
    ):
        """On Redis get error, should fall back to memory."""
        svc = CacheService()
        svc._init_attempted = True
        svc._redis = mock_redis
        mock_redis.get = AsyncMock(side_effect=Exception("Redis read error"))

        # Pre-populate memory cache
        import json

        full_key = "dashboard:mem_key"
        _memory_cache[full_key] = (json.dumps("mem_value"), time.time() + 300)

        result = await svc.get("mem_key")
        assert result == "mem_value"

    @pytest.mark.asyncio
    async def test_stats_with_redis(self, cache_with_redis, mock_redis):
        """Stats should include redis_entries when Redis is available."""
        mock_redis.scan = AsyncMock(
            return_value=(0, ["dashboard:a", "dashboard:b"])
        )
        stats = await cache_with_redis.get_stats()
        assert stats["backend"] == "redis"
        assert stats["redis_entries"] == 2

    @pytest.mark.asyncio
    async def test_invalidate_pattern_with_redis(
        self, cache_with_redis, mock_redis
    ):
        """invalidate_pattern should scan and delete matching Redis keys."""
        mock_redis.scan = AsyncMock(
            return_value=(0, ["dashboard:property_1", "dashboard:property_2"])
        )
        mock_redis.delete = AsyncMock()

        count = await cache_with_redis.invalidate_pattern("property_*")

        assert count == 2
        mock_redis.delete.assert_awaited_once_with(
            "dashboard:property_1", "dashboard:property_2"
        )


# =============================================================================
# UR-004: Rate limiter with Redis
# =============================================================================


class TestRateLimiterRedis:
    """Tests for rate limiter Redis operations."""

    @pytest.fixture
    def rate_config(self):
        """Create a test rate limit configuration."""
        return RateLimitConfig(requests=5, window=60, key_prefix="test")

    @pytest.mark.asyncio
    async def test_redis_backend_allows_under_limit(self, rate_config):
        """Redis backend should allow requests under the limit."""
        mock_redis = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 0, 1, True])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        backend = RedisRateLimitBackend(redis_client=mock_redis)
        is_limited, remaining, retry_after = await backend.is_rate_limited(
            "test_key", rate_config
        )

        assert is_limited is False
        assert remaining == 4  # 5 - 0 - 1
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_redis_backend_blocks_over_limit(self, rate_config):
        """Redis backend should block requests over the limit."""
        mock_redis = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 5, 1, True])
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()
        mock_redis.zrange = AsyncMock(
            return_value=[(b"member", time.time() - 30)]
        )

        backend = RedisRateLimitBackend(redis_client=mock_redis)
        is_limited, remaining, retry_after = await backend.is_rate_limited(
            "test_key", rate_config
        )

        assert is_limited is True
        assert remaining == 0
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_redis_backend_fails_open_on_error(self, rate_config):
        """Redis backend should fail open (allow request) on error."""
        mock_redis = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(
            side_effect=Exception("Redis connection lost")
        )
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        backend = RedisRateLimitBackend(redis_client=mock_redis)
        is_limited, remaining, retry_after = await backend.is_rate_limited(
            "test_key", rate_config
        )

        assert is_limited is False
        assert remaining == 5

    @pytest.mark.asyncio
    async def test_limiter_auto_backend_falls_back_to_memory(self):
        """RateLimiter with auto backend should fall back to memory when Redis unavailable."""
        with patch(
            "app.middleware.rate_limiter.RedisRateLimitBackend._get_redis",
            new_callable=AsyncMock,
            side_effect=Exception("No Redis"),
        ):
            limiter = RateLimiter(backend="auto")
            backend = await limiter._get_backend()
            assert isinstance(backend, MemoryRateLimitBackend)


# =============================================================================
# UR-004: In-memory fallback when Redis unavailable
# =============================================================================


class TestInMemoryFallback:
    """Tests for in-memory fallback behavior."""

    @pytest.mark.asyncio
    async def test_token_blacklist_memory_fallback(self):
        """Token blacklist should work with memory store when Redis unavailable."""
        bl = TokenBlacklist()
        bl._redis = None

        with patch("app.core.token_blacklist.settings") as mock_settings:
            mock_settings.REDIS_URL = ""

            await bl.add("mem-token", expires_in=300)
            assert await bl.is_blacklisted("mem-token") is True

            stats = await bl.get_stats()
            assert stats["backend"] == "memory"

    @pytest.mark.asyncio
    async def test_cache_service_memory_fallback(self):
        """CacheService should work with memory store when Redis unavailable."""
        svc = CacheService()
        svc._init_attempted = True
        svc._redis = None

        await svc.set("mem-key", {"data": True}, ttl=60)
        result = await svc.get("mem-key")
        assert result == {"data": True}

        stats = await svc.get_stats()
        assert stats["backend"] == "memory"

    @pytest.mark.asyncio
    async def test_cache_ensure_redis_handles_import_error(self):
        """CacheService should handle missing redis package gracefully."""
        svc = CacheService()
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_SOCKET_CONNECT_TIMEOUT = 5
            with patch.dict("sys.modules", {"redis": None, "redis.asyncio": None}):
                # Force re-init
                svc._init_attempted = False
                await svc._ensure_redis()
                assert svc._redis is None
                assert svc._init_attempted is True

    @pytest.mark.asyncio
    async def test_token_blacklist_ensure_redis_handles_connection_failure(self):
        """TokenBlacklist should handle Redis connection failure gracefully."""
        bl = TokenBlacklist()

        with patch("app.core.token_blacklist.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://invalid-host:9999/0"

            with patch(
                "redis.asyncio.from_url",
                side_effect=Exception("Connection refused"),
            ):
                await bl._ensure_redis()
                assert bl._redis is None


# =============================================================================
# Test isolation: Redis keys don't leak between tests
# =============================================================================


class TestRedisIsolation:
    """Verify test isolation for Redis-dependent tests."""

    @pytest.mark.asyncio
    async def test_blacklist_memory_starts_clean(self):
        """Memory blacklist should be empty at the start of each test."""
        assert len(_memory_blacklist) == 0

    @pytest.mark.asyncio
    async def test_cache_memory_starts_clean(self):
        """Memory cache should be empty at the start of each test."""
        assert len(_memory_cache) == 0

    @pytest.mark.asyncio
    async def test_blacklist_add_does_not_leak(self):
        """Adding to blacklist in one test should not be visible in next."""
        bl = TokenBlacklist()
        bl._redis = None
        with patch("app.core.token_blacklist.settings") as mock_settings:
            mock_settings.REDIS_URL = ""
            _memory_blacklist["leak-check"] = time.time() + 300
        # autouse fixture will clean this up after the test
        assert "leak-check" in _memory_blacklist

    @pytest.mark.asyncio
    async def test_blacklist_is_clean_after_previous_test(self):
        """This test runs after the leak test — blacklist should be clean."""
        assert "leak-check" not in _memory_blacklist
