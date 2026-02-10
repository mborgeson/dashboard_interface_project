"""
Deal model for tracking investment opportunities through the pipeline.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum as PyEnum

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class DealStage(PyEnum):
    """Deal pipeline stages for Kanban board (6-stage model)."""

    DEAD = "dead"
    INITIAL_REVIEW = "initial_review"
    ACTIVE_REVIEW = "active_review"
    UNDER_CONTRACT = "under_contract"
    CLOSED = "closed"
    REALIZED = "realized"


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
        Enum(DealStage, values_callable=lambda e: [m.value for m in e]),
        default=DealStage.INITIAL_REVIEW,
        nullable=False,
        index=True,
    )
    stage_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )  # For ordering within stage on Kanban

    # Relationships (Foreign Keys)
    property_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
    )
    assigned_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    # Financial Terms
    asking_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    offer_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    final_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )

    # Underwriting Metrics
    projected_irr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    projected_coc: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    projected_equity_multiple: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    hold_period_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timeline
    initial_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    loi_submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_diligence_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_diligence_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Source and Competition
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    broker_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    competition_level: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # low, medium, high

    # Notes and Documents
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    investment_thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    documents: Mapped[list | None] = mapped_column(JSON, nullable=True)
    activity_log: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Deal-specific metadata
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Scoring
    deal_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
    )  # low, medium, high, urgent

    # Stage history for tracking movement
    stage_updated_at: Mapped[datetime | None] = mapped_column(
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
        from datetime import datetime

        self.stage = new_stage
        self.stage_updated_at = datetime.now(UTC)

    def add_activity(self, activity: dict) -> None:
        """Add an activity to the log."""
        from datetime import datetime

        if self.activity_log is None:
            self.activity_log = []
        activity["timestamp"] = datetime.now(UTC).isoformat()
        self.activity_log.append(activity)
