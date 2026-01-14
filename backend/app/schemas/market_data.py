"""
Market data schemas for API request/response validation.
"""

from datetime import datetime

from pydantic import Field

from .base import BaseSchema


class SubmarketMetrics(BaseSchema):
    """Schema for submarket performance metrics."""

    name: str = Field(..., description="Submarket name")
    avg_rent: float = Field(..., description="Average rent per unit")
    rent_growth: float = Field(..., description="Year-over-year rent growth rate")
    occupancy: float = Field(..., description="Occupancy rate (0-1)")
    cap_rate: float = Field(..., description="Average cap rate (0-1)")
    inventory: int = Field(..., description="Total unit inventory")
    absorption: int = Field(..., description="Net absorption (units)")


class MarketTrend(BaseSchema):
    """Schema for monthly market trend data."""

    month: str = Field(..., description="Month label (e.g., Jan, Feb)")
    rent_growth: float = Field(..., description="Rent growth rate")
    occupancy: float = Field(..., description="Occupancy rate")
    cap_rate: float = Field(..., description="Average cap rate")


class EconomicIndicator(BaseSchema):
    """Schema for economic indicator data."""

    indicator: str = Field(..., description="Indicator name")
    value: float = Field(..., description="Current value")
    yoy_change: float = Field(..., description="Year-over-year change")
    unit: str = Field(..., description="Unit of measurement (%, $, etc.)")


class MSAOverview(BaseSchema):
    """Schema for MSA (Metropolitan Statistical Area) overview."""

    population: int = Field(..., description="Total population")
    employment: int = Field(..., description="Total employment")
    gdp: float = Field(..., description="GDP in dollars")
    population_growth: float = Field(..., description="Population growth rate")
    employment_growth: float = Field(..., description="Employment growth rate")
    gdp_growth: float = Field(..., description="GDP growth rate")
    last_updated: str = Field(..., description="Last update date (YYYY-MM-DD)")


class MonthlyMarketData(BaseSchema):
    """Schema for monthly market data with economic metrics."""

    month: str = Field(..., description="Month label")
    rent_growth: float = Field(..., description="Rent growth rate")
    occupancy: float = Field(..., description="Occupancy rate")
    cap_rate: float = Field(..., description="Average cap rate")
    employment: int = Field(..., description="Total employment")
    population: int = Field(..., description="Total population")


class PropertyComparable(BaseSchema):
    """Schema for property comparable data."""

    id: str = Field(..., description="Property ID")
    name: str = Field(..., description="Property name")
    address: str = Field(..., description="Property address")
    submarket: str = Field(..., description="Submarket name")
    units: int = Field(..., description="Number of units")
    year_built: int = Field(..., description="Year built")
    avg_rent: float = Field(..., description="Average rent")
    occupancy: float = Field(..., description="Occupancy rate")
    sale_price: float | None = Field(None, description="Recent sale price if sold")
    sale_date: str | None = Field(None, description="Sale date if sold")
    cap_rate: float | None = Field(None, description="Cap rate at sale")


# ==================== Response Schemas ====================


class MarketOverviewResponse(BaseSchema):
    """Response schema for market overview."""

    msa_overview: MSAOverview
    economic_indicators: list[EconomicIndicator]
    last_updated: datetime
    source: str = "computed"


class SubmarketsResponse(BaseSchema):
    """Response schema for submarket breakdown."""

    submarkets: list[SubmarketMetrics]
    total_inventory: int
    total_absorption: int
    average_occupancy: float
    average_rent_growth: float
    last_updated: datetime
    source: str = "computed"


class MarketTrendsResponse(BaseSchema):
    """Response schema for market trends."""

    trends: list[MarketTrend]
    monthly_data: list[MonthlyMarketData]
    period: str = Field("12M", description="Period covered (e.g., 12M, 24M)")
    last_updated: datetime
    source: str = "computed"


class ComparablesResponse(BaseSchema):
    """Response schema for property comparables."""

    comparables: list[PropertyComparable]
    total: int
    radius_miles: float = Field(5.0, description="Search radius in miles")
    last_updated: datetime
    source: str = "computed"
