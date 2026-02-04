"""
Extraction operations endpoints.

Endpoints for starting, canceling, and managing extraction runs.
"""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

# Import from common module - these can be patched via the package __init__.py
from app.api.v1.endpoints.extraction import common
from app.core.config import settings
from app.crud.extraction import ExtractionRunCRUD
from app.db.session import get_sync_db
from app.extraction.sharepoint import SharePointAuthError
from app.schemas.extraction import (
    ExtractionStartRequest,
    ExtractionStartResponse,
)

# Re-export for easier access
discover_sharepoint_files = common.discover_sharepoint_files
logger = common.logger

router = APIRouter()


@router.post("/start", response_model=ExtractionStartResponse)
async def start_extraction(
    request: ExtractionStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db),
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
            sharepoint_files = await discover_sharepoint_files()
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
            Path(__file__).parent.parent.parent.parent.parent.parent
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
    # Use common.run_extraction_task to allow patching via the package namespace
    background_tasks.add_task(
        common.run_extraction_task, run.id, request.source, request.file_paths
    )

    source_label = "SharePoint" if request.source == "sharepoint" else request.source
    return ExtractionStartResponse(
        run_id=run.id,
        status="running",
        message=f"Extraction started from {source_label} for {files_discovered} files",
        files_discovered=files_discovered,
    )


@router.post("/cancel")
async def cancel_extraction(
    run_id: UUID | None = None, db: Session = Depends(get_sync_db)
):
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

    if cancelled is None:
        raise HTTPException(status_code=500, detail="Failed to cancel extraction")
    return {
        "message": "Extraction cancelled",
        "run_id": cancelled.id,
        "status": cancelled.status,
    }
