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
            .where(Transaction.is_deleted.is_(False))  # noqa: E712
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
            .where(Transaction.is_deleted.is_(False))  # noqa: E712
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
            .where(Transaction.is_deleted.is_(False))  # noqa: E712
            .order_by(Transaction.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def _build_transaction_conditions(
        self,
        *,
        transaction_type: str | None = None,
        property_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        category: str | None = None,
    ) -> list:
        """Build SQLAlchemy filter conditions for transaction queries."""
        conditions: list = []

        if transaction_type:
            conditions.append(Transaction.type == transaction_type)

        if property_id:
            conditions.append(Transaction.property_id == property_id)

        if date_from:
            conditions.append(Transaction.date >= date_from)

        if date_to:
            conditions.append(Transaction.date <= date_to)

        if category:
            conditions.append(Transaction.category == category)

        return conditions

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
        conditions = self._build_transaction_conditions(
            transaction_type=transaction_type,
            property_id=property_id,
            date_from=date_from,
            date_to=date_to,
            category=category,
        )
        return await self.get_multi_ordered(
            db,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
            conditions=conditions,
        )

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
        conditions = self._build_transaction_conditions(
            transaction_type=transaction_type,
            property_id=property_id,
            date_from=date_from,
            date_to=date_to,
            category=category,
        )
        return await self.count_where(db, conditions=conditions)

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
            .where(Transaction.is_deleted.is_(False))
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

        summary: dict[str, Any] = {
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
            await db.flush()
            await db.refresh(transaction)
        return transaction


# Singleton instance
transaction = CRUDTransaction(Transaction)
