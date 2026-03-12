"""Tests for CRUDBase pagination, ordering, and filter helpers.

Validates:
- PaginatedResult math (page, per_page, total, pages, has_next, has_prev)
- Empty results handled correctly
- Edge cases (page beyond total, per_page=0, per_page=1)
- Ordering works via get_multi_ordered
- count_where with conditions
- get_paginated end-to-end
"""

from decimal import Decimal

import pytest
import pytest_asyncio

from app.crud.base import CRUDBase, PaginatedResult
from app.crud.crud_deal import deal as deal_crud
from app.models import Deal, DealStage

# ============================================================================
# PaginatedResult unit tests (pure math, no DB)
# ============================================================================


class TestPaginatedResult:
    """Test PaginatedResult container math."""

    def test_single_page(self):
        result = PaginatedResult(items=["a", "b", "c"], total=3, page=1, per_page=10)
        assert result.pages == 1
        assert result.has_next is False
        assert result.has_prev is False

    def test_multiple_pages_first_page(self):
        result = PaginatedResult(items=["a", "b"], total=5, page=1, per_page=2)
        assert result.pages == 3  # ceil(5/2) = 3
        assert result.has_next is True
        assert result.has_prev is False

    def test_multiple_pages_middle_page(self):
        result = PaginatedResult(items=["c", "d"], total=5, page=2, per_page=2)
        assert result.pages == 3
        assert result.has_next is True
        assert result.has_prev is True

    def test_multiple_pages_last_page(self):
        result = PaginatedResult(items=["e"], total=5, page=3, per_page=2)
        assert result.pages == 3
        assert result.has_next is False
        assert result.has_prev is True

    def test_empty_results(self):
        result = PaginatedResult(items=[], total=0, page=1, per_page=10)
        assert result.pages == 0
        assert result.has_next is False
        assert result.has_prev is False
        assert result.total == 0

    def test_per_page_zero_yields_zero_pages(self):
        """per_page=0 is clamped to 1 by get_paginated, but PaginatedResult itself handles 0."""
        result = PaginatedResult(items=[], total=5, page=1, per_page=0)
        assert result.pages == 0

    def test_per_page_one(self):
        result = PaginatedResult(items=["a"], total=5, page=1, per_page=1)
        assert result.pages == 5
        assert result.has_next is True

    def test_page_beyond_total(self):
        result = PaginatedResult(items=[], total=5, page=10, per_page=2)
        assert result.pages == 3
        assert result.has_next is False  # page 10 > pages 3
        assert result.has_prev is True

    def test_exact_division(self):
        result = PaginatedResult(items=["a", "b"], total=6, page=3, per_page=2)
        assert result.pages == 3
        assert result.has_next is False
        assert result.has_prev is True

    def test_to_dict(self):
        result = PaginatedResult(items=["a", "b"], total=5, page=1, per_page=2)
        d = result.to_dict()
        assert d["items"] == ["a", "b"]
        assert d["total"] == 5
        assert d["page"] == 1
        assert d["per_page"] == 2
        assert d["pages"] == 3
        assert d["has_next"] is True
        assert d["has_prev"] is False


# ============================================================================
# Database integration tests
# ============================================================================


@pytest_asyncio.fixture
async def many_deals(db_session, test_user):
    """Create 7 deals across stages for pagination testing."""
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
            name=f"Pagination Deal #{i + 1:04d}",
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
async def test_get_paginated_first_page(db_session, many_deals):
    """get_paginated returns correct first page."""
    result = await deal_crud.get_paginated(
        db_session, page=1, per_page=3, order_by="name", order_desc=False
    )
    assert isinstance(result, PaginatedResult)
    assert len(result.items) == 3
    assert result.total == 7
    assert result.page == 1
    assert result.per_page == 3
    assert result.pages == 3  # ceil(7/3)
    assert result.has_next is True
    assert result.has_prev is False


@pytest.mark.asyncio
async def test_get_paginated_last_page(db_session, many_deals):
    """Last page contains the remainder."""
    result = await deal_crud.get_paginated(
        db_session, page=3, per_page=3, order_by="name", order_desc=False
    )
    assert len(result.items) == 1  # 7 % 3 = 1
    assert result.has_next is False
    assert result.has_prev is True


@pytest.mark.asyncio
async def test_get_paginated_beyond_total(db_session, many_deals):
    """Page beyond total returns empty items but correct metadata."""
    result = await deal_crud.get_paginated(
        db_session, page=99, per_page=3, order_by="name", order_desc=False
    )
    assert len(result.items) == 0
    assert result.total == 7
    assert result.pages == 3


@pytest.mark.asyncio
async def test_get_paginated_empty_table(db_session):
    """Pagination on empty table returns zeros."""
    result = await deal_crud.get_paginated(
        db_session, page=1, per_page=10, order_by="name"
    )
    assert result.items == []
    assert result.total == 0
    assert result.pages == 0
    assert result.has_next is False
    assert result.has_prev is False


@pytest.mark.asyncio
async def test_get_paginated_per_page_clamped(db_session, many_deals):
    """per_page is clamped to minimum of 1."""
    result = await deal_crud.get_paginated(
        db_session, page=1, per_page=0, order_by="name"
    )
    # per_page=0 gets clamped to 1
    assert result.per_page == 1
    assert len(result.items) == 1
    assert result.pages == 7


@pytest.mark.asyncio
async def test_get_paginated_with_conditions(db_session, many_deals):
    """Pagination with filter conditions."""
    result = await deal_crud.get_paginated(
        db_session,
        page=1,
        per_page=10,
        conditions=[Deal.stage == DealStage.INITIAL_REVIEW],
    )
    assert result.total == 3  # 3 initial_review deals
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_get_multi_ordered_default(db_session, many_deals):
    """get_multi_ordered returns items with ordering."""
    items = await deal_crud.get_multi_ordered(
        db_session, skip=0, limit=3, order_by="name", order_desc=False
    )
    assert len(items) == 3
    # Should be alphabetically sorted
    names = [d.name for d in items]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_get_multi_ordered_desc(db_session, many_deals):
    """get_multi_ordered with desc ordering."""
    items = await deal_crud.get_multi_ordered(
        db_session, skip=0, limit=3, order_by="name", order_desc=True
    )
    names = [d.name for d in items]
    assert names == sorted(names, reverse=True)


@pytest.mark.asyncio
async def test_get_multi_ordered_with_conditions(db_session, many_deals):
    """get_multi_ordered respects filter conditions."""
    items = await deal_crud.get_multi_ordered(
        db_session,
        skip=0,
        limit=100,
        conditions=[Deal.priority == "high"],
    )
    assert len(items) == 3
    for item in items:
        assert item.priority == "high"


@pytest.mark.asyncio
async def test_count_where_no_conditions(db_session, many_deals):
    """count_where with no conditions counts all."""
    count = await deal_crud.count_where(db_session)
    assert count == 7


@pytest.mark.asyncio
async def test_count_where_with_conditions(db_session, many_deals):
    """count_where with conditions filters correctly."""
    count = await deal_crud.count_where(
        db_session, conditions=[Deal.stage == DealStage.ACTIVE_REVIEW]
    )
    assert count == 2


@pytest.mark.asyncio
async def test_count_where_empty(db_session):
    """count_where on empty table returns 0."""
    count = await deal_crud.count_where(db_session)
    assert count == 0


@pytest.mark.asyncio
async def test_ordering_with_invalid_column(db_session, many_deals):
    """Invalid order_by column is silently ignored."""
    items = await deal_crud.get_multi_ordered(
        db_session, skip=0, limit=10, order_by="nonexistent_column"
    )
    # Should still return items, just without specific ordering
    assert len(items) == 7


@pytest.mark.asyncio
async def test_get_paginated_to_dict(db_session, many_deals):
    """PaginatedResult.to_dict() works correctly."""
    result = await deal_crud.get_paginated(
        db_session, page=1, per_page=2, order_by="name"
    )
    d = result.to_dict()
    assert d["total"] == 7
    assert d["page"] == 1
    assert d["per_page"] == 2
    assert d["pages"] == 4  # ceil(7/2)
    assert d["has_next"] is True
    assert d["has_prev"] is False
    assert len(d["items"]) == 2
