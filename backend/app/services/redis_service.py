"""
Redis caching service for application-wide caching.
"""

import json
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings


class RedisService:
    """
    Redis service for caching and pub/sub messaging.

    Features:
    - Key-value caching with TTL
    - JSON serialization
    - Pub/sub for real-time updates
    - Connection pooling
    """

    def __init__(self):
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            # Test connection
            await self._client.ping()  # type: ignore[misc]
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # ==================== Basic Operations ====================

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default from settings)
        """
        try:
            serialized = json.dumps(value, default=str)
            ttl = ttl or settings.REDIS_CACHE_TTL
            await self.client.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    # ==================== Bulk Operations ====================

    async def mget(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values at once."""
        try:
            values = await self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values, strict=False):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"Redis MGET error: {e}")
            return {}

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE PATTERN error for {pattern}: {e}")
            return 0

    # ==================== Cache Key Builders ====================

    @staticmethod
    def build_key(*parts: str) -> str:
        """Build a cache key from parts."""
        return ":".join(str(p) for p in parts)

    @staticmethod
    def property_key(property_id: int) -> str:
        """Build cache key for property."""
        return f"property:{property_id}"

    @staticmethod
    def deal_key(deal_id: int) -> str:
        """Build cache key for deal."""
        return f"deal:{deal_id}"

    @staticmethod
    def user_key(user_id: int) -> str:
        """Build cache key for user."""
        return f"user:{user_id}"

    @staticmethod
    def analytics_key(report_type: str, *params: str) -> str:
        """Build cache key for analytics data."""
        return f"analytics:{report_type}:" + ":".join(str(p) for p in params)

    # ==================== Pub/Sub ====================

    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        try:
            serialized = json.dumps(message, default=str)
            return await self.client.publish(channel, serialized)
        except Exception as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return 0

    async def subscribe(self, *channels: str):
        """Subscribe to channels and yield messages."""
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(*channels)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except json.JSONDecodeError:
                        yield message["data"]
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE error: {e}")
            raise


# Singleton instance
_redis_service: RedisService | None = None


async def get_redis_service() -> RedisService:
    """Get or create Redis service singleton."""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
        await _redis_service.connect()
    return _redis_service
