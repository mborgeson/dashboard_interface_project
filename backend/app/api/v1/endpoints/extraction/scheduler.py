"""
Extraction scheduler endpoints.

Endpoints for managing scheduled extraction runs.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.extraction import (
    SchedulerConfigRequest,
    SchedulerStatusResponse,
)
from app.services.extraction.scheduler import get_extraction_scheduler

from .common import logger

router = APIRouter()


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """
    Get the current status of the extraction scheduler.

    Returns information about:
    - Whether scheduling is enabled
    - The cron expression for scheduling
    - The timezone for scheduling
    - Next scheduled run time
    - Last run timestamp
    - Whether an extraction is currently in progress
    """
    scheduler = get_extraction_scheduler()
    status = scheduler.get_status()

    return SchedulerStatusResponse(
        enabled=status["enabled"],
        cron_expression=status["cron_expression"],
        timezone=status["timezone"],
        next_run=status["next_run"],
        last_run=status["last_run"],
        last_run_id=status["last_run_id"],
        running=status["running"],
    )


@router.post("/scheduler/enable", response_model=SchedulerStatusResponse)
async def enable_scheduler():
    """
    Enable scheduled extractions.

    Starts the scheduler with the current cron configuration.
    The scheduler will run extractions automatically according to the schedule.
    """
    scheduler = get_extraction_scheduler()

    try:
        status = await scheduler.enable()
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable scheduler: {e}",
        ) from None

    logger.info(
        "scheduler_enabled",
        next_run=status.get("next_run"),
        cron_expression=status.get("cron_expression"),
    )

    return SchedulerStatusResponse(
        enabled=status["enabled"],
        cron_expression=status["cron_expression"],
        timezone=status["timezone"],
        next_run=status["next_run"],
        last_run=status["last_run"],
        last_run_id=status["last_run_id"],
        running=status["running"],
    )


@router.post("/scheduler/disable", response_model=SchedulerStatusResponse)
async def disable_scheduler():
    """
    Disable scheduled extractions.

    Stops the scheduler. No automatic extractions will run until re-enabled.
    Does not affect any currently running extraction.
    """
    scheduler = get_extraction_scheduler()

    try:
        status = await scheduler.disable()
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable scheduler: {e}",
        ) from None

    logger.info("scheduler_disabled")

    return SchedulerStatusResponse(
        enabled=status["enabled"],
        cron_expression=status["cron_expression"],
        timezone=status["timezone"],
        next_run=status["next_run"],
        last_run=status["last_run"],
        last_run_id=status["last_run_id"],
        running=status["running"],
    )


@router.put("/scheduler/config", response_model=SchedulerStatusResponse)
async def update_scheduler_config(request: SchedulerConfigRequest):
    """
    Update scheduler configuration.

    Allows updating:
    - enabled: Enable or disable the scheduler
    - cron_expression: The cron schedule (e.g., "0 2 * * *" for daily at 2 AM)
    - timezone: The timezone for scheduling (e.g., "America/Phoenix")

    Changes take effect immediately. If the scheduler is enabled,
    the next run time will be recalculated based on the new configuration.
    """
    scheduler = get_extraction_scheduler()

    try:
        status = await scheduler.update_config(
            enabled=request.enabled,
            cron_expression=request.cron_expression,
            timezone=request.timezone,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update scheduler configuration: {e}",
        ) from None

    logger.info(
        "scheduler_config_updated",
        enabled=status.get("enabled"),
        cron_expression=status.get("cron_expression"),
        timezone=status.get("timezone"),
        next_run=status.get("next_run"),
    )

    return SchedulerStatusResponse(
        enabled=status["enabled"],
        cron_expression=status["cron_expression"],
        timezone=status["timezone"],
        next_run=status["next_run"],
        last_run=status["last_run"],
        last_run_id=status["last_run_id"],
        running=status["running"],
    )
