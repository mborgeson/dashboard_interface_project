"""
Reporting endpoints for report templates, queued reports, and distribution schedules.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_report_template import (
    distribution_schedule as schedule_crud,
)
from app.crud.crud_report_template import (
    queued_report as queued_crud,
)
from app.crud.crud_report_template import (
    report_template as template_crud,
)
from app.db.session import get_db
from app.models.report_settings import ReportSettings
from app.schemas.reporting import (
    DistributionScheduleCreate,
    DistributionScheduleListResponse,
    DistributionScheduleResponse,
    DistributionScheduleUpdate,
    GenerateReportRequest,
    GenerateReportResponse,
    QueuedReportListResponse,
    QueuedReportResponse,
    ReportSettingsSchema,
    ReportSettingsUpdate,
    ReportStatusSchema,
    ReportTemplateCreate,
    ReportTemplateListResponse,
    ReportTemplateResponse,
    ReportTemplateUpdate,
    ReportWidgetListResponse,
    ReportWidgetSchema,
)

router = APIRouter()


# ==================== Report Template Endpoints ====================


@router.get("/templates", response_model=ReportTemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    is_default: bool | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all report templates with optional filtering.

    Supports filtering by:
    - category: executive, financial, market, portfolio, custom
    - is_default: Show only default system templates
    - search: Search by name or description
    """
    skip = (page - 1) * page_size

    items = await template_crud.get_filtered(
        db,
        skip=skip,
        limit=page_size,
        category=category,
        is_default=is_default,
        search=search,
    )

    total = await template_crud.count_filtered(
        db,
        category=category,
        is_default=is_default,
        search=search,
    )

    return ReportTemplateListResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report template by ID."""
    template = await template_crud.get(db, template_id)

    if not template or template.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )

    return template


@router.post(
    "/templates",
    response_model=ReportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    template_data: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new report template."""
    new_template = await template_crud.create(db, obj_in=template_data)

    logger.info(f"Created report template: {new_template.name} (ID: {new_template.id})")

    return new_template


@router.put("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_template(
    template_id: int,
    template_data: ReportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing report template."""
    existing = await template_crud.get(db, template_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )

    updated_template = await template_crud.update(
        db, db_obj=existing, obj_in=template_data
    )

    logger.info(f"Updated report template: {template_id}")

    return updated_template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a report template (soft delete)."""
    existing = await template_crud.get(db, template_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )

    existing.soft_delete()
    db.add(existing)
    await db.commit()

    logger.info(f"Deleted report template: {template_id}")
    return None


# ==================== Report Generation Endpoints ====================


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new report from a template.

    This queues the report for generation and returns immediately.
    Use the queued report ID to check generation status.
    """
    # Verify template exists
    template = await template_crud.get(db, request.template_id)
    if not template or template.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {request.template_id} not found",
        )

    # Create queued report
    from app.schemas.reporting import QueuedReportCreate

    queued_data = QueuedReportCreate(
        name=request.name,
        template_id=request.template_id,
        format=request.format,
        requested_by="current_user",  # Would come from auth in production
    )

    queued = await queued_crud.create_with_timestamp(db, obj_in=queued_data)

    logger.info(f"Queued report generation: {queued.name} (ID: {queued.id})")

    return GenerateReportResponse(
        queued_report_id=queued.id,
        status=ReportStatusSchema.PENDING,
        message=f"Report '{request.name}' queued for generation",
    )


@router.get("/queue", response_model=QueuedReportListResponse)
async def list_queued_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    template_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List queued reports with optional filtering.

    Supports filtering by:
    - status: pending, generating, completed, failed
    - template_id: Filter to specific template
    """
    skip = (page - 1) * page_size

    items = await queued_crud.get_filtered(
        db,
        skip=skip,
        limit=page_size,
        status=status,
        template_id=template_id,
    )

    total = await queued_crud.count_filtered(
        db,
        status=status,
        template_id=template_id,
    )

    # Enrich with template names
    enriched_items = []
    for item in items:
        template = await template_crud.get(db, item.template_id)
        item_dict = {
            "id": item.id,
            "name": item.name,
            "template_id": item.template_id,
            "template_name": template.name if template else None,
            "format": item.format,
            "requested_by": item.requested_by,
            "status": item.status,
            "progress": item.progress,
            "requested_at": item.requested_at,
            "completed_at": item.completed_at,
            "file_size": item.file_size,
            "download_url": item.download_url,
            "error": item.error,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        enriched_items.append(QueuedReportResponse(**item_dict))  # type: ignore[arg-type]

    return QueuedReportListResponse(
        items=enriched_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/queue/{report_id}", response_model=QueuedReportResponse)
async def get_queued_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific queued report by ID."""
    report = await queued_crud.get(db, report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queued report {report_id} not found",
        )

    template = await template_crud.get(db, report.template_id)

    return QueuedReportResponse(
        id=report.id,
        name=report.name,
        template_id=report.template_id,
        template_name=template.name if template else None,
        format=report.format,  # type: ignore[arg-type]
        requested_by=report.requested_by,
        status=report.status,  # type: ignore[arg-type]
        progress=report.progress,
        requested_at=report.requested_at,
        completed_at=report.completed_at,
        file_size=report.file_size,
        download_url=report.download_url,
        error=report.error,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ==================== Distribution Schedule Endpoints ====================


@router.get("/schedules", response_model=DistributionScheduleListResponse)
async def list_schedules(
    active_only: bool = Query(False, description="Show only active schedules"),
    template_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List distribution schedules.

    Supports filtering by:
    - active_only: Show only active schedules
    - template_id: Filter to specific template
    """
    if template_id:
        items = await schedule_crud.get_by_template(db, template_id)
    elif active_only:
        items = await schedule_crud.get_active(db)
    else:
        items = await schedule_crud.get_multi(db, skip=0, limit=100)

    # Enrich with template names
    enriched_items = []
    for item in items:
        if item.is_deleted:
            continue
        template = await template_crud.get(db, item.template_id)
        item_dict = {
            "id": item.id,
            "name": item.name,
            "template_id": item.template_id,
            "template_name": template.name if template else None,
            "recipients": item.recipients,
            "frequency": item.frequency,
            "day_of_week": item.day_of_week,
            "day_of_month": item.day_of_month,
            "time": item.time,
            "format": item.format,
            "is_active": item.is_active,
            "last_sent": item.last_sent,
            "next_scheduled": item.next_scheduled,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        enriched_items.append(DistributionScheduleResponse(**item_dict))  # type: ignore[arg-type]

    return DistributionScheduleListResponse(
        items=enriched_items,
        total=len(enriched_items),
    )


@router.post(
    "/schedules",
    response_model=DistributionScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    schedule_data: DistributionScheduleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new distribution schedule."""
    # Verify template exists
    template = await template_crud.get(db, schedule_data.template_id)
    if not template or template.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {schedule_data.template_id} not found",
        )

    new_schedule = await schedule_crud.create(db, obj_in=schedule_data)

    logger.info(
        f"Created distribution schedule: {new_schedule.name} (ID: {new_schedule.id})"
    )

    return DistributionScheduleResponse(
        id=new_schedule.id,
        name=new_schedule.name,
        template_id=new_schedule.template_id,
        template_name=template.name,
        recipients=new_schedule.recipients,
        frequency=new_schedule.frequency,  # type: ignore[arg-type]
        day_of_week=new_schedule.day_of_week,
        day_of_month=new_schedule.day_of_month,
        time=new_schedule.time,
        format=new_schedule.format,  # type: ignore[arg-type]
        is_active=new_schedule.is_active,
        last_sent=new_schedule.last_sent,
        next_scheduled=new_schedule.next_scheduled,
        created_at=new_schedule.created_at,
        updated_at=new_schedule.updated_at,
    )


@router.put("/schedules/{schedule_id}", response_model=DistributionScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: DistributionScheduleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing distribution schedule."""
    existing = await schedule_crud.get(db, schedule_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    updated_schedule = await schedule_crud.update(
        db, db_obj=existing, obj_in=schedule_data
    )
    template = await template_crud.get(db, updated_schedule.template_id)

    logger.info(f"Updated distribution schedule: {schedule_id}")

    return DistributionScheduleResponse(
        id=updated_schedule.id,
        name=updated_schedule.name,
        template_id=updated_schedule.template_id,
        template_name=template.name if template else None,
        recipients=updated_schedule.recipients,
        frequency=updated_schedule.frequency,  # type: ignore[arg-type]
        day_of_week=updated_schedule.day_of_week,
        day_of_month=updated_schedule.day_of_month,
        time=updated_schedule.time,
        format=updated_schedule.format,  # type: ignore[arg-type]
        is_active=updated_schedule.is_active,
        last_sent=updated_schedule.last_sent,
        next_scheduled=updated_schedule.next_scheduled,
        created_at=updated_schedule.created_at,
        updated_at=updated_schedule.updated_at,
    )


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a distribution schedule (soft delete)."""
    existing = await schedule_crud.get(db, schedule_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    existing.soft_delete()
    db.add(existing)
    await db.commit()

    logger.info(f"Deleted distribution schedule: {schedule_id}")
    return None


# ==================== Report Settings Endpoints ====================


@router.get("/settings", response_model=ReportSettingsSchema)
async def get_report_settings(
    db: AsyncSession = Depends(get_db),
):
    """Get the current report settings (singleton row)."""
    result = await db.execute(select(ReportSettings).where(ReportSettings.id == 1))
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report settings not found",
        )

    return settings


@router.put("/settings", response_model=ReportSettingsSchema)
async def update_report_settings(
    settings_data: ReportSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update report settings (partial update)."""
    result = await db.execute(select(ReportSettings).where(ReportSettings.id == 1))
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report settings not found",
        )

    update_data = settings_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.add(settings)
    await db.commit()
    await db.refresh(settings)

    logger.info(f"Updated report settings: {list(update_data.keys())}")

    return settings


# ==================== Widget Endpoints ====================


@router.get("/widgets", response_model=ReportWidgetListResponse)
async def list_widgets(
    widget_type: str | None = Query(
        None, description="Filter by type: chart, table, metric, etc."
    ),
):
    """
    List available report widgets for custom report building.

    Supports filtering by type: chart, table, metric, text, image, map
    """
    # Static widget definitions (from mock data pattern)
    all_widgets = [
        # Chart Widgets
        ReportWidgetSchema(
            id="widget-line-chart",
            type="chart",
            name="Line Chart",
            description="Time series data visualization",
            category="Charts",
            icon="LineChart",
            default_width=6,
            default_height=3,
            configurable=True,
        ),
        ReportWidgetSchema(
            id="widget-bar-chart",
            type="chart",
            name="Bar Chart",
            description="Categorical comparison chart",
            category="Charts",
            icon="BarChart",
            default_width=6,
            default_height=3,
            configurable=True,
        ),
        ReportWidgetSchema(
            id="widget-pie-chart",
            type="chart",
            name="Pie Chart",
            description="Distribution visualization",
            category="Charts",
            icon="PieChart",
            default_width=4,
            default_height=3,
            configurable=True,
        ),
        # Table Widgets
        ReportWidgetSchema(
            id="widget-data-table",
            type="table",
            name="Data Table",
            description="Tabular data display",
            category="Tables",
            icon="Table",
            default_width=12,
            default_height=4,
            configurable=True,
        ),
        ReportWidgetSchema(
            id="widget-summary-table",
            type="table",
            name="Summary Table",
            description="Condensed metrics table",
            category="Tables",
            icon="TableProperties",
            default_width=6,
            default_height=2,
            configurable=True,
        ),
        # Metric Widgets
        ReportWidgetSchema(
            id="widget-kpi-card",
            type="metric",
            name="KPI Card",
            description="Single metric with change indicator",
            category="Metrics",
            icon="TrendingUp",
            default_width=3,
            default_height=1,
            configurable=True,
        ),
        ReportWidgetSchema(
            id="widget-gauge",
            type="metric",
            name="Gauge Chart",
            description="Progress or threshold indicator",
            category="Metrics",
            icon="Gauge",
            default_width=3,
            default_height=2,
            configurable=True,
        ),
        # Text Widgets
        ReportWidgetSchema(
            id="widget-text-block",
            type="text",
            name="Text Block",
            description="Rich text content area",
            category="Content",
            icon="FileText",
            default_width=12,
            default_height=2,
            configurable=True,
        ),
        # Map Widgets
        ReportWidgetSchema(
            id="widget-property-map",
            type="map",
            name="Property Map",
            description="Geographic property visualization",
            category="Maps",
            icon="Map",
            default_width=6,
            default_height=4,
            configurable=True,
        ),
    ]

    # Filter by type if specified
    if widget_type:
        all_widgets = [w for w in all_widgets if w.type == widget_type]

    return ReportWidgetListResponse(
        widgets=all_widgets,
        total=len(all_widgets),
    )
