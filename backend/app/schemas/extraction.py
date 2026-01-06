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

    enabled: bool = Field(description="Whether the scheduler is enabled")
    cron_expression: str = Field(description="Cron expression for scheduling")
    timezone: str = Field(description="Timezone for scheduling")
    next_run: datetime | None = Field(
        default=None, description="Next scheduled run time"
    )
    last_run: datetime | None = Field(default=None, description="Last run timestamp")
    last_run_id: str | None = Field(
        default=None, description="UUID of the last extraction run"
    )
    running: bool = Field(
        default=False, description="Whether an extraction is currently in progress"
    )


class SchedulerConfigRequest(BaseModel):
    """Request to update scheduler configuration."""

    enabled: bool | None = Field(
        default=None, description="Enable or disable scheduled extractions"
    )
    cron_expression: str | None = Field(
        default=None,
        description="Cron expression (e.g., '0 2 * * *' for daily at 2 AM)",
    )
    timezone: str | None = Field(
        default=None,
        description="Timezone for scheduling (e.g., 'America/Phoenix')",
    )


class SchedulerUpdateRequest(BaseModel):
    """Request to update scheduler settings (deprecated, use SchedulerConfigRequest)."""

    enabled: bool | None = None
    cron_expression: str | None = None


class FileFilterConfig(BaseModel):
    """Current file filter configuration."""

    file_pattern: str | None = Field(
        default=None,
        description="Regex pattern for matching UW model filenames",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="List of substrings to exclude from processing",
    )
    valid_extensions: list[str] = Field(
        default_factory=list,
        description="List of valid file extensions",
    )
    cutoff_date: str | None = Field(
        default=None,
        description="Skip files older than this date (ISO format)",
    )
    max_file_size_mb: float = Field(
        default=100.0,
        description="Maximum file size in MB",
    )


class FileFilterResponse(BaseModel):
    """Response containing filter configuration and statistics."""

    config: FileFilterConfig
    source: str = Field(
        default="environment",
        description="Configuration source (environment, defaults)",
    )


class SkippedFileInfo(BaseModel):
    """Information about a file that was skipped during discovery."""

    name: str
    path: str
    size_bytes: int
    modified_date: datetime
    skip_reason: str
    deal_name: str


class DiscoveryResultResponse(BaseModel):
    """Response containing file discovery results with filtering."""

    files_accepted: int
    files_skipped: int
    total_scanned: int
    folders_scanned: int
    skipped_files: list[SkippedFileInfo] = Field(
        default_factory=list,
        description="Details of skipped files (limited to first 100)",
    )
    skip_reasons_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count of files skipped by each reason",
    )
