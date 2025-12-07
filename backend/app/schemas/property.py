"""
Property schemas for API request/response validation.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, Any
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
    county: Optional[str] = Field(None, max_length=100)
    market: Optional[str] = Field(None, max_length=100)
    submarket: Optional[str] = Field(None, max_length=100)

    # Physical Characteristics
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    year_renovated: Optional[int] = Field(None, ge=1800, le=2100)
    total_units: Optional[int] = Field(None, ge=0)
    total_sf: Optional[int] = Field(None, ge=0)
    lot_size_acres: Optional[Decimal] = Field(None, ge=0)
    stories: Optional[int] = Field(None, ge=1)
    parking_spaces: Optional[int] = Field(None, ge=0)


class PropertyCreate(PropertyBase):
    """Schema for creating a new property."""

    # Financial Metrics (optional on create)
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    current_value: Optional[Decimal] = Field(None, ge=0)
    acquisition_date: Optional[date] = None

    # Operating Metrics
    occupancy_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    avg_rent_per_unit: Optional[Decimal] = Field(None, ge=0)
    avg_rent_per_sf: Optional[Decimal] = Field(None, ge=0)
    noi: Optional[Decimal] = None
    cap_rate: Optional[Decimal] = Field(None, ge=0, le=1)

    # Additional Data
    description: Optional[str] = None
    amenities: Optional[dict[str, Any]] = None
    unit_mix: Optional[dict[str, Any]] = None
    images: Optional[list[str]] = None
    external_id: Optional[str] = Field(None, max_length=100)
    data_source: Optional[str] = Field(None, max_length=50)


class PropertyUpdate(BaseSchema):
    """Schema for updating a property. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    property_type: Optional[str] = Field(
        None,
        pattern="^(multifamily|office|retail|industrial|mixed_use|other)$"
    )

    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    county: Optional[str] = Field(None, max_length=100)
    market: Optional[str] = Field(None, max_length=100)
    submarket: Optional[str] = Field(None, max_length=100)

    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    year_renovated: Optional[int] = Field(None, ge=1800, le=2100)
    total_units: Optional[int] = Field(None, ge=0)
    total_sf: Optional[int] = Field(None, ge=0)
    lot_size_acres: Optional[Decimal] = Field(None, ge=0)
    stories: Optional[int] = Field(None, ge=1)
    parking_spaces: Optional[int] = Field(None, ge=0)

    purchase_price: Optional[Decimal] = Field(None, ge=0)
    current_value: Optional[Decimal] = Field(None, ge=0)
    acquisition_date: Optional[date] = None

    occupancy_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    avg_rent_per_unit: Optional[Decimal] = Field(None, ge=0)
    avg_rent_per_sf: Optional[Decimal] = Field(None, ge=0)
    noi: Optional[Decimal] = None
    cap_rate: Optional[Decimal] = Field(None, ge=0, le=1)

    description: Optional[str] = None
    amenities: Optional[dict[str, Any]] = None
    unit_mix: Optional[dict[str, Any]] = None
    images: Optional[list[str]] = None


class PropertyResponse(PropertyBase, TimestampSchema):
    """Schema for property response."""

    id: int

    # Financial Metrics
    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    acquisition_date: Optional[date] = None

    # Operating Metrics
    occupancy_rate: Optional[Decimal] = None
    avg_rent_per_unit: Optional[Decimal] = None
    avg_rent_per_sf: Optional[Decimal] = None
    noi: Optional[Decimal] = None
    cap_rate: Optional[Decimal] = None

    # Additional Data
    description: Optional[str] = None
    amenities: Optional[dict[str, Any]] = None
    unit_mix: Optional[dict[str, Any]] = None
    images: Optional[list[str]] = None
    external_id: Optional[str] = None
    data_source: Optional[str] = None

    # Computed fields
    price_per_unit: Optional[Decimal] = None
    price_per_sf: Optional[Decimal] = None


class PropertyListResponse(BaseSchema):
    """Paginated list of properties."""

    items: list[PropertyResponse]
    total: int
    page: int
    page_size: int
