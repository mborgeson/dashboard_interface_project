"""
Prometheus Metrics Definitions

Defines all application metrics collected for monitoring and alerting:
- HTTP request metrics (count, latency, in-progress)
- Database query metrics
- Cache metrics (Redis hits/misses)
- WebSocket connection metrics
- Business metrics (active users, deals, etc.)
"""

import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from loguru import logger
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# =============================================================================
# HTTP Request Metrics
# =============================================================================

REQUEST_COUNT = Counter(
    name="http_requests_total",
    documentation="Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    name="http_request_duration_seconds",
    documentation="HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

REQUEST_IN_PROGRESS = Gauge(
    name="http_requests_in_progress",
    documentation="Number of HTTP requests currently being processed",
    labelnames=["method", "endpoint"],
)

REQUEST_SIZE = Histogram(
    name="http_request_size_bytes",
    documentation="HTTP request body size in bytes",
    labelnames=["method", "endpoint"],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
)

RESPONSE_SIZE = Histogram(
    name="http_response_size_bytes",
    documentation="HTTP response body size in bytes",
    labelnames=["method", "endpoint"],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
)


# =============================================================================
# Database Metrics
# =============================================================================

DB_QUERY_COUNT = Counter(
    name="database_queries_total",
    documentation="Total number of database queries",
    labelnames=["operation", "table"],
)

DB_QUERY_LATENCY = Histogram(
    name="database_query_duration_seconds",
    documentation="Database query latency in seconds",
    labelnames=["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

DB_CONNECTION_POOL_SIZE = Gauge(
    name="database_connection_pool_size",
    documentation="Current database connection pool size",
    labelnames=["pool_type"],
)

DB_CONNECTION_POOL_CHECKED_OUT = Gauge(
    name="database_connection_pool_checked_out",
    documentation="Number of connections currently checked out from pool",
    labelnames=["pool_type"],
)


# =============================================================================
# Cache Metrics (Redis)
# =============================================================================

CACHE_HITS = Counter(
    name="cache_hits_total",
    documentation="Total number of cache hits",
    labelnames=["cache_name"],
)

CACHE_MISSES = Counter(
    name="cache_misses_total",
    documentation="Total number of cache misses",
    labelnames=["cache_name"],
)

CACHE_OPERATIONS = Counter(
    name="cache_operations_total",
    documentation="Total number of cache operations",
    labelnames=["operation", "cache_name"],
)

CACHE_LATENCY = Histogram(
    name="cache_operation_duration_seconds",
    documentation="Cache operation latency in seconds",
    labelnames=["operation", "cache_name"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)


# =============================================================================
# WebSocket Metrics
# =============================================================================

WEBSOCKET_CONNECTIONS = Gauge(
    name="websocket_connections_active",
    documentation="Number of active WebSocket connections",
    labelnames=["channel"],
)

WEBSOCKET_MESSAGES = Counter(
    name="websocket_messages_total",
    documentation="Total number of WebSocket messages",
    labelnames=["direction", "channel", "message_type"],
)


# =============================================================================
# Business Metrics
# =============================================================================

ACTIVE_USERS = Gauge(
    name="active_users",
    documentation="Number of currently active users",
    labelnames=["user_type"],
)

DEALS_COUNT = Gauge(
    name="deals_total",
    documentation="Total number of deals in the system",
    labelnames=["status", "stage"],
)

PROPERTIES_COUNT = Gauge(
    name="properties_total",
    documentation="Total number of properties in the system",
    labelnames=["status"],
)

UNDERWRITING_MODELS_COUNT = Gauge(
    name="underwriting_models_total",
    documentation="Total number of underwriting models",
    labelnames=["status"],
)

ML_PREDICTIONS = Counter(
    name="ml_predictions_total",
    documentation="Total number of ML predictions made",
    labelnames=["model_name", "prediction_type"],
)

ML_PREDICTION_LATENCY = Histogram(
    name="ml_prediction_duration_seconds",
    documentation="ML prediction latency in seconds",
    labelnames=["model_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# =============================================================================
# Application Info
# =============================================================================

APP_INFO = Info(
    name="app",
    documentation="Application information",
)


# =============================================================================
# Metrics Manager
# =============================================================================


class MetricsManager:
    """
    Centralized metrics management class.

    Provides:
    - Metrics initialization and configuration
    - Prometheus metrics export
    - Custom metric registration
    - Metric collection utilities
    """

    def __init__(self, app_name: str, app_version: str, environment: str):
        """Initialize metrics manager with application info."""
        self.app_name = app_name
        self.app_version = app_version
        self.environment = environment
        self._initialized = False

    def initialize(self) -> None:
        """Initialize metrics with application info."""
        if self._initialized:
            return

        APP_INFO.info(
            {
                "name": self.app_name,
                "version": self.app_version,
                "environment": self.environment,
            }
        )

        logger.info(f"Metrics initialized for {self.app_name} v{self.app_version}")
        self._initialized = True

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output."""
        return generate_latest(REGISTRY)

    @property
    def content_type(self) -> str:
        """Return Prometheus content type."""
        return CONTENT_TYPE_LATEST

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0,
    ) -> None:
        """Record HTTP request metrics."""
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

    def record_db_query(
        self,
        operation: str,
        table: str,
        duration: float,
    ) -> None:
        """Record database query metrics."""
        DB_QUERY_COUNT.labels(
            operation=operation,
            table=table,
        ).inc()

        DB_QUERY_LATENCY.labels(
            operation=operation,
            table=table,
        ).observe(duration)

    def record_cache_operation(
        self,
        operation: str,
        cache_name: str,
        hit: bool | None = None,
        duration: float = 0,
    ) -> None:
        """Record cache operation metrics."""
        CACHE_OPERATIONS.labels(
            operation=operation,
            cache_name=cache_name,
        ).inc()

        if hit is not None:
            if hit:
                CACHE_HITS.labels(cache_name=cache_name).inc()
            else:
                CACHE_MISSES.labels(cache_name=cache_name).inc()

        if duration > 0:
            CACHE_LATENCY.labels(
                operation=operation,
                cache_name=cache_name,
            ).observe(duration)


# =============================================================================
# Singleton Instance
# =============================================================================

_metrics_manager: MetricsManager | None = None


def get_metrics_manager() -> MetricsManager:
    """Get or create the metrics manager singleton."""
    global _metrics_manager
    if _metrics_manager is None:
        from app.core.config import settings

        _metrics_manager = MetricsManager(
            app_name=settings.APP_NAME,
            app_version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
        )
    return _metrics_manager


# =============================================================================
# Utility Functions
# =============================================================================


@contextmanager
def track_time(metric: Histogram, labels: dict):
    """
    Context manager to track execution time.

    Usage:
        with track_time(DB_QUERY_LATENCY, {"operation": "select", "table": "users"}):
            result = await db.execute(query)
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        metric.labels(**labels).observe(duration)


def timed(metric: Histogram, labels_func: Callable | None = None):
    """
    Decorator to track function execution time.

    Usage:
        @timed(ML_PREDICTION_LATENCY, lambda args, kwargs: {"model_name": args[0]})
        async def predict(model_name: str, data: dict):
            ...
    """

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs) -> Any:
            labels = labels_func(args, kwargs) if labels_func else {}
            start_time = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start_time
                metric.labels(**labels).observe(duration)

        def sync_wrapper(*args, **kwargs) -> Any:
            labels = labels_func(args, kwargs) if labels_func else {}
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start_time
                metric.labels(**labels).observe(duration)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
