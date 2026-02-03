"""
Deal endpoints for pipeline management and Kanban board operations.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user
from app.crud import deal as deal_crud
from app.crud.crud_activity import watchlist as watchlist_crud
from app.db.session import get_db
from app.models import Property
from app.models.deal import DealStage
from app.models.extraction import ExtractedValue
from app.schemas.activity import WatchlistToggleResponse
from app.schemas.comparison import (
    ComparisonSummary,
    DealComparisonResponse,
    DealMetrics,
    MetricComparison,
)
from app.schemas.deal import (
    DealCreate,
    DealListResponse,
    DealResponse,
    DealStageUpdate,
    DealUpdate,
    KanbanBoardResponse,
)
from app.services import get_websocket_manager

router = APIRouter()


async def _enrich_deals_with_extraction(
    db: AsyncSession, deal_responses: list[DealResponse]
) -> list[DealResponse]:
    """Add extraction-derived fields (units, owner, IRR, etc.) to deal responses."""
    # Collect property IDs
    prop_ids = [d.property_id for d in deal_responses if d.property_id]
    if not prop_ids:
        return deal_responses

    # Fetch needed extraction fields in one query
    needed_fields = [
        "TOTAL_UNITS", "AVERAGE_UNIT_SF", "CURRENT_OWNER",
        "LAST_SALE_PRICE_PER_UNIT", "LAST_SALE_DATE",
        "T12_RETURN_ON_COST", "LP_RETURNS_IRR", "LP_RETURNS_MOIC",
    ]
    stmt = (
        select(ExtractedValue)
        .where(
            ExtractedValue.property_id.in_(prop_ids),
            ExtractedValue.field_name.in_(needed_fields),
        )
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Build lookup: {property_id: {field_name: row}}
    lookup: dict[int, dict[str, ExtractedValue]] = {}
    for row in rows:
        lookup.setdefault(row.property_id, {})[row.field_name] = row

    # Also fetch equity commitment from property financial_data
    prop_stmt = select(Property.id, Property.financial_data).where(Property.id.in_(prop_ids))
    prop_result = await db.execute(prop_stmt)
    prop_map = dict(prop_result.all())

    for deal in deal_responses:
        if not deal.property_id:
            continue
        fields = lookup.get(deal.property_id, {})

        ev = fields.get("TOTAL_UNITS")
        if ev and ev.value_numeric is not None:
            deal.total_units = int(ev.value_numeric)

        ev = fields.get("AVERAGE_UNIT_SF")
        if ev and ev.value_numeric is not None:
            deal.avg_unit_sf = float(ev.value_numeric)

        ev = fields.get("CURRENT_OWNER")
        if ev and ev.value_text:
            deal.current_owner = ev.value_text

        ev = fields.get("LAST_SALE_PRICE_PER_UNIT")
        if ev and ev.value_numeric is not None:
            deal.last_sale_price_per_unit = float(ev.value_numeric)

        ev = fields.get("LAST_SALE_DATE")
        if ev and ev.value_text:
            deal.last_sale_date = ev.value_text

        ev = fields.get("T12_RETURN_ON_COST")
        if ev and ev.value_numeric is not None:
            deal.t12_return_on_cost = float(ev.value_numeric)

        ev = fields.get("LP_RETURNS_IRR")
        if ev and ev.value_numeric is not None:
            deal.levered_irr = float(ev.value_numeric)

        ev = fields.get("LP_RETURNS_MOIC")
        if ev and ev.value_numeric is not None:
            deal.levered_moic = float(ev.value_numeric)

        # Equity commitment from property financial_data
        fd = prop_map.get(deal.property_id)
        if fd and isinstance(fd, dict):
            ret = fd.get("returns", {})
            ec = ret.get("totalEquityCommitment")
            if ec is not None:
                deal.total_equity_commitment = float(ec)

    return deal_responses


@router.get("/", response_model=DealListResponse)
async def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stage: str | None = None,
    deal_type: str | None = None,
    priority: str | None = None,
    assigned_user_id: int | None = None,
    sort_by: str | None = "created_at",
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

    # Convert ORM items to Pydantic, then enrich with extraction data
    deal_responses = [DealResponse.model_validate(item) for item in items]
    enriched = await _enrich_deals_with_extraction(db, deal_responses)

    return DealListResponse(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/kanban", response_model=KanbanBoardResponse)
async def get_kanban_board(
    deal_type: str | None = None,
    assigned_user_id: int | None = None,
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

    # Enrich all deals across stages with extraction data
    all_responses: list[DealResponse] = []
    stage_response_map: dict[str, list[DealResponse]] = {}
    for stage_name, deals_list in kanban_data["stages"].items():
        responses = [DealResponse.model_validate(d) for d in deals_list]
        stage_response_map[stage_name] = responses
        all_responses.extend(responses)

    await _enrich_deals_with_extraction(db, all_responses)

    return KanbanBoardResponse(
        stages=stage_response_map,
        total_deals=kanban_data["total_deals"],
        stage_counts=kanban_data["stage_counts"],
    )


@router.get("/compare", response_model=DealComparisonResponse)
async def compare_deals(
    ids: str = Query(
        ...,
        description="Comma-separated deal IDs to compare (2-10 deals)",
        examples=["1,2,3"],
    ),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Compare multiple deals side-by-side.

    Returns detailed metrics for each deal along with a comparison summary
    highlighting which deal has the best values for each metric.

    - **ids**: Comma-separated list of deal IDs (minimum 2, maximum 10)

    The comparison_summary includes:
    - best_irr: Deal ID with highest projected IRR
    - best_coc: Deal ID with highest projected cash-on-cash return
    - best_equity_multiple: Deal ID with highest equity multiple
    - lowest_price: Deal ID with lowest asking price
    - highest_score: Deal ID with highest deal score
    - overall_recommendation: Suggested best deal based on weighted metrics
    """
    # Parse deal IDs
    try:
        deal_ids = [int(id.strip()) for id in ids.split(",") if id.strip()]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deal ID format. IDs must be comma-separated integers.",
        ) from e

    # Validate count
    if len(deal_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 deal IDs required for comparison",
        )
    if len(deal_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 deals can be compared at once",
        )

    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for id in deal_ids:
        if id not in seen:
            seen.add(id)
            unique_ids.append(id)
    deal_ids = unique_ids

    # Fetch deals from database
    deals = []
    for deal_id in deal_ids:
        deal = await deal_crud.get_with_relations(db, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal {deal_id} not found",
            )
        deals.append(deal)

    # Get property info for each deal
    property_info = {}
    for deal in deals:
        if deal.property_id:
            result = await db.execute(
                select(Property).where(Property.id == deal.property_id)
            )
            prop = result.scalar_one_or_none()
            if prop:
                property_info[deal.id] = prop

    # Build deal metrics
    deal_metrics = []
    for deal in deals:
        prop = property_info.get(deal.id)

        # Calculate days in pipeline
        days_in_pipeline = None
        if deal.initial_contact_date:
            days_in_pipeline = (
                datetime.now(UTC).date() - deal.initial_contact_date
            ).days

        metrics = DealMetrics(
            id=deal.id,
            name=deal.name,
            deal_type=deal.deal_type,
            stage=deal.stage.value if hasattr(deal.stage, "value") else str(deal.stage),
            priority=deal.priority,
            asking_price=deal.asking_price,
            offer_price=deal.offer_price,
            final_price=deal.final_price,
            projected_irr=deal.projected_irr,
            projected_coc=deal.projected_coc,
            projected_equity_multiple=deal.projected_equity_multiple,
            hold_period_years=deal.hold_period_years,
            deal_score=deal.deal_score,
            days_in_pipeline=days_in_pipeline,
            target_close_date=deal.target_close_date.isoformat()
            if deal.target_close_date
            else None,
            property_name=prop.name if prop else None,
            property_type=prop.property_type if prop else None,
            property_market=prop.market if prop else None,
            total_units=prop.total_units if prop else None,
            total_sf=prop.total_sf if prop else None,
        )
        deal_metrics.append(metrics)

    # Build comparison summary
    def find_best(attr: str, higher_is_better: bool = True) -> int | None:
        """Find deal ID with best value for an attribute."""
        values = [
            (d.id, getattr(d, attr))
            for d in deal_metrics
            if getattr(d, attr) is not None
        ]
        if not values:
            return None
        if higher_is_better:
            return max(values, key=lambda x: x[1])[0]
        return min(values, key=lambda x: x[1])[0]

    best_irr = find_best("projected_irr", higher_is_better=True)
    best_coc = find_best("projected_coc", higher_is_better=True)
    best_equity_multiple = find_best("projected_equity_multiple", higher_is_better=True)
    lowest_price = find_best("asking_price", higher_is_better=False)
    highest_score = find_best("deal_score", higher_is_better=True)

    # Calculate overall recommendation based on weighted score
    def calculate_weighted_score(deal: DealMetrics) -> float:
        """Calculate weighted score for overall recommendation."""
        score = 0.0
        weights = {
            "projected_irr": 0.3,
            "projected_coc": 0.2,
            "projected_equity_multiple": 0.2,
            "deal_score": 0.3,
        }

        for attr, weight in weights.items():
            value = getattr(deal, attr)
            if value is not None:
                if attr == "deal_score":
                    score += (float(value) / 100.0) * weight
                else:
                    score += float(value) * weight

        return score

    scores = [(d.id, calculate_weighted_score(d)) for d in deal_metrics]
    overall_recommendation = max(scores, key=lambda x: x[1])[0] if scores else None

    # Build recommendation reason
    reasons = []
    if overall_recommendation:
        rec_deal = next(
            (d for d in deal_metrics if d.id == overall_recommendation), None
        )
        if rec_deal:
            if rec_deal.projected_irr:
                reasons.append(
                    f"{float(rec_deal.projected_irr) * 100:.1f}% projected IRR"
                )
            if rec_deal.deal_score:
                reasons.append(f"score of {rec_deal.deal_score}/100")

    recommendation_reason = (
        f"Best overall metrics: {', '.join(reasons)}" if reasons else None
    )

    comparison_summary = ComparisonSummary(
        best_irr=best_irr,
        best_coc=best_coc,
        best_equity_multiple=best_equity_multiple,
        lowest_price=lowest_price,
        highest_score=highest_score,
        overall_recommendation=overall_recommendation,
        recommendation_reason=recommendation_reason,
    )

    # Build metric comparisons
    metric_comparisons = []

    def add_metric_comparison(
        metric_name: str,
        attr: str,
        comparison_type: str = "higher_is_better",
    ):
        """Add a metric comparison to the list."""
        values = {d.id: getattr(d, attr) for d in deal_metrics}
        non_null_values = {k: v for k, v in values.items() if v is not None}

        best_id = None
        best_val = None
        if non_null_values:
            if comparison_type == "higher_is_better":
                best_id = max(non_null_values, key=lambda k: non_null_values[k])
            else:
                best_id = min(non_null_values, key=lambda k: non_null_values[k])
            best_val = non_null_values[best_id]

        metric_comparisons.append(
            MetricComparison(
                metric_name=metric_name,
                values=values,
                best_deal_id=best_id,
                best_value=best_val,
                comparison_type=comparison_type,
            )
        )

    add_metric_comparison("Projected IRR", "projected_irr", "higher_is_better")
    add_metric_comparison("Projected CoC", "projected_coc", "higher_is_better")
    add_metric_comparison(
        "Equity Multiple", "projected_equity_multiple", "higher_is_better"
    )
    add_metric_comparison("Asking Price", "asking_price", "lower_is_better")
    add_metric_comparison("Deal Score", "deal_score", "higher_is_better")
    add_metric_comparison("Days in Pipeline", "days_in_pipeline", "lower_is_better")

    logger.info(f"User {current_user.email} compared deals: {deal_ids}")

    return DealComparisonResponse(
        deals=deal_metrics,
        comparison_summary=comparison_summary,
        metric_comparisons=metric_comparisons,
        deal_count=len(deal_metrics),
        compared_at=datetime.now(UTC).isoformat(),
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
    activity["timestamp"] = datetime.now(UTC).isoformat()
    activity["deal_id"] = deal_id

    return {"message": "Activity added", "activity": activity}


@router.post("/{deal_id}/watchlist", response_model=WatchlistToggleResponse)
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
        logger.info(f"User {current_user.email} added deal {deal_id} to watchlist")
    else:
        message = f"Deal '{deal.name}' removed from your watchlist"
        logger.info(f"User {current_user.email} removed deal {deal_id} from watchlist")

    return WatchlistToggleResponse(
        deal_id=deal_id,
        is_watched=is_watched,
        message=message,
        watchlist_id=watchlist_entry.id if watchlist_entry else None,
    )


@router.get("/{deal_id}/watchlist/status")
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
