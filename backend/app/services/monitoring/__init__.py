"""
Performance Monitoring Service Package

Provides comprehensive application monitoring capabilities:
- Prometheus metrics collection and export
- Request/response timing middleware
- Database and Redis connection metrics
- Custom business metrics
- Health check probes (liveness, readiness)
"""

from app.services.monitoring.metrics import (
    MetricsManager,
    get_metrics_manager,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_IN_PROGRESS,
    DB_QUERY_COUNT,
    DB_QUERY_LATENCY,
    CACHE_HITS,
    CACHE_MISSES,
    WEBSOCKET_CONNECTIONS,
    ACTIVE_USERS,
    track_time,
)
from app.services.monitoring.middleware import MetricsMiddleware
from app.services.monitoring.collectors import (
    SystemMetricsCollector,
    DatabaseMetricsCollector,
    ApplicationMetricsCollector,
)

__all__ = [
    # Manager
    "MetricsManager",
    "get_metrics_manager",
    # Metrics
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "REQUEST_IN_PROGRESS",
    "DB_QUERY_COUNT",
    "DB_QUERY_LATENCY",
    "CACHE_HITS",
    "CACHE_MISSES",
    "WEBSOCKET_CONNECTIONS",
    "ACTIVE_USERS",
    # Utilities
    "track_time",
    # Middleware
    "MetricsMiddleware",
    # Collectors
    "SystemMetricsCollector",
    "DatabaseMetricsCollector",
    "ApplicationMetricsCollector",
]
