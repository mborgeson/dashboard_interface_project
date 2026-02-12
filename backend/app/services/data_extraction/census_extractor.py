"""
Census Bureau Extractor — fetches ACS 5-Year estimates for Phoenix MSA.

Variables:
  B01003_001E — Total Population
  B19013_001E — Median Household Income

Geography: Phoenix-Mesa-Chandler MSA (CBSA 38060)
Range: 2010–2024

Usage:
  python -m app.services.data_extraction.census_extractor
"""

from __future__ import annotations

import asyncio
import sys

import httpx
import structlog
from sqlalchemy import create_engine, text

from app.core.config import settings

log = structlog.get_logger(__name__)


class CensusExtractor:
    """Extracts population and economic data from Census Bureau API."""

    BASE_URL = "https://api.census.gov/data"

    # ACS 5-Year Subject variables for Phoenix MSA (CBSA 38060)
    VARIABLES = {
        "B01003_001E": "Total Population",
        "B19013_001E": "Median Household Income",
    }

    GEOGRAPHY = {
        "for": "metropolitan statistical area/micropolitan statistical area:38060",
    }

    PHOENIX_CBSA = "38060"
    GEOGRAPHY_NAME = "Phoenix-Mesa-Chandler, AZ Metro Area"

    # Year range for ACS 5-Year estimates
    YEAR_START = 2010
    YEAR_END = 2024

    # Rate limiting: 0.5s between requests (Census API is slower)
    REQUEST_DELAY = 0.5

    def __init__(self, api_key: str, db_url: str) -> None:
        """Initialize with Census API key and database URL."""
        self.api_key = api_key
        self.db_url = db_url
        self._engine = create_engine(db_url)

    async def extract_all(self) -> dict:
        """Extract all configured variables for all years.

        Returns summary dict with record counts.
        """
        log.info(
            "census_extraction_started", year_range=f"{self.YEAR_START}-{self.YEAR_END}"
        )

        # Log extraction start
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO extraction_log (source, status) "
                    "VALUES ('census', 'running') RETURNING id"
                ),
            )
            log_id = result.scalar()

        total_records = 0
        years_processed = 0
        errors: list[str] = []

        for year in range(self.YEAR_START, self.YEAR_END + 1):
            try:
                count = await self.extract_year(year)
                total_records += count
                if count > 0:
                    years_processed += 1
            except Exception as exc:
                msg = f"{year}: {exc}"
                log.error("census_year_error", year=year, error=str(exc))
                errors.append(msg)

            # Rate limiting between requests
            await asyncio.sleep(self.REQUEST_DELAY)

        # Update extraction log
        status = "success" if not errors else "error"
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE extraction_log "
                    "SET finished_at = NOW(), status = :status, records_upserted = :records, "
                    "    error_message = :errors, details = :details "
                    "WHERE id = :log_id"
                ),
                {
                    "status": status,
                    "records": total_records,
                    "errors": "; ".join(errors) if errors else None,
                    "details": f'{{"years_processed": {years_processed}}}',
                    "log_id": log_id,
                },
            )

        summary = {
            "status": status,
            "years_processed": years_processed,
            "records_upserted": total_records,
            "errors": errors,
        }
        log.info("census_extraction_complete", **summary)
        return summary

    async def extract_year(self, year: int) -> int:
        """Fetch ACS data for a specific year.

        Tries ACS 1-Year first, falls back to ACS 5-Year if unavailable.
        Returns number of records upserted.
        """
        var_codes = list(self.VARIABLES.keys())

        # Try ACS 1-Year first (more recent, but limited geographies)
        data = await self._fetch_acs_data(year, var_codes, dataset="acs1")
        dataset_used = "acs1"

        if data is None:
            # Fall back to ACS 5-Year (broader coverage)
            data = await self._fetch_acs_data(year, var_codes, dataset="acs5")
            dataset_used = "acs5"

        if data is None:
            log.debug("census_no_data", year=year)
            return 0

        count = 0
        with self._engine.begin() as conn:
            for var_code, value in data.items():
                conn.execute(
                    text(
                        "INSERT INTO census_timeseries "
                        "    (variable_code, variable_name, geography, geography_code, "
                        "     year, value, dataset) "
                        "VALUES "
                        "    (:var_code, :var_name, :geo, :geo_code, :year, :value, :dataset) "
                        "ON CONFLICT (variable_code, geography_code, year) "
                        "DO UPDATE SET value = EXCLUDED.value, "
                        "    dataset = EXCLUDED.dataset, imported_at = NOW()"
                    ),
                    {
                        "var_code": var_code,
                        "var_name": self.VARIABLES[var_code],
                        "geo": self.GEOGRAPHY_NAME,
                        "geo_code": self.PHOENIX_CBSA,
                        "year": year,
                        "value": value,
                        "dataset": dataset_used,
                    },
                )
                count += 1

        log.info(
            "census_year_fetched", year=year, variables=count, dataset=dataset_used
        )
        return count

    async def _fetch_acs_data(
        self, year: int, variables: list[str], dataset: str = "acs1"
    ) -> dict[str, float] | None:
        """Call Census API for ACS estimates.

        Args:
            year: Data year.
            variables: List of Census variable codes.
            dataset: ACS dataset to query — ``"acs1"`` (1-Year) or ``"acs5"`` (5-Year).

        URL pattern:
          https://api.census.gov/data/{year}/acs/{dataset}
            ?get=NAME,{variable_codes}
            &for=metropolitan+statistical+area/micropolitan+statistical+area:38060
            &key={api_key}

        Returns parsed variable-to-value mapping, or None on error.
        """
        var_str = ",".join(["NAME"] + variables)
        url = f"{self.BASE_URL}/{year}/acs/{dataset}"
        params = {
            "get": var_str,
            "for": self.GEOGRAPHY["for"],
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if len(data) < 2:
                return None

            header = data[0]
            values = data[1]

            result: dict[str, float] = {}
            for var_code in variables:
                try:
                    idx = header.index(var_code)
                    val = values[idx]
                    if val is not None and str(val) not in ("", "-", "null"):
                        result[var_code] = float(val)
                except (ValueError, IndexError):
                    continue

            return result if result else None

        except httpx.HTTPStatusError as exc:
            log.warning(
                "census_api_http_error",
                year=year,
                dataset=dataset,
                status_code=exc.response.status_code,
            )
            return None
        except Exception as exc:
            log.warning("census_api_error", year=year, dataset=dataset, error=str(exc))
            return None


# ---------------------------------------------------------------------------
# Synchronous wrapper (backward-compatible with scheduler / existing callers)
# ---------------------------------------------------------------------------


def run_census_extraction(engine=None) -> dict:
    """Synchronous entry point for the extraction scheduler.

    Creates a CensusExtractor and runs extract_all().
    """
    api_key = settings.CENSUS_API_KEY
    if not api_key:
        log.error("census_api_key_missing")
        return {"status": "error", "message": "No Census API key"}

    db_url = settings.MARKET_ANALYSIS_DB_URL
    if not db_url:
        log.error("census_db_url_missing")
        return {"status": "error", "message": "No DB URL configured"}

    extractor = CensusExtractor(api_key=api_key, db_url=db_url)

    # Allow caller to inject an engine (used by scheduler)
    if engine is not None:
        extractor._engine = engine

    return asyncio.run(extractor.extract_all())


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    """Async main for direct script execution."""
    api_key = settings.CENSUS_API_KEY
    db_url = settings.MARKET_ANALYSIS_DB_URL

    if not api_key:
        print("ERROR: CENSUS_API_KEY not set")
        sys.exit(1)
    if not db_url:
        print("ERROR: MARKET_ANALYSIS_DB_URL not set")
        sys.exit(1)

    extractor = CensusExtractor(api_key=api_key, db_url=db_url)
    result = await extractor.extract_all()
    print(f"Census extraction complete: {result}")
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    asyncio.run(main())
