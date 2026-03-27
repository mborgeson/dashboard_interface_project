"""
Pydantic schemas for the reconciliation report service.

Defines request/response models for comparing SharePoint folder contents
with database state and tracking discrepancies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FileDiscrepancy(BaseModel):
    """A single file that exists in one source but not the other."""

    model_config = ConfigDict(from_attributes=True)

    file_path: str
    file_name: str
    deal_name: str
    location: Literal["sharepoint_only", "database_only"]
    last_modified: datetime | None = None
    size_bytes: int | None = None


class ExtractionStaleness(BaseModel):
    """Tracks how stale an extraction is for a given file."""

    model_config = ConfigDict(from_attributes=True)

    file_path: str
    file_name: str
    deal_name: str
    file_modified_date: datetime
    last_extracted: datetime | None = None
    hours_stale: float | None = None


class ReconciliationReport(BaseModel):
    """Complete reconciliation report comparing SharePoint and database state."""

    model_config = ConfigDict(from_attributes=True)

    report_id: str = Field(description="Unique identifier for the report run")
    generated_at: datetime
    duration_seconds: float = Field(
        description="How long the reconciliation took to run"
    )

    # Summary counts
    total_sharepoint_files: int = 0
    total_database_files: int = 0
    files_in_sync: int = 0

    # Discrepancies
    sharepoint_only: list[FileDiscrepancy] = Field(
        default_factory=list,
        description="Files in SharePoint but not tracked in the database",
    )
    database_only: list[FileDiscrepancy] = Field(
        default_factory=list,
        description="Files tracked in database but missing from SharePoint",
    )

    # Stale extractions
    stale_extractions: list[ExtractionStaleness] = Field(
        default_factory=list,
        description="Files where the extraction is older than the file modification",
    )

    # Status
    sharepoint_available: bool = Field(
        description="Whether SharePoint was reachable during this run"
    )
    error: str | None = Field(
        default=None,
        description="Error message if reconciliation could not complete fully",
    )

    @property
    def total_discrepancies(self) -> int:
        return len(self.sharepoint_only) + len(self.database_only)


class ReconciliationHistoryItem(BaseModel):
    """Abbreviated report for the history listing."""

    model_config = ConfigDict(from_attributes=True)

    report_id: str
    generated_at: datetime
    total_sharepoint_files: int
    total_database_files: int
    files_in_sync: int
    sharepoint_only_count: int
    database_only_count: int
    stale_extraction_count: int
    sharepoint_available: bool
    error: str | None = None


class ReconciliationTriggerResponse(BaseModel):
    """Response when triggering a new reconciliation."""

    message: str
    report: ReconciliationReport
