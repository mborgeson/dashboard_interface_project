"""
Deal endpoints for pipeline management and Kanban board operations.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.crud import deal as deal_crud
from app.schemas.deal import (
    DealCreate,
    DealUpdate,
    DealResponse,
    DealListResponse,
    DealStageUpdate,
    KanbanBoardResponse,
)
from app.services import get_websocket_manager
from app.models.deal import DealStage

router = APIRouter()


@router.get("/", response_model=DealListResponse)
async def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stage: Optional[str] = None,
    deal_type: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_user_id: Optional[int] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    """
    List all deals with filtering and pagination.
    """
    skip = (page - 1) * page_size
    order_desc = sort_order.lower() == "desc"

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

    return DealListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/kanban", response_model=KanbanBoardResponse)
async def get_kanban_board(
    deal_type: Optional[str] = None,
    assigned_user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get deals organized by stage for Kanban board view.

    Returns deals grouped by pipeline stage with counts.
    """
    kanban_data = await deal_crud.get_kanban_data(
        db,
        deal_type=deal_type,
        assigned_user_id=assigned_user_id,
    )

    return KanbanBoardResponse(
        stages=kanban_data["stages"],
        total_deals=kanban_data["total_deals"],
        stage_counts=kanban_data["stage_counts"],
    )


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific deal by ID.
    """
    deal = await deal_crud.get_with_relations(db, deal_id)

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    return deal


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    deal_data: DealCreate,
    db: AsyncSession = Depends(get_db),
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

    logger.info(f"Created deal: {new_deal.name} (ID: {new_deal.id})")

    return new_deal


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    deal_data: DealUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing deal.
    """
    existing = await deal_crud.get(db, deal_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Update deal in database
    updated_deal = await deal_crud.update(db, db_obj=existing, obj_in=deal_data)

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="updated",
        data={"id": updated_deal.id, "name": updated_deal.name},
    )

    logger.info(f"Updated deal: {deal_id}")

    return updated_deal


@router.patch("/{deal_id}", response_model=DealResponse)
async def patch_deal(
    deal_id: int,
    deal_data: DealUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update an existing deal.
    """
    existing = await deal_crud.get(db, deal_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Update deal in database
    updated_deal = await deal_crud.update(db, db_obj=existing, obj_in=deal_data)

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="updated",
        data={"id": updated_deal.id, "name": updated_deal.name},
    )

    logger.info(f"Patched deal: {deal_id}")

    return updated_deal


@router.patch("/{deal_id}/stage", response_model=DealResponse)
async def update_deal_stage(
    deal_id: int,
    stage_data: DealStageUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update deal stage (for Kanban drag-and-drop).

    This is optimized for quick stage changes from the Kanban board.
    """
    existing = await deal_crud.get(db, deal_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    old_stage = existing.stage

    # Update stage via CRUD
    try:
        new_stage_enum = DealStage(stage_data.stage)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage: {stage_data.stage}",
        )

    updated_deal = await deal_crud.update_stage(
        db,
        deal_id=deal_id,
        new_stage=new_stage_enum,
        stage_order=stage_data.stage_order,
    )

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="stage_changed",
        data={
            "deal_id": deal_id,
            "old_stage": old_stage.value if hasattr(old_stage, 'value') else str(old_stage),
            "new_stage": stage_data.stage,
        },
    )

    logger.info(f"Deal {deal_id} moved from {old_stage} to {stage_data.stage}")

    return updated_deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a deal.
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

    logger.info(f"Deleted deal: {deal_id}")
    return None


@router.post("/{deal_id}/activity")
async def add_deal_activity(
    deal_id: int,
    activity: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Add an activity log entry to a deal.
    """
    existing = await deal_crud.get(db, deal_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # TODO: Implement activity logging in a separate ActivityLog model
    activity["timestamp"] = datetime.now(timezone.utc).isoformat()
    activity["deal_id"] = deal_id

    return {"message": "Activity added", "activity": activity}
