"""
Transaction model for tracking financial transactions across properties.
"""

from datetime import date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class TransactionType(str, PyEnum):
    """Transaction type categories."""

    ACQUISITION = "acquisition"
    DISPOSITION = "disposition"
    CAPITAL_IMPROVEMENT = "capital_improvement"
    REFINANCE = "refinance"
    DISTRIBUTION = "distribution"


class Transaction(Base, TimestampMixin, SoftDeleteMixin):
    """Transaction model representing financial transactions in the portfolio."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Property Reference
    property_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )
    property_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Transaction Details
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # acquisition, disposition, capital_improvement, refinance, distribution
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # Purchase, Unit Renovation, Quarterly Distribution, etc.
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Optional related documents
    documents: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id}: {self.type} ${self.amount} - {self.property_name}>"
