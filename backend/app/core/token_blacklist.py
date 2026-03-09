"""
Token blacklist implementation for JWT invalidation.

Uses async Redis for non-blocking O(1) lookups with automatic expiration.
Falls back to in-memory store if Redis unavailable.
"""

import time

from loguru import logger

from app.core.config import settings

# In-memory fallback store
_memory_blacklist: dict[str, float] = {}


class TokenBlacklist:
    """
    Token blacklist for invalidating JWTs on logout.

    Supports async Redis for production use with automatic TTL expiration,
    and falls back to in-memory storage for development/testing.
    """

    def __init__(self):
        self._redis = None

    async def _ensure_redis(self) -> None:
        """Lazily initialize async Redis connection if configured."""
        if self._redis is not None:
            return
        if not settings.REDIS_URL:
            logger.info("Token blacklist: No REDIS_URL configured, using memory store")
            return

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._redis.ping()
            logger.info("Token blacklist: async Redis connection established")
        except ImportError:
            logger.warning(
                "Token blacklist: redis package not installed, using memory store"
            )
            self._redis = None
        except Exception as e:
            logger.warning(
                f"Token blacklist: Redis connection failed ({e}), using memory store"
            )
            self._redis = None

    @property
    def is_redis_available(self) -> bool:
        """Check if Redis backend is available."""
        return self._redis is not None

    async def revoke_user_tokens(self, user_id: str, expires_in: int = 604800) -> None:
        """
        Revoke all tokens for a user by setting a user-level revocation timestamp.

        Any token issued before this timestamp will be considered invalid.
        Used for replay attack detection during refresh token rotation.

        Args:
            user_id: The user ID whose tokens should be revoked
            expires_in: Seconds until revocation expires (default 7 days = refresh token lifetime)
        """
        if not user_id:
            return

        import time as _time

        revoked_at = str(int(_time.time()))
        key = f"user_revoked:{user_id}"

        await self._ensure_redis()

        if self._redis:
            try:
                await self._redis.setex(key, expires_in, revoked_at)
                logger.warning(
                    f"All tokens revoked for user {user_id} (replay attack detected)"
                )
            except Exception as e:
                logger.error(f"Redis user revocation failed: {e}")
                _memory_blacklist[key] = time.time() + expires_in
        else:
            # For memory store, store the revocation timestamp as a special entry
            _memory_blacklist[key] = time.time() + expires_in
            logger.warning(
                f"All tokens revoked for user {user_id} in memory (replay attack detected)"
            )

    async def is_user_revoked(self, user_id: str, token_iat: int | None = None) -> bool:
        """
        Check if a user's tokens have been revoked.

        Args:
            user_id: The user ID to check
            token_iat: The token's issued-at timestamp (unused for now, reserved for future use)

        Returns:
            True if user's tokens are revoked, False otherwise
        """
        if not user_id:
            return False

        key = f"user_revoked:{user_id}"

        await self._ensure_redis()

        if self._redis:
            try:
                return bool(await self._redis.exists(key))
            except Exception as e:
                logger.error(f"Redis user revocation check failed: {e}")
                return self._check_memory_blacklist(key)
        else:
            return self._check_memory_blacklist(key)

    async def clear_user_revocation(self, user_id: str) -> None:
        """
        Clear user-level token revocation (for testing/admin purposes).

        Args:
            user_id: The user ID to clear revocation for
        """
        key = f"user_revoked:{user_id}"

        await self._ensure_redis()

        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.error(f"Redis clear user revocation failed: {e}")
                if key in _memory_blacklist:
                    del _memory_blacklist[key]
        else:
            if key in _memory_blacklist:
                del _memory_blacklist[key]

    async def add(self, token_jti: str, expires_in: int = 1800) -> None:
        """
        Add token to blacklist with expiration.

        Args:
            token_jti: Unique token identifier (JWT ID)
            expires_in: Seconds until token expires (default 30 minutes)
        """
        if not token_jti:
            return

        await self._ensure_redis()

        if self._redis:
            try:
                await self._redis.setex(f"blacklist:{token_jti}", expires_in, "1")
                logger.debug(f"Token blacklisted in Redis: {token_jti[:8]}...")
            except Exception as e:
                logger.error(f"Redis blacklist add failed: {e}")
                # Fallback to memory
                _memory_blacklist[token_jti] = time.time() + expires_in
        else:
            _memory_blacklist[token_jti] = time.time() + expires_in
            logger.debug(f"Token blacklisted in memory: {token_jti[:8]}...")

    async def is_blacklisted(self, token_jti: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            token_jti: Unique token identifier (JWT ID)

        Returns:
            True if token is blacklisted, False otherwise
        """
        if not token_jti:
            return False

        await self._ensure_redis()

        if self._redis:
            try:
                return bool(await self._redis.exists(f"blacklist:{token_jti}"))
            except Exception as e:
                logger.error(f"Redis blacklist check failed: {e}")
                # Fallback to memory check
                return self._check_memory_blacklist(token_jti)
        else:
            return self._check_memory_blacklist(token_jti)

    def _check_memory_blacklist(self, token_jti: str) -> bool:
        """Check in-memory blacklist with expiration handling."""
        exp = _memory_blacklist.get(token_jti, 0)
        if exp > time.time():
            return True
        elif token_jti in _memory_blacklist:
            # Clean up expired entry
            del _memory_blacklist[token_jti]
        return False

    def cleanup_memory(self) -> int:
        """
        Clean expired tokens from memory store.

        Returns:
            Number of tokens removed
        """
        now = time.time()
        expired = [k for k, v in _memory_blacklist.items() if v <= now]
        for k in expired:
            del _memory_blacklist[k]
        if expired:
            logger.debug(f"Cleaned {len(expired)} expired tokens from memory blacklist")
        return len(expired)

    async def remove(self, token_jti: str) -> None:
        """
        Remove token from blacklist (for testing/admin purposes).

        Args:
            token_jti: Unique token identifier (JWT ID)
        """
        if not token_jti:
            return

        await self._ensure_redis()

        if self._redis:
            try:
                await self._redis.delete(f"blacklist:{token_jti}")
            except Exception as e:
                logger.error(f"Redis blacklist remove failed: {e}")
                if token_jti in _memory_blacklist:
                    del _memory_blacklist[token_jti]
        else:
            if token_jti in _memory_blacklist:
                del _memory_blacklist[token_jti]

    async def get_stats(self) -> dict:
        """Get blacklist statistics."""
        stats = {
            "backend": "redis" if self._redis else "memory",
            "memory_entries": len(_memory_blacklist),
        }
        if self._redis:
            try:
                # Count blacklist keys in Redis
                cursor = 0
                count = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor, match="blacklist:*", count=100
                    )
                    count += len(keys)
                    if cursor == 0:
                        break
                stats["redis_entries"] = count
            except Exception:
                stats["redis_entries"] = "error"
        return stats


# Global singleton instance
token_blacklist = TokenBlacklist()
