"""
Deal pipeline/Kanban board endpoints — stage management and board view.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.permissions import CurrentUser, require_analyst, require_manager
from app.crud import deal as deal_crud
from app.crud.crud_activity_log import activity_log as activity_log_crud
from app.db.session import get_db
from app.models.deal import DealStage
from app.models.stage_change_log import StageChangeLog
from app.schemas.deal import (
    DealResponse,
    DealStageUpdate,
    KanbanBoardResponse,
    RecentActivityItem,
    StageChangeLogResponse,
    StageHistoryResponse,
    StageMappingResponse,
)
from app.services import get_websocket_manager

from .enrichment import enrich_deals_with_extraction

router = APIRouter()


@router.get(
    "/stage-mapping",
    response_model=StageMappingResponse,
    summary="Get stage mapping reference data",
    description="Returns canonical deal stages and the folder-to-stage mapping "
    "used by SharePoint sync. No authentication required (reference data).",
)
async def get_stage_mapping():
    """
    Return canonical stages and folder-to-stage mapping.
    """
    from app.services.stage_mapping import FOLDER_TO_STAGE

    return StageMappingResponse(
        stages=[s.value for s in DealStage],
        folder_to_stage={k: v.value for k, v in FOLDER_TO_STAGE.items()},
    )


@router.get(
    "/kanban",
    response_model=KanbanBoardResponse,
    summary="Get Kanban board",
    description="Get all deals organized by pipeline stage for the Kanban board view. "
    "Each deal is enriched with extraction-derived metrics and includes up to 3 recent "
    "activity log entries. Supports filtering by deal type and assigned user.",
    responses={
        200: {
            "description": "Deals grouped by stage with counts and recent activities"
        },
    },
)
async def get_kanban_board(
    deal_type: str | None = None,
    assigned_user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
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

    # Enrich all deals across stages with extraction data
    all_responses: list[DealResponse] = []
    stage_response_map: dict[str, list[DealResponse]] = {}
    for stage_name, deals_list in kanban_data["stages"].items():
        responses = [DealResponse.model_validate(d) for d in deals_list]
        stage_response_map[stage_name] = responses
        all_responses.extend(responses)

    await enrich_deals_with_extraction(db, all_responses)

    # Batch-fetch recent activities for all deals (3 per deal)
    deal_ids = [d.id for d in all_responses]
    if deal_ids:
        activities_map = await activity_log_crud.get_recent_for_deals(
            db, deal_ids=deal_ids, limit_per_deal=3
        )
        for deal_resp in all_responses:
            logs = activities_map.get(deal_resp.id, [])
            if logs:
                deal_resp.recent_activities = [
                    RecentActivityItem(
                        action=log.action.value
                        if hasattr(log.action, "value")
                        else str(log.action),
                        description=log.description,
                        created_at=log.created_at,
                    )
                    for log in logs
                ]

    return KanbanBoardResponse(
        stages=stage_response_map,
        total_deals=kanban_data["total_deals"],
        stage_counts=kanban_data["stage_counts"],
    )


@router.patch(
    "/{deal_id}/stage",
    response_model=DealResponse,
    summary="Update deal stage",
    description="Move a deal to a different pipeline stage, typically triggered by "
    "Kanban board drag-and-drop. Sends a WebSocket notification with the stage change. "
    "Requires manager role.",
    responses={
        200: {"description": "Deal stage updated successfully"},
        400: {"description": "Invalid stage value"},
        404: {"description": "Deal not found"},
    },
)
async def update_deal_stage(
    deal_id: int,
    stage_data: DealStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage: {stage_data.stage}",
        ) from e

    updated_deal = await deal_crud.update_stage(
        db,
        deal_id=deal_id,
        new_stage=new_stage_enum,
        stage_order=stage_data.stage_order,
        changed_by_user_id=current_user.id,
    )

    # Notify via WebSocket
    ws_manager = get_websocket_manager()
    await ws_manager.notify_deal_update(
        deal_id=deal_id,
        action="stage_changed",
        data={
            "deal_id": deal_id,
            "old_stage": (
                old_stage.value if hasattr(old_stage, "value") else str(old_stage)
            ),
            "new_stage": stage_data.stage,
        },
    )

    old_stage_val = old_stage.value if hasattr(old_stage, "value") else str(old_stage)
    logger.info(
        f"deal_stage_changed deal_id={deal_id} old_stage={old_stage_val} "
        f"new_stage={stage_data.stage} user_id={current_user.id} "
        f"user_email={current_user.email}"
    )

    await cache.invalidate_deals()
    return updated_deal


@router.get(
    "/{deal_id}/stage-history",
    response_model=StageHistoryResponse,
    summary="Get deal stage change history",
    description="Returns the audit trail of all stage transitions for a deal, "
    "ordered by most recent first. Each entry records the old/new stage, the "
    "source of the change, the user who made it (if applicable), and an "
    "optional reason.",
    responses={
        200: {"description": "Stage change history"},
        404: {"description": "Deal not found"},
    },
)
async def get_stage_history(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get the full stage change audit trail for a deal.
    """
    # Verify deal exists
    deal = await deal_crud.get(db, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    stmt = (
        select(StageChangeLog)
        .where(StageChangeLog.deal_id == deal_id)
        .order_by(StageChangeLog.created_at.desc())
    )
    result = await db.execute(stmt)
    entries = list(result.scalars().all())

    return StageHistoryResponse(
        deal_id=deal_id,
        history=[StageChangeLogResponse.model_validate(e) for e in entries],
        total=len(entries),
    )
