"""
Pydantic schemas for Domain Validation API endpoints.
"""

from pydantic import BaseModel, ConfigDict


class DomainWarningItem(BaseModel):
    """Response schema for a single domain validation warning."""

    model_config = ConfigDict(from_attributes=True)

    field_name: str
    value: str | None = None
    property_name: str
    domain_warning: str
    source_file: str | None = None


class DomainWarningListResponse(BaseModel):
    """Paginated response for domain validation warnings."""

    warnings: list[DomainWarningItem]
    total: int
    limit: int
    offset: int
