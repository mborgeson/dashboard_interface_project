"""
Database models for SharePoint file monitoring.

Tracks the state of monitored files to detect changes:
- New files added to deal folders
- Existing files modified (updated modified_date)
- Files that have been deleted
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class MonitoredFile(Base, TimestampMixin):
    """
    Tracks SharePoint files being monitored for changes.

    Stores the last known state of each UW model file in SharePoint
    to enable change detection through periodic polling.
    """

    __tablename__ = "monitored_files"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )

    # File identification
    file_path: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # File metadata for change detection
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    modified_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hash for content-based change detection

    # Tracking timestamps
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    last_checked: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    last_extracted: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extraction_pending: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationship to extraction runs
    extraction_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Additional file metadata
    deal_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    extraction_run: Mapped["ExtractionRun"] = relationship(
        "ExtractionRun", foreign_keys=[extraction_run_id]
    )

    __table_args__ = (
        # Index for finding files by deal
        Index("idx_monitored_files_deal", "deal_name", "is_active"),
        # Index for finding pending extractions
        Index("idx_monitored_files_pending", "extraction_pending", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<MonitoredFile {self.file_name} ({self.deal_name})>"

    @property
    def needs_extraction(self) -> bool:
        """Check if file needs extraction based on tracking state."""
        if not self.is_active:
            return False
        if self.extraction_pending:
            return True
        if self.last_extracted is None:
            return True
        return self.modified_date > self.last_extracted


class FileChangeLog(Base, TimestampMixin):
    """
    Logs detected file changes for audit trail and debugging.

    Records each detected change (added, modified, deleted) to help
    understand file activity patterns and troubleshoot issues.
    """

    __tablename__ = "file_change_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )

    # Change details
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Change type: 'added', 'modified', 'deleted'
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Before/after state for modifications
    old_modified_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_modified_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    old_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    new_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # When the change was detected
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Link to monitored file (if still exists)
    monitored_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("monitored_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Whether extraction was triggered
    extraction_triggered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    extraction_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        # Index for finding recent changes
        Index("idx_file_change_logs_detected", "detected_at"),
    )

    def __repr__(self) -> str:
        return f"<FileChangeLog {self.change_type}: {self.file_name}>"
