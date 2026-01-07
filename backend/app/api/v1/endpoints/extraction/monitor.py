"""
File monitoring endpoints.

Endpoints for managing SharePoint file monitoring and change detection.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.extraction.sharepoint import SharePointAuthError
from app.models.file_monitor import MonitoredFile

from .common import logger

router = APIRouter()


@router.get("/monitor/status")
async def get_monitor_status(db: AsyncSession = Depends(get_db)):
    """
    Get the current status of the file monitoring system.

    Returns information about:
    - Whether monitoring is enabled
    - Check interval in minutes
    - Auto-extraction setting
    - Last and next check times
    - Total monitored files
    - Files pending extraction
    """
    from app.crud.file_monitor import MonitoredFileCRUD
    from app.schemas.file_monitor import MonitorStatusResponse
    from app.services.extraction.monitor_scheduler import get_monitor_scheduler

    scheduler = get_monitor_scheduler()
    status = scheduler.get_status()

    # Get file statistics
    stats = await MonitoredFileCRUD.get_stats(db)

    return MonitorStatusResponse(
        enabled=status["enabled"],
        interval_minutes=status["interval_minutes"],
        auto_extract=status["auto_extract"],
        last_check=datetime.fromisoformat(status["last_check"])
        if status["last_check"]
        else None,
        next_check=datetime.fromisoformat(status["next_check"])
        if status["next_check"]
        else None,
        total_monitored_files=stats["total_files"],
        files_pending_extraction=stats["pending_extraction"],
        is_checking=status["is_checking"],
    )


@router.get("/monitor/changes")
async def get_recent_changes(
    limit: int = 50,
    offset: int = 0,
    change_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent file changes detected by monitoring.

    Args:
        limit: Maximum number of changes to return (default 50)
        offset: Number of changes to skip for pagination
        change_type: Filter by change type (added, modified, deleted)

    Returns:
        List of recent file changes with pagination info.
    """
    from app.crud.file_monitor import FileChangeLogCRUD
    from app.schemas.file_monitor import FileChangeInfo, RecentChangesResponse

    changes = await FileChangeLogCRUD.get_recent(
        db, limit=limit, offset=offset, change_type=change_type
    )
    total = await FileChangeLogCRUD.get_total_count(db)

    return RecentChangesResponse(
        changes=[
            FileChangeInfo(
                file_path=c.file_path,
                file_name=c.file_name,
                change_type=c.change_type,
                deal_name=c.deal_name,
                old_modified_date=c.old_modified_date,
                new_modified_date=c.new_modified_date,
                old_size_bytes=c.old_size_bytes,
                new_size_bytes=c.new_size_bytes,
                detected_at=c.detected_at,
            )
            for c in changes
        ],
        total=total,
        has_more=offset + limit < total,
    )


@router.post("/monitor/check")
async def trigger_monitor_check(db: AsyncSession = Depends(get_db)):
    """
    Trigger a manual file monitoring check.

    Scans SharePoint for file changes immediately, without waiting
    for the next scheduled check. Returns details of any changes detected.

    Note: This endpoint may take several seconds depending on the
    number of files to scan.
    """
    from app.schemas.file_monitor import FileChangeInfo, MonitorCheckResponse
    from app.services.extraction.file_monitor import SharePointFileMonitor

    try:
        monitor = SharePointFileMonitor(db)
        result = await monitor.check_for_changes(
            auto_trigger_extraction=settings.AUTO_EXTRACT_ON_CHANGE
        )

        return MonitorCheckResponse(
            changes_detected=result.changes_detected,
            files_added=result.files_added,
            files_modified=result.files_modified,
            files_deleted=result.files_deleted,
            extraction_triggered=result.extraction_triggered,
            extraction_run_id=result.extraction_run_id,
            changes=[
                FileChangeInfo(
                    file_path=c.file_path,
                    file_name=c.file_name,
                    change_type=c.change_type,
                    deal_name=c.deal_name,
                    old_modified_date=c.old_modified_date,
                    new_modified_date=c.new_modified_date,
                    old_size_bytes=c.old_size_bytes,
                    new_size_bytes=c.new_size_bytes,
                    detected_at=c.detected_at or datetime.utcnow(),
                )
                for c in result.changes
            ],
            check_duration_seconds=result.check_duration_seconds,
        )

    except SharePointAuthError as e:
        raise HTTPException(
            status_code=401,
            detail=f"SharePoint authentication failed: {e}",
        ) from None
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None


@router.get("/monitor/files")
async def list_monitored_files(
    deal_name: str | None = None,
    pending_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List files being monitored.

    Args:
        deal_name: Filter by deal name
        pending_only: Only return files pending extraction
        limit: Maximum number of files to return
        offset: Number of files to skip for pagination

    Returns:
        List of monitored files with metadata.
    """
    from app.schemas.file_monitor import MonitoredFileInfo, MonitoredFilesResponse

    # Build query
    stmt = select(MonitoredFile).where(MonitoredFile.is_active.is_(True))

    if deal_name:
        stmt = stmt.where(MonitoredFile.deal_name == deal_name)
    if pending_only:
        stmt = stmt.where(MonitoredFile.extraction_pending.is_(True))

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Get pending count
    pending_stmt = select(func.count(MonitoredFile.id)).where(
        MonitoredFile.is_active.is_(True),
        MonitoredFile.extraction_pending.is_(True),
    )
    pending = (await db.execute(pending_stmt)).scalar_one()

    # Apply pagination
    stmt = stmt.order_by(MonitoredFile.deal_name, MonitoredFile.file_name)
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    files = result.scalars().all()

    return MonitoredFilesResponse(
        files=[
            MonitoredFileInfo(
                id=f.id,
                file_path=f.file_path,
                file_name=f.file_name,
                deal_name=f.deal_name,
                size_bytes=f.size_bytes,
                modified_date=f.modified_date,
                first_seen=f.first_seen,
                last_checked=f.last_checked,
                last_extracted=f.last_extracted,
                is_active=f.is_active,
                extraction_pending=f.extraction_pending,
                deal_stage=f.deal_stage,
            )
            for f in files
        ],
        total=total,
        pending_extraction=pending,
    )


@router.post("/monitor/enable")
async def enable_monitor():
    """
    Enable file monitoring.

    Starts the file monitor scheduler with the current configuration.
    """
    from app.services.extraction.monitor_scheduler import get_monitor_scheduler

    scheduler = get_monitor_scheduler()

    try:
        status = await scheduler.enable()
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable monitoring: {e}",
        ) from None

    logger.info(
        "file_monitor_enabled",
        next_check=status.get("next_check"),
        interval_minutes=status.get("interval_minutes"),
    )

    return {
        "message": "File monitoring enabled",
        "status": status,
    }


@router.post("/monitor/disable")
async def disable_monitor():
    """
    Disable file monitoring.

    Stops the file monitor scheduler. No automatic checks will run
    until re-enabled. Does not affect any currently running check.
    """
    from app.services.extraction.monitor_scheduler import get_monitor_scheduler

    scheduler = get_monitor_scheduler()

    try:
        status = await scheduler.disable()
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable monitoring: {e}",
        ) from None

    logger.info("file_monitor_disabled")

    return {
        "message": "File monitoring disabled",
        "status": status,
    }


@router.put("/monitor/config")
async def update_monitor_config(
    enabled: bool | None = None,
    interval_minutes: int | None = None,
    auto_extract: bool | None = None,
):
    """
    Update file monitor configuration.

    Args:
        enabled: Enable or disable monitoring
        interval_minutes: Check interval in minutes (5-1440)
        auto_extract: Auto-trigger extraction on changes

    Changes take effect immediately.
    """
    from app.services.extraction.monitor_scheduler import get_monitor_scheduler

    scheduler = get_monitor_scheduler()

    try:
        status = await scheduler.update_config(
            enabled=enabled,
            interval_minutes=interval_minutes,
            auto_extract=auto_extract,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update configuration: {e}",
        ) from None

    logger.info(
        "file_monitor_config_updated",
        enabled=status.get("enabled"),
        interval_minutes=status.get("interval_minutes"),
        auto_extract=status.get("auto_extract"),
    )

    return {
        "message": "Configuration updated",
        "status": status,
    }
