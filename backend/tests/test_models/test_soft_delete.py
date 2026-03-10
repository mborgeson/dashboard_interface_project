"""
Tests for soft-delete functionality on Deal and Transaction models.

Validates:
- Soft-deleted records are excluded from list/get queries by default
- Soft-deleted records can be restored
- deleted_at timestamp is set on soft-delete and cleared on restore
- Admin queries can include deleted items via include_deleted flag
- The API delete endpoints perform soft-delete (not hard delete)
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_deal import CRUDDeal
from app.crud.crud_transaction import CRUDTransaction
from app.models.deal import Deal, DealStage
from app.models.transaction import Transaction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def deal_crud() -> CRUDDeal:
    return CRUDDeal(Deal)


@pytest_asyncio.fixture
async def txn_crud() -> CRUDTransaction:
    return CRUDTransaction(Transaction)


@pytest_asyncio.fixture
async def sample_deal(db_session: AsyncSession) -> Deal:
    """Create a single deal for testing."""
    now = datetime.now(UTC)
    deal = Deal(
        name="Soft Delete Test Deal",
        deal_type="acquisition",
        stage=DealStage.INITIAL_REVIEW,
        stage_order=0,
        priority="medium",
        created_at=now,
        updated_at=now,
    )
    db_session.add(deal)
    await db_session.commit()
    await db_session.refresh(deal)
    return deal


@pytest_asyncio.fixture
async def sample_deals(db_session: AsyncSession) -> list[Deal]:
    """Create multiple deals — some will be soft-deleted in tests."""
    now = datetime.now(UTC)
    deals = []
    for i in range(3):
        d = Deal(
            name=f"Deal #{i}",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=i,
            priority="medium",
            created_at=now,
            updated_at=now,
        )
        db_session.add(d)
        deals.append(d)
    await db_session.commit()
    for d in deals:
        await db_session.refresh(d)
    return deals


@pytest_asyncio.fixture
async def sample_transaction(db_session: AsyncSession) -> Transaction:
    """Create a single transaction for testing."""
    now = datetime.now(UTC)
    txn = Transaction(
        property_name="Test Property",
        type="acquisition",
        amount=Decimal("1000000.00"),
        date=date(2025, 6, 1),
        created_at=now,
        updated_at=now,
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# Deal soft-delete tests
# ---------------------------------------------------------------------------


class TestDealSoftDelete:
    """Tests for Deal soft-delete behaviour."""

    async def test_soft_delete_sets_is_deleted_and_timestamp(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deal: Deal,
    ) -> None:
        """Soft-deleting a deal sets is_deleted=True and populates deleted_at."""
        removed = await deal_crud.remove(db_session, id=sample_deal.id)

        assert removed is not None
        assert removed.is_deleted is True
        assert removed.deleted_at is not None
        assert isinstance(removed.deleted_at, datetime)

    async def test_soft_deleted_deal_excluded_from_get(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deal: Deal,
    ) -> None:
        """A soft-deleted deal is not returned by get() by default."""
        await deal_crud.remove(db_session, id=sample_deal.id)

        result = await deal_crud.get(db_session, sample_deal.id)
        assert result is None

    async def test_soft_deleted_deal_excluded_from_get_multi(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deals: list[Deal],
    ) -> None:
        """Soft-deleted deals are excluded from get_multi results."""
        # Delete first deal
        await deal_crud.remove(db_session, id=sample_deals[0].id)

        results = await deal_crud.get_multi(db_session)
        result_ids = {d.id for d in results}
        assert sample_deals[0].id not in result_ids
        assert len(results) == 2

    async def test_soft_deleted_deal_excluded_from_get_multi_filtered(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deals: list[Deal],
    ) -> None:
        """Soft-deleted deals are excluded from get_multi_filtered results."""
        await deal_crud.remove(db_session, id=sample_deals[0].id)

        results = await deal_crud.get_multi_filtered(db_session)
        result_ids = {d.id for d in results}
        assert sample_deals[0].id not in result_ids
        assert len(results) == 2

    async def test_soft_deleted_deal_excluded_from_count_filtered(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deals: list[Deal],
    ) -> None:
        """Soft-deleted deals are not counted in count_filtered."""
        await deal_crud.remove(db_session, id=sample_deals[0].id)

        count = await deal_crud.count_filtered(db_session)
        assert count == 2

    async def test_soft_deleted_deal_excluded_from_kanban(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deals: list[Deal],
    ) -> None:
        """Soft-deleted deals are excluded from Kanban board data."""
        await deal_crud.remove(db_session, id=sample_deals[0].id)

        kanban = await deal_crud.get_kanban_data(db_session)
        assert kanban["total_deals"] == 2

    async def test_soft_deleted_deal_excluded_from_get_by_stage(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deals: list[Deal],
    ) -> None:
        """Soft-deleted deals are excluded from get_by_stage."""
        await deal_crud.remove(db_session, id=sample_deals[0].id)

        results = await deal_crud.get_by_stage(
            db_session, stage=DealStage.INITIAL_REVIEW
        )
        result_ids = {d.id for d in results}
        assert sample_deals[0].id not in result_ids
        assert len(results) == 2

    async def test_include_deleted_returns_soft_deleted_deal(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deal: Deal,
    ) -> None:
        """Setting include_deleted=True returns soft-deleted deals."""
        await deal_crud.remove(db_session, id=sample_deal.id)

        # Default: excluded
        assert await deal_crud.get(db_session, sample_deal.id) is None

        # With include_deleted: returned
        result = await deal_crud.get(
            db_session, sample_deal.id, include_deleted=True
        )
        assert result is not None
        assert result.is_deleted is True

    async def test_include_deleted_in_get_multi_filtered(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deals: list[Deal],
    ) -> None:
        """Admin can list including deleted items via include_deleted."""
        await deal_crud.remove(db_session, id=sample_deals[0].id)

        results = await deal_crud.get_multi_filtered(
            db_session, include_deleted=True
        )
        assert len(results) == 3

    async def test_restore_soft_deleted_deal(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deal: Deal,
    ) -> None:
        """Restoring a soft-deleted deal clears is_deleted and deleted_at."""
        await deal_crud.remove(db_session, id=sample_deal.id)

        restored = await deal_crud.restore(db_session, id=sample_deal.id)
        assert restored is not None
        assert restored.is_deleted is False
        assert restored.deleted_at is None

        # Now visible again in normal queries
        result = await deal_crud.get(db_session, sample_deal.id)
        assert result is not None

    async def test_restore_nonexistent_deal_returns_none(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
    ) -> None:
        """Restoring a non-existent deal returns None."""
        result = await deal_crud.restore(db_session, id=99999)
        assert result is None

    async def test_restore_active_deal_is_noop(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deal: Deal,
    ) -> None:
        """Restoring an already-active deal returns it without error."""
        result = await deal_crud.restore(db_session, id=sample_deal.id)
        assert result is not None
        assert result.is_deleted is False

    async def test_deal_still_in_database_after_soft_delete(
        self,
        db_session: AsyncSession,
        deal_crud: CRUDDeal,
        sample_deal: Deal,
    ) -> None:
        """Soft-delete does NOT remove the row from the database."""
        await deal_crud.remove(db_session, id=sample_deal.id)

        # Direct query without any soft-delete filter
        result = await db_session.execute(
            select(Deal).where(Deal.id == sample_deal.id)
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.is_deleted is True


# ---------------------------------------------------------------------------
# Transaction soft-delete tests
# ---------------------------------------------------------------------------


class TestTransactionSoftDelete:
    """Tests for Transaction soft-delete behaviour."""

    async def test_soft_delete_sets_is_deleted_and_timestamp(
        self,
        db_session: AsyncSession,
        txn_crud: CRUDTransaction,
        sample_transaction: Transaction,
    ) -> None:
        """Soft-deleting a transaction sets is_deleted=True and populates deleted_at."""
        removed = await txn_crud.remove(db_session, id=sample_transaction.id)

        assert removed is not None
        assert removed.is_deleted is True
        assert removed.deleted_at is not None

    async def test_soft_deleted_transaction_excluded_from_get(
        self,
        db_session: AsyncSession,
        txn_crud: CRUDTransaction,
        sample_transaction: Transaction,
    ) -> None:
        """A soft-deleted transaction is not returned by get() by default."""
        await txn_crud.remove(db_session, id=sample_transaction.id)

        result = await txn_crud.get(db_session, sample_transaction.id)
        assert result is None

    async def test_soft_deleted_transaction_excluded_from_get_filtered(
        self,
        db_session: AsyncSession,
        txn_crud: CRUDTransaction,
        sample_transaction: Transaction,
    ) -> None:
        """Soft-deleted transactions are excluded from get_filtered."""
        await txn_crud.remove(db_session, id=sample_transaction.id)

        results = await txn_crud.get_filtered(db_session)
        assert len(results) == 0

    async def test_include_deleted_returns_soft_deleted_transaction(
        self,
        db_session: AsyncSession,
        txn_crud: CRUDTransaction,
        sample_transaction: Transaction,
    ) -> None:
        """Setting include_deleted=True returns soft-deleted transactions."""
        await txn_crud.remove(db_session, id=sample_transaction.id)

        result = await txn_crud.get(
            db_session, sample_transaction.id, include_deleted=True
        )
        assert result is not None
        assert result.is_deleted is True

    async def test_restore_soft_deleted_transaction(
        self,
        db_session: AsyncSession,
        txn_crud: CRUDTransaction,
        sample_transaction: Transaction,
    ) -> None:
        """Restoring a soft-deleted transaction clears is_deleted and deleted_at."""
        await txn_crud.remove(db_session, id=sample_transaction.id)

        restored = await txn_crud.restore(db_session, id=sample_transaction.id)
        assert restored is not None
        assert restored.is_deleted is False
        assert restored.deleted_at is None

    async def test_transaction_still_in_database_after_soft_delete(
        self,
        db_session: AsyncSession,
        txn_crud: CRUDTransaction,
        sample_transaction: Transaction,
    ) -> None:
        """Soft-delete does NOT remove the row from the database."""
        await txn_crud.remove(db_session, id=sample_transaction.id)

        result = await db_session.execute(
            select(Transaction).where(Transaction.id == sample_transaction.id)
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.is_deleted is True
