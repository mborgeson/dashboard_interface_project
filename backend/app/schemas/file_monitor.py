"""
Pydantic schemas for file monitoring API endpoints.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FileChangeInfo(BaseModel):
    """Information about a detected file change."""

    file_path: str = Field(description="Full SharePoint path to the file")
    file_name: str = Field(description="File name")
    change_type: Literal["added", "modified", "deleted"] = Field(
        description="Type of change detected"
    )
    deal_name: str = Field(description="Name of the deal folder")
    old_modified_date: datetime | None = Field(
        default=None, description="Previous modification date (for modified files)"
    )
    new_modified_date: datetime | None = Field(
        default=None, description="New modification date"
    )
    old_size_bytes: int | None = Field(
        default=None, description="Previous file size (for modified files)"
    )
    new_size_bytes: int | None = Field(
        default=None, description="New file size"
    )
    detected_at: datetime = Field(description="When the change was detected")


class MonitoredFileInfo(BaseModel):
    """Information about a monitored file."""

    id: UUID
    file_path: str
    file_name: str
    deal_name: str
    size_bytes: int
    modified_date: datetime
    first_seen: datetime
    last_checked: datetime
    last_extracted: datetime | None = None
    is_active: bool
    extraction_pending: bool
    deal_stage: str | None = None

    class Config:
        from_attributes = True


class MonitorStatusResponse(BaseModel):
    """Status of the file monitoring system."""

    enabled: bool = Field(description="Whether file monitoring is enabled")
    interval_minutes: int = Field(description="Monitoring check interval in minutes")
    auto_extract: bool = Field(
        description="Whether extraction triggers automatically on changes"
    )
    last_check: datetime | None = Field(
        default=None, description="When the last check was performed"
    )
    next_check: datetime | None = Field(
        default=None, description="When the next check is scheduled"
    )
    total_monitored_files: int = Field(description="Total files being monitored")
    files_pending_extraction: int = Field(
        description="Files with pending extraction"
    )
    is_checking: bool = Field(
        default=False, description="Whether a check is currently in progress"
    )


class MonitorCheckResponse(BaseModel):
    """Response from a manual monitoring check."""

    changes_detected: int = Field(description="Number of changes detected")
    files_added: int = Field(description="Number of new files detected")
    files_modified: int = Field(description="Number of modified files")
    files_deleted: int = Field(description="Number of deleted files")
    extraction_triggered: bool = Field(
        description="Whether extraction was triggered"
    )
    extraction_run_id: UUID | None = Field(
        default=None, description="ID of triggered extraction run"
    )
    changes: list[FileChangeInfo] = Field(
        default_factory=list, description="Details of detected changes"
    )
    check_duration_seconds: float = Field(
        description="How long the check took"
    )


class RecentChangesResponse(BaseModel):
    """Response containing recent file changes."""

    changes: list[FileChangeInfo]
    total: int
    has_more: bool = Field(
        default=False, description="Whether there are more changes to fetch"
    )


class MonitoredFilesResponse(BaseModel):
    """Response containing monitored files list."""

    files: list[MonitoredFileInfo]
    total: int
    pending_extraction: int


class MonitorConfigRequest(BaseModel):
    """Request to update monitoring configuration."""

    enabled: bool | None = Field(
        default=None, description="Enable or disable monitoring"
    )
    interval_minutes: int | None = Field(
        default=None,
        ge=5,
        le=1440,
        description="Check interval in minutes (5-1440)"
    )
    auto_extract: bool | None = Field(
        default=None, description="Auto-trigger extraction on changes"
    )


class TriggerExtractionRequest(BaseModel):
    """Request to trigger extraction for specific files."""

    file_paths: list[str] | None = Field(
        default=None,
        description="Specific file paths to extract. If None, extracts all pending."
    )
    force: bool = Field(
        default=False,
        description="Force extraction even if files haven't changed"
    )
