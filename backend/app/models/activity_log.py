"""
ActivityLog model for tracking deal activities with UUID-based IDs.

This model provides a separate, comprehensive audit trail for deal activities
with JSON metadata support for storing old/new values on changes.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityAction(PyEnum):
    """Types of actions that can be logged for deals."""

    CREATED = "created"
    UPDATED = "updated"
    STAGE_CHANGED = "stage_changed"
    DOCUMENT_ADDED = "document_added"
    DOCUMENT_REMOVED = "document_removed"
    NOTE_ADDED = "note_added"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    PRICE_CHANGED = "price_changed"
    VIEWED = "viewed"


class ActivityLog(Base):
    """
    Activity log for tracking all changes and events on deals.

    Uses UUID primary keys and JSON for flexible metadata storage.
    This provides a comprehensive audit trail for deal lifecycle events.

    Note: Uses JSON type for SQLite compatibility in tests. Production
    PostgreSQL will use the same JSON type which works well.
    """

    __tablename__ = "activity_logs"

    # UUID primary key - uses PG_UUID for PostgreSQL, falls back to String for SQLite
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Relationship to deal (integer FK to match deals table)
    deal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional user identifier (string for future auth flexibility)
    user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Action type (enum)
    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )

    # Human-readable description
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # JSON metadata for storing old/new values, additional context
    # Example: {"old_stage": "initial_review", "new_stage": "active_review"}
    # Note: Using 'meta' instead of 'metadata' to avoid SQLAlchemy reserved attribute
    # Uses JSONB on PostgreSQL (with variant) and JSON on SQLite for testing
    meta: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        nullable=True,
        name="metadata",  # Column name in DB is still 'metadata'
    )

    # Timestamp (no server_default for SQLite test compatibility)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ActivityLog {self.id} action={self.action.value} deal={self.deal_id}>"
