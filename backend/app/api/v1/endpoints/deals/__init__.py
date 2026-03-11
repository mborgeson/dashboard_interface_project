"""
Deal endpoints package for pipeline management and Kanban board operations.

Sub-modules:
- crud.py: CRUD endpoints (list, get, create, update, delete, restore)
- pipeline.py: Kanban/pipeline endpoints (stages, move, board)
- comparison.py: Deal comparison endpoints
- activity.py: Deal activity/timeline and watchlist endpoints
- analytics.py: Deal analytics/proforma metrics endpoints
- enrichment.py: Shared extraction enrichment helpers
"""

from fastapi import APIRouter

from .activity import router as activity_router
from .analytics import router as analytics_router
from .comparison import router as comparison_router
from .crud import router as crud_router
from .enrichment import (
    EXTRACTION_CACHE_PREFIX,
    PROFORMA_FIELDS,
    enrich_deals_with_extraction,
    invalidate_extraction_enrichment_cache,
)
from .pipeline import router as pipeline_router

# Create main router that combines all sub-routers.
# Order matters: routes with fixed paths (e.g., /kanban, /compare, /cursor)
# must be included BEFORE routes with path parameters (e.g., /{deal_id}).
# FastAPI matches routes in registration order, so /{deal_id} would
# swallow /kanban if registered first.
router = APIRouter()

# Pipeline routes first (includes /kanban which must precede /{deal_id})
router.include_router(pipeline_router)
# Comparison routes (/compare must precede /{deal_id})
router.include_router(comparison_router)
# CRUD routes (includes /, /cursor, /{deal_id}, etc.)
router.include_router(crud_router)
# Activity routes (all under /{deal_id}/activity*, /{deal_id}/watchlist*)
router.include_router(activity_router)
# Analytics routes (/{deal_id}/proforma-returns)
router.include_router(analytics_router)

__all__ = [
    "router",
    "enrich_deals_with_extraction",
    "invalidate_extraction_enrichment_cache",
    "EXTRACTION_CACHE_PREFIX",
    "PROFORMA_FIELDS",
]
