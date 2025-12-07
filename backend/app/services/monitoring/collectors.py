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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from app.services.monitoring.metrics import (
    DB_CONNECTION_POOL_SIZE,
    DB_CONNECTION_POOL_CHECKED_OUT,
    ACTIVE_USERS,
    DEALS_COUNT,
    PROPERTIES_COUNT,
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

    def __init__(self):
        """Initialize system metrics collector."""
        self._last_collection: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=5)
        self._cached_metrics: Dict[str, Any] = {}

    async def collect(self) -> Dict[str, Any]:
        """Collect system metrics."""
        now = datetime.utcnow()

        # Return cached if still valid
        if (
            self._last_collection
            and now - self._last_collection < self._cache_duration
        ):
            return self._cached_metrics

        metrics = {
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
    - Connection pool status
    - Active connections
    - Query performance statistics
    """

    def __init__(self):
        """Initialize database metrics collector."""
        self._engine = None

    def set_engine(self, engine) -> None:
        """Set the SQLAlchemy engine for pool monitoring."""
        self._engine = engine

    async def collect(self) -> Dict[str, Any]:
        """Collect database metrics."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "connected": False,
            "pool": {},
        }

        if self._engine is None:
            return metrics

        try:
            # Get pool statistics
            pool = self._engine.pool

            pool_status = {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
            }

            metrics["pool"] = pool_status
            metrics["connected"] = True

            # Update Prometheus gauges
            DB_CONNECTION_POOL_SIZE.labels(pool_type="main").set(pool_status["size"])
            DB_CONNECTION_POOL_CHECKED_OUT.labels(pool_type="main").set(
                pool_status["checked_out"]
            )

        except Exception as e:
            logger.warning(f"Failed to collect database metrics: {e}")
            metrics["error"] = str(e)

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

    def __init__(self):
        """Initialize application metrics collector."""
        self._db_session_factory = None
        self._last_collection: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=30)
        self._cached_metrics: Dict[str, Any] = {}

    def set_session_factory(self, session_factory) -> None:
        """Set the database session factory for queries."""
        self._db_session_factory = session_factory

    async def collect(self) -> Dict[str, Any]:
        """Collect application metrics."""
        now = datetime.utcnow()

        # Return cached if still valid
        if (
            self._last_collection
            and now - self._last_collection < self._cache_duration
        ):
            return self._cached_metrics

        metrics = {
            "timestamp": now.isoformat(),
            "users": {},
            "deals": {},
            "properties": {},
            "underwriting_models": {},
        }

        if self._db_session_factory is None:
            return metrics

        try:
            from sqlalchemy import select, func
            from sqlalchemy.ext.asyncio import AsyncSession

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

                property_count = await session.scalar(
                    select(func.count(Property.id))
                )
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


# =============================================================================
# Collector Registry
# =============================================================================

class CollectorRegistry:
    """
    Registry for managing all metric collectors.

    Provides centralized access to all collectors and
    coordinated metric collection.
    """

    def __init__(self):
        """Initialize collector registry."""
        self.system = SystemMetricsCollector()
        self.database = DatabaseMetricsCollector()
        self.application = ApplicationMetricsCollector()

    async def collect_all(self) -> Dict[str, Any]:
        """Collect metrics from all collectors."""
        results = await asyncio.gather(
            self.system.collect(),
            self.database.collect(),
            self.application.collect(),
            return_exceptions=True,
        )

        return {
            "system": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "database": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "application": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        }


# Singleton registry instance
_collector_registry: Optional[CollectorRegistry] = None


def get_collector_registry() -> CollectorRegistry:
    """Get or create the collector registry singleton."""
    global _collector_registry
    if _collector_registry is None:
        _collector_registry = CollectorRegistry()
    return _collector_registry
