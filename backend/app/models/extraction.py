"""
Extraction models for tracking SharePoint UW model data extraction runs and values.

Uses Entity-Attribute-Value (EAV) pattern to store extracted fields as rows
rather than 1,179 columns, which:
- Avoids column limit issues
- Makes adding new fields trivial
- Enables field-by-field error tracking
- Simplifies queries with proper indexing
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class ExtractionRun(Base, TimestampMixin):
    """
    Tracks each extraction batch run.

    Records when extractions are started/completed, how many files were
    processed, and aggregated error information.
    """

    __tablename__ = "extraction_runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status: running, completed, failed, cancelled
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running", index=True
    )

    # Trigger type: manual, scheduled
    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )

    # Processing statistics
    files_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Error summary (JSON for flexibility)
    error_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    extracted_values: Mapped[list["ExtractedValue"]] = relationship(
        "ExtractedValue", back_populates="extraction_run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ExtractionRun {self.id} ({self.status})>"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate extraction duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float | None:
        """Calculate file processing success rate."""
        total = self.files_processed + self.files_failed
        if total > 0:
            return round(self.files_processed / total * 100, 1)
        return None


class ExtractedValue(Base, TimestampMixin):
    """
    Stores individual extracted values from UW models.

    Uses EAV (Entity-Attribute-Value) pattern where each field from the
    Excel extraction becomes a row rather than a column.
    """

    __tablename__ = "extracted_values"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )

    # Foreign keys
    extraction_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Property identifier (links to main properties table or standalone)
    property_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Property name (for cases where property_id doesn't exist yet)
    property_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Field metadata
    field_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    field_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cell_address: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Value storage (multiple columns for different types)
    # All values also stored as text for universal access
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Numeric values use Decimal(20, 4) to handle large financial numbers
    # without integer overflow issues
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    value_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    # Error tracking
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Source file path
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    extraction_run: Mapped["ExtractionRun"] = relationship(
        "ExtractionRun", back_populates="extracted_values"
    )

    # Constraints
    __table_args__ = (
        # Prevent duplicate fields for same extraction run + property
        UniqueConstraint(
            "extraction_run_id",
            "property_name",
            "field_name",
            name="uq_extracted_value",
        ),
        # Index for common queries
        Index("idx_extracted_values_lookup", "property_name", "field_name"),
    )

    def __repr__(self) -> str:
        return f"<ExtractedValue {self.property_name}.{self.field_name}>"

    @property
    def value(self):
        """Get the most appropriate value based on type."""
        if self.value_numeric is not None:
            return self.value_numeric
        if self.value_date is not None:
            return self.value_date
        return self.value_text
