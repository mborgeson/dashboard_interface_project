"""
Sales analysis schemas for API request/response validation.

Extracted from backend/app/api/v1/endpoints/sales_analysis.py
to follow the project convention of schemas in app/schemas/.
"""

from datetime import date

from .base import BaseSchema


class SalesRecord(BaseSchema):
    """A single sales transaction record."""

    id: int
    property_name: str | None = None
    property_address: str | None = None
    property_city: str | None = None
    submarket_cluster: str | None = None
    star_rating: str | None = None
    year_built: int | None = None
    number_of_units: int | None = None
    avg_unit_sf: float | None = None
    sale_date: date | None = None
    sale_price: float | None = None
    price_per_unit: float | None = None
    buyer_true_company: str | None = None
    seller_true_company: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    nrsf: float | None = None
    price_per_nrsf: float | None = None


class PaginatedSalesResponse(BaseSchema):
    """Paginated list of sales transactions."""

    data: list[SalesRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class TimeSeriesPoint(BaseSchema):
    """Sales volume time-series data point."""

    period: str
    count: int
    total_volume: float
    avg_price_per_unit: float | None = None


class SubmarketComparison(BaseSchema):
    """Submarket-level sales comparison for a given year."""

    submarket: str
    year: int
    avg_price_per_unit: float | None = None
    sales_count: int
    total_volume: float


class BuyerActivity(BaseSchema):
    """Buyer activity summary across transactions."""

    buyer: str
    transaction_count: int
    total_volume: float
    submarkets: list[str]
    first_purchase: date | None = None
    last_purchase: date | None = None


class DistributionBucket(BaseSchema):
    """Distribution histogram bucket."""

    label: str
    count: int
    avg_price_per_unit: float | None = None


class SalesDataQualityReport(BaseSchema):
    """Data quality report for sales data."""

    total_records: int
    records_by_file: dict[str, int]
    null_rates: dict[str, float]
    flagged_outliers: dict[str, int]


class SalesImportResponse(BaseSchema):
    """Response from sales data import."""

    success: bool
    message: str
    rows_imported: int = 0
    rows_updated: int = 0


class SalesImportStatusResponse(BaseSchema):
    """Status of sales data imports."""

    unimported_files: list[str]
    last_imported_file: str | None = None
    last_import_date: str | None = None


class ReminderStatusResponse(BaseSchema):
    """Sales data import reminder status."""

    show_reminder: bool
    last_imported_file_name: str | None = None
    last_imported_file_date: str | None = None


class SalesFilterOptionsResponse(BaseSchema):
    """Available filter values for sales analysis dropdowns."""

    submarkets: list[str]
