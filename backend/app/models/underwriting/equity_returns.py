"""
EquityReturns - Equity-level return metrics (21 fields).

Maps to: 'Assumptions (Summary)' LP/GP Returns sections
Cell Reference Category: "Equity-Level Return Metrics"
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


class EquityReturns(Base, TimestampMixin, SourceTrackingMixin):
    """
    Equity-level return metrics for LP and GP.

    Contains: Levered returns, LP/GP splits, promote calculations,
    and distribution waterfall results.
    """

    __tablename__ = "uw_equity_returns"

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
        back_populates="equity_returns",
    )

    # ==========================================================================
    # LEVERED RETURNS (TOTAL)
    # ==========================================================================

    levered_irr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Total levered project IRR"
    )
    levered_equity_multiple: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3), nullable=True, comment="Total levered equity multiple"
    )
    levered_cash_on_cash_year_1: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Year 1 levered cash-on-cash"
    )
    levered_cash_on_cash_avg: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="Average levered cash-on-cash"
    )

    # ==========================================================================
    # LP RETURNS
    # ==========================================================================

    lp_irr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="LP internal rate of return"
    )
    lp_equity_multiple: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3), nullable=True, comment="LP equity multiple"
    )
    lp_total_distributions: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total LP distributions"
    )
    lp_preferred_return: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="LP preferred return earned"
    )
    lp_profit_share: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="LP share of profits above pref"
    )

    # ==========================================================================
    # GP RETURNS
    # ==========================================================================

    gp_irr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True, comment="GP internal rate of return"
    )
    gp_equity_multiple: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3), nullable=True, comment="GP equity multiple"
    )
    gp_total_distributions: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total GP distributions"
    )
    gp_promote_earned: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="GP promote/carried interest earned"
    )
    gp_fees_earned: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total GP fees earned"
    )

    # ==========================================================================
    # DISTRIBUTION WATERFALL SUMMARY
    # ==========================================================================

    total_equity_invested: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total equity invested"
    )
    total_distributions: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total distributions to all equity"
    )
    total_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Total profit (distributions - invested)"
    )

    # Promote Tier Achievement
    promote_tier_achieved: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Highest promote tier achieved (1, 2, or 3)"
    )
    promote_tier_1_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Promote earned at tier 1"
    )
    promote_tier_2_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Promote earned at tier 2"
    )
    promote_tier_3_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="Promote earned at tier 3"
    )

    def __repr__(self) -> str:
        return f"<EquityReturns lp_irr={self.lp_irr} gp_irr={self.gp_irr}>"
