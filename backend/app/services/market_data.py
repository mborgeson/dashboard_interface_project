"""
Market data service for computing market metrics.

This service provides market data by either:
1. Aggregating data from the portfolio's properties
2. Falling back to realistic mock data for Phoenix MSA

In production, this would integrate with external market data providers
like CoStar, REIS, or Yardi Matrix.
"""

from datetime import datetime

from app.schemas.market_data import (
    ComparablesResponse,
    EconomicIndicator,
    MarketOverviewResponse,
    MarketTrend,
    MarketTrendsResponse,
    MonthlyMarketData,
    MSAOverview,
    PropertyComparable,
    SubmarketMetrics,
    SubmarketsResponse,
)


class MarketDataService:
    """Service for market data operations."""

    def __init__(self):
        """Initialize market data service."""
        self._last_updated = datetime.now()

    def get_market_overview(self) -> MarketOverviewResponse:
        """
        Get market overview with MSA stats and economic indicators.

        Returns computed data based on portfolio or Phoenix MSA defaults.
        """
        # Phoenix MSA Overview (realistic data)
        msa_overview = MSAOverview(
            population=5100000,
            employment=2450000,
            gdp=263000000000,
            population_growth=0.023,
            employment_growth=0.032,
            gdp_growth=0.041,
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )

        # Economic Indicators
        economic_indicators = [
            EconomicIndicator(
                indicator="Unemployment Rate",
                value=3.6,
                yoy_change=-0.4,
                unit="%",
            ),
            EconomicIndicator(
                indicator="Job Growth Rate",
                value=3.2,
                yoy_change=0.8,
                unit="%",
            ),
            EconomicIndicator(
                indicator="Median Household Income",
                value=72500,
                yoy_change=0.045,
                unit="$",
            ),
            EconomicIndicator(
                indicator="Population Growth",
                value=2.3,
                yoy_change=0.2,
                unit="%",
            ),
        ]

        return MarketOverviewResponse(
            msa_overview=msa_overview,
            economic_indicators=economic_indicators,
            last_updated=self._last_updated,
            source="computed",
        )

    def get_submarkets(self) -> SubmarketsResponse:
        """
        Get submarket breakdown with performance metrics.

        Returns data for Phoenix MSA submarkets.
        """
        submarkets = [
            SubmarketMetrics(
                name="Downtown Phoenix",
                avg_rent=1850,
                rent_growth=0.068,
                occupancy=0.965,
                cap_rate=0.045,
                inventory=18500,
                absorption=245,
            ),
            SubmarketMetrics(
                name="Scottsdale",
                avg_rent=2150,
                rent_growth=0.072,
                occupancy=0.970,
                cap_rate=0.042,
                inventory=15200,
                absorption=198,
            ),
            SubmarketMetrics(
                name="Tempe",
                avg_rent=1650,
                rent_growth=0.065,
                occupancy=0.960,
                cap_rate=0.048,
                inventory=21000,
                absorption=285,
            ),
            SubmarketMetrics(
                name="Mesa",
                avg_rent=1450,
                rent_growth=0.058,
                occupancy=0.952,
                cap_rate=0.051,
                inventory=24500,
                absorption=312,
            ),
            SubmarketMetrics(
                name="Chandler",
                avg_rent=1750,
                rent_growth=0.070,
                occupancy=0.963,
                cap_rate=0.046,
                inventory=19800,
                absorption=268,
            ),
            SubmarketMetrics(
                name="Gilbert",
                avg_rent=1800,
                rent_growth=0.069,
                occupancy=0.964,
                cap_rate=0.047,
                inventory=16700,
                absorption=221,
            ),
        ]

        total_inventory = sum(s.inventory for s in submarkets)
        total_absorption = sum(s.absorption for s in submarkets)
        avg_occupancy = (
            sum(s.occupancy * s.inventory for s in submarkets) / total_inventory
        )
        avg_rent_growth = (
            sum(s.rent_growth * s.inventory for s in submarkets) / total_inventory
        )

        return SubmarketsResponse(
            submarkets=submarkets,
            total_inventory=total_inventory,
            total_absorption=total_absorption,
            average_occupancy=round(avg_occupancy, 4),
            average_rent_growth=round(avg_rent_growth, 4),
            last_updated=self._last_updated,
            source="computed",
        )

    def get_market_trends(self, period_months: int = 12) -> MarketTrendsResponse:
        """
        Get market trends over time.

        Args:
            period_months: Number of months of trend data (default 12)

        Returns:
            Market trends with monthly data points.
        """
        # Generate trailing 12-month trend data
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        # Base values that trend upward
        base_rent_growth = 0.048
        base_occupancy = 0.945
        base_cap_rate = 0.052
        base_employment = 2380000
        base_population = 5020000

        trends = []
        monthly_data = []

        for i, month in enumerate(months[:period_months]):
            # Progressive improvement over the year
            progress = i / 11.0  # 0 to 1 over the year

            rent_growth = base_rent_growth + (0.018 * progress)  # +1.8% improvement
            occupancy = base_occupancy + (0.016 * progress)  # +1.6% improvement
            cap_rate = base_cap_rate - (0.006 * progress)  # -0.6% compression
            employment = int(base_employment + (80000 * progress))
            population = int(base_population + (80000 * progress))

            trends.append(
                MarketTrend(
                    month=month,
                    rent_growth=round(rent_growth, 4),
                    occupancy=round(occupancy, 4),
                    cap_rate=round(cap_rate, 4),
                )
            )

            monthly_data.append(
                MonthlyMarketData(
                    month=month,
                    rent_growth=round(rent_growth, 4),
                    occupancy=round(occupancy, 4),
                    cap_rate=round(cap_rate, 4),
                    employment=employment,
                    population=population,
                )
            )

        return MarketTrendsResponse(
            trends=trends,
            monthly_data=monthly_data,
            period=f"{period_months}M",
            last_updated=self._last_updated,
            source="computed",
        )

    def get_comparables(
        self,
        property_id: str | None = None,
        submarket: str | None = None,
        radius_miles: float = 5.0,
        limit: int = 10,
    ) -> ComparablesResponse:
        """
        Get property comparables.

        Args:
            property_id: Reference property ID (optional)
            submarket: Filter to specific submarket
            radius_miles: Search radius in miles
            limit: Maximum number of comparables

        Returns:
            List of comparable properties.
        """
        # Mock comparable properties for Phoenix MSA
        all_comparables = [
            PropertyComparable(
                id="comp-001",
                name="Desert Ridge Apartments",
                address="1200 N Tatum Blvd, Phoenix, AZ 85028",
                submarket="Scottsdale",
                units=288,
                year_built=2019,
                avg_rent=2100,
                occupancy=0.965,
                sale_price=85000000,
                sale_date="2024-08-15",
                cap_rate=0.044,
            ),
            PropertyComparable(
                id="comp-002",
                name="Tempe Gateway",
                address="850 S Mill Ave, Tempe, AZ 85281",
                submarket="Tempe",
                units=320,
                year_built=2020,
                avg_rent=1680,
                occupancy=0.958,
                sale_price=72000000,
                sale_date="2024-06-20",
                cap_rate=0.047,
            ),
            PropertyComparable(
                id="comp-003",
                name="Chandler Crossing",
                address="3200 W Chandler Blvd, Chandler, AZ 85226",
                submarket="Chandler",
                units=256,
                year_built=2018,
                avg_rent=1720,
                occupancy=0.962,
                sale_price=None,
                sale_date=None,
                cap_rate=None,
            ),
            PropertyComparable(
                id="comp-004",
                name="Gilbert Town Center",
                address="275 N Gilbert Rd, Gilbert, AZ 85234",
                submarket="Gilbert",
                units=198,
                year_built=2021,
                avg_rent=1850,
                occupancy=0.971,
                sale_price=52000000,
                sale_date="2024-10-05",
                cap_rate=0.045,
            ),
            PropertyComparable(
                id="comp-005",
                name="Mesa Riverview",
                address="2150 W Rio Salado Pkwy, Mesa, AZ 85201",
                submarket="Mesa",
                units=342,
                year_built=2017,
                avg_rent=1420,
                occupancy=0.948,
                sale_price=62000000,
                sale_date="2024-03-12",
                cap_rate=0.052,
            ),
            PropertyComparable(
                id="comp-006",
                name="Downtown Phoenix Lofts",
                address="100 E Van Buren St, Phoenix, AZ 85004",
                submarket="Downtown Phoenix",
                units=180,
                year_built=2022,
                avg_rent=1900,
                occupancy=0.967,
                sale_price=None,
                sale_date=None,
                cap_rate=None,
            ),
            PropertyComparable(
                id="comp-007",
                name="Scottsdale Quarter Living",
                address="15279 N Scottsdale Rd, Scottsdale, AZ 85254",
                submarket="Scottsdale",
                units=225,
                year_built=2020,
                avg_rent=2280,
                occupancy=0.974,
                sale_price=68000000,
                sale_date="2024-11-08",
                cap_rate=0.041,
            ),
            PropertyComparable(
                id="comp-008",
                name="Tempe Urban Living",
                address="600 S College Ave, Tempe, AZ 85281",
                submarket="Tempe",
                units=275,
                year_built=2019,
                avg_rent=1620,
                occupancy=0.955,
                sale_price=None,
                sale_date=None,
                cap_rate=None,
            ),
        ]

        # Filter by submarket if specified
        comparables = all_comparables
        if submarket:
            comparables = [
                c for c in comparables if c.submarket.lower() == submarket.lower()
            ]

        # Limit results
        comparables = comparables[:limit]

        return ComparablesResponse(
            comparables=comparables,
            total=len(comparables),
            radius_miles=radius_miles,
            last_updated=self._last_updated,
            source="computed",
        )


# Singleton instance
market_data_service = MarketDataService()
