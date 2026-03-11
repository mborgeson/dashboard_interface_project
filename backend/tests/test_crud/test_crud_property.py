"""Tests for Property CRUD operations.

Covers CRUDProperty:
- _build_property_conditions: filter condition builder
- get_multi_filtered / count_filtered: multi-filter queries
- get_by_market: market-based retrieval
- get_analytics_summary: aggregate statistics
- get_markets: distinct market list
"""

from decimal import Decimal

import pytest

from app.crud.crud_property import property as property_crud
from app.models import Property

# =============================================================================
# Helpers
# =============================================================================


async def _create_property(
    db_session,
    name: str = "Test Property",
    property_type: str = "multifamily",
    city: str = "Phoenix",
    state: str = "AZ",
    market: str = "Phoenix Metro",
    total_units: int = 100,
    year_built: int = 1990,
    cap_rate: Decimal | None = Decimal("6.5"),
    occupancy_rate: Decimal | None = Decimal("95.0"),
    purchase_price: Decimal | None = Decimal("10000000"),
) -> Property:
    """Insert a property directly for testing."""
    prop = Property(
        name=name,
        property_type=property_type,
        address="123 Test St",
        city=city,
        state=state,
        zip_code="85001",
        market=market,
        year_built=year_built,
        total_sf=total_units * 800,
        total_units=total_units,
        purchase_price=purchase_price,
        cap_rate=cap_rate,
        occupancy_rate=occupancy_rate,
    )
    db_session.add(prop)
    await db_session.flush()
    await db_session.refresh(prop)
    return prop


# =============================================================================
# _build_property_conditions
# =============================================================================


class TestBuildPropertyConditions:
    """Tests for _build_property_conditions."""

    def test_no_filters(self):
        conditions = property_crud._build_property_conditions()
        assert conditions == []

    def test_property_type_filter(self):
        conditions = property_crud._build_property_conditions(
            property_type="multifamily"
        )
        assert len(conditions) == 1

    def test_city_filter(self):
        conditions = property_crud._build_property_conditions(city="Phoenix")
        assert len(conditions) == 1

    def test_state_filter(self):
        conditions = property_crud._build_property_conditions(state="AZ")
        assert len(conditions) == 1

    def test_market_filter(self):
        conditions = property_crud._build_property_conditions(
            market="Phoenix Metro"
        )
        assert len(conditions) == 1

    def test_min_units_filter(self):
        conditions = property_crud._build_property_conditions(min_units=50)
        assert len(conditions) == 1

    def test_max_units_filter(self):
        conditions = property_crud._build_property_conditions(max_units=200)
        assert len(conditions) == 1

    def test_units_range(self):
        conditions = property_crud._build_property_conditions(
            min_units=50, max_units=200
        )
        assert len(conditions) == 2

    def test_all_filters(self):
        conditions = property_crud._build_property_conditions(
            property_type="multifamily",
            city="Phoenix",
            state="AZ",
            market="Phoenix Metro",
            min_units=50,
            max_units=200,
        )
        assert len(conditions) == 6


# =============================================================================
# get_multi_filtered / count_filtered
# =============================================================================


class TestGetMultiFiltered:
    """Tests for get_multi_filtered and count_filtered."""

    @pytest.mark.asyncio
    async def test_returns_all_unfiltered(self, db_session):
        """get_multi_filtered returns all properties with no filters."""
        await _create_property(db_session, "A")
        await _create_property(db_session, "B")

        results = await property_crud.get_multi_filtered(db_session)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filters_by_type(self, db_session):
        """get_multi_filtered filters by property_type."""
        await _create_property(db_session, "MF", property_type="multifamily")
        await _create_property(db_session, "Off", property_type="office")

        results = await property_crud.get_multi_filtered(
            db_session, property_type="multifamily"
        )
        assert len(results) == 1
        assert results[0].property_type == "multifamily"

    @pytest.mark.asyncio
    async def test_filters_by_city_case_insensitive(self, db_session):
        """get_multi_filtered city filter is case-insensitive."""
        await _create_property(db_session, "PHX", city="Phoenix")
        await _create_property(db_session, "TUC", city="Tucson")

        results = await property_crud.get_multi_filtered(
            db_session, city="phoenix"
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_filters_by_state_case_insensitive(self, db_session):
        """get_multi_filtered state filter is case-insensitive."""
        await _create_property(db_session, "AZ Prop", state="AZ")
        await _create_property(db_session, "CA Prop", state="CA")

        results = await property_crud.get_multi_filtered(
            db_session, state="az"
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_filters_by_unit_range(self, db_session):
        """get_multi_filtered filters by min/max units."""
        await _create_property(db_session, "Small", total_units=30)
        await _create_property(db_session, "Medium", total_units=100)
        await _create_property(db_session, "Large", total_units=300)

        results = await property_crud.get_multi_filtered(
            db_session, min_units=50, max_units=200
        )
        assert len(results) == 1
        assert results[0].name == "Medium"

    @pytest.mark.asyncio
    async def test_count_filtered_matches(self, db_session):
        """count_filtered returns same count as get_multi_filtered."""
        await _create_property(db_session, "A", city="Phoenix")
        await _create_property(db_session, "B", city="Phoenix")
        await _create_property(db_session, "C", city="Tucson")

        count = await property_crud.count_filtered(db_session, city="Phoenix")
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_filtered_no_filters(self, db_session):
        """count_filtered returns total when no filters."""
        await _create_property(db_session, "A")
        await _create_property(db_session, "B")
        await _create_property(db_session, "C")

        count = await property_crud.count_filtered(db_session)
        assert count == 3

    @pytest.mark.asyncio
    async def test_pagination(self, db_session):
        """get_multi_filtered supports skip and limit."""
        for i in range(5):
            await _create_property(db_session, f"Prop {i}")

        results = await property_crud.get_multi_filtered(
            db_session, skip=0, limit=2
        )
        assert len(results) == 2


# =============================================================================
# get_by_market
# =============================================================================


class TestGetByMarket:
    """Tests for get_by_market."""

    @pytest.mark.asyncio
    async def test_returns_matching_market(self, db_session):
        """get_by_market returns properties in the given market."""
        await _create_property(db_session, "A", market="Phoenix Metro")
        await _create_property(db_session, "B", market="Phoenix Metro")
        await _create_property(db_session, "C", market="Tucson Metro")

        results = await property_crud.get_by_market(
            db_session, market="Phoenix Metro"
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_case_insensitive(self, db_session):
        """get_by_market is case-insensitive."""
        await _create_property(db_session, "A", market="Phoenix Metro")

        results = await property_crud.get_by_market(
            db_session, market="phoenix metro"
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_empty_market(self, db_session):
        """get_by_market returns empty for nonexistent market."""
        results = await property_crud.get_by_market(
            db_session, market="Nonexistent"
        )
        assert results == []


# =============================================================================
# get_analytics_summary
# =============================================================================


class TestGetAnalyticsSummary:
    """Tests for get_analytics_summary."""

    @pytest.mark.asyncio
    async def test_empty_database(self, db_session):
        """get_analytics_summary returns zeros when no properties."""
        summary = await property_crud.get_analytics_summary(db_session)
        assert summary["total_properties"] == 0
        assert summary["total_units"] == 0
        assert summary["total_sf"] == 0
        assert summary["avg_cap_rate"] is None
        assert summary["avg_occupancy"] is None

    @pytest.mark.asyncio
    async def test_aggregates_correctly(self, db_session):
        """get_analytics_summary computes correct aggregates."""
        await _create_property(
            db_session, "A", total_units=100, cap_rate=Decimal("6.0"),
            occupancy_rate=Decimal("95.0"),
        )
        await _create_property(
            db_session, "B", total_units=200, cap_rate=Decimal("8.0"),
            occupancy_rate=Decimal("90.0"),
        )

        summary = await property_crud.get_analytics_summary(db_session)
        assert summary["total_properties"] == 2
        assert summary["total_units"] == 300
        # Average cap rate: (6.0 + 8.0) / 2 = 7.0
        assert abs(summary["avg_cap_rate"] - 7.0) < 0.01
        # Average occupancy: (95.0 + 90.0) / 2 = 92.5
        assert abs(summary["avg_occupancy"] - 92.5) < 0.01


# =============================================================================
# get_markets
# =============================================================================


class TestGetMarkets:
    """Tests for get_markets."""

    @pytest.mark.asyncio
    async def test_returns_distinct_markets(self, db_session):
        """get_markets returns unique market names."""
        await _create_property(db_session, "A", market="Phoenix Metro")
        await _create_property(db_session, "B", market="Phoenix Metro")
        await _create_property(db_session, "C", market="Tucson Metro")

        markets = await property_crud.get_markets(db_session)
        assert len(markets) == 2
        assert "Phoenix Metro" in markets
        assert "Tucson Metro" in markets

    @pytest.mark.asyncio
    async def test_empty_database(self, db_session):
        """get_markets returns empty list when no properties."""
        markets = await property_crud.get_markets(db_session)
        assert markets == []

    @pytest.mark.asyncio
    async def test_excludes_null_markets(self, db_session):
        """get_markets excludes properties with NULL market."""
        await _create_property(db_session, "A", market="Phoenix Metro")
        # Create property with None market
        prop = Property(
            name="No Market",
            property_type="multifamily",
            address="456 Test St",
            city="Unknown",
            state="AZ",
            zip_code="85001",
            market=None,
            total_units=50,
        )
        db_session.add(prop)
        await db_session.flush()

        markets = await property_crud.get_markets(db_session)
        assert len(markets) == 1
        assert "Phoenix Metro" in markets
