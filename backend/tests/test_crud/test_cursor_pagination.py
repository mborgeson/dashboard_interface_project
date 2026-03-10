"""Tests for cursor-based pagination in CRUDBase.

Validates:
- First page (no cursor) returns items + next_cursor
- Navigating forward with next_cursor
- Navigating backward with prev direction
- Ascending and descending order
- Pagination with filter conditions
- Empty table returns empty results
- Invalid cursor raises ValueError
- Cursor encode/decode round-trip
- Total count inclusion
"""

from decimal import Decimal

import pytest
import pytest_asyncio

from app.crud.crud_deal import deal as deal_crud
from app.models import Deal, DealStage
from app.schemas.pagination import (
    CursorPaginationParams,
    decode_cursor,
    encode_cursor,
)


# ============================================================================
# Cursor encode/decode unit tests (no DB)
# ============================================================================


class TestCursorEncodeDecode:
    """Test cursor serialization round-trip."""

    def test_roundtrip_int_id(self):
        cursor = encode_cursor(42, 7)
        sort_val, row_id = decode_cursor(cursor)
        assert sort_val == 42
        assert row_id == 7

    def test_roundtrip_string_value(self):
        cursor = encode_cursor("some_name", 99)
        sort_val, row_id = decode_cursor(cursor)
        assert sort_val == "some_name"
        assert row_id == 99

    def test_roundtrip_none_value(self):
        cursor = encode_cursor(None, 5)
        sort_val, row_id = decode_cursor(cursor)
        assert sort_val is None
        assert row_id == 5

    def test_invalid_cursor_raises(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-a-valid-cursor!!!")

    def test_empty_string_cursor_raises(self):
        with pytest.raises(ValueError):
            decode_cursor("")


# ============================================================================
# Database integration tests
# ============================================================================


@pytest_asyncio.fixture
async def cursor_deals(db_session, test_user):
    """Create 7 deals for cursor pagination testing, with distinct names for deterministic ordering."""
    deals = []
    stages = [
        DealStage.INITIAL_REVIEW,
        DealStage.INITIAL_REVIEW,
        DealStage.INITIAL_REVIEW,
        DealStage.ACTIVE_REVIEW,
        DealStage.ACTIVE_REVIEW,
        DealStage.UNDER_CONTRACT,
        DealStage.CLOSED,
    ]
    for i, stage in enumerate(stages):
        deal = Deal(
            name=f"Cursor Deal {chr(65 + i)}",  # A, B, C, D, E, F, G
            deal_type="acquisition",
            stage=stage,
            stage_order=i,
            assigned_user_id=test_user.id,
            asking_price=Decimal(str(1_000_000 * (i + 1))),
            priority="high" if i < 3 else "medium",
        )
        db_session.add(deal)
        deals.append(deal)

    await db_session.commit()
    for deal in deals:
        await db_session.refresh(deal)
    return deals


@pytest.mark.asyncio
async def test_cursor_first_page_desc(db_session, cursor_deals):
    """First page (no cursor) returns items ordered by id DESC."""
    params = CursorPaginationParams(cursor=None, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    assert len(result.items) == 3
    assert result.has_more is True
    assert result.next_cursor is not None
    assert result.prev_cursor is None  # First page
    assert result.total == 7
    # IDs should be descending
    ids = [item.id for item in result.items]
    assert ids == sorted(ids, reverse=True)


@pytest.mark.asyncio
async def test_cursor_first_page_asc(db_session, cursor_deals):
    """First page ascending order."""
    params = CursorPaginationParams(cursor=None, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="name", order_desc=False
    )
    assert len(result.items) == 3
    assert result.has_more is True
    names = [item.name for item in result.items]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_cursor_navigate_forward(db_session, cursor_deals):
    """Navigate through all pages using next_cursor."""
    all_ids: list[int] = []

    params = CursorPaginationParams(cursor=None, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    all_ids.extend(item.id for item in result.items)

    # Second page
    assert result.next_cursor is not None
    params = CursorPaginationParams(cursor=result.next_cursor, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    all_ids.extend(item.id for item in result.items)
    assert len(result.items) == 3

    # Third page (last)
    assert result.next_cursor is not None
    params = CursorPaginationParams(cursor=result.next_cursor, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    all_ids.extend(item.id for item in result.items)
    assert len(result.items) == 1  # 7 % 3 = 1

    # Should have seen all 7 deals
    assert len(all_ids) == 7
    # All unique
    assert len(set(all_ids)) == 7
    # Strictly descending across all pages
    assert all_ids == sorted(all_ids, reverse=True)


@pytest.mark.asyncio
async def test_cursor_navigate_backward(db_session, cursor_deals):
    """Navigate backward using prev direction."""
    # Get first page
    params = CursorPaginationParams(cursor=None, limit=3, direction="next")
    page1 = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )

    # Get second page
    params = CursorPaginationParams(cursor=page1.next_cursor, limit=3, direction="next")
    page2 = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )

    # Go back using prev_cursor from page2
    assert page2.prev_cursor is not None
    params = CursorPaginationParams(cursor=page2.prev_cursor, limit=3, direction="prev")
    page_back = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )

    # Should get back the same items as page 1
    page1_ids = [item.id for item in page1.items]
    back_ids = [item.id for item in page_back.items]
    assert back_ids == page1_ids


@pytest.mark.asyncio
async def test_cursor_with_conditions(db_session, cursor_deals):
    """Cursor pagination respects filter conditions."""
    params = CursorPaginationParams(cursor=None, limit=10, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session,
        params=params,
        order_by="id",
        order_desc=True,
        conditions=[Deal.stage == DealStage.INITIAL_REVIEW],
    )
    assert result.total == 3
    assert len(result.items) == 3
    for item in result.items:
        assert item.stage == DealStage.INITIAL_REVIEW


@pytest.mark.asyncio
async def test_cursor_empty_table(db_session):
    """Cursor pagination on empty table returns empty results."""
    params = CursorPaginationParams(cursor=None, limit=10, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    assert result.items == []
    assert result.total == 0
    assert result.next_cursor is None
    assert result.prev_cursor is None
    assert result.has_more is False


@pytest.mark.asyncio
async def test_cursor_invalid_cursor_raises(db_session, cursor_deals):
    """Invalid cursor string raises ValueError."""
    params = CursorPaginationParams(cursor="bad-cursor", limit=3, direction="next")
    with pytest.raises(ValueError, match="Invalid cursor"):
        await deal_crud.get_cursor_paginated(
            db_session, params=params, order_by="id", order_desc=True
        )


@pytest.mark.asyncio
async def test_cursor_without_total(db_session, cursor_deals):
    """include_total=False skips the count query."""
    params = CursorPaginationParams(cursor=None, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session,
        params=params,
        order_by="id",
        order_desc=True,
        include_total=False,
    )
    assert len(result.items) == 3
    assert result.total is None


@pytest.mark.asyncio
async def test_cursor_limit_one(db_session, cursor_deals):
    """Limit=1 pages through one item at a time."""
    params = CursorPaginationParams(cursor=None, limit=1, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    assert len(result.items) == 1
    assert result.has_more is True
    assert result.next_cursor is not None


@pytest.mark.asyncio
async def test_cursor_exact_page_boundary(db_session, cursor_deals):
    """When limit exactly divides total, last page has_more=False."""
    # 7 deals, limit=7 should give exactly one full page
    params = CursorPaginationParams(cursor=None, limit=7, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="id", order_desc=True
    )
    assert len(result.items) == 7
    assert result.has_more is False


@pytest.mark.asyncio
async def test_cursor_sort_by_name_asc(db_session, cursor_deals):
    """Sorting by name ascending produces alphabetical order across pages."""
    all_names: list[str] = []

    params = CursorPaginationParams(cursor=None, limit=3, direction="next")
    result = await deal_crud.get_cursor_paginated(
        db_session, params=params, order_by="name", order_desc=False
    )
    all_names.extend(item.name for item in result.items)

    while result.next_cursor:
        params = CursorPaginationParams(cursor=result.next_cursor, limit=3, direction="next")
        result = await deal_crud.get_cursor_paginated(
            db_session, params=params, order_by="name", order_desc=False
        )
        all_names.extend(item.name for item in result.items)

    assert len(all_names) == 7
    assert all_names == sorted(all_names)
