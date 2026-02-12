"""
ReminderDismissal model — tracks dismissed import reminders per session/user.

Each row represents a reminder dismissal for a specific month, allowing
dismissals to persist across server restarts.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class ReminderDismissal(Base, TimestampMixin):
    """Tracks dismissed import reminders."""

    __tablename__ = "reminder_dismissals"

    __table_args__ = (
        UniqueConstraint(
            "user_identifier",
            "dismissed_month",
            name="uq_reminder_dismissal_user_month",
        ),
        Index("ix_reminder_dismissals_month", "dismissed_month"),
    )

    # ── Primary Key ──────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Dismissal Details ────────────────────────────────────────────────
    # User/session identifier (can be session ID, user ID, or "global" for all users)
    user_identifier: Mapped[str] = mapped_column(String(255), nullable=False)

    # The month that was dismissed (format: "YYYY-MM")
    dismissed_month: Mapped[str] = mapped_column(String(7), nullable=False)

    # When the dismissal occurred
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ReminderDismissal(id={self.id}, user={self.user_identifier}, "
            f"month={self.dismissed_month})>"
        )
