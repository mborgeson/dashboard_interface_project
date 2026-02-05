"""
Admin endpoints for market data extraction management.

Provides manual triggers for FRED, CoStar, and Census extractions,
status/freshness reporting, and materialized view refresh.

All endpoints require admin-level authentication.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger

from app.core.permissions import CurrentUser, require_admin
from app.services.data_extraction.scheduler import get_market_data_scheduler

router = APIRouter(prefix="/admin/market-data", tags=["Admin - Market Data"])


# ---------------------------------------------------------------------------
# Manual extraction triggers
# ---------------------------------------------------------------------------


@router.post("/extract/fred", summary="Trigger FRED extraction")
async def trigger_fred_extraction(
    background_tasks: BackgroundTasks,
    incremental: bool = True,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    """Manually trigger FRED data extraction.

    Runs the extraction as a background task so the response returns
    immediately.  Use ``GET /status`` to monitor progress.

    Query params:
        incremental: If True (default), only fetches data newer than the
            latest date already in the database.
    """
    scheduler = get_market_data_scheduler()

    async def _run() -> None:
        result = await scheduler.run_fred_extraction(incremental=incremental)
        logger.info(
            "admin_fred_extraction_complete",
            triggered_by=current_user.email,
            result=result,
        )

    background_tasks.add_task(_run)

    return {
        "message": "FRED extraction started",
        "incremental": incremental,
        "triggered_by": current_user.email,
    }


@router.post("/extract/costar", summary="Trigger CoStar extraction")
async def trigger_costar_extraction(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    """Manually trigger CoStar data extraction.

    Parses all Excel files in the configured ``COSTAR_DATA_DIR`` and
    upserts rows into ``costar_timeseries``.  Runs as a background task.
    """
    scheduler = get_market_data_scheduler()

    async def _run() -> None:
        result = await scheduler.run_costar_extraction()
        logger.info(
            "admin_costar_extraction_complete",
            triggered_by=current_user.email,
            result=result,
        )

    background_tasks.add_task(_run)

    return {
        "message": "CoStar extraction started",
        "triggered_by": current_user.email,
    }


@router.post("/extract/census", summary="Trigger Census extraction")
async def trigger_census_extraction(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    """Manually trigger Census Bureau ACS data extraction.

    Fetches ACS 5-year estimates for the Phoenix MSA across all
    available years (2010-2024).  Runs as a background task.
    """
    scheduler = get_market_data_scheduler()

    async def _run() -> None:
        result = await scheduler.run_census_extraction()
        logger.info(
            "admin_census_extraction_complete",
            triggered_by=current_user.email,
            result=result,
        )

    background_tasks.add_task(_run)

    return {
        "message": "Census extraction started",
        "triggered_by": current_user.email,
    }


@router.post("/extract/all", summary="Trigger all extractions")
async def trigger_all_extractions(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    """Manually trigger all market data extractions (FRED, CoStar, Census).

    Extractions run sequentially in the background: FRED -> CoStar -> Census.
    Use ``GET /status`` to monitor progress.
    """
    scheduler = get_market_data_scheduler()

    async def _run() -> None:
        result = await scheduler.run_all()
        logger.info(
            "admin_all_extractions_complete",
            triggered_by=current_user.email,
            result=result,
        )

    background_tasks.add_task(_run)

    return {
        "message": "All extractions started (FRED -> CoStar -> Census)",
        "triggered_by": current_user.email,
    }


# ---------------------------------------------------------------------------
# Status and monitoring
# ---------------------------------------------------------------------------


@router.get("/status", summary="Get market data status")
async def get_market_data_status(
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    """Get data freshness and extraction status.

    Returns:
        - Last extraction time per source
        - Record counts per source
        - Next scheduled run times
        - Recent extraction log entries
        - Scheduler running state
    """
    scheduler = get_market_data_scheduler()
    try:
        status = await scheduler.get_status()
        return status
    except Exception as exc:
        logger.error("market_data_status_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve market data status: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Materialized view management
# ---------------------------------------------------------------------------


@router.post("/refresh-views", summary="Refresh materialized views")
async def refresh_materialized_views(
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    """Manually refresh materialized views (costar_latest, fred_latest).

    Attempts a concurrent refresh first, falling back to a standard
    refresh if the view lacks a unique index.
    """
    scheduler = get_market_data_scheduler()
    try:
        results = await scheduler.refresh_materialized_views()
        logger.info(
            "admin_views_refreshed",
            triggered_by=current_user.email,
            results=results,
        )
        return {
            "message": "Materialized views refreshed",
            "views": results,
            "triggered_by": current_user.email,
        }
    except Exception as exc:
        logger.error("materialized_view_refresh_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh materialized views: {exc}",
        ) from exc
