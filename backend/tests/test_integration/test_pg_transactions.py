"""
PostgreSQL integration tests for real transaction behaviour (T-DEBT-015).

SQLite with StaticPool does not support reliable ``begin_nested()`` (savepoints).
These tests verify savepoints, rollback, and concurrent-access patterns against
a real PostgreSQL instance.

Every test is marked ``@pytest.mark.pg`` and is skipped when
``TEST_DATABASE_URL`` is not set.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_pg import pg_available

pytestmark = [pytest.mark.pg, pg_available]


# ---------------------------------------------------------------------------
# Savepoints / nested transactions
# ---------------------------------------------------------------------------


class TestSavepoints:
    """Verify that savepoints (begin_nested) work correctly under PG."""

    async def test_savepoint_commit(self, pg_session: AsyncSession):
        """Data committed inside a savepoint should persist after outer commit."""
        from app.models import Property

        async with pg_session.begin_nested():
            prop = Property(
                name="Savepoint Commit",
                property_type="multifamily",
                address="1 Savepoint Ln",
                city="Gilbert",
                state="AZ",
                zip_code="85233",
                total_units=80,
                total_sf=60000,
            )
            pg_session.add(prop)

        await pg_session.commit()

        result = await pg_session.execute(
            select(Property).where(Property.name == "Savepoint Commit")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.city == "Gilbert"

    async def test_savepoint_rollback_does_not_affect_outer(
        self, pg_session: AsyncSession
    ):
        """Rolling back a savepoint should not discard data from outside it."""
        from app.models import Property

        # Insert outside of savepoint
        outer_prop = Property(
            name="Outer Property",
            property_type="multifamily",
            address="2 Outer Ln",
            city="Chandler",
            state="AZ",
            zip_code="85224",
            total_units=50,
            total_sf=40000,
        )
        pg_session.add(outer_prop)
        await pg_session.flush()

        # Insert inside a savepoint, then roll it back
        try:
            async with pg_session.begin_nested():
                inner_prop = Property(
                    name="Inner Property",
                    property_type="multifamily",
                    address="3 Inner Ln",
                    city="Scottsdale",
                    state="AZ",
                    zip_code="85251",
                    total_units=30,
                    total_sf=25000,
                )
                pg_session.add(inner_prop)
                await pg_session.flush()
                # Force a rollback by raising
                raise IntegrityError("simulated", params=None, orig=Exception())
        except IntegrityError:
            pass  # savepoint rolled back

        await pg_session.commit()

        # Outer row should survive
        result = await pg_session.execute(
            select(Property).where(Property.name == "Outer Property")
        )
        assert result.scalar_one_or_none() is not None

        # Inner row should NOT be present
        result = await pg_session.execute(
            select(Property).where(Property.name == "Inner Property")
        )
        assert result.scalar_one_or_none() is None

    async def test_nested_savepoints(self, pg_session: AsyncSession):
        """Multiple levels of savepoints should work correctly."""
        from app.core.security import get_password_hash
        from app.models import User

        async with pg_session.begin_nested():
            u1 = User(
                email="sp_level1@example.com",
                hashed_password=get_password_hash("test"),
                full_name="Level 1",
                role="viewer",
                is_active=True,
            )
            pg_session.add(u1)

            async with pg_session.begin_nested():
                u2 = User(
                    email="sp_level2@example.com",
                    hashed_password=get_password_hash("test"),
                    full_name="Level 2",
                    role="viewer",
                    is_active=True,
                )
                pg_session.add(u2)

        await pg_session.commit()

        result = await pg_session.execute(
            select(User).where(
                User.email.in_(["sp_level1@example.com", "sp_level2@example.com"])
            )
        )
        users = result.scalars().all()
        assert len(users) == 2


# ---------------------------------------------------------------------------
# Rollback behaviour
# ---------------------------------------------------------------------------


class TestRollback:
    """Verify full-transaction rollback under PG."""

    async def test_rollback_discards_all_changes(self, pg_session: AsyncSession):
        """A full rollback should discard all pending changes."""
        from app.models import Property

        prop = Property(
            name="Rollback Test",
            property_type="multifamily",
            address="10 Rollback Ave",
            city="Glendale",
            state="AZ",
            zip_code="85301",
            total_units=40,
            total_sf=35000,
        )
        pg_session.add(prop)
        await pg_session.flush()

        # Verify it's visible within the transaction
        result = await pg_session.execute(
            select(Property).where(Property.name == "Rollback Test")
        )
        assert result.scalar_one_or_none() is not None

        # Rollback
        await pg_session.rollback()

        # Should no longer be visible
        result = await pg_session.execute(
            select(Property).where(Property.name == "Rollback Test")
        )
        assert result.scalar_one_or_none() is None

    async def test_rollback_after_integrity_error(self, pg_session: AsyncSession):
        """Session should recover after an IntegrityError + rollback."""
        from app.core.security import get_password_hash
        from app.models import User

        user1 = User(
            email="dupe@example.com",
            hashed_password=get_password_hash("test"),
            full_name="First",
            role="viewer",
            is_active=True,
        )
        pg_session.add(user1)
        await pg_session.commit()

        # Attempt to insert duplicate email
        user2 = User(
            email="dupe@example.com",
            hashed_password=get_password_hash("test"),
            full_name="Second",
            role="viewer",
            is_active=True,
        )
        pg_session.add(user2)

        with pytest.raises(IntegrityError):
            await pg_session.flush()

        await pg_session.rollback()

        # Session should still be usable after rollback
        result = await pg_session.execute(
            select(User).where(User.email == "dupe@example.com")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.full_name == "First"


# ---------------------------------------------------------------------------
# Unique constraint enforcement
# ---------------------------------------------------------------------------


class TestUniqueConstraints:
    """Verify that unique constraints are enforced at the DB level."""

    async def test_user_email_unique_constraint(self, pg_session: AsyncSession):
        """Duplicate emails should raise IntegrityError."""
        from app.core.security import get_password_hash
        from app.models import User

        u1 = User(
            email="unique@example.com",
            hashed_password=get_password_hash("test"),
            full_name="User 1",
            role="viewer",
            is_active=True,
        )
        pg_session.add(u1)
        await pg_session.commit()

        u2 = User(
            email="unique@example.com",
            hashed_password=get_password_hash("test"),
            full_name="User 2",
            role="viewer",
            is_active=True,
        )
        pg_session.add(u2)

        with pytest.raises(IntegrityError):
            await pg_session.flush()

        await pg_session.rollback()

    async def test_extracted_value_unique_constraint(self, pg_session: AsyncSession):
        """Duplicate (run_id, property_name, field_name) should raise IntegrityError."""
        from app.models.extraction import ExtractedValue, ExtractionRun

        run = ExtractionRun(trigger_type="manual")
        pg_session.add(run)
        await pg_session.commit()
        await pg_session.refresh(run)

        v1 = ExtractedValue(
            extraction_run_id=run.id,
            property_name="DupeTest",
            field_name="NOI",
            value_numeric=Decimal("100000.00"),
        )
        pg_session.add(v1)
        await pg_session.commit()

        v2 = ExtractedValue(
            extraction_run_id=run.id,
            property_name="DupeTest",
            field_name="NOI",
            value_numeric=Decimal("200000.00"),
        )
        pg_session.add(v2)

        with pytest.raises(IntegrityError):
            await pg_session.flush()

        await pg_session.rollback()


# ---------------------------------------------------------------------------
# Check constraint enforcement
# ---------------------------------------------------------------------------


class TestCheckConstraints:
    """Verify that CHECK constraints fire at the DB level."""

    async def test_property_negative_purchase_price_rejected(
        self, pg_session: AsyncSession
    ):
        """CHECK constraint should reject negative purchase_price."""
        from app.models import Property

        prop = Property(
            name="Negative Price",
            property_type="multifamily",
            address="99 Bad St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            total_units=10,
            total_sf=8000,
            purchase_price=Decimal("-1.00"),
        )
        pg_session.add(prop)

        with pytest.raises(IntegrityError):
            await pg_session.flush()

        await pg_session.rollback()

    async def test_property_cap_rate_out_of_range_rejected(
        self, pg_session: AsyncSession
    ):
        """CHECK constraint or column overflow should reject cap_rate > 100."""
        from app.models import Property

        prop = Property(
            name="Bad Cap Rate",
            property_type="multifamily",
            address="100 Bad St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            total_units=10,
            total_sf=8000,
            cap_rate=Decimal("150.000"),
        )
        pg_session.add(prop)

        # NUMERIC(5,3) overflows before CHECK runs — both are DBAPIError subclasses
        with pytest.raises((IntegrityError, DBAPIError)):
            await pg_session.flush()

        await pg_session.rollback()

    async def test_deal_negative_asking_price_rejected(
        self, pg_session: AsyncSession, pg_user
    ):
        """CHECK constraint should reject negative asking_price."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Negative Ask",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            asking_price=Decimal("-5000.00"),
            priority="low",
        )
        pg_session.add(deal)

        with pytest.raises(IntegrityError):
            await pg_session.flush()

        await pg_session.rollback()


# ---------------------------------------------------------------------------
# Foreign key cascade
# ---------------------------------------------------------------------------


class TestForeignKeyCascade:
    """Verify FK behaviour under PG."""

    async def test_deal_references_valid_user(self, pg_session: AsyncSession, pg_user):
        """A deal should be able to reference an existing user."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="FK Test Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="medium",
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.assigned_user_id == pg_user.id

    async def test_deal_with_invalid_user_id_rejected(self, pg_session: AsyncSession):
        """FK constraint should reject a deal with a non-existent user_id."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Bad FK Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=999999,  # non-existent
            priority="medium",
        )
        pg_session.add(deal)

        with pytest.raises(IntegrityError):
            await pg_session.flush()

        await pg_session.rollback()
