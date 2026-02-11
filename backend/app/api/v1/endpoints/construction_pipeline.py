"""
Construction Pipeline endpoints — paginated table, analytics, import management.

All endpoints use async sessions and the ConstructionProject model for CoStar
multifamily construction pipeline data. Permit/employment time-series use
ConstructionPermitData and ConstructionEmploymentData.
"""

import math
import os
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, get_sync_db
from app.models.construction import (
    ConstructionEmploymentData,
    ConstructionPermitData,
    ConstructionProject,
    ConstructionSourceLog,
)

router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────────────

CONSTRUCTION_DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "..",
    "data",
    "construction",
    "Phoenix",
)
CONSTRUCTION_DATA_DIR = os.path.normpath(CONSTRUCTION_DATA_DIR)


# ── Pydantic Response Schemas ─────────────────────────────────────────────────


class ProjectRecord(BaseModel):
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


class PaginatedProjectsResponse(BaseModel):
    data: list[ProjectRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class FilterOptionsResponse(BaseModel):
    submarkets: list[str]
    cities: list[str]
    statuses: list[str]
    classifications: list[str]
    rent_types: list[str]


class PipelineSummaryItem(BaseModel):
    status: str
    project_count: int
    total_units: int


class PipelineFunnelItem(BaseModel):
    status: str
    project_count: int
    total_units: int
    cumulative_units: int


class PermitTrendPoint(BaseModel):
    period: str
    source: str
    series_id: str
    value: float


class EmploymentPoint(BaseModel):
    period: str
    series_id: str
    value: float


class PermitVelocityPoint(BaseModel):
    source: str
    period: str
    count: int
    total_value: float


class SubmarketPipelineItem(BaseModel):
    submarket: str
    total_projects: int
    total_units: int
    proposed: int
    under_construction: int
    delivered: int


class ClassificationBreakdownItem(BaseModel):
    classification: str
    project_count: int
    total_units: int


class DeliveryTimelineItem(BaseModel):
    quarter: str  # e.g. "Q1 2026"
    total_units: int
    project_count: int


class DataQualityReport(BaseModel):
    total_projects: int
    projects_by_source: dict[str, int]
    source_logs: list[dict[str, Any]]
    null_rates: dict[str, float]
    permit_data_count: int
    employment_data_count: int


class ImportResponse(BaseModel):
    success: bool
    message: str
    rows_imported: int = 0
    rows_updated: int = 0


class ImportStatusResponse(BaseModel):
    unimported_files: list[str]
    last_imported_file: str | None = None
    last_import_date: str | None = None
    total_projects: int = 0


# ── Shared filter helper ──────────────────────────────────────────────────────


def _apply_filters(
    stmt,
    search: str | None = None,
    statuses: str | None = None,
    classifications: str | None = None,
    submarkets: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_year_built: int | None = None,
    max_year_built: int | None = None,
    rent_type: str | None = None,
):
    """Apply common filter criteria to a SQLAlchemy select statement."""
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            ConstructionProject.project_name.ilike(pattern)
            | ConstructionProject.project_address.ilike(pattern)
            | ConstructionProject.city.ilike(pattern)
            | ConstructionProject.developer_name.ilike(pattern)
            | ConstructionProject.owner_name.ilike(pattern)
            | ConstructionProject.submarket_cluster.ilike(pattern)
        )
    if statuses:
        status_list = [s.strip() for s in statuses.split(",") if s.strip()]
        if status_list:
            stmt = stmt.where(ConstructionProject.pipeline_status.in_(status_list))
    if classifications:
        cls_list = [c.strip() for c in classifications.split(",") if c.strip()]
        if cls_list:
            stmt = stmt.where(ConstructionProject.primary_classification.in_(cls_list))
    if submarkets:
        sub_list = [s.strip() for s in submarkets.split(",") if s.strip()]
        if sub_list:
            stmt = stmt.where(ConstructionProject.submarket_cluster.in_(sub_list))
    if cities:
        city_list = [c.strip() for c in cities.split(",") if c.strip()]
        if city_list:
            stmt = stmt.where(ConstructionProject.city.in_(city_list))
    if min_units is not None:
        stmt = stmt.where(ConstructionProject.number_of_units >= min_units)
    if max_units is not None:
        stmt = stmt.where(ConstructionProject.number_of_units <= max_units)
    if min_year_built is not None:
        stmt = stmt.where(ConstructionProject.year_built >= min_year_built)
    if max_year_built is not None:
        stmt = stmt.where(ConstructionProject.year_built <= max_year_built)
    if rent_type:
        stmt = stmt.where(ConstructionProject.rent_type == rent_type)
    return stmt


# ── 0. GET /filter-options ────────────────────────────────────────────────────


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def filter_options(db: AsyncSession = Depends(get_db)):
    """Return distinct values for filter dropdowns."""
    submarkets = [
        row[0]
        for row in (
            await db.execute(
                select(ConstructionProject.submarket_cluster)
                .where(
                    ConstructionProject.submarket_cluster.isnot(None),
                    ConstructionProject.submarket_cluster != "",
                )
                .distinct()
                .order_by(ConstructionProject.submarket_cluster)
            )
        ).all()
    ]
    cities = [
        row[0]
        for row in (
            await db.execute(
                select(ConstructionProject.city)
                .where(
                    ConstructionProject.city.isnot(None),
                    ConstructionProject.city != "",
                )
                .distinct()
                .order_by(ConstructionProject.city)
            )
        ).all()
    ]
    statuses = [
        row[0]
        for row in (
            await db.execute(
                select(ConstructionProject.pipeline_status)
                .where(ConstructionProject.pipeline_status.isnot(None))
                .distinct()
                .order_by(ConstructionProject.pipeline_status)
            )
        ).all()
    ]
    classifications = [
        row[0]
        for row in (
            await db.execute(
                select(ConstructionProject.primary_classification)
                .where(ConstructionProject.primary_classification.isnot(None))
                .distinct()
                .order_by(ConstructionProject.primary_classification)
            )
        ).all()
    ]
    rent_types = [
        row[0]
        for row in (
            await db.execute(
                select(ConstructionProject.rent_type)
                .where(
                    ConstructionProject.rent_type.isnot(None),
                    ConstructionProject.rent_type != "",
                )
                .distinct()
                .order_by(ConstructionProject.rent_type)
            )
        ).all()
    ]
    return FilterOptionsResponse(
        submarkets=submarkets,
        cities=cities,
        statuses=statuses,
        classifications=classifications,
        rent_types=rent_types,
    )


# ── 1. GET / — Paginated table data ──────────────────────────────────────────

_SORTABLE_COLUMNS: dict[str, Any] = {
    "id": ConstructionProject.id,
    "project_name": ConstructionProject.project_name,
    "city": ConstructionProject.city,
    "submarket_cluster": ConstructionProject.submarket_cluster,
    "pipeline_status": ConstructionProject.pipeline_status,
    "primary_classification": ConstructionProject.primary_classification,
    "number_of_units": ConstructionProject.number_of_units,
    "number_of_stories": ConstructionProject.number_of_stories,
    "year_built": ConstructionProject.year_built,
    "developer_name": ConstructionProject.developer_name,
    "star_rating": ConstructionProject.star_rating,
    "estimated_delivery_date": ConstructionProject.estimated_delivery_date,
    "building_sf": ConstructionProject.building_sf,
}


@router.get("/", response_model=PaginatedProjectsResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("id"),
    sort_dir: str = Query("desc"),
    search: str | None = None,
    statuses: str | None = None,
    classifications: str | None = None,
    submarkets: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_year_built: int | None = None,
    max_year_built: int | None = None,
    rent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable, sortable list of construction projects."""

    # Count query
    count_stmt = select(func.count()).select_from(ConstructionProject)
    count_stmt = _apply_filters(
        count_stmt,
        search,
        statuses,
        classifications,
        submarkets,
        cities,
        min_units,
        max_units,
        min_year_built,
        max_year_built,
        rent_type,
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Data query
    data_stmt = select(ConstructionProject)
    data_stmt = _apply_filters(
        data_stmt,
        search,
        statuses,
        classifications,
        submarkets,
        cities,
        min_units,
        max_units,
        min_year_built,
        max_year_built,
        rent_type,
    )

    sort_col = _SORTABLE_COLUMNS.get(sort_by, ConstructionProject.id)
    if sort_dir.lower() == "asc":
        data_stmt = data_stmt.order_by(sort_col.asc().nulls_last())
    else:
        data_stmt = data_stmt.order_by(sort_col.desc().nulls_last())

    offset = (page - 1) * page_size
    data_stmt = data_stmt.offset(offset).limit(page_size)

    result = await db.execute(data_stmt)
    rows = result.scalars().all()

    records = [
        ProjectRecord(
            id=r.id,
            project_name=r.project_name,
            project_address=r.project_address,
            city=r.city,
            submarket_cluster=r.submarket_cluster,
            pipeline_status=r.pipeline_status,
            primary_classification=r.primary_classification,
            number_of_units=r.number_of_units,
            number_of_stories=r.number_of_stories,
            year_built=r.year_built,
            developer_name=r.developer_name,
            owner_name=r.owner_name,
            latitude=r.latitude,
            longitude=r.longitude,
            building_sf=r.building_sf,
            avg_unit_sf=r.avg_unit_sf,
            star_rating=r.star_rating,
            rent_type=r.rent_type,
            vacancy_pct=r.vacancy_pct,
            estimated_delivery_date=r.estimated_delivery_date,
            construction_begin=r.construction_begin,
            for_sale_price=r.for_sale_price,
            source_type=r.source_type,
        )
        for r in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedProjectsResponse(
        data=records,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ── 2. GET /analytics/pipeline-summary ────────────────────────────────────────


@router.get("/analytics/pipeline-summary", response_model=list[PipelineSummaryItem])
async def pipeline_summary(
    search: str | None = None,
    statuses: str | None = None,
    classifications: str | None = None,
    submarkets: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_year_built: int | None = None,
    max_year_built: int | None = None,
    rent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Project counts and unit totals by pipeline status."""
    stmt = (
        select(
            ConstructionProject.pipeline_status.label("status"),
            func.count().label("project_count"),
            func.coalesce(func.sum(ConstructionProject.number_of_units), 0).label(
                "total_units"
            ),
        )
        .group_by(ConstructionProject.pipeline_status)
        .order_by(ConstructionProject.pipeline_status)
    )
    stmt = _apply_filters(
        stmt,
        search,
        statuses,
        classifications,
        submarkets,
        cities,
        min_units,
        max_units,
        min_year_built,
        max_year_built,
        rent_type,
    )
    result = await db.execute(stmt)
    return [
        PipelineSummaryItem(
            status=str(r.status),
            project_count=r.project_count,
            total_units=int(r.total_units),
        )
        for r in result.all()
    ]


# ── 3. GET /analytics/pipeline-funnel ─────────────────────────────────────────

# Ordered pipeline stages for funnel display
_FUNNEL_ORDER = [
    "proposed",
    "final_planning",
    "permitted",
    "under_construction",
    "delivered",
]


@router.get("/analytics/pipeline-funnel", response_model=list[PipelineFunnelItem])
async def pipeline_funnel(
    search: str | None = None,
    classifications: str | None = None,
    submarkets: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    rent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Unit counts through each pipeline stage (funnel view)."""
    stmt = select(
        ConstructionProject.pipeline_status.label("status"),
        func.count().label("project_count"),
        func.coalesce(func.sum(ConstructionProject.number_of_units), 0).label(
            "total_units"
        ),
    ).group_by(ConstructionProject.pipeline_status)
    stmt = _apply_filters(
        stmt,
        search,
        None,  # Don't filter by status in funnel view
        classifications,
        submarkets,
        cities,
        min_units,
        max_units,
        None,
        None,
        rent_type,
    )
    result = await db.execute(stmt)
    status_data = {
        str(r.status): (r.project_count, int(r.total_units)) for r in result.all()
    }

    # Build funnel with cumulative units
    funnel = []
    cumulative = 0
    for status in _FUNNEL_ORDER:
        count, units = status_data.get(status, (0, 0))
        cumulative += units
        funnel.append(
            PipelineFunnelItem(
                status=status,
                project_count=count,
                total_units=units,
                cumulative_units=cumulative,
            )
        )
    return funnel


# ── 4. GET /analytics/permit-trends ───────────────────────────────────────────


@router.get("/analytics/permit-trends", response_model=list[PermitTrendPoint])
async def permit_trends(
    source: str | None = None,
    months: int = Query(24, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
):
    """Census BPS + FRED permit time-series data."""
    stmt = (
        select(
            ConstructionPermitData.period_date,
            ConstructionPermitData.source,
            ConstructionPermitData.series_id,
            ConstructionPermitData.value,
        )
        .order_by(ConstructionPermitData.period_date.desc())
        .limit(months * 10)  # Multiple series per month
    )
    if source:
        stmt = stmt.where(ConstructionPermitData.source == source)

    result = await db.execute(stmt)
    return [
        PermitTrendPoint(
            period=str(r.period_date),
            source=r.source,
            series_id=r.series_id,
            value=float(r.value),
        )
        for r in result.all()
    ]


# ── 5. GET /analytics/employment-overlay ──────────────────────────────────────


@router.get("/analytics/employment-overlay", response_model=list[EmploymentPoint])
async def employment_overlay(
    months: int = Query(24, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
):
    """BLS construction employment time-series for Phoenix MSA."""
    stmt = (
        select(
            ConstructionEmploymentData.period_date,
            ConstructionEmploymentData.series_id,
            ConstructionEmploymentData.value,
        )
        .order_by(ConstructionEmploymentData.period_date.desc())
        .limit(months * 5)  # Multiple series per month
    )
    result = await db.execute(stmt)
    return [
        EmploymentPoint(
            period=str(r.period_date),
            series_id=r.series_id,
            value=float(r.value),
        )
        for r in result.all()
    ]


# ── 6. GET /analytics/permit-velocity ─────────────────────────────────────────


@router.get("/analytics/permit-velocity", response_model=list[PermitVelocityPoint])
async def permit_velocity(
    months: int = Query(12, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
):
    """Municipal permit issuance rates (Mesa, Tempe, Gilbert)."""
    # Filter to municipal sources only
    municipal_sources = ["mesa_soda", "tempe_blds", "gilbert_arcgis"]
    stmt = (
        select(
            ConstructionPermitData.source.label("source"),
            ConstructionPermitData.period_date.label("period"),
            func.count().label("permit_count"),
            func.coalesce(func.sum(ConstructionPermitData.value), 0).label(
                "total_value"
            ),
        )
        .where(ConstructionPermitData.source.in_(municipal_sources))
        .group_by(
            ConstructionPermitData.source,
            ConstructionPermitData.period_date,
        )
        .order_by(ConstructionPermitData.period_date.desc())
        .limit(months * len(municipal_sources))
    )
    result = await db.execute(stmt)
    return [
        PermitVelocityPoint(
            source=r.source,
            period=str(r.period),
            count=r.permit_count,
            total_value=float(r.total_value),
        )
        for r in result.all()
    ]


# ── 7. GET /analytics/submarket-pipeline ──────────────────────────────────────


@router.get(
    "/analytics/submarket-pipeline",
    response_model=list[SubmarketPipelineItem],
)
async def submarket_pipeline(
    search: str | None = None,
    classifications: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    rent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Pipeline breakdown by submarket with status counts."""
    stmt = (
        select(
            ConstructionProject.submarket_cluster.label("submarket"),
            func.count().label("total_projects"),
            func.coalesce(func.sum(ConstructionProject.number_of_units), 0).label(
                "total_units"
            ),
            func.sum(
                case(
                    (ConstructionProject.pipeline_status == "proposed", 1),
                    else_=0,
                )
            ).label("proposed_raw"),
            func.sum(
                case(
                    (ConstructionProject.pipeline_status == "under_construction", 1),
                    else_=0,
                )
            ).label("uc_raw"),
            func.sum(
                case(
                    (ConstructionProject.pipeline_status == "delivered", 1),
                    else_=0,
                )
            ).label("delivered_raw"),
        )
        .where(
            ConstructionProject.submarket_cluster.isnot(None),
            ConstructionProject.submarket_cluster != "",
        )
        .group_by(ConstructionProject.submarket_cluster)
        .order_by(func.sum(ConstructionProject.number_of_units).desc().nulls_last())
    )
    stmt = _apply_filters(
        stmt,
        search,
        None,
        classifications,
        None,
        cities,
        min_units,
        max_units,
        None,
        None,
        rent_type,
    )
    result = await db.execute(stmt)
    return [
        SubmarketPipelineItem(
            submarket=r.submarket,
            total_projects=r.total_projects,
            total_units=int(r.total_units),
            proposed=int(r.proposed_raw or 0),
            under_construction=int(r.uc_raw or 0),
            delivered=int(r.delivered_raw or 0),
        )
        for r in result.all()
    ]


# ── 8. GET /analytics/classification-breakdown ────────────────────────────────


@router.get(
    "/analytics/classification-breakdown",
    response_model=list[ClassificationBreakdownItem],
)
async def classification_breakdown(
    search: str | None = None,
    statuses: str | None = None,
    submarkets: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    rent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Units by classification type."""
    stmt = (
        select(
            ConstructionProject.primary_classification.label("classification"),
            func.count().label("project_count"),
            func.coalesce(func.sum(ConstructionProject.number_of_units), 0).label(
                "total_units"
            ),
        )
        .group_by(ConstructionProject.primary_classification)
        .order_by(func.sum(ConstructionProject.number_of_units).desc().nulls_last())
    )
    stmt = _apply_filters(
        stmt,
        search,
        statuses,
        None,
        submarkets,
        cities,
        min_units,
        max_units,
        None,
        None,
        rent_type,
    )
    result = await db.execute(stmt)
    return [
        ClassificationBreakdownItem(
            classification=str(r.classification),
            project_count=r.project_count,
            total_units=int(r.total_units),
        )
        for r in result.all()
    ]


# ── 8b. GET /analytics/delivery-timeline ──────────────────────────────────────


@router.get(
    "/analytics/delivery-timeline",
    response_model=list[DeliveryTimelineItem],
)
async def delivery_timeline(
    search: str | None = None,
    statuses: str | None = None,
    classifications: str | None = None,
    submarkets: str | None = None,
    cities: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    rent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Delivery timeline: units by quarter over the next 3 years."""
    from dateutil.relativedelta import relativedelta

    today = date.today()
    horizon = today + relativedelta(years=3)

    stmt = select(
        ConstructionProject.estimated_delivery_date,
        ConstructionProject.number_of_units,
    ).where(
        ConstructionProject.estimated_delivery_date.isnot(None),
        ConstructionProject.estimated_delivery_date >= today,
        ConstructionProject.estimated_delivery_date <= horizon,
    )
    stmt = _apply_filters(
        stmt,
        search,
        statuses,
        classifications,
        submarkets,
        cities,
        min_units,
        max_units,
        None,
        None,
        rent_type,
    )
    result = await db.execute(stmt)

    # Bucket into quarters
    quarter_buckets: dict[str, dict] = {}
    for row in result.all():
        dt = row[0]
        units = row[1] or 0
        q = (dt.month - 1) // 3 + 1
        key = f"Q{q} {dt.year}"
        if key not in quarter_buckets:
            quarter_buckets[key] = {"total_units": 0, "project_count": 0}
        quarter_buckets[key]["total_units"] += units
        quarter_buckets[key]["project_count"] += 1

    # Build complete timeline with all quarters in range (even empty ones)
    items: list[DeliveryTimelineItem] = []
    cursor = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    while cursor <= horizon:
        q = (cursor.month - 1) // 3 + 1
        key = f"Q{q} {cursor.year}"
        bucket = quarter_buckets.get(key, {"total_units": 0, "project_count": 0})
        items.append(
            DeliveryTimelineItem(
                quarter=key,
                total_units=bucket["total_units"],
                project_count=bucket["project_count"],
            )
        )
        cursor += relativedelta(months=3)

    return items


# ── 9. GET /analytics/data-quality ────────────────────────────────────────────


@router.get("/analytics/data-quality", response_model=DataQualityReport)
async def data_quality(db: AsyncSession = Depends(get_db)):
    """Data quality overview: record counts, source freshness, null rates."""

    # Total projects
    total = (
        await db.execute(select(func.count()).select_from(ConstructionProject))
    ).scalar() or 0

    # Projects by source type
    source_stmt = (
        select(ConstructionProject.source_type, func.count())
        .group_by(ConstructionProject.source_type)
        .order_by(ConstructionProject.source_type)
    )
    source_rows = (await db.execute(source_stmt)).all()
    projects_by_source = {str(r[0] or "unknown"): r[1] for r in source_rows}

    # Recent source logs
    log_stmt = (
        select(ConstructionSourceLog)
        .order_by(ConstructionSourceLog.fetched_at.desc())
        .limit(10)
    )
    log_rows = (await db.execute(log_stmt)).scalars().all()
    source_logs = [
        {
            "source_name": log.source_name,
            "fetch_type": log.fetch_type,
            "fetched_at": str(log.fetched_at),
            "records_fetched": log.records_fetched,
            "records_inserted": log.records_inserted,
            "records_updated": log.records_updated,
            "success": log.success,
            "error_message": log.error_message,
        }
        for log in log_rows
    ]

    # Null rates for key fields
    null_rates: dict[str, float] = {}
    if total > 0:
        key_fields = {
            "project_name": ConstructionProject.project_name,
            "number_of_units": ConstructionProject.number_of_units,
            "pipeline_status": ConstructionProject.pipeline_status,
            "submarket_cluster": ConstructionProject.submarket_cluster,
            "developer_name": ConstructionProject.developer_name,
            "latitude": ConstructionProject.latitude,
            "year_built": ConstructionProject.year_built,
        }
        for field_name, col in key_fields.items():
            null_count = (
                await db.execute(
                    select(func.count())
                    .select_from(ConstructionProject)
                    .where(col.is_(None))
                )
            ).scalar() or 0
            null_rates[field_name] = round(null_count / total, 4)

    # Time-series data counts
    permit_count = (
        await db.execute(select(func.count()).select_from(ConstructionPermitData))
    ).scalar() or 0
    employment_count = (
        await db.execute(select(func.count()).select_from(ConstructionEmploymentData))
    ).scalar() or 0

    return DataQualityReport(
        total_projects=total,
        projects_by_source=projects_by_source,
        source_logs=source_logs,
        null_rates=null_rates,
        permit_data_count=permit_count,
        employment_data_count=employment_count,
    )


# ── 10. POST /import ─────────────────────────────────────────────────────────


@router.post("/import", response_model=ImportResponse)
async def trigger_import(db_sync=Depends(get_sync_db)):
    """Import any unimported CoStar construction Excel files."""
    from app.services.construction_import import (
        get_unimported_files,
        import_construction_file,
    )

    try:
        unimported = get_unimported_files(db_sync, CONSTRUCTION_DATA_DIR)
        if not unimported:
            return ImportResponse(
                success=True,
                message="No new files to import.",
                rows_imported=0,
                rows_updated=0,
            )

        total_imported = 0
        total_updated = 0
        for filepath in unimported:
            result = import_construction_file(db_sync, filepath)
            total_imported += result.rows_imported
            total_updated += result.rows_updated
            if result.errors:
                logger.warning(f"Import errors for {result.filename}: {result.errors}")

        return ImportResponse(
            success=True,
            message=f"Imported {len(unimported)} file(s).",
            rows_imported=total_imported,
            rows_updated=total_updated,
        )
    except Exception as e:
        logger.error(f"Construction import failed: {e}")
        return ImportResponse(success=False, message=str(e))


# ── 11. GET /import/status ────────────────────────────────────────────────────


@router.get("/import/status", response_model=ImportStatusResponse)
async def import_status(db_sync=Depends(get_sync_db)):
    """Check for unimported files and last import info."""
    from app.services.construction_import import get_unimported_files

    unimported = get_unimported_files(db_sync, CONSTRUCTION_DATA_DIR)
    unimported_names = [os.path.basename(f) for f in unimported]

    from sqlalchemy import select as sa_select

    # Most recent imported project
    last_row = db_sync.execute(
        sa_select(ConstructionProject.source_file, ConstructionProject.imported_at)
        .where(ConstructionProject.imported_at.isnot(None))
        .order_by(ConstructionProject.imported_at.desc())
        .limit(1)
    ).first()

    # Total project count
    total = (
        db_sync.execute(
            sa_select(func.count()).select_from(ConstructionProject)
        ).scalar()
        or 0
    )

    return ImportStatusResponse(
        unimported_files=unimported_names,
        last_imported_file=last_row[0] if last_row else None,
        last_import_date=str(last_row[1]) if last_row else None,
        total_projects=total,
    )
