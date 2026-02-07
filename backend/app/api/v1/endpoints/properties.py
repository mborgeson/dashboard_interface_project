"""
Property endpoints for CRUD operations, analytics, and dashboard views.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints._property_transforms import (
    _decimal_to_float,
    to_frontend_property,
)
from app.core.permissions import CurrentUser, get_current_user
from app.crud import property as property_crud
from app.crud.crud_activity import property_activity
from app.db.session import get_db
from app.models import Property
from app.models.activity import ActivityType as ActivityTypeModel
from app.schemas.activity import (
    ActivityType,
    PropertyActivityCreate,
    PropertyActivityListResponse,
    PropertyActivityResponse,
)
from app.schemas.property import (
    PropertyCreate,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdate,
)

router = APIRouter()


@router.get("/dashboard")
async def list_properties_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """
    List all properties in the nested frontend format.
    Returns { properties: [...], total: N } matching the frontend Property type.
    """
    items = await property_crud.get_multi_filtered(
        db,
        skip=0,
        limit=200,
        order_by="name",
        order_desc=False,
    )
    total = await property_crud.count_filtered(db)
    properties = [to_frontend_property(p) for p in items]
    return {"properties": properties, "total": total}


@router.get("/dashboard/{property_id}")
async def get_property_dashboard(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single property in the nested frontend format.
    """
    prop = await property_crud.get(db, property_id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )
    return to_frontend_property(prop)


@router.get("/summary")
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio-level summary statistics.
    Returns PropertySummaryStats matching the frontend type.
    """
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

    return {
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


@router.get("/", response_model=PropertyListResponse)
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


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
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


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new property.
    """
    new_property = await property_crud.create(db, obj_in=property_data)
    logger.info(f"Created property: {new_property.name} (ID: {new_property.id})")
    return new_property


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
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

    return updated_property


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
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
    return None


@router.get("/{property_id}/analytics")
async def get_property_analytics(
    property_id: int,
    db: AsyncSession = Depends(get_db),
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
                "periods": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            },
            "comparables": {
                "market_avg_rent": 1425,
                "market_avg_occupancy": 94.0,
                "market_avg_cap_rate": 5.5,
                "comparable_count": 0,
            },
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
        "trends": {
            # Trends would need historical data - returning current values as single point
            "rent": [round(current_rent, 0)] if current_rent else [],
            "occupancy": [round(current_occupancy, 1)] if current_occupancy else [],
            "periods": ["Current"],
            "note": "Historical trend data requires time-series tracking",
        },
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


@router.get("/{property_id}/activities", response_model=PropertyActivityListResponse)
async def get_property_activities(
    property_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    activity_type: str | None = Query(
        None,
        description="Filter by activity type: view, edit, comment, status_change, document_upload",
    ),
    db: AsyncSession = Depends(get_db),
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

    # Convert to response models
    items = []
    for activity in activities:
        items.append(
            PropertyActivityResponse(
                id=activity.id,
                property_id=activity.property_id,
                user_id=activity.user_id,
                user_name=None,  # Would need join with users table
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


@router.post("/{property_id}/activities", response_model=PropertyActivityResponse)
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
