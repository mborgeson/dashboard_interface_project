"""
Market data endpoints package for market analytics and comparables.

Sub-modules:
- overview.py: Market overview, trends, and submarket endpoints
- sales.py: Property comparables endpoints
- refresh.py: Admin-only FRED data refresh endpoint
- _service.py: Shared service reference (mock target for tests)
"""

from fastapi import APIRouter, Depends

from app.core.permissions import require_viewer

# Re-export market_data_service so that the existing test mock target
# ``app.api.v1.endpoints.market_data.market_data_service`` still resolves.
from ._service import market_data_service  # noqa: F401
from .overview import router as overview_router
from .refresh import router as refresh_router
from .sales import router as sales_router

# Create main router that combines all sub-routers.
# The require_viewer dependency applies to all routes in this package,
# matching the original market_data.py behavior.
router = APIRouter(dependencies=[Depends(require_viewer)])

router.include_router(refresh_router)
router.include_router(overview_router)
router.include_router(sales_router)

__all__ = ["router", "market_data_service"]
