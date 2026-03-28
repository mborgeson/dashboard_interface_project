"""
SchemaDriftAlert model for persisting drift detection results.

When the schema drift detector finds a warning or error-level divergence
between a new file and its group baseline, an alert is persisted so that
analysts can review and resolve it.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class SchemaDriftAlert(Base, TimestampMixin):
    """Persisted alert from schema drift detection.

    Created when a file's structural fingerprint diverges from the
    group baseline beyond the "ok" threshold.
    """

    __tablename__ = "schema_drift_alerts"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    group_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    similarity_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    changed_sheets: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    missing_sheets: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    new_sheets: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SchemaDriftAlert group={self.group_name!r} "
            f"severity={self.severity!r} resolved={self.resolved}>"
        )
