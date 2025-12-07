"""
SalesComp - Transaction comparables (per-comp rows).

Maps to: 'Sales Comps' sheet data
Cell Reference Category: "Sales Comps"

This table is normalized - instead of 273 columns (10 comps × 27 fields),
each row represents one comparable transaction.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, Date, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.underwriting.source_tracking import SourceTrackingMixin

if TYPE_CHECKING:
    from app.models.underwriting.underwriting_model import UnderwritingModel


class SalesComp(Base, TimestampMixin, SourceTrackingMixin):
    """
    Sales comparable transaction data - one row per comparable.

    Contains: Property identification, transaction details,
    pricing metrics, and cap rates.
    """

    __tablename__ = "uw_sales_comps"

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
        back_populates="sales_comps",
    )

    # Comp ordering
    comp_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Comparable number (1, 2, 3, etc.)"
    )

    # ==========================================================================
    # PROPERTY IDENTIFICATION
    # ==========================================================================

    property_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Comparable property name"
    )
    property_address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Full street address"
    )
    property_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City"
    )
    property_state: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="State"
    )
    property_zip: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="ZIP code"
    )
    submarket: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Submarket name"
    )
    distance_miles: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Distance from subject property in miles"
    )

    # ==========================================================================
    # PHYSICAL CHARACTERISTICS
    # ==========================================================================

    year_built: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Year built"
    )
    year_renovated: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Year renovated"
    )
    total_units: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of units"
    )
    total_sf: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total square feet"
    )
    avg_unit_sf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Average unit size in SF"
    )
    stories: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of stories"
    )
    building_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Garden, Mid-Rise, High-Rise"
    )
    lot_size_acres: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Lot size in acres"
    )

    # ==========================================================================
    # QUALITY & CLASSIFICATION
    # ==========================================================================

    asset_class: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Class A, B, C, D"
    )
    condition_at_sale: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Condition at time of sale"
    )

    # ==========================================================================
    # TRANSACTION DETAILS
    # ==========================================================================

    sale_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date of sale"
    )
    sale_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Total sale price"
    )
    price_per_unit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Sale price per unit"
    )
    price_per_sf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Sale price per SF"
    )

    # Transaction Type
    transaction_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Arm's length, Portfolio, Distressed"
    )
    sale_conditions: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Special sale conditions if any"
    )

    # ==========================================================================
    # CAP RATES & NOI
    # ==========================================================================

    cap_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Cap rate at sale"
    )
    cap_rate_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Actual, Pro Forma, Broker"
    )
    noi_at_sale: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="NOI at time of sale"
    )
    noi_per_unit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="NOI per unit at sale"
    )

    # ==========================================================================
    # RENT METRICS AT SALE
    # ==========================================================================

    avg_rent_at_sale: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Average rent at time of sale"
    )
    avg_rent_per_sf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Average rent per SF at sale"
    )
    occupancy_at_sale: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Occupancy at time of sale"
    )

    # ==========================================================================
    # BUYER/SELLER INFORMATION
    # ==========================================================================

    buyer_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Buyer name"
    )
    buyer_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="REIT, Private Equity, Family Office, etc."
    )
    seller_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Seller name"
    )
    seller_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of seller"
    )
    broker: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Broker/brokerage that handled sale"
    )

    # ==========================================================================
    # FINANCING
    # ==========================================================================

    financing_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Agency, Bank, Life Co, etc."
    )
    loan_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Loan amount if known"
    )
    ltv: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Loan-to-value ratio"
    )

    # ==========================================================================
    # DATA SOURCE
    # ==========================================================================

    data_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="CoStar, RCA, Public Records, etc."
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about comparable"
    )

    def __repr__(self) -> str:
        return f"<SalesComp #{self.comp_number} {self.property_name} @ ${self.sale_price}>"
