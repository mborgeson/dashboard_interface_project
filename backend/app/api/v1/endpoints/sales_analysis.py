"""
Sales Analysis endpoints — paginated table, analytics, import, and reminder management.

All endpoints use async sessions and the SalesData model for CoStar multifamily
sales transaction data.
"""

import math
import os
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import Integer as SAInteger
from sqlalchemy import String as SAString
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, get_sync_db
from app.models.sales_data import SalesData

router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────────────

SALES_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "data", "sales", "Phoenix"
)
SALES_DATA_DIR = os.path.normpath(SALES_DATA_DIR)


# ── Pydantic Response Schemas ─────────────────────────────────────────────────


class SalesRecord(BaseModel):
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


class PaginatedSalesResponse(BaseModel):
    data: list[SalesRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class TimeSeriesPoint(BaseModel):
    period: str
    count: int
    total_volume: float
    median_price_per_unit: float | None = None


class SubmarketComparison(BaseModel):
    submarket: str
    year: int
    median_price_per_unit: float | None = None
    sales_count: int
    total_volume: float


class BuyerActivity(BaseModel):
    buyer: str
    transaction_count: int
    total_volume: float
    submarkets: list[str]
    first_purchase: date | None = None
    last_purchase: date | None = None


class DistributionBucket(BaseModel):
    label: str
    count: int
    median_price_per_unit: float | None = None
    avg_price_per_unit: float | None = None


class DataQualityReport(BaseModel):
    total_records: int
    records_by_file: dict[str, int]
    null_rates: dict[str, float]
    flagged_outliers: dict[str, int]


class ImportResponse(BaseModel):
    success: bool
    message: str
    rows_imported: int = 0
    rows_updated: int = 0


class ImportStatusResponse(BaseModel):
    unimported_files: list[str]
    last_imported_file: str | None = None
    last_import_date: str | None = None


class ReminderStatusResponse(BaseModel):
    show_reminder: bool
    last_imported_file_name: str | None = None
    last_imported_file_date: str | None = None


class FilterOptionsResponse(BaseModel):
    submarkets: list[str]


# ── 0. GET /filter-options — Distinct values for filter dropdowns ────────────


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def filter_options(
    db: AsyncSession = Depends(get_db),
):
    """Return distinct submarket values for filter dropdowns."""
    stmt = (
        select(SalesData.submarket_cluster)
        .where(
            SalesData.submarket_cluster.isnot(None),
            SalesData.submarket_cluster != "",
        )
        .distinct()
        .order_by(SalesData.submarket_cluster)
    )
    result = await db.execute(stmt)
    submarkets = [row[0] for row in result.all()]
    return FilterOptionsResponse(submarkets=submarkets)


# ── Shared filter helper ──────────────────────────────────────────────────────


def _apply_filters(
    stmt,
    search: str | None = None,
    submarkets: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_price_per_unit: float | None = None,
    max_price_per_unit: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Apply common filter criteria to a SQLAlchemy select statement."""
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            SalesData.property_name.ilike(pattern)
            | SalesData.property_address.ilike(pattern)
            | SalesData.property_city.ilike(pattern)
            | SalesData.buyer_true_company.ilike(pattern)
            | SalesData.seller_true_company.ilike(pattern)
            | SalesData.submarket_cluster.ilike(pattern)
        )
    if submarkets:
        sub_list = [s.strip() for s in submarkets.split(",") if s.strip()]
        if sub_list:
            stmt = stmt.where(SalesData.submarket_cluster.in_(sub_list))
    if min_units is not None:
        stmt = stmt.where(SalesData.number_of_units >= min_units)
    if max_units is not None:
        stmt = stmt.where(SalesData.number_of_units <= max_units)
    if min_price is not None:
        stmt = stmt.where(SalesData.sale_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(SalesData.sale_price <= max_price)
    if min_price_per_unit is not None:
        stmt = stmt.where(SalesData.price_per_unit >= min_price_per_unit)
    if max_price_per_unit is not None:
        stmt = stmt.where(SalesData.price_per_unit <= max_price_per_unit)
    if date_from is not None:
        stmt = stmt.where(SalesData.sale_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(SalesData.sale_date <= date_to)
    return stmt


# ── 1. GET / — Paginated table data ──────────────────────────────────────────


# Columns that the client may sort by
_SORTABLE_COLUMNS: dict[str, Any] = {
    "id": SalesData.id,
    "property_name": SalesData.property_name,
    "property_city": SalesData.property_city,
    "submarket_cluster": SalesData.submarket_cluster,
    "star_rating": SalesData.star_rating,
    "year_built": SalesData.year_built,
    "number_of_units": SalesData.number_of_units,
    "avg_unit_sf": SalesData.avg_unit_sf,
    "sale_date": SalesData.sale_date,
    "sale_price": SalesData.sale_price,
    "price_per_unit": SalesData.price_per_unit,
    "buyer_true_company": SalesData.buyer_true_company,
    "seller_true_company": SalesData.seller_true_company,
}


@router.get("/", response_model=PaginatedSalesResponse)
async def list_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("sale_date"),
    sort_dir: str = Query("desc"),
    search: str | None = None,
    submarkets: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_price_per_unit: float | None = None,
    max_price_per_unit: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable, sortable list of sales records."""

    # ── Count query ───────────────────────────────────────────────────────
    count_stmt = select(func.count()).select_from(SalesData)
    count_stmt = _apply_filters(
        count_stmt,
        search,
        submarkets,
        min_units,
        max_units,
        min_price,
        max_price,
        min_price_per_unit,
        max_price_per_unit,
        date_from,
        date_to,
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # ── Data query ────────────────────────────────────────────────────────
    data_stmt = select(SalesData)
    data_stmt = _apply_filters(
        data_stmt,
        search,
        submarkets,
        min_units,
        max_units,
        min_price,
        max_price,
        min_price_per_unit,
        max_price_per_unit,
        date_from,
        date_to,
    )

    # Sort
    sort_col = _SORTABLE_COLUMNS.get(sort_by, SalesData.sale_date)
    if sort_dir.lower() == "asc":
        data_stmt = data_stmt.order_by(sort_col.asc().nulls_last())
    else:
        data_stmt = data_stmt.order_by(sort_col.desc().nulls_last())

    # Pagination
    offset = (page - 1) * page_size
    data_stmt = data_stmt.offset(offset).limit(page_size)

    result = await db.execute(data_stmt)
    rows = result.scalars().all()

    records = []
    for r in rows:
        nrsf = None
        price_per_nrsf = None
        if r.number_of_units and r.avg_unit_sf:
            nrsf = r.number_of_units * r.avg_unit_sf
            if r.sale_price and nrsf > 0:
                price_per_nrsf = r.sale_price / nrsf

        records.append(
            SalesRecord(
                id=r.id,
                property_name=r.property_name,
                property_address=r.property_address,
                property_city=r.property_city,
                submarket_cluster=r.submarket_cluster,
                star_rating=r.star_rating,
                year_built=r.year_built,
                number_of_units=r.number_of_units,
                avg_unit_sf=r.avg_unit_sf,
                sale_date=r.sale_date,
                sale_price=r.sale_price,
                price_per_unit=r.price_per_unit,
                buyer_true_company=r.buyer_true_company,
                seller_true_company=r.seller_true_company,
                latitude=r.latitude,
                longitude=r.longitude,
                nrsf=round(nrsf, 2) if nrsf else None,
                price_per_nrsf=round(price_per_nrsf, 2) if price_per_nrsf else None,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedSalesResponse(
        data=records,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ── 2. GET /analytics/time-series ────────────────────────────────────────────


@router.get("/analytics/time-series", response_model=list[TimeSeriesPoint])
async def time_series(
    granularity: str = Query("year", pattern="^(month|quarter|year)$"),
    search: str | None = None,
    submarkets: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_price_per_unit: float | None = None,
    max_price_per_unit: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Transaction volume over time grouped by month, quarter, or year."""

    # Build the period expression depending on granularity
    period_expr: Any
    if granularity == "month":
        period_expr = func.to_char(SalesData.sale_date, "YYYY-MM")
    elif granularity == "quarter":
        period_expr = func.concat(
            func.extract("year", SalesData.sale_date).cast(SAInteger),
            "-Q",
            func.extract("quarter", SalesData.sale_date).cast(SAInteger),
        )
    else:  # year
        period_expr = (
            func.extract("year", SalesData.sale_date).cast(SAInteger).cast(SAString)
        )

    stmt = (
        select(
            period_expr.label("period"),
            func.count().label("count"),
            func.coalesce(func.sum(SalesData.sale_price), 0).label("total_volume"),
            func.percentile_cont(0.5)
            .within_group(SalesData.price_per_unit)
            .label("median_price_per_unit"),
        )
        .where(SalesData.sale_date.isnot(None))
        .group_by(period_expr)
        .order_by(period_expr)
    )

    stmt = _apply_filters(
        stmt,
        search,
        submarkets,
        min_units,
        max_units,
        min_price,
        max_price,
        min_price_per_unit,
        max_price_per_unit,
        date_from,
        date_to,
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        TimeSeriesPoint(
            period=str(r.period),
            count=r.count,  # type: ignore[arg-type]
            total_volume=float(r.total_volume or 0),
            median_price_per_unit=float(r.median_price_per_unit)
            if r.median_price_per_unit is not None
            else None,
        )
        for r in rows
    ]


# ── 3. GET /analytics/submarket-comparison ────────────────────────────────────


@router.get(
    "/analytics/submarket-comparison",
    response_model=list[SubmarketComparison],
)
async def submarket_comparison(
    db: AsyncSession = Depends(get_db),
):
    """Median price-per-unit and volume by submarket and year."""

    year_expr = func.extract("year", SalesData.sale_date).cast(SAInteger)

    stmt = (
        select(
            SalesData.submarket_cluster.label("submarket"),
            year_expr.label("year"),
            func.percentile_cont(0.5)
            .within_group(SalesData.price_per_unit)
            .label("median_price_per_unit"),
            func.count().label("sales_count"),
            func.coalesce(func.sum(SalesData.sale_price), 0).label("total_volume"),
        )
        .where(
            SalesData.submarket_cluster.isnot(None),
            SalesData.sale_date.isnot(None),
        )
        .group_by(SalesData.submarket_cluster, year_expr)
        .order_by(SalesData.submarket_cluster, year_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        SubmarketComparison(
            submarket=r.submarket,
            year=int(r.year),
            median_price_per_unit=float(r.median_price_per_unit)
            if r.median_price_per_unit is not None
            else None,
            sales_count=r.sales_count,
            total_volume=float(r.total_volume or 0),
        )
        for r in rows
    ]


# ── 4. GET /analytics/buyer-activity ──────────────────────────────────────────


@router.get("/analytics/buyer-activity", response_model=list[BuyerActivity])
async def buyer_activity(
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    submarkets: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_price_per_unit: float | None = None,
    max_price_per_unit: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Top buyers ranked by total acquisition volume."""

    # Main aggregate query
    stmt = (
        select(
            SalesData.buyer_true_company.label("buyer"),
            func.count().label("transaction_count"),
            func.coalesce(func.sum(SalesData.sale_price), 0).label("total_volume"),
            func.min(SalesData.sale_date).label("first_purchase"),
            func.max(SalesData.sale_date).label("last_purchase"),
            func.array_agg(func.distinct(SalesData.submarket_cluster)).label(
                "submarkets_arr"
            ),
        )
        .where(
            SalesData.buyer_true_company.isnot(None),
            SalesData.buyer_true_company != "",
        )
        .group_by(SalesData.buyer_true_company)
        .order_by(func.sum(SalesData.sale_price).desc().nulls_last())
        .limit(limit)
    )

    stmt = _apply_filters(
        stmt,
        search,
        submarkets,
        min_units,
        max_units,
        min_price,
        max_price,
        min_price_per_unit,
        max_price_per_unit,
        date_from,
        date_to,
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        BuyerActivity(
            buyer=r.buyer,
            transaction_count=r.transaction_count,
            total_volume=float(r.total_volume or 0),
            submarkets=[s for s in (r.submarkets_arr or []) if s is not None],
            first_purchase=r.first_purchase,
            last_purchase=r.last_purchase,
        )
        for r in rows
    ]


# ── 5. GET /analytics/distributions ──────────────────────────────────────────


@router.get("/analytics/distributions", response_model=list[DistributionBucket])
async def distributions(
    group_by: str = Query("vintage", pattern="^(vintage|unit_count|star_rating)$"),
    search: str | None = None,
    submarkets: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_price_per_unit: float | None = None,
    max_price_per_unit: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Distribution of sales by vintage, unit count, or star rating buckets."""

    if group_by == "vintage":
        label_expr = case(
            (SalesData.year_built < 1990, "Pre-1990"),
            (SalesData.year_built.between(1990, 2004), "1990-2005"),
            (SalesData.year_built.between(2005, 2019), "2005-2020"),
            (SalesData.year_built >= 2020, "Post-2020"),
            else_="Unknown",
        )
    elif group_by == "unit_count":
        label_expr = case(
            (SalesData.number_of_units.between(1, 50), "1-50"),
            (SalesData.number_of_units.between(51, 100), "51-100"),
            (SalesData.number_of_units.between(101, 200), "101-200"),
            (SalesData.number_of_units.between(201, 500), "201-500"),
            (SalesData.number_of_units > 500, "500+"),
            else_="Unknown",
        )
    else:  # star_rating
        label_expr = func.coalesce(SalesData.star_rating, "Unknown")  # type: ignore[assignment]

    stmt = (
        select(
            label_expr.label("label"),
            func.count().label("count"),
            func.percentile_cont(0.5)
            .within_group(SalesData.price_per_unit)
            .label("median_price_per_unit"),
            func.avg(SalesData.price_per_unit).label("avg_price_per_unit"),
        )
        .group_by(label_expr)
        .order_by(label_expr)
    )

    stmt = _apply_filters(
        stmt,
        search,
        submarkets,
        min_units,
        max_units,
        min_price,
        max_price,
        min_price_per_unit,
        max_price_per_unit,
        date_from,
        date_to,
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        DistributionBucket(
            label=str(r.label),
            count=r.count,  # type: ignore[arg-type]
            median_price_per_unit=float(r.median_price_per_unit)
            if r.median_price_per_unit is not None
            else None,
            avg_price_per_unit=round(float(r.avg_price_per_unit), 2)
            if r.avg_price_per_unit is not None
            else None,
        )
        for r in rows
    ]


# ── 6. GET /analytics/data-quality ────────────────────────────────────────────


@router.get("/analytics/data-quality", response_model=DataQualityReport)
async def data_quality(
    db: AsyncSession = Depends(get_db),
):
    """Data quality overview: record counts, null rates, flagged outliers."""

    # Total records
    total = (
        await db.execute(select(func.count()).select_from(SalesData))
    ).scalar() or 0

    # Records by file
    file_stmt = (
        select(SalesData.source_file, func.count())
        .group_by(SalesData.source_file)
        .order_by(SalesData.source_file)
    )
    file_rows = (await db.execute(file_stmt)).all()
    records_by_file = {str(r[0] or "unknown"): r[1] for r in file_rows}

    # Null rates for key fields
    null_rates: dict[str, float] = {}
    if total > 0:
        key_fields = {
            "actual_cap_rate": SalesData.actual_cap_rate,
            "price_per_unit": SalesData.price_per_unit,
            "avg_unit_sf": SalesData.avg_unit_sf,
            "property_name": SalesData.property_name,
            "sale_price": SalesData.sale_price,
            "sale_date": SalesData.sale_date,
        }
        for field_name, col in key_fields.items():
            null_count = (
                await db.execute(
                    select(func.count()).select_from(SalesData).where(col.is_(None))
                )
            ).scalar() or 0
            null_rates[field_name] = round(null_count / total, 4)

    # Flagged outliers
    dollar_one_sales = (
        await db.execute(
            select(func.count())
            .select_from(SalesData)
            .where(SalesData.sale_price <= 1, SalesData.sale_price.isnot(None))
        )
    ).scalar() or 0

    high_units = (
        await db.execute(
            select(func.count())
            .select_from(SalesData)
            .where(SalesData.number_of_units > 800)
        )
    ).scalar() or 0

    flagged_outliers = {
        "dollar_one_sales": dollar_one_sales,
        "high_unit_count_over_800": high_units,
    }

    return DataQualityReport(
        total_records=total,
        records_by_file=records_by_file,
        null_rates=null_rates,
        flagged_outliers=flagged_outliers,
    )


# ── 7. POST /import — Trigger file import ────────────────────────────────────


@router.post("/import", response_model=ImportResponse)
async def trigger_import(
    db_sync=Depends(get_sync_db),
):
    """Import any unimported CoStar Excel files from the data directory."""
    from app.services.sales_import import get_unimported_files, import_sales_file

    try:
        unimported = get_unimported_files(db_sync, SALES_DATA_DIR)
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
            result = import_sales_file(db_sync, filepath, market="Phoenix")
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
        logger.error(f"Import failed: {e}")
        return ImportResponse(success=False, message=str(e))


# ── 8. GET /import/status ─────────────────────────────────────────────────────


@router.get("/import/status", response_model=ImportStatusResponse)
async def import_status(
    db_sync=Depends(get_sync_db),
):
    """Check for unimported files and last import date."""
    from app.services.sales_import import get_unimported_files

    unimported = get_unimported_files(db_sync, SALES_DATA_DIR)
    unimported_names = [os.path.basename(f) for f in unimported]

    # Most recent imported file (sync session uses SQLAlchemy 1.x-style query)
    from sqlalchemy import select as sa_select

    last_row = db_sync.execute(
        sa_select(SalesData.source_file, SalesData.imported_at)
        .where(SalesData.imported_at.isnot(None))
        .order_by(SalesData.imported_at.desc())
        .limit(1)
    ).first()

    return ImportStatusResponse(
        unimported_files=unimported_names,
        last_imported_file=last_row[0] if last_row else None,
        last_import_date=str(last_row[1]) if last_row else None,
    )


# ── 9. PUT /reminder/dismiss ─────────────────────────────────────────────────

# Store dismissals in-memory keyed by month for simplicity.
# For production, this should be persisted in a DB table.
_reminder_dismissals: dict[str, datetime] = {}


@router.put("/reminder/dismiss")
async def dismiss_reminder():
    """Dismiss the monthly import reminder for the current month."""
    month_key = datetime.now(UTC).strftime("%Y-%m")
    _reminder_dismissals[month_key] = datetime.now(UTC)
    return {"dismissed": True, "month": month_key}


# ── 10. GET /reminder/status ─────────────────────────────────────────────────


@router.get("/reminder/status", response_model=ReminderStatusResponse)
async def reminder_status(
    db: AsyncSession = Depends(get_db),
):
    """Check if the import reminder should be shown this month."""
    now = datetime.now(UTC)
    month_key = now.strftime("%Y-%m")

    # Check if dismissed this month
    dismissed = month_key in _reminder_dismissals

    # Show reminder on the 1st of the month (or if not dismissed)
    show_reminder = (now.day <= 7) and not dismissed

    # Get last imported file info
    last_row_result = await db.execute(
        select(SalesData.source_file, SalesData.imported_at)
        .where(SalesData.imported_at.isnot(None))
        .order_by(SalesData.imported_at.desc())
        .limit(1)
    )
    last_row = last_row_result.first()

    return ReminderStatusResponse(
        show_reminder=show_reminder,
        last_imported_file_name=last_row[0] if last_row else None,
        last_imported_file_date=str(last_row[1]) if last_row else None,
    )
