"""
Property schemas for API request/response validation.
"""
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field

from .base import BaseSchema, TimestampSchema


class PropertyBase(BaseSchema):
    """Base property schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    property_type: str = Field(
        ...,
        pattern="^(multifamily|office|retail|industrial|mixed_use|other)$"
    )

    # Location
    address: str = Field(..., max_length=500)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=50)
    zip_code: str = Field(..., max_length=20)
    county: str | None = Field(None, max_length=100)
    market: str | None = Field(None, max_length=100)
    submarket: str | None = Field(None, max_length=100)

    # Physical Characteristics
    year_built: int | None = Field(None, ge=1800, le=2100)
    year_renovated: int | None = Field(None, ge=1800, le=2100)
    total_units: int | None = Field(None, ge=0)
    total_sf: int | None = Field(None, ge=0)
    lot_size_acres: Decimal | None = Field(None, ge=0)
    stories: int | None = Field(None, ge=1)
    parking_spaces: int | None = Field(None, ge=0)


class PropertyCreate(PropertyBase):
    """Schema for creating a new property."""

    # Financial Metrics (optional on create)
    purchase_price: Decimal | None = Field(None, ge=0)
    current_value: Decimal | None = Field(None, ge=0)
    acquisition_date: date | None = None

    # Operating Metrics
    occupancy_rate: Decimal | None = Field(None, ge=0, le=100)
    avg_rent_per_unit: Decimal | None = Field(None, ge=0)
    avg_rent_per_sf: Decimal | None = Field(None, ge=0)
    noi: Decimal | None = None
    cap_rate: Decimal | None = Field(None, ge=0, le=1)

    # Additional Data
    description: str | None = None
    amenities: dict[str, Any] | None = None
    unit_mix: dict[str, Any] | None = None
    images: list[str] | None = None
    external_id: str | None = Field(None, max_length=100)
    data_source: str | None = Field(None, max_length=50)


class PropertyUpdate(BaseSchema):
    """Schema for updating a property. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    property_type: str | None = Field(
        None,
        pattern="^(multifamily|office|retail|industrial|mixed_use|other)$"
    )

    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=50)
    zip_code: str | None = Field(None, max_length=20)
    county: str | None = Field(None, max_length=100)
    market: str | None = Field(None, max_length=100)
    submarket: str | None = Field(None, max_length=100)

    year_built: int | None = Field(None, ge=1800, le=2100)
    year_renovated: int | None = Field(None, ge=1800, le=2100)
    total_units: int | None = Field(None, ge=0)
    total_sf: int | None = Field(None, ge=0)
    lot_size_acres: Decimal | None = Field(None, ge=0)
    stories: int | None = Field(None, ge=1)
    parking_spaces: int | None = Field(None, ge=0)

    purchase_price: Decimal | None = Field(None, ge=0)
    current_value: Decimal | None = Field(None, ge=0)
    acquisition_date: date | None = None

    occupancy_rate: Decimal | None = Field(None, ge=0, le=100)
    avg_rent_per_unit: Decimal | None = Field(None, ge=0)
    avg_rent_per_sf: Decimal | None = Field(None, ge=0)
    noi: Decimal | None = None
    cap_rate: Decimal | None = Field(None, ge=0, le=1)

    description: str | None = None
    amenities: dict[str, Any] | None = None
    unit_mix: dict[str, Any] | None = None
    images: list[str] | None = None


class PropertyResponse(PropertyBase, TimestampSchema):
    """Schema for property response."""

    id: int

    # Financial Metrics
    purchase_price: Decimal | None = None
    current_value: Decimal | None = None
    acquisition_date: date | None = None

    # Operating Metrics
    occupancy_rate: Decimal | None = None
    avg_rent_per_unit: Decimal | None = None
    avg_rent_per_sf: Decimal | None = None
    noi: Decimal | None = None
    cap_rate: Decimal | None = None

    # Additional Data
    description: str | None = None
    amenities: dict[str, Any] | None = None
    unit_mix: dict[str, Any] | None = None
    images: list[str] | None = None
    external_id: str | None = None
    data_source: str | None = None

    # Computed fields
    price_per_unit: Decimal | None = None
    price_per_sf: Decimal | None = None


class PropertyListResponse(BaseSchema):
    """Paginated list of properties."""

    items: list[PropertyResponse]
    total: int
    page: int
    page_size: int
