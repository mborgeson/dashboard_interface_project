"""
Deal CRUD endpoints — list, get, create, update, delete, restore.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.permissions import CurrentUser, require_analyst, require_manager
from app.crud import deal as deal_crud
from app.db.session import get_db
from app.models.deal import Deal
from app.schemas.deal import (
    DealCreate,
    DealCursorPaginatedResponse,
    DealListResponse,
    DealResponse,
    DealUpdate,
)
from app.schemas.pagination import CursorPaginationParams
from app.services import get_websocket_manager

from .enrichment import enrich_deals_with_extraction

router = APIRouter()

_SORTABLE_COLUMNS = {
    "name": Deal.name,
    "stage": Deal.stage,
    "deal_type": Deal.deal_type,
    "priority": Deal.priority,
    "asking_price": Deal.asking_price,
    "deal_score": Deal.deal_score,
    "created_at": Deal.created_at,
    "updated_at": Deal.updated_at,
}


@router.get(
    "/",
    response_model=DealListResponse,
    summary="List deals",
    description="List all deals in the pipeline with filtering by stage, type, priority, "
    "and assigned user. Supports pagination and sorting. Results are enriched with "
    "extraction-derived financial metrics (IRR, MOIC, cap rates, etc.).",
    responses={
        200: {"description": "Paginated list of deals with extraction enrichment"},
    },
)
async def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stage: str | None = None,
    deal_type: str | None = None,
    priority: str | None = None,
    assigned_user_id: int | None = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    List all deals with filtering and pagination.
    """
    if sort_by not in _SORTABLE_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Valid options: {list(_SORTABLE_COLUMNS.keys())}",
        )
    if sort_order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort_order. Must be 'asc' or 'desc'.",
        )
    skip = (page - 1) * page_size
    order_desc = sort_order == "desc"

    # Get filtered deals from database
    items = await deal_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=page_size,
        stage=stage,
        deal_type=deal_type,
        priority=priority,
        assigned_user_id=assigned_user_id,
        order_by=sort_by or "created_at",
        order_desc=order_desc,
    )

    # Get total count for pagination
    total = await deal_crud.count_filtered(
        db,
        stage=stage,
        deal_type=deal_type,
        priority=priority,
        assigned_user_id=assigned_user_id,
    )

    # Convert ORM items to Pydantic, then enrich with extraction data
    deal_responses = [DealResponse.model_validate(item) for item in items]
    enriched = await enrich_deals_with_extraction(db, deal_responses)

    return DealListResponse(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/cursor",
    response_model=DealCursorPaginatedResponse,
    summary="List deals (cursor pagination)",
    description="List deals using cursor-based pagination for efficient, stable paging. "
    "Supports filtering by stage, type, priority, and assigned user. "
    "Results are enriched with extraction-derived financial metrics.",
    responses={
        200: {"description": "Cursor-paginated list of deals"},
        400: {"description": "Invalid cursor"},
    },
)
async def list_deals_cursor(
    cursor: str | None = Query(
        None, description="Opaque cursor from previous response"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    direction: str = Query(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    ),
    stage: str | None = None,
    deal_type: str | None = None,
    priority: str | None = None,
    assigned_user_id: int | None = None,
    sort_by: str | None = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    List deals with cursor-based pagination.

    Cursor pagination provides stable, efficient paging even when new deals
    are added or existing deals change position in the sort order.
    """
    order_desc = sort_order.lower() == "desc"

    # Build filter conditions
    conditions = deal_crud._build_deal_conditions(
        stage=stage,
        deal_type=deal_type,
        priority=priority,
        assigned_user_id=assigned_user_id,
    )

    params = CursorPaginationParams(cursor=cursor, limit=limit, direction=direction)

    try:
        result = await deal_crud.get_cursor_paginated(
            db,
            params=params,
            order_by=sort_by or "created_at",
            order_desc=order_desc,
            conditions=conditions,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Convert ORM items to Pydantic, then enrich with extraction data
    deal_responses = [DealResponse.model_validate(item) for item in result.items]
    enriched = await enrich_deals_with_extraction(db, deal_responses)

    return DealCursorPaginatedResponse(
        items=enriched,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_more=result.has_more,
        total=result.total,
    )


@router.get(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Get deal by ID",
    description="Retrieve a single deal with all extraction-enriched financial metrics "
    "including cap rates, IRR, MOIC, unit counts, and location data.",
    responses={
        200: {"description": "Deal details with extraction enrichment"},
        404: {"description": "Deal not found"},
    },
)
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get a specific deal by ID with extraction enrichment.
    """
    deal = await deal_crud.get_with_relations(db, deal_id)

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Enrich with extraction data
    deal_resp = DealResponse.model_validate(deal)
    enriched = await enrich_deals_with_extraction(db, [deal_resp])
    return enriched[0]


@router.post(
    "/",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new deal",
    description="Create a new deal in the acquisition pipeline. Triggers a WebSocket "
    "notification to all connected clients. Requires manager role.",
    responses={
        201: {"description": "Deal created successfully"},
    },
)
async def create_deal(
    deal_data: DealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Create a new deal in the pipeline.
    """
    # Create deal in database
    new_deal = await deal_crud.create(db, obj_in=deal_data)

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=new_deal.id,
        action="created",
        data={"id": new_deal.id, "name": new_deal.name},
    )

    logger.info(
        f"deal_created deal_id={new_deal.id} deal_name={new_deal.name} "
        f"user_id={current_user.id} user_email={current_user.email}"
    )

    await cache.invalidate_deals()
    return new_deal


@router.patch(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Update a deal (partial)",
    description="Partial update of a deal using optimistic locking. Only fields included "
    "in the request body are updated. The `version` field is required for conflict "
    "detection. Returns 409 Conflict if the deal has been modified by another user "
    "since then. Requires manager role.",
    responses={
        200: {"description": "Deal updated successfully"},
        404: {"description": "Deal not found"},
        409: {
            "description": "Optimistic locking conflict — deal was modified by another user"
        },
    },
)
async def patch_deal(
    deal_id: int,
    deal_data: DealUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Partially update an existing deal (with optimistic locking).

    The client must include the `version` field from its last read.
    If another user has updated the deal since then, a 409 Conflict is returned.
    """
    existing = await deal_crud.get(db, deal_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Use optimistic locking via version column
    update_data = deal_data.model_dump(exclude_unset=True)
    expected_version = update_data.pop("version")

    updated_deal = await deal_crud.update_optimistic(
        db,
        deal_id=deal_id,
        expected_version=expected_version,
        update_data=update_data,
    )

    if updated_deal is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Deal {deal_id} has been modified by another user. "
                f"Expected version {expected_version}, but the deal has been updated. "
                "Please refresh and try again."
            ),
        )

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="updated",
        data={"id": updated_deal.id, "name": updated_deal.name},
    )

    logger.info(
        f"deal_updated deal_id={deal_id} user_id={current_user.id} "
        f"user_email={current_user.email} fields_changed={list(update_data.keys())}"
    )

    await cache.invalidate_deals()
    return updated_deal


# PUT kept for backwards compatibility — delegates to PATCH logic
@router.put(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Update a deal (partial, PUT alias)",
    description="Alias for PATCH /{deal_id} — kept for backwards compatibility. "
    "Only fields present in the request body are updated. "
    "The `version` field is required for optimistic locking.",
    responses={
        200: {"description": "Deal updated successfully"},
        404: {"description": "Deal not found"},
        409: {
            "description": "Optimistic locking conflict — deal was modified by another user"
        },
    },
    deprecated=True,
)
async def update_deal(
    deal_id: int,
    deal_data: DealUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """Update a deal via PUT (delegates to PATCH for backwards compatibility)."""
    return await patch_deal(deal_id, deal_data, db, current_user)


@router.delete(
    "/{deal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deal",
    description="Soft-delete a deal from the pipeline. The deal is marked as deleted but "
    "retained in the database for audit purposes. Use the restore endpoint to undo. "
    "Requires manager role.",
    responses={
        204: {"description": "Deal deleted successfully"},
        404: {"description": "Deal not found"},
    },
)
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Soft-delete a deal.

    The deal is marked as deleted but retained in the database.
    Use POST /{deal_id}/restore to undo.
    """
    existing = await deal_crud.get(db, deal_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    await deal_crud.remove(db, id=deal_id)

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="deleted",
        data={"id": deal_id},
    )

    logger.info(
        f"deal_deleted deal_id={deal_id} user_id={current_user.id} "
        f"user_email={current_user.email}"
    )
    await cache.invalidate_deals()
    return None


@router.post(
    "/{deal_id}/restore",
    response_model=DealResponse,
    summary="Restore a deleted deal",
    description="Restore a previously soft-deleted deal back into the pipeline. "
    "Returns 400 if the deal is not currently deleted. Requires manager role.",
    responses={
        200: {"description": "Deal restored successfully"},
        400: {"description": "Deal is not deleted"},
        404: {"description": "Deal not found"},
        500: {"description": "Failed to restore deal"},
    },
)
async def restore_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Restore a soft-deleted deal.
    """
    # Look up the deal including deleted ones
    existing = await deal_crud.get(db, deal_id, include_deleted=True)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    if not existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deal {deal_id} is not deleted",
        )

    restored = await deal_crud.restore(db, id=deal_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore deal",
        )

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="restored",
        data={"id": deal_id, "name": restored.name},
    )

    logger.info(
        f"deal_restored deal_id={deal_id} deal_name={restored.name} "
        f"user_id={current_user.id} user_email={current_user.email}"
    )
    return DealResponse.model_validate(restored)
