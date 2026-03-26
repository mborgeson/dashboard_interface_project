"""
StageChangeLog model — audit trail for deal stage transitions.

Records every stage change with source tracking so we know
whether a transition was triggered by SharePoint sync, Kanban
drag-and-drop, extraction sync, or manual override.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StageChangeSource(StrEnum):
    """How a deal stage change was triggered."""

    SHAREPOINT_SYNC = "sharepoint_sync"
    USER_KANBAN = "user_kanban"
    EXTRACTION_SYNC = "extraction_sync"
    MANUAL_OVERRIDE = "manual_override"


class StageChangeLog(Base):
    """Audit log entry for a single deal stage transition."""

    __tablename__ = "stage_change_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    deal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    old_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    new_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source: Mapped[StageChangeSource] = mapped_column(
        Enum(
            StageChangeSource,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        nullable=False,
    )

    changed_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
