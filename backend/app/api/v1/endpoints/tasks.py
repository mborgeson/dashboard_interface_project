"""
Task status API endpoints.

Provides visibility into background task status for jobs dispatched
via the ARQ task queue. Requires analyst-level authentication.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.permissions import CurrentUser, require_analyst

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "/{job_id}",
    summary="Get background task status",
    description="Get the current status of a background task by its job ID. "
    "Returns status, timing, and result information.",
    responses={
        200: {
            "description": "Task status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "abc123",
                        "status": "complete",
                        "function": "refresh_fred_data_task",
                        "start_time": "2026-03-11T10:00:00",
                        "finish_time": "2026-03-11T10:01:30",
                        "success": True,
                        "result": {"source": "fred", "records": 150},
                    }
                }
            },
        },
        503: {"description": "Redis unavailable — task queue not configured"},
    },
)
async def get_task_status(
    job_id: str,
    _: CurrentUser = Depends(require_analyst),
) -> dict[str, Any]:
    """Get the status of a background task.

    Queries the ARQ Redis backend for the job's current status.
    Returns 503 if Redis is not available (task queue not configured).
    """
    try:
        from app.tasks.registry import get_task_status as _get_status

        status = await _get_status(job_id)
        return status
    except Exception as exc:
        logger.warning(f"Failed to get task status for {job_id}: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Task queue not available. Redis may not be configured.",
        ) from exc


@router.get(
    "",
    summary="Task queue health",
    description="Check whether the ARQ task queue is reachable.",
    responses={
        200: {
            "description": "Task queue is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "backend": "redis",
                    }
                }
            },
        },
        503: {"description": "Task queue unavailable"},
    },
)
async def task_queue_health(
    _: CurrentUser = Depends(require_analyst),
) -> dict[str, Any]:
    """Check task queue health.

    Attempts to connect to Redis and returns the connection status.
    """
    try:
        from app.tasks.registry import get_task_pool

        pool = await get_task_pool()
        # Ping to verify connection is alive
        info = await pool.info()
        return {
            "status": "healthy",
            "backend": "redis",
            "redis_version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", "unknown"),
        }
    except Exception as exc:
        logger.warning(f"Task queue health check failed: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Task queue not available. Redis may not be configured.",
        ) from exc
