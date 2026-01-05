"""
Pydantic schemas for extraction API endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExtractionStartRequest(BaseModel):
    """Request to start a new extraction."""

    source: str = Field(
        default="sharepoint", description="Data source: 'sharepoint' or 'local'"
    )
    file_paths: list[str] | None = Field(
        default=None, description="Specific file paths to extract (for local source)"
    )


class ExtractionStartResponse(BaseModel):
    """Response after starting extraction."""

    run_id: UUID
    status: str
    message: str
    files_discovered: int


class ExtractionStatusResponse(BaseModel):
    """Current status of an extraction run."""

    run_id: UUID
    status: str  # running, completed, failed, cancelled
    trigger_type: str
    started_at: datetime
    completed_at: datetime | None = None
    files_discovered: int
    files_processed: int
    files_failed: int
    success_rate: float | None = None
    duration_seconds: float | None = None
    error_summary: dict[str, Any] | None = None


class ExtractionHistoryItem(BaseModel):
    """Summary of a past extraction run."""

    run_id: UUID
    status: str
    trigger_type: str
    started_at: datetime
    completed_at: datetime | None = None
    files_processed: int
    files_failed: int
    success_rate: float | None = None

    class Config:
        from_attributes = True


class ExtractionHistoryResponse(BaseModel):
    """Response for extraction history."""

    runs: list[ExtractionHistoryItem]
    total: int


class ExtractedPropertySummary(BaseModel):
    """Summary of extracted data for a property."""

    property_name: str
    extraction_run_id: UUID
    total_fields: int
    successful_fields: int
    error_fields: int
    sample_values: dict[str, Any]


class PropertyListResponse(BaseModel):
    """List of properties with extracted data."""

    properties: list[str]
    total: int


class SchedulerStatusResponse(BaseModel):
    """Status of the extraction scheduler."""

    enabled: bool
    cron_expression: str
    next_run: datetime | None = None
    last_run: datetime | None = None


class SchedulerUpdateRequest(BaseModel):
    """Request to update scheduler settings."""

    enabled: bool | None = None
    cron_expression: str | None = None
