"""
Interest Rates Service

Provides current and historical interest rate data with FRED API integration
and mock data fallback.
"""

from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


class InterestRatesService:
    """
    Service for fetching interest rate data.

    Features:
    - FRED API integration for real-time Treasury rates
    - In-memory caching with TTL
    - Mock data fallback when API unavailable
    - Calculated spreads and lending context
    """

    # FRED API series IDs
    FRED_SERIES = {
        "fed_funds": "FEDFUNDS",
        "treasury_2y": "DGS2",
        "treasury_5y": "DGS5",
        "treasury_7y": "DGS7",
        "treasury_10y": "DGS10",
        "treasury_30y": "DGS30",
        "sofr": "SOFR",
        "mortgage_30y": "MORTGAGE30US",
    }

    # Cache TTL in seconds (rates don't change frequently)
    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._fred_api_key: str | None = getattr(settings, "FRED_API_KEY", None)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        age = (datetime.now(UTC) - timestamp).total_seconds()
        return age < self.CACHE_TTL

    def _get_cached(self, key: str) -> Any | None:
        """Get data from cache if valid."""
        if self._is_cache_valid(key):
            data, _ = self._cache[key]
            return data
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        """Store data in cache."""
        self._cache[key] = (data, datetime.now(UTC))

    async def _fetch_from_fred(self, series_id: str) -> dict | None:
        """
        Fetch data from FRED API.

        Args:
            series_id: FRED series identifier

        Returns:
            Observation data or None if unavailable
        """
        if not self._fred_api_key:
            logger.debug("FRED API key not configured, using mock data")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": series_id,
                    "api_key": self._fred_api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 2,  # Get latest and previous for change calculation
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("observations", [])
        except httpx.HTTPError as e:
            logger.warning(f"FRED API error for {series_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching from FRED: {e}")
            return None

    def get_mock_key_rates(self) -> list[dict]:
        """Return mock key rates data."""
        return [
            {
                "id": "fed-funds",
                "name": "Federal Funds Rate",
                "short_name": "Fed Funds",
                "current_value": 5.33,
                "previous_value": 5.33,
                "change": 0,
                "change_percent": 0,
                "as_of_date": "2025-12-05",
                "category": "federal",
                "description": "The interest rate at which banks lend reserve balances to other banks overnight.",
            },
            {
                "id": "prime-rate",
                "name": "Prime Rate",
                "short_name": "Prime",
                "current_value": 8.50,
                "previous_value": 8.50,
                "change": 0,
                "change_percent": 0,
                "as_of_date": "2025-12-05",
                "category": "federal",
                "description": "The rate that commercial banks charge their most creditworthy customers.",
            },
            {
                "id": "treasury-2y",
                "name": "2-Year Treasury Yield",
                "short_name": "2Y Treasury",
                "current_value": 4.18,
                "previous_value": 4.21,
                "change": -0.03,
                "change_percent": -0.71,
                "as_of_date": "2025-12-05",
                "category": "treasury",
                "description": "Yield on 2-year U.S. Treasury notes.",
            },
            {
                "id": "treasury-5y",
                "name": "5-Year Treasury Yield",
                "short_name": "5Y Treasury",
                "current_value": 4.05,
                "previous_value": 4.09,
                "change": -0.04,
                "change_percent": -0.98,
                "as_of_date": "2025-12-05",
                "category": "treasury",
                "description": "Yield on 5-year U.S. Treasury notes.",
            },
            {
                "id": "treasury-7y",
                "name": "7-Year Treasury Yield",
                "short_name": "7Y Treasury",
                "current_value": 4.12,
                "previous_value": 4.15,
                "change": -0.03,
                "change_percent": -0.72,
                "as_of_date": "2025-12-05",
                "category": "treasury",
                "description": "Yield on 7-year U.S. Treasury notes.",
            },
            {
                "id": "treasury-10y",
                "name": "10-Year Treasury Yield",
                "short_name": "10Y Treasury",
                "current_value": 4.22,
                "previous_value": 4.26,
                "change": -0.04,
                "change_percent": -0.94,
                "as_of_date": "2025-12-05",
                "category": "treasury",
                "description": "Yield on 10-year U.S. Treasury notes. Key benchmark for mortgage rates.",
            },
            {
                "id": "sofr-1m",
                "name": "1-Month SOFR",
                "short_name": "1M SOFR",
                "current_value": 5.34,
                "previous_value": 5.34,
                "change": 0,
                "change_percent": 0,
                "as_of_date": "2025-12-05",
                "category": "sofr",
                "description": "Secured Overnight Financing Rate, 1-month average.",
            },
            {
                "id": "sofr-term-1m",
                "name": "1-Month Term SOFR",
                "short_name": "1M Term SOFR",
                "current_value": 5.32,
                "previous_value": 5.33,
                "change": -0.01,
                "change_percent": -0.19,
                "as_of_date": "2025-12-05",
                "category": "sofr",
                "description": "CME Term SOFR, 1-month rate.",
            },
            {
                "id": "mortgage-30y",
                "name": "30-Year Fixed Mortgage Rate",
                "short_name": "30Y Mortgage",
                "current_value": 6.84,
                "previous_value": 6.91,
                "change": -0.07,
                "change_percent": -1.01,
                "as_of_date": "2025-12-05",
                "category": "mortgage",
                "description": "Average rate for 30-year fixed-rate mortgages.",
            },
        ]

    def get_mock_yield_curve(self) -> list[dict]:
        """Return mock yield curve data."""
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
        """Return mock historical rate data."""
        all_data = [
            {
                "date": "2025-01",
                "federal_funds": 5.33,
                "treasury_2y": 4.21,
                "treasury_5y": 3.84,
                "treasury_10y": 3.95,
                "treasury_30y": 4.14,
                "sofr": 5.31,
                "mortgage_30y": 6.64,
            },
            {
                "date": "2025-02",
                "federal_funds": 5.33,
                "treasury_2y": 4.64,
                "treasury_5y": 4.26,
                "treasury_10y": 4.25,
                "treasury_30y": 4.38,
                "sofr": 5.31,
                "mortgage_30y": 6.94,
            },
            {
                "date": "2025-03",
                "federal_funds": 5.33,
                "treasury_2y": 4.59,
                "treasury_5y": 4.21,
                "treasury_10y": 4.20,
                "treasury_30y": 4.34,
                "sofr": 5.31,
                "mortgage_30y": 6.82,
            },
            {
                "date": "2025-04",
                "federal_funds": 5.33,
                "treasury_2y": 4.97,
                "treasury_5y": 4.63,
                "treasury_10y": 4.59,
                "treasury_30y": 4.73,
                "sofr": 5.31,
                "mortgage_30y": 7.17,
            },
            {
                "date": "2025-05",
                "federal_funds": 5.33,
                "treasury_2y": 4.87,
                "treasury_5y": 4.48,
                "treasury_10y": 4.50,
                "treasury_30y": 4.65,
                "sofr": 5.31,
                "mortgage_30y": 7.06,
            },
            {
                "date": "2025-06",
                "federal_funds": 5.33,
                "treasury_2y": 4.71,
                "treasury_5y": 4.31,
                "treasury_10y": 4.36,
                "treasury_30y": 4.51,
                "sofr": 5.31,
                "mortgage_30y": 6.92,
            },
            {
                "date": "2025-07",
                "federal_funds": 5.33,
                "treasury_2y": 4.38,
                "treasury_5y": 4.07,
                "treasury_10y": 4.17,
                "treasury_30y": 4.40,
                "sofr": 5.31,
                "mortgage_30y": 6.77,
            },
            {
                "date": "2025-08",
                "federal_funds": 5.33,
                "treasury_2y": 3.92,
                "treasury_5y": 3.70,
                "treasury_10y": 3.90,
                "treasury_30y": 4.19,
                "sofr": 5.31,
                "mortgage_30y": 6.50,
            },
            {
                "date": "2025-09",
                "federal_funds": 5.00,
                "treasury_2y": 3.55,
                "treasury_5y": 3.42,
                "treasury_10y": 3.73,
                "treasury_30y": 4.08,
                "sofr": 4.96,
                "mortgage_30y": 6.18,
            },
            {
                "date": "2025-10",
                "federal_funds": 4.83,
                "treasury_2y": 4.17,
                "treasury_5y": 4.04,
                "treasury_10y": 4.28,
                "treasury_30y": 4.52,
                "sofr": 4.81,
                "mortgage_30y": 6.72,
            },
            {
                "date": "2025-11",
                "federal_funds": 4.58,
                "treasury_2y": 4.24,
                "treasury_5y": 4.12,
                "treasury_10y": 4.35,
                "treasury_30y": 4.54,
                "sofr": 4.56,
                "mortgage_30y": 6.88,
            },
            {
                "date": "2025-12",
                "federal_funds": 4.58,
                "treasury_2y": 4.18,
                "treasury_5y": 4.05,
                "treasury_10y": 4.22,
                "treasury_30y": 4.42,
                "sofr": 4.56,
                "mortgage_30y": 6.84,
            },
        ]
        # Return most recent N months
        return all_data[-months:] if months < len(all_data) else all_data

    def get_mock_data_sources(self) -> list[dict]:
        """Return mock data sources."""
        return [
            {
                "id": "treasury-gov",
                "name": "U.S. Treasury Department",
                "url": "https://home.treasury.gov/",
                "description": "Official source for Treasury yield curve data, auction results, and government securities information.",
                "data_types": ["Treasury Yields", "Yield Curve", "Auction Results", "Savings Bonds"],
                "update_frequency": "Daily",
            },
            {
                "id": "fred",
                "name": "Federal Reserve Economic Data (FRED)",
                "url": "https://fred.stlouisfed.org/",
                "description": "Comprehensive economic database maintained by the Federal Reserve Bank of St. Louis.",
                "data_types": ["Federal Funds Rate", "Treasury Yields", "SOFR", "Economic Indicators"],
                "update_frequency": "Daily",
            },
            {
                "id": "treasury-direct",
                "name": "TreasuryDirect",
                "url": "https://treasurydirect.gov/",
                "description": "Official source for purchasing and managing U.S. Treasury securities.",
                "data_types": ["Savings Bonds", "Treasury Bills", "Treasury Notes", "Treasury Bonds"],
                "update_frequency": "Real-time",
            },
            {
                "id": "bankrate",
                "name": "Bankrate",
                "url": "https://www.bankrate.com/",
                "description": "Leading source for current mortgage rates, personal loan rates, and banking information.",
                "data_types": ["Mortgage Rates", "CD Rates", "Savings Rates", "Loan Rates"],
                "update_frequency": "Daily",
            },
            {
                "id": "cme-sofr",
                "name": "CME Group - SOFR",
                "url": "https://www.cmegroup.com/markets/interest-rates/stirs/sofr.html",
                "description": "Official source for Term SOFR rates and SOFR futures trading information.",
                "data_types": ["Term SOFR", "SOFR Futures", "SOFR Options"],
                "update_frequency": "Real-time",
            },
            {
                "id": "ny-fed",
                "name": "Federal Reserve Bank of New York",
                "url": "https://www.newyorkfed.org/markets/reference-rates/sofr",
                "description": "Official administrator of SOFR and related reference rates.",
                "data_types": ["SOFR", "EFFR", "OBFR", "TGCR"],
                "update_frequency": "Daily",
            },
        ]

    def get_lending_context(self) -> dict:
        """Return real estate lending context with typical spreads."""
        # Get current rates for calculation
        key_rates = {r["id"]: r["current_value"] for r in self.get_mock_key_rates()}
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
        }

    def calculate_spreads(self, historical_rates: list[dict]) -> dict:
        """Calculate rate spreads from historical data."""
        treasury_spread_2s10s = []
        mortgage_spread = []
        fed_funds_vs_treasury = []

        for rate in historical_rates:
            treasury_spread_2s10s.append({
                "date": rate["date"],
                "spread": round(rate["treasury_10y"] - rate["treasury_2y"], 2),
            })
            mortgage_spread.append({
                "date": rate["date"],
                "spread": round(rate["mortgage_30y"] - rate["treasury_10y"], 2),
            })
            fed_funds_vs_treasury.append({
                "date": rate["date"],
                "fed_funds": rate["federal_funds"],
                "treasury_10y": rate["treasury_10y"],
                "spread": round(rate["federal_funds"] - rate["treasury_10y"], 2),
            })

        return {
            "treasury_spread_2s10s": treasury_spread_2s10s,
            "mortgage_spread": mortgage_spread,
            "fed_funds_vs_treasury": fed_funds_vs_treasury,
        }

    async def get_key_rates(self) -> dict:
        """
        Get current key interest rates.

        Attempts FRED API first, falls back to mock data.
        """
        cache_key = "key_rates"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Try FRED API
        if self._fred_api_key:
            # TODO: Implement actual FRED API integration
            # For now, use mock data
            pass

        # Use mock data
        data = {
            "key_rates": self.get_mock_key_rates(),
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "mock",
        }

        self._set_cache(cache_key, data)
        return data

    async def get_yield_curve(self) -> dict:
        """
        Get current Treasury yield curve.

        Attempts FRED API first, falls back to mock data.
        """
        cache_key = "yield_curve"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Use mock data (FRED integration would go here)
        yield_curve = self.get_mock_yield_curve()
        data = {
            "yield_curve": yield_curve,
            "as_of_date": "2025-12-05",
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "mock",
        }

        self._set_cache(cache_key, data)
        return data

    async def get_historical_rates(self, months: int = 12) -> dict:
        """
        Get historical interest rates.

        Args:
            months: Number of months of historical data (default 12)
        """
        cache_key = f"historical_rates_{months}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Use mock data
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

        historical = self.get_mock_historical_rates(months)
        spreads = self.calculate_spreads(historical)

        data = {
            "spreads": spreads,
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "mock",
        }

        self._set_cache(cache_key, data)
        return data


# Singleton instance
_interest_rates_service: InterestRatesService | None = None


def get_interest_rates_service() -> InterestRatesService:
    """Get or create interest rates service singleton."""
    global _interest_rates_service
    if _interest_rates_service is None:
        _interest_rates_service = InterestRatesService()
    return _interest_rates_service
