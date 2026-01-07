"""
Extraction status and history endpoints.

Endpoints for querying extraction run status, history, and results.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.session import get_sync_db
from app.schemas.extraction import (
    ExtractionHistoryItem,
    ExtractionHistoryResponse,
    ExtractionStatusResponse,
    PropertyListResponse,
)

router = APIRouter()


@router.get("/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(
    run_id: UUID | None = None, db: Session = Depends(get_sync_db)
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
    limit: int = 10, offset: int = 0, db: Session = Depends(get_sync_db)
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


@router.get("/properties", response_model=PropertyListResponse)
async def list_extracted_properties(
    run_id: UUID | None = None, db: Session = Depends(get_sync_db)
):
    """
    List all properties with extracted data.
    """
    properties = ExtractedValueCRUD.list_properties(db, run_id)

    return PropertyListResponse(properties=properties, total=len(properties))


@router.get("/properties/{property_name}")
async def get_property_data(
    property_name: str, run_id: UUID | None = None, db: Session = Depends(get_sync_db)
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
