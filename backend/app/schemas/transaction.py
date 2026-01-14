"""
Transaction schemas for API request/response validation.
"""

from datetime import date as date_type
from decimal import Decimal

from pydantic import Field

from .base import BaseSchema, TimestampSchema


class TransactionBase(BaseSchema):
    """Base transaction schema with common fields."""

    property_id: int | None = None
    property_name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(
        ...,
        pattern="^(acquisition|disposition|capital_improvement|refinance|distribution)$",
    )
    category: str | None = Field(None, max_length=100)
    amount: Decimal = Field(..., ge=0)
    date: date_type
    description: str | None = None


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    documents: list[str] | None = None


class TransactionUpdate(BaseSchema):
    """Schema for updating a transaction. All fields optional."""

    property_id: int | None = None
    property_name: str | None = Field(None, min_length=1, max_length=255)
    type: str | None = Field(
        None,
        pattern="^(acquisition|disposition|capital_improvement|refinance|distribution)$",
    )
    category: str | None = Field(None, max_length=100)
    amount: Decimal | None = Field(None, ge=0)
    date: date_type | None = None
    description: str | None = None
    documents: list[str] | None = None


class TransactionResponse(TransactionBase, TimestampSchema):
    """Schema for transaction response."""

    id: int
    documents: list[str] | None = None


class TransactionListResponse(BaseSchema):
    """Paginated list of transactions."""

    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class TransactionSummaryResponse(BaseSchema):
    """Transaction summary statistics."""

    total_acquisitions: Decimal = Field(default=Decimal("0"))
    total_dispositions: Decimal = Field(default=Decimal("0"))
    total_capital_improvements: Decimal = Field(default=Decimal("0"))
    total_refinances: Decimal = Field(default=Decimal("0"))
    total_distributions: Decimal = Field(default=Decimal("0"))
    transaction_count: int = 0
    transactions_by_type: dict[str, int] = Field(default_factory=dict)
