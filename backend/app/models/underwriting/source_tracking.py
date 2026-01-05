"""
Source Tracking Mixin for Excel/SharePoint data extraction traceability.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class SourceTrackingMixin:
    """
    Mixin for tracking data source from Excel/SharePoint extraction.

    Enables:
    - Traceability back to source files
    - Audit trail for data lineage
    - Conflict resolution for updates
    - Data quality monitoring
    """

    # Source file information
    source_file_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Name of the source Excel file"
    )
    source_file_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Full SharePoint/file path to source"
    )
    source_file_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last modified timestamp of source file",
    )

    # Extraction metadata
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When data was extracted from source",
    )
    extraction_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Version of extraction script used"
    )

    # Data quality flags
    extraction_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default="pending",
        comment="Status: pending, success, partial, error",
    )
    extraction_errors: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Any errors during extraction"
    )
