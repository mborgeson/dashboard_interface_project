"""
Admin endpoints for market data extraction management and audit logging.
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.admin import AuditLogEntry, AuditLogListResponse
from app.services import audit_service
from app.services.data_extraction.scheduler import (
    get_data_freshness,
    trigger_census_extraction,
    trigger_costar_extraction,
    trigger_fred_extraction,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/extract/fred",
    summary="Trigger FRED extraction",
    description="Queue a background FRED data extraction job. "
    "Supports incremental (default) or full extraction.",
)
async def extract_fred(
    background_tasks: BackgroundTasks,
    request: Request,
    incremental: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Trigger FRED data extraction (runs in background)."""
    background_tasks.add_task(trigger_fred_extraction, incremental=incremental)
    await audit_service.log_action(
        db=db,
        user=current_user,
        action="extract.trigger",
        resource_type="extraction",
        resource_id="fred",
        details={"source": "fred", "incremental": incremental},
        request=request,
    )
    return {"status": "started", "source": "fred", "incremental": incremental}


@router.post(
    "/extract/costar",
    summary="Trigger CoStar extraction",
    description="Queue a background CoStar market data extraction job.",
)
async def extract_costar(
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Trigger CoStar data extraction (runs in background)."""
    background_tasks.add_task(trigger_costar_extraction)
    await audit_service.log_action(
        db=db,
        user=current_user,
        action="extract.trigger",
        resource_type="extraction",
        resource_id="costar",
        details={"source": "costar"},
        request=request,
    )
    return {"status": "started", "source": "costar"}


@router.post(
    "/extract/census",
    summary="Trigger Census extraction",
    description="Queue a background U.S. Census data extraction job.",
)
async def extract_census(
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Trigger Census data extraction (runs in background)."""
    background_tasks.add_task(trigger_census_extraction)
    await audit_service.log_action(
        db=db,
        user=current_user,
        action="extract.trigger",
        resource_type="extraction",
        resource_id="census",
        details={"source": "census"},
        request=request,
    )
    return {"status": "started", "source": "census"}


@router.get(
    "/market-data-status",
    summary="Market data freshness status",
    description="Get data freshness and last-extraction timestamps for all "
    "configured market data sources (FRED, CoStar, Census).",
)
async def market_data_status():
    """Get data freshness and extraction status for all market data sources."""
    return get_data_freshness()


@router.get(
    "/audit-log",
    response_model=AuditLogListResponse,
    summary="List audit log entries",
    description="Retrieve paginated admin action audit trail with optional filters "
    "by action, user, resource type, and date range. Ordered newest first.",
    responses={
        200: {"description": "Paginated audit log entries"},
    },
)
async def list_audit_log(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    action: str | None = Query(None, description="Filter by action"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    from_date: datetime | None = Query(
        None, description="Start date filter (ISO 8601)"
    ),
    to_date: datetime | None = Query(None, description="End date filter (ISO 8601)"),
):
    """
    List audit log entries with pagination and filtering.

    Returns paginated admin action audit trail, newest first.
    """
    # Build base query
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    # Apply filters
    if action is not None:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if from_date is not None:
        query = query.where(AuditLog.timestamp >= from_date)
        count_query = count_query.where(AuditLog.timestamp >= from_date)
    if to_date is not None:
        query = query.where(AuditLog.timestamp <= to_date)
        count_query = count_query.where(AuditLog.timestamp <= to_date)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    offset = (page - 1) * per_page
    query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    entries = result.scalars().all()

    return AuditLogListResponse(
        items=[
            AuditLogEntry(
                id=entry.id,
                timestamp=entry.timestamp.isoformat() if entry.timestamp else None,
                user_id=entry.user_id,
                user_email=entry.user_email,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=entry.details,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
            )
            for entry in entries
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )
