"""
Deal schemas for API request/response validation.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class DealBase(BaseSchema):
    """Base deal schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    deal_type: str = Field(
        ...,
        pattern="^(acquisition|disposition|development|refinance)$"
    )
    property_id: Optional[int] = None
    assigned_user_id: Optional[int] = None


class DealCreate(DealBase):
    """Schema for creating a new deal."""

    # Initial stage (defaults to LEAD)
    stage: str = Field(
        default="lead",
        pattern="^(lead|initial_review|underwriting|due_diligence|loi_submitted|under_contract|closed|dead)$"
    )

    # Financial Terms
    asking_price: Optional[Decimal] = Field(None, ge=0)
    offer_price: Optional[Decimal] = Field(None, ge=0)

    # Underwriting Metrics
    projected_irr: Optional[Decimal] = Field(None, ge=0, le=1)
    projected_coc: Optional[Decimal] = Field(None, ge=0, le=1)
    projected_equity_multiple: Optional[Decimal] = Field(None, ge=0)
    hold_period_years: Optional[int] = Field(None, ge=1, le=30)

    # Timeline
    initial_contact_date: Optional[date] = None
    target_close_date: Optional[date] = None

    # Source
    source: Optional[str] = Field(None, max_length=100)
    broker_name: Optional[str] = Field(None, max_length=255)
    broker_company: Optional[str] = Field(None, max_length=255)
    competition_level: Optional[str] = Field(
        None,
        pattern="^(low|medium|high)$"
    )

    # Notes
    notes: Optional[str] = None
    investment_thesis: Optional[str] = None
    key_risks: Optional[str] = None

    # Metadata
    tags: Optional[list[str]] = None
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high|urgent)$"
    )


class DealUpdate(BaseSchema):
    """Schema for updating a deal. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    deal_type: Optional[str] = Field(
        None,
        pattern="^(acquisition|disposition|development|refinance)$"
    )
    property_id: Optional[int] = None
    assigned_user_id: Optional[int] = None

    asking_price: Optional[Decimal] = Field(None, ge=0)
    offer_price: Optional[Decimal] = Field(None, ge=0)
    final_price: Optional[Decimal] = Field(None, ge=0)

    projected_irr: Optional[Decimal] = Field(None, ge=0, le=1)
    projected_coc: Optional[Decimal] = Field(None, ge=0, le=1)
    projected_equity_multiple: Optional[Decimal] = Field(None, ge=0)
    hold_period_years: Optional[int] = Field(None, ge=1, le=30)

    initial_contact_date: Optional[date] = None
    loi_submitted_date: Optional[date] = None
    due_diligence_start: Optional[date] = None
    due_diligence_end: Optional[date] = None
    target_close_date: Optional[date] = None
    actual_close_date: Optional[date] = None

    source: Optional[str] = Field(None, max_length=100)
    broker_name: Optional[str] = Field(None, max_length=255)
    broker_company: Optional[str] = Field(None, max_length=255)
    competition_level: Optional[str] = Field(
        None,
        pattern="^(low|medium|high)$"
    )

    notes: Optional[str] = None
    investment_thesis: Optional[str] = None
    key_risks: Optional[str] = None

    tags: Optional[list[str]] = None
    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high|urgent)$"
    )
    deal_score: Optional[int] = Field(None, ge=0, le=100)


class DealStageUpdate(BaseSchema):
    """Schema for updating deal stage (Kanban movement)."""

    stage: str = Field(
        ...,
        pattern="^(lead|initial_review|underwriting|due_diligence|loi_submitted|under_contract|closed|dead)$"
    )
    stage_order: Optional[int] = Field(None, ge=0)


class DealResponse(DealBase, TimestampSchema):
    """Schema for deal response."""

    id: int
    stage: str
    stage_order: int

    asking_price: Optional[Decimal] = None
    offer_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None

    projected_irr: Optional[Decimal] = None
    projected_coc: Optional[Decimal] = None
    projected_equity_multiple: Optional[Decimal] = None
    hold_period_years: Optional[int] = None

    initial_contact_date: Optional[date] = None
    loi_submitted_date: Optional[date] = None
    due_diligence_start: Optional[date] = None
    due_diligence_end: Optional[date] = None
    target_close_date: Optional[date] = None
    actual_close_date: Optional[date] = None

    source: Optional[str] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    competition_level: Optional[str] = None

    notes: Optional[str] = None
    investment_thesis: Optional[str] = None
    key_risks: Optional[str] = None
    documents: Optional[list[dict]] = None
    activity_log: Optional[list[dict]] = None

    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    deal_score: Optional[int] = None
    priority: str

    stage_updated_at: Optional[datetime] = None


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
