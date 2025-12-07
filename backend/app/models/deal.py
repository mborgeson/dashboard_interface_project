"""
Deal model for tracking investment opportunities through the pipeline.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    String, Integer, Numeric, Date, DateTime, Text, JSON,
    ForeignKey, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class DealStage(str, PyEnum):
    """Deal pipeline stages for Kanban board."""
    LEAD = "lead"
    INITIAL_REVIEW = "initial_review"
    UNDERWRITING = "underwriting"
    DUE_DILIGENCE = "due_diligence"
    LOI_SUBMITTED = "loi_submitted"
    UNDER_CONTRACT = "under_contract"
    CLOSED = "closed"
    DEAD = "dead"


class Deal(Base, TimestampMixin, SoftDeleteMixin):
    """Deal model representing investment opportunities in the pipeline."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    deal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # acquisition, disposition, development

    # Pipeline Stage
    stage: Mapped[DealStage] = mapped_column(
        Enum(DealStage),
        default=DealStage.LEAD,
        nullable=False,
        index=True,
    )
    stage_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )  # For ordering within stage on Kanban

    # Relationships (Foreign Keys)
    property_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
    )
    assigned_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    # Financial Terms
    asking_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    offer_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    final_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )

    # Underwriting Metrics
    projected_irr: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    projected_coc: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    projected_equity_multiple: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    hold_period_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timeline
    initial_contact_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    loi_submitted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_diligence_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_diligence_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Source and Competition
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    broker_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    broker_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    competition_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # low, medium, high

    # Notes and Documents
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    investment_thesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_risks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    documents: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    activity_log: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Deal-specific metadata
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Scoring
    deal_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
    )  # low, medium, high, urgent

    # Stage history for tracking movement
    stage_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    # property: Mapped["Property"] = relationship("Property", back_populates="deals")
    # assigned_user: Mapped["User"] = relationship("User", back_populates="deals")

    def __repr__(self) -> str:
        return f"<Deal {self.name} ({self.stage.value})>"

    def update_stage(self, new_stage: DealStage) -> None:
        """Update the deal stage with timestamp."""
        from datetime import datetime, timezone
        self.stage = new_stage
        self.stage_updated_at = datetime.now(timezone.utc)

    def add_activity(self, activity: dict) -> None:
        """Add an activity to the log."""
        from datetime import datetime, timezone
        if self.activity_log is None:
            self.activity_log = []
        activity["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.activity_log.append(activity)
