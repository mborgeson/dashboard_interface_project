"""
Interest Rates Service

Provides current and historical interest rate data with 2-tier fallback:
1. Market data database (fred_latest / fred_timeseries)
2. Direct FRED API calls

Returns an error/empty response when neither source is available.
"""

from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings

# FRED series ID → display config mapping
_RATE_DISPLAY = {
    "FEDFUNDS": {
        "id": "fed-funds",
        "name": "Federal Funds Rate",
        "short_name": "Fed Funds",
        "category": "federal",
    },
    "DPRIME": {
        "id": "prime-rate",
        "name": "Prime Rate",
        "short_name": "Prime",
        "category": "federal",
    },
    "DGS2": {
        "id": "treasury-2y",
        "name": "2-Year Treasury Yield",
        "short_name": "2Y Treasury",
        "category": "treasury",
    },
    "DGS5": {
        "id": "treasury-5y",
        "name": "5-Year Treasury Yield",
        "short_name": "5Y Treasury",
        "category": "treasury",
    },
    "DGS7": {
        "id": "treasury-7y",
        "name": "7-Year Treasury Yield",
        "short_name": "7Y Treasury",
        "category": "treasury",
    },
    "DGS10": {
        "id": "treasury-10y",
        "name": "10-Year Treasury Yield",
        "short_name": "10Y Treasury",
        "category": "treasury",
    },
    "DGS30": {
        "id": "treasury-30y",
        "name": "30-Year Treasury Yield",
        "short_name": "30Y Treasury",
        "category": "treasury",
    },
    "SOFR": {
        "id": "sofr-1m",
        "name": "SOFR Rate",
        "short_name": "SOFR",
        "category": "sofr",
    },
    "MORTGAGE30US": {
        "id": "mortgage-30y",
        "name": "30-Year Fixed Mortgage Rate",
        "short_name": "30Y Mortgage",
        "category": "mortgage",
    },
}

# Yield curve maturities in order
_YIELD_CURVE_SERIES = [
    ("DGS1MO", "1M", 1),
    ("DGS3MO", "3M", 3),
    ("DGS6MO", "6M", 6),
    ("DGS1", "1Y", 12),
    ("DGS2", "2Y", 24),
    ("DGS5", "5Y", 60),
    ("DGS7", "7Y", 84),
    ("DGS10", "10Y", 120),
    ("DGS20", "20Y", 240),
    ("DGS30", "30Y", 360),
]

# Historical rate series for monthly aggregation
_HISTORICAL_SERIES = {
    "federal_funds": "FEDFUNDS",
    "treasury_2y": "DGS2",
    "treasury_5y": "DGS5",
    "treasury_10y": "DGS10",
    "treasury_30y": "DGS30",
    "sofr": "SOFR",
    "mortgage_30y": "MORTGAGE30US",
}


class InterestRatesService:
    """
    Service for fetching interest rate data.

    2-tier fallback: database → FRED API.
    Returns empty/error response when neither source is available.
    """

    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._fred_api_key: str | None = getattr(settings, "FRED_API_KEY", None)
        self._market_db_engine = None
        self._db_available = False

    async def _get_db_engine(self):
        """Lazily create sync engine for market data DB."""
        if self._market_db_engine is not None:
            return self._market_db_engine

        db_url = settings.MARKET_ANALYSIS_DB_URL
        if not db_url:
            self._db_available = False
            return None

        try:
            from sqlalchemy import create_engine, text

            self._market_db_engine = create_engine(db_url, pool_size=2, max_overflow=1)
            # Test connection
            with self._market_db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._db_available = True
            return self._market_db_engine
        except Exception as e:
            logger.debug(f"Market data DB not available for interest rates: {e}")
            self._db_available = False
            return None

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (datetime.now(UTC) - timestamp).total_seconds() < self.CACHE_TTL

    def _get_cached(self, key: str) -> Any | None:
        if self._is_cache_valid(key):
            return self._cache[key][0]
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = (data, datetime.now(UTC))

    # ── FRED API direct fetch ──

    async def _fetch_from_fred(self, series_id: str) -> list[dict] | None:
        """Fetch the latest 2 observations for a single FRED series."""
        if not self._fred_api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": self._fred_api_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 2,
                    },
                )
                response.raise_for_status()
                return response.json().get("observations", [])
        except Exception as e:
            logger.debug(f"FRED API error for {series_id}: {e}")
            return None

    async def _fetch_historical_from_fred(
        self, series_id: str, start_date: str, end_date: str
    ) -> list[dict] | None:
        """Fetch historical observations for a FRED series over a date range.

        Args:
            series_id: FRED series identifier (e.g. 'DGS10').
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of {date, value} dicts sorted ascending, or None on failure.
        """
        if not self._fred_api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": self._fred_api_key,
                        "file_type": "json",
                        "observation_start": start_date,
                        "observation_end": end_date,
                        "sort_order": "asc",
                        "frequency": "m",  # monthly aggregation
                        "aggregation_method": "avg",
                    },
                )
                response.raise_for_status()
                observations = response.json().get("observations", [])
                # Filter out missing values (FRED uses "." for unavailable data)
                return [
                    {"date": obs["date"], "value": float(obs["value"])}
                    for obs in observations
                    if obs.get("value", ".") != "."
                ]
        except Exception as e:
            logger.debug(f"FRED API historical error for {series_id}: {e}")
            return None

    # ── Database queries ──

    def _get_rates_from_db(
        self, series_ids: list[str]
    ) -> dict[str, tuple[float, float, str]] | None:
        """Query fred_timeseries for latest 2 values per series using a single query.

        Returns dict of series_id -> (current_value, previous_value, as_of_date)
        or None if DB is unavailable or returns no data.
        """
        if not self._db_available or not self._market_db_engine:
            return None

        try:
            from sqlalchemy import text

            results: dict[str, tuple[float, float, str]] = {}
            with self._market_db_engine.connect() as conn:
                # Use a single query with a window function to fetch the latest
                # 2 rows per series, avoiding N+1 individual queries.
                rows = conn.execute(
                    text("""
                        WITH ranked AS (
                            SELECT
                                series_id,
                                value,
                                date::text AS date_str,
                                ROW_NUMBER() OVER (
                                    PARTITION BY series_id ORDER BY date DESC
                                ) AS rn
                            FROM fred_timeseries
                            WHERE series_id = ANY(:sids)
                        )
                        SELECT series_id, value, date_str, rn
                        FROM ranked
                        WHERE rn <= 2
                        ORDER BY series_id, rn
                    """),
                    {"sids": series_ids},
                ).fetchall()

                # Group by series_id
                series_rows: dict[str, list[tuple[float, str]]] = {}
                for row in rows:
                    sid = row[0]
                    val = float(row[1])
                    date_str = row[2]
                    if sid not in series_rows:
                        series_rows[sid] = []
                    series_rows[sid].append((val, date_str))

                for sid, vals in series_rows.items():
                    current = vals[0][0]
                    previous = vals[1][0] if len(vals) > 1 else current
                    as_of = vals[0][1]
                    results[sid] = (current, previous, as_of)

            return results if results else None
        except Exception as e:
            logger.warning(f"DB query failed for interest rates: {e}")
            return None

    def _get_historical_from_db(self, months: int = 12) -> list[dict] | None:
        """Query fred_timeseries for monthly historical rates."""
        if not self._db_available or not self._market_db_engine:
            return None

        try:
            from sqlalchemy import text

            with self._market_db_engine.connect() as conn:
                # Get monthly averages for each series
                series_data: dict[str, dict[str, float]] = {}

                for key, sid in _HISTORICAL_SERIES.items():
                    rows = conn.execute(
                        text("""
                            SELECT TO_CHAR(date, 'YYYY-MM') as month, AVG(value) as avg_val
                            FROM fred_timeseries
                            WHERE series_id = :sid
                            AND date >= (CURRENT_DATE - make_interval(months => :months))
                            GROUP BY TO_CHAR(date, 'YYYY-MM')
                            ORDER BY month
                        """),
                        {"sid": sid, "months": months},
                    ).fetchall()

                    for row in rows:
                        month_key = row[0]
                        if month_key not in series_data:
                            series_data[month_key] = {"date": month_key}
                        series_data[month_key][key] = round(float(row[1]), 2)

                if not series_data:
                    return None

                # Filter to months that have at least fed_funds and treasury_10y
                result = sorted(
                    [
                        v
                        for v in series_data.values()
                        if "federal_funds" in v and "treasury_10y" in v
                    ],
                    key=lambda x: x["date"],
                )
                return result[-months:] if result else None
        except Exception as e:
            logger.warning(f"DB historical query failed: {e}")
            return None

    # ── Public methods ──

    async def get_key_rates(self) -> dict:
        """Get current key interest rates. DB -> FRED API -> error."""
        cache_key = "key_rates"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Tier 1: Try DB first
        await self._get_db_engine()
        series_ids = list(_RATE_DISPLAY.keys())
        db_rates = self._get_rates_from_db(series_ids)

        if db_rates and len(db_rates) >= 5:
            rates = []
            for sid, config in _RATE_DISPLAY.items():
                if sid in db_rates:
                    current, previous, as_of = db_rates[sid]
                    change = round(current - previous, 2)
                    change_pct = round((change / previous * 100) if previous else 0, 2)
                    rates.append(
                        {
                            **config,
                            "current_value": current,
                            "previous_value": previous,
                            "change": change,
                            "change_percent": change_pct,
                            "as_of_date": as_of,
                            "description": "From market database",
                        }
                    )

            if rates:
                logger.info(
                    "Key rates sourced from database",
                    count=len(rates),
                )
                data = {
                    "key_rates": rates,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "source": "database",
                    "data_source": "database",
                }
                self._set_cache(cache_key, data)
                return data

        # Tier 2: Try FRED API directly
        if self._fred_api_key:
            rates = []
            for sid, config in _RATE_DISPLAY.items():
                obs = await self._fetch_from_fred(sid)
                if obs and len(obs) > 0:
                    current = (
                        float(obs[0].get("value", 0))
                        if obs[0].get("value", ".") != "."
                        else 0
                    )
                    previous = (
                        float(obs[1].get("value", 0))
                        if len(obs) > 1 and obs[1].get("value", ".") != "."
                        else current
                    )
                    if current > 0:
                        change = round(current - previous, 2)
                        change_pct = round(
                            (change / previous * 100) if previous else 0, 2
                        )
                        rates.append(
                            {
                                **config,
                                "current_value": current,
                                "previous_value": previous,
                                "change": change,
                                "change_percent": change_pct,
                                "as_of_date": obs[0].get("date", ""),
                                "description": "Live from FRED API",
                            }
                        )

            if len(rates) >= 5:
                logger.info(
                    "Key rates sourced from FRED API",
                    count=len(rates),
                )
                data = {
                    "key_rates": rates,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "source": "fred_api",
                    "data_source": "fred_api",
                }
                self._set_cache(cache_key, data)
                return data

        # Tier 3: No data available
        logger.warning("Key rates unavailable — both database and FRED API failed")
        data = {
            "key_rates": [],
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "unavailable",
            "data_source": "unavailable",
            "error": "Unable to fetch rate data from database or FRED API",
        }
        return data

    async def get_yield_curve(self) -> dict:
        """Get Treasury yield curve. DB -> FRED API -> error."""
        cache_key = "yield_curve"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Tier 1: Try DB
        await self._get_db_engine()
        series_ids = [s[0] for s in _YIELD_CURVE_SERIES]
        db_rates = self._get_rates_from_db(series_ids)

        if db_rates and len(db_rates) >= 6:
            curve = []
            for sid, label, months in _YIELD_CURVE_SERIES:
                if sid in db_rates:
                    current, previous, _ = db_rates[sid]
                    curve.append(
                        {
                            "maturity": label,
                            "yield": current,
                            "previous_yield": previous,
                            "maturity_months": months,
                        }
                    )

            if curve:
                as_of = db_rates["DGS10"][2] if "DGS10" in db_rates else ""
                logger.info(
                    "Yield curve sourced from database",
                    points=len(curve),
                )
                data = {
                    "yield_curve": curve,
                    "as_of_date": as_of,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "source": "database",
                    "data_source": "database",
                }
                self._set_cache(cache_key, data)
                return data

        # Tier 2: Try FRED API for each yield curve maturity
        if self._fred_api_key:
            curve = []
            for sid, label, maturity_months in _YIELD_CURVE_SERIES:
                obs = await self._fetch_from_fred(sid)
                if obs and len(obs) > 0:
                    current_val = obs[0].get("value", ".")
                    if current_val != ".":
                        current = float(current_val)
                        previous = (
                            float(obs[1]["value"])
                            if len(obs) > 1 and obs[1].get("value", ".") != "."
                            else current
                        )
                        curve.append(
                            {
                                "maturity": label,
                                "yield": current,
                                "previous_yield": previous,
                                "maturity_months": maturity_months,
                            }
                        )

            if len(curve) >= 6:
                as_of = ""
                # Extract as_of_date from the 10Y observation if available
                for sid, _label, _m in _YIELD_CURVE_SERIES:
                    if sid == "DGS10":
                        ten_yr_obs = await self._fetch_from_fred(sid)
                        if ten_yr_obs:
                            as_of = ten_yr_obs[0].get("date", "")
                        break

                logger.info(
                    "Yield curve sourced from FRED API",
                    points=len(curve),
                )
                data = {
                    "yield_curve": curve,
                    "as_of_date": as_of,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "source": "fred_api",
                    "data_source": "fred_api",
                }
                self._set_cache(cache_key, data)
                return data

        # Tier 3: No data available
        logger.warning("Yield curve unavailable — both database and FRED API failed")
        data = {
            "yield_curve": [],
            "as_of_date": "",
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "unavailable",
            "data_source": "unavailable",
            "error": "Unable to fetch yield curve data from database or FRED API",
        }
        return data

    async def get_historical_rates(self, months: int = 12) -> dict:
        """Get historical rates. DB -> FRED API -> error."""
        cache_key = f"historical_rates_{months}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Tier 1: Try DB
        await self._get_db_engine()
        db_historical = self._get_historical_from_db(months)

        if db_historical:
            logger.info(
                "Historical rates sourced from database",
                months=months,
                rows=len(db_historical),
            )
            data = {
                "rates": db_historical,
                "start_date": db_historical[0]["date"],
                "end_date": db_historical[-1]["date"],
                "last_updated": datetime.now(UTC).isoformat(),
                "source": "database",
                "data_source": "database",
            }
            self._set_cache(cache_key, data)
            return data

        # Tier 2: Try FRED API for historical data
        if self._fred_api_key:
            fred_historical = await self._fetch_historical_rates_from_fred(months)
            if fred_historical:
                logger.info(
                    "Historical rates sourced from FRED API",
                    months=months,
                    rows=len(fred_historical),
                )
                data = {
                    "rates": fred_historical,
                    "start_date": fred_historical[0]["date"],
                    "end_date": fred_historical[-1]["date"],
                    "last_updated": datetime.now(UTC).isoformat(),
                    "source": "fred_api",
                    "data_source": "fred_api",
                }
                self._set_cache(cache_key, data)
                return data

        # Tier 3: No data available
        logger.warning(
            "Historical rates unavailable — both database and FRED API failed"
        )
        data = {
            "rates": [],
            "start_date": "",
            "end_date": "",
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "unavailable",
            "data_source": "unavailable",
            "error": "Unable to fetch historical rate data from database or FRED API",
        }
        return data

    async def _fetch_historical_rates_from_fred(
        self, months: int = 12
    ) -> list[dict] | None:
        """Fetch monthly historical rates from FRED API for all tracked series.

        Aggregates each series into monthly averages and merges them into a list
        of dicts: [{date: "YYYY-MM", federal_funds: x, treasury_2y: x, ...}, ...]

        Returns None if insufficient data is available.
        """
        now = datetime.now(UTC)
        end_date = now.strftime("%Y-%m-%d")
        # Calculate start date going back the requested number of months
        start_year = now.year
        start_month = now.month - months
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start_date = f"{start_year}-{start_month:02d}-01"

        # Fetch all series in parallel-ish (sequential but with shared client)
        series_data: dict[str, dict[str, float]] = {}

        for key, sid in _HISTORICAL_SERIES.items():
            observations = await self._fetch_historical_from_fred(
                sid, start_date, end_date
            )
            if not observations:
                continue

            for obs in observations:
                # Convert YYYY-MM-DD to YYYY-MM for monthly grouping
                month_key = obs["date"][:7]
                if month_key not in series_data:
                    series_data[month_key] = {"date": month_key}
                # Since FRED already returns monthly avg, use directly
                series_data[month_key][key] = round(obs["value"], 2)

        if not series_data:
            return None

        # Filter to months that have at least federal_funds and treasury_10y
        result = sorted(
            [
                v
                for v in series_data.values()
                if "federal_funds" in v and "treasury_10y" in v
            ],
            key=lambda x: x["date"],
        )
        return result[-months:] if result else None

    async def get_rate_spreads(self, months: int = 12) -> dict:
        """Get calculated rate spreads."""
        cache_key = f"rate_spreads_{months}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Use historical rates (which already do DB -> FRED API fallback)
        historical_data = await self.get_historical_rates(months)
        rates = historical_data.get("rates", [])
        spreads = self.calculate_spreads(rates)

        data = {
            "spreads": spreads,
            "last_updated": datetime.now(UTC).isoformat(),
            "source": historical_data.get("source", "unavailable"),
            "data_source": historical_data.get("data_source", "unavailable"),
        }
        self._set_cache(cache_key, data)
        return data

    async def get_lending_context(self) -> dict:
        """Get lending context with indicative rates from live data when available.

        Uses the same 2-tier fallback as get_key_rates() to source benchmark values.
        """
        # Try to get live key rates (DB -> FRED API)
        key_rates_response = await self.get_key_rates()
        key_rates_list = key_rates_response.get("key_rates", [])
        source = key_rates_response.get("data_source", "unavailable")

        # Build lookup by id
        key_rates = {r["id"]: r["current_value"] for r in key_rates_list}
        treasury_10y = key_rates.get("treasury-10y", 4.22)
        sofr = key_rates.get("sofr-1m", 5.34)
        prime = key_rates.get("prime-rate", 8.50)

        return {
            "typical_spreads": {
                "multifamily_perm": {
                    "name": "Multifamily Permanent",
                    "spread": 1.50,
                    "benchmark": "10Y Treasury",
                },
                "multifamily_bridge": {
                    "name": "Multifamily Bridge",
                    "spread": 3.00,
                    "benchmark": "SOFR",
                },
                "commercial_perm": {
                    "name": "Commercial Permanent",
                    "spread": 1.75,
                    "benchmark": "10Y Treasury",
                },
                "construction": {
                    "name": "Construction",
                    "spread": 0.50,
                    "benchmark": "Prime Rate",
                },
            },
            "current_indicative_rates": {
                "multifamily_perm": round(treasury_10y + 1.50, 2),
                "multifamily_bridge": round(sofr + 3.00, 2),
                "commercial_perm": round(treasury_10y + 1.75, 2),
                "construction": round(prime + 0.50, 2),
            },
            "data_source": source,
        }

    def calculate_spreads(self, historical_rates: list[dict]) -> dict:
        treasury_spread_2s10s = []
        mortgage_spread = []
        fed_funds_vs_treasury = []

        for rate in historical_rates:
            t10 = rate.get("treasury_10y", 0)
            t2 = rate.get("treasury_2y", 0)
            ff = rate.get("federal_funds", 0)
            m30 = rate.get("mortgage_30y", 0)

            treasury_spread_2s10s.append(
                {"date": rate["date"], "spread": round(t10 - t2, 2)}
            )
            mortgage_spread.append(
                {"date": rate["date"], "spread": round(m30 - t10, 2)}
            )
            fed_funds_vs_treasury.append(
                {
                    "date": rate["date"],
                    "fed_funds": ff,
                    "treasury_10y": t10,
                    "spread": round(ff - t10, 2),
                }
            )

        return {
            "treasury_spread_2s10s": treasury_spread_2s10s,
            "mortgage_spread": mortgage_spread,
            "fed_funds_vs_treasury": fed_funds_vs_treasury,
        }


# Singleton instance
_interest_rates_service: InterestRatesService | None = None


def get_interest_rates_service() -> InterestRatesService:
    global _interest_rates_service
    if _interest_rates_service is None:
        _interest_rates_service = InterestRatesService()
    return _interest_rates_service
