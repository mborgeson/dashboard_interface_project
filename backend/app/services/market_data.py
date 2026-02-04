"""
Market data service for computing market metrics.

This service provides market data by:
1. Querying the dashboard_market_data PostgreSQL database (CoStar + FRED + Census data) if configured
2. Falling back to realistic static data for Phoenix MSA

Configure MARKET_ANALYSIS_DB_URL env var to enable real data.
Required tables (see database/schemas/market_data_schema.sql):
  - costar_timeseries / costar_latest  (materialized view)
  - fred_timeseries / fred_latest      (materialized view)
  - census_timeseries
"""

from datetime import datetime

from loguru import logger

from app.core.config import settings
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

# Optional: async DB engine for market_analysis database
_market_engine = None
_market_db_available = False
_market_data_freshness: str | None = None


async def _get_market_engine():
    """Lazily create async engine for market_analysis DB."""
    global _market_engine, _market_db_available, _market_data_freshness

    if _market_engine is not None:
        return _market_engine

    db_url = settings.MARKET_ANALYSIS_DB_URL
    if not db_url:
        _market_db_available = False
        return None

    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        _market_engine = create_async_engine(async_url, pool_size=3, max_overflow=2)

        # Test connection and get data freshness
        from sqlalchemy import text

        async with _market_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT MAX(date) FROM costar_timeseries WHERE is_forecast = FALSE LIMIT 1")
            )
            row = result.fetchone()
            if row and row[0]:
                _market_data_freshness = str(row[0])

        _market_db_available = True
        logger.info(
            f"Market analysis DB connected, data as of {_market_data_freshness}"
        )
        return _market_engine
    except Exception as e:
        logger.warning(f"Market analysis DB not available: {e}")
        _market_db_available = False
        _market_engine = None
        return None


def _extract_submarket_name(geography_name: str) -> str:
    """Extract submarket name from CoStar geography string.

    'Phoenix - AZ USA - Tempe' → 'Tempe'
    'Phoenix - AZ USA - North West Valley ' → 'North West Valley'
    """
    parts = geography_name.split(" - ")
    if len(parts) >= 3:
        return parts[-1].strip()
    return geography_name.strip()


class MarketDataService:
    """Service for market data operations."""

    def __init__(self):
        """Initialize market data service."""
        self._last_updated = datetime.now()

    async def get_market_overview(self) -> MarketOverviewResponse:
        """
        Get market overview with MSA stats and economic indicators.
        Tries market_analysis DB first, falls back to static data.
        """
        engine = await _get_market_engine()

        if engine and _market_db_available:
            try:
                return await self._get_overview_from_db(engine)
            except Exception as e:
                logger.warning(f"Failed to query market DB for overview: {e}")

        return self._get_overview_static()

    async def _get_overview_from_db(self, engine) -> MarketOverviewResponse:
        """Query market_analysis DB for economic indicators."""
        from sqlalchemy import text

        async with engine.connect() as conn:
            indicators = []

            # Unemployment from FRED
            unemp_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PHOE004UR'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            unemp_rows = unemp_result.fetchall()
            if unemp_rows:
                current_unemp = float(unemp_rows[0][0])
                prev_unemp = float(unemp_rows[1][0]) if len(unemp_rows) > 1 else current_unemp
                indicators.append(
                    EconomicIndicator(
                        indicator="Unemployment Rate",
                        value=current_unemp,
                        yoy_change=round(current_unemp - prev_unemp, 2),
                        unit="%",
                    )
                )

            # Employment from FRED (job growth YoY)
            emp_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PHOE004NA'
                    ORDER BY date DESC LIMIT 13
                """)
            )
            emp_rows = emp_result.fetchall()
            if emp_rows and len(emp_rows) >= 2:
                current_emp = float(emp_rows[0][0])
                prev_emp = float(emp_rows[-1][0])
                job_growth = round((current_emp - prev_emp) / prev_emp * 100, 1) if prev_emp else 0
                indicators.append(
                    EconomicIndicator(
                        indicator="Job Growth Rate",
                        value=job_growth,
                        yoy_change=0,
                        unit="%",
                    )
                )

            # Median Household Income from CoStar or Census
            income_result = await conn.execute(
                text("""
                    SELECT value FROM costar_latest
                    WHERE concept = 'Median Household Income'
                    AND geography_type = 'Metro'
                    LIMIT 1
                """)
            )
            income_row = income_result.fetchone()
            if not income_row:
                # Fallback to Census
                income_result = await conn.execute(
                    text("""
                        SELECT value FROM census_timeseries
                        WHERE variable_code = 'B19013_001E'
                        ORDER BY year DESC LIMIT 1
                    """)
                )
                income_row = income_result.fetchone()
            if income_row:
                indicators.append(
                    EconomicIndicator(
                        indicator="Median Household Income",
                        value=float(income_row[0]),
                        yoy_change=0,
                        unit="$",
                    )
                )

            # Population from CoStar or Census
            pop_result = await conn.execute(
                text("""
                    SELECT value FROM costar_latest
                    WHERE concept = 'Population'
                    AND geography_type = 'Metro'
                    LIMIT 1
                """)
            )
            pop_row = pop_result.fetchone()
            pop_value = int(float(pop_row[0])) if pop_row else None

            if not pop_value:
                census_pop = await conn.execute(
                    text("""
                        SELECT value FROM census_timeseries
                        WHERE variable_code = 'B01003_001E'
                        ORDER BY year DESC LIMIT 1
                    """)
                )
                census_row = census_pop.fetchone()
                if census_row:
                    pop_value = int(float(census_row[0]))

            # Population growth from Census (compare last 2 years)
            pop_growth_result = await conn.execute(
                text("""
                    SELECT value, year FROM census_timeseries
                    WHERE variable_code = 'B01003_001E'
                    ORDER BY year DESC LIMIT 2
                """)
            )
            pop_growth_rows = pop_growth_result.fetchall()
            if len(pop_growth_rows) >= 2:
                pop_growth = round(
                    (float(pop_growth_rows[0][0]) - float(pop_growth_rows[1][0]))
                    / float(pop_growth_rows[1][0]),
                    4,
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Population Growth",
                        value=round(pop_growth * 100, 1),
                        yoy_change=0,
                        unit="%",
                    )
                )

            # Fill missing indicators with static defaults
            indicator_names = {i.indicator for i in indicators}
            for default in self._get_overview_static().economic_indicators:
                if default.indicator not in indicator_names:
                    indicators.append(default)

            employment_val = int(float(emp_rows[0][0]) * 1000) if emp_rows else 2450000

            msa_overview = MSAOverview(
                population=pop_value or 5100000,
                employment=employment_val,
                gdp=263000000000,
                population_growth=pop_growth if len(pop_growth_rows) >= 2 else 0.023,
                employment_growth=job_growth / 100 if emp_rows else 0.032,
                gdp_growth=0.041,
                last_updated=_market_data_freshness or datetime.now().strftime("%Y-%m-%d"),
            )

            return MarketOverviewResponse(
                msa_overview=msa_overview,
                economic_indicators=indicators,
                last_updated=self._last_updated,
                source="database",
            )

    def _get_overview_static(self) -> MarketOverviewResponse:
        """Static fallback for market overview."""
        msa_overview = MSAOverview(
            population=5100000,
            employment=2450000,
            gdp=263000000000,
            population_growth=0.023,
            employment_growth=0.032,
            gdp_growth=0.041,
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )

        economic_indicators = [
            EconomicIndicator(indicator="Unemployment Rate", value=3.6, yoy_change=-0.4, unit="%"),
            EconomicIndicator(indicator="Job Growth Rate", value=3.2, yoy_change=0.8, unit="%"),
            EconomicIndicator(indicator="Median Household Income", value=72500, yoy_change=0.045, unit="$"),
            EconomicIndicator(indicator="Population Growth", value=2.3, yoy_change=0.2, unit="%"),
        ]

        return MarketOverviewResponse(
            msa_overview=msa_overview,
            economic_indicators=economic_indicators,
            last_updated=self._last_updated,
            source="static",
        )

    async def get_submarkets(self) -> SubmarketsResponse:
        """
        Get submarket breakdown with performance metrics.
        Tries market_analysis DB first, falls back to static data.
        """
        engine = await _get_market_engine()

        if engine and _market_db_available:
            try:
                return await self._get_submarkets_from_db(engine)
            except Exception as e:
                logger.warning(f"Failed to query market DB for submarkets: {e}")

        return self._get_submarkets_static()

    async def _get_submarkets_from_db(self, engine) -> SubmarketsResponse:
        """Query market_analysis DB for submarket data from CoStar."""
        from sqlalchemy import text

        async with engine.connect() as conn:
            # Pivot costar_latest for submarket-level data
            result = await conn.execute(
                text("""
                    SELECT
                        geography_name,
                        MAX(CASE WHEN concept = 'Market Asking Rent/Unit' THEN value END) as avg_rent,
                        MAX(CASE WHEN concept = 'Market Asking Rent Growth' THEN value END) as rent_growth,
                        MAX(CASE WHEN concept = 'Vacancy Rate' THEN value END) as vacancy,
                        MAX(CASE WHEN concept = 'Market Cap Rate' THEN value END) as cap_rate,
                        MAX(CASE WHEN concept = 'Inventory Units' THEN value END) as inventory,
                        MAX(CASE WHEN concept = 'Absorption Units' THEN value END) as absorption
                    FROM costar_latest
                    WHERE geography_type = 'Submarket'
                    GROUP BY geography_name
                    ORDER BY geography_name
                """)
            )
            rows = result.fetchall()

            if not rows:
                return self._get_submarkets_static()

            submarkets = []
            for row in rows:
                name = _extract_submarket_name(row[0])
                vacancy = float(row[3]) if row[3] is not None else 0.05
                # CoStar vacancy is already a decimal (e.g. 0.094)
                occupancy = round(1 - vacancy, 4) if vacancy < 1 else round(1 - vacancy / 100, 4)
                rent_growth = float(row[2]) if row[2] is not None else 0.0
                # CoStar rent growth might be decimal (e.g. -0.04 = -4%) — keep as-is

                submarkets.append(
                    SubmarketMetrics(
                        name=name,
                        avg_rent=int(float(row[1])) if row[1] else 1500,
                        rent_growth=rent_growth,
                        occupancy=occupancy,
                        cap_rate=float(row[4]) if row[4] is not None else 0.05,
                        inventory=int(float(row[5])) if row[5] else 0,
                        absorption=int(float(row[6])) if row[6] else 0,
                    )
                )

            total_inventory = sum(s.inventory for s in submarkets)
            total_absorption = sum(s.absorption for s in submarkets)
            avg_occupancy = (
                sum(s.occupancy * s.inventory for s in submarkets) / total_inventory
                if total_inventory
                else 0.95
            )
            avg_rent_growth = (
                sum(s.rent_growth * s.inventory for s in submarkets) / total_inventory
                if total_inventory
                else 0.05
            )

            return SubmarketsResponse(
                submarkets=submarkets,
                total_inventory=total_inventory,
                total_absorption=total_absorption,
                average_occupancy=round(avg_occupancy, 4),
                average_rent_growth=round(avg_rent_growth, 4),
                last_updated=self._last_updated,
                source="database",
            )

    def _get_submarkets_static(self) -> SubmarketsResponse:
        """Static fallback for submarket data."""
        submarkets = [
            SubmarketMetrics(name="Tempe", avg_rent=1650, rent_growth=0.065, occupancy=0.960, cap_rate=0.048, inventory=21000, absorption=285),
            SubmarketMetrics(name="East Valley", avg_rent=1500, rent_growth=0.060, occupancy=0.953, cap_rate=0.050, inventory=28500, absorption=340),
            SubmarketMetrics(name="Downtown Phoenix", avg_rent=1850, rent_growth=0.068, occupancy=0.965, cap_rate=0.045, inventory=18500, absorption=245),
            SubmarketMetrics(name="North Phoenix", avg_rent=1550, rent_growth=0.062, occupancy=0.955, cap_rate=0.049, inventory=22000, absorption=275),
            SubmarketMetrics(name="Deer Valley", avg_rent=1600, rent_growth=0.064, occupancy=0.958, cap_rate=0.047, inventory=17500, absorption=230),
            SubmarketMetrics(name="Chandler", avg_rent=1750, rent_growth=0.070, occupancy=0.963, cap_rate=0.046, inventory=19800, absorption=268),
            SubmarketMetrics(name="Gilbert", avg_rent=1800, rent_growth=0.069, occupancy=0.964, cap_rate=0.047, inventory=16700, absorption=221),
            SubmarketMetrics(name="Old Town Scottsdale", avg_rent=2150, rent_growth=0.072, occupancy=0.970, cap_rate=0.042, inventory=15200, absorption=198),
            SubmarketMetrics(name="North West Valley", avg_rent=1450, rent_growth=0.058, occupancy=0.950, cap_rate=0.052, inventory=25000, absorption=310),
            SubmarketMetrics(name="South West Valley", avg_rent=1400, rent_growth=0.055, occupancy=0.948, cap_rate=0.053, inventory=20000, absorption=250),
            SubmarketMetrics(name="South Phoenix", avg_rent=1350, rent_growth=0.052, occupancy=0.945, cap_rate=0.054, inventory=14000, absorption=170),
            SubmarketMetrics(name="North Scottsdale", avg_rent=2300, rent_growth=0.074, occupancy=0.972, cap_rate=0.040, inventory=12000, absorption=155),
            SubmarketMetrics(name="West Maricopa County", avg_rent=1400, rent_growth=0.054, occupancy=0.946, cap_rate=0.055, inventory=18000, absorption=220),
            SubmarketMetrics(name="Camelback", avg_rent=1900, rent_growth=0.071, occupancy=0.968, cap_rate=0.044, inventory=14500, absorption=190),
            SubmarketMetrics(name="Southeast Valley", avg_rent=1650, rent_growth=0.063, occupancy=0.957, cap_rate=0.049, inventory=13000, absorption=165),
        ]

        total_inventory = sum(s.inventory for s in submarkets)
        total_absorption = sum(s.absorption for s in submarkets)
        avg_occupancy = sum(s.occupancy * s.inventory for s in submarkets) / total_inventory
        avg_rent_growth = sum(s.rent_growth * s.inventory for s in submarkets) / total_inventory

        return SubmarketsResponse(
            submarkets=submarkets,
            total_inventory=total_inventory,
            total_absorption=total_absorption,
            average_occupancy=round(avg_occupancy, 4),
            average_rent_growth=round(avg_rent_growth, 4),
            last_updated=self._last_updated,
            source="static",
        )

    async def get_market_trends(self, period_months: int = 12) -> MarketTrendsResponse:
        """
        Get market trends over time.
        Tries market_analysis DB first, falls back to static data.
        """
        engine = await _get_market_engine()

        if engine and _market_db_available:
            try:
                return await self._get_trends_from_db(engine, period_months)
            except Exception as e:
                logger.warning(f"Failed to query market DB for trends: {e}")

        return self._get_trends_static(period_months)

    async def _get_trends_from_db(self, engine, period_months: int) -> MarketTrendsResponse:
        """Query market_analysis DB for trailing trend data from CoStar."""
        from sqlalchemy import text

        # Convert months to quarters (CoStar is quarterly)
        num_quarters = max(period_months // 3, 4)

        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT
                        date,
                        TO_CHAR(date, 'Mon YYYY') as label,
                        MAX(CASE WHEN concept = 'Market Asking Rent Growth' THEN value END) as rent_growth,
                        MAX(CASE WHEN concept = 'Vacancy Rate' THEN value END) as vacancy,
                        MAX(CASE WHEN concept = 'Market Cap Rate' THEN value END) as cap_rate
                    FROM costar_timeseries
                    WHERE geography_type = 'Metro'
                    AND is_forecast = FALSE
                    AND concept IN ('Market Asking Rent Growth', 'Vacancy Rate', 'Market Cap Rate')
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT :limit
                """),
                {"limit": num_quarters},
            )
            rows = result.fetchall()

            if not rows:
                return self._get_trends_static(period_months)

            # Reverse to chronological order
            rows = list(reversed(rows))

            trends = []
            monthly_data = []
            for row in rows:
                vacancy = float(row[3]) if row[3] is not None else 0.05
                rg = float(row[2]) if row[2] is not None else 0.0
                occ = round(1 - vacancy, 4) if vacancy < 1 else round(1 - vacancy / 100, 4)
                cr = float(row[4]) if row[4] is not None else 0.05

                trends.append(
                    MarketTrend(month=row[1], rent_growth=rg, occupancy=occ, cap_rate=cr)
                )
                monthly_data.append(
                    MonthlyMarketData(
                        month=row[1], rent_growth=rg, occupancy=occ,
                        cap_rate=cr, employment=0, population=0,
                    )
                )

            return MarketTrendsResponse(
                trends=trends,
                monthly_data=monthly_data,
                period=f"{period_months}M",
                last_updated=self._last_updated,
                source="database",
            )

    def _get_trends_static(self, period_months: int) -> MarketTrendsResponse:
        """Static fallback for trend data."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        base_rent_growth = 0.048
        base_occupancy = 0.945
        base_cap_rate = 0.052
        base_employment = 2380000
        base_population = 5020000

        trends = []
        monthly_data = []

        for i, month in enumerate(months[:period_months]):
            progress = i / 11.0
            rent_growth = base_rent_growth + (0.018 * progress)
            occupancy = base_occupancy + (0.016 * progress)
            cap_rate = base_cap_rate - (0.006 * progress)
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
            source="static",
        )

    async def get_comparables(
        self,
        property_id: str | None = None,
        submarket: str | None = None,
        radius_miles: float = 5.0,
        limit: int = 10,
    ) -> ComparablesResponse:
        """Get property comparables. Static data — no DB source for sales comps yet."""
        all_comparables = [
            PropertyComparable(id="comp-001", name="Desert Ridge Apartments", address="1200 N Tatum Blvd, Phoenix, AZ 85028", submarket="Scottsdale", units=288, year_built=2019, avg_rent=2100, occupancy=0.965, sale_price=85000000, sale_date="2024-08-15", cap_rate=0.044),
            PropertyComparable(id="comp-002", name="Tempe Gateway", address="850 S Mill Ave, Tempe, AZ 85281", submarket="Tempe", units=320, year_built=2020, avg_rent=1680, occupancy=0.958, sale_price=72000000, sale_date="2024-06-20", cap_rate=0.047),
            PropertyComparable(id="comp-003", name="Chandler Crossing", address="3200 W Chandler Blvd, Chandler, AZ 85226", submarket="Chandler", units=256, year_built=2018, avg_rent=1720, occupancy=0.962, sale_price=None, sale_date=None, cap_rate=None),
            PropertyComparable(id="comp-004", name="Gilbert Town Center", address="275 N Gilbert Rd, Gilbert, AZ 85234", submarket="Gilbert", units=198, year_built=2021, avg_rent=1850, occupancy=0.971, sale_price=52000000, sale_date="2024-10-05", cap_rate=0.045),
            PropertyComparable(id="comp-005", name="Mesa Riverview", address="2150 W Rio Salado Pkwy, Mesa, AZ 85201", submarket="Mesa", units=342, year_built=2017, avg_rent=1420, occupancy=0.948, sale_price=62000000, sale_date="2024-03-12", cap_rate=0.052),
            PropertyComparable(id="comp-006", name="Downtown Phoenix Lofts", address="100 E Van Buren St, Phoenix, AZ 85004", submarket="Downtown Phoenix", units=180, year_built=2022, avg_rent=1900, occupancy=0.967, sale_price=None, sale_date=None, cap_rate=None),
            PropertyComparable(id="comp-007", name="Scottsdale Quarter Living", address="15279 N Scottsdale Rd, Scottsdale, AZ 85254", submarket="Scottsdale", units=225, year_built=2020, avg_rent=2280, occupancy=0.974, sale_price=68000000, sale_date="2024-11-08", cap_rate=0.041),
            PropertyComparable(id="comp-008", name="Tempe Urban Living", address="600 S College Ave, Tempe, AZ 85281", submarket="Tempe", units=275, year_built=2019, avg_rent=1620, occupancy=0.955, sale_price=None, sale_date=None, cap_rate=None),
        ]

        comparables = all_comparables
        if submarket:
            comparables = [c for c in comparables if c.submarket.lower() == submarket.lower()]
        comparables = comparables[:limit]

        return ComparablesResponse(
            comparables=comparables,
            total=len(comparables),
            radius_miles=radius_miles,
            last_updated=self._last_updated,
            source="static",
        )


# Singleton instance
market_data_service = MarketDataService()
