"""
Property model for real estate assets.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class Property(Base, TimestampMixin, SoftDeleteMixin):
    """Property model representing real estate assets."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    property_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # multifamily, office, retail, industrial

    # Location
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    submarket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )

    # Physical Characteristics
    building_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_sf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lot_size_acres: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    stories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Financial Metrics
    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    current_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Operating Metrics
    occupancy_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    avg_rent_per_unit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    avg_rent_per_sf: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    noi: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )
    cap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3),
        nullable=True,
    )

    # Extended Financial Data (JSON blob for nested frontend fields)
    financial_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Additional Data
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amenities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    unit_mix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # External IDs
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )
    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    # deals: Mapped[List["Deal"]] = relationship("Deal", back_populates="property")

    def __repr__(self) -> str:
        return f"<Property {self.name} ({self.city}, {self.state})>"

    @property
    def price_per_unit(self) -> Decimal | None:
        """Calculate price per unit."""
        if self.purchase_price and self.total_units:
            return self.purchase_price / self.total_units
        return None

    @property
    def price_per_sf(self) -> Decimal | None:
        """Calculate price per square foot."""
        if self.purchase_price and self.total_sf:
            return self.purchase_price / self.total_sf
        return None
