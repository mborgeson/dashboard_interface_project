"""
ActivityLog schemas for API request/response validation.

Provides Pydantic models for the UUID-based ActivityLog system.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from .base import BaseSchema


class ActivityAction(StrEnum):
    """Types of actions that can be logged for deals."""

    CREATED = "created"
    UPDATED = "updated"
    STAGE_CHANGED = "stage_changed"
    DOCUMENT_ADDED = "document_added"
    DOCUMENT_REMOVED = "document_removed"
    NOTE_ADDED = "note_added"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    PRICE_CHANGED = "price_changed"
    VIEWED = "viewed"


class ActivityLogCreate(BaseSchema):
    """Schema for creating an activity log entry."""

    action: ActivityAction
    description: str = Field(..., min_length=1, max_length=2000)
    metadata: dict[str, Any] | None = Field(default=None, alias="meta")


class ActivityLogResponse(BaseSchema):
    """Schema for activity log response."""

    id: UUID
    deal_id: int
    user_id: str | None = None
    action: ActivityAction
    description: str
    # Use 'meta' from model but expose as 'metadata' in API
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="meta")
    created_at: datetime


class ActivityLogListResponse(BaseSchema):
    """Paginated list of activity logs."""

    items: list[ActivityLogResponse]
    total: int
    page: int = 1
    page_size: int = 50
