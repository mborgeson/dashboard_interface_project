"""
Deal comparison schemas for API request/response validation.
"""

from decimal import Decimal

from pydantic import Field

from .base import BaseSchema


class DealMetrics(BaseSchema):
    """Metrics for a single deal used in comparison."""

    id: int
    name: str
    deal_type: str
    stage: str
    priority: str

    # Financial metrics
    asking_price: Decimal | None = None
    offer_price: Decimal | None = None
    final_price: Decimal | None = None

    # Performance projections
    projected_irr: Decimal | None = None
    projected_coc: Decimal | None = None
    projected_equity_multiple: Decimal | None = None
    hold_period_years: int | None = None

    # Deal score
    deal_score: int | None = None

    # Timeline info
    days_in_pipeline: int | None = None
    target_close_date: str | None = None

    # Property info (if linked)
    property_name: str | None = None
    property_type: str | None = None
    property_market: str | None = None
    total_units: int | None = None
    total_sf: int | None = None


class MetricComparison(BaseSchema):
    """Comparison results for a specific metric across deals."""

    metric_name: str
    values: dict[int, Decimal | int | str | None]  # deal_id -> value
    best_deal_id: int | None = None
    best_value: Decimal | int | str | None = None
    comparison_type: str = "higher_is_better"  # or "lower_is_better"


class ComparisonSummary(BaseSchema):
    """Summary of which deal is best for each key metric."""

    best_irr: int | None = None  # deal_id with best IRR
    best_coc: int | None = None  # deal_id with best CoC
    best_equity_multiple: int | None = None
    lowest_price: int | None = None
    highest_score: int | None = None
    overall_recommendation: int | None = None  # Overall best deal
    recommendation_reason: str | None = None


class DealComparisonResponse(BaseSchema):
    """Response for deal comparison endpoint."""

    deals: list[DealMetrics]
    comparison_summary: ComparisonSummary
    metric_comparisons: list[MetricComparison]

    # Request metadata
    deal_count: int
    compared_at: str  # ISO timestamp


class DealComparisonRequest(BaseSchema):
    """Request body for deal comparison (alternative to query param)."""

    deal_ids: list[int] = Field(..., min_length=2, max_length=10)


class QuickCompareResponse(BaseSchema):
    """Simplified comparison for quick view."""

    deals: list[dict]  # Simplified deal info
    winner: dict | None = None  # Best deal summary
    key_differences: list[str]  # List of notable differences
