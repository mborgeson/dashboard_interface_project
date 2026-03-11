"""
ARQ worker configuration.

Provides Redis connection settings and worker configuration for the
ARQ background task worker. Start with:

    arq app.tasks.config.WorkerSettings

Settings are loaded from the application config (REDIS_URL env var).
"""

from __future__ import annotations

from urllib.parse import urlparse

from arq.connections import RedisSettings
from loguru import logger


def get_redis_settings() -> RedisSettings:
    """Get Redis settings from app config, with fallback to localhost.

    Parses the REDIS_URL from application settings. Supports the standard
    ``redis://host:port/db`` URL format.

    Returns:
        RedisSettings configured for the application's Redis instance.
    """
    try:
        from app.core.config import settings

        redis_url = settings.REDIS_URL
    except Exception:
        redis_url = "redis://localhost:6379/0"

    if redis_url:
        try:
            parsed = urlparse(redis_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            database = int(parsed.path.lstrip("/") or "0")
            password = parsed.password

            return RedisSettings(
                host=host,
                port=port,
                database=database,
                password=password,
                conn_timeout=5,
                conn_retries=3,
                conn_retry_delay=1,
            )
        except Exception as exc:
            logger.warning(f"Failed to parse REDIS_URL, using defaults: {exc}")

    return RedisSettings()  # localhost:6379/0 default


def _get_task_functions() -> list:  # type: ignore[type-arg]
    """Import and return all registered task functions.

    Deferred import avoids circular dependencies at module load time.
    """
    from app.tasks.extraction import run_extraction_task
    from app.tasks.market_data import (
        refresh_all_market_data_task,
        refresh_census_data_task,
        refresh_costar_data_task,
        refresh_fred_data_task,
    )
    from app.tasks.reports import generate_report_task

    return [
        refresh_fred_data_task,
        refresh_costar_data_task,
        refresh_census_data_task,
        refresh_all_market_data_task,
        generate_report_task,
        run_extraction_task,
    ]


class WorkerSettings:
    """ARQ worker settings.

    Used by the ARQ CLI to configure the worker process:

        arq app.tasks.config.WorkerSettings

    Attributes:
        functions: Task functions registered with the worker.
        redis_settings: Connection settings for the Redis broker.
        max_jobs: Maximum concurrent jobs per worker.
        job_timeout: Default timeout (seconds) for each job.
        retry_jobs: Whether to retry failed jobs.
        max_tries: Maximum number of attempts per job.
        health_check_interval: Interval (seconds) for worker health checks.
    """

    functions = _get_task_functions()

    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 300  # 5 minutes default
    retry_jobs = True
    max_tries = 3
    health_check_interval = 30
