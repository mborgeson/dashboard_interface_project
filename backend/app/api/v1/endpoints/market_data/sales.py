"""
Market sales comp endpoints — property comparables for market analysis.

Note: market_data_service is accessed via sys.modules to support test mocking.
Tests patch ``app.api.v1.endpoints.market_data.market_data_service``, so all
sub-modules must resolve the service through the package namespace.
"""

import sys

from fastapi import APIRouter, Query

from app.schemas.market_data import ComparablesResponse

router = APIRouter()


def _svc():
    """Resolve market_data_service through the package namespace for mock support."""
    return sys.modules["app.api.v1.endpoints.market_data"].market_data_service


@router.get("/comparables", response_model=ComparablesResponse)
async def get_comparables(
    property_id: str | None = Query(None, description="Reference property ID"),
    submarket: str | None = Query(None, description="Filter to specific submarket"),
    radius_miles: float = Query(
        5.0, ge=0.5, le=25.0, description="Search radius in miles"
    ),
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
    return await _svc().get_comparables(
        property_id=property_id,
        submarket=submarket,
        radius_miles=radius_miles,
        limit=limit,
    )
