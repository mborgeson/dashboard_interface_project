"""
Reporting schemas for API request/response validation.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import BaseSchema


class ReportCategorySchema(StrEnum):
    """Report template categories."""

    EXECUTIVE = "executive"
    FINANCIAL = "financial"
    MARKET = "market"
    PORTFOLIO = "portfolio"
    CUSTOM = "custom"


class ReportFormatSchema(StrEnum):
    """Report export formats."""

    PDF = "pdf"
    EXCEL = "excel"
    PPTX = "pptx"


class ReportStatusSchema(StrEnum):
    """Queued report status."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleFrequencySchema(StrEnum):
    """Distribution schedule frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


# ==================== Report Template Schemas ====================


class ReportTemplateBase(BaseSchema):
    """Base schema for report template."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, description="Template description")
    category: ReportCategorySchema = Field(
        ReportCategorySchema.CUSTOM,
        description="Template category",
    )
    sections: list[str] = Field(default_factory=list, description="Report sections")
    export_formats: list[ReportFormatSchema] = Field(
        default_factory=lambda: [ReportFormatSchema.PDF],
        description="Available export formats",
    )
    is_default: bool = Field(False, description="Is this a default system template")


class ReportTemplateCreate(ReportTemplateBase):
    """Schema for creating a report template."""

    created_by: str = Field("System", description="User who created the template")
    config: dict | None = Field(None, description="Custom widget/layout configuration")


class ReportTemplateUpdate(BaseSchema):
    """Schema for updating a report template."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: ReportCategorySchema | None = None
    sections: list[str] | None = None
    export_formats: list[ReportFormatSchema] | None = None
    is_default: bool | None = None
    config: dict | None = None


class ReportTemplateResponse(ReportTemplateBase):
    """Response schema for report template."""

    id: int
    created_by: str
    config: dict | None = None
    created_at: datetime
    updated_at: datetime


class ReportTemplateListResponse(BaseSchema):
    """Response schema for list of report templates."""

    items: list[ReportTemplateResponse]
    total: int
    page: int
    page_size: int


# ==================== Queued Report Schemas ====================


class QueuedReportBase(BaseSchema):
    """Base schema for queued report."""

    name: str = Field(..., min_length=1, max_length=255, description="Report name")
    template_id: int = Field(..., description="Template ID")
    format: ReportFormatSchema = Field(
        ReportFormatSchema.PDF, description="Export format"
    )
    requested_by: str = Field(..., description="User who requested the report")


class QueuedReportCreate(QueuedReportBase):
    """Schema for creating a queued report."""

    pass


class QueuedReportResponse(QueuedReportBase):
    """Response schema for queued report."""

    id: int
    template_name: str | None = Field(None, description="Template name")
    status: ReportStatusSchema
    progress: int = Field(..., ge=0, le=100, description="Generation progress 0-100")
    requested_at: datetime
    completed_at: datetime | None = None
    file_size: str | None = None
    download_url: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class QueuedReportListResponse(BaseSchema):
    """Response schema for list of queued reports."""

    items: list[QueuedReportResponse]
    total: int
    page: int
    page_size: int


# ==================== Distribution Schedule Schemas ====================


class DistributionScheduleBase(BaseSchema):
    """Base schema for distribution schedule."""

    name: str = Field(..., min_length=1, max_length=255, description="Schedule name")
    template_id: int = Field(..., description="Template ID")
    recipients: list[str] = Field(..., min_length=1, description="Email recipients")
    frequency: ScheduleFrequencySchema = Field(
        ..., description="Distribution frequency"
    )
    day_of_week: int | None = Field(
        None, ge=0, le=6, description="Day of week (0=Mon, 6=Sun)"
    )
    day_of_month: int | None = Field(
        None, ge=1, le=31, description="Day of month (1-31)"
    )
    time: str = Field(
        ...,
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
        description="Time in HH:MM format",
    )
    format: ReportFormatSchema = Field(
        ReportFormatSchema.PDF, description="Export format"
    )
    is_active: bool = Field(True, description="Is schedule active")


class DistributionScheduleCreate(DistributionScheduleBase):
    """Schema for creating a distribution schedule."""

    next_scheduled: datetime = Field(..., description="Next scheduled run time")


class DistributionScheduleUpdate(BaseSchema):
    """Schema for updating a distribution schedule."""

    name: str | None = Field(None, min_length=1, max_length=255)
    recipients: list[str] | None = None
    frequency: ScheduleFrequencySchema | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    time: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    format: ReportFormatSchema | None = None
    is_active: bool | None = None
    next_scheduled: datetime | None = None


class DistributionScheduleResponse(DistributionScheduleBase):
    """Response schema for distribution schedule."""

    id: int
    template_name: str | None = Field(None, description="Template name")
    last_sent: datetime | None = None
    next_scheduled: datetime
    created_at: datetime
    updated_at: datetime


class DistributionScheduleListResponse(BaseSchema):
    """Response schema for list of distribution schedules."""

    items: list[DistributionScheduleResponse]
    total: int


# ==================== Report Generation Schemas ====================


class GenerateReportRequest(BaseSchema):
    """Request schema for generating a report."""

    template_id: int = Field(..., description="Template ID to use")
    name: str = Field(..., min_length=1, max_length=255, description="Report name")
    format: ReportFormatSchema = Field(
        ReportFormatSchema.PDF, description="Export format"
    )
    parameters: dict | None = Field(None, description="Additional report parameters")


class GenerateReportResponse(BaseSchema):
    """Response schema for report generation request."""

    queued_report_id: int
    status: ReportStatusSchema
    message: str


# ==================== Report Widget Schemas ====================


class ReportWidgetSchema(BaseSchema):
    """Schema for report widget definition."""

    id: str
    type: str = Field(
        ..., description="Widget type: chart, table, metric, text, image, map"
    )
    name: str
    description: str
    category: str
    icon: str
    default_width: int = Field(..., ge=1, le=12, description="Grid width units")
    default_height: int = Field(..., ge=1, description="Grid height units")
    configurable: bool = True


class ReportWidgetListResponse(BaseSchema):
    """Response schema for list of report widgets."""

    widgets: list[ReportWidgetSchema]
    total: int


# ==================== Report Settings Schemas ====================


class ReportSettingsSchema(BaseSchema):
    """Schema for report settings."""

    company_name: str
    company_logo: str | None = None
    primary_color: str
    secondary_color: str
    default_font: str
    default_page_size: str = Field(..., pattern="^(letter|a4|legal)$")
    default_orientation: str = Field(..., pattern="^(portrait|landscape)$")
    include_page_numbers: bool = True
    include_table_of_contents: bool = True
    include_timestamp: bool = True
    footer_text: str
    header_text: str
    watermark_text: str | None = None


class ReportSettingsUpdate(BaseSchema):
    """Schema for updating report settings."""

    company_name: str | None = None
    company_logo: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    default_font: str | None = None
    default_page_size: str | None = Field(None, pattern="^(letter|a4|legal)$")
    default_orientation: str | None = Field(None, pattern="^(portrait|landscape)$")
    include_page_numbers: bool | None = None
    include_table_of_contents: bool | None = None
    include_timestamp: bool | None = None
    footer_text: str | None = None
    header_text: str | None = None
    watermark_text: str | None = None
