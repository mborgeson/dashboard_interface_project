"""
Property endpoints for CRUD operations, analytics, and dashboard views.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints._property_transforms import (
    _decimal_to_float,
    to_frontend_property,
)
from app.core.cache import LONG_TTL, cache
from app.core.permissions import (
    CurrentUser,
    get_current_user,
    require_analyst,
    require_manager,
)
from app.crud import property as property_crud
from app.crud.crud_activity import property_activity
from app.db.session import get_db
from app.models import Property
from app.models.activity import ActivityType as ActivityTypeModel
from app.models.extraction import ExtractedValue
from app.models.user import User
from app.schemas.activity import (
    ActivityType,
    PropertyActivityCreate,
    PropertyActivityListResponse,
    PropertyActivityResponse,
)
from app.schemas.pagination import CursorPaginationParams
from app.schemas.property import (
    PropertyCreate,
    PropertyCursorPaginatedResponse,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdate,
)

router = APIRouter()

# Projected NOI fields from proforma extractions, ordered by year
_PROJECTED_NOI_FIELDS: list[tuple[str, str]] = [
    ("PROFORMA_NOI_YR1", "Year 1"),
    ("PROFORMA_NOI_YR2", "Year 2"),
    ("PROFORMA_NOI_YR3", "Year 3"),
    ("NOI_PER_UNIT_YR2", "Year 2"),
    ("NOI_PER_UNIT_YR3", "Year 3"),
    ("NOI_PER_UNIT_YR5", "Year 5"),
    ("NOI_PER_UNIT_YR7", "Year 7"),
]

# All field names we query for trend projections
_TREND_PROJECTION_FIELDS: set[str] = {f for f, _ in _PROJECTED_NOI_FIELDS}


async def _build_projected_trends(
    db: AsyncSession,
    property_id: int,
    property_name: str,
    current_noi: float | None,
) -> dict:
    """
    Build multi-point trend data from extracted proforma projections.

    Queries extracted_values for year-specific NOI fields and assembles them
    into arrays the frontend can render as trend lines.

    Returns a dict with keys: noi, periods, data_points, trend_type, note.
    """
    # Query extracted projections for this property
    stmt = select(
        ExtractedValue.field_name,
        ExtractedValue.value_numeric,
    ).where(
        or_(
            ExtractedValue.property_id == property_id,
            ExtractedValue.property_name == property_name,
        ),
        ExtractedValue.field_name.in_(_TREND_PROJECTION_FIELDS),
        ExtractedValue.is_error.is_(False),
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Build a lookup: field_name -> numeric value
    projections: dict[str, float] = {}
    for row in rows:
        if row.value_numeric is not None:
            projections[row.field_name] = float(row.value_numeric)

    if not projections:
        return {}

    # Prefer PROFORMA_NOI series (absolute NOI), fall back to NOI_PER_UNIT
    noi_series: list[tuple[str, float]] = []  # (period_label, value)
    proforma_noi_keys = [
        ("PROFORMA_NOI_YR1", "Year 1"),
        ("PROFORMA_NOI_YR2", "Year 2"),
        ("PROFORMA_NOI_YR3", "Year 3"),
    ]
    noi_per_unit_keys = [
        ("NOI_PER_UNIT_YR2", "Year 2"),
        ("NOI_PER_UNIT_YR3", "Year 3"),
        ("NOI_PER_UNIT_YR5", "Year 5"),
        ("NOI_PER_UNIT_YR7", "Year 7"),
    ]

    # Try PROFORMA_NOI first (absolute dollars)
    for field, label in proforma_noi_keys:
        if field in projections:
            noi_series.append((label, round(projections[field], 2)))

    # If we got fewer than 2 points from PROFORMA_NOI, try NOI_PER_UNIT
    if len(noi_series) < 2:
        noi_series = []
        for field, label in noi_per_unit_keys:
            if field in projections:
                noi_series.append((label, round(projections[field], 2)))

    if not noi_series:
        return {}

    # Prepend current NOI as "Current" if available and not already covered
    periods = [label for label, _ in noi_series]
    values = [val for _, val in noi_series]

    if current_noi is not None and "Year 1" not in periods:
        periods.insert(0, "Current")
        values.insert(0, round(current_noi, 2))

    return {
        "noi": values,
        "periods": periods,
        "data_points": len(values),
        "trend_type": "projected",
        "note": "Projected from proforma underwriting model",
    }


@router.get(
    "/dashboard",
    summary="List properties (dashboard format)",
    description="List all properties in the nested frontend format used by the dashboard. "
    "Properties missing financial_data are lazily enriched from extracted values.",
    responses={
        200: {
            "description": "Properties list in frontend-compatible format with total count"
        },
    },
)
async def list_properties_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    List all properties in the nested frontend format.
    Returns { properties: [...], total: N } matching the frontend Property type.
    """
    cache_key = "property_dashboard_list"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    items = await property_crud.get_multi_filtered(
        db,
        skip=0,
        limit=200,
        order_by="name",
        order_desc=False,
    )
    total = await property_crud.count_filtered(db)

    # Batch enrichment: 2 queries for all properties instead of 2-3 per property (N+1 fix)
    items = await property_crud.enrich_financial_data_batch(db, items)

    properties = [to_frontend_property(p) for p in items]
    result = {"properties": properties, "total": total}

    await cache.set(cache_key, result, ttl=LONG_TTL)
    return result


@router.get(
    "/dashboard/{property_id}",
    summary="Get property (dashboard format)",
    description="Get a single property in the nested frontend format. Lazily enriches "
    "financial_data from extracted_values if it has not been populated yet.",
    responses={
        200: {"description": "Property in frontend-compatible format"},
        404: {"description": "Property not found"},
    },
)
async def get_property_dashboard(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get a single property in the nested frontend format.

    If ``financial_data`` has not been populated yet (e.g. hydration did
    not run after extraction), this endpoint lazily enriches the property
    from the ``extracted_values`` table before returning.
    """
    prop = await property_crud.get(db, property_id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Lazy enrichment: populate financial_data from extracted_values
    fd = prop.financial_data or {}
    if not fd or "expenses" not in fd or "operationsByYear" not in fd:
        prop = await property_crud.enrich_financial_data(db, prop)

    return to_frontend_property(prop)


@router.get(
    "/summary",
    summary="Get portfolio summary",
    description="Return portfolio-level summary statistics including total properties, units, "
    "value, NOI, average occupancy, average cap rate, and equity-weighted IRR and cash-on-cash.",
    responses={
        200: {"description": "Portfolio summary statistics"},
    },
)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get portfolio-level summary statistics.
    Returns PropertySummaryStats matching the frontend type.
    """
    cache_key = "portfolio_summary"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    items = await property_crud.get_multi_filtered(
        db,
        skip=0,
        limit=200,
        order_by="name",
        order_desc=False,
    )

    if not items:
        return {
            "totalProperties": 0,
            "totalUnits": 0,
            "totalValue": 0,
            "totalInvested": 0,
            "totalNOI": 0,
            "averageOccupancy": 0,
            "averageCapRate": 0,
            "portfolioCashOnCash": 0,
            "portfolioIRR": 0,
        }

    # Batch enrichment: 2 queries for all properties instead of 2-3 per property (N+1 fix)
    items = await property_crud.enrich_financial_data_batch(db, items)

    total_properties = len(items)
    total_units = sum(p.total_units or 0 for p in items)
    total_value = sum(float(p.current_value or 0) for p in items)

    # Use financial_data for invested amounts and returns
    total_invested: float = 0
    total_noi: float = 0
    occ_sum: float = 0
    cap_sum: float = 0
    occ_count: int = 0
    cap_count: int = 0
    irr_weighted: float = 0
    coc_weighted: float = 0
    equity_sum: float = 0

    for p in items:
        fd = p.financial_data or {}
        acq = fd.get("acquisition", {})
        ret = fd.get("returns", {})

        invested = acq.get("totalAcquisitionBudget") or float(p.purchase_price or 0)
        total_invested += invested

        # NOI in DB is annual per-unit — multiply by units for total
        noi_per_unit = float(p.noi or 0)
        units = p.total_units or 0
        annual_noi = noi_per_unit * units if noi_per_unit and units else 0
        total_noi += annual_noi

        if p.occupancy_rate:
            occ_sum += float(p.occupancy_rate)
            occ_count += 1

        # Compute cap rate from annual NOI / purchase price
        pp = float(p.purchase_price or 0)
        if annual_noi > 0 and pp > 0:
            cap_sum += annual_noi / pp
            cap_count += 1

        irr = ret.get("lpIrr") or 0
        coc = ret.get("cashOnCashYear1") or 0
        loan = fd.get("financing", {}).get("loanAmount") or 0
        equity = invested - loan if invested and loan else invested
        if equity > 0:
            irr_weighted += irr * equity
            coc_weighted += coc * equity
            equity_sum += equity

    result = {
        "totalProperties": total_properties,
        "totalUnits": total_units,
        "totalValue": round(total_value, 2),
        "totalInvested": round(total_invested, 2),
        "totalNOI": round(total_noi, 2),
        "averageOccupancy": round(occ_sum / occ_count / 100, 4) if occ_count else 0,
        "averageCapRate": round(cap_sum / cap_count, 4) if cap_count else 0,
        "portfolioCashOnCash": round(coc_weighted / equity_sum, 4) if equity_sum else 0,
        "portfolioIRR": round(irr_weighted / equity_sum, 4) if equity_sum else 0,
    }

    await cache.set(cache_key, result, ttl=LONG_TTL)
    return result


@router.get(
    "/",
    response_model=PropertyListResponse,
    summary="List properties",
    description="List all properties with filtering by type, city, state, market, and unit "
    "count range. Supports pagination and sorting.",
    responses={
        200: {"description": "Paginated list of properties"},
    },
)
async def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    property_type: str | None = None,
    city: str | None = None,
    state: str | None = None,
    market: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    sort_by: str | None = "name",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    List all properties with filtering and pagination.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **property_type**: Filter by type (multifamily, office, retail, industrial)
    - **city**: Filter by city
    - **state**: Filter by state
    - **market**: Filter by market
    """
    skip = (page - 1) * page_size
    order_desc = sort_order.lower() == "desc"

    # Get filtered properties from database
    items = await property_crud.get_multi_filtered(
        db,
        skip=skip,
        limit=page_size,
        property_type=property_type,
        city=city,
        state=state,
        market=market,
        min_units=min_units,
        max_units=max_units,
        order_by=sort_by or "name",
        order_desc=order_desc,
    )

    # Get total count for pagination
    total = await property_crud.count_filtered(
        db,
        property_type=property_type,
        city=city,
        state=state,
        market=market,
        min_units=min_units,
        max_units=max_units,
    )

    return PropertyListResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/cursor",
    response_model=PropertyCursorPaginatedResponse,
    summary="List properties (cursor pagination)",
    description="List properties using cursor-based pagination for efficient, stable paging. "
    "Supports the same filters as the standard list endpoint.",
    responses={
        200: {"description": "Cursor-paginated list of properties"},
        400: {"description": "Invalid cursor"},
    },
)
async def list_properties_cursor(
    cursor: str | None = Query(
        None, description="Opaque cursor from previous response"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    direction: str = Query(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    ),
    property_type: str | None = None,
    city: str | None = None,
    state: str | None = None,
    market: str | None = None,
    min_units: int | None = None,
    max_units: int | None = None,
    sort_by: str | None = "name",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    List properties with cursor-based pagination.

    Cursor pagination provides stable, efficient paging without offset scans.
    """
    order_desc = sort_order.lower() == "desc"

    conditions = property_crud._build_property_conditions(
        property_type=property_type,
        city=city,
        state=state,
        market=market,
        min_units=min_units,
        max_units=max_units,
    )

    params = CursorPaginationParams(cursor=cursor, limit=limit, direction=direction)

    try:
        result = await property_crud.get_cursor_paginated(
            db,
            params=params,
            order_by=sort_by or "name",
            order_desc=order_desc,
            conditions=conditions,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return PropertyCursorPaginatedResponse(
        items=result.items,  # type: ignore[arg-type]
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_more=result.has_more,
        total=result.total,
    )


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Get property by ID",
    description="Retrieve a single property by its database ID.",
    responses={
        200: {"description": "Property details"},
        404: {"description": "Property not found"},
    },
)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get a specific property by ID.
    """
    property_obj = await property_crud.get(db, property_id)

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    return property_obj


@router.post(
    "/",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a property",
    description="Create a new property record. Requires manager role.",
    responses={
        201: {"description": "Property created successfully"},
    },
)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Create a new property.
    """
    new_property = await property_crud.create(db, obj_in=property_data)
    logger.info(f"Created property: {new_property.name} (ID: {new_property.id})")
    await cache.invalidate_properties()
    return new_property


@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Update a property",
    description="Full update of an existing property. Requires manager role.",
    responses={
        200: {"description": "Property updated successfully"},
        404: {"description": "Property not found"},
    },
)
async def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Update an existing property.
    """
    existing = await property_crud.get(db, property_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    updated_property = await property_crud.update(
        db, db_obj=existing, obj_in=property_data
    )
    logger.info(f"Updated property: {property_id}")
    await cache.invalidate_properties()
    return updated_property


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a property",
    description="Soft-delete a property. Requires manager role.",
    responses={
        204: {"description": "Property deleted successfully"},
        404: {"description": "Property not found"},
    },
)
async def delete_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
):
    """
    Delete a property (soft delete).
    """
    existing = await property_crud.get(db, property_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    await property_crud.remove(db, id=property_id)
    logger.info(f"Deleted property: {property_id}")
    await cache.invalidate_properties()
    return None


@router.get(
    "/{property_id}/analytics",
    summary="Get property analytics",
    description="Return analytics data for a property including current performance metrics, "
    "rent/occupancy trends, and market comparables from properties in the same market and type. "
    "Falls back to mock data if no real metrics are available.",
    responses={
        200: {
            "description": "Property analytics with metrics, trends, and market comparables"
        },
        404: {"description": "Property not found"},
    },
)
async def get_property_analytics(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get analytics data for a specific property.

    Returns:
    - Historical performance metrics
    - Rent growth trends
    - Occupancy trends
    - Comparable market data
    """
    # Verify property exists
    property_obj = await property_crud.get(db, property_id)
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Get market comparables - properties in same market and type
    market_comps_filters = []
    if property_obj.market:
        market_comps_filters.append(
            func.lower(Property.market) == func.lower(property_obj.market)
        )
    if property_obj.property_type:
        market_comps_filters.append(
            Property.property_type == property_obj.property_type
        )

    # Exclude current property from comparables
    market_comps_filters.append(Property.id != property_id)

    # Query market averages for comparable properties
    market_comps_result = await db.execute(
        select(
            func.avg(Property.avg_rent_per_unit).label("avg_rent"),
            func.avg(Property.occupancy_rate).label("avg_occupancy"),
            func.avg(Property.cap_rate).label("avg_cap_rate"),
            func.count(Property.id).label("comp_count"),
        ).where(
            *market_comps_filters if market_comps_filters else [literal_column("1=1")]
        )
    )
    market_row = market_comps_result.fetchone()

    # Get current property metrics
    current_rent = _decimal_to_float(property_obj.avg_rent_per_unit)
    raw_occ = _decimal_to_float(property_obj.occupancy_rate)
    current_occupancy = raw_occ / 100 if raw_occ and raw_occ > 1 else raw_occ
    current_cap_rate = _decimal_to_float(property_obj.cap_rate)
    current_noi = _decimal_to_float(property_obj.noi)

    # Get market averages
    market_avg_rent = _decimal_to_float(market_row.avg_rent) if market_row else None
    raw_market_occ = _decimal_to_float(market_row.avg_occupancy) if market_row else None
    market_avg_occupancy = (
        raw_market_occ / 100
        if raw_market_occ and raw_market_occ > 1
        else raw_market_occ
    )
    market_avg_cap_rate = (
        _decimal_to_float(market_row.avg_cap_rate) if market_row else None
    )
    comp_count = market_row.comp_count if market_row else 0

    # Calculate rent vs market ratio
    rent_vs_market = None
    if current_rent and market_avg_rent and market_avg_rent > 0:
        rent_vs_market = round(current_rent / market_avg_rent, 2)

    # If no real data available, return mock data as fallback
    if current_rent is None and current_occupancy is None:
        return {
            "property_id": property_id,
            "property_name": property_obj.name,
            "data_source": "mock",
            "metrics": {
                "ytd_rent_growth": 3.2,
                "ytd_noi_growth": 4.1,
                "avg_occupancy_12m": 95.0,
                "rent_vs_market": 1.05,
            },
            "trends": {
                "rent": [1400, 1425, 1450, 1475, 1490, 1500],
                "occupancy": [94.0, 95.0, 96.0, 96.5, 96.0, 96.5],
                "noi": [],
                "periods": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                "data_points": 6,
                "trend_type": "historical",
                "note": "Mock data for demonstration",
            },
            "comparables": {
                "market_avg_rent": 1425,
                "market_avg_occupancy": 94.0,
                "market_avg_cap_rate": 5.5,
                "comparable_count": 0,
            },
        }

    # Try to build projected trends from extracted proforma data
    projected_trends = await _build_projected_trends(
        db, property_id, property_obj.name, current_noi
    )

    if projected_trends:
        # We have multi-point projection data from proforma extractions
        trends_data = {
            "rent": [round(current_rent, 0)] if current_rent else [],
            "occupancy": [round(current_occupancy, 1)] if current_occupancy else [],
            "noi": projected_trends["noi"],
            "periods": projected_trends["periods"],
            "data_points": projected_trends["data_points"],
            "trend_type": projected_trends["trend_type"],
            "note": projected_trends["note"],
        }
    elif current_rent is not None or current_occupancy is not None:
        # Single-point data only — pad with nulls so frontend shows "Insufficient data"
        trends_data = {
            "rent": [round(current_rent, 0)] if current_rent else [],
            "occupancy": [round(current_occupancy, 1)] if current_occupancy else [],
            "noi": [round(current_noi, 2)] if current_noi else [],
            "periods": ["Current", None, None, None, None],
            "data_points": 1,
            "trend_type": "current_only",
            "note": "Insufficient trend data — only current values available",
        }
    else:
        # No data at all
        trends_data = {
            "rent": [],
            "occupancy": [],
            "noi": [],
            "periods": [],
            "data_points": 0,
            "trend_type": "current_only",
            "note": "No trend data available",
        }

    # Build response with actual data
    return {
        "property_id": property_id,
        "property_name": property_obj.name,
        "data_source": "database",
        "metrics": {
            "current_rent_per_unit": round(current_rent, 2) if current_rent else None,
            "current_occupancy": round(current_occupancy, 1)
            if current_occupancy
            else None,
            "current_cap_rate": round(current_cap_rate, 2)
            if current_cap_rate
            else None,
            "current_noi": round(current_noi, 2) if current_noi else None,
            # Historical growth rates would need time-series data
            "ytd_rent_growth": None,  # Would need historical rent data
            "ytd_noi_growth": None,  # Would need historical NOI data
            "avg_occupancy_12m": round(current_occupancy, 1)
            if current_occupancy
            else None,
            "rent_vs_market": rent_vs_market,
        },
        "trends": trends_data,
        "comparables": {
            "market": property_obj.market,
            "property_type": property_obj.property_type,
            "market_avg_rent": round(market_avg_rent, 2) if market_avg_rent else None,
            "market_avg_occupancy": round(market_avg_occupancy, 1)
            if market_avg_occupancy
            else None,
            "market_avg_cap_rate": round(market_avg_cap_rate, 2)
            if market_avg_cap_rate
            else None,
            "comparable_count": comp_count,
        },
    }


@router.get(
    "/{property_id}/activities",
    response_model=PropertyActivityListResponse,
    summary="Get property activities",
    description="Retrieve paginated activity history for a property including views, edits, "
    "comments, status changes, and document uploads. Supports filtering by activity type.",
    responses={
        200: {"description": "Paginated list of property activities"},
        400: {"description": "Invalid activity_type filter value"},
        404: {"description": "Property not found"},
    },
)
async def get_property_activities(
    property_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    activity_type: str | None = Query(
        None,
        description="Filter by activity type: view, edit, comment, status_change, document_upload",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """
    Get activity history for a property.

    Returns a paginated list of activities including views, edits, comments,
    status changes, and document uploads.

    - **property_id**: Property ID to get activities for
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 50, max: 100)
    - **activity_type**: Filter by type (view, edit, comment, status_change, document_upload)
    """
    # Verify property exists
    property_obj = await property_crud.get(db, property_id)
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Validate activity_type if provided
    valid_types = {"view", "edit", "comment", "status_change", "document_upload"}
    if activity_type and activity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity_type. Must be one of: {', '.join(valid_types)}",
        )

    # Get activities from database
    activities = await property_activity.get_by_property(
        db,
        property_id=property_id,
        skip=skip,
        limit=limit,
        activity_type=activity_type,
    )

    # Get total count
    total = await property_activity.count_by_property(
        db,
        property_id=property_id,
        activity_type=activity_type,
    )

    # Batch lookup user display names to avoid N+1 queries
    user_ids = list({a.user_id for a in activities if a.user_id is not None})
    user_name_map: dict[int, str] = {}
    if user_ids:
        user_rows = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(user_ids))
        )
        user_name_map = {row.id: row.full_name for row in user_rows}

    # Convert to response models
    items = []
    for activity in activities:
        items.append(
            PropertyActivityResponse(
                id=activity.id,
                property_id=activity.property_id,
                user_id=activity.user_id,
                user_name=user_name_map.get(activity.user_id)
                if activity.user_id
                else None,
                activity_type=ActivityType(activity.activity_type.value),
                description=activity.description,
                field_changed=activity.field_changed,
                old_value=activity.old_value,
                new_value=activity.new_value,
                comment_text=activity.comment_text,
                document_name=activity.document_name,
                document_url=activity.document_url,
                created_at=activity.created_at,
                updated_at=activity.updated_at,
            )
        )

    return PropertyActivityListResponse(
        activities=items,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.post(
    "/{property_id}/activities",
    response_model=PropertyActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create property activity",
    description="Log a new activity entry for a property such as comments, document uploads, "
    "or manual status changes. Views and edits are typically logged automatically.",
    responses={
        201: {"description": "Activity created successfully"},
        400: {"description": "Property ID in body does not match path parameter"},
        404: {"description": "Property not found"},
    },
)
async def create_property_activity(
    property_id: int,
    activity_data: PropertyActivityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Create a new activity entry for a property.

    Used to log comments, document uploads, and other manual activities.
    Views and edits are typically logged automatically.

    - **property_id**: Property ID
    - **activity_data**: Activity details
    """
    # Verify property exists
    property_obj = await property_crud.get(db, property_id)
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Ensure property_id in body matches path
    if activity_data.property_id != property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property ID in body must match path parameter",
        )

    # Create the activity
    from app.models.activity import PropertyActivity as PropertyActivityModel

    activity = PropertyActivityModel(
        property_id=property_id,
        user_id=current_user.id,
        activity_type=ActivityTypeModel(activity_data.activity_type.value),
        description=activity_data.description,
        field_changed=activity_data.field_changed,
        old_value=activity_data.old_value,
        new_value=activity_data.new_value,
        comment_text=activity_data.comment_text,
        document_name=activity_data.document_name,
        document_url=activity_data.document_url,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    logger.info(
        f"User {current_user.email} created {activity_data.activity_type} activity for property {property_id}"
    )

    return PropertyActivityResponse(
        id=activity.id,
        property_id=activity.property_id,
        user_id=activity.user_id,
        user_name=current_user.full_name,
        activity_type=ActivityType(activity.activity_type.value),
        description=activity.description,
        field_changed=activity.field_changed,
        old_value=activity.old_value,
        new_value=activity.new_value,
        comment_text=activity.comment_text,
        document_name=activity.document_name,
        document_url=activity.document_url,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )
