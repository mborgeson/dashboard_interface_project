"""Tests for shared pagination and filter utilities.

Tests cover:
- PaginationParams default values and constraints
- parse_csv_list edge cases
- apply_numeric_range_filter with SQLAlchemy statements
- apply_date_range_filter with SQLAlchemy statements
- apply_search_filter with SQLAlchemy statements
- Dashboard endpoint pagination integration
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.utils.filters import (
    apply_date_range_filter,
    apply_numeric_range_filter,
    apply_search_filter,
    parse_csv_list,
)
from app.api.v1.utils.pagination import PaginationParams
from app.models import Property

# =============================================================================
# PaginationParams Unit Tests
# =============================================================================


class TestPaginationParams:
    """Test PaginationParams dataclass defaults and constraints."""

    def test_default_values(self):
        """Default Query objects have default=0 (skip) and default=50 (limit).

        When PaginationParams is instantiated outside of a FastAPI request,
        the fields are ``Query(...)`` descriptor objects.  We verify their
        defaults instead of comparing to plain int, since FastAPI resolves
        them at request time.
        """
        params = PaginationParams()
        # FastAPI resolves Query descriptors during dependency injection.
        # Outside a request the raw Query objects have a .default attribute.
        skip_val = (
            params.skip.default if hasattr(params.skip, "default") else params.skip
        )
        limit_val = (
            params.limit.default if hasattr(params.limit, "default") else params.limit
        )
        assert skip_val == 0
        assert limit_val == 50

    def test_custom_values(self):
        """Custom skip and limit values are accepted."""
        params = PaginationParams(skip=10, limit=100)
        skip_val = params.skip if isinstance(params.skip, int) else params.skip.default
        limit_val = (
            params.limit if isinstance(params.limit, int) else params.limit.default
        )
        assert skip_val == 10
        assert limit_val == 100


# =============================================================================
# parse_csv_list Tests
# =============================================================================


class TestParseCsvList:
    """Test the parse_csv_list utility."""

    def test_none_returns_empty(self):
        assert parse_csv_list(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_csv_list("") == []

    def test_whitespace_only_returns_empty(self):
        assert parse_csv_list("   ") == []

    def test_single_value(self):
        assert parse_csv_list("Phoenix") == ["Phoenix"]

    def test_multiple_values(self):
        result = parse_csv_list("Phoenix, Tempe, Mesa")
        assert result == ["Phoenix", "Tempe", "Mesa"]

    def test_strips_whitespace(self):
        result = parse_csv_list("  Phoenix ,  Tempe  ,Mesa  ")
        assert result == ["Phoenix", "Tempe", "Mesa"]

    def test_filters_empty_entries(self):
        result = parse_csv_list("Phoenix,,Tempe,,,Mesa")
        assert result == ["Phoenix", "Tempe", "Mesa"]

    def test_comma_only(self):
        assert parse_csv_list(",,,") == []


# =============================================================================
# apply_numeric_range_filter Tests
# =============================================================================


class TestApplyNumericRangeFilter:
    """Test numeric range filter application to SQLAlchemy statements."""

    def test_no_bounds_returns_unchanged(self):
        """Neither min nor max modifies the statement."""
        stmt = select(Property)
        result = apply_numeric_range_filter(
            stmt, Property.total_units, min_val=None, max_val=None
        )
        # Should be the same object (no WHERE added)
        assert str(result) == str(stmt)

    def test_min_only(self):
        """Only min_val adds a >= condition."""
        stmt = select(Property)
        result = apply_numeric_range_filter(
            stmt, Property.total_units, min_val=50, max_val=None
        )
        compiled = str(result)
        assert ">=" in compiled

    def test_max_only(self):
        """Only max_val adds a <= condition."""
        stmt = select(Property)
        result = apply_numeric_range_filter(
            stmt, Property.total_units, min_val=None, max_val=200
        )
        compiled = str(result)
        assert "<=" in compiled

    def test_both_bounds(self):
        """Both min and max add two conditions."""
        stmt = select(Property)
        result = apply_numeric_range_filter(
            stmt, Property.total_units, min_val=50, max_val=200
        )
        compiled = str(result)
        assert ">=" in compiled
        assert "<=" in compiled


# =============================================================================
# apply_date_range_filter Tests
# =============================================================================


class TestApplyDateRangeFilter:
    """Test date range filter application to SQLAlchemy statements."""

    def test_no_dates_returns_unchanged(self):
        stmt = select(Property)
        result = apply_date_range_filter(
            stmt, Property.created_at, date_from=None, date_to=None
        )
        assert str(result) == str(stmt)

    def test_date_from_only(self):
        stmt = select(Property)
        result = apply_date_range_filter(
            stmt, Property.created_at, date_from=date(2025, 1, 1), date_to=None
        )
        compiled = str(result)
        assert ">=" in compiled

    def test_date_to_only(self):
        stmt = select(Property)
        result = apply_date_range_filter(
            stmt, Property.created_at, date_from=None, date_to=date(2025, 12, 31)
        )
        compiled = str(result)
        assert "<=" in compiled


# =============================================================================
# apply_search_filter Tests
# =============================================================================


class TestApplySearchFilter:
    """Test search filter application to SQLAlchemy statements."""

    def test_none_search_returns_unchanged(self):
        stmt = select(Property)
        result = apply_search_filter(stmt, None, [Property.name, Property.city])
        assert str(result) == str(stmt)

    def test_empty_search_returns_unchanged(self):
        stmt = select(Property)
        result = apply_search_filter(stmt, "", [Property.name, Property.city])
        assert str(result) == str(stmt)

    def test_empty_columns_returns_unchanged(self):
        stmt = select(Property)
        result = apply_search_filter(stmt, "test", [])
        assert str(result) == str(stmt)

    def test_search_adds_ilike(self):
        stmt = select(Property)
        result = apply_search_filter(stmt, "Phoenix", [Property.name, Property.city])
        compiled = str(result)
        assert "LIKE" in compiled.upper()


# =============================================================================
# Dashboard Pagination Integration Tests
# =============================================================================


@pytest_asyncio.fixture
async def multiple_properties(db_session: AsyncSession) -> list[Property]:
    """Create multiple test properties for pagination testing."""
    props = []
    for i in range(5):
        prop = Property(
            name=f"Property {i + 1:03d}",
            property_type="multifamily",
            address=f"{100 + i} Test St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            market="Phoenix Metro",
            year_built=2020,
            total_sf=50000,
            total_units=100 + i * 10,
            purchase_price=Decimal("10000000.00"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(prop)
        props.append(prop)

    await db_session.commit()
    for p in props:
        await db_session.refresh(p)
    return props


@pytest.mark.asyncio
async def test_dashboard_default_pagination(
    client, db_session, auth_headers, multiple_properties
):
    """Dashboard endpoint returns paginated results with default limit."""
    # Invalidate cache so our freshly-created test properties are returned
    from app.core.cache import cache

    await cache.invalidate_properties()

    response = await client.get(
        "/api/v1/properties/dashboard",
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    assert "properties" in data
    assert "total" in data
    # total reflects at least our 5 fixture properties
    # (other tests may create additional properties in the shared DB)
    assert data["total"] >= 5
    # Default limit=50, so all fixture properties fit in one page
    assert len(data["properties"]) >= 5


@pytest.mark.asyncio
async def test_dashboard_custom_pagination(
    client, db_session, auth_headers, multiple_properties
):
    """Dashboard endpoint respects skip and limit query params."""
    from app.core.cache import cache

    await cache.invalidate_properties()

    response = await client.get(
        "/api/v1/properties/dashboard",
        params={"skip": 0, "limit": 2},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["properties"]) == 2
    assert data["total"] >= 5  # total is always the full count


@pytest.mark.asyncio
async def test_dashboard_skip_pagination(
    client, db_session, auth_headers, multiple_properties
):
    """Dashboard endpoint skip works correctly."""
    from app.core.cache import cache

    await cache.invalidate_properties()

    response = await client.get(
        "/api/v1/properties/dashboard",
        params={"skip": 3, "limit": 10},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 200
    data = response.json()
    # skip 3 from total — at least our 5 fixture properties exist
    assert len(data["properties"]) >= 2
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_dashboard_limit_max_500(
    client, db_session, auth_headers, multiple_properties
):
    """Dashboard endpoint rejects limit > 500."""
    response = await client.get(
        "/api/v1/properties/dashboard",
        params={"limit": 501},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_dashboard_limit_min_1(
    client, db_session, auth_headers, multiple_properties
):
    """Dashboard endpoint rejects limit < 1."""
    response = await client.get(
        "/api/v1/properties/dashboard",
        params={"limit": 0},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_dashboard_skip_negative(
    client, db_session, auth_headers, multiple_properties
):
    """Dashboard endpoint rejects negative skip."""
    response = await client.get(
        "/api/v1/properties/dashboard",
        params={"skip": -1},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert response.status_code == 422  # Validation error
