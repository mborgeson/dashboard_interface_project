"""
Market data endpoints for market analytics and comparables.
"""

from fastapi import APIRouter, Query

from app.schemas.market_data import (
    ComparablesResponse,
    MarketOverviewResponse,
    MarketTrendsResponse,
    SubmarketsResponse,
)
from app.services.market_data import market_data_service

router = APIRouter()


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview():
    """
    Get market overview with MSA statistics and economic indicators.

    Returns:
        MSA overview data including population, employment, GDP,
        and key economic indicators for the Phoenix MSA.
    """
    return market_data_service.get_market_overview()


@router.get("/submarkets", response_model=SubmarketsResponse)
async def get_submarkets():
    """
    Get submarket breakdown with performance metrics.

    Returns:
        List of submarkets with rent, occupancy, cap rate,
        inventory, and absorption metrics.
    """
    return market_data_service.get_submarkets()


@router.get("/trends", response_model=MarketTrendsResponse)
async def get_market_trends(
    period_months: int = Query(12, ge=1, le=36, description="Number of months of trend data"),
):
    """
    Get market trends over time.

    Args:
        period_months: Number of months of historical data (1-36, default 12)

    Returns:
        Monthly trend data including rent growth, occupancy,
        cap rates, and economic metrics.
    """
    return market_data_service.get_market_trends(period_months=period_months)


@router.get("/comparables", response_model=ComparablesResponse)
async def get_comparables(
    property_id: str | None = Query(None, description="Reference property ID"),
    submarket: str | None = Query(None, description="Filter to specific submarket"),
    radius_miles: float = Query(5.0, ge=0.5, le=25.0, description="Search radius in miles"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of comparables"),
):
    """
    Get property comparables for market analysis.

    Args:
        property_id: Reference property to find comparables for
        submarket: Filter to specific submarket
        radius_miles: Search radius in miles (0.5-25)
        limit: Maximum number of results (1-50)

    Returns:
        List of comparable properties with sale and performance data.
    """
    return market_data_service.get_comparables(
        property_id=property_id,
        submarket=submarket,
        radius_miles=radius_miles,
        limit=limit,
    )
