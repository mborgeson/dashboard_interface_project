"""
UnderwritingModel - Parent entity linking property/deal to underwriting data.
"""

from datetime import datetime
from enum import StrEnum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.annual_cashflow import AnnualCashflow
    from app.models.underwriting.budget_assumptions import BudgetAssumptions
    from app.models.underwriting.equity_returns import EquityReturns
    from app.models.underwriting.exit_assumptions import ExitAssumptions
    from app.models.underwriting.financing_assumptions import FinancingAssumptions
    from app.models.underwriting.general_assumptions import GeneralAssumptions
    from app.models.underwriting.noi_assumptions import NOIAssumptions
    from app.models.underwriting.property_returns import PropertyReturns
    from app.models.underwriting.rent_comp import RentComp
    from app.models.underwriting.sales_comp import SalesComp
    from app.models.underwriting.unit_mix import UnitMix


class UnderwritingStatus(PyEnum):
    """Status of the underwriting model."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class UnderwritingModel(Base, TimestampMixin, SoftDeleteMixin, SourceTrackingMixin):
    """
    Parent table for underwriting models.

    Links a property/deal to its complete underwriting analysis.
    Supports versioning for scenario analysis and historical tracking.
    """

    __tablename__ = "underwriting_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Underwriting model name/identifier",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Version number for scenario tracking",
    )
    scenario_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Scenario label: Base Case, Upside, Downside, etc.",
    )

    # Relationships to core entities
    property_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )
    deal_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("deals.id"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    # Status and workflow
    status: Mapped[UnderwritingStatus] = mapped_column(
        Enum(UnderwritingStatus),
        default=UnderwritingStatus.DRAFT,
        nullable=False,
        index=True,
    )
    approved_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Description and notes
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Description of this underwriting scenario"
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Internal notes and comments"
    )

    # Child relationships (one-to-one for assumption tables)
    general_assumptions: Mapped[Optional["GeneralAssumptions"]] = relationship(
        "GeneralAssumptions",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    exit_assumptions: Mapped[Optional["ExitAssumptions"]] = relationship(
        "ExitAssumptions",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    noi_assumptions: Mapped[Optional["NOIAssumptions"]] = relationship(
        "NOIAssumptions",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    financing_assumptions: Mapped[Optional["FinancingAssumptions"]] = relationship(
        "FinancingAssumptions",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    budget_assumptions: Mapped[Optional["BudgetAssumptions"]] = relationship(
        "BudgetAssumptions",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    property_returns: Mapped[Optional["PropertyReturns"]] = relationship(
        "PropertyReturns",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    equity_returns: Mapped[Optional["EquityReturns"]] = relationship(
        "EquityReturns",
        back_populates="underwriting_model",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Child relationships (one-to-many for normalized tables)
    unit_mixes: Mapped[list["UnitMix"]] = relationship(
        "UnitMix",
        back_populates="underwriting_model",
        cascade="all, delete-orphan",
    )
    rent_comps: Mapped[list["RentComp"]] = relationship(
        "RentComp",
        back_populates="underwriting_model",
        cascade="all, delete-orphan",
    )
    sales_comps: Mapped[list["SalesComp"]] = relationship(
        "SalesComp",
        back_populates="underwriting_model",
        cascade="all, delete-orphan",
    )
    annual_cashflows: Mapped[list["AnnualCashflow"]] = relationship(
        "AnnualCashflow",
        back_populates="underwriting_model",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<UnderwritingModel {self.name} v{self.version} ({self.status.value})>"
