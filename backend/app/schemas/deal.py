"""
Deal schemas for API request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from .base import BaseSchema, TimestampSchema


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

    # Initial stage (defaults to LEAD)
    stage: str = Field(
        default="lead",
        pattern="^(lead|initial_review|underwriting|due_diligence|loi_submitted|under_contract|closed|dead)$",
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


class DealUpdate(BaseSchema):
    """Schema for updating a deal. All fields optional."""

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


class DealStageUpdate(BaseSchema):
    """Schema for updating deal stage (Kanban movement)."""

    stage: str = Field(
        ...,
        pattern="^(lead|initial_review|underwriting|due_diligence|loi_submitted|under_contract|closed|dead)$",
    )
    stage_order: int | None = Field(None, ge=0)


class DealResponse(DealBase, TimestampSchema):
    """Schema for deal response."""

    id: int
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


class DealListResponse(BaseSchema):
    """Paginated list of deals."""

    items: list[DealResponse]
    total: int
    page: int
    page_size: int


class KanbanBoardResponse(BaseSchema):
    """Kanban board with deals grouped by stage."""

    stages: dict[str, list[DealResponse]]
    total_deals: int
    stage_counts: dict[str, int]
