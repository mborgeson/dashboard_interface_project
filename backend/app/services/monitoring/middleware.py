"""
Performance Monitoring Middleware

Provides automatic request/response metrics collection:
- Request timing and latency tracking
- Request/response size tracking
- In-progress request counting
- Error rate tracking
"""

import contextlib
import time
from collections.abc import Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.monitoring.metrics import (
    REQUEST_COUNT,
    REQUEST_IN_PROGRESS,
    REQUEST_LATENCY,
    REQUEST_SIZE,
    RESPONSE_SIZE,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects HTTP request metrics.

    Automatically tracks:
    - Request count by method, endpoint, and status code
    - Request latency histograms
    - Request/response body sizes
    - In-progress request gauges
    """

    # Endpoints to exclude from metrics (health checks, metrics endpoint itself)
    EXCLUDED_PATHS = {
        "/api/v1/health",
        "/api/v1/monitoring/health/live",
        "/api/v1/monitoring/health/ready",
        "/api/v1/monitoring/metrics",
        "/metrics",
        "/health",
    }

    def __init__(self, app, exclude_paths: set[str] | None = None):
        """Initialize middleware with optional custom exclusions."""
        super().__init__(app)
        self.exclude_paths = exclude_paths or self.EXCLUDED_PATHS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        path = request.url.path

        # Skip metrics for excluded paths
        if path in self.exclude_paths:
            return await call_next(request)

        # Normalize path for metrics (replace IDs with placeholders)
        endpoint = self._normalize_path(path)
        method = request.method

        # Track request in progress
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()

        # Get request body size
        request_size = 0
        if request.headers.get("content-length"):
            with contextlib.suppress(ValueError, TypeError):
                request_size = int(request.headers["content-length"])

        # Time the request
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Get response body size
            response_size = 0
            if hasattr(response, "headers") and response.headers.get("content-length"):
                with contextlib.suppress(ValueError, TypeError):
                    response_size = int(response.headers["content-length"])

        except Exception:
            # Track exceptions as 500 errors
            status_code = 500
            response_size = 0
            logger.exception(f"Request failed: {method} {path}")
            raise
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time

            # Decrement in-progress counter
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code),
            ).inc()

            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            if request_size > 0:
                REQUEST_SIZE.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(request_size)

            if response_size > 0:
                RESPONSE_SIZE.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(response_size)

            # Log slow requests
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {method} {path} took {duration:.2f}s "
                    f"(status: {status_code})"
                )

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing IDs with placeholders.

        This prevents high cardinality in metrics labels.
        Examples:
            /api/v1/properties/123 -> /api/v1/properties/{id}
            /api/v1/deals/abc-123/documents -> /api/v1/deals/{id}/documents
        """
        parts = path.split("/")
        normalized: list[str] = []

        for _, part in enumerate(parts):
            if not part:
                normalized.append(part)
                continue

            # Check if this looks like an ID (UUID, numeric, or alphanumeric with dashes)
            if self._is_id_like(part):
                normalized.append("{id}")
            else:
                normalized.append(part)

        return "/".join(normalized)

    def _is_id_like(self, value: str) -> bool:
        """
        Check if a path segment looks like an ID.

        Matches:
        - Pure numeric IDs: 123, 456789
        - UUIDs: 550e8400-e29b-41d4-a716-446655440000
        - Short IDs: abc123, A1B2C3
        """
        # Pure numeric
        if value.isdigit():
            return True

        # UUID format
        if len(value) == 36 and value.count("-") == 4:
            return True

        # Short alphanumeric IDs (between 8-32 chars, contains both letters and numbers)
        if 8 <= len(value) <= 32:
            has_alpha = any(c.isalpha() for c in value)
            has_digit = any(c.isdigit() for c in value)
            has_only_valid = all(c.isalnum() or c == "-" or c == "_" for c in value)
            if has_alpha and has_digit and has_only_valid:
                return True

        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request details.

    Useful for debugging and audit trails.
    """

    EXCLUDED_PATHS = {"/health", "/metrics", "/api/v1/health"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Generate request ID
        request_id = str(id(request))[:8]

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Log response
            logger.info(
                f"[{request_id}] Response {response.status_code} in {duration:.3f}s"
            )

            return response

        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.error(f"[{request_id}] Error after {duration:.3f}s: {exc}")
            raise
