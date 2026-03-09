"""
AuditLog model for tracking admin actions.

Provides a tamper-evident audit trail for administrative operations
including user management, settings changes, and data modifications.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """
    Audit log entry for admin actions.

    Records who did what, when, and from where. Details column stores
    JSON-serialized context (old/new values, request body summaries).

    Note: No server_default on timestamps for SQLite test compatibility.
    """

    __tablename__ = "audit_logs_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # When
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Who
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # What
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Context
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Standard timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} action={self.action} user={self.user_email}>"
