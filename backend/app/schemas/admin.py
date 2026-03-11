"""
Admin schemas for audit log API responses.
"""

from typing import Any

from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    """Single audit log entry returned by the admin audit-log endpoint."""

    id: int
    timestamp: str | None = None
    user_id: int
    user_email: str
    action: str
    resource_type: str
    resource_id: str | None = None
    details: Any = None
    ip_address: str | None = None
    user_agent: str | None = None


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditLogEntry]
    total: int
    page: int
    per_page: int
    pages: int = Field(description="Total number of pages")
