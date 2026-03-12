"""
PostgreSQL integration tests for PG-specific query features (T-DEBT-015).

These tests exercise ILIKE search, numeric/date range filters, pagination,
JSON columns, and enum queries — all features that behave differently (or
don't exist) on SQLite.

Every test is marked ``@pytest.mark.pg`` and is skipped when
``TEST_DATABASE_URL`` is not set.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_pg import pg_available

pytestmark = [pytest.mark.pg, pg_available]


# ---------------------------------------------------------------------------
# Helper: bulk-insert properties
# ---------------------------------------------------------------------------


async def _seed_properties(session: AsyncSession, count: int = 20) -> list:
    """Insert ``count`` properties with varied data for filter testing."""
    from app.models import Property

    cities = ["Phoenix", "Tempe", "Mesa", "Scottsdale", "Chandler"]
    props = []
    for i in range(count):
        prop = Property(
            name=f"Integration Property {i:03d}",
            property_type="multifamily",
            address=f"{100 + i} Test Blvd",
            city=cities[i % len(cities)],
            state="AZ",
            zip_code=f"8{5000 + i}",
            market="Phoenix Metro",
            year_built=1980 + i,
            total_units=50 + i * 5,
            total_sf=30000 + i * 2000,
            purchase_price=Decimal(str(5_000_000 + i * 500_000)),
            cap_rate=Decimal(str(round(4.5 + i * 0.25, 3))),
            occupancy_rate=Decimal(str(round(88.0 + i * 0.5, 2))),
        )
        session.add(prop)
        props.append(prop)

    await session.commit()
    for p in props:
        await session.refresh(p)
    return props


async def _seed_deals(session: AsyncSession, user_id: int, count: int = 15) -> list:
    """Insert ``count`` deals with varied stages and prices."""
    from app.models import Deal, DealStage

    stages = list(DealStage)
    props = []
    for i in range(count):
        deal = Deal(
            name=f"Integration Deal {i:03d}",
            deal_type="acquisition",
            stage=stages[i % len(stages)],
            stage_order=i,
            assigned_user_id=user_id,
            asking_price=Decimal(str(8_000_000 + i * 1_000_000)),
            offer_price=Decimal(str(7_500_000 + i * 900_000)),
            projected_irr=Decimal(str(round(12.0 + i * 0.5, 3))),
            priority=["low", "medium", "high", "urgent"][i % 4],
            initial_contact_date=date(2026, 1, 1) + timedelta(days=i * 7),
            source=["CBRE", "JLL", "Marcus & Millichap", "Cushman & Wakefield"][i % 4],
        )
        session.add(deal)
        props.append(deal)

    await session.commit()
    for d in props:
        await session.refresh(d)
    return props


# ---------------------------------------------------------------------------
# ILIKE search
# ---------------------------------------------------------------------------


class TestILIKESearch:
    """Test case-insensitive LIKE via PostgreSQL ILIKE."""

    async def test_ilike_case_insensitive_property_name(self, pg_session):
        """ILIKE should match regardless of case."""
        from app.models import Property

        await _seed_properties(pg_session, count=5)

        # Search with different case
        pattern = "%integration property%"
        result = await pg_session.execute(
            select(Property).where(Property.name.ilike(pattern))
        )
        found = result.scalars().all()
        assert len(found) == 5

        # Upper case search
        pattern_upper = "%INTEGRATION PROPERTY%"
        result = await pg_session.execute(
            select(Property).where(Property.name.ilike(pattern_upper))
        )
        found_upper = result.scalars().all()
        assert len(found_upper) == 5

    async def test_ilike_partial_match(self, pg_session):
        """ILIKE should support partial pattern matching."""
        from app.models import Property

        await _seed_properties(pg_session, count=10)

        # Match properties in specific city
        result = await pg_session.execute(
            select(Property).where(Property.city.ilike("%phoe%"))
        )
        phoenix_props = result.scalars().all()
        # Every 5th property is Phoenix (indices 0, 5)
        assert len(phoenix_props) == 2

    async def test_apply_search_filter_multi_column(self, pg_session):
        """apply_search_filter should search across multiple columns."""
        from app.api.v1.utils.filters import apply_search_filter
        from app.models import Property

        await _seed_properties(pg_session, count=10)

        stmt = select(Property)
        stmt = apply_search_filter(stmt, "Tempe", [Property.name, Property.city])
        result = await pg_session.execute(stmt)
        found = result.scalars().all()

        # Should find properties where city='Tempe' (indices 1, 6)
        assert len(found) >= 2
        assert all("Tempe" in p.city or "Tempe" in p.name for p in found)

    async def test_ilike_no_results(self, pg_session):
        """ILIKE with non-matching pattern should return empty."""
        from app.models import Property

        await _seed_properties(pg_session, count=5)

        result = await pg_session.execute(
            select(Property).where(Property.name.ilike("%nonexistent xyz%"))
        )
        assert result.scalars().all() == []


# ---------------------------------------------------------------------------
# Numeric range filters
# ---------------------------------------------------------------------------


class TestNumericRangeFilters:
    """Test numeric range queries under PG."""

    async def test_cap_rate_range_filter(self, pg_session):
        """Filter properties by cap_rate range."""
        from app.models import Property

        props = await _seed_properties(pg_session, count=10)

        min_cap = Decimal("5.0")
        max_cap = Decimal("7.0")
        result = await pg_session.execute(
            select(Property).where(
                Property.cap_rate >= min_cap,
                Property.cap_rate <= max_cap,
            )
        )
        filtered = result.scalars().all()

        # Verify all returned properties are within range
        for p in filtered:
            assert min_cap <= p.cap_rate <= max_cap

    async def test_purchase_price_min_filter(self, pg_session):
        """Filter properties with purchase_price above a threshold."""
        from app.models import Property

        await _seed_properties(pg_session, count=10)

        threshold = Decimal("8000000")
        result = await pg_session.execute(
            select(Property).where(Property.purchase_price >= threshold)
        )
        filtered = result.scalars().all()

        for p in filtered:
            assert p.purchase_price >= threshold

    async def test_apply_numeric_range_filter_helper(self, pg_session):
        """apply_numeric_range_filter should correctly bound queries."""
        from app.api.v1.utils.filters import apply_numeric_range_filter
        from app.models import Property

        await _seed_properties(pg_session, count=20)

        stmt = select(Property)
        stmt = apply_numeric_range_filter(
            stmt, Property.year_built, min_val=1990, max_val=1995
        )
        result = await pg_session.execute(stmt)
        filtered = result.scalars().all()

        for p in filtered:
            assert 1990 <= p.year_built <= 1995

    async def test_total_units_filter(self, pg_session):
        """Filter properties by total_units range."""
        from app.models import Property

        await _seed_properties(pg_session, count=20)

        result = await pg_session.execute(
            select(Property).where(
                Property.total_units >= 80,
                Property.total_units <= 120,
            )
        )
        filtered = result.scalars().all()
        for p in filtered:
            assert 80 <= p.total_units <= 120


# ---------------------------------------------------------------------------
# Date range filters
# ---------------------------------------------------------------------------


class TestDateRangeFilters:
    """Test date range queries under PG."""

    async def test_deal_initial_contact_date_range(self, pg_session, pg_user):
        """Filter deals by initial_contact_date range."""
        from app.models import Deal

        deals = await _seed_deals(pg_session, pg_user.id, count=15)

        start = date(2026, 1, 15)
        end = date(2026, 3, 1)
        result = await pg_session.execute(
            select(Deal).where(
                Deal.initial_contact_date >= start,
                Deal.initial_contact_date <= end,
            )
        )
        filtered = result.scalars().all()
        for d in filtered:
            assert start <= d.initial_contact_date <= end

    async def test_apply_date_range_filter_helper(self, pg_session, pg_user):
        """apply_date_range_filter should work with PG date columns."""
        from app.api.v1.utils.filters import apply_date_range_filter
        from app.models import Deal

        await _seed_deals(pg_session, pg_user.id, count=10)

        stmt = select(Deal)
        stmt = apply_date_range_filter(
            stmt,
            Deal.initial_contact_date,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 2, 1),
        )
        result = await pg_session.execute(stmt)
        filtered = result.scalars().all()

        for d in filtered:
            assert date(2026, 1, 1) <= d.initial_contact_date <= date(2026, 2, 1)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    """Test LIMIT/OFFSET pagination with real data volumes."""

    async def test_offset_limit_basic(self, pg_session):
        """LIMIT + OFFSET should page through results correctly."""
        from app.models import Property

        total = 25
        await _seed_properties(pg_session, count=total)

        page_size = 10

        # Page 1
        result = await pg_session.execute(
            select(Property).order_by(Property.id).limit(page_size).offset(0)
        )
        page1 = result.scalars().all()
        assert len(page1) == page_size

        # Page 2
        result = await pg_session.execute(
            select(Property).order_by(Property.id).limit(page_size).offset(10)
        )
        page2 = result.scalars().all()
        assert len(page2) == page_size

        # Page 3 (partial)
        result = await pg_session.execute(
            select(Property).order_by(Property.id).limit(page_size).offset(20)
        )
        page3 = result.scalars().all()
        assert len(page3) == total - 20

        # No overlap
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        page3_ids = {p.id for p in page3}
        assert page1_ids.isdisjoint(page2_ids)
        assert page2_ids.isdisjoint(page3_ids)

    async def test_count_with_filter(self, pg_session):
        """COUNT(*) with filters should return correct totals for pagination metadata."""
        from app.models import Property

        await _seed_properties(pg_session, count=20)

        result = await pg_session.execute(
            select(func.count()).select_from(Property).where(Property.city == "Phoenix")
        )
        count = result.scalar()
        assert count == 4  # indices 0, 5, 10, 15

    async def test_pagination_with_sorting(self, pg_session, pg_user):
        """Pagination should respect ORDER BY across pages."""
        from app.models import Deal

        await _seed_deals(pg_session, pg_user.id, count=20)

        # All deals ordered by asking_price DESC
        result = await pg_session.execute(
            select(Deal).order_by(Deal.asking_price.desc())
        )
        all_deals = result.scalars().all()

        # First page
        result = await pg_session.execute(
            select(Deal).order_by(Deal.asking_price.desc()).limit(5).offset(0)
        )
        page1 = result.scalars().all()

        assert page1[0].asking_price == all_deals[0].asking_price
        assert page1[-1].asking_price == all_deals[4].asking_price


# ---------------------------------------------------------------------------
# Enum queries
# ---------------------------------------------------------------------------


class TestEnumQueries:
    """Test SQLAlchemy StrEnum queries under PG."""

    async def test_filter_deals_by_stage(self, pg_session, pg_user):
        """Filtering by DealStage enum should work correctly."""
        from app.models import Deal, DealStage

        await _seed_deals(pg_session, pg_user.id, count=12)

        result = await pg_session.execute(
            select(Deal).where(Deal.stage == DealStage.ACTIVE_REVIEW)
        )
        active = result.scalars().all()

        for d in active:
            assert d.stage == DealStage.ACTIVE_REVIEW

    async def test_filter_deals_by_multiple_stages(self, pg_session, pg_user):
        """IN query with multiple enum values should work."""
        from app.models import Deal, DealStage

        await _seed_deals(pg_session, pg_user.id, count=12)

        target_stages = [DealStage.INITIAL_REVIEW, DealStage.CLOSED]
        result = await pg_session.execute(
            select(Deal).where(Deal.stage.in_(target_stages))
        )
        filtered = result.scalars().all()

        for d in filtered:
            assert d.stage in target_stages


# ---------------------------------------------------------------------------
# JSON column queries
# ---------------------------------------------------------------------------


class TestJSONColumns:
    """Test JSON column storage and retrieval under PG."""

    async def test_property_json_amenities(self, pg_session):
        """JSON amenities column should store and retrieve dicts."""
        from app.models import Property

        amenities = {
            "pool": True,
            "gym": True,
            "parking": "covered",
            "units_breakdown": {"studio": 10, "1br": 30, "2br": 20},
        }

        prop = Property(
            name="JSON Test Property",
            property_type="multifamily",
            address="500 JSON Ave",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            total_units=60,
            total_sf=50000,
            amenities=amenities,
        )
        pg_session.add(prop)
        await pg_session.commit()
        await pg_session.refresh(prop)

        assert prop.amenities is not None
        assert prop.amenities["pool"] is True
        assert prop.amenities["units_breakdown"]["1br"] == 30

    async def test_deal_json_tags(self, pg_session, pg_user):
        """JSON tags column should store and retrieve lists."""
        from app.models import Deal, DealStage

        tags = ["value-add", "phoenix-msa", "100+units"]

        deal = Deal(
            name="Tagged Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="high",
            tags=tags,
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.tags == tags
        assert "value-add" in deal.tags

    async def test_deal_json_custom_fields(self, pg_session, pg_user):
        """JSON custom_fields column should handle nested structures."""
        from app.models import Deal, DealStage

        custom = {
            "lender_contacts": [
                {"name": "John", "company": "Wells Fargo"},
                {"name": "Jane", "company": "JPMorgan"},
            ],
            "due_diligence_items": {"phase1": "complete", "phase2": "pending"},
        }

        deal = Deal(
            name="Custom Fields Deal",
            deal_type="acquisition",
            stage=DealStage.ACTIVE_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="medium",
            custom_fields=custom,
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.custom_fields["lender_contacts"][0]["company"] == "Wells Fargo"
        assert deal.custom_fields["due_diligence_items"]["phase1"] == "complete"


# ---------------------------------------------------------------------------
# Aggregation queries
# ---------------------------------------------------------------------------


class TestAggregationQueries:
    """Test aggregate functions under PG."""

    async def test_avg_cap_rate_by_city(self, pg_session):
        """AVG() grouped by city should produce correct results."""
        from app.models import Property

        await _seed_properties(pg_session, count=10)

        result = await pg_session.execute(
            select(
                Property.city,
                func.avg(Property.cap_rate).label("avg_cap"),
                func.count().label("count"),
            )
            .group_by(Property.city)
            .order_by(Property.city)
        )
        rows = result.all()

        # Should have up to 5 cities
        assert len(rows) >= 1
        for city, avg_cap, count in rows:
            assert city is not None
            assert avg_cap is not None
            assert count > 0

    async def test_sum_asking_price_by_stage(self, pg_session, pg_user):
        """SUM() asking_price grouped by stage should work."""
        from app.models import Deal

        await _seed_deals(pg_session, pg_user.id, count=12)

        result = await pg_session.execute(
            select(
                Deal.stage,
                func.sum(Deal.asking_price).label("total_ask"),
                func.count().label("deal_count"),
            ).group_by(Deal.stage)
        )
        rows = result.all()

        total_sum = sum(row.total_ask for row in rows if row.total_ask)
        assert total_sum > 0

    async def test_max_min_purchase_price(self, pg_session):
        """MAX/MIN on Numeric columns should return correct values."""
        from app.models import Property

        props = await _seed_properties(pg_session, count=10)

        result = await pg_session.execute(
            select(
                func.min(Property.purchase_price).label("min_price"),
                func.max(Property.purchase_price).label("max_price"),
            )
        )
        row = result.one()

        expected_min = min(p.purchase_price for p in props)
        expected_max = max(p.purchase_price for p in props)
        assert row.min_price == expected_min
        assert row.max_price == expected_max
