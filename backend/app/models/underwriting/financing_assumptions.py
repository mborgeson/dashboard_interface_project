"""
FinancingAssumptions - Debt and equity structure (53 fields).

Maps to: 'Assumptions (Summary)' Debt & Equity sections
Cell Reference Category: "Debt and Equity Assumptions"
"""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class FinancingAssumptions(Base, TimestampMixin, SourceTrackingMixin):
    """
    Financing assumptions for debt and equity structure.

    Contains: Senior debt terms, mezzanine/preferred equity,
    common equity structure, and waterfall parameters.
    """

    __tablename__ = "uw_financing_assumptions"

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
        back_populates="financing_assumptions",
    )

    # ==========================================================================
    # SENIOR DEBT
    # ==========================================================================

    # Loan Amount & LTV
    senior_loan_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Senior loan amount"
    )
    senior_ltv: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Senior loan-to-value ratio"
    )
    senior_ltc: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Senior loan-to-cost ratio"
    )

    # Interest Rate
    senior_interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6),
        nullable=True,
        comment="Senior debt interest rate (annual)"
    )
    senior_rate_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Fixed, Floating, Hybrid"
    )
    senior_index_rate: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="SOFR, Prime, Treasury, etc."
    )
    senior_spread: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Spread over index rate"
    )
    senior_rate_floor: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Interest rate floor"
    )
    senior_rate_cap: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Interest rate cap"
    )

    # Loan Terms
    senior_term_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Loan term in months"
    )
    senior_amortization_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Amortization period in months"
    )
    senior_io_period_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Interest-only period in months"
    )
    senior_maturity_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Loan maturity date"
    )

    # Loan Costs
    senior_origination_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Origination fee percentage"
    )
    senior_exit_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Exit/prepayment fee percentage"
    )
    senior_closing_costs: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Total closing costs"
    )

    # DSCR Requirements
    senior_min_dscr: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Minimum DSCR requirement"
    )
    senior_dscr_at_close: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="DSCR at loan closing"
    )

    # Lender Information
    senior_lender_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Senior lender name"
    )
    senior_lender_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Agency, Bank, Life Co, CMBS, etc."
    )

    # ==========================================================================
    # MEZZANINE / PREFERRED EQUITY
    # ==========================================================================

    mezz_loan_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Mezzanine/preferred equity amount"
    )
    mezz_interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6),
        nullable=True,
        comment="Mezzanine interest/preferred return rate"
    )
    mezz_term_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Mezzanine term in months"
    )
    mezz_origination_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Mezzanine origination fee"
    )
    mezz_accrual_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6),
        nullable=True,
        comment="PIK/accrual rate if applicable"
    )
    mezz_participation_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Profit participation percentage"
    )

    # ==========================================================================
    # EQUITY STRUCTURE
    # ==========================================================================

    # Total Equity
    total_equity_required: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total equity required"
    )
    lp_equity_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="LP equity percentage"
    )
    gp_equity_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="GP equity percentage"
    )
    lp_equity_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="LP equity amount"
    )
    gp_equity_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="GP equity amount"
    )

    # Waterfall Structure
    preferred_return: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Preferred return rate (pref)"
    )
    preferred_return_accrual: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Simple, Compound, IRR-based"
    )
    catchup_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="GP catch-up percentage"
    )

    # Promote Tiers
    promote_tier_1_hurdle: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="First promote tier hurdle (IRR)"
    )
    promote_tier_1_gp_split: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="GP split at tier 1"
    )
    promote_tier_2_hurdle: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Second promote tier hurdle (IRR)"
    )
    promote_tier_2_gp_split: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="GP split at tier 2"
    )
    promote_tier_3_hurdle: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Third promote tier hurdle (IRR)"
    )
    promote_tier_3_gp_split: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="GP split at tier 3"
    )

    # Fees
    acquisition_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Acquisition fee percentage"
    )
    disposition_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Disposition fee percentage"
    )
    refinance_fee_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Refinance fee percentage"
    )

    def __repr__(self) -> str:
        return f"<FinancingAssumptions senior={self.senior_loan_amount} equity={self.total_equity_required}>"
