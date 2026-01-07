"""
Property endpoints for CRUD operations and analytics.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import property as property_crud
from app.db.session import get_db
from app.models import Property
from app.schemas.property import (
    PropertyCreate,
    PropertyListResponse,
    PropertyResponse,
    PropertyUpdate,
)

router = APIRouter()


def _decimal_to_float(value: Decimal | None) -> float | None:
    """Convert Decimal to float, returning None if input is None."""
    return float(value) if value is not None else None


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
        items=items,
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
        market_comps_filters.append(Property.property_type == property_obj.property_type)

    # Exclude current property from comparables
    market_comps_filters.append(Property.id != property_id)

    # Query market averages for comparable properties
    market_comps_result = await db.execute(
        select(
            func.avg(Property.avg_rent_per_unit).label("avg_rent"),
            func.avg(Property.occupancy_rate).label("avg_occupancy"),
            func.avg(Property.cap_rate).label("avg_cap_rate"),
            func.count(Property.id).label("comp_count"),
        ).where(*market_comps_filters if market_comps_filters else [True])
    )
    market_row = market_comps_result.fetchone()

    # Get current property metrics
    current_rent = _decimal_to_float(property_obj.avg_rent_per_unit)
    current_occupancy = _decimal_to_float(property_obj.occupancy_rate)
    current_cap_rate = _decimal_to_float(property_obj.cap_rate)
    current_noi = _decimal_to_float(property_obj.noi)

    # Get market averages
    market_avg_rent = _decimal_to_float(market_row.avg_rent) if market_row else None
    market_avg_occupancy = _decimal_to_float(market_row.avg_occupancy) if market_row else None
    market_avg_cap_rate = _decimal_to_float(market_row.avg_cap_rate) if market_row else None
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
            "current_occupancy": round(current_occupancy, 1) if current_occupancy else None,
            "current_cap_rate": round(current_cap_rate, 2) if current_cap_rate else None,
            "current_noi": round(current_noi, 2) if current_noi else None,
            # Historical growth rates would need time-series data
            "ytd_rent_growth": None,  # Would need historical rent data
            "ytd_noi_growth": None,  # Would need historical NOI data
            "avg_occupancy_12m": round(current_occupancy, 1) if current_occupancy else None,
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
            "market_avg_occupancy": round(market_avg_occupancy, 1) if market_avg_occupancy else None,
            "market_avg_cap_rate": round(market_avg_cap_rate, 2) if market_avg_cap_rate else None,
            "comparable_count": comp_count,
        },
    }
