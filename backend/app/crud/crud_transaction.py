"""
CRUD operations for Transaction model.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionUpdate]):
    """
    CRUD operations for Transaction model with additional transaction-specific methods.
    """

    async def get_by_property(
        self,
        db: AsyncSession,
        property_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions for a specific property."""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.property_id == property_id)
            .where(Transaction.is_deleted == False)  # noqa: E712
            .order_by(Transaction.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        db: AsyncSession,
        transaction_type: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions filtered by type."""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.type == transaction_type)
            .where(Transaction.is_deleted == False)  # noqa: E712
            .order_by(Transaction.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions within a date range."""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.date >= start_date)
            .where(Transaction.date <= end_date)
            .where(Transaction.is_deleted == False)  # noqa: E712
            .order_by(Transaction.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        transaction_type: str | None = None,
        property_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        category: str | None = None,
        order_by: str = "date",
        order_desc: bool = True,
    ) -> list[Transaction]:
        """Get transactions with multiple filters."""
        query = select(Transaction).where(Transaction.is_deleted == False)  # noqa: E712

        # Apply filters
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        if property_id:
            query = query.where(Transaction.property_id == property_id)

        if date_from:
            query = query.where(Transaction.date >= date_from)

        if date_to:
            query = query.where(Transaction.date <= date_to)

        if category:
            query = query.where(Transaction.category == category)

        # Apply ordering
        if hasattr(Transaction, order_by):
            col = getattr(Transaction, order_by)
            query = query.order_by(col.desc() if order_desc else col.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        transaction_type: str | None = None,
        property_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        category: str | None = None,
    ) -> int:
        """Count transactions with filters."""
        query = (
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.is_deleted == False  # noqa: E712
            )
        )

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        if property_id:
            query = query.where(Transaction.property_id == property_id)

        if date_from:
            query = query.where(Transaction.date >= date_from)

        if date_to:
            query = query.where(Transaction.date <= date_to)

        if category:
            query = query.where(Transaction.category == category)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_summary(
        self,
        db: AsyncSession,
        *,
        property_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Get transaction summary statistics."""
        query = (
            select(
                Transaction.type,
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total"),
            )
            .where(Transaction.is_deleted == False)
            .group_by(Transaction.type)
        )  # noqa: E712

        if property_id:
            query = query.where(Transaction.property_id == property_id)

        if date_from:
            query = query.where(Transaction.date >= date_from)

        if date_to:
            query = query.where(Transaction.date <= date_to)

        result = await db.execute(query)
        rows = result.all()

        summary = {
            "total_acquisitions": Decimal("0"),
            "total_dispositions": Decimal("0"),
            "total_capital_improvements": Decimal("0"),
            "total_refinances": Decimal("0"),
            "total_distributions": Decimal("0"),
            "transaction_count": 0,
            "transactions_by_type": {},
        }

        for row in rows:
            type_name = row.type
            count = row.count
            total = row.total or Decimal("0")

            summary["transaction_count"] += count
            summary["transactions_by_type"][type_name] = count

            if type_name == TransactionType.ACQUISITION.value:
                summary["total_acquisitions"] = total
            elif type_name == TransactionType.DISPOSITION.value:
                summary["total_dispositions"] = total
            elif type_name == TransactionType.CAPITAL_IMPROVEMENT.value:
                summary["total_capital_improvements"] = total
            elif type_name == TransactionType.REFINANCE.value:
                summary["total_refinances"] = total
            elif type_name == TransactionType.DISTRIBUTION.value:
                summary["total_distributions"] = total

        return summary

    async def soft_delete(self, db: AsyncSession, *, id: int) -> Transaction | None:
        """Soft delete a transaction."""
        transaction = await self.get(db, id)
        if transaction:
            transaction.soft_delete()
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
        return transaction


# Singleton instance
transaction = CRUDTransaction(Transaction)
