"""
Monitoring API Endpoints

Provides endpoints for:
- Prometheus metrics export
- Health check probes (liveness, readiness)
- Detailed system health information
- Performance statistics
"""

from datetime import datetime
from typing import Any  # noqa: F401 - used for type hints in collectors

from fastapi import APIRouter, Depends, Response
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.monitoring.collectors import get_collector_registry
from app.services.monitoring.metrics import get_metrics_manager

router = APIRouter()


# =============================================================================
# Prometheus Metrics Endpoint
# =============================================================================


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Export metrics in Prometheus format for scraping.",
    response_class=Response,
    tags=["monitoring"],
)
async def prometheus_metrics():
    """
    Export Prometheus metrics.

    Returns metrics in Prometheus text format for scraping by
    Prometheus server or compatible monitoring systems.
    """
    metrics_manager = get_metrics_manager()
    metrics_manager.initialize()

    return Response(
        content=metrics_manager.generate_metrics(),
        media_type=metrics_manager.content_type,
    )


# =============================================================================
# Health Check Endpoints
# =============================================================================


@router.get(
    "/health/live",
    summary="Liveness Probe",
    description="Simple liveness check - returns 200 if the service is running.",
    tags=["monitoring"],
)
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 OK if the application is running.
    Does not check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/ready",
    summary="Readiness Probe",
    description="Readiness check - verifies the service can handle requests.",
    tags=["monitoring"],
)
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.

    Returns 200 OK if the application is ready to handle requests.
    Checks database connectivity.
    """
    checks = {
        "database": False,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        checks["database_error"] = str(e)

    # Determine overall status
    is_ready = checks["database"]
    checks["status"] = "ready" if is_ready else "not_ready"

    if not is_ready:
        return Response(
            content=str(checks),
            status_code=503,
            media_type="application/json",
        )

    return checks


@router.get(
    "/health/detailed",
    summary="Detailed Health Check",
    description="Comprehensive health check with system and component status.",
    tags=["monitoring"],
)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check endpoint.

    Returns comprehensive health information including:
    - Application info
    - Database status
    - System metrics (CPU, memory, disk)
    - Component health
    """
    collector_registry = get_collector_registry()

    # Collect all metrics
    all_metrics = await collector_registry.collect_all()

    # Build health response
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
        "checks": {},
        "metrics": all_metrics,
    }

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = {
            "status": "healthy",
            "type": "postgresql",
        }
    except Exception as e:
        health["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["status"] = "degraded"

    # Redis check (if configured)
    try:
        from app.services.redis_service import get_redis_client

        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.ping()
            health["checks"]["redis"] = {"status": "healthy"}
        else:
            health["checks"]["redis"] = {"status": "not_configured"}
    except Exception as e:
        health["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    return health


# =============================================================================
# Performance Statistics
# =============================================================================


@router.get(
    "/stats",
    summary="Performance Statistics",
    description="Get current performance statistics and metrics summary.",
    tags=["monitoring"],
)
async def performance_stats():
    """
    Get performance statistics summary.

    Returns aggregated performance metrics including:
    - Request statistics
    - Database query statistics
    - Cache performance
    - System resource usage
    """
    collector_registry = get_collector_registry()

    # Collect system metrics
    system_metrics = await collector_registry.system.collect()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_metrics,
        "note": "For detailed metrics, use /monitoring/metrics endpoint",
    }


@router.get(
    "/info",
    summary="Application Info",
    description="Get application information and configuration (non-sensitive).",
    tags=["monitoring"],
)
async def application_info():
    """
    Get application information.

    Returns non-sensitive application configuration
    useful for debugging and monitoring.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "server": {
            "host": settings.HOST,
            "port": settings.PORT,
            "workers": settings.WORKERS,
        },
        "features": {
            "websocket": True,
            "ml_predictions": True,
            "email_notifications": bool(settings.SMTP_USER),
            "redis_cache": bool(settings.REDIS_URL),
        },
        "api": {
            "version": "v1",
            "docs_enabled": settings.DEBUG,
        },
    }
