"""
Cursor-based pagination schemas for API request/response validation.

Cursor pagination uses an opaque, base64-encoded cursor string (encoding the
sort-column value + row ID) to fetch the next/previous page.  This avoids the
O(n) offset scans of traditional page-based pagination and provides stable
results when rows are inserted or deleted between requests.
"""

import base64
import json
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Request parameters
# ---------------------------------------------------------------------------


class CursorPaginationParams(BaseModel):
    """Query parameters accepted by cursor-paginated endpoints.

    Attributes:
        cursor: Opaque cursor string from a previous response.  ``None``
            means "start from the beginning".
        limit: Maximum number of items to return (1–100).
        direction: ``"next"`` (default) fetches items *after* the cursor,
            ``"prev"`` fetches items *before* the cursor.
    """

    cursor: str | None = Field(
        None,
        description="Opaque cursor from a previous paginated response",
    )
    limit: int = Field(20, ge=1, le=100, description="Items per page (1–100)")
    direction: str = Field(
        "next",
        pattern="^(next|prev)$",
        description="Pagination direction: 'next' or 'prev'",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cursor": None,
                "limit": 20,
                "direction": "next",
            }
        }
    )


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for cursor-paginated list responses.

    Attributes:
        items: The page of results.
        next_cursor: Cursor to fetch the next page (``None`` when at the end).
        prev_cursor: Cursor to fetch the previous page (``None`` on first page).
        has_more: Whether more items exist in the ``direction`` of travel.
        total: Total count of matching records (optional; may be ``None`` for
            performance reasons on very large tables).
    """

    items: list[T]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_more: bool = False
    total: int | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Cursor encode / decode helpers
# ---------------------------------------------------------------------------


def encode_cursor(sort_value: Any, row_id: int) -> str:
    """Encode a (sort_value, row_id) pair into an opaque cursor string.

    The cursor is a base64-encoded JSON array ``[sort_value, row_id]``.
    """
    payload = json.dumps([_serialize(sort_value), row_id], default=str)
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[Any, int]:
    """Decode an opaque cursor string back into ``(sort_value, row_id)``.

    Raises ``ValueError`` for malformed cursors so the calling endpoint
    can return a 400 response.
    """
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        sort_value, row_id = json.loads(payload)
        return sort_value, int(row_id)
    except Exception as exc:
        raise ValueError(f"Invalid cursor: {exc}") from exc


def _serialize(value: Any) -> Any:
    """Convert a value to a JSON-safe primitive for cursor encoding."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # Decimal, float, int, str all serialize cleanly via json.dumps default=str
    return value
