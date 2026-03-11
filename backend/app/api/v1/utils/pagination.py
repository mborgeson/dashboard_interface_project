"""
Shared pagination parameters for API endpoints.

Provides a reusable ``PaginationParams`` dependency that standardizes
skip/limit pagination across all list endpoints.  The default page size
is 50, capped at 200.

Usage in an endpoint::

    from app.api.v1.utils.pagination import PaginationParams

    @router.get("/items")
    async def list_items(pagination: PaginationParams = Depends()):
        items = await crud.get_multi(db, skip=pagination.skip, limit=pagination.limit)

NOTE: The dashboard properties endpoint previously returned up to 1,000
records.  With this utility the default is 50 (max 200).  Existing
clients that relied on the unbounded response must pass an explicit
``limit`` query parameter to retrieve more records.
"""

from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    """Reusable pagination query parameters.

    Attributes:
        skip: Number of records to skip (offset). Must be >= 0.
        limit: Maximum number of records to return. Clamped to [1, 200].
    """

    skip: int = Query(0, ge=0, description="Number of records to skip")
    limit: int = Query(50, ge=1, le=200, description="Max records to return")
