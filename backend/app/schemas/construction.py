"""
Construction pipeline schemas for API request/response validation.

Extracted from backend/app/api/v1/endpoints/construction_pipeline.py
to follow the project convention of schemas in app/schemas/.
"""

from datetime import date
from typing import Any

from .base import BaseSchema


class ProjectRecord(BaseSchema):
    """A single construction project record."""

    id: int
    project_name: str | None = None
    project_address: str | None = None
    city: str | None = None
    submarket_cluster: str | None = None
    pipeline_status: str | None = None
    primary_classification: str | None = None
    number_of_units: int | None = None
    number_of_stories: int | None = None
    year_built: int | None = None
    developer_name: str | None = None
    owner_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    building_sf: float | None = None
    avg_unit_sf: float | None = None
    star_rating: str | None = None
    rent_type: str | None = None
    vacancy_pct: float | None = None
    estimated_delivery_date: date | None = None
    construction_begin: str | None = None
    for_sale_price: float | None = None
    source_type: str | None = None


class PaginatedProjectsResponse(BaseSchema):
    """Paginated list of construction projects."""

    data: list[ProjectRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConstructionFilterOptionsResponse(BaseSchema):
    """Available filter values for construction pipeline dropdowns."""

    submarkets: list[str]
    cities: list[str]
    statuses: list[str]
    classifications: list[str]
    rent_types: list[str]


class PipelineSummaryItem(BaseSchema):
    """Summary of projects by pipeline status."""

    status: str
    project_count: int
    total_units: int


class PipelineFunnelItem(BaseSchema):
    """Funnel chart data point with cumulative units."""

    status: str
    project_count: int
    total_units: int
    cumulative_units: int


class PermitTrendPoint(BaseSchema):
    """Permit trend time-series data point."""

    period: str
    source: str
    series_id: str
    value: float


class EmploymentPoint(BaseSchema):
    """Employment time-series data point."""

    period: str
    series_id: str
    value: float


class PermitVelocityPoint(BaseSchema):
    """Permit velocity data point."""

    source: str
    period: str
    count: int
    total_value: float


class SubmarketPipelineItem(BaseSchema):
    """Pipeline breakdown by submarket."""

    submarket: str
    total_projects: int
    total_units: int
    proposed: int
    under_construction: int
    delivered: int


class ClassificationBreakdownItem(BaseSchema):
    """Pipeline breakdown by classification."""

    classification: str
    project_count: int
    total_units: int


class DeliveryTimelineItem(BaseSchema):
    """Delivery timeline data point by quarter."""

    quarter: str  # e.g. "Q1 2026"
    total_units: int
    project_count: int


class ConstructionDataQualityReport(BaseSchema):
    """Data quality report for construction pipeline."""

    total_projects: int
    projects_by_source: dict[str, int]
    source_logs: list[dict[str, Any]]
    null_rates: dict[str, float]
    permit_data_count: int
    employment_data_count: int


class ConstructionImportResponse(BaseSchema):
    """Response from construction data import."""

    success: bool
    message: str
    rows_imported: int = 0
    rows_updated: int = 0


class ConstructionImportStatusResponse(BaseSchema):
    """Status of construction data imports."""

    unimported_files: list[str]
    last_imported_file: str | None = None
    last_import_date: str | None = None
    total_projects: int = 0


class FetchAllResponse(BaseSchema):
    """Response from fetch-all data sources operation."""

    success: bool
    message: str
    results: dict[str, Any] = {}


class BackfillResponse(BaseSchema):
    """Response from data backfill operation."""

    success: bool
    message: str
    rows_updated: int = 0
