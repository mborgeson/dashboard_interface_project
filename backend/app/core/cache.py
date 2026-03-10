"""
Redis caching layer for frequently-accessed, rarely-changing data.

Provides async get/set/delete/invalidate helpers with TTL-based expiration
and an in-memory fallback when Redis is unavailable.

Key prefix scheme:
    dashboard:portfolio_summary
    dashboard:property_list
    dashboard:property_dashboard:{property_id}
    dashboard:analytics_dashboard
    dashboard:deal_stats:{time_period}
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from loguru import logger

from app.core.config import settings

# In-memory fallback cache: key -> (value_json, expires_at)
_memory_cache: dict[str, tuple[str, float]] = {}

# All dashboard cache keys use this prefix for bulk invalidation
CACHE_PREFIX = "dashboard"

# Default TTLs (seconds)
DEFAULT_TTL: int = settings.REDIS_CACHE_TTL  # 1 hour from config
SHORT_TTL: int = (
    settings.CACHE_SHORT_TTL
)  # 5 minutes — for data that changes more often
LONG_TTL: int = settings.CACHE_LONG_TTL  # 2 hours — for rarely-changing aggregates


class CacheService:
    """
    Async Redis cache with lazy connection and in-memory fallback.

    Mirrors the pattern from token_blacklist.py: lazy ``_ensure_redis()``,
    Redis preferred, memory store as fallback.
    """

    def __init__(self) -> None:
        self._redis: Any = None
        self._init_attempted = False

    async def _ensure_redis(self) -> None:
        """Lazily initialize async Redis connection if configured."""
        if self._init_attempted:
            return
        self._init_attempted = True

        if not settings.REDIS_URL:
            logger.info("Cache: No REDIS_URL configured, using memory store")
            return

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            )
            await self._redis.ping()
            logger.info("Cache: async Redis connection established")
        except ImportError:
            logger.warning("Cache: redis package not installed, using memory store")
            self._redis = None
        except Exception as e:
            logger.warning(f"Cache: Redis connection failed ({e}), using memory store")
            self._redis = None

    @property
    def is_redis_available(self) -> bool:
        """Check if Redis backend is available."""
        return self._redis is not None

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Any | None:
        """
        Retrieve a cached value by key.

        Returns the deserialized Python object, or None on miss/error.
        """
        full_key = f"{CACHE_PREFIX}:{key}"
        await self._ensure_redis()

        if self._redis:
            try:
                raw = await self._redis.get(full_key)
                if raw is not None:
                    logger.debug(f"Cache HIT (Redis): {full_key}")
                    return json.loads(raw)
                logger.debug(f"Cache MISS (Redis): {full_key}")
                return None
            except Exception as e:
                logger.error(f"Cache get error (Redis): {e}")
                # Fall through to memory check
                return self._memory_get(full_key)
        else:
            return self._memory_get(full_key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Store a value in the cache with optional TTL.

        Args:
            key: Cache key (prefix is added automatically).
            value: Any JSON-serializable Python object.
            ttl: Time-to-live in seconds (defaults to REDIS_CACHE_TTL).
        """
        full_key = f"{CACHE_PREFIX}:{key}"
        ttl = ttl if ttl is not None else DEFAULT_TTL
        raw = json.dumps(value, default=str)

        await self._ensure_redis()

        if self._redis:
            try:
                await self._redis.setex(full_key, ttl, raw)
                logger.debug(f"Cache SET (Redis): {full_key} TTL={ttl}s")
            except Exception as e:
                logger.error(f"Cache set error (Redis): {e}")
                self._memory_set(full_key, raw, ttl)
        else:
            self._memory_set(full_key, raw, ttl)

    async def delete(self, key: str) -> None:
        """Delete a single cache entry."""
        full_key = f"{CACHE_PREFIX}:{key}"
        await self._ensure_redis()

        if self._redis:
            try:
                await self._redis.delete(full_key)
                logger.debug(f"Cache DELETE (Redis): {full_key}")
            except Exception as e:
                logger.error(f"Cache delete error (Redis): {e}")
                _memory_cache.pop(full_key, None)
        else:
            _memory_cache.pop(full_key, None)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all cache entries matching a glob pattern.

        Args:
            pattern: Glob pattern relative to CACHE_PREFIX (e.g. "property_*").

        Returns:
            Number of keys deleted.
        """
        full_pattern = f"{CACHE_PREFIX}:{pattern}"
        await self._ensure_redis()
        count = 0

        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor, match=full_pattern, count=100
                    )
                    if keys:
                        await self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
                logger.info(f"Cache INVALIDATE (Redis): {full_pattern} -> {count} keys")
            except Exception as e:
                logger.error(f"Cache invalidate_pattern error (Redis): {e}")
                count = self._memory_invalidate_pattern(full_pattern)
        else:
            count = self._memory_invalidate_pattern(full_pattern)

        return count

    async def invalidate_properties(self) -> int:
        """Invalidate all property-related caches."""
        count = 0
        count += await self.invalidate_pattern("property_*")
        count += await self.invalidate_pattern("portfolio_summary*")
        count += await self.invalidate_pattern("analytics_dashboard*")
        logger.info(f"Cache: invalidated {count} property-related keys")
        return count

    async def invalidate_deals(self) -> int:
        """Invalidate all deal-related caches."""
        count = 0
        count += await self.invalidate_pattern("deal_*")
        count += await self.invalidate_pattern("analytics_dashboard*")
        logger.info(f"Cache: invalidated {count} deal-related keys")
        return count

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats: dict[str, Any] = {
            "backend": "redis" if self._redis else "memory",
            "memory_entries": len(_memory_cache),
        }
        if self._redis:
            try:
                cursor = 0
                count = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor, match=f"{CACHE_PREFIX}:*", count=100
                    )
                    count += len(keys)
                    if cursor == 0:
                        break
                stats["redis_entries"] = count
            except Exception:
                stats["redis_entries"] = "error"
        return stats

    # ------------------------------------------------------------------
    # In-memory fallback helpers
    # ------------------------------------------------------------------

    def _memory_get(self, full_key: str) -> Any | None:
        entry = _memory_cache.get(full_key)
        if entry is None:
            return None
        raw, expires_at = entry
        if time.time() > expires_at:
            del _memory_cache[full_key]
            return None
        return json.loads(raw)

    def _memory_set(self, full_key: str, raw: str, ttl: int) -> None:
        _memory_cache[full_key] = (raw, time.time() + ttl)

    def _memory_invalidate_pattern(self, pattern: str) -> int:
        """Delete memory cache entries matching a simple glob pattern (only trailing *)."""
        import fnmatch

        to_delete = [k for k in _memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in to_delete:
            del _memory_cache[k]
        return len(to_delete)

    def cleanup_memory(self) -> int:
        """Remove expired entries from the in-memory cache."""
        now = time.time()
        expired = [k for k, (_, exp) in _memory_cache.items() if exp <= now]
        for k in expired:
            del _memory_cache[k]
        if expired:
            logger.debug(f"Cache: cleaned {len(expired)} expired memory entries")
        return len(expired)


def make_cache_key(*parts: str) -> str:
    """
    Build a cache key from parts.

    Example::

        make_cache_key("property_list", property_type="multifamily", page="1")
        # -> "property_list:multifamily:1"
    """
    return ":".join(str(p) for p in parts if p)


def make_cache_key_from_params(prefix: str, **params: Any) -> str:
    """
    Build a deterministic cache key from a prefix and keyword params.

    Sorts params alphabetically and hashes them to keep the key short.

    Example::

        make_cache_key_from_params("property_list", page=1, type="multifamily")
        # -> "property_list:a1b2c3d4"
    """
    if not params or all(v is None for v in params.values()):
        return prefix
    # Filter out None values, sort, and hash
    filtered = {k: v for k, v in sorted(params.items()) if v is not None}
    if not filtered:
        return prefix
    raw = json.dumps(filtered, sort_keys=True, default=str)
    digest = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:8]  # noqa: S324
    return f"{prefix}:{digest}"


# Global singleton instance
cache = CacheService()
