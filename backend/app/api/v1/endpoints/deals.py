"""
Deal endpoints for pipeline management and Kanban board operations.
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CurrentUser,
    get_current_user,
    require_analyst,
    require_manager,
)
from app.crud import deal as deal_crud
from app.crud.crud_activity import deal_activity
from app.crud.crud_activity import watchlist as watchlist_crud
from app.crud.crud_activity_log import activity_log as activity_log_crud
from app.db.session import get_db
from app.models.activity_log import ActivityAction as ModelActivityAction
from app.models.deal import DealStage
from app.models.extraction import ExtractedValue, ExtractionRun
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
from app.schemas.comparison import (
    ComparisonSummary,
    DealComparisonResponse,
    MetricComparison,
)
from app.schemas.deal import (
    DealCreate,
    DealListResponse,
    DealResponse,
    DealStageUpdate,
    DealUpdate,
    KanbanBoardResponse,
    RecentActivityItem,
)
from app.services import get_websocket_manager

router = APIRouter()
slog = structlog.get_logger("app.api.deals")


async def _enrich_deals_with_extraction(
    db: AsyncSession, deal_responses: list[DealResponse]
) -> list[DealResponse]:
    """Add extraction-derived fields (units, owner, IRR, etc.) to deal responses."""
    # Collect property IDs
    prop_ids = [d.property_id for d in deal_responses if d.property_id]
    if not prop_ids:
        return deal_responses

    # Fetch needed extraction fields from the latest completed run per property
    needed_fields = [
        "TOTAL_UNITS",
        "AVERAGE_UNIT_SF",
        "CURRENT_OWNER",
        "LAST_SALE_PRICE_PER_UNIT",
        "LAST_SALE_DATE",
        "T12_RETURN_ON_COST",
        "LP_RETURNS_IRR",
        "LP_RETURNS_MOIC",
        "UNLEVERED_RETURNS_IRR",
        "UNLEVERED_RETURNS_MOIC",
        "LEVERED_RETURNS_IRR",
        "LEVERED_RETURNS_MOIC",
        "PROPERTY_CITY",
        "SUBMARKET",
        "YEAR_BUILT",
        "YEAR_RENOVATED",
        "VACANCY_LOSS_YEAR_1_RATE",
        "BAD_DEBTS_YEAR_1_RATE",
        "OTHER_LOSS_YEAR_1_RATE",
        "CONCESSIONS_YEAR_1_RATE",
        "NET_OPERATING_INCOME_MARGIN",
        "PURCHASE_PRICE",
        "TOTAL_ACQUISITION_BUDGET",
        "BASIS_UNIT_AT_CLOSE",
        "T12_RETURN_ON_PP",
        "T3_RETURN_ON_PP",
        # TOTAL_RETURN_ON_COST_AT_EXIT and PURCHASE_PRICE_RETURN_ON_COST_AT_EXIT
        # are exit metrics, not going-in cap rates — no longer used for TC cap rates
        "LOAN_AMOUNT",
        "EQUITY_LP_CAPITAL",
        "EXIT_PERIOD_MONTHS",
        "EXIT_CAP_RATE",
        "T3_RETURN_ON_COST",
        "PROPERTY_LATITUDE",
        "PROPERTY_LONGITUDE",
    ]

    # Subquery: latest completed extraction_run_id per property_id
    latest_run_subq = (
        select(
            ExtractedValue.property_id,
            func.max(ExtractionRun.completed_at).label("max_completed"),
        )
        .join(ExtractionRun, ExtractedValue.extraction_run_id == ExtractionRun.id)
        .where(
            ExtractedValue.property_id.in_(prop_ids),
            ExtractionRun.status == "completed",
        )
        .group_by(ExtractedValue.property_id)
        .subquery()
    )

    stmt = (
        select(ExtractedValue)
        .join(ExtractionRun, ExtractedValue.extraction_run_id == ExtractionRun.id)
        .join(
            latest_run_subq,
            (ExtractedValue.property_id == latest_run_subq.c.property_id)
            & (ExtractionRun.completed_at == latest_run_subq.c.max_completed),
        )
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
        if row.property_id is not None:
            lookup.setdefault(row.property_id, {})[row.field_name] = row

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
            deal.lp_irr = float(ev.value_numeric)

        ev = fields.get("LP_RETURNS_MOIC")
        if ev and ev.value_numeric is not None:
            deal.lp_moic = float(ev.value_numeric)

        ev = fields.get("LEVERED_RETURNS_IRR")
        if ev and ev.value_numeric is not None:
            deal.levered_irr = float(ev.value_numeric)

        ev = fields.get("LEVERED_RETURNS_MOIC")
        if ev and ev.value_numeric is not None:
            deal.levered_moic = float(ev.value_numeric)

        ev = fields.get("PROPERTY_CITY")
        if ev and ev.value_text:
            deal.property_city = ev.value_text

        ev = fields.get("SUBMARKET")
        if ev and ev.value_text:
            deal.submarket = ev.value_text

        ev = fields.get("YEAR_BUILT")
        if ev and ev.value_numeric is not None:
            deal.year_built = int(ev.value_numeric)

        ev = fields.get("YEAR_RENOVATED")
        if ev and ev.value_numeric is not None:
            deal.year_renovated = int(ev.value_numeric)

        ev = fields.get("VACANCY_LOSS_YEAR_1_RATE")
        if ev and ev.value_numeric is not None:
            deal.vacancy_rate = float(ev.value_numeric)

        ev = fields.get("BAD_DEBTS_YEAR_1_RATE")
        if ev and ev.value_numeric is not None:
            deal.bad_debt_rate = float(ev.value_numeric)

        ev = fields.get("OTHER_LOSS_YEAR_1_RATE")
        if ev and ev.value_numeric is not None:
            deal.other_loss_rate = float(ev.value_numeric)

        ev = fields.get("CONCESSIONS_YEAR_1_RATE")
        if ev and ev.value_numeric is not None:
            deal.concessions_rate = float(ev.value_numeric)

        ev = fields.get("NET_OPERATING_INCOME_MARGIN")
        if ev and ev.value_numeric is not None:
            deal.noi_margin = float(ev.value_numeric)

        ev = fields.get("PURCHASE_PRICE")
        if ev and ev.value_numeric is not None:
            deal.purchase_price_extracted = float(ev.value_numeric)

        ev = fields.get("TOTAL_ACQUISITION_BUDGET")
        if ev and ev.value_numeric is not None:
            deal.total_acquisition_budget = float(ev.value_numeric)

        ev = fields.get("BASIS_UNIT_AT_CLOSE")
        if ev and ev.value_numeric is not None and float(ev.value_numeric) > 0:
            deal.basis_per_unit = float(ev.value_numeric)
        elif deal.total_units and deal.total_units > 0:
            # Calculate basis/unit from total acquisition budget / units
            budget = deal.total_acquisition_budget or deal.purchase_price_extracted
            if budget and budget > 0:
                deal.basis_per_unit = budget / deal.total_units

        ev = fields.get("T12_RETURN_ON_PP")
        if ev and ev.value_numeric is not None and float(ev.value_numeric) > 0:
            deal.t12_cap_on_pp = float(ev.value_numeric)

        ev = fields.get("T3_RETURN_ON_PP")
        if ev and ev.value_numeric is not None and float(ev.value_numeric) > 0:
            deal.t3_cap_on_pp = float(ev.value_numeric)

        # Cap Rate on Total Cost: use T12_RETURN_ON_COST (going-in, not exit)
        ev = fields.get("T12_RETURN_ON_COST")
        if ev and ev.value_numeric is not None and float(ev.value_numeric) > 0:
            deal.total_cost_cap_t12 = float(ev.value_numeric)

        # T3 Cap Rate on Total Cost: cell G27 on Assumptions (Summary)
        ev = fields.get("T3_RETURN_ON_COST")
        if ev and ev.value_numeric is not None and float(ev.value_numeric) > 0:
            deal.total_cost_cap_t3 = float(ev.value_numeric)

        ev = fields.get("LOAN_AMOUNT")
        if ev and ev.value_numeric is not None:
            deal.loan_amount = float(ev.value_numeric)

        ev = fields.get("EQUITY_LP_CAPITAL")
        if ev and ev.value_numeric is not None:
            deal.lp_equity = float(ev.value_numeric)

        ev = fields.get("EXIT_PERIOD_MONTHS")
        if ev and ev.value_numeric is not None:
            deal.exit_months = float(ev.value_numeric)

        ev = fields.get("EXIT_CAP_RATE")
        if ev and ev.value_numeric is not None:
            deal.exit_cap_rate = float(ev.value_numeric)

        ev = fields.get("UNLEVERED_RETURNS_IRR")
        if ev and ev.value_numeric is not None:
            deal.unlevered_irr = float(ev.value_numeric)

        ev = fields.get("UNLEVERED_RETURNS_MOIC")
        if ev and ev.value_numeric is not None:
            deal.unlevered_moic = float(ev.value_numeric)

        ev = fields.get("PROPERTY_LATITUDE")
        if ev and ev.value_numeric is not None:
            deal.latitude = float(ev.value_numeric)

        ev = fields.get("PROPERTY_LONGITUDE")
        if ev and ev.value_numeric is not None:
            deal.longitude = float(ev.value_numeric)

        # Equity commitment: use LP capital from extraction
        ev = fields.get("EQUITY_LP_CAPITAL")
        if ev and ev.value_numeric is not None:
            deal.total_equity_commitment = float(ev.value_numeric)

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
    current_user: CurrentUser = Depends(require_analyst),
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

    await _enrich_deals_with_extraction(db, all_responses)

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

    # Fetch deals and build DealResponse objects (same as list/kanban endpoints)
    deal_responses: list[DealResponse] = []
    for deal_id in deal_ids:
        deal = await deal_crud.get_with_relations(db, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal {deal_id} not found",
            )
        deal_responses.append(DealResponse.model_validate(deal))

    # Enrich with extraction data (same pipeline as kanban endpoint)
    deal_responses = await _enrich_deals_with_extraction(db, deal_responses)

    # Build comparison summary from enriched data
    def find_best(attr: str, higher_is_better: bool = True) -> int | None:
        values = [
            (d.id, getattr(d, attr))
            for d in deal_responses
            if getattr(d, attr, None) is not None
        ]
        if not values:
            return None
        if higher_is_better:
            return max(values, key=lambda x: x[1])[0]
        return min(values, key=lambda x: x[1])[0]

    best_irr = find_best("levered_irr", higher_is_better=True)
    best_coc = find_best("projected_coc", higher_is_better=True)
    best_equity_multiple = find_best("projected_equity_multiple", higher_is_better=True)
    lowest_price = find_best("asking_price", higher_is_better=False)
    highest_score = find_best("deal_score", higher_is_better=True)

    # Overall recommendation
    def calc_score(d: DealResponse) -> float:
        s = 0.0
        if d.levered_irr is not None:
            s += float(d.levered_irr) * 0.3
        if d.projected_coc is not None:
            s += float(d.projected_coc) * 0.2
        if d.projected_equity_multiple is not None:
            s += float(d.projected_equity_multiple) * 0.2
        if d.deal_score is not None:
            s += (float(d.deal_score) / 100.0) * 0.3
        return s

    scores = [(d.id, calc_score(d)) for d in deal_responses]
    overall_rec = max(scores, key=lambda x: x[1])[0] if scores else None

    reasons = []
    if overall_rec:
        rec = next((d for d in deal_responses if d.id == overall_rec), None)
        if rec and rec.levered_irr is not None:
            reasons.append(f"{float(rec.levered_irr) * 100:.1f}% levered IRR")
        if rec and rec.deal_score is not None:
            reasons.append(f"score of {rec.deal_score}/100")

    comparison_summary = ComparisonSummary(
        best_irr=best_irr,
        best_coc=best_coc,
        best_equity_multiple=best_equity_multiple,
        lowest_price=lowest_price,
        highest_score=highest_score,
        overall_recommendation=overall_rec,
        recommendation_reason=f"Best overall metrics: {', '.join(reasons)}"
        if reasons
        else None,
    )

    # Build metric comparisons
    metric_comparisons = []

    def add_mc(name: str, attr: str, ctype: str = "higher_is_better"):
        vals = {d.id: getattr(d, attr, None) for d in deal_responses}
        nn = {k: v for k, v in vals.items() if v is not None}
        best_id = None
        best_val = None
        if nn:
            best_id = (
                max(nn, key=lambda k: nn[k])
                if ctype == "higher_is_better"
                else min(nn, key=lambda k: nn[k])
            )
            best_val = nn[best_id]
        metric_comparisons.append(
            MetricComparison(
                metric_name=name,
                values=vals,
                best_deal_id=best_id,
                best_value=best_val,
                comparison_type=ctype,
            )
        )

    add_mc("Levered IRR", "levered_irr")
    add_mc("NOI Margin", "noi_margin")
    add_mc("T12 Cap on PP", "t12_cap_on_pp")
    add_mc("Asking Price", "asking_price", "lower_is_better")
    add_mc("Deal Score", "deal_score")
    add_mc("Unlevered IRR", "unlevered_irr")

    slog.info(
        "deals_compared",
        user_email=current_user.email,
        user_id=current_user.id,
        deal_ids=deal_ids,
        deal_count=len(deal_ids),
        overall_recommendation=overall_rec,
    )

    return DealComparisonResponse(
        deals=deal_responses,
        comparison_summary=comparison_summary,
        metric_comparisons=metric_comparisons,
        deal_count=len(deal_responses),
        compared_at=datetime.now(UTC).isoformat(),
    )


@router.get("/{deal_id}", response_model=DealResponse)
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
    enriched = await _enrich_deals_with_extraction(db, [deal_resp])
    return enriched[0]


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
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

    slog.info(
        "deal_created",
        deal_id=new_deal.id,
        deal_name=new_deal.name,
        user_id=current_user.id,
        user_email=current_user.email,
    )

    return new_deal


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    deal_data: DealUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Update an existing deal (with optimistic locking).

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

    slog.info(
        "deal_updated",
        deal_id=deal_id,
        user_id=current_user.id,
        user_email=current_user.email,
        fields_changed=list(update_data.keys()),
    )

    return updated_deal


@router.patch("/{deal_id}", response_model=DealResponse)
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

    slog.info(
        "deal_patched",
        deal_id=deal_id,
        user_id=current_user.id,
        user_email=current_user.email,
        fields_changed=list(update_data.keys()),
    )

    return updated_deal


@router.patch("/{deal_id}/stage", response_model=DealResponse)
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

    slog.info(
        "deal_stage_changed",
        deal_id=deal_id,
        old_stage=old_stage.value if hasattr(old_stage, "value") else str(old_stage),
        new_stage=stage_data.stage,
        user_id=current_user.id,
        user_email=current_user.email,
    )

    return updated_deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
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

    slog.info(
        "deal_deleted",
        deal_id=deal_id,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return None


@router.post("/{deal_id}/restore", response_model=DealResponse)
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

    slog.info(
        "deal_restored",
        deal_id=deal_id,
        deal_name=restored.name,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return DealResponse.model_validate(restored)


@router.post("/{deal_id}/activity", response_model=DealActivityResponse)
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


@router.get("/{deal_id}/activity", response_model=DealActivityListResponse)
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


# =============================================================================
# Activity Log Endpoints (UUID-based)
# =============================================================================


@router.get("/{deal_id}/activity-log", response_model=ActivityLogListResponse)
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


@router.post("/{deal_id}/activity-log", response_model=ActivityLogResponse)
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


# ---------- Proforma Returns (from extracted_values) ----------

# Fields that only exist in Proforma/group-extraction runs
PROFORMA_FIELDS = {
    # Year-specific IRR / MOIC
    "LEVERED_RETURNS_IRR_YR2",
    "LEVERED_RETURNS_IRR_YR3",
    "LEVERED_RETURNS_IRR_YR7",
    "LEVERED_RETURNS_MOIC_YR2",
    "LEVERED_RETURNS_MOIC_YR3",
    "LEVERED_RETURNS_MOIC_YR7",
    "UNLEVERED_RETURNS_IRR_YR2",
    "UNLEVERED_RETURNS_IRR_YR3",
    "UNLEVERED_RETURNS_IRR_YR7",
    "UNLEVERED_RETURNS_MOIC_YR2",
    "UNLEVERED_RETURNS_MOIC_YR3",
    "UNLEVERED_RETURNS_MOIC_YR7",
    # NOI per unit by year
    "NOI_PER_UNIT_YR2",
    "NOI_PER_UNIT_YR3",
    "NOI_PER_UNIT_YR5",
    "NOI_PER_UNIT_YR7",
    # Cap rates
    "CAP_RATE_ALL_IN_YR3",
    "CAP_RATE_ALL_IN_YR5",
    # Cash-on-cash / DSCR
    "COC_YR5",
    "DSCR_T3",
    "DSCR_YR5",
    # Proforma NOI / DSCR / Debt Yield
    "PROFORMA_NOI_YR1",
    "PROFORMA_NOI_YR2",
    "PROFORMA_NOI_YR3",
    "PROFORMA_DSCR_YR1",
    "PROFORMA_DSCR_YR2",
    "PROFORMA_DSCR_YR3",
    "PROFORMA_DEBT_YIELD_YR1",
    "PROFORMA_DEBT_YIELD_YR2",
    "PROFORMA_DEBT_YIELD_YR3",
}


@router.get("/{deal_id}/proforma-returns")
async def get_deal_proforma_returns(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get Proforma-specific extracted values for a deal.

    Queries extracted_values for year-specific IRR, MOIC, NOI, cap rates,
    DSCR, and other fields that exist only in Proforma/group extraction runs.
    Returns values grouped by category.
    """
    # Get the deal to find its name (used as property_name in extracted_values)
    deal = await deal_crud.get(db, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal {deal_id} not found",
        )

    deal_name = deal.name

    # Also try the base name without "(City, ST)" suffix
    # sync_extracted_to_properties may have stored either variant
    import re as _re

    base_name_match = _re.match(r"^(.+?)\s*\([^)]+,\s*[A-Z]{2}\)", deal_name)
    names_to_search = [deal_name]
    if base_name_match:
        names_to_search.append(base_name_match.group(1).strip())

    # Query extracted_values for proforma fields matching this deal
    from sqlalchemy import or_

    stmt = (
        select(
            ExtractedValue.field_name,
            ExtractedValue.field_category,
            ExtractedValue.value_numeric,
            ExtractedValue.value_text,
            ExtractedValue.source_file,
        )
        .where(
            or_(*[ExtractedValue.property_name == n for n in names_to_search]),
            ExtractedValue.field_name.in_(PROFORMA_FIELDS),
            ExtractedValue.is_error.is_(False),
        )
        .order_by(ExtractedValue.field_category, ExtractedValue.field_name)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return {"deal_id": deal_id, "deal_name": deal_name, "groups": [], "total": 0}

    # Group by category
    groups: dict[str, list[dict]] = {}
    for row in rows:
        cat = row.field_category or "Proforma"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(
            {
                "field_name": row.field_name,
                "value_numeric": float(row.value_numeric)
                if row.value_numeric is not None
                else None,
                "value_text": row.value_text,
            }
        )

    return {
        "deal_id": deal_id,
        "deal_name": deal_name,
        "groups": [
            {"category": cat, "fields": fields} for cat, fields in groups.items()
        ],
        "total": len(rows),
    }
