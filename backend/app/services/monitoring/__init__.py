"""
Performance Monitoring Service Package

Provides comprehensive application monitoring capabilities:
- Prometheus metrics collection and export
- Request/response timing middleware
- Database and Redis connection metrics
- Custom business metrics
- Health check probes (liveness, readiness)
"""

from app.services.monitoring.collectors import (
    ApplicationMetricsCollector,
    DatabaseMetricsCollector,
    SystemMetricsCollector,
)
from app.services.monitoring.metrics import (
    ACTIVE_USERS,
    CACHE_HITS,
    CACHE_MISSES,
    DB_QUERY_COUNT,
    DB_QUERY_LATENCY,
    REQUEST_COUNT,
    REQUEST_IN_PROGRESS,
    REQUEST_LATENCY,
    WEBSOCKET_CONNECTIONS,
    MetricsManager,
    get_metrics_manager,
    track_time,
)
from app.services.monitoring.middleware import MetricsMiddleware

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
