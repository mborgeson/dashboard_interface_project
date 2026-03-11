"""
Deal schemas for API request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from app.core.sanitization import make_sanitized_validator

from .base import BaseSchema, TimestampSchema


class RecentActivityItem(BaseSchema):
    """Compact activity entry embedded in deal responses."""

    action: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DealBase(BaseSchema):
    """Base deal schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    deal_type: str = Field(
        ..., pattern="^(acquisition|disposition|development|refinance)$"
    )
    property_id: int | None = None
    assigned_user_id: int | None = None


class DealCreate(DealBase):
    """Schema for creating a new deal."""

    # Initial stage (defaults to initial_review)
    stage: str = Field(
        default="initial_review",
        pattern="^(dead|initial_review|active_review|under_contract|closed|realized)$",
    )

    # Financial Terms
    asking_price: Decimal | None = Field(None, ge=0)
    offer_price: Decimal | None = Field(None, ge=0)

    # Underwriting Metrics
    projected_irr: Decimal | None = Field(None, ge=0, le=1)
    projected_coc: Decimal | None = Field(None, ge=0, le=1)
    projected_equity_multiple: Decimal | None = Field(None, ge=0)
    hold_period_years: int | None = Field(None, ge=1, le=30)

    # Timeline
    initial_contact_date: date | None = None
    target_close_date: date | None = None

    # Source
    source: str | None = Field(None, max_length=100)
    broker_name: str | None = Field(None, max_length=255)
    broker_company: str | None = Field(None, max_length=255)
    competition_level: str | None = Field(None, pattern="^(low|medium|high)$")

    # Notes
    notes: str | None = None
    investment_thesis: str | None = None
    key_risks: str | None = None

    # Metadata
    tags: list[str] | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")

    _sanitize = model_validator(mode="before")(
        make_sanitized_validator(
            "name",
            "source",
            "broker_name",
            "broker_company",
            "notes",
            "investment_thesis",
            "key_risks",
            "tags",
        )
    )


class DealUpdate(BaseSchema):
    """Schema for updating a deal. All fields optional except version (optimistic lock)."""

    # Optimistic locking — client must send the version it last read
    version: int = Field(..., description="Current version for optimistic locking")

    name: str | None = Field(None, min_length=1, max_length=255)
    deal_type: str | None = Field(
        None, pattern="^(acquisition|disposition|development|refinance)$"
    )
    property_id: int | None = None
    assigned_user_id: int | None = None

    asking_price: Decimal | None = Field(None, ge=0)
    offer_price: Decimal | None = Field(None, ge=0)
    final_price: Decimal | None = Field(None, ge=0)

    projected_irr: Decimal | None = Field(None, ge=0, le=1)
    projected_coc: Decimal | None = Field(None, ge=0, le=1)
    projected_equity_multiple: Decimal | None = Field(None, ge=0)
    hold_period_years: int | None = Field(None, ge=1, le=30)

    initial_contact_date: date | None = None
    loi_submitted_date: date | None = None
    due_diligence_start: date | None = None
    due_diligence_end: date | None = None
    target_close_date: date | None = None
    actual_close_date: date | None = None

    source: str | None = Field(None, max_length=100)
    broker_name: str | None = Field(None, max_length=255)
    broker_company: str | None = Field(None, max_length=255)
    competition_level: str | None = Field(None, pattern="^(low|medium|high)$")

    notes: str | None = None
    investment_thesis: str | None = None
    key_risks: str | None = None

    tags: list[str] | None = None
    priority: str | None = Field(None, pattern="^(low|medium|high|urgent)$")
    deal_score: int | None = Field(None, ge=0, le=100)

    _sanitize = model_validator(mode="before")(
        make_sanitized_validator(
            "name",
            "source",
            "broker_name",
            "broker_company",
            "notes",
            "investment_thesis",
            "key_risks",
            "tags",
        )
    )


class DealStageUpdate(BaseSchema):
    """Schema for updating deal stage (Kanban movement)."""

    stage: str = Field(
        ...,
        pattern="^(dead|initial_review|active_review|under_contract|closed|realized)$",
    )
    stage_order: int | None = Field(None, ge=0)


class DealResponse(DealBase, TimestampSchema):
    """Schema for deal response."""

    id: int
    version: int = 1
    # Override inherited pattern constraints — response schemas must not re-validate
    # data already stored in the database.  Any value present in the DB is valid here.
    deal_type: str
    name: str
    stage: str
    stage_order: int

    asking_price: Decimal | None = None
    offer_price: Decimal | None = None
    final_price: Decimal | None = None

    projected_irr: Decimal | None = None
    projected_coc: Decimal | None = None
    projected_equity_multiple: Decimal | None = None
    hold_period_years: int | None = None

    initial_contact_date: date | None = None
    loi_submitted_date: date | None = None
    due_diligence_start: date | None = None
    due_diligence_end: date | None = None
    target_close_date: date | None = None
    actual_close_date: date | None = None

    source: str | None = None
    broker_name: str | None = None
    broker_company: str | None = None
    competition_level: str | None = None

    notes: str | None = None
    investment_thesis: str | None = None
    key_risks: str | None = None
    documents: list[dict] | None = None
    activity_log: list[dict] | None = None

    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None
    deal_score: int | None = None
    priority: str

    stage_updated_at: datetime | None = None

    # Enrichment fields from extraction data
    total_units: int | None = None
    avg_unit_sf: float | None = None
    current_owner: str | None = None
    last_sale_price_per_unit: float | None = None
    last_sale_date: str | None = None
    t12_return_on_cost: float | None = None
    levered_irr: float | None = None
    levered_moic: float | None = None
    total_equity_commitment: float | None = None
    # Location
    property_city: str | None = None
    submarket: str | None = None
    year_built: int | None = None
    year_renovated: int | None = None
    # Loss factors
    vacancy_rate: float | None = None
    bad_debt_rate: float | None = None
    other_loss_rate: float | None = None
    concessions_rate: float | None = None
    # NOI
    noi_margin: float | None = None
    # Basis
    purchase_price_extracted: float | None = None
    total_acquisition_budget: float | None = None
    basis_per_unit: float | None = None
    # Cap rates
    t12_cap_on_pp: float | None = None
    t3_cap_on_pp: float | None = None
    total_cost_cap_t12: float | None = None
    total_cost_cap_t3: float | None = None
    # Capital
    loan_amount: float | None = None
    lp_equity: float | None = None
    # Exit
    exit_months: float | None = None
    exit_cap_rate: float | None = None
    # Returns
    unlevered_irr: float | None = None
    unlevered_moic: float | None = None
    lp_irr: float | None = None
    lp_moic: float | None = None
    # Map coordinates
    latitude: float | None = None
    longitude: float | None = None

    # Mini activity feed (most recent 1-3 actions)
    recent_activities: list[RecentActivityItem] | None = None


class DealListResponse(BaseSchema):
    """Paginated list of deals."""

    items: list[DealResponse]
    total: int
    page: int
    page_size: int


class DealCursorPaginatedResponse(BaseSchema):
    """Cursor-paginated list of deals."""

    items: list[DealResponse]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class KanbanBoardResponse(BaseSchema):
    """Kanban board with deals grouped by stage."""

    stages: dict[str, list[DealResponse]]
    total_deals: int
    stage_counts: dict[str, int]


# ── Proforma Returns Response ────────────────────────────────────────────────


class ProformaFieldValue(BaseSchema):
    """A single proforma field with its extracted value."""

    field_name: str
    value_numeric: float | None = None
    value_text: str | None = None


class ProformaFieldGroup(BaseSchema):
    """A group of proforma fields under a category."""

    category: str
    fields: list[ProformaFieldValue]


class ProformaReturnsResponse(BaseSchema):
    """Proforma returns extracted from UW models for a deal."""

    deal_id: int
    deal_name: str
    groups: list[ProformaFieldGroup]
    total: int


# ── Watchlist Status Response ────────────────────────────────────────────────


class WatchlistStatusResponse(BaseSchema):
    """Watchlist status for a deal and the current user."""

    deal_id: int
    is_watched: bool
