"""
Extraction status and history endpoints.

Endpoints for querying extraction run status, history, and results.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, func, literal, select
from sqlalchemy.orm import Session

from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.session import get_sync_db
from app.models.extraction import ExtractedValue, ExtractionRun

router = APIRouter()


def _run_to_item(run: ExtractionRun) -> dict:
    """Convert an ExtractionRun ORM object to the frontend-expected shape."""
    return {
        "id": str(run.id),
        "started_at": run.started_at.isoformat() if run.started_at else "",
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status,
        "trigger_type": run.trigger_type,
        "files_discovered": run.files_discovered,
        "files_processed": run.files_processed,
        "files_failed": run.files_failed,
        "error_message": (
            run.error_summary.get("message") if run.error_summary else None
        ),
    }


@router.get("/status")
async def get_extraction_status(
    run_id: UUID | None = None, db: Session = Depends(get_sync_db)
):
    """
    Get status of extraction runs.

    Returns the current running extraction (if any), the last completed run,
    and overall extraction statistics.
    """
    # Get currently running extraction
    current_run = ExtractionRunCRUD.get_running(db)

    # If a specific run_id is requested, use that as the "current" run
    if run_id:
        specific_run = ExtractionRunCRUD.get(db, run_id)
        if not specific_run:
            raise HTTPException(status_code=404, detail="Extraction run not found")
        current_run = specific_run

    # Get last completed run
    stmt = (
        select(ExtractionRun)
        .where(ExtractionRun.status == "completed")
        .order_by(ExtractionRun.started_at.desc())
        .limit(1)
    )
    last_completed = db.execute(stmt).scalar_one_or_none()

    # Build stats
    total_runs = db.execute(
        select(func.count(ExtractionRun.id))
    ).scalar_one()
    successful_runs = db.execute(
        select(func.count(ExtractionRun.id)).where(
            ExtractionRun.status == "completed"
        )
    ).scalar_one()
    failed_runs = db.execute(
        select(func.count(ExtractionRun.id)).where(
            ExtractionRun.status == "failed"
        )
    ).scalar_one()

    # Get total properties and fields from latest completed run
    total_properties = 0
    total_fields = 0
    if last_completed:
        total_properties = db.execute(
            select(func.count(func.distinct(ExtractedValue.property_name))).where(
                ExtractedValue.extraction_run_id == last_completed.id
            )
        ).scalar_one()
        total_fields = db.execute(
            select(func.count(ExtractedValue.id)).where(
                ExtractedValue.extraction_run_id == last_completed.id
            )
        ).scalar_one()

    last_run_at = None
    if last_completed and last_completed.started_at:
        last_run_at = last_completed.started_at.isoformat()

    return {
        "current_run": _run_to_item(current_run) if current_run else None,
        "last_completed_run": _run_to_item(last_completed) if last_completed else None,
        "stats": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "total_properties": total_properties,
            "total_fields_extracted": total_fields,
            "last_run_at": last_run_at,
        },
    }


@router.get("/history")
async def get_extraction_history(
    limit: int = 10, offset: int = 0, page: int | None = None,
    db: Session = Depends(get_sync_db),
):
    """
    Get history of extraction runs.

    Supports both offset-based and page-based pagination.
    """
    # Support page-based pagination from frontend
    if page is not None and page > 0:
        actual_offset = (page - 1) * limit
    else:
        actual_offset = offset
        page = (offset // limit) + 1 if limit > 0 else 1

    runs = ExtractionRunCRUD.list_recent(db, limit, actual_offset)

    total = db.execute(select(func.count(ExtractionRun.id))).scalar_one()

    return {
        "runs": [
            {
                "id": str(r.id),
                "run_id": str(r.id),
                "status": r.status,
                "trigger_type": r.trigger_type,
                "started_at": r.started_at.isoformat() if r.started_at else "",
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "files_discovered": r.files_discovered,
                "files_processed": r.files_processed,
                "files_failed": r.files_failed,
                "success_rate": r.success_rate,
            }
            for r in runs
        ],
        "total": total,
        "page": page,
        "page_size": limit,
    }


@router.get("/properties")
async def list_extracted_properties(
    run_id: UUID | None = None,
    search: str | None = None,
    has_errors: bool | None = None,
    db: Session = Depends(get_sync_db),
):
    """
    List all properties with extracted data, including field counts and categories.

    Returns ExtractedProperty objects (not just strings) to match frontend expectations.
    """
    # Determine which run to query
    target_run_id = run_id
    if not target_run_id:
        latest = ExtractionRunCRUD.get_latest(db)
        if latest:
            target_run_id = latest.id

    if not target_run_id:
        return {"properties": [], "total": 0}

    # Get property summaries with aggregations
    stmt = (
        select(
            ExtractedValue.property_name,
            func.count(ExtractedValue.id).label("total_fields"),
            func.sum(
                case((ExtractedValue.is_error.is_(True), literal(1)), else_=literal(0))
            ).label("error_count"),
            func.max(ExtractedValue.updated_at).label("last_extracted_at"),
        )
        .where(ExtractedValue.extraction_run_id == target_run_id)
        .group_by(ExtractedValue.property_name)
        .order_by(ExtractedValue.property_name)
    )

    rows = db.execute(stmt).all()

    # Get categories per property (database-agnostic approach)
    cat_stmt = (
        select(
            ExtractedValue.property_name,
            ExtractedValue.field_category,
        )
        .where(
            and_(
                ExtractedValue.extraction_run_id == target_run_id,
                ExtractedValue.field_category.isnot(None),
            )
        )
        .distinct()
        .order_by(ExtractedValue.property_name, ExtractedValue.field_category)
    )
    cat_rows: dict[str, list[str]] = {}
    for row in db.execute(cat_stmt).all():
        cat_rows.setdefault(row.property_name, []).append(row.field_category)

    properties = []
    for row in rows:
        prop = {
            "property_name": row.property_name,
            "total_fields": row.total_fields,
            "error_count": row.error_count or 0,
            "categories": cat_rows.get(row.property_name, []),
            "last_extracted_at": (
                row.last_extracted_at.isoformat() if row.last_extracted_at else None
            ),
        }

        # Apply filters
        if search and search.lower() not in prop["property_name"].lower():
            continue
        if has_errors is True and prop["error_count"] == 0:
            continue
        if has_errors is False and prop["error_count"] > 0:
            continue

        properties.append(prop)

    return {"properties": properties, "total": len(properties)}


@router.get("/properties/{property_name}")
async def get_property_data(
    property_name: str,
    run_id: UUID | None = None,
    db: Session = Depends(get_sync_db),
):
    """
    Get all extracted data for a specific property.

    Returns full ExtractedValue objects with categories and totals.
    """
    # Determine run_id
    target_run_id = run_id
    if not target_run_id:
        latest = ExtractionRunCRUD.get_latest(db)
        if latest:
            target_run_id = latest.id

    values = ExtractedValueCRUD.get_by_property(db, property_name, target_run_id)

    if not values:
        raise HTTPException(
            status_code=404, detail=f"No data found for property: {property_name}"
        )

    # Build categories list
    categories = sorted(
        {v.field_category for v in values if v.field_category}
    )

    # Build value items
    value_items = []
    for v in values:
        # Determine data_type
        if v.is_error:
            data_type = "error"
        elif v.value_numeric is not None:
            data_type = "numeric"
        elif v.value_date is not None:
            data_type = "date"
        else:
            data_type = "text"

        value_items.append(
            {
                "id": str(v.id),
                "extraction_run_id": str(v.extraction_run_id),
                "property_name": v.property_name,
                "field_name": v.field_name,
                "field_category": v.field_category or "",
                "sheet_name": v.sheet_name or "",
                "cell_address": v.cell_address or "",
                "value_text": v.value_text,
                "value_numeric": float(v.value_numeric) if v.value_numeric is not None else None,
                "value_date": v.value_date.isoformat() if v.value_date else None,
                "data_type": data_type,
                "is_error": v.is_error,
                "error_category": v.error_category,
                "error_message": None,
                "extracted_at": v.created_at.isoformat() if v.created_at else "",
            }
        )

    return {
        "property_name": property_name,
        "values": value_items,
        "categories": categories,
        "total": len(value_items),
    }
