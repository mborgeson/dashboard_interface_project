"""
Tests for Domain Validation Framework (Epic 4.2, UR-022).

Covers:
- DomainRule matching (exact, regex, case-insensitive)
- validate_domain_range() boundary conditions for every rule
- validate_domain_range() with non-numeric and unmatched fields
- validate_extracted_values() batch validation
- Integration into ExtractedValue model (domain_warning column)
- API endpoint GET /extraction/domain-warnings
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, Role, get_current_user
from app.db.base import Base
from app.extraction.domain_validators import (
    DOMAIN_RULES,
    DomainRule,
    ValidationWarning,
    _find_matching_rule,
    validate_domain_range,
    validate_extracted_values,
)
from app.main import app
from app.models.extraction import ExtractedValue, ExtractionRun

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def auto_auth():
    """Override auth for API tests."""

    async def _override():
        return CurrentUser(
            id=1,
            email="test@example.com",
            role=Role.ADMIN,
            full_name="Test Admin",
            is_active=True,
        )

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Unit Tests — DomainRule
# ============================================================================


class TestDomainRuleMatching:
    """Tests for DomainRule.matches()."""

    def test_exact_field_match(self):
        rule = DomainRule(".*CAP_RATE.*", 0.01, 0.20)
        assert rule.matches("CAP_RATE") is True

    def test_prefix_match(self):
        rule = DomainRule(".*CAP_RATE.*", 0.01, 0.20)
        assert rule.matches("GOING_IN_CAP_RATE") is True

    def test_suffix_match(self):
        rule = DomainRule(".*CAP_RATE.*", 0.01, 0.20)
        assert rule.matches("CAP_RATE_YEAR_1") is True

    def test_case_insensitive(self):
        rule = DomainRule(".*CAP_RATE.*", 0.01, 0.20)
        assert rule.matches("cap_rate") is True
        assert rule.matches("Cap_Rate") is True

    def test_no_match(self):
        rule = DomainRule(".*CAP_RATE.*", 0.01, 0.20)
        assert rule.matches("PURCHASE_PRICE") is False

    def test_alternation_pattern(self):
        rule = DomainRule(r".*SQ.*FT.*|.*SQUARE.*FOOT.*", 100, 10_000_000)
        assert rule.matches("TOTAL_SQ_FT") is True
        assert rule.matches("SQUARE_FOOTAGE") is True
        assert rule.matches("UNIT_COUNT") is False

    def test_rent_unit_pattern(self):
        rule = DomainRule(".*RENT.*UNIT.*", 300, 8000)
        assert rule.matches("AVG_RENT_PER_UNIT") is True
        assert rule.matches("RENT_UNIT_MIX") is True
        assert rule.matches("TOTAL_RENT") is False


# ============================================================================
# Unit Tests — _find_matching_rule
# ============================================================================


class TestFindMatchingRule:
    """Tests for _find_matching_rule()."""

    def test_finds_cap_rate_rule(self):
        rule = _find_matching_rule("GOING_IN_CAP_RATE")
        assert rule is not None
        # Should match the more specific GOING_IN_CAP rule first
        assert "GOING_IN_CAP" in rule.field_pattern

    def test_finds_generic_cap_rate(self):
        rule = _find_matching_rule("EXIT_CAP_RATE")
        assert rule is not None
        assert "CAP_RATE" in rule.field_pattern

    def test_returns_none_for_unknown(self):
        rule = _find_matching_rule("SOME_RANDOM_FIELD")
        assert rule is None

    def test_finds_noi_rule(self):
        rule = _find_matching_rule("T12_NOI")
        assert rule is not None
        assert "NOI" in rule.field_pattern

    def test_finds_irr_rule(self):
        rule = _find_matching_rule("LEVERED_IRR")
        assert rule is not None
        assert "IRR" in rule.field_pattern


# ============================================================================
# Unit Tests — validate_domain_range: Cap Rates
# ============================================================================


class TestCapRateValidation:
    """Boundary tests for cap rate rules."""

    def test_cap_rate_below_min(self):
        warning = validate_domain_range("EXIT_CAP_RATE", 0.005)
        assert warning is not None
        assert "below minimum" in warning.reason

    def test_cap_rate_at_min(self):
        warning = validate_domain_range("EXIT_CAP_RATE", 0.01)
        assert warning is None

    def test_cap_rate_in_range(self):
        warning = validate_domain_range("EXIT_CAP_RATE", 0.06)
        assert warning is None

    def test_cap_rate_at_max(self):
        warning = validate_domain_range("EXIT_CAP_RATE", 0.20)
        assert warning is None

    def test_cap_rate_above_max(self):
        warning = validate_domain_range("EXIT_CAP_RATE", 0.50)
        assert warning is not None
        assert "above maximum" in warning.reason

    def test_going_in_cap_below_min(self):
        warning = validate_domain_range("GOING_IN_CAP_RATE", 0.02)
        assert warning is not None
        assert "below minimum" in warning.reason

    def test_going_in_cap_in_range(self):
        warning = validate_domain_range("GOING_IN_CAP_RATE", 0.055)
        assert warning is None

    def test_going_in_cap_above_max(self):
        warning = validate_domain_range("GOING_IN_CAP_RATE", 0.25)
        assert warning is not None
        assert "above maximum" in warning.reason


# ============================================================================
# Unit Tests — validate_domain_range: Returns
# ============================================================================


class TestReturnsValidation:
    """Boundary tests for IRR, MOIC, return on cost."""

    def test_irr_below_min(self):
        warning = validate_domain_range("LEVERED_IRR", -0.50)
        assert warning is not None

    def test_irr_at_min(self):
        warning = validate_domain_range("LEVERED_IRR", -0.30)
        assert warning is None

    def test_irr_in_range(self):
        warning = validate_domain_range("UNLEVERED_IRR", 0.12)
        assert warning is None

    def test_irr_above_max(self):
        warning = validate_domain_range("LEVERED_IRR", 0.80)
        assert warning is not None

    def test_moic_below_min(self):
        warning = validate_domain_range("LEVERED_MOIC", 0.1)
        assert warning is not None

    def test_moic_in_range(self):
        warning = validate_domain_range("LEVERED_MOIC", 2.0)
        assert warning is None

    def test_moic_above_max(self):
        warning = validate_domain_range("UNLEVERED_MOIC", 8.0)
        assert warning is not None

    def test_return_on_cost_below_min(self):
        warning = validate_domain_range("T3_RETURN_ON_COST", -0.20)
        assert warning is not None

    def test_return_on_cost_in_range(self):
        warning = validate_domain_range("T3_RETURN_ON_COST", 0.06)
        assert warning is None

    def test_return_on_cost_above_max(self):
        warning = validate_domain_range("T3_RETURN_ON_COST", 0.50)
        assert warning is not None


# ============================================================================
# Unit Tests — validate_domain_range: Income / Expenses
# ============================================================================


class TestIncomeExpenseValidation:
    """Boundary tests for NOI, revenue, expenses."""

    def test_noi_below_min(self):
        warning = validate_domain_range("T12_NOI", 100)
        assert warning is not None

    def test_noi_in_range(self):
        warning = validate_domain_range("T12_NOI", 1_500_000)
        assert warning is None

    def test_noi_above_max(self):
        warning = validate_domain_range("YEAR_1_NOI", 500_000_000)
        assert warning is not None

    def test_revenue_in_range(self):
        warning = validate_domain_range("TOTAL_REVENUE", 5_000_000)
        assert warning is None

    def test_expense_in_range(self):
        warning = validate_domain_range("TOTAL_EXPENSE", 2_000_000)
        assert warning is None


# ============================================================================
# Unit Tests — validate_domain_range: Property Metrics
# ============================================================================


class TestPropertyMetricValidation:
    """Boundary tests for purchase price, units, occupancy, etc."""

    def test_purchase_price_below_min(self):
        warning = validate_domain_range("PURCHASE_PRICE", 10_000)
        assert warning is not None

    def test_purchase_price_in_range(self):
        warning = validate_domain_range("PURCHASE_PRICE", 25_000_000)
        assert warning is None

    def test_unit_count_below_min(self):
        warning = validate_domain_range("UNIT_COUNT", 0)
        assert warning is not None

    def test_unit_count_in_range(self):
        warning = validate_domain_range("UNIT_COUNT", 250)
        assert warning is None

    def test_unit_count_above_max(self):
        warning = validate_domain_range("UNIT_COUNT", 10_000)
        assert warning is not None

    def test_price_per_unit_in_range(self):
        warning = validate_domain_range("PRICE_PER_UNIT", 120_000)
        assert warning is None

    def test_rent_per_unit_in_range(self):
        warning = validate_domain_range("AVG_RENT_PER_UNIT", 1200)
        assert warning is None

    def test_rent_per_unit_below_min(self):
        warning = validate_domain_range("AVG_RENT_PER_UNIT", 50)
        assert warning is not None

    def test_occupancy_at_zero(self):
        warning = validate_domain_range("OCCUPANCY", 0.0)
        assert warning is None

    def test_occupancy_at_one(self):
        warning = validate_domain_range("OCCUPANCY", 1.0)
        assert warning is None

    def test_occupancy_above_one(self):
        warning = validate_domain_range("OCCUPANCY", 1.5)
        assert warning is not None

    def test_year_built_in_range(self):
        warning = validate_domain_range("YEAR_BUILT", 1985)
        assert warning is None

    def test_year_built_below_min(self):
        warning = validate_domain_range("YEAR_BUILT", 1800)
        assert warning is not None

    def test_year_built_above_max(self):
        warning = validate_domain_range("YEAR_BUILT", 2050)
        assert warning is not None

    def test_sq_ft_in_range(self):
        warning = validate_domain_range("TOTAL_SQ_FT", 150_000)
        assert warning is None

    def test_sq_ft_below_min(self):
        warning = validate_domain_range("TOTAL_SQ_FT", 10)
        assert warning is not None


# ============================================================================
# Unit Tests — Edge Cases
# ============================================================================


class TestEdgeCases:
    """Non-numeric values, unmatched fields, etc."""

    def test_none_value_returns_none(self):
        assert validate_domain_range("CAP_RATE", None) is None

    def test_string_value_returns_none(self):
        assert validate_domain_range("CAP_RATE", "N/A") is None

    def test_empty_string_returns_none(self):
        assert validate_domain_range("CAP_RATE", "") is None

    def test_unmatched_field_returns_none(self):
        assert validate_domain_range("RANDOM_METRIC", 9999) is None

    def test_decimal_value_works(self):
        warning = validate_domain_range("EXIT_CAP_RATE", Decimal("0.08"))
        assert warning is None

    def test_integer_value_works(self):
        warning = validate_domain_range("UNIT_COUNT", 100)
        assert warning is None

    def test_negative_numeric(self):
        warning = validate_domain_range("LEVERED_IRR", -0.049)
        assert warning is None  # within -0.30 to 0.60

    def test_warning_severity_is_warning(self):
        warning = validate_domain_range("CAP_RATE", 5.0)
        assert warning is not None
        assert warning.severity == "warning"

    def test_warning_contains_field_name(self):
        warning = validate_domain_range("EXIT_CAP_RATE", 5.0)
        assert warning is not None
        assert "EXIT_CAP_RATE" in warning.reason


# ============================================================================
# Unit Tests — validate_extracted_values (batch)
# ============================================================================


class TestValidateExtractedValues:
    """Tests for validate_extracted_values()."""

    def test_all_valid_returns_empty(self):
        data = {
            "GOING_IN_CAP_RATE": 0.055,
            "PURCHASE_PRICE": 25_000_000,
            "UNIT_COUNT": 250,
        }
        warnings = validate_extracted_values(data)
        assert warnings == []

    def test_mixed_valid_invalid(self):
        data = {
            "GOING_IN_CAP_RATE": 0.055,  # OK
            "PURCHASE_PRICE": 100,  # too low
            "UNIT_COUNT": 10_000,  # too high
        }
        warnings = validate_extracted_values(data)
        assert len(warnings) == 2
        field_names = {w.field_name for w in warnings}
        assert "PURCHASE_PRICE" in field_names
        assert "UNIT_COUNT" in field_names

    def test_non_numeric_values_skipped(self):
        data = {
            "GOING_IN_CAP_RATE": "TBD",
            "PROPERTY_ADDRESS": "123 Main St",
        }
        warnings = validate_extracted_values(data)
        assert warnings == []

    def test_empty_dict(self):
        warnings = validate_extracted_values({})
        assert warnings == []

    def test_unmatched_fields_skipped(self):
        data = {"RANDOM_FIELD_1": 999, "RANDOM_FIELD_2": -5}
        warnings = validate_extracted_values(data)
        assert warnings == []


# ============================================================================
# Unit Tests — DOMAIN_RULES coverage
# ============================================================================


class TestDomainRulesCoverage:
    """Ensure every rule in DOMAIN_RULES is exercised at least once."""

    @pytest.mark.parametrize(
        "field_name,value_ok",
        [
            ("EXIT_CAP_RATE", 0.06),
            ("GOING_IN_CAP_RATE", 0.055),
            ("LEVERED_IRR", 0.12),
            ("LEVERED_MOIC", 2.0),
            ("T3_RETURN_ON_COST", 0.08),
            ("T12_NOI", 1_500_000),
            ("TOTAL_REVENUE", 5_000_000),
            ("TOTAL_EXPENSE", 2_000_000),
            ("PURCHASE_PRICE", 25_000_000),
            ("UNIT_COUNT", 250),
            ("PRICE_PER_UNIT", 120_000),
            ("AVG_RENT_PER_UNIT", 1200),
            ("OCCUPANCY", 0.95),
            ("YEAR_BUILT", 1985),
            ("TOTAL_SQ_FT", 150_000),
        ],
    )
    def test_valid_value_no_warning(self, field_name: str, value_ok: float):
        assert validate_domain_range(field_name, value_ok) is None


# ============================================================================
# Model Tests — ExtractedValue.domain_warning column
# ============================================================================


class TestExtractedValueDomainWarning:
    """Verify the domain_warning column exists on the model."""

    @pytest_asyncio.fixture
    async def db_session(self):
        """Fresh in-memory DB with all tables."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )
        from sqlalchemy.pool import StaticPool

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as session:
            yield session

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_domain_warning_column_persists(self, db_session: AsyncSession):
        """domain_warning column should round-trip through the DB."""
        run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(run)
        await db_session.flush()

        ev = ExtractedValue(
            id=uuid4(),
            extraction_run_id=run.id,
            property_name="Test Property",
            field_name="GOING_IN_CAP_RATE",
            value_numeric=Decimal("5.0"),
            value_text="5.0",
            domain_warning="GOING_IN_CAP_RATE=5.0 is above maximum 0.15",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(ev)
        await db_session.commit()
        await db_session.refresh(ev)

        assert ev.domain_warning == "GOING_IN_CAP_RATE=5.0 is above maximum 0.15"

    @pytest.mark.asyncio
    async def test_domain_warning_nullable(self, db_session: AsyncSession):
        """domain_warning should be nullable."""
        run = ExtractionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(run)
        await db_session.flush()

        ev = ExtractedValue(
            id=uuid4(),
            extraction_run_id=run.id,
            property_name="Test Property",
            field_name="GOING_IN_CAP_RATE",
            value_numeric=Decimal("0.055"),
            value_text="0.055",
            domain_warning=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(ev)
        await db_session.commit()
        await db_session.refresh(ev)

        assert ev.domain_warning is None


# ============================================================================
# API Tests — GET /extraction/domain-warnings
# ============================================================================


class TestDomainWarningsAPI:
    """API endpoint tests for the domain-warnings endpoint."""

    @pytest_asyncio.fixture
    async def db_session(self):
        """Fresh in-memory DB with all tables."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )
        from sqlalchemy.pool import StaticPool

        from app.db.session import get_db

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as session:
            # Override dependency
            async def override_get_db():
                yield session

            app.dependency_overrides[get_db] = override_get_db
            yield session

        app.dependency_overrides.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest_asyncio.fixture
    async def seeded_db(self, db_session: AsyncSession):
        """Seed the DB with extraction runs and values (some with warnings)."""
        run_id = uuid4()
        run = ExtractionRun(
            id=run_id,
            status="completed",
            trigger_type="manual",
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(run)
        await db_session.flush()

        # Value WITH warning
        ev1 = ExtractedValue(
            id=uuid4(),
            extraction_run_id=run_id,
            property_name="Hayden Park",
            field_name="GOING_IN_CAP_RATE",
            value_numeric=Decimal("5.0"),
            value_text="5.0",
            domain_warning="GOING_IN_CAP_RATE=5.0 is above maximum 0.15",
            source_file="/test/hayden.xlsx",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # Value WITHOUT warning
        ev2 = ExtractedValue(
            id=uuid4(),
            extraction_run_id=run_id,
            property_name="Hayden Park",
            field_name="UNIT_COUNT",
            value_numeric=Decimal("250"),
            value_text="250",
            domain_warning=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # Another value WITH warning, different property
        ev3 = ExtractedValue(
            id=uuid4(),
            extraction_run_id=run_id,
            property_name="Broadstone 7th",
            field_name="T3_RETURN_ON_COST",
            value_numeric=Decimal("0.0"),
            value_text="0.0",
            domain_warning="T3_RETURN_ON_COST=0.0 unusual value",
            source_file="/test/broadstone.xlsx",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add_all([ev1, ev2, ev3])
        await db_session.commit()
        return {"run_id": run_id}

    @pytest_asyncio.fixture
    async def client(self, db_session: AsyncSession, auto_auth):
        """AsyncClient with auth override."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_list_warnings_empty(self, client: AsyncClient, db_session):
        """No warnings in empty DB returns empty list."""
        resp = await client.get("/api/v1/extraction/domain-warnings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["warnings"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_warnings_returns_only_flagged(
        self, client: AsyncClient, seeded_db
    ):
        """Only rows with domain_warning IS NOT NULL are returned."""
        resp = await client.get("/api/v1/extraction/domain-warnings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["warnings"]) == 2

    @pytest.mark.asyncio
    async def test_filter_by_property_name(self, client: AsyncClient, seeded_db):
        """Filter by property_name returns subset."""
        resp = await client.get(
            "/api/v1/extraction/domain-warnings",
            params={"property_name": "Hayden Park"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["warnings"][0]["property_name"] == "Hayden Park"

    @pytest.mark.asyncio
    async def test_filter_by_field_name(self, client: AsyncClient, seeded_db):
        """Filter by field_name returns subset."""
        resp = await client.get(
            "/api/v1/extraction/domain-warnings",
            params={"field_name": "GOING_IN_CAP_RATE"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_run_id(self, client: AsyncClient, seeded_db):
        """Filter by run_id."""
        run_id = seeded_db["run_id"]
        resp = await client.get(
            "/api/v1/extraction/domain-warnings",
            params={"run_id": str(run_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient, seeded_db):
        """Pagination with limit and offset works."""
        resp = await client.get(
            "/api/v1/extraction/domain-warnings",
            params={"limit": 1, "offset": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["warnings"]) == 1
        assert data["total"] == 2  # total count is still 2
        assert data["limit"] == 1
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_requires_auth(self, db_session: AsyncSession):
        """Endpoint requires authentication."""
        # Clear any auth overrides
        app.dependency_overrides.pop(get_current_user, None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/extraction/domain-warnings")
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_response_shape(self, client: AsyncClient, seeded_db):
        """Response has expected keys."""
        resp = await client.get("/api/v1/extraction/domain-warnings")
        data = resp.json()
        assert "warnings" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        # Each warning has expected fields
        w = data["warnings"][0]
        assert "field_name" in w
        assert "value" in w
        assert "property_name" in w
        assert "domain_warning" in w
        assert "source_file" in w
