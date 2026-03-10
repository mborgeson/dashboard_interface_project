"""
Custom Metrics Collectors

Provides collectors for gathering metrics from various system components:
- System metrics (CPU, memory, disk)
- Database metrics (connections, queries)
- Application metrics (users, deals, models)
"""

import asyncio
import os
import platform
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.services.monitoring.metrics import (
    ACTIVE_USERS,
    DB_CONNECTION_POOL_CHECKED_IN,
    DB_CONNECTION_POOL_CHECKED_OUT,
    DB_CONNECTION_POOL_OVERFLOW,
    DB_CONNECTION_POOL_SIZE,
    DEALS_COUNT,
    PROPERTIES_COUNT,
    REDIS_CONNECTION_POOL_AVAILABLE,
    REDIS_CONNECTION_POOL_IN_USE,
    REDIS_CONNECTION_POOL_SIZE,
    UNDERWRITING_MODELS_COUNT,
)


class SystemMetricsCollector:
    """
    Collects system-level metrics.

    Metrics include:
    - CPU usage and load averages
    - Memory usage (total, available, used)
    - Disk usage
    - Process information
    """

    def __init__(self) -> None:
        """Initialize system metrics collector."""
        self._last_collection: datetime | None = None
        self._cache_duration = timedelta(seconds=5)
        self._cached_metrics: dict[str, Any] = {}

    async def collect(self) -> dict[str, Any]:
        """Collect system metrics."""
        now = datetime.now(UTC)

        # Return cached if still valid
        if self._last_collection and now - self._last_collection < self._cache_duration:
            return self._cached_metrics

        metrics: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
            "process": {
                "pid": os.getpid(),
            },
        }

        # Try to get psutil metrics if available
        try:
            import psutil

            # CPU metrics
            metrics["cpu"] = {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "load_avg": os.getloadavg() if hasattr(os, "getloadavg") else None,
            }

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics["memory"] = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
            }

            # Disk metrics
            disk = psutil.disk_usage("/")
            metrics["disk"] = {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round(disk.percent, 1),
            }

            # Process metrics
            process = psutil.Process(os.getpid())
            metrics["process"]["memory_mb"] = round(
                process.memory_info().rss / (1024**2), 2
            )
            metrics["process"]["cpu_percent"] = process.cpu_percent()
            metrics["process"]["threads"] = process.num_threads()

        except ImportError:
            logger.debug("psutil not available, skipping system metrics")
            metrics["cpu"] = {"available": False}
            metrics["memory"] = {"available": False}
            metrics["disk"] = {"available": False}

        self._cached_metrics = metrics
        self._last_collection = now

        return metrics


class DatabaseMetricsCollector:
    """
    Collects database connection and query metrics.

    Metrics include:
    - Connection pool status (async and sync engines)
    - Active connections
    - Query performance statistics
    """

    def __init__(self) -> None:
        """Initialize database metrics collector."""
        self._engine = None
        self._sync_engine = None

    def set_engine(self, engine) -> None:
        """Set the SQLAlchemy async engine for pool monitoring."""
        self._engine = engine

    def set_sync_engine(self, engine) -> None:
        """Set the SQLAlchemy sync engine for pool monitoring."""
        self._sync_engine = engine

    def _collect_pool_stats(self, pool, pool_type: str) -> dict[str, Any]:
        """Extract pool statistics from a SQLAlchemy pool and update Prometheus gauges."""
        pool_status = {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
        }

        # Update Prometheus gauges
        DB_CONNECTION_POOL_SIZE.labels(pool_type=pool_type).set(pool_status["size"])
        DB_CONNECTION_POOL_CHECKED_OUT.labels(pool_type=pool_type).set(
            pool_status["checked_out"]
        )
        DB_CONNECTION_POOL_OVERFLOW.labels(pool_type=pool_type).set(
            pool_status["overflow"]
        )
        DB_CONNECTION_POOL_CHECKED_IN.labels(pool_type=pool_type).set(
            pool_status["checked_in"]
        )

        return pool_status

    async def collect(self) -> dict[str, Any]:
        """Collect database metrics."""
        metrics: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "connected": False,
            "pool": {},
        }

        if self._engine is None and self._sync_engine is None:
            return metrics

        try:
            # Async engine pool stats
            if self._engine is not None:
                pool = self._engine.pool
                metrics["pool"]["async"] = self._collect_pool_stats(pool, "async")
                metrics["connected"] = True

                # Keep backward-compatible top-level keys
                metrics["pool"]["size"] = metrics["pool"]["async"]["size"]
                metrics["pool"]["checked_out"] = metrics["pool"]["async"]["checked_out"]
                metrics["pool"]["overflow"] = metrics["pool"]["async"]["overflow"]
                metrics["pool"]["checked_in"] = metrics["pool"]["async"]["checked_in"]

        except Exception as e:
            logger.warning(f"Failed to collect async database pool metrics: {e}")
            metrics["pool"]["async_error"] = str(e)

        try:
            # Sync engine pool stats
            if self._sync_engine is not None:
                pool = self._sync_engine.pool
                metrics["pool"]["sync"] = self._collect_pool_stats(pool, "sync")
                metrics["connected"] = True

        except Exception as e:
            logger.warning(f"Failed to collect sync database pool metrics: {e}")
            metrics["pool"]["sync_error"] = str(e)

        if not metrics["connected"]:
            metrics["error"] = "No engines available"

        return metrics


class ApplicationMetricsCollector:
    """
    Collects application-level business metrics.

    Metrics include:
    - Active user counts
    - Deal statistics by status
    - Property counts
    - Underwriting model statistics
    """

    def __init__(self) -> None:
        """Initialize application metrics collector."""
        self._db_session_factory = None
        self._last_collection: datetime | None = None
        self._cache_duration = timedelta(seconds=30)
        self._cached_metrics: dict[str, Any] = {}

    def set_session_factory(self, session_factory) -> None:
        """Set the database session factory for queries."""
        self._db_session_factory = session_factory

    async def collect(self) -> dict[str, Any]:
        """Collect application metrics."""
        now = datetime.now(UTC)

        # Return cached if still valid
        if self._last_collection and now - self._last_collection < self._cache_duration:
            return self._cached_metrics

        metrics: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "users": {},
            "deals": {},
            "properties": {},
            "underwriting_models": {},
        }

        if self._db_session_factory is None:
            return metrics

        try:
            from sqlalchemy import func, select

            async with self._db_session_factory() as session:
                # User counts
                from app.models.user import User

                user_count = await session.scalar(select(func.count(User.id)))
                metrics["users"]["total"] = user_count or 0
                ACTIVE_USERS.labels(user_type="total").set(user_count or 0)

                # Deal counts by stage
                from app.models.deal import Deal, DealStage

                for stage in DealStage:
                    count = await session.scalar(
                        select(func.count(Deal.id)).where(Deal.stage == stage)
                    )
                    metrics["deals"][stage.value] = count or 0
                    DEALS_COUNT.labels(status="active", stage=stage.value).set(
                        count or 0
                    )

                # Property counts
                from app.models.property import Property

                property_count = await session.scalar(select(func.count(Property.id)))
                metrics["properties"]["total"] = property_count or 0
                PROPERTIES_COUNT.labels(status="active").set(property_count or 0)

                # Underwriting model counts by status
                from app.models.underwriting import (
                    UnderwritingModel,
                    UnderwritingStatus,
                )

                for status in UnderwritingStatus:
                    count = await session.scalar(
                        select(func.count(UnderwritingModel.id)).where(
                            UnderwritingModel.status == status
                        )
                    )
                    metrics["underwriting_models"][status.value] = count or 0
                    UNDERWRITING_MODELS_COUNT.labels(status=status.value).set(
                        count or 0
                    )

        except Exception as e:
            logger.warning(f"Failed to collect application metrics: {e}")
            metrics["error"] = str(e)

        self._cached_metrics = metrics
        self._last_collection = now

        return metrics


class ConnectionPoolCollector:
    """
    Collects connection pool statistics for both database and Redis.

    Provides a unified view of all connection pool health metrics:
    - SQLAlchemy async/sync engine pool stats
    - Redis connection pool stats (when available)
    """

    def __init__(self) -> None:
        """Initialize connection pool collector."""
        self._engine = None
        self._sync_engine = None
        self._last_collection: datetime | None = None
        self._cache_duration = timedelta(seconds=3)
        self._cached_metrics: dict[str, Any] = {}

    def set_engine(self, engine) -> None:
        """Set the SQLAlchemy async engine for pool monitoring."""
        self._engine = engine

    def set_sync_engine(self, engine) -> None:
        """Set the SQLAlchemy sync engine for pool monitoring."""
        self._sync_engine = engine

    def _collect_sqlalchemy_pool(self, pool, label: str) -> dict[str, Any]:
        """Extract stats from a SQLAlchemy connection pool."""
        return {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
            "max_overflow": getattr(pool, "_max_overflow", None),
            "pool_class": type(pool).__name__,
            "label": label,
        }

    async def _collect_redis_pool(self, name: str, redis_client: Any) -> dict[str, Any]:
        """Extract stats from a Redis connection pool."""
        stats: dict[str, Any] = {
            "name": name,
            "backend": "redis",
            "available": False,
        }

        if redis_client is None:
            stats["backend"] = "memory"
            return stats

        try:
            pool = getattr(redis_client, "connection_pool", None)
            if pool is None:
                stats["note"] = "no connection pool attribute"
                return stats

            stats["available"] = True
            stats["pool_class"] = type(pool).__name__
            stats["max_connections"] = getattr(pool, "max_connections", None)

            # ConnectionPool exposes _created_connections and _available_connections
            created = getattr(pool, "_created_connections", None)
            if created is not None:
                stats["created_connections"] = created

            available_conns = getattr(pool, "_available_connections", None)
            if available_conns is not None:
                stats["available_connections"] = len(available_conns)

            in_use = getattr(pool, "_in_use_connections", None)
            if in_use is not None:
                stats["in_use_connections"] = len(in_use)
            elif created is not None and available_conns is not None:
                stats["in_use_connections"] = created - len(available_conns)

            # Update Prometheus gauges
            if created is not None:
                REDIS_CONNECTION_POOL_SIZE.labels(pool_name=name).set(created)
            if available_conns is not None:
                REDIS_CONNECTION_POOL_AVAILABLE.labels(pool_name=name).set(
                    len(available_conns)
                )
            if "in_use_connections" in stats:
                REDIS_CONNECTION_POOL_IN_USE.labels(pool_name=name).set(
                    stats["in_use_connections"]
                )

        except Exception as e:
            stats["error"] = str(e)
            logger.debug(f"Failed to collect Redis pool stats for {name}: {e}")

        return stats

    async def collect(self) -> dict[str, Any]:
        """Collect all connection pool statistics."""
        now = datetime.now(UTC)

        # Return cached if still valid
        if self._last_collection and now - self._last_collection < self._cache_duration:
            return self._cached_metrics

        metrics: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "database": {},
            "redis": {},
        }

        # Database pools
        try:
            if self._engine is not None:
                pool = self._engine.pool
                metrics["database"]["async"] = self._collect_sqlalchemy_pool(
                    pool, "async"
                )
        except Exception as e:
            metrics["database"]["async_error"] = str(e)

        try:
            if self._sync_engine is not None:
                pool = self._sync_engine.pool
                metrics["database"]["sync"] = self._collect_sqlalchemy_pool(
                    pool, "sync"
                )
        except Exception as e:
            metrics["database"]["sync_error"] = str(e)

        # Redis pools — collect from known Redis singletons
        redis_clients: list[tuple[str, Any]] = []

        try:
            from app.core.cache import cache

            redis_clients.append(("cache", cache._redis))
        except Exception:
            pass

        try:
            from app.core.token_blacklist import token_blacklist

            redis_clients.append(("token_blacklist", token_blacklist._redis))
        except Exception:
            pass

        try:
            from app.services.redis_service import _redis_service

            if _redis_service is not None and _redis_service._client is not None:
                redis_clients.append(("redis_service", _redis_service._client))
        except Exception:
            pass

        for name, client in redis_clients:
            metrics["redis"][name] = await self._collect_redis_pool(name, client)

        # Summary
        db_total_checked_out = 0
        db_total_size = 0
        for pool_data in metrics["database"].values():
            if isinstance(pool_data, dict):
                db_total_checked_out += pool_data.get("checked_out", 0)
                db_total_size += pool_data.get("size", 0)

        metrics["summary"] = {
            "db_pool_total_size": db_total_size,
            "db_pool_total_checked_out": db_total_checked_out,
            "db_pool_utilization_pct": (
                round(db_total_checked_out / db_total_size * 100, 1)
                if db_total_size > 0
                else 0.0
            ),
            "redis_pools_configured": len(redis_clients),
            "redis_pools_connected": sum(
                1 for name, client in redis_clients if client is not None
            ),
        }

        self._cached_metrics = metrics
        self._last_collection = now

        return metrics


# =============================================================================
# Collector Registry
# =============================================================================


class CollectorRegistry:
    """
    Registry for managing all metric collectors.

    Provides centralized access to all collectors and
    coordinated metric collection.
    """

    def __init__(self) -> None:
        """Initialize collector registry."""
        self.system = SystemMetricsCollector()
        self.database = DatabaseMetricsCollector()
        self.application = ApplicationMetricsCollector()
        self.connection_pool = ConnectionPoolCollector()

    async def collect_all(self) -> dict[str, Any]:
        """Collect metrics from all collectors."""
        results = await asyncio.gather(
            self.system.collect(),
            self.database.collect(),
            self.application.collect(),
            self.connection_pool.collect(),
            return_exceptions=True,
        )

        return {
            "system": results[0]
            if not isinstance(results[0], Exception)
            else {"error": str(results[0])},
            "database": results[1]
            if not isinstance(results[1], Exception)
            else {"error": str(results[1])},
            "application": results[2]
            if not isinstance(results[2], Exception)
            else {"error": str(results[2])},
            "connection_pools": results[3]
            if not isinstance(results[3], Exception)
            else {"error": str(results[3])},
        }


# Singleton registry instance
_collector_registry: CollectorRegistry | None = None


def get_collector_registry() -> CollectorRegistry:
    """Get or create the collector registry singleton."""
    global _collector_registry
    if _collector_registry is None:
        _collector_registry = CollectorRegistry()
    return _collector_registry
