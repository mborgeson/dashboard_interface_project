"""
External task queue infrastructure using ARQ (async Redis queue).

Replaces inline BackgroundTasks with a persistent, retryable task queue.
Falls back to inline execution when Redis is unavailable.

Usage:
    from app.tasks import enqueue_or_run_inline
    from app.tasks.market_data import refresh_market_data_task

    job_id = await enqueue_or_run_inline(
        refresh_market_data_task, incremental=True
    )

Worker startup (requires Redis):
    arq app.tasks.config.WorkerSettings
"""

from app.tasks.fallback import enqueue_or_run_inline
from app.tasks.registry import enqueue_task, get_task_pool, get_task_status

__all__ = [
    "enqueue_or_run_inline",
    "enqueue_task",
    "get_task_pool",
    "get_task_status",
]
