"""
Fallback mechanism for task execution without Redis.

When Redis is unavailable, tasks are executed inline (in-process)
rather than being queued. This ensures the application works without
Redis as a hard dependency.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from loguru import logger


async def enqueue_or_run_inline(
    task_func: Callable[..., Any],
    *args: Any,
    _job_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Try to enqueue via ARQ; fall back to running inline if Redis is unavailable.

    This is the primary entry point for dispatching background work.
    It provides graceful degradation: tasks run in the ARQ queue when
    Redis is available, and execute inline (blocking) when it is not.

    Args:
        task_func: The async task function to execute.
        *args: Positional arguments for the task.
        _job_id: Optional custom job ID for deduplication.
        **kwargs: Keyword arguments for the task.

    Returns:
        Dictionary with execution result:
        - job_id: The job/execution identifier
        - mode: "queued" or "inline"
        - result: Task return value (inline mode only)
    """
    # Try ARQ queue first
    try:
        from app.tasks import registry

        job_id = await registry.enqueue_task(
            task_func.__name__,
            *args,
            _job_id=_job_id,
            **kwargs,
        )
        logger.info(f"Task {task_func.__name__} enqueued via ARQ (job_id={job_id})")
        return {
            "job_id": job_id,
            "mode": "queued",
        }
    except Exception as exc:
        logger.warning(f"Redis unavailable, running {task_func.__name__} inline: {exc}")

    # Fallback: run inline
    inline_id = _job_id or f"inline-{uuid.uuid4().hex[:12]}"
    try:
        # ARQ tasks receive a ctx dict as the first argument
        ctx: dict[str, Any] = {"job_id": inline_id, "inline": True}
        result = await task_func(ctx, *args, **kwargs)
        logger.info(f"Task {task_func.__name__} completed inline (id={inline_id})")
        return {
            "job_id": inline_id,
            "mode": "inline",
            "result": result,
        }
    except Exception as inline_exc:
        logger.error(f"Inline task {task_func.__name__} failed: {inline_exc}")
        return {
            "job_id": inline_id,
            "mode": "inline",
            "error": str(inline_exc),
        }
