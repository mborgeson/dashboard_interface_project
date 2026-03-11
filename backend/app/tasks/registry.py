"""
Task registration and dispatch via ARQ Redis pool.

Provides functions to enqueue tasks, check their status, and manage
the ARQ connection pool lifecycle.
"""

from __future__ import annotations

from typing import Any

from arq.connections import ArqRedis, create_pool
from arq.jobs import Job, JobStatus
from loguru import logger

from app.tasks.config import get_redis_settings

_pool: ArqRedis | None = None


async def get_task_pool() -> ArqRedis:
    """Get or create the ARQ Redis connection pool.

    Returns:
        ArqRedis connection pool for enqueuing and querying jobs.

    Raises:
        ConnectionError: If Redis is unreachable.
    """
    global _pool
    if _pool is None:
        redis_settings = get_redis_settings()
        _pool = await create_pool(redis_settings)
        logger.info("ARQ Redis connection pool created")
    return _pool


async def close_task_pool() -> None:
    """Close the ARQ Redis connection pool.

    Should be called during application shutdown.
    """
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("ARQ Redis connection pool closed")


async def enqueue_task(
    task_name: str,
    *args: Any,
    _job_id: str | None = None,
    _queue_name: str | None = None,
    _defer_by: float | None = None,
    **kwargs: Any,
) -> str:
    """Enqueue a task and return the job ID.

    Args:
        task_name: Name of the registered task function.
        *args: Positional arguments passed to the task.
        _job_id: Optional custom job ID (for deduplication).
        _queue_name: Optional queue name override.
        _defer_by: Delay execution by N seconds.
        **kwargs: Keyword arguments passed to the task.

    Returns:
        The job ID string for tracking.

    Raises:
        ConnectionError: If Redis is unreachable.
    """
    pool = await get_task_pool()

    enqueue_kwargs: dict[str, Any] = {}
    if _job_id is not None:
        enqueue_kwargs["_job_id"] = _job_id
    if _queue_name is not None:
        enqueue_kwargs["_queue_name"] = _queue_name
    if _defer_by is not None:
        from datetime import timedelta

        enqueue_kwargs["_defer_by"] = timedelta(seconds=_defer_by)

    job = await pool.enqueue_job(task_name, *args, **kwargs, **enqueue_kwargs)

    if job is None:
        # Job already exists with this ID (deduplication)
        logger.warning(f"Task {task_name} already queued with ID {_job_id}")
        return _job_id or "unknown"

    logger.info(f"Enqueued task {task_name} with job_id={job.job_id}")
    return job.job_id


async def get_task_status(job_id: str) -> dict[str, Any]:
    """Get the status of a queued task.

    Args:
        job_id: The job ID returned from enqueue_task.

    Returns:
        Dictionary with job status information:
        - job_id: The job identifier
        - status: One of: unknown, queued, in_progress, complete, not_found
        - result: The job result (if complete)
        - start_time: When the job started (if available)
        - finish_time: When the job finished (if available)
        - success: Whether the job succeeded (if complete)

    Raises:
        ConnectionError: If Redis is unreachable.
    """
    pool = await get_task_pool()
    job = Job(job_id, redis=pool)

    status = await job.status()

    result: dict[str, Any] = {
        "job_id": job_id,
        "status": status.value if isinstance(status, JobStatus) else str(status),
    }

    # Fetch additional info for completed/in-progress jobs
    info = await job.info()
    if info is not None:
        result["start_time"] = getattr(info, "start_time", None)
        if result["start_time"] is not None:
            result["start_time"] = result["start_time"].isoformat()
        result["finish_time"] = getattr(info, "finish_time", None)
        if result["finish_time"] is not None:
            result["finish_time"] = result["finish_time"].isoformat()
        success = getattr(info, "success", None)
        result["success"] = success
        result["function"] = info.function
        result["queue_name"] = getattr(info, "queue_name", None)

        job_result = getattr(info, "result", None)
        if success is True:
            result["result"] = job_result
        elif success is False:
            result["result"] = str(job_result) if job_result else None

    return result
