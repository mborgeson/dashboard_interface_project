"""
Extraction API endpoints for SharePoint UW model data extraction.

Endpoints:
- POST /extraction/start - Start a new extraction
- GET /extraction/status - Get current extraction status
- GET /extraction/history - List past extractions
- POST /extraction/cancel - Cancel running extraction
- GET /extraction/properties - List extracted properties
- GET /extraction/properties/{name} - Get property data
"""

from typing import Optional
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.extraction import (
    ExtractionStartRequest,
    ExtractionStartResponse,
    ExtractionStatusResponse,
    ExtractionHistoryResponse,
    ExtractionHistoryItem,
    PropertyListResponse,
)
from app.crud.extraction import ExtractionRunCRUD, ExtractedValueCRUD

router = APIRouter()

# Path to reference file
REFERENCE_FILE = Path(__file__).parent.parent.parent.parent.parent / (
    "Underwriting_Dashboard_Cell_References.xlsx"
)


def run_extraction_task(
    run_id: UUID, db: Session, source: str, file_paths: Optional[list] = None
):
    """
    Background task to run extraction.

    This is executed in a separate thread by FastAPI BackgroundTasks.
    """
    from app.extraction import CellMappingParser, ExcelDataExtractor
    from app.crud.extraction import ExtractionRunCRUD, ExtractedValueCRUD

    try:
        # Load mappings
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()

        # Determine files to process
        if source == "local" and file_paths:
            files_to_process = [{"file_path": p} for p in file_paths]
        else:
            # TODO: Implement SharePoint file discovery
            # For now, use test fixtures
            fixtures_dir = (
                Path(__file__).parent.parent.parent.parent.parent
                / "tests"
                / "fixtures"
                / "uw_models"
            )
            files_to_process = [
                {"file_path": str(f)} for f in fixtures_dir.glob("*.xlsb")
            ]

        # Update run with file count
        ExtractionRunCRUD.update_progress(db, run_id, files_processed=0, files_failed=0)

        # Create extractor
        extractor = ExcelDataExtractor(mappings)

        processed = 0
        failed = 0

        for file_info in files_to_process:
            file_path = file_info["file_path"]
            try:
                # Extract data
                result = extractor.extract_from_file(file_path)

                # Get property name from extracted data
                property_name = result.get(
                    "PROPERTY_NAME",
                    Path(file_path).stem.replace(" UW Model vCurrent", ""),
                )

                # Insert into database
                ExtractedValueCRUD.bulk_insert(
                    db,
                    extraction_run_id=run_id,
                    extracted_data=result,
                    mappings=mappings,
                    property_name=str(property_name),
                    source_file=file_path,
                )

                processed += 1

            except Exception as e:
                failed += 1
                print(f"Error processing {file_path}: {e}")

            # Update progress
            ExtractionRunCRUD.update_progress(
                db, run_id, files_processed=processed, files_failed=failed
            )

        # Mark complete
        ExtractionRunCRUD.complete(
            db, run_id, files_processed=processed, files_failed=failed
        )

    except Exception as e:
        ExtractionRunCRUD.fail(db, run_id, {"error": str(e)})
        raise


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
    """
    # Check if extraction is already running
    running = ExtractionRunCRUD.get_running(db)
    if running:
        raise HTTPException(
            status_code=409, detail=f"Extraction already running (id={running.id})"
        )

    # Determine file count
    if request.source == "local" and request.file_paths:
        files_discovered = len(request.file_paths)
    else:
        # Count fixture files for now
        fixtures_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "tests"
            / "fixtures"
            / "uw_models"
        )
        files_discovered = len(list(fixtures_dir.glob("*.xlsb")))

    # Create extraction run
    run = ExtractionRunCRUD.create(
        db, trigger_type="manual", files_discovered=files_discovered
    )

    # Start background task
    background_tasks.add_task(
        run_extraction_task, run.id, db, request.source, request.file_paths
    )

    return ExtractionStartResponse(
        run_id=run.id,
        status="running",
        message=f"Extraction started for {files_discovered} files",
        files_discovered=files_discovered,
    )


@router.get("/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(
    run_id: Optional[UUID] = None, db: Session = Depends(get_db)
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
async def cancel_extraction(
    run_id: Optional[UUID] = None, db: Session = Depends(get_db)
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

    return {
        "message": "Extraction cancelled",
        "run_id": cancelled.id,
        "status": cancelled.status,
    }


@router.get("/properties", response_model=PropertyListResponse)
async def list_extracted_properties(
    run_id: Optional[UUID] = None, db: Session = Depends(get_db)
):
    """
    List all properties with extracted data.
    """
    properties = ExtractedValueCRUD.list_properties(db, run_id)

    return PropertyListResponse(properties=properties, total=len(properties))


@router.get("/properties/{property_name}")
async def get_property_data(
    property_name: str, run_id: Optional[UUID] = None, db: Session = Depends(get_db)
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
