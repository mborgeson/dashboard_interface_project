"""
Deal activity and watchlist endpoints — activity logs, timeline, watchlist.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_analyst
from app.crud import deal as deal_crud
from app.crud.crud_activity import deal_activity
from app.crud.crud_activity import watchlist as watchlist_crud
from app.crud.crud_activity_log import activity_log as activity_log_crud
from app.db.session import get_db
from app.models.activity_log import ActivityAction as ModelActivityAction
from app.schemas.activity import (
    DealActivityCreate,
    DealActivityListResponse,
    DealActivityResponse,
    WatchlistToggleResponse,
)
from app.schemas.activity_log import (
    ActivityAction,
    ActivityLogCreate,
    ActivityLogListResponse,
    ActivityLogResponse,
)
from app.schemas.deal import WatchlistStatusResponse

router = APIRouter()
slog = structlog.get_logger("app.api.deals")


@router.post(
    "/{deal_id}/activity",
    response_model=DealActivityResponse,
    summary="Add deal activity",
    description="Add an activity log entry to a deal with automatic user attribution "
    "from the authenticated session.",
    responses={
        200: {"description": "Activity created successfully"},
        404: {"description": "Deal not found"},
    },
)
async def add_deal_activity(
    deal_id: int,
    activity: DealActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Add an activity log entry to a deal.

    Persists the activity to the database with proper user attribution.
    """
    # Verify deal exists
    existing = await deal_crud.get(db, deal_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Create activity with user_id from authenticated user
    activity_data = activity.model_dump()
    activity_data["user_id"] = current_user.id
    activity_data["deal_id"] = deal_id

    # Create and persist the activity
    created_activity = await deal_activity.create(db, obj_in=activity_data)

    slog.info(
        "deal_activity_logged",
        deal_id=deal_id,
        activity_type=activity.activity_type,
        user_id=current_user.id,
    )

    return created_activity


@router.get(
    "/{deal_id}/activity",
    response_model=DealActivityListResponse,
    summary="Get deal activities",
    description="Retrieve paginated activity history for a deal in reverse chronological "
    "order. Supports filtering by activity type.",
    responses={
        200: {"description": "Paginated list of deal activities"},
        404: {"description": "Deal not found"},
    },
)
async def get_deal_activities(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    activity_type: str | None = Query(None, description="Filter by activity type"),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get all activities for a specific deal with pagination.

    Returns activities in reverse chronological order (newest first).
    """
    # Verify deal exists
    existing = await deal_crud.get(db, deal_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Calculate skip/limit for pagination
    skip = (page - 1) * page_size

    # Get activities
    activities = await deal_activity.get_by_deal(
        db,
        deal_id=deal_id,
        skip=skip,
        limit=page_size,
        activity_type=activity_type,
    )

    # Get total count
    total = await deal_activity.count_by_deal(
        db,
        deal_id=deal_id,
        activity_type=activity_type,
    )

    return DealActivityListResponse(
        items=[
            DealActivityResponse.model_validate(a, from_attributes=True)
            for a in activities
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{deal_id}/watchlist",
    response_model=WatchlistToggleResponse,
    summary="Toggle deal watchlist",
    description="Add or remove a deal from the current user's watchlist. If the deal is "
    "currently watched, it will be removed; otherwise it will be added.",
    responses={
        200: {"description": "Watchlist status toggled successfully"},
        404: {"description": "Deal not found"},
    },
)
async def toggle_watchlist(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Toggle a deal on/off the current user's watchlist.

    If the deal is currently watched, it will be removed from the watchlist.
    If the deal is not watched, it will be added to the watchlist.

    Returns the new watchlist status for the deal.
    """
    # Verify deal exists
    deal = await deal_crud.get(db, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Toggle watchlist status
    is_watched, watchlist_entry = await watchlist_crud.toggle_watchlist(
        db,
        user_id=current_user.id,
        deal_id=deal_id,
    )

    if is_watched:
        message = f"Deal '{deal.name}' added to your watchlist"
    else:
        message = f"Deal '{deal.name}' removed from your watchlist"

    slog.info(
        "deal_watchlist_toggled",
        deal_id=deal_id,
        is_watched=is_watched,
        user_id=current_user.id,
        user_email=current_user.email,
    )

    return WatchlistToggleResponse(
        deal_id=deal_id,
        is_watched=is_watched,
        message=message,
        watchlist_id=watchlist_entry.id if watchlist_entry else None,
    )


@router.get(
    "/{deal_id}/watchlist/status",
    response_model=WatchlistStatusResponse,
    summary="Get watchlist status",
    description="Check whether a deal is on the current user's watchlist.",
    responses={
        200: {"description": "Watchlist status for the deal"},
        404: {"description": "Deal not found"},
    },
)
async def get_watchlist_status(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Check if a deal is on the current user's watchlist.
    """
    # Verify deal exists
    deal = await deal_crud.get(db, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    is_watched = await watchlist_crud.is_watching(
        db,
        user_id=current_user.id,
        deal_id=deal_id,
    )

    return {
        "deal_id": deal_id,
        "is_watched": is_watched,
    }


# =============================================================================
# Activity Log Endpoints (UUID-based)
# =============================================================================


@router.get(
    "/{deal_id}/activity-log",
    response_model=ActivityLogListResponse,
    summary="Get deal activity logs",
    description="Retrieve UUID-based activity logs for a deal with JSONB metadata support. "
    "Returns entries in reverse chronological order. Supports filtering by action type "
    "(created, updated, stage_changed, document_added, note_added, etc.).",
    responses={
        200: {"description": "Paginated activity logs"},
        400: {"description": "Invalid action type"},
        404: {"description": "Deal not found"},
    },
)
async def get_deal_activity_logs(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    action: str | None = Query(None, description="Filter by action type"),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get activity logs for a specific deal with pagination.

    Returns activity logs in reverse chronological order (newest first).
    This endpoint uses the UUID-based ActivityLog model for comprehensive
    audit trails with JSONB metadata support.

    Available action types:
    - created, updated, stage_changed, document_added, document_removed,
      note_added, assigned, unassigned, price_changed, viewed
    """
    # Verify deal exists
    existing = await deal_crud.get(db, deal_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Validate action type if provided
    if action:
        valid_actions = [a.value for a in ActivityAction]
        if action not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type. Must be one of: {', '.join(valid_actions)}",
            )

    # Calculate skip for pagination
    skip = (page - 1) * page_size

    # Get activity logs
    logs = await activity_log_crud.get_by_deal(
        db,
        deal_id=deal_id,
        skip=skip,
        limit=page_size,
        action=action,
    )

    # Get total count
    total = await activity_log_crud.count_by_deal(
        db,
        deal_id=deal_id,
        action=action,
    )

    return ActivityLogListResponse(
        items=[
            ActivityLogResponse.model_validate(log, from_attributes=True)
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{deal_id}/activity-log",
    response_model=ActivityLogResponse,
    summary="Create deal activity log entry",
    description="Add a manual activity log entry to a deal's audit trail. Activity logs "
    "are immutable once created. User ID is automatically set from the authenticated session.",
    responses={
        200: {"description": "Activity log entry created"},
        404: {"description": "Deal not found"},
    },
)
async def create_deal_activity_log(
    deal_id: int,
    activity_data: ActivityLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Add a manual activity log entry to a deal.

    This endpoint allows creating activity logs with custom descriptions
    and optional metadata. The user_id is automatically populated from
    the authenticated user.

    Activity logs are immutable once created - they serve as an audit trail.
    """
    # Verify deal exists
    existing = await deal_crud.get(db, deal_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Get metadata from the activity_data (handles alias)
    meta = activity_data.model_dump().get("metadata")

    # Convert schema enum to model enum
    model_action = ModelActivityAction(activity_data.action.value)

    # Create activity log with authenticated user
    created_log = await activity_log_crud.create_for_deal(
        db,
        deal_id=deal_id,
        action=model_action,
        description=activity_data.description,
        user_id=str(current_user.id),
        meta=meta,
    )

    slog.info(
        "deal_activity_log_created",
        deal_id=deal_id,
        action=activity_data.action.value,
        user_id=current_user.id,
        description=activity_data.description,
    )

    return ActivityLogResponse.model_validate(created_log, from_attributes=True)
