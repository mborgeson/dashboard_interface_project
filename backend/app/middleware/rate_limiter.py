"""
Rate limiting middleware using sliding window algorithm.

Supports both in-memory (development) and Redis-based (production) backends.
Configurable via environment variables for flexible deployment.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules."""

    requests: int  # Maximum requests allowed
    window: int  # Time window in seconds
    key_prefix: str = "rate_limit"  # Prefix for storage keys


class RateLimitBackend(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def is_rate_limited(
        self, key: str, config: RateLimitConfig
    ) -> tuple[bool, int, int]:
        """
        Check if a request should be rate limited using sliding window algorithm.

        Args:
            key: Unique identifier for the rate limit (e.g., IP address, user ID)
            config: Rate limit configuration

        Returns:
            Tuple of (is_limited, remaining_requests, retry_after_seconds)
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up expired entries (for memory backend) or connections."""
        pass


class MemoryRateLimitBackend(RateLimitBackend):
    """
    In-memory rate limit backend using sliding window log algorithm.

    Suitable for development and single-instance deployments.
    Not recommended for production with multiple workers/instances.
    """

    def __init__(self):
        # Store request timestamps for each key: {key: [timestamp1, timestamp2, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_rate_limited(
        self, key: str, config: RateLimitConfig
    ) -> tuple[bool, int, int]:
        """
        Check rate limit using sliding window log algorithm.

        This algorithm maintains a log of timestamps for each request.
        Old timestamps outside the window are removed, and new requests
        are counted against the remaining slots.
        """
        current_time = time.time()
        window_start = current_time - config.window

        async with self._lock:
            # Remove expired timestamps
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > window_start
            ]

            request_count = len(self._requests[key])

            if request_count >= config.requests:
                # Calculate retry-after based on oldest request in window
                if self._requests[key]:
                    oldest_request = min(self._requests[key])
                    retry_after = int(oldest_request + config.window - current_time) + 1
                else:
                    retry_after = config.window
                return True, 0, max(1, retry_after)

            # Add current request timestamp
            self._requests[key].append(current_time)
            remaining = config.requests - len(self._requests[key])
            return False, remaining, 0

    async def cleanup(self) -> None:
        """Remove all expired entries to prevent memory leaks."""
        current_time = time.time()
        # Use a reasonable max window (1 hour) for cleanup
        max_window = 3600

        async with self._lock:
            keys_to_remove = []
            for key, timestamps in self._requests.items():
                # Remove old timestamps
                self._requests[key] = [
                    ts for ts in timestamps if ts > current_time - max_window
                ]
                # Mark empty keys for removal
                if not self._requests[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._requests[key]


class RedisRateLimitBackend(RateLimitBackend):
    """
    Redis-based rate limit backend using sliding window counter algorithm.

    Suitable for production with multiple workers/instances.
    Provides distributed rate limiting across all application instances.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._connected = False

    async def _get_redis(self):
        """Get or create Redis client."""
        if self._redis is None:
            try:
                from app.services.redis_service import get_redis_service

                redis_service = await get_redis_service()
                self._redis = redis_service.client
                self._connected = True
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
                raise
        return self._redis

    async def is_rate_limited(
        self, key: str, config: RateLimitConfig
    ) -> tuple[bool, int, int]:
        """
        Check rate limit using Redis sliding window counter algorithm.

        Uses a single Redis key with INCR and EXPIRE for efficient counting.
        The sliding window is approximated using fixed time buckets.
        """
        try:
            redis = await self._get_redis()
            current_time = int(time.time())
            # Create a bucket key based on the window
            bucket_key = f"{config.key_prefix}:{key}:{current_time // config.window}"

            # Use pipeline for atomic operations
            pipe = redis.pipeline()
            pipe.incr(bucket_key)
            pipe.expire(bucket_key, config.window * 2)  # Keep for 2 windows
            results = await pipe.execute()

            request_count = int(results[0])

            if request_count > config.requests:
                # Calculate retry-after
                window_end = ((current_time // config.window) + 1) * config.window
                retry_after = max(1, window_end - current_time)
                return True, 0, retry_after

            remaining = config.requests - request_count
            return False, remaining, 0

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open - allow request if Redis is unavailable
            return False, config.requests, 0

    async def cleanup(self) -> None:
        """Redis handles expiration automatically."""
        pass


class RateLimiter:
    """
    Rate limiter with configurable backend and per-endpoint rules.

    Usage:
        limiter = RateLimiter(backend="memory")
        limiter.add_rule("/api/v1/auth/", requests=5, window=60)
        limiter.add_rule("/api/", requests=100, window=60)
    """

    # Class-level singleton for test reset access
    _instance: Optional["RateLimiter"] = None

    def __init__(self, backend: str = "auto"):
        """
        Initialize rate limiter.

        Args:
            backend: "memory", "redis", or "auto" (uses Redis if available)
        """
        self._backend: Optional[RateLimitBackend] = None
        self._backend_type = backend
        self._rules: list[tuple[str, RateLimitConfig]] = []
        self._default_config = RateLimitConfig(
            requests=getattr(settings, "RATE_LIMIT_REQUESTS", 100),
            window=getattr(settings, "RATE_LIMIT_WINDOW", 60),
        )
        # Store instance for test access
        RateLimiter._instance = self

    async def _get_backend(self) -> RateLimitBackend:
        """Get or create the rate limit backend."""
        if self._backend is not None:
            return self._backend

        if self._backend_type == "memory":
            self._backend = MemoryRateLimitBackend()
        elif self._backend_type == "redis":
            self._backend = RedisRateLimitBackend()
        else:  # auto
            try:
                backend = RedisRateLimitBackend()
                await backend._get_redis()
                self._backend = backend
                logger.info("Using Redis backend for rate limiting")
            except Exception:
                self._backend = MemoryRateLimitBackend()
                logger.info("Using in-memory backend for rate limiting")

        return self._backend

    def add_rule(
        self, path_prefix: str, requests: int, window: int, key_prefix: str = "rl"
    ) -> "RateLimiter":
        """
        Add a rate limit rule for a path prefix.

        Args:
            path_prefix: URL path prefix to match
            requests: Maximum requests allowed in window
            window: Time window in seconds
            key_prefix: Prefix for storage keys

        Returns:
            self for method chaining
        """
        config = RateLimitConfig(
            requests=requests, window=window, key_prefix=key_prefix
        )
        self._rules.append((path_prefix, config))
        # Sort by path length (longest first) for most specific match
        self._rules.sort(key=lambda x: len(x[0]), reverse=True)
        return self

    def get_config_for_path(self, path: str) -> RateLimitConfig:
        """Get the rate limit configuration for a given path."""
        for path_prefix, config in self._rules:
            if path.startswith(path_prefix):
                return config
        return self._default_config

    def get_client_key(self, request: Request) -> str:
        """
        Extract client identifier from request.

        Uses X-Forwarded-For header if behind proxy, otherwise client IP.
        Can be extended to include user ID for authenticated requests.
        """
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (original client)
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Include user ID if authenticated (from JWT token)
        # This prevents a single user from being rate limited by IP sharing
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        return f"ip:{client_ip}"

    async def check_rate_limit(
        self, request: Request
    ) -> tuple[bool, int, int, RateLimitConfig]:
        """
        Check if request should be rate limited.

        Returns:
            Tuple of (is_limited, remaining, retry_after, config)
        """
        backend = await self._get_backend()
        config = self.get_config_for_path(request.url.path)
        key = f"{config.key_prefix}:{self.get_client_key(request)}:{request.url.path}"

        is_limited, remaining, retry_after = await backend.is_rate_limited(key, config)
        return is_limited, remaining, retry_after, config

    def reset(self) -> None:
        """
        Reset the rate limiter state. Used for testing.
        """
        if self._backend is not None and isinstance(self._backend, MemoryRateLimitBackend):
            self._backend._requests.clear()

    @classmethod
    def get_instance(cls) -> Optional["RateLimiter"]:
        """Get the current rate limiter instance. Used for testing."""
        return cls._instance


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting requests.

    Adds rate limit headers to responses and returns 429 when limit exceeded.
    """

    def __init__(
        self,
        app,
        limiter: Optional[RateLimiter] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.limiter = limiter or self._create_default_limiter()
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/api/docs", "/api/redoc"]

    def _create_default_limiter(self) -> RateLimiter:
        """Create default rate limiter with standard rules."""
        limiter = RateLimiter(backend="auto")

        # Auth endpoints - stricter limits to prevent brute force
        auth_requests = getattr(settings, "RATE_LIMIT_AUTH_REQUESTS", 5)
        auth_window = getattr(settings, "RATE_LIMIT_AUTH_WINDOW", 60)
        limiter.add_rule("/api/v1/auth/login", requests=auth_requests, window=auth_window, key_prefix="rl:auth")
        limiter.add_rule("/api/v1/auth/register", requests=auth_requests, window=auth_window, key_prefix="rl:auth")
        limiter.add_rule("/api/v1/auth/refresh", requests=10, window=auth_window, key_prefix="rl:auth")

        # API endpoints - standard limits
        api_requests = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
        api_window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
        limiter.add_rule("/api/", requests=api_requests, window=api_window, key_prefix="rl:api")

        return limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply rate limiting."""
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Skip non-API paths
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        try:
            is_limited, remaining, retry_after, config = await self.limiter.check_rate_limit(request)

            if is_limited:
                logger.warning(
                    f"Rate limit exceeded for {request.url.path} from {self.limiter.get_client_key(request)}"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many requests. Please slow down.",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(config.requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                    },
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to successful responses
            response.headers["X-RateLimit-Limit"] = str(config.requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)

            return response

        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Fail open - allow request if rate limiting fails
            return await call_next(request)
