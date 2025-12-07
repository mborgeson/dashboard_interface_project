"""
Deal endpoints for pipeline management and Kanban board operations.
"""
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
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

# Demo data for initial development
DEMO_DEALS = [
    {
        "id": 1,
        "name": "Phoenix Multifamily Portfolio",
        "deal_type": "acquisition",
        "stage": "underwriting",
        "stage_order": 0,
        "property_id": 1,
        "asking_price": 25000000,
        "projected_irr": 0.18,
        "projected_coc": 0.08,
        "projected_equity_multiple": 2.1,
        "hold_period_years": 5,
        "source": "CBRE",
        "broker_name": "John Smith",
        "priority": "high",
        "created_at": "2024-12-01T10:00:00Z",
        "updated_at": "2024-12-05T14:30:00Z",
    },
    {
        "id": 2,
        "name": "Scottsdale Office Acquisition",
        "deal_type": "acquisition",
        "stage": "initial_review",
        "stage_order": 1,
        "property_id": 2,
        "asking_price": 18500000,
        "projected_irr": 0.15,
        "priority": "medium",
        "created_at": "2024-12-03T09:00:00Z",
        "updated_at": "2024-12-04T11:00:00Z",
    },
    {
        "id": 3,
        "name": "Tempe Retail Development",
        "deal_type": "development",
        "stage": "lead",
        "stage_order": 0,
        "asking_price": 12000000,
        "priority": "low",
        "created_at": "2024-12-04T15:00:00Z",
        "updated_at": "2024-12-04T15:00:00Z",
    },
    {
        "id": 4,
        "name": "Mesa Industrial Park",
        "deal_type": "acquisition",
        "stage": "due_diligence",
        "stage_order": 0,
        "asking_price": 32000000,
        "offer_price": 30500000,
        "projected_irr": 0.20,
        "projected_coc": 0.09,
        "priority": "urgent",
        "created_at": "2024-11-15T08:00:00Z",
        "updated_at": "2024-12-05T16:00:00Z",
    },
]


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
    # TODO: Implement actual database queries
    filtered = DEMO_DEALS.copy()

    if stage:
        filtered = [d for d in filtered if d["stage"] == stage]
    if deal_type:
        filtered = [d for d in filtered if d["deal_type"] == deal_type]
    if priority:
        filtered = [d for d in filtered if d["priority"] == priority]
    if assigned_user_id:
        filtered = [d for d in filtered if d.get("assigned_user_id") == assigned_user_id]

    # Sort
    reverse = sort_order.lower() == "desc"
    if sort_by:
        filtered.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)

    # Paginate
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

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
    filtered = DEMO_DEALS.copy()

    if deal_type:
        filtered = [d for d in filtered if d["deal_type"] == deal_type]
    if assigned_user_id:
        filtered = [d for d in filtered if d.get("assigned_user_id") == assigned_user_id]

    # Group by stage
    stages = {stage.value: [] for stage in DealStage}
    stage_counts = {stage.value: 0 for stage in DealStage}

    for deal in filtered:
        stage = deal["stage"]
        if stage in stages:
            stages[stage].append(deal)
            stage_counts[stage] += 1

    # Sort deals within each stage by stage_order
    for stage in stages:
        stages[stage].sort(key=lambda x: x.get("stage_order", 0))

    return KanbanBoardResponse(
        stages=stages,
        total_deals=len(filtered),
        stage_counts=stage_counts,
    )


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific deal by ID.
    """
    deal = next((d for d in DEMO_DEALS if d["id"] == deal_id), None)

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
    new_id = max(d["id"] for d in DEMO_DEALS) + 1 if DEMO_DEALS else 1

    new_deal = {
        "id": new_id,
        **deal_data.model_dump(),
        "stage_order": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=new_id,
        action="created",
        data=new_deal,
    )

    logger.info(f"Created deal: {new_deal['name']}")

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
    existing = next((d for d in DEMO_DEALS if d["id"] == deal_id), None)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    # Update fields
    update_data = deal_data.model_dump(exclude_unset=True)
    existing.update(update_data)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="updated",
        data=existing,
    )

    logger.info(f"Updated deal: {deal_id}")

    return existing


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
    existing = next((d for d in DEMO_DEALS if d["id"] == deal_id), None)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    old_stage = existing["stage"]
    existing["stage"] = stage_data.stage
    if stage_data.stage_order is not None:
        existing["stage_order"] = stage_data.stage_order
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="stage_changed",
        data={
            "deal": existing,
            "old_stage": old_stage,
            "new_stage": stage_data.stage,
        },
    )

    logger.info(f"Deal {deal_id} moved from {old_stage} to {stage_data.stage}")

    return existing


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a deal (soft delete).
    """
    existing = next((d for d in DEMO_DEALS if d["id"] == deal_id), None)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

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
    existing = next((d for d in DEMO_DEALS if d["id"] == deal_id), None)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    if "activity_log" not in existing:
        existing["activity_log"] = []

    activity["timestamp"] = datetime.now(timezone.utc).isoformat()
    existing["activity_log"].append(activity)

    return {"message": "Activity added", "activity": activity}
