"""
Extraction API endpoints for SharePoint UW model data extraction.

Endpoints:
- POST /extraction/start - Start a new extraction
- GET /extraction/status - Get current extraction status
- GET /extraction/history - List past extractions
- POST /extraction/cancel - Cancel running extraction
- GET /extraction/properties - List extracted properties
- GET /extraction/properties/{name} - Get property data
- GET /extraction/scheduler/status - Get scheduler status
- POST /extraction/scheduler/enable - Enable scheduled extraction
- POST /extraction/scheduler/disable - Disable scheduled extraction
- PUT /extraction/scheduler/config - Update schedule configuration
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.session import get_db
from app.extraction.file_filter import get_file_filter
from app.extraction.sharepoint import (
    SharePointAuthError,
    SharePointClient,
    SharePointFile,
)
from app.schemas.extraction import (
    ExtractionHistoryItem,
    ExtractionHistoryResponse,
    ExtractionStartRequest,
    ExtractionStartResponse,
    ExtractionStatusResponse,
    FileFilterConfig,
    FileFilterResponse,
    PropertyListResponse,
    SchedulerConfigRequest,
    SchedulerStatusResponse,
)
from app.services.extraction.scheduler import get_extraction_scheduler

logger = structlog.get_logger().bind(component="extraction_api")

router = APIRouter()

# Path to reference file
REFERENCE_FILE = Path(__file__).parent.parent.parent.parent.parent / (
    "Underwriting_Dashboard_Cell_References.xlsx"
)


async def _discover_sharepoint_files() -> list[SharePointFile]:
    """
    Discover UW model files from SharePoint.

    Returns:
        List of SharePointFile objects for discovered UW models.

    Raises:
        SharePointAuthError: If authentication fails.
        ValueError: If SharePoint is not configured.
    """
    if not settings.sharepoint_configured:
        missing = settings.get_sharepoint_config_errors()
        raise ValueError(f"SharePoint not configured. Missing: {', '.join(missing)}")

    client = SharePointClient()
    logger.info("sharepoint_discovery_started", site_url=settings.SHAREPOINT_SITE_URL)

    files = await client.find_uw_models()
    logger.info("sharepoint_files_discovered", count=len(files))

    return files


async def _download_sharepoint_file(
    client: SharePointClient, file: SharePointFile, temp_dir: str
) -> str:
    """
    Download a SharePoint file to a temporary directory.

    Args:
        client: SharePointClient instance.
        file: SharePointFile to download.
        temp_dir: Temporary directory path.

    Returns:
        Path to the downloaded file.
    """
    content = await client.download_file(file)
    local_path = Path(temp_dir) / file.name
    local_path.write_bytes(content)
    logger.info(
        "sharepoint_file_downloaded",
        name=file.name,
        size=len(content),
        deal_name=file.deal_name,
    )
    return str(local_path)


def run_extraction_task(
    run_id: UUID, db: Session, source: str, file_paths: list | None = None
):
    """
    Background task to run extraction.

    This is executed in a separate thread by FastAPI BackgroundTasks.
    Supports both local files and SharePoint sources.
    """
    from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
    from app.extraction import CellMappingParser

    try:
        # Load mappings
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()

        # Determine files to process based on source
        if source == "local" and file_paths:
            # Local file extraction
            files_to_process = [
                {
                    "file_path": p,
                    "deal_name": Path(p).stem.replace(" UW Model vCurrent", ""),
                }
                for p in file_paths
            ]
            logger.info("local_extraction_started", file_count=len(files_to_process))

        elif source == "sharepoint":
            # SharePoint extraction - run async discovery in sync context
            logger.info("sharepoint_extraction_started")

            try:
                # Create new event loop for async operations in background thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    sharepoint_files = loop.run_until_complete(
                        _discover_sharepoint_files()
                    )

                    if not sharepoint_files:
                        logger.warning("no_sharepoint_files_found")
                        ExtractionRunCRUD.complete(
                            db, run_id, files_processed=0, files_failed=0
                        )
                        return

                    # Download files to temp directory
                    client = SharePointClient()
                    files_to_process = []

                    with tempfile.TemporaryDirectory(prefix="uw_models_") as temp_dir:
                        for sp_file in sharepoint_files:
                            try:
                                local_path = loop.run_until_complete(
                                    _download_sharepoint_file(client, sp_file, temp_dir)
                                )
                                files_to_process.append(
                                    {
                                        "file_path": local_path,
                                        "deal_name": sp_file.deal_name,
                                        "deal_stage": sp_file.deal_stage,
                                        "sharepoint_path": sp_file.path,
                                    }
                                )
                            except Exception as e:
                                logger.error(
                                    "sharepoint_download_failed",
                                    file=sp_file.name,
                                    error=str(e),
                                )

                        # Process downloaded files within temp directory context
                        _process_files(
                            db,
                            run_id,
                            files_to_process,
                            mappings,
                            ExtractionRunCRUD,
                            ExtractedValueCRUD,
                        )
                        return
                finally:
                    loop.close()

            except SharePointAuthError as e:
                logger.error("sharepoint_auth_failed", error=str(e))
                ExtractionRunCRUD.fail(
                    db,
                    run_id,
                    {
                        "error": "SharePoint authentication failed",
                        "details": str(e),
                    },
                )
                return

            except ValueError as e:
                logger.error("sharepoint_config_error", error=str(e))
                ExtractionRunCRUD.fail(
                    db,
                    run_id,
                    {
                        "error": "SharePoint configuration error",
                        "details": str(e),
                    },
                )
                return

        else:
            # Fallback to test fixtures for development/testing
            logger.info("fixture_extraction_started", source=source)
            fixtures_dir = (
                Path(__file__).parent.parent.parent.parent.parent
                / "tests"
                / "fixtures"
                / "uw_models"
            )
            files_to_process = [
                {
                    "file_path": str(f),
                    "deal_name": f.stem.replace(" UW Model vCurrent", ""),
                }
                for f in fixtures_dir.glob("*.xlsb")
            ]

        # Process files (for local and fixture sources)
        _process_files(
            db,
            run_id,
            files_to_process,
            mappings,
            ExtractionRunCRUD,
            ExtractedValueCRUD,
        )

    except Exception as e:
        logger.exception("extraction_task_failed", error=str(e))
        ExtractionRunCRUD.fail(db, run_id, {"error": str(e)})
        raise


def _process_files(
    db: Session,
    run_id: UUID,
    files_to_process: list[dict],
    mappings: dict,
    ExtractionRunCRUD,
    ExtractedValueCRUD,
):
    """
    Process a list of files and extract data.

    Args:
        db: Database session.
        run_id: Extraction run ID.
        files_to_process: List of file info dicts with file_path and deal_name.
        mappings: Cell mappings for extraction.
        ExtractionRunCRUD: CRUD class for extraction runs.
        ExtractedValueCRUD: CRUD class for extracted values.
    """
    from app.extraction import ExcelDataExtractor

    # Update run with file count
    ExtractionRunCRUD.update_progress(db, run_id, files_processed=0, files_failed=0)

    # Create extractor
    extractor = ExcelDataExtractor(mappings)

    processed = 0
    failed = 0

    for file_info in files_to_process:
        file_path = file_info["file_path"]
        deal_name = file_info.get("deal_name", "")

        try:
            # Extract data
            result = extractor.extract_from_file(file_path)

            # Get property name from extracted data or use deal name
            property_name = (
                result.get("PROPERTY_NAME", deal_name) or Path(file_path).stem
            )

            # Include SharePoint metadata if available
            source_file = file_info.get("sharepoint_path", file_path)

            # Insert into database
            ExtractedValueCRUD.bulk_insert(
                db,
                extraction_run_id=run_id,
                extracted_data=result,
                mappings=mappings,
                property_name=str(property_name),
                source_file=source_file,
            )

            processed += 1
            logger.info(
                "file_processed",
                file=Path(file_path).name,
                property=property_name,
                fields_extracted=len(result),
            )

        except Exception as e:
            failed += 1
            logger.error(
                "file_processing_failed",
                file=Path(file_path).name,
                error=str(e),
            )

        # Update progress
        ExtractionRunCRUD.update_progress(
            db, run_id, files_processed=processed, files_failed=failed
        )

    # Mark complete
    ExtractionRunCRUD.complete(
        db, run_id, files_processed=processed, files_failed=failed
    )
    logger.info(
        "extraction_completed",
        run_id=str(run_id),
        processed=processed,
        failed=failed,
    )


@router.post("/start", response_model=ExtractionStartResponse)
async def start_extraction(
    request: ExtractionStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start a new extraction run.

    Initiates extraction from SharePoint or local files. The extraction
    runs in the background and progress can be monitored via /status.

    For SharePoint source, requires AZURE_TENANT_ID, AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET, and SHAREPOINT_SITE_URL to be configured.
    """
    # Check if extraction is already running
    running = ExtractionRunCRUD.get_running(db)
    if running:
        raise HTTPException(
            status_code=409, detail=f"Extraction already running (id={running.id})"
        )

    # Determine file count based on source
    if request.source == "local" and request.file_paths:
        files_discovered = len(request.file_paths)
        logger.info("local_extraction_requested", file_count=files_discovered)

    elif request.source == "sharepoint":
        # Validate SharePoint configuration before starting
        if not settings.sharepoint_configured:
            missing = settings.get_sharepoint_config_errors()
            logger.error("sharepoint_not_configured", missing=missing)
            raise HTTPException(
                status_code=400,
                detail=f"SharePoint not configured. Missing environment variables: {', '.join(missing)}",
            )

        # Attempt to discover files from SharePoint
        try:
            sharepoint_files = await _discover_sharepoint_files()
            files_discovered = len(sharepoint_files)
            logger.info(
                "sharepoint_extraction_requested",
                file_count=files_discovered,
                site_url=settings.SHAREPOINT_SITE_URL,
            )

            if files_discovered == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No UW model files found in SharePoint. Check SHAREPOINT_DEALS_FOLDER configuration.",
                )

        except SharePointAuthError as e:
            logger.error("sharepoint_auth_failed_at_start", error=str(e))
            raise HTTPException(
                status_code=401,
                detail=f"SharePoint authentication failed: {e}",
            ) from None

    else:
        # Fallback to test fixtures for development/testing
        fixtures_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "tests"
            / "fixtures"
            / "uw_models"
        )
        files_discovered = len(list(fixtures_dir.glob("*.xlsb")))
        logger.info("fixture_extraction_requested", file_count=files_discovered)

    # Create extraction run
    run = ExtractionRunCRUD.create(
        db, trigger_type="manual", files_discovered=files_discovered
    )

    # Start background task
    background_tasks.add_task(
        run_extraction_task, run.id, db, request.source, request.file_paths
    )

    source_label = "SharePoint" if request.source == "sharepoint" else request.source
    return ExtractionStartResponse(
        run_id=run.id,
        status="running",
        message=f"Extraction started from {source_label} for {files_discovered} files",
        files_discovered=files_discovered,
    )


@router.get("/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(
    run_id: UUID | None = None, db: Session = Depends(get_db)
):
    """
    Get status of an extraction run.

    If run_id is not provided, returns status of the most recent run.
    """
    if run_id:
        run = ExtractionRunCRUD.get(db, run_id)
    else:
        run = ExtractionRunCRUD.get_latest(db)

    if not run:
        raise HTTPException(status_code=404, detail="No extraction runs found")

    return ExtractionStatusResponse(
        run_id=run.id,
        status=run.status,
        trigger_type=run.trigger_type,
        started_at=run.started_at,
        completed_at=run.completed_at,
        files_discovered=run.files_discovered,
        files_processed=run.files_processed,
        files_failed=run.files_failed,
        success_rate=run.success_rate,
        duration_seconds=run.duration_seconds,
        error_summary=run.error_summary,
    )


@router.get("/history", response_model=ExtractionHistoryResponse)
async def get_extraction_history(
    limit: int = 10, offset: int = 0, db: Session = Depends(get_db)
):
    """
    Get history of extraction runs.
    """
    runs = ExtractionRunCRUD.list_recent(db, limit, offset)

    return ExtractionHistoryResponse(
        runs=[
            ExtractionHistoryItem(
                run_id=r.id,
                status=r.status,
                trigger_type=r.trigger_type,
                started_at=r.started_at,
                completed_at=r.completed_at,
                files_processed=r.files_processed,
                files_failed=r.files_failed,
                success_rate=r.success_rate,
            )
            for r in runs
        ],
        total=len(runs),
    )


@router.post("/cancel")
async def cancel_extraction(run_id: UUID | None = None, db: Session = Depends(get_db)):
    """
    Cancel a running extraction.

    If run_id is not provided, cancels the currently running extraction.
    """
    if run_id:
        run = ExtractionRunCRUD.get(db, run_id)
    else:
        run = ExtractionRunCRUD.get_running(db)

    if not run:
        raise HTTPException(status_code=404, detail="No running extraction found")

    if run.status != "running":
        raise HTTPException(
            status_code=400, detail=f"Extraction is not running (status={run.status})"
        )

    cancelled = ExtractionRunCRUD.cancel(db, run.id)

    return {
        "message": "Extraction cancelled",
        "run_id": cancelled.id,
        "status": cancelled.status,
    }


@router.get("/properties", response_model=PropertyListResponse)
async def list_extracted_properties(
    run_id: UUID | None = None, db: Session = Depends(get_db)
):
    """
    List all properties with extracted data.
    """
    properties = ExtractedValueCRUD.list_properties(db, run_id)

    return PropertyListResponse(properties=properties, total=len(properties))


@router.get("/properties/{property_name}")
async def get_property_data(
    property_name: str, run_id: UUID | None = None, db: Session = Depends(get_db)
):
    """
    Get all extracted data for a specific property.
    """
    values = ExtractedValueCRUD.get_by_property(db, property_name, run_id)

    if not values:
        raise HTTPException(
            status_code=404, detail=f"No data found for property: {property_name}"
        )

    # Convert to dict
    data = {v.field_name: v.value for v in values}

    # Add metadata
    error_count = sum(1 for v in values if v.is_error)

    return {
        "property_name": property_name,
        "extraction_run_id": str(values[0].extraction_run_id),
        "total_fields": len(values),
        "successful_fields": len(values) - error_count,
        "error_fields": error_count,
        "data": data,
    }


# =============================================================================
# Scheduler Endpoints
# =============================================================================


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


# =============================================================================
# File Filter Endpoints
# =============================================================================


@router.get("/filters", response_model=FileFilterResponse)
async def get_filter_configuration():
    """
    Get current file filter configuration.

    Returns the active filter settings used to determine which files
    are processed during SharePoint discovery and extraction:

    - file_pattern: Regex pattern for matching UW model filenames
    - exclude_patterns: List of substrings that cause files to be skipped
    - valid_extensions: List of allowed file extensions
    - cutoff_date: Files older than this date are skipped
    - max_file_size_mb: Files larger than this are skipped

    These settings are loaded from environment variables or use defaults.
    Changes require updating environment variables and restarting the server.
    """
    file_filter = get_file_filter()
    config = file_filter.get_config()

    return FileFilterResponse(
        config=FileFilterConfig(
            file_pattern=config["file_pattern"],
            exclude_patterns=config["exclude_patterns"],
            valid_extensions=config["valid_extensions"],
            cutoff_date=config["cutoff_date"],
            max_file_size_mb=config["max_file_size_mb"],
        ),
        source="environment",
    )


@router.post("/filters/test")
async def test_file_filter(filename: str, size_mb: float = 1.0, days_old: int = 0):
    """
    Test if a file would be processed by the current filter configuration.

    Args:
        filename: The filename to test (e.g., "Property UW Model vCurrent.xlsb")
        size_mb: File size in MB (default 1.0)
        days_old: How many days old the file is (default 0 = today)

    Returns:
        Whether the file would be processed and the reason if skipped.
    """
    from datetime import timedelta

    file_filter = get_file_filter()

    # Calculate modification date
    modified_date = datetime.now() - timedelta(days=days_old)
    size_bytes = int(size_mb * 1024 * 1024)

    result = file_filter.should_process(
        filename=filename,
        size_bytes=size_bytes,
        modified_date=modified_date,
    )

    return {
        "filename": filename,
        "size_mb": size_mb,
        "days_old": days_old,
        "would_process": result.should_process,
        "skip_reason": result.reason_message,
    }


# =============================================================================
# File Monitor Endpoints
# =============================================================================


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
    from sqlalchemy import func, select

    from app.models.file_monitor import MonitoredFile
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
