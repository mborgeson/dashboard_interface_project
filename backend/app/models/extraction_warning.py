"""Stores reconciliation, validation, and drift warnings from extraction pipeline."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractionWarning(Base):
    __tablename__ = "extraction_warnings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    extraction_run_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    property_name: Mapped[str] = mapped_column(String(500), index=True)
    source_file: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    warning_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # "reconciliation" | "validation" | "drift"
    severity: Mapped[str] = mapped_column(String(20))  # "error" | "warning" | "info"
    field_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
