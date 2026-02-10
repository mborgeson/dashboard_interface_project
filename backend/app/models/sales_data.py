"""
SalesData model — stores CoStar multifamily sales transaction records.

Each row represents a single property sale imported from CoStar Excel exports.
Comp ID is NOT unique (duplicates exist across files), so we use an
auto-increment primary key and a unique constraint on (comp_id, source_file).
"""

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class SalesData(Base, TimestampMixin):
    """CoStar multifamily sales transaction record."""

    __tablename__ = "sales_data"

    __table_args__ = (
        UniqueConstraint("comp_id", "source_file", name="uq_sales_data_comp_id_source"),
        Index("ix_sales_data_submarket", "submarket_name"),
        Index("ix_sales_data_sale_date", "sale_date"),
        Index("ix_sales_data_market", "market"),
    )

    # ── Primary Key ──────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Import Metadata ──────────────────────────────────────────────────
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    market: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 1-10: Core Property Identifiers ──────────────────────────────────
    property_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    property_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comp_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    property_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    property_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    property_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    property_zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    property_county: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── 11-14: Market / Geography ────────────────────────────────────────
    submarket_cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submarket_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parcel_number_1_min: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parcel_number_2_max: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── 15-22: Land & Building Overview ──────────────────────────────────
    land_area_ac: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_area_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    star_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market_column: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submarket_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    building_class: Mapped[str | None] = mapped_column(String(10), nullable=True)
    affordable_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── 23-34: Parties ───────────────────────────────────────────────────
    buyer_true_company: Mapped[str | None] = mapped_column(String(500), nullable=True)
    buyer_true_contact: Mapped[str | None] = mapped_column(String(500), nullable=True)
    acquisition_fund_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    buyer_contact: Mapped[str | None] = mapped_column(String(500), nullable=True)
    seller_true_company: Mapped[str | None] = mapped_column(String(500), nullable=True)
    disposition_fund_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    listing_broker_company: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    listing_broker_agent_first_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    listing_broker_agent_last_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    buyers_broker_company: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    buyers_broker_agent_first_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    buyers_broker_agent_last_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # ── 35-47: Building Details ──────────────────────────────────────────
    construction_begin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    building_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_materials: Mapped[str | None] = mapped_column(String(500), nullable=True)
    building_condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    construction_material: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    roof_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ceiling_height: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number_of_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 48-54: Units & Parking ───────────────────────────────────────────
    number_of_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number_of_parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number_of_tenants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    land_sf_gross: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_sf_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    flood_risk: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flood_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 55: Avg Unit SF ──────────────────────────────────────────────────
    avg_unit_sf: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 56-68: Transaction Details ───────────────────────────────────────
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_sf_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_sf: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_period: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    down_payment: Mapped[float | None] = mapped_column(Float, nullable=True)
    sale_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    sale_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    sale_price_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    sale_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sale_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 69-78: Financial Metrics ─────────────────────────────────────────
    actual_cap_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    units_per_acre: Mapped[float | None] = mapped_column(Float, nullable=True)
    zoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    number_of_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gross_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    grm: Mapped[float | None] = mapped_column(Float, nullable=True)
    gim: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_operating_expenses: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_expense_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    vacancy: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 79-82: Assessment ────────────────────────────────────────────────
    assessed_improved: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessed_land: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessed_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 83-87: Unit Mix ──────────────────────────────────────────────────
    number_of_studios_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number_of_1_bedrooms_units: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    number_of_2_bedrooms_units: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    number_of_3_bedrooms_units: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    number_of_other_bedrooms_units: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # ── 88-96: Debt & Title ──────────────────────────────────────────────
    first_trust_deed_terms: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    first_trust_deed_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_trust_deed_lender: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    first_trust_deed_payment: Mapped[float | None] = mapped_column(Float, nullable=True)
    second_trust_deed_balance: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    second_trust_deed_lender: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    second_trust_deed_payment: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    second_trust_deed_terms: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    title_company: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── 97-101: Notes & Metadata ─────────────────────────────────────────
    amenities: Mapped[str | None] = mapped_column(Text, nullable=True)
    sewer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transaction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_status: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SalesData(id={self.id}, comp_id={self.comp_id}, "
            f"address={self.property_address}, sale_date={self.sale_date})>"
        )
