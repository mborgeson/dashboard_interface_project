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

Architecture:
  Each public method follows a 3-tier pattern:
    Database query -> Static fallback -> Empty/error
  Static methods are prefixed with _static_ and kept intact as fallbacks.
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


def _extract_submarket_name(geography_name: str) -> str:
    """Extract submarket name from CoStar geography string.

    'Phoenix - AZ USA - Tempe' -> 'Tempe'
    'Phoenix - AZ USA - North West Valley ' -> 'North West Valley'
    """
    parts = geography_name.split(" - ")
    if len(parts) >= 3:
        return parts[-1].strip()
    return geography_name.strip()


class MarketDataService:
    """Service for market data operations.

    Initialises an optional async engine for the market_analysis PostgreSQL
    database.  Every public method tries the database first, catches any
    exception, and falls back to the corresponding ``_static_*`` method so
    the API always returns data.
    """

    def __init__(self):
        """Initialize market data service and market DB engine."""
        self._last_updated = datetime.now()
        self._market_db_engine = None
        self._market_db_available = False
        self._market_data_freshness: str | None = None
        self._init_market_db()

    # ------------------------------------------------------------------
    # Engine initialisation
    # ------------------------------------------------------------------

    def _init_market_db(self):
        """Create async engine for market data database if URL configured.

        The engine is created lazily on first use if this synchronous init
        cannot import asyncpg (e.g. during tests).  The actual connection
        test happens in ``_ensure_market_db``.
        """
        if not settings.MARKET_ANALYSIS_DB_URL:
            logger.info(
                "MARKET_ANALYSIS_DB_URL not configured — using static market data"
            )
            return

        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            db_url = settings.MARKET_ANALYSIS_DB_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            self._market_db_engine = create_async_engine(
                db_url, pool_size=5, max_overflow=3
            )
            logger.info("Market analysis DB engine created (connection not yet tested)")
        except Exception as exc:
            logger.warning(f"Could not create market DB engine: {exc}")
            self._market_db_engine = None

    async def _ensure_market_db(self):
        """Ensure the market DB engine is connected and return it, or None.

        On first successful call the data-freshness timestamp is cached.
        """
        if self._market_db_engine is None:
            return None

        # Already verified
        if self._market_db_available:
            return self._market_db_engine

        try:
            from sqlalchemy import text

            async with self._market_db_engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT MAX(date) FROM costar_timeseries "
                        "WHERE is_forecast = FALSE LIMIT 1"
                    )
                )
                row = result.fetchone()
                if row and row[0]:
                    self._market_data_freshness = str(row[0])

            self._market_db_available = True
            logger.info(
                f"Market analysis DB connected, data as of {self._market_data_freshness}"
            )
            return self._market_db_engine
        except Exception as exc:
            logger.warning(f"Market analysis DB not available: {exc}")
            self._market_db_available = False
            return None

    # ==================================================================
    # get_market_overview
    # ==================================================================

    async def get_market_overview(self) -> MarketOverviewResponse:
        """Get market overview with MSA stats and economic indicators.

        Tries market_analysis DB first, falls back to static data.
        """
        engine = await self._ensure_market_db()

        if engine is not None:
            try:
                response = await self._db_get_market_overview(engine)
                logger.info("get_market_overview served from database")
                return response
            except Exception as exc:
                logger.warning(
                    f"DB query failed for market overview, using static fallback: {exc}"
                )

        logger.info("get_market_overview served from static_fallback")
        return self._static_get_market_overview()

    async def _db_get_market_overview(self, engine) -> MarketOverviewResponse:
        """Query market_analysis DB for MSA overview and economic indicators."""
        from sqlalchemy import text

        async with engine.connect() as conn:
            indicators: list[EconomicIndicator] = []

            # -- Unemployment Rate from FRED --
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
                prev_unemp = (
                    float(unemp_rows[1][0]) if len(unemp_rows) > 1 else current_unemp
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Unemployment Rate",
                        value=current_unemp,
                        yoy_change=round(current_unemp - prev_unemp, 2),
                        unit="%",
                    )
                )

            # -- Employment / Job Growth from FRED --
            emp_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PHOE004NA'
                    ORDER BY date DESC LIMIT 13
                """)
            )
            emp_rows = emp_result.fetchall()
            job_growth = 0.0
            if emp_rows and len(emp_rows) >= 2:
                current_emp = float(emp_rows[0][0])
                prev_emp = float(emp_rows[-1][0])
                job_growth = (
                    round((current_emp - prev_emp) / prev_emp * 100, 1)
                    if prev_emp
                    else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Job Growth Rate",
                        value=job_growth,
                        yoy_change=0,
                        unit="%",
                    )
                )

            # -- Median Household Income (CoStar -> Census fallback) --
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

            # -- Population (CoStar -> Census fallback) --
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

            # -- Population Growth from Census (compare last 2 years) --
            pop_growth = 0.023  # default
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
            for default in self._static_get_market_overview().economic_indicators:
                if default.indicator not in indicator_names:
                    indicators.append(default)

            employment_val = int(float(emp_rows[0][0]) * 1000) if emp_rows else 2450000

            msa_overview = MSAOverview(
                population=pop_value or 5100000,
                employment=employment_val,
                gdp=263000000000,
                population_growth=pop_growth,
                employment_growth=job_growth / 100 if emp_rows else 0.032,
                gdp_growth=0.041,
                last_updated=self._market_data_freshness
                or datetime.now().strftime("%Y-%m-%d"),
            )

            return MarketOverviewResponse(
                msa_overview=msa_overview,
                economic_indicators=indicators,
                last_updated=self._last_updated,
                source="database",
            )

    def _static_get_market_overview(self) -> MarketOverviewResponse:
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
            EconomicIndicator(
                indicator="Unemployment Rate", value=3.6, yoy_change=-0.4, unit="%"
            ),
            EconomicIndicator(
                indicator="Job Growth Rate", value=3.2, yoy_change=0.8, unit="%"
            ),
            EconomicIndicator(
                indicator="Median Household Income",
                value=72500,
                yoy_change=0.045,
                unit="$",
            ),
            EconomicIndicator(
                indicator="Population Growth", value=2.3, yoy_change=0.2, unit="%"
            ),
        ]

        return MarketOverviewResponse(
            msa_overview=msa_overview,
            economic_indicators=economic_indicators,
            last_updated=self._last_updated,
            source="static_fallback",
        )

    # ==================================================================
    # get_economic_indicators  (standalone — queries FRED + Census)
    # ==================================================================

    async def get_economic_indicators(self) -> list[EconomicIndicator]:
        """Get economic indicators independently of the full overview.

        Queries FRED for unemployment (PHOE004UR) and employment (PHOE004NA),
        Census for population/income, and CPI from FRED (CPIAUCSL).
        Falls back to static data when DB is unavailable.
        """
        engine = await self._ensure_market_db()

        if engine is not None:
            try:
                indicators = await self._db_get_economic_indicators(engine)
                logger.info("get_economic_indicators served from database")
                return indicators
            except Exception as exc:
                logger.warning(
                    f"DB query failed for economic indicators, using static fallback: {exc}"
                )

        logger.info("get_economic_indicators served from static_fallback")
        return self._static_get_economic_indicators()

    async def _db_get_economic_indicators(self, engine) -> list[EconomicIndicator]:
        """Query FRED + Census for economic indicators."""
        from sqlalchemy import text

        indicators: list[EconomicIndicator] = []

        async with engine.connect() as conn:
            # Unemployment
            unemp = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PHOE004UR'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            unemp_rows = unemp.fetchall()
            if unemp_rows:
                cur = float(unemp_rows[0][0])
                prev = float(unemp_rows[1][0]) if len(unemp_rows) > 1 else cur
                indicators.append(
                    EconomicIndicator(
                        indicator="Unemployment Rate",
                        value=cur,
                        yoy_change=round(cur - prev, 2),
                        unit="%",
                    )
                )

            # Employment (Non-Farm Payrolls)
            emp = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PHOE004NA'
                    ORDER BY date DESC LIMIT 13
                """)
            )
            emp_rows = emp.fetchall()
            if emp_rows and len(emp_rows) >= 2:
                cur_emp = float(emp_rows[0][0])
                prev_emp = float(emp_rows[-1][0])
                growth = (
                    round((cur_emp - prev_emp) / prev_emp * 100, 1) if prev_emp else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Job Growth Rate",
                        value=growth,
                        yoy_change=0,
                        unit="%",
                    )
                )

            # CPI from FRED
            cpi = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'CPIAUCSL'
                    ORDER BY date DESC LIMIT 13
                """)
            )
            cpi_rows = cpi.fetchall()
            if cpi_rows and len(cpi_rows) >= 2:
                cur_cpi = float(cpi_rows[0][0])
                prev_cpi = float(cpi_rows[-1][0])
                cpi_change = (
                    round((cur_cpi - prev_cpi) / prev_cpi * 100, 1) if prev_cpi else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="CPI (All Urban)",
                        value=round(cur_cpi, 1),
                        yoy_change=cpi_change,
                        unit="index",
                    )
                )

            # Population from Census
            pop = await conn.execute(
                text("""
                    SELECT value, year FROM census_timeseries
                    WHERE variable_code = 'B01003_001E'
                    ORDER BY year DESC LIMIT 2
                """)
            )
            pop_rows = pop.fetchall()
            if pop_rows:
                pop_val = int(float(pop_rows[0][0]))
                pop_change = 0.0
                if len(pop_rows) >= 2:
                    pop_change = round(
                        (float(pop_rows[0][0]) - float(pop_rows[1][0]))
                        / float(pop_rows[1][0])
                        * 100,
                        1,
                    )
                indicators.append(
                    EconomicIndicator(
                        indicator="Population",
                        value=pop_val,
                        yoy_change=pop_change,
                        unit="people",
                    )
                )

            # Median Household Income from Census
            income = await conn.execute(
                text("""
                    SELECT value, year FROM census_timeseries
                    WHERE variable_code = 'B19013_001E'
                    ORDER BY year DESC LIMIT 2
                """)
            )
            income_rows = income.fetchall()
            if income_rows:
                inc_val = float(income_rows[0][0])
                inc_change = 0.0
                if len(income_rows) >= 2:
                    inc_change = round(
                        (float(income_rows[0][0]) - float(income_rows[1][0]))
                        / float(income_rows[1][0])
                        * 100,
                        1,
                    )
                indicators.append(
                    EconomicIndicator(
                        indicator="Median Household Income",
                        value=inc_val,
                        yoy_change=inc_change,
                        unit="$",
                    )
                )

        # Fill missing with static defaults
        indicator_names = {i.indicator for i in indicators}
        for default in self._static_get_economic_indicators():
            if default.indicator not in indicator_names:
                indicators.append(default)

        return indicators

    def _static_get_economic_indicators(self) -> list[EconomicIndicator]:
        """Static fallback for economic indicators."""
        return [
            EconomicIndicator(
                indicator="Unemployment Rate", value=3.6, yoy_change=-0.4, unit="%"
            ),
            EconomicIndicator(
                indicator="Job Growth Rate", value=3.2, yoy_change=0.8, unit="%"
            ),
            EconomicIndicator(
                indicator="CPI (All Urban)", value=314.2, yoy_change=3.1, unit="index"
            ),
            EconomicIndicator(
                indicator="Population", value=5100000, yoy_change=2.3, unit="people"
            ),
            EconomicIndicator(
                indicator="Median Household Income",
                value=72500,
                yoy_change=4.5,
                unit="$",
            ),
        ]

    # ==================================================================
    # get_submarkets
    # ==================================================================

    async def get_submarkets(self) -> SubmarketsResponse:
        """Get submarket breakdown with performance metrics.

        Tries market_analysis DB first, falls back to static data.
        """
        engine = await self._ensure_market_db()

        if engine is not None:
            try:
                response = await self._db_get_submarkets(engine)
                logger.info("get_submarkets served from database")
                return response
            except Exception as exc:
                logger.warning(
                    f"DB query failed for submarkets, using static fallback: {exc}"
                )

        logger.info("get_submarkets served from static_fallback")
        return self._static_get_submarkets()

    async def _db_get_submarkets(self, engine) -> SubmarketsResponse:
        """Query market_analysis DB for submarket data from CoStar."""
        from sqlalchemy import text

        async with engine.connect() as conn:
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
                logger.info("No submarket rows in DB, falling back to static")
                return self._static_get_submarkets()

            submarkets = []
            for row in rows:
                name = _extract_submarket_name(row[0])
                vacancy = float(row[3]) if row[3] is not None else 0.05
                # CoStar vacancy is already a decimal (e.g. 0.094)
                occupancy = (
                    round(1 - vacancy, 4)
                    if vacancy < 1
                    else round(1 - vacancy / 100, 4)
                )
                rent_growth = float(row[2]) if row[2] is not None else 0.0

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

    def _static_get_submarkets(self) -> SubmarketsResponse:
        """Static fallback for submarket data."""
        submarkets = [
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
                name="East Valley",
                avg_rent=1500,
                rent_growth=0.060,
                occupancy=0.953,
                cap_rate=0.050,
                inventory=28500,
                absorption=340,
            ),
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
                name="North Phoenix",
                avg_rent=1550,
                rent_growth=0.062,
                occupancy=0.955,
                cap_rate=0.049,
                inventory=22000,
                absorption=275,
            ),
            SubmarketMetrics(
                name="Deer Valley",
                avg_rent=1600,
                rent_growth=0.064,
                occupancy=0.958,
                cap_rate=0.047,
                inventory=17500,
                absorption=230,
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
            SubmarketMetrics(
                name="Old Town Scottsdale",
                avg_rent=2150,
                rent_growth=0.072,
                occupancy=0.970,
                cap_rate=0.042,
                inventory=15200,
                absorption=198,
            ),
            SubmarketMetrics(
                name="North West Valley",
                avg_rent=1450,
                rent_growth=0.058,
                occupancy=0.950,
                cap_rate=0.052,
                inventory=25000,
                absorption=310,
            ),
            SubmarketMetrics(
                name="South West Valley",
                avg_rent=1400,
                rent_growth=0.055,
                occupancy=0.948,
                cap_rate=0.053,
                inventory=20000,
                absorption=250,
            ),
            SubmarketMetrics(
                name="South Phoenix",
                avg_rent=1350,
                rent_growth=0.052,
                occupancy=0.945,
                cap_rate=0.054,
                inventory=14000,
                absorption=170,
            ),
            SubmarketMetrics(
                name="North Scottsdale",
                avg_rent=2300,
                rent_growth=0.074,
                occupancy=0.972,
                cap_rate=0.040,
                inventory=12000,
                absorption=155,
            ),
            SubmarketMetrics(
                name="West Maricopa County",
                avg_rent=1400,
                rent_growth=0.054,
                occupancy=0.946,
                cap_rate=0.055,
                inventory=18000,
                absorption=220,
            ),
            SubmarketMetrics(
                name="Camelback",
                avg_rent=1900,
                rent_growth=0.071,
                occupancy=0.968,
                cap_rate=0.044,
                inventory=14500,
                absorption=190,
            ),
            SubmarketMetrics(
                name="Southeast Valley",
                avg_rent=1650,
                rent_growth=0.063,
                occupancy=0.957,
                cap_rate=0.049,
                inventory=13000,
                absorption=165,
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
            source="static_fallback",
        )

    # ==================================================================
    # get_market_trends
    # ==================================================================

    async def get_market_trends(self, period_months: int = 12) -> MarketTrendsResponse:
        """Get market trends over time.

        Tries market_analysis DB first, falls back to static data.
        """
        engine = await self._ensure_market_db()

        if engine is not None:
            try:
                response = await self._db_get_market_trends(engine, period_months)
                logger.info("get_market_trends served from database")
                return response
            except Exception as exc:
                logger.warning(
                    f"DB query failed for market trends, using static fallback: {exc}"
                )

        logger.info("get_market_trends served from static_fallback")
        return self._static_get_market_trends(period_months)

    async def _db_get_market_trends(
        self, engine, period_months: int
    ) -> MarketTrendsResponse:
        """Query market_analysis DB for trailing trend data from CoStar."""
        from sqlalchemy import text

        # Convert months to quarters (CoStar data is quarterly)
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
                logger.info("No trend rows in DB, falling back to static")
                return self._static_get_market_trends(period_months)

            # Reverse to chronological order
            rows = list(reversed(rows))

            trends = []
            monthly_data = []
            for row in rows:
                vacancy = float(row[3]) if row[3] is not None else 0.05
                rg = float(row[2]) if row[2] is not None else 0.0
                occ = (
                    round(1 - vacancy, 4)
                    if vacancy < 1
                    else round(1 - vacancy / 100, 4)
                )
                cr = float(row[4]) if row[4] is not None else 0.05

                trends.append(
                    MarketTrend(
                        month=row[1], rent_growth=rg, occupancy=occ, cap_rate=cr
                    )
                )
                monthly_data.append(
                    MonthlyMarketData(
                        month=row[1],
                        rent_growth=rg,
                        occupancy=occ,
                        cap_rate=cr,
                        employment=0,
                        population=0,
                    )
                )

            return MarketTrendsResponse(
                trends=trends,
                monthly_data=monthly_data,
                period=f"{period_months}M",
                last_updated=self._last_updated,
                source="database",
            )

    def _static_get_market_trends(self, period_months: int) -> MarketTrendsResponse:
        """Static fallback for trend data."""
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
            source="static_fallback",
        )

    # ==================================================================
    # get_comparables
    # ==================================================================

    async def get_comparables(
        self,
        property_id: str | None = None,
        submarket: str | None = None,
        radius_miles: float = 5.0,
        limit: int = 10,
    ) -> ComparablesResponse:
        """Get property comparables, enriched with DB submarket context when available.

        The base comparable data is portfolio-based (static). When the market
        database is available, each comparable is enriched with live submarket
        metrics (avg rent, vacancy, cap rate) from costar_latest.
        """
        # Start with static comparables
        comparables = self._static_get_comparables_list()

        if submarket:
            comparables = [
                c for c in comparables if c.submarket.lower() == submarket.lower()
            ]
        comparables = comparables[:limit]

        # Try to enrich with DB submarket context
        source = "static_fallback"
        engine = await self._ensure_market_db()
        if engine is not None:
            try:
                comparables = await self._enrich_comparables_with_db(
                    engine, comparables
                )
                source = "database"
                logger.info("get_comparables served from database (enriched)")
            except Exception as exc:
                logger.warning(
                    f"Could not enrich comparables from DB, returning static: {exc}"
                )
                logger.info("get_comparables served from static_fallback")
        else:
            logger.info("get_comparables served from static_fallback")

        return ComparablesResponse(
            comparables=comparables,
            total=len(comparables),
            radius_miles=radius_miles,
            last_updated=self._last_updated,
            source=source,
        )

    async def _enrich_comparables_with_db(
        self, engine, comparables: list[PropertyComparable]
    ) -> list[PropertyComparable]:
        """Enrich comparable properties with live submarket context from costar_latest.

        For each comparable's submarket, fetch latest avg rent, vacancy, and
        cap rate so the frontend can show market context alongside the comp.
        """
        from sqlalchemy import text

        # Collect unique submarket names
        submarket_names = {c.submarket for c in comparables}
        if not submarket_names:
            return comparables

        async with engine.connect() as conn:
            # Build a lookup of submarket metrics from costar_latest
            result = await conn.execute(
                text("""
                    SELECT
                        geography_name,
                        MAX(CASE WHEN concept = 'Market Asking Rent/Unit' THEN value END) as avg_rent,
                        MAX(CASE WHEN concept = 'Vacancy Rate' THEN value END) as vacancy,
                        MAX(CASE WHEN concept = 'Market Cap Rate' THEN value END) as cap_rate
                    FROM costar_latest
                    WHERE geography_type = 'Submarket'
                    GROUP BY geography_name
                """)
            )
            rows = result.fetchall()

            # Map extracted submarket names to their metrics
            submarket_lookup: dict[str, dict] = {}
            for row in rows:
                name = _extract_submarket_name(row[0])
                submarket_lookup[name.lower()] = {
                    "avg_rent": float(row[1]) if row[1] is not None else None,
                    "vacancy": float(row[2]) if row[2] is not None else None,
                    "cap_rate": float(row[3]) if row[3] is not None else None,
                }

        # Enrich comparables — update fields where DB data is available
        enriched = []
        for comp in comparables:
            market = submarket_lookup.get(comp.submarket.lower())
            if market:
                # Update comp fields with live market data where the comp
                # doesn't already have a sale-specific value
                enriched.append(
                    PropertyComparable(
                        id=comp.id,
                        name=comp.name,
                        address=comp.address,
                        submarket=comp.submarket,
                        units=comp.units,
                        year_built=comp.year_built,
                        avg_rent=market["avg_rent"]
                        if market["avg_rent"] is not None
                        else comp.avg_rent,
                        occupancy=(
                            round(1 - market["vacancy"], 4)
                            if market["vacancy"] is not None and market["vacancy"] < 1
                            else comp.occupancy
                        ),
                        sale_price=comp.sale_price,
                        sale_date=comp.sale_date,
                        cap_rate=comp.cap_rate
                        if comp.cap_rate is not None
                        else market.get("cap_rate"),
                    )
                )
            else:
                enriched.append(comp)

        return enriched

    def _static_get_comparables_list(self) -> list[PropertyComparable]:
        """Static list of property comparables (portfolio-based)."""
        return [
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

    # ==================================================================
    # USA (National) Market Overview
    # ==================================================================

    # National FRED series mapping
    _USA_FRED_SERIES = {
        "unemployment": "UNRATE",  # National unemployment rate (%)
        "payrolls": "PAYEMS",  # Total nonfarm payrolls (thousands)
        "cpi": "CPIAUCSL",  # CPI, all urban consumers (index)
        "gdp": "GDP",  # GDP (billions)
        "mortgage30": "MORTGAGE30US",  # 30-year fixed mortgage rate (%)
        "treasury10": "DGS10",  # 10-year Treasury yield (%)
        "fedfunds": "FEDFUNDS",  # Federal Funds rate (%)
        "housing_starts": "HOUST",  # Housing starts (thousands)
        "permits": "PERMIT",  # Building permits (thousands)
    }

    async def get_usa_market_overview(self) -> MarketOverviewResponse:
        """Get national (USA) market overview with economic indicators.

        Tries market_analysis DB first, falls back to static data.
        """
        engine = await self._ensure_market_db()

        if engine is not None:
            try:
                response = await self._db_get_usa_market_overview(engine)
                logger.info("get_usa_market_overview served from database")
                return response
            except Exception as exc:
                logger.warning(
                    f"DB query failed for USA market overview, using static fallback: {exc}"
                )

        logger.info("get_usa_market_overview served from static_fallback")
        return self._static_get_usa_market_overview()

    async def _db_get_usa_market_overview(self, engine) -> MarketOverviewResponse:
        """Query market_analysis DB for national economic indicators from FRED."""
        from sqlalchemy import text

        async with engine.connect() as conn:
            indicators: list[EconomicIndicator] = []

            # -- Unemployment Rate (UNRATE) --
            unemp_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'UNRATE'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            unemp_rows = unemp_result.fetchall()
            if unemp_rows:
                current_unemp = float(unemp_rows[0][0])
                prev_unemp = (
                    float(unemp_rows[1][0]) if len(unemp_rows) > 1 else current_unemp
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Unemployment Rate",
                        value=current_unemp,
                        yoy_change=round(current_unemp - prev_unemp, 2),
                        unit="%",
                    )
                )

            # -- Total Nonfarm Payrolls (PAYEMS) --
            emp_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PAYEMS'
                    ORDER BY date DESC LIMIT 13
                """)
            )
            emp_rows = emp_result.fetchall()
            job_growth = 0.0
            if emp_rows and len(emp_rows) >= 2:
                current_emp = float(emp_rows[0][0])
                prev_emp = float(emp_rows[-1][0])
                job_growth = (
                    round((current_emp - prev_emp) / prev_emp * 100, 1)
                    if prev_emp
                    else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Job Growth Rate",
                        value=job_growth,
                        yoy_change=0,
                        unit="%",
                    )
                )

            # -- CPI (CPIAUCSL) --
            cpi_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'CPIAUCSL'
                    ORDER BY date DESC LIMIT 13
                """)
            )
            cpi_rows = cpi_result.fetchall()
            if cpi_rows and len(cpi_rows) >= 2:
                cur_cpi = float(cpi_rows[0][0])
                prev_cpi = float(cpi_rows[-1][0])
                cpi_change = (
                    round((cur_cpi - prev_cpi) / prev_cpi * 100, 1) if prev_cpi else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="CPI (All Urban)",
                        value=round(cur_cpi, 1),
                        yoy_change=cpi_change,
                        unit="index",
                    )
                )

            # -- 30-Year Mortgage Rate (MORTGAGE30US) --
            mortgage_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'MORTGAGE30US'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            mortgage_rows = mortgage_result.fetchall()
            if mortgage_rows:
                cur_mort = float(mortgage_rows[0][0])
                prev_mort = (
                    float(mortgage_rows[1][0]) if len(mortgage_rows) > 1 else cur_mort
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="30-Year Mortgage Rate",
                        value=cur_mort,
                        yoy_change=round(cur_mort - prev_mort, 2),
                        unit="%",
                    )
                )

            # -- Federal Funds Rate (FEDFUNDS) --
            fedfunds_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'FEDFUNDS'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            fedfunds_rows = fedfunds_result.fetchall()
            if fedfunds_rows:
                cur_ff = float(fedfunds_rows[0][0])
                prev_ff = (
                    float(fedfunds_rows[1][0]) if len(fedfunds_rows) > 1 else cur_ff
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Federal Funds Rate",
                        value=cur_ff,
                        yoy_change=round(cur_ff - prev_ff, 2),
                        unit="%",
                    )
                )

            # -- Housing Starts (HOUST) --
            houst_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'HOUST'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            houst_rows = houst_result.fetchall()
            if houst_rows:
                cur_houst = float(houst_rows[0][0])
                prev_houst = (
                    float(houst_rows[1][0]) if len(houst_rows) > 1 else cur_houst
                )
                houst_change = (
                    round((cur_houst - prev_houst) / prev_houst * 100, 1)
                    if prev_houst
                    else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Housing Starts",
                        value=cur_houst,
                        yoy_change=houst_change,
                        unit="K",
                    )
                )

            # -- Building Permits (PERMIT) --
            permit_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'PERMIT'
                    ORDER BY date DESC LIMIT 2
                """)
            )
            permit_rows = permit_result.fetchall()
            if permit_rows:
                cur_permit = float(permit_rows[0][0])
                prev_permit = (
                    float(permit_rows[1][0]) if len(permit_rows) > 1 else cur_permit
                )
                permit_change = (
                    round((cur_permit - prev_permit) / prev_permit * 100, 1)
                    if prev_permit
                    else 0
                )
                indicators.append(
                    EconomicIndicator(
                        indicator="Building Permits",
                        value=cur_permit,
                        yoy_change=permit_change,
                        unit="K",
                    )
                )

            # Fill missing indicators with static defaults
            indicator_names = {i.indicator for i in indicators}
            for default in self._static_get_usa_market_overview().economic_indicators:
                if default.indicator not in indicator_names:
                    indicators.append(default)

            employment_val = (
                int(float(emp_rows[0][0]) * 1000) if emp_rows else 157000000
            )

            # -- GDP (GDP series — quarterly, billions) --
            gdp_val = 28000000000000  # default ~$28T
            gdp_growth = 0.025
            gdp_result = await conn.execute(
                text("""
                    SELECT value, date FROM fred_timeseries
                    WHERE series_id = 'GDP'
                    ORDER BY date DESC LIMIT 5
                """)
            )
            gdp_rows = gdp_result.fetchall()
            if gdp_rows:
                gdp_val = int(float(gdp_rows[0][0]) * 1000000000)  # billions -> dollars
                if len(gdp_rows) >= 5:
                    prev_gdp = float(gdp_rows[-1][0])
                    cur_gdp = float(gdp_rows[0][0])
                    gdp_growth = (
                        round((cur_gdp - prev_gdp) / prev_gdp, 4) if prev_gdp else 0.025
                    )

            msa_overview = MSAOverview(
                population=331000000,
                employment=employment_val,
                gdp=gdp_val,
                population_growth=0.006,
                employment_growth=job_growth / 100 if emp_rows else 0.017,
                gdp_growth=gdp_growth,
                last_updated=self._market_data_freshness
                or datetime.now().strftime("%Y-%m-%d"),
            )

            return MarketOverviewResponse(
                msa_overview=msa_overview,
                economic_indicators=indicators,
                last_updated=self._last_updated,
                source="database",
            )

    def _static_get_usa_market_overview(self) -> MarketOverviewResponse:
        """Static fallback for national market overview."""
        msa_overview = MSAOverview(
            population=331000000,
            employment=157000000,
            gdp=28000000000000,
            population_growth=0.006,
            employment_growth=0.017,
            gdp_growth=0.025,
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )

        economic_indicators = [
            EconomicIndicator(
                indicator="Unemployment Rate", value=3.9, yoy_change=-0.2, unit="%"
            ),
            EconomicIndicator(
                indicator="Job Growth Rate", value=1.7, yoy_change=0.3, unit="%"
            ),
            EconomicIndicator(
                indicator="CPI (All Urban)", value=314.2, yoy_change=3.1, unit="index"
            ),
            EconomicIndicator(
                indicator="30-Year Mortgage Rate",
                value=6.8,
                yoy_change=0.1,
                unit="%",
            ),
            EconomicIndicator(
                indicator="Federal Funds Rate",
                value=5.33,
                yoy_change=-0.25,
                unit="%",
            ),
            EconomicIndicator(
                indicator="Housing Starts",
                value=1420,
                yoy_change=-2.1,
                unit="K",
            ),
            EconomicIndicator(
                indicator="Building Permits",
                value=1480,
                yoy_change=1.5,
                unit="K",
            ),
        ]

        return MarketOverviewResponse(
            msa_overview=msa_overview,
            economic_indicators=economic_indicators,
            last_updated=self._last_updated,
            source="static_fallback",
        )

    # ==================================================================
    # USA (National) Market Trends
    # ==================================================================

    async def get_usa_market_trends(
        self, period_months: int = 12
    ) -> MarketTrendsResponse:
        """Get national market trends over time.

        Tries market_analysis DB for national FRED series, falls back to static data.
        """
        engine = await self._ensure_market_db()

        if engine is not None:
            try:
                response = await self._db_get_usa_market_trends(engine, period_months)
                logger.info("get_usa_market_trends served from database")
                return response
            except Exception as exc:
                logger.warning(
                    f"DB query failed for USA market trends, using static fallback: {exc}"
                )

        logger.info("get_usa_market_trends served from static_fallback")
        return self._static_get_usa_market_trends(period_months)

    async def _db_get_usa_market_trends(
        self, engine, period_months: int
    ) -> MarketTrendsResponse:
        """Query market_analysis DB for national trailing trend data from FRED."""
        from sqlalchemy import text

        async with engine.connect() as conn:
            # Query key national FRED series over the period
            result = await conn.execute(
                text("""
                    SELECT
                        u.date,
                        TO_CHAR(u.date, 'Mon YYYY') as label,
                        u.value as unemployment,
                        m.value as mortgage_rate,
                        f.value as fedfunds
                    FROM fred_timeseries u
                    LEFT JOIN fred_timeseries m
                        ON m.series_id = 'MORTGAGE30US' AND m.date = u.date
                    LEFT JOIN fred_timeseries f
                        ON f.series_id = 'FEDFUNDS' AND f.date = u.date
                    WHERE u.series_id = 'UNRATE'
                    ORDER BY u.date DESC
                    LIMIT :limit
                """),
                {"limit": period_months},
            )
            rows = result.fetchall()

            if not rows:
                logger.info("No USA trend rows in DB, falling back to static")
                return self._static_get_usa_market_trends(period_months)

            # Reverse to chronological order
            rows = list(reversed(rows))

            trends = []
            monthly_data = []
            for row in rows:
                unemp = float(row[2]) if row[2] is not None else 3.9
                mortgage = float(row[3]) if row[3] is not None else 6.8
                # Map national data into the MarketTrend shape:
                #   rent_growth -> unemployment rate (repurposed for national view)
                #   occupancy -> 1 - (unemployment/100) as "employment rate"
                #   cap_rate -> mortgage rate (as a key rate metric)
                employment_rate = round(1 - unemp / 100, 4)

                trends.append(
                    MarketTrend(
                        month=row[1],
                        rent_growth=round(unemp, 2),
                        occupancy=employment_rate,
                        cap_rate=round(mortgage, 2),
                    )
                )
                monthly_data.append(
                    MonthlyMarketData(
                        month=row[1],
                        rent_growth=round(unemp, 2),
                        occupancy=employment_rate,
                        cap_rate=round(mortgage, 2),
                        employment=0,
                        population=0,
                    )
                )

            return MarketTrendsResponse(
                trends=trends,
                monthly_data=monthly_data,
                period=f"{period_months}M",
                last_updated=self._last_updated,
                source="database",
            )

    def _static_get_usa_market_trends(self, period_months: int) -> MarketTrendsResponse:
        """Static fallback for national trend data."""
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

        base_unemployment = 4.1
        base_employment_rate = 0.959
        base_mortgage_rate = 7.1
        base_employment = 156000000
        base_population = 330000000

        trends = []
        monthly_data = []

        for i, month in enumerate(months[:period_months]):
            progress = i / 11.0
            unemployment = base_unemployment - (0.3 * progress)
            employment_rate = base_employment_rate + (0.003 * progress)
            mortgage_rate = base_mortgage_rate - (0.4 * progress)
            employment = int(base_employment + (1200000 * progress))
            population = int(base_population + (800000 * progress))

            trends.append(
                MarketTrend(
                    month=month,
                    rent_growth=round(unemployment, 2),
                    occupancy=round(employment_rate, 4),
                    cap_rate=round(mortgage_rate, 2),
                )
            )
            monthly_data.append(
                MonthlyMarketData(
                    month=month,
                    rent_growth=round(unemployment, 2),
                    occupancy=round(employment_rate, 4),
                    cap_rate=round(mortgage_rate, 2),
                    employment=employment,
                    population=population,
                )
            )

        return MarketTrendsResponse(
            trends=trends,
            monthly_data=monthly_data,
            period=f"{period_months}M",
            last_updated=self._last_updated,
            source="static_fallback",
        )

    # ==================================================================
    # get_comparables
    # ==================================================================

    def _static_get_comparables(
        self,
        property_id: str | None = None,
        submarket: str | None = None,
        radius_miles: float = 5.0,
        limit: int = 10,
    ) -> ComparablesResponse:
        """Static fallback for comparables (full response)."""
        comparables = self._static_get_comparables_list()

        if submarket:
            comparables = [
                c for c in comparables if c.submarket.lower() == submarket.lower()
            ]
        comparables = comparables[:limit]

        return ComparablesResponse(
            comparables=comparables,
            total=len(comparables),
            radius_miles=radius_miles,
            last_updated=self._last_updated,
            source="static_fallback",
        )


# Singleton instance
market_data_service = MarketDataService()
