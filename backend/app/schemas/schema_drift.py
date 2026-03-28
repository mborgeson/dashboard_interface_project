"""
Pydantic schemas for Schema Drift Detection API endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SchemaDriftAlertResponse(BaseModel):
    """Response schema for a single drift alert."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_name: str
    file_path: str
    similarity_score: float
    severity: str
    changed_sheets: list[str] | None = None
    missing_sheets: list[str] | None = None
    new_sheets: list[str] | None = None
    details: dict | None = None
    resolved: bool
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SchemaDriftAlertListResponse(BaseModel):
    """Response schema for listing drift alerts."""

    alerts: list[SchemaDriftAlertResponse]
    total: int
