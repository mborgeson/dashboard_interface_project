"""
ARQ task definitions for market data extraction.

Thin wrappers around existing service functions in
``app.services.data_extraction.scheduler``.
"""

from __future__ import annotations

from typing import Any

from loguru import logger


async def refresh_fred_data_task(
    ctx: dict[str, Any],
    incremental: bool = True,
) -> dict[str, Any]:
    """ARQ task: Refresh market data from the FRED API.

    Wraps ``MarketDataScheduler.run_fred_extraction()``.

    Args:
        ctx: ARQ job context (contains job_id, etc.).
        incremental: If True, only fetch data newer than existing records.

    Returns:
        Extraction result dictionary from the scheduler.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[task:{job_id}] Starting FRED extraction (incremental={incremental})")

    from app.services.data_extraction.scheduler import get_market_data_scheduler

    scheduler = get_market_data_scheduler()
    result = await scheduler.run_fred_extraction(incremental=incremental)

    logger.info(f"[task:{job_id}] FRED extraction complete", result=result)
    return {"source": "fred", "incremental": incremental, "result": result}


async def refresh_costar_data_task(
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """ARQ task: Refresh CoStar submarket data.

    Wraps ``MarketDataScheduler.run_costar_extraction()``.

    Args:
        ctx: ARQ job context.

    Returns:
        Extraction result dictionary.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[task:{job_id}] Starting CoStar extraction")

    from app.services.data_extraction.scheduler import get_market_data_scheduler

    scheduler = get_market_data_scheduler()
    result = await scheduler.run_costar_extraction()

    logger.info(f"[task:{job_id}] CoStar extraction complete", result=result)
    return {"source": "costar", "result": result}


async def refresh_census_data_task(
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """ARQ task: Refresh Census Bureau ACS data.

    Wraps ``MarketDataScheduler.run_census_extraction()``.

    Args:
        ctx: ARQ job context.

    Returns:
        Extraction result dictionary.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[task:{job_id}] Starting Census extraction")

    from app.services.data_extraction.scheduler import get_market_data_scheduler

    scheduler = get_market_data_scheduler()
    result = await scheduler.run_census_extraction()

    logger.info(f"[task:{job_id}] Census extraction complete", result=result)
    return {"source": "census", "result": result}


async def refresh_all_market_data_task(
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """ARQ task: Refresh all market data sources sequentially.

    Runs FRED -> CoStar -> Census in order. Wraps
    ``MarketDataScheduler.run_all()``.

    Args:
        ctx: ARQ job context.

    Returns:
        Combined result from all sources.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[task:{job_id}] Starting all market data extractions")

    from app.services.data_extraction.scheduler import get_market_data_scheduler

    scheduler = get_market_data_scheduler()
    result = await scheduler.run_all()

    logger.info(f"[task:{job_id}] All market data extractions complete", result=result)
    return {"source": "all", "result": result}
