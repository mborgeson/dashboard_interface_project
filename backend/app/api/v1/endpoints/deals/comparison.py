"""
Deal comparison endpoints — side-by-side deal analysis.

TODO (C-TD-018): The comparison logic (scoring, metric comparisons,
recommendation generation) in ``compare_deals`` is a candidate for
extraction into a dedicated service layer (e.g.
``app/services/deal_comparison_service.py``). This would:
  - Improve testability (unit-test scoring logic without HTTP)
  - Enable reuse (e.g. batch comparison in reports)
  - Reduce endpoint function length (~150 lines -> ~30)
Deferred to a future sprint as it requires careful integration testing.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user
from app.crud import deal as deal_crud
from app.db.session import get_db
from app.schemas.comparison import (
    ComparisonSummary,
    DealComparisonResponse,
    MetricComparison,
)
from app.schemas.deal import DealResponse

from .enrichment import enrich_deals_with_extraction

router = APIRouter()


@router.get(
    "/compare",
    response_model=DealComparisonResponse,
    summary="Compare deals side-by-side",
    description="Compare 2-10 deals with detailed metric comparisons including levered/unlevered "
    "IRR, NOI margin, cap rates, and deal scores. Returns a recommendation based on "
    "weighted scoring across all metrics.",
    responses={
        200: {
            "description": "Side-by-side deal comparison with summary and recommendation"
        },
        400: {
            "description": "Invalid deal IDs or fewer than 2 / more than 10 deals specified"
        },
        404: {"description": "One or more deal IDs not found"},
    },
)
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

    # Batch-fetch all deals in a single query instead of one query per deal (N+1 fix)
    deals = await deal_crud.get_by_ids(db, ids=deal_ids)
    found_ids = {d.id for d in deals}
    for did in deal_ids:
        if did not in found_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal {did} not found",
            )
    # Preserve the original order requested by the caller
    deals_by_id = {d.id: d for d in deals}
    deal_responses = [DealResponse.model_validate(deals_by_id[did]) for did in deal_ids]

    # Enrich with extraction data (same pipeline as kanban endpoint)
    deal_responses = await enrich_deals_with_extraction(db, deal_responses)

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

    logger.info(
        f"deals_compared user_email={current_user.email} user_id={current_user.id} "
        f"deal_ids={deal_ids} deal_count={len(deal_ids)} overall_recommendation={overall_rec}"
    )

    return DealComparisonResponse(
        deals=deal_responses,
        comparison_summary=comparison_summary,
        metric_comparisons=metric_comparisons,
        deal_count=len(deal_responses),
        compared_at=datetime.now(UTC).isoformat(),
    )
