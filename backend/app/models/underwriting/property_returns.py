"""
PropertyReturns - Property-level return metrics (44 fields).

Maps to: 'Assumptions (Summary)' Returns sections
Cell Reference Category: "Property-Level Return Metrics"
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class PropertyReturns(Base, TimestampMixin, SourceTrackingMixin):
    """
    Property-level return metrics.

    Contains: Unlevered returns, cap rates, NOI projections,
    and property-level IRR/equity multiples.
    """

    __tablename__ = "uw_property_returns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Parent relationship
    underwriting_model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("underwriting_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    underwriting_model: Mapped["UnderwritingModel"] = relationship(
        "UnderwritingModel",
        back_populates="property_returns",
    )

    # ==========================================================================
    # CAP RATES
    # ==========================================================================

    going_in_cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Going-in cap rate (T-12 NOI / Purchase Price)",
    )
    year_1_cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Year 1 cap rate"
    )
    stabilized_cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Stabilized cap rate"
    )
    exit_cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Exit cap rate assumption"
    )
    cap_rate_spread: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Spread between going-in and exit cap"
    )

    # ==========================================================================
    # NOI PROJECTIONS
    # ==========================================================================

    t12_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Trailing 12 month NOI"
    )
    year_1_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 1 projected NOI"
    )
    year_2_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 2 projected NOI"
    )
    year_3_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 3 projected NOI"
    )
    year_4_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 4 projected NOI"
    )
    year_5_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 5 projected NOI"
    )
    stabilized_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Stabilized NOI"
    )
    exit_noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Exit year NOI"
    )

    # ==========================================================================
    # PROPERTY VALUE
    # ==========================================================================

    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Initial purchase price"
    )
    total_cost_basis: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total cost basis including improvements"
    )
    stabilized_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Stabilized property value"
    )
    exit_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Projected exit/sale value"
    )
    gross_sale_proceeds: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Gross sale proceeds"
    )
    net_sale_proceeds: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Net sale proceeds after costs"
    )
    value_creation: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total value creation (exit - cost)"
    )

    # ==========================================================================
    # UNLEVERED RETURNS
    # ==========================================================================

    unlevered_irr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Unlevered IRR"
    )
    unlevered_equity_multiple: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3), nullable=True, comment="Unlevered equity multiple"
    )
    unlevered_cash_on_cash_year_1: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Year 1 unlevered cash-on-cash"
    )
    unlevered_cash_on_cash_avg: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Average unlevered cash-on-cash"
    )

    # ==========================================================================
    # YIELD METRICS
    # ==========================================================================

    year_1_yield_on_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Year 1 yield on cost"
    )
    stabilized_yield_on_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Stabilized yield on cost"
    )
    development_spread: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Development spread (stabilized yield - exit cap)",
    )

    # ==========================================================================
    # CASH FLOW SUMMARY
    # ==========================================================================

    year_1_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 1 property cash flow"
    )
    year_2_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 2 property cash flow"
    )
    year_3_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 3 property cash flow"
    )
    year_4_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 4 property cash flow"
    )
    year_5_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Year 5 property cash flow"
    )
    total_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total property cash flow over hold"
    )

    # ==========================================================================
    # PER UNIT METRICS
    # ==========================================================================

    noi_per_unit_year_1: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Year 1 NOI per unit"
    )
    noi_per_unit_stabilized: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Stabilized NOI per unit"
    )
    value_per_unit_purchase: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Purchase price per unit"
    )
    value_per_unit_exit: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Exit value per unit"
    )

    def __repr__(self) -> str:
        return f"<PropertyReturns unlevered_irr={self.unlevered_irr}>"
