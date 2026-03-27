"""
Health check endpoint with dependency status.

Provides a comprehensive health check for load balancers, monitoring systems,
and operational dashboards. Does NOT require authentication.
"""

from __future__ import annotations

import asyncio
import shutil
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()

# Track application start time
_app_start_time: float = time.monotonic()

# ── SharePoint auth status cache ────────────────────────────────────────────
# Cache the SharePoint auth check result for 5 minutes to avoid hitting the
# Graph API on every health check request.
_sharepoint_auth_cache: dict[str, Any] | None = None
_sharepoint_auth_cache_time: float = 0.0
_SHAREPOINT_AUTH_CACHE_TTL: float = 300.0  # 5 minutes


def _get_uptime_seconds() -> float:
    return round(time.monotonic() - _app_start_time, 1)


async def _check_database(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity by executing SELECT 1."""
    try:
        start = time.monotonic()
        result = await asyncio.wait_for(
            db.execute(text("SELECT 1")),
            timeout=2.0,
        )
        _ = result.scalar()
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"status": "up", "latency_ms": latency_ms}
    except TimeoutError:
        logger.warning("Health check: database ping timed out")
        return {"status": "down", "error": "timeout"}
    except Exception as e:
        logger.warning(f"health_check_db_error: {e}")
        return {"status": "down", "error": "connection_failed"}


async def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity via ping."""
    try:
        import redis.asyncio as aioredis
    except ImportError:
        return {"status": "not_installed"}

    if not settings.REDIS_URL:
        return {"status": "not_configured"}

    try:
        start = time.monotonic()
        r = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            pong = await asyncio.wait_for(r.ping(), timeout=2.0)
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            if pong:
                return {"status": "up", "latency_ms": latency_ms}
            return {"status": "down", "error": "ping returned False"}
        finally:
            await r.aclose()
    except TimeoutError:
        return {"status": "down", "error": "timeout"}
    except Exception as e:
        logger.warning(f"health_check_redis_error: {e}")
        return {"status": "down", "error": "unavailable"}


async def _check_sharepoint_auth() -> dict[str, Any]:
    """Check SharePoint authentication status with a live Graph API call.

    Makes a lightweight GET /me request to verify the Azure AD token is valid.
    Results are cached for 5 minutes to avoid excessive Graph API calls.
    The overall health check is NOT failed if SharePoint is unreachable --
    the status is reported for operational awareness only.
    """
    global _sharepoint_auth_cache, _sharepoint_auth_cache_time  # noqa: PLW0603

    # Return cached result if still fresh
    now = time.monotonic()
    if (
        _sharepoint_auth_cache is not None
        and (now - _sharepoint_auth_cache_time) < _SHAREPOINT_AUTH_CACHE_TTL
    ):
        return _sharepoint_auth_cache

    if not settings.sharepoint_configured:
        result: dict[str, Any] = {
            "status": "not_configured",
            "last_checked": datetime.now(UTC).isoformat(),
        }
        _sharepoint_auth_cache = result
        _sharepoint_auth_cache_time = now
        return result

    try:
        from app.extraction.sharepoint import SharePointClient

        client = SharePointClient()
        token = await asyncio.wait_for(
            client._get_access_token(),
            timeout=5.0,
        )
        if token:
            result = {
                "status": "connected",
                "last_checked": datetime.now(UTC).isoformat(),
            }
        else:
            result = {
                "status": "disconnected",
                "last_checked": datetime.now(UTC).isoformat(),
                "error": "empty_token",
            }
    except TimeoutError:
        result = {
            "status": "disconnected",
            "last_checked": datetime.now(UTC).isoformat(),
            "error": "timeout",
        }
    except Exception as exc:
        error_msg = str(exc)
        # Sanitize error message -- don't leak secrets
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        result = {
            "status": "error",
            "last_checked": datetime.now(UTC).isoformat(),
            "error": error_msg,
        }
        logger.warning(f"health_check_sharepoint_error: {error_msg}")

    _sharepoint_auth_cache = result
    _sharepoint_auth_cache_time = now
    return result


def _check_external_apis() -> dict[str, Any]:
    """Check if external API keys are set."""
    result: dict[str, Any] = {}
    result["fred_api"] = {
        "status": "configured" if settings.FRED_API_KEY else "not_configured"
    }
    result["census_api"] = {
        "status": "configured" if settings.CENSUS_API_KEY else "not_configured"
    }
    return result


def _check_disk_space() -> dict[str, Any]:
    """Check free disk space on the current working directory."""
    try:
        usage = shutil.disk_usage(".")
        free_gb = round(usage.free / (1024**3), 1)
        total_gb = round(usage.total / (1024**3), 1)
        pct_free = round((usage.free / usage.total) * 100, 1)
        status = "ok" if pct_free > 5 else "low"
        return {
            "status": status,
            "free_gb": free_gb,
            "total_gb": total_gb,
            "percent_free": pct_free,
        }
    except Exception as e:
        logger.warning(f"health_check_disk_error: {e}")
        return {"status": "error", "error": "unavailable"}


def _determine_overall_status(checks: dict[str, Any]) -> str:
    """
    Determine overall health status.

    - "healthy": database up and no critical failures
    - "degraded": database up but optional services down
    - "unhealthy": database down
    """
    db_status = checks.get("database", {}).get("status")
    if db_status != "up":
        return "unhealthy"

    # Check optional services — if any are "down", mark degraded
    optional_keys = ["redis", "sharepoint", "fred_api", "census_api"]
    for key in optional_keys:
        check = checks.get(key, {})
        if check.get("status") == "down":
            return "degraded"

    return "healthy"


@router.get(
    "/ready",
    summary="Readiness probe (deep health check)",
    response_description="Core dependency readiness for load balancers and orchestrators",
)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Response:
    """
    Deep health / readiness check endpoint.

    Verifies that core dependencies (database and Redis) are reachable and
    responsive.  Returns HTTP 503 if the database is down, since the
    application cannot serve requests without it.

    Designed for Kubernetes readiness probes and load balancer health checks
    that need to verify the instance can actually handle traffic, not just
    that the process is alive.

    No authentication required.
    """
    from starlette.responses import JSONResponse

    db_check, redis_check = await asyncio.gather(
        _check_database(db),
        _check_redis(),
    )

    db_ready = db_check.get("status") == "up"
    overall_ready = db_ready  # Database is the hard requirement

    result = {
        "ready": overall_ready,
        "checks": {
            "database": db_check,
            "redis": redis_check,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }

    status_code = 200 if overall_ready else 503
    return JSONResponse(content=result, status_code=status_code)


@router.get(
    "",
    summary="Health check with dependency status",
    response_description="Application health status with dependency checks",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns overall application status, individual dependency checks,
    version info, and uptime. Designed for load balancers and monitoring.

    No authentication required.
    """
    # Run async checks concurrently
    db_check, redis_check, sharepoint_check = await asyncio.gather(
        _check_database(db),
        _check_redis(),
        _check_sharepoint_auth(),
    )

    # Sync checks
    api_checks = _check_external_apis()
    disk_check = _check_disk_space()

    checks = {
        "database": db_check,
        "redis": redis_check,
        "sharepoint": sharepoint_check,
        "fred_api": api_checks["fred_api"],
        "census_api": api_checks["census_api"],
        "disk_space": disk_check,
    }

    overall_status = _determine_overall_status(checks)

    return {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
        "uptime_seconds": _get_uptime_seconds(),
    }
