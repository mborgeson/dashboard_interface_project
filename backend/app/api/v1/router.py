"""
API v1 router aggregating all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    deals,
    exports,
    extraction,
    monitoring,
    properties,
    users,
)

api_router = APIRouter()


# Health check endpoint (legacy - use /monitoring/health/* for detailed checks)
@api_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "version": "2.0.0"}


# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(deals.router, prefix="/deals", tags=["deals"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
