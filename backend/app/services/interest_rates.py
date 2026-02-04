"""
Interest Rates Service

Provides current and historical interest rate data with 3-tier fallback:
1. Market data database (fred_latest / fred_timeseries)
2. Direct FRED API calls
3. Mock data
"""

from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings

# FRED series ID → display config mapping
_RATE_DISPLAY = {
    "FEDFUNDS": {"id": "fed-funds", "name": "Federal Funds Rate", "short_name": "Fed Funds", "category": "federal"},
    "DPRIME": {"id": "prime-rate", "name": "Prime Rate", "short_name": "Prime", "category": "federal"},
    "DGS2": {"id": "treasury-2y", "name": "2-Year Treasury Yield", "short_name": "2Y Treasury", "category": "treasury"},
    "DGS5": {"id": "treasury-5y", "name": "5-Year Treasury Yield", "short_name": "5Y Treasury", "category": "treasury"},
    "DGS7": {"id": "treasury-7y", "name": "7-Year Treasury Yield", "short_name": "7Y Treasury", "category": "treasury"},
    "DGS10": {"id": "treasury-10y", "name": "10-Year Treasury Yield", "short_name": "10Y Treasury", "category": "treasury"},
    "DGS30": {"id": "treasury-30y", "name": "30-Year Treasury Yield", "short_name": "30Y Treasury", "category": "treasury"},
    "SOFR": {"id": "sofr-1m", "name": "SOFR Rate", "short_name": "SOFR", "category": "sofr"},
    "MORTGAGE30US": {"id": "mortgage-30y", "name": "30-Year Fixed Mortgage Rate", "short_name": "30Y Mortgage", "category": "mortgage"},
}

# Yield curve maturities in order
_YIELD_CURVE_SERIES = [
    ("DGS1MO", "1M", 1), ("DGS3MO", "3M", 3), ("DGS6MO", "6M", 6),
    ("DGS1", "1Y", 12), ("DGS2", "2Y", 24), ("DGS5", "5Y", 60),
    ("DGS7", "7Y", 84), ("DGS10", "10Y", 120), ("DGS20", "20Y", 240),
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

    3-tier fallback: database → FRED API → mock data.
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

    # ── Database queries ──

    def _get_rates_from_db(self, series_ids: list[str]) -> dict[str, tuple[float, float, str]] | None:
        """Query fred_timeseries for latest 2 values per series.

        Returns dict of series_id → (current_value, previous_value, as_of_date)
        """
        if not self._db_available or not self._market_db_engine:
            return None

        try:
            from sqlalchemy import text

            results = {}
            with self._market_db_engine.connect() as conn:
                for sid in series_ids:
                    rows = conn.execute(
                        text("""
                            SELECT value, date::text FROM fred_timeseries
                            WHERE series_id = :sid
                            ORDER BY date DESC LIMIT 2
                        """),
                        {"sid": sid},
                    ).fetchall()

                    if rows:
                        current = float(rows[0][0])
                        previous = float(rows[1][0]) if len(rows) > 1 else current
                        results[sid] = (current, previous, rows[0][1])

            return results if results else None
        except Exception as e:
            logger.debug(f"DB query failed for interest rates: {e}")
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
                            AND date >= (CURRENT_DATE - INTERVAL ':months months')
                            GROUP BY TO_CHAR(date, 'YYYY-MM')
                            ORDER BY month
                        """.replace(":months", str(months))),
                        {"sid": sid},
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
                    [v for v in series_data.values() if "federal_funds" in v and "treasury_10y" in v],
                    key=lambda x: x["date"],
                )
                return result[-months:] if result else None
        except Exception as e:
            logger.debug(f"DB historical query failed: {e}")
            return None

    # ── Public methods ──

    async def get_key_rates(self) -> dict:
        """Get current key interest rates. DB → FRED API → mock."""
        cache_key = "key_rates"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Try DB first
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
                    rates.append({
                        **config,
                        "current_value": current,
                        "previous_value": previous,
                        "change": change,
                        "change_percent": change_pct,
                        "as_of_date": as_of,
                        "description": "From market database",
                    })

            if rates:
                data = {"key_rates": rates, "last_updated": datetime.now(UTC).isoformat(), "source": "database"}
                self._set_cache(cache_key, data)
                return data

        # Try FRED API directly
        if self._fred_api_key:
            rates = []
            for sid, config in _RATE_DISPLAY.items():
                obs = await self._fetch_from_fred(sid)
                if obs and len(obs) > 0:
                    current = float(obs[0].get("value", 0)) if obs[0].get("value", ".") != "." else 0
                    previous = float(obs[1].get("value", 0)) if len(obs) > 1 and obs[1].get("value", ".") != "." else current
                    if current > 0:
                        change = round(current - previous, 2)
                        change_pct = round((change / previous * 100) if previous else 0, 2)
                        rates.append({
                            **config,
                            "current_value": current,
                            "previous_value": previous,
                            "change": change,
                            "change_percent": change_pct,
                            "as_of_date": obs[0].get("date", ""),
                            "description": "Live from FRED API",
                        })

            if len(rates) >= 5:
                data = {"key_rates": rates, "last_updated": datetime.now(UTC).isoformat(), "source": "fred_api"}
                self._set_cache(cache_key, data)
                return data

        # Fall back to mock
        data = {"key_rates": self.get_mock_key_rates(), "last_updated": datetime.now(UTC).isoformat(), "source": "mock"}
        self._set_cache(cache_key, data)
        return data

    async def get_yield_curve(self) -> dict:
        """Get Treasury yield curve. DB → FRED API → mock."""
        cache_key = "yield_curve"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Try DB
        await self._get_db_engine()
        series_ids = [s[0] for s in _YIELD_CURVE_SERIES]
        db_rates = self._get_rates_from_db(series_ids)

        if db_rates and len(db_rates) >= 6:
            curve = []
            for sid, label, months in _YIELD_CURVE_SERIES:
                if sid in db_rates:
                    current, previous, _ = db_rates[sid]
                    curve.append({
                        "maturity": label,
                        "yield": current,
                        "previous_yield": previous,
                        "maturity_months": months,
                    })

            if curve:
                data = {
                    "yield_curve": curve,
                    "as_of_date": db_rates.get("DGS10", (0, 0, ""))[2] if "DGS10" in db_rates else "",
                    "last_updated": datetime.now(UTC).isoformat(),
                    "source": "database",
                }
                self._set_cache(cache_key, data)
                return data

        # Fall back to mock
        data = {
            "yield_curve": self.get_mock_yield_curve(),
            "as_of_date": "2025-12-05",
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "mock",
        }
        self._set_cache(cache_key, data)
        return data

    async def get_historical_rates(self, months: int = 12) -> dict:
        """Get historical rates. DB → mock."""
        cache_key = f"historical_rates_{months}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Try DB
        await self._get_db_engine()
        db_historical = self._get_historical_from_db(months)

        if db_historical:
            data = {
                "rates": db_historical,
                "start_date": db_historical[0]["date"],
                "end_date": db_historical[-1]["date"],
                "last_updated": datetime.now(UTC).isoformat(),
                "source": "database",
            }
            self._set_cache(cache_key, data)
            return data

        # Fall back to mock
        rates = self.get_mock_historical_rates(months)
        data = {
            "rates": rates,
            "start_date": rates[0]["date"] if rates else "",
            "end_date": rates[-1]["date"] if rates else "",
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "mock",
        }
        self._set_cache(cache_key, data)
        return data

    async def get_rate_spreads(self, months: int = 12) -> dict:
        """Get calculated rate spreads."""
        cache_key = f"rate_spreads_{months}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Use historical rates (which already do DB → mock fallback)
        historical_data = await self.get_historical_rates(months)
        rates = historical_data.get("rates", [])
        spreads = self.calculate_spreads(rates)

        data = {
            "spreads": spreads,
            "last_updated": datetime.now(UTC).isoformat(),
            "source": historical_data.get("source", "mock"),
        }
        self._set_cache(cache_key, data)
        return data

    # ── Mock data (unchanged, kept as fallback) ──

    def get_mock_key_rates(self) -> list[dict]:
        return [
            {"id": "fed-funds", "name": "Federal Funds Rate", "short_name": "Fed Funds", "current_value": 5.33, "previous_value": 5.33, "change": 0, "change_percent": 0, "as_of_date": "2025-12-05", "category": "federal", "description": "The interest rate at which banks lend reserve balances to other banks overnight."},
            {"id": "prime-rate", "name": "Prime Rate", "short_name": "Prime", "current_value": 8.50, "previous_value": 8.50, "change": 0, "change_percent": 0, "as_of_date": "2025-12-05", "category": "federal", "description": "The rate that commercial banks charge their most creditworthy customers."},
            {"id": "treasury-2y", "name": "2-Year Treasury Yield", "short_name": "2Y Treasury", "current_value": 4.18, "previous_value": 4.21, "change": -0.03, "change_percent": -0.71, "as_of_date": "2025-12-05", "category": "treasury", "description": "Yield on 2-year U.S. Treasury notes."},
            {"id": "treasury-5y", "name": "5-Year Treasury Yield", "short_name": "5Y Treasury", "current_value": 4.05, "previous_value": 4.09, "change": -0.04, "change_percent": -0.98, "as_of_date": "2025-12-05", "category": "treasury", "description": "Yield on 5-year U.S. Treasury notes."},
            {"id": "treasury-7y", "name": "7-Year Treasury Yield", "short_name": "7Y Treasury", "current_value": 4.12, "previous_value": 4.15, "change": -0.03, "change_percent": -0.72, "as_of_date": "2025-12-05", "category": "treasury", "description": "Yield on 7-year U.S. Treasury notes."},
            {"id": "treasury-10y", "name": "10-Year Treasury Yield", "short_name": "10Y Treasury", "current_value": 4.22, "previous_value": 4.26, "change": -0.04, "change_percent": -0.94, "as_of_date": "2025-12-05", "category": "treasury", "description": "Yield on 10-year U.S. Treasury notes. Key benchmark for mortgage rates."},
            {"id": "sofr-1m", "name": "1-Month SOFR", "short_name": "1M SOFR", "current_value": 5.34, "previous_value": 5.34, "change": 0, "change_percent": 0, "as_of_date": "2025-12-05", "category": "sofr", "description": "Secured Overnight Financing Rate, 1-month average."},
            {"id": "sofr-term-1m", "name": "1-Month Term SOFR", "short_name": "1M Term SOFR", "current_value": 5.32, "previous_value": 5.33, "change": -0.01, "change_percent": -0.19, "as_of_date": "2025-12-05", "category": "sofr", "description": "CME Term SOFR, 1-month rate."},
            {"id": "mortgage-30y", "name": "30-Year Fixed Mortgage Rate", "short_name": "30Y Mortgage", "current_value": 6.84, "previous_value": 6.91, "change": -0.07, "change_percent": -1.01, "as_of_date": "2025-12-05", "category": "mortgage", "description": "Average rate for 30-year fixed-rate mortgages."},
        ]

    def get_mock_yield_curve(self) -> list[dict]:
        return [
            {"maturity": "1M", "yield": 5.47, "previous_yield": 5.48, "maturity_months": 1},
            {"maturity": "3M", "yield": 5.41, "previous_yield": 5.42, "maturity_months": 3},
            {"maturity": "6M", "yield": 5.18, "previous_yield": 5.20, "maturity_months": 6},
            {"maturity": "1Y", "yield": 4.65, "previous_yield": 4.68, "maturity_months": 12},
            {"maturity": "2Y", "yield": 4.18, "previous_yield": 4.21, "maturity_months": 24},
            {"maturity": "3Y", "yield": 4.08, "previous_yield": 4.11, "maturity_months": 36},
            {"maturity": "5Y", "yield": 4.05, "previous_yield": 4.09, "maturity_months": 60},
            {"maturity": "7Y", "yield": 4.12, "previous_yield": 4.15, "maturity_months": 84},
            {"maturity": "10Y", "yield": 4.22, "previous_yield": 4.26, "maturity_months": 120},
            {"maturity": "20Y", "yield": 4.52, "previous_yield": 4.55, "maturity_months": 240},
            {"maturity": "30Y", "yield": 4.42, "previous_yield": 4.46, "maturity_months": 360},
        ]

    def get_mock_historical_rates(self, months: int = 12) -> list[dict]:
        all_data = [
            {"date": "2025-01", "federal_funds": 5.33, "treasury_2y": 4.21, "treasury_5y": 3.84, "treasury_10y": 3.95, "treasury_30y": 4.14, "sofr": 5.31, "mortgage_30y": 6.64},
            {"date": "2025-02", "federal_funds": 5.33, "treasury_2y": 4.64, "treasury_5y": 4.26, "treasury_10y": 4.25, "treasury_30y": 4.38, "sofr": 5.31, "mortgage_30y": 6.94},
            {"date": "2025-03", "federal_funds": 5.33, "treasury_2y": 4.59, "treasury_5y": 4.21, "treasury_10y": 4.20, "treasury_30y": 4.34, "sofr": 5.31, "mortgage_30y": 6.82},
            {"date": "2025-04", "federal_funds": 5.33, "treasury_2y": 4.97, "treasury_5y": 4.63, "treasury_10y": 4.59, "treasury_30y": 4.73, "sofr": 5.31, "mortgage_30y": 7.17},
            {"date": "2025-05", "federal_funds": 5.33, "treasury_2y": 4.87, "treasury_5y": 4.48, "treasury_10y": 4.50, "treasury_30y": 4.65, "sofr": 5.31, "mortgage_30y": 7.06},
            {"date": "2025-06", "federal_funds": 5.33, "treasury_2y": 4.71, "treasury_5y": 4.31, "treasury_10y": 4.36, "treasury_30y": 4.51, "sofr": 5.31, "mortgage_30y": 6.92},
            {"date": "2025-07", "federal_funds": 5.33, "treasury_2y": 4.38, "treasury_5y": 4.07, "treasury_10y": 4.17, "treasury_30y": 4.40, "sofr": 5.31, "mortgage_30y": 6.77},
            {"date": "2025-08", "federal_funds": 5.33, "treasury_2y": 3.92, "treasury_5y": 3.70, "treasury_10y": 3.90, "treasury_30y": 4.19, "sofr": 5.31, "mortgage_30y": 6.50},
            {"date": "2025-09", "federal_funds": 5.00, "treasury_2y": 3.55, "treasury_5y": 3.42, "treasury_10y": 3.73, "treasury_30y": 4.08, "sofr": 4.96, "mortgage_30y": 6.18},
            {"date": "2025-10", "federal_funds": 4.83, "treasury_2y": 4.17, "treasury_5y": 4.04, "treasury_10y": 4.28, "treasury_30y": 4.52, "sofr": 4.81, "mortgage_30y": 6.72},
            {"date": "2025-11", "federal_funds": 4.58, "treasury_2y": 4.24, "treasury_5y": 4.12, "treasury_10y": 4.35, "treasury_30y": 4.54, "sofr": 4.56, "mortgage_30y": 6.88},
            {"date": "2025-12", "federal_funds": 4.58, "treasury_2y": 4.18, "treasury_5y": 4.05, "treasury_10y": 4.22, "treasury_30y": 4.42, "sofr": 4.56, "mortgage_30y": 6.84},
        ]
        return all_data[-months:] if months < len(all_data) else all_data

    def get_mock_data_sources(self) -> list[dict]:
        return [
            {"id": "treasury-gov", "name": "U.S. Treasury Department", "url": "https://home.treasury.gov/", "description": "Official source for Treasury yield curve data.", "data_types": ["Treasury Yields", "Yield Curve", "Auction Results"], "update_frequency": "Daily"},
            {"id": "fred", "name": "Federal Reserve Economic Data (FRED)", "url": "https://fred.stlouisfed.org/", "description": "Comprehensive economic database by Federal Reserve Bank of St. Louis.", "data_types": ["Federal Funds Rate", "Treasury Yields", "SOFR", "Economic Indicators"], "update_frequency": "Daily"},
            {"id": "cme-sofr", "name": "CME Group - SOFR", "url": "https://www.cmegroup.com/markets/interest-rates/stirs/sofr.html", "description": "Official source for Term SOFR rates.", "data_types": ["Term SOFR", "SOFR Futures"], "update_frequency": "Real-time"},
            {"id": "ny-fed", "name": "Federal Reserve Bank of New York", "url": "https://www.newyorkfed.org/markets/reference-rates/sofr", "description": "Official administrator of SOFR.", "data_types": ["SOFR", "EFFR", "OBFR"], "update_frequency": "Daily"},
        ]

    def get_lending_context(self) -> dict:
        key_rates = {r["id"]: r["current_value"] for r in self.get_mock_key_rates()}
        treasury_10y = key_rates.get("treasury-10y", 4.22)
        sofr = key_rates.get("sofr-1m", 5.34)
        prime = key_rates.get("prime-rate", 8.50)

        return {
            "typical_spreads": {
                "multifamily_perm": {"name": "Multifamily Permanent", "spread": 1.50, "benchmark": "10Y Treasury"},
                "multifamily_bridge": {"name": "Multifamily Bridge", "spread": 3.00, "benchmark": "SOFR"},
                "commercial_perm": {"name": "Commercial Permanent", "spread": 1.75, "benchmark": "10Y Treasury"},
                "construction": {"name": "Construction", "spread": 0.50, "benchmark": "Prime Rate"},
            },
            "current_indicative_rates": {
                "multifamily_perm": round(treasury_10y + 1.50, 2),
                "multifamily_bridge": round(sofr + 3.00, 2),
                "commercial_perm": round(treasury_10y + 1.75, 2),
                "construction": round(prime + 0.50, 2),
            },
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

            treasury_spread_2s10s.append({"date": rate["date"], "spread": round(t10 - t2, 2)})
            mortgage_spread.append({"date": rate["date"], "spread": round(m30 - t10, 2)})
            fed_funds_vs_treasury.append({
                "date": rate["date"], "fed_funds": ff, "treasury_10y": t10, "spread": round(ff - t10, 2),
            })

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
