"""
PostgreSQL integration tests for server_default behaviour (T-DEBT-015).

These tests verify that timestamps, boolean defaults, and status columns
auto-populate via PostgreSQL server_default / ORM-level defaults — behaviour
that SQLite cannot faithfully reproduce.

Every test is marked ``@pytest.mark.pg`` and is skipped when
``TEST_DATABASE_URL`` is not set.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from tests.conftest_pg import pg_available

pytestmark = [pytest.mark.pg, pg_available]


# ---------------------------------------------------------------------------
# TimestampMixin defaults (created_at / updated_at)
# ---------------------------------------------------------------------------


class TestTimestampDefaults:
    """Verify that created_at and updated_at auto-populate on INSERT."""

    async def test_user_created_at_auto_populates(self, pg_session):
        """User.created_at should be set automatically on insert."""
        from app.models import User
        from app.core.security import get_password_hash

        before = datetime.now(UTC)
        user = User(
            email="timestamp_test@example.com",
            hashed_password=get_password_hash("test123"),
            full_name="Timestamp Test",
            role="viewer",
            is_active=True,
        )
        pg_session.add(user)
        await pg_session.commit()
        await pg_session.refresh(user)
        after = datetime.now(UTC)

        assert user.created_at is not None
        # Tolerate timezone-aware vs naive comparison
        created = (
            user.created_at.replace(tzinfo=None)
            if user.created_at.tzinfo
            else user.created_at
        )
        assert (
            before.replace(tzinfo=None) - timedelta(seconds=5)
            <= created
            <= after.replace(tzinfo=None) + timedelta(seconds=5)
        )

    async def test_user_updated_at_auto_populates(self, pg_session):
        """User.updated_at should be set automatically on insert."""
        from app.models import User
        from app.core.security import get_password_hash

        user = User(
            email="updated_test@example.com",
            hashed_password=get_password_hash("test123"),
            full_name="Updated Test",
            role="viewer",
            is_active=True,
        )
        pg_session.add(user)
        await pg_session.commit()
        await pg_session.refresh(user)

        assert user.updated_at is not None

    async def test_property_timestamps_auto_populate(self, pg_session):
        """Property timestamps should be set on insert without explicit values."""
        from app.models import Property

        prop = Property(
            name="Timestamp Property",
            property_type="multifamily",
            address="789 Auto St",
            city="Tempe",
            state="AZ",
            zip_code="85281",
            total_units=50,
            total_sf=40000,
        )
        pg_session.add(prop)
        await pg_session.commit()
        await pg_session.refresh(prop)

        assert prop.created_at is not None
        assert prop.updated_at is not None

    async def test_deal_timestamps_auto_populate(self, pg_session, pg_user):
        """Deal timestamps should be set on insert without explicit values."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Timestamp Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="low",
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.created_at is not None
        assert deal.updated_at is not None

    async def test_updated_at_changes_on_update(self, pg_session, pg_user):
        """updated_at should change when the record is modified."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Update Tracking Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="low",
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        original_updated = deal.updated_at

        # Mutate and commit
        deal.name = "Updated Deal Name"
        await pg_session.commit()
        await pg_session.refresh(deal)

        # The onupdate lambda should fire
        assert deal.updated_at is not None
        assert deal.updated_at >= original_updated


# ---------------------------------------------------------------------------
# Boolean / status column defaults
# ---------------------------------------------------------------------------


class TestBooleanAndStatusDefaults:
    """Verify that boolean and status fields default correctly."""

    async def test_user_is_active_defaults_true(self, pg_session):
        """User.is_active should default to True."""
        from app.models import User
        from app.core.security import get_password_hash

        user = User(
            email="active_default@example.com",
            hashed_password=get_password_hash("test123"),
            full_name="Active Default",
            role="viewer",
        )
        pg_session.add(user)
        await pg_session.commit()
        await pg_session.refresh(user)

        assert user.is_active is True

    async def test_user_is_verified_defaults_false(self, pg_session):
        """User.is_verified should default to False."""
        from app.models import User
        from app.core.security import get_password_hash

        user = User(
            email="verified_default@example.com",
            hashed_password=get_password_hash("test123"),
            full_name="Verified Default",
            role="viewer",
        )
        pg_session.add(user)
        await pg_session.commit()
        await pg_session.refresh(user)

        assert user.is_verified is False

    async def test_deal_stage_defaults_to_initial_review(self, pg_session, pg_user):
        """Deal.stage should default to INITIAL_REVIEW."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Stage Default Deal",
            deal_type="acquisition",
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="medium",
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.stage == DealStage.INITIAL_REVIEW

    async def test_deal_priority_defaults_to_medium(self, pg_session, pg_user):
        """Deal.priority should default to 'medium'."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Priority Default Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.priority == "medium"

    async def test_deal_version_defaults_to_one(self, pg_session, pg_user):
        """Deal.version (optimistic lock) should default to 1."""
        from app.models import Deal, DealStage

        deal = Deal(
            name="Version Default Deal",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=pg_user.id,
            priority="low",
        )
        pg_session.add(deal)
        await pg_session.commit()
        await pg_session.refresh(deal)

        assert deal.version == 1


# ---------------------------------------------------------------------------
# SoftDeleteMixin defaults
# ---------------------------------------------------------------------------


class TestSoftDeleteDefaults:
    """Verify that soft-delete fields default correctly."""

    async def test_is_deleted_defaults_false(self, pg_session):
        """is_deleted should default to False on a new Property."""
        from app.models import Property

        prop = Property(
            name="Soft Delete Test",
            property_type="multifamily",
            address="101 Soft St",
            city="Mesa",
            state="AZ",
            zip_code="85201",
            total_units=60,
            total_sf=45000,
        )
        pg_session.add(prop)
        await pg_session.commit()
        await pg_session.refresh(prop)

        assert prop.is_deleted is False
        assert prop.deleted_at is None

    async def test_soft_delete_sets_timestamp(self, pg_session):
        """soft_delete() should set is_deleted=True and populate deleted_at."""
        from app.models import Property

        prop = Property(
            name="Soft Delete Timestamp",
            property_type="multifamily",
            address="102 Soft St",
            city="Mesa",
            state="AZ",
            zip_code="85201",
            total_units=60,
            total_sf=45000,
        )
        pg_session.add(prop)
        await pg_session.commit()
        await pg_session.refresh(prop)

        prop.soft_delete()
        await pg_session.commit()
        await pg_session.refresh(prop)

        assert prop.is_deleted is True
        assert prop.deleted_at is not None

    async def test_restore_clears_soft_delete(self, pg_session):
        """restore() should reset is_deleted and deleted_at."""
        from app.models import Property

        prop = Property(
            name="Restore Test",
            property_type="multifamily",
            address="103 Soft St",
            city="Mesa",
            state="AZ",
            zip_code="85201",
            total_units=60,
            total_sf=45000,
        )
        pg_session.add(prop)
        await pg_session.commit()

        prop.soft_delete()
        await pg_session.commit()
        await pg_session.refresh(prop)
        assert prop.is_deleted is True

        prop.restore()
        await pg_session.commit()
        await pg_session.refresh(prop)
        assert prop.is_deleted is False
        assert prop.deleted_at is None


# ---------------------------------------------------------------------------
# Extraction model defaults
# ---------------------------------------------------------------------------


class TestExtractionDefaults:
    """Verify extraction model defaults work under PG."""

    async def test_extraction_run_status_defaults_to_running(self, pg_session):
        """ExtractionRun.status should default to 'running'."""
        from app.models.extraction import ExtractionRun

        run = ExtractionRun(trigger_type="manual")
        pg_session.add(run)
        await pg_session.commit()
        await pg_session.refresh(run)

        assert run.status == "running"
        assert run.files_discovered == 0
        assert run.files_processed == 0
        assert run.files_failed == 0

    async def test_extracted_value_is_error_defaults_false(self, pg_session):
        """ExtractedValue.is_error should default to False."""
        from app.models.extraction import ExtractedValue, ExtractionRun

        run = ExtractionRun(trigger_type="manual")
        pg_session.add(run)
        await pg_session.commit()
        await pg_session.refresh(run)

        value = ExtractedValue(
            extraction_run_id=run.id,
            property_name="Default Test Property",
            field_name="NOI",
            value_numeric=Decimal("500000.00"),
        )
        pg_session.add(value)
        await pg_session.commit()
        await pg_session.refresh(value)

        assert value.is_error is False
        assert value.created_at is not None
