"""
Pydantic schemas for the dead-letter (quarantine) API endpoints.

Provides request/response schemas for:
- Listing quarantined files
- Retrying quarantined files
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeadLetterFileResponse(BaseModel):
    """Response schema for a single quarantined file."""

    id: UUID = Field(description="Monitored file ID")
    file_path: str = Field(description="Full path to the file")
    file_name: str = Field(description="File name")
    deal_name: str = Field(description="Associated deal name")
    consecutive_failures: int = Field(description="Number of consecutive failures")
    last_failure_at: datetime | None = Field(
        default=None, description="When the last failure occurred"
    )
    last_failure_reason: str | None = Field(
        default=None, description="Reason for the last failure"
    )
    quarantined_at: datetime | None = Field(
        default=None, description="When the file was quarantined"
    )
    is_active: bool = Field(description="Whether the file is still active")
    deal_stage: str | None = Field(default=None, description="Current deal stage")

    model_config = ConfigDict(from_attributes=True)


class DeadLetterListResponse(BaseModel):
    """Paginated list of quarantined files."""

    items: list[DeadLetterFileResponse] = Field(description="List of quarantined files")
    total: int = Field(description="Total number of quarantined files")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Maximum records per page")
    has_more: bool = Field(description="Whether more records exist")


class DeadLetterRetryResponse(BaseModel):
    """Response from retrying a quarantined file."""

    id: UUID = Field(description="Monitored file ID")
    file_name: str = Field(description="File name")
    deal_name: str = Field(description="Associated deal name")
    message: str = Field(description="Status message")
    extraction_pending: bool = Field(description="Whether extraction is now pending")
