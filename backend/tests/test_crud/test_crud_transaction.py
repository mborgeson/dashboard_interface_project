"""Tests for Transaction CRUD operations.

Covers:
- Transaction creation and retrieval
- Property-based filtering
- Type-based filtering
- Date range queries
- Multi-filter queries
- Summary statistics
- Soft delete
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from app.crud.crud_transaction import transaction as txn_crud
from app.models.transaction import Transaction, TransactionType


@pytest_asyncio.fixture
async def sample_transactions(db_session):
    """Create a set of sample transactions for testing."""
    now = date.today()
    transactions = [
        Transaction(
            property_id=1,
            property_name="Sunset Apartments",
            type=TransactionType.ACQUISITION.value,
            category="Purchase",
            amount=Decimal("8500000.00"),
            date=now - timedelta(days=90),
            description="Initial acquisition",
        ),
        Transaction(
            property_id=1,
            property_name="Sunset Apartments",
            type=TransactionType.CAPITAL_IMPROVEMENT.value,
            category="Unit Renovation",
            amount=Decimal("250000.00"),
            date=now - timedelta(days=30),
            description="Phase 1 unit renovations",
        ),
        Transaction(
            property_id=2,
            property_name="Mesa Ridge",
            type=TransactionType.ACQUISITION.value,
            category="Purchase",
            amount=Decimal("12000000.00"),
            date=now - timedelta(days=60),
            description="Mesa Ridge acquisition",
        ),
        Transaction(
            property_id=2,
            property_name="Mesa Ridge",
            type=TransactionType.DISTRIBUTION.value,
            category="Quarterly Distribution",
            amount=Decimal("75000.00"),
            date=now - timedelta(days=5),
            description="Q4 distribution",
        ),
    ]

    for t in transactions:
        db_session.add(t)
    await db_session.commit()
    for t in transactions:
        await db_session.refresh(t)
    return transactions


# =============================================================================
# Basic CRUD
# =============================================================================


@pytest.mark.asyncio
async def test_create_transaction(db_session):
    """Create a transaction and verify persistence."""
    created = await txn_crud.create(
        db_session,
        obj_in={
            "property_id": 1,
            "property_name": "Test Property",
            "type": TransactionType.REFINANCE.value,
            "amount": Decimal("5000000.00"),
            "date": date.today(),
            "description": "Refinance at lower rate",
        },
    )

    assert created.id is not None
    assert created.type == TransactionType.REFINANCE.value
    assert created.amount == Decimal("5000000.00")


@pytest.mark.asyncio
async def test_get_transaction(db_session, sample_transactions):
    """Retrieve transaction by ID."""
    txn = sample_transactions[0]
    found = await txn_crud.get(db_session, txn.id)
    assert found is not None
    assert found.id == txn.id
    assert found.property_name == "Sunset Apartments"


# =============================================================================
# Property-based Filtering
# =============================================================================


@pytest.mark.asyncio
async def test_get_by_property(db_session, sample_transactions):
    """Get transactions for a specific property."""
    results = await txn_crud.get_by_property(db_session, property_id=1)
    assert len(results) == 2
    assert all(t.property_id == 1 for t in results)


@pytest.mark.asyncio
async def test_get_by_property_empty(db_session, sample_transactions):
    """Property with no transactions returns empty list."""
    results = await txn_crud.get_by_property(db_session, property_id=999)
    assert results == []


# =============================================================================
# Type-based Filtering
# =============================================================================


@pytest.mark.asyncio
async def test_get_by_type(db_session, sample_transactions):
    """Filter transactions by type."""
    results = await txn_crud.get_by_type(
        db_session, transaction_type=TransactionType.ACQUISITION.value
    )
    assert len(results) == 2
    assert all(t.type == TransactionType.ACQUISITION.value for t in results)


# =============================================================================
# Date Range Filtering
# =============================================================================


@pytest.mark.asyncio
async def test_get_by_date_range(db_session, sample_transactions):
    """Filter transactions within a date range."""
    now = date.today()
    results = await txn_crud.get_by_date_range(
        db_session,
        start_date=now - timedelta(days=45),
        end_date=now,
    )
    # Should include 30-day-old and 5-day-old transactions
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_by_date_range_no_results(db_session, sample_transactions):
    """Date range with no transactions returns empty list."""
    future = date.today() + timedelta(days=365)
    results = await txn_crud.get_by_date_range(
        db_session,
        start_date=future,
        end_date=future + timedelta(days=30),
    )
    assert results == []


# =============================================================================
# Multi-filter Queries
# =============================================================================


@pytest.mark.asyncio
async def test_get_filtered_by_type_and_property(db_session, sample_transactions):
    """Filter by both type and property."""
    results = await txn_crud.get_filtered(
        db_session,
        transaction_type=TransactionType.ACQUISITION.value,
        property_id=1,
    )
    assert len(results) == 1
    assert results[0].property_name == "Sunset Apartments"


@pytest.mark.asyncio
async def test_get_filtered_by_category(db_session, sample_transactions):
    """Filter by category."""
    results = await txn_crud.get_filtered(
        db_session, category="Purchase"
    )
    assert len(results) == 2


@pytest.mark.asyncio
async def test_count_filtered(db_session, sample_transactions):
    """Count transactions with filters."""
    count = await txn_crud.count_filtered(
        db_session, transaction_type=TransactionType.ACQUISITION.value
    )
    assert count == 2

    total = await txn_crud.count_filtered(db_session)
    assert total == 4


# =============================================================================
# Summary Statistics
# =============================================================================


@pytest.mark.asyncio
async def test_get_summary(db_session, sample_transactions):
    """Summary should aggregate by type."""
    summary = await txn_crud.get_summary(db_session)

    assert summary["transaction_count"] == 4
    assert summary["total_acquisitions"] == Decimal("8500000.00") + Decimal("12000000.00")
    assert summary["total_capital_improvements"] == Decimal("250000.00")
    assert summary["total_distributions"] == Decimal("75000.00")
    assert summary["total_dispositions"] == Decimal("0")
    assert summary["total_refinances"] == Decimal("0")


@pytest.mark.asyncio
async def test_get_summary_by_property(db_session, sample_transactions):
    """Summary filtered by property."""
    summary = await txn_crud.get_summary(db_session, property_id=1)

    assert summary["transaction_count"] == 2
    assert summary["total_acquisitions"] == Decimal("8500000.00")


@pytest.mark.asyncio
async def test_get_summary_empty(db_session):
    """Summary with no transactions returns zeros."""
    summary = await txn_crud.get_summary(db_session)

    assert summary["transaction_count"] == 0
    assert summary["total_acquisitions"] == Decimal("0")


# =============================================================================
# Soft Delete
# =============================================================================


@pytest.mark.asyncio
async def test_soft_delete(db_session, sample_transactions):
    """Soft delete should mark transaction as deleted."""
    txn = sample_transactions[0]
    deleted = await txn_crud.soft_delete(db_session, id=txn.id)

    assert deleted is not None
    assert deleted.is_deleted is True


@pytest.mark.asyncio
async def test_soft_delete_nonexistent(db_session):
    """Soft deleting non-existent transaction returns None."""
    result = await txn_crud.soft_delete(db_session, id=99999)
    assert result is None


@pytest.mark.asyncio
async def test_soft_deleted_excluded_from_property_query(db_session, sample_transactions):
    """Soft-deleted transactions should be excluded from get_by_property."""
    txn = sample_transactions[0]
    await txn_crud.soft_delete(db_session, id=txn.id)

    results = await txn_crud.get_by_property(db_session, property_id=1)
    assert len(results) == 1  # Was 2, now 1 after soft delete


# =============================================================================
# Build Conditions
# =============================================================================


class TestBuildTransactionConditions:
    """Test the internal _build_transaction_conditions method."""

    def test_no_filters(self):
        conditions = txn_crud._build_transaction_conditions()
        assert conditions == []

    def test_all_filters(self):
        conditions = txn_crud._build_transaction_conditions(
            transaction_type="acquisition",
            property_id=1,
            date_from=date.today(),
            date_to=date.today(),
            category="Purchase",
        )
        assert len(conditions) == 5
