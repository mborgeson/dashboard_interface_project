"""
FRED API Extractor — fetches Federal Reserve Economic Data series.

17 series covering interest rates, Phoenix economic indicators, and national CPI.
Supports full-history first run and incremental updates.

Usage:
  python -m app.services.data_extraction.fred_extractor
  python -m app.services.data_extraction.fred_extractor --incremental
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from typing import Any

import httpx
import structlog
from sqlalchemy import create_engine, text

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATCH_SIZE = 1000
REQUEST_DELAY = 0.6  # seconds — FRED allows ~120 requests/min


class FREDExtractor:
    """Extracts economic data from the FRED API and stores in database."""

    SERIES_IDS: dict[str, str] = {
        # Interest rates (14)
        "FEDFUNDS": "Federal Funds Effective Rate",
        "DPRIME": "Bank Prime Loan Rate",
        "DGS1MO": "1-Month Treasury",
        "DGS3MO": "3-Month Treasury",
        "DGS6MO": "6-Month Treasury",
        "DGS1": "1-Year Treasury",
        "DGS2": "2-Year Treasury",
        "DGS5": "5-Year Treasury",
        "DGS7": "7-Year Treasury",
        "DGS10": "10-Year Treasury",
        "DGS20": "20-Year Treasury",
        "DGS30": "30-Year Treasury",
        "SOFR": "Secured Overnight Financing Rate",
        "MORTGAGE30US": "30-Year Fixed Rate Mortgage Average",
        # Phoenix economic (2)
        "PHOE004UR": "Phoenix Unemployment Rate",
        "PHOE004NA": "Phoenix All Employees Total Nonfarm",
        # National economic (1)
        "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    }

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: str, db_url: str) -> None:
        """Initialize with FRED API key and database URL."""
        if not api_key:
            raise ValueError("FRED API key is required")
        if not db_url:
            raise ValueError("Database URL is required")

        self._api_key = api_key
        self._db_url = db_url
        self._engine = create_engine(db_url)
        self._log = logger.bind(service="fred_extractor")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def extract_all(self, incremental: bool = True) -> dict[str, Any]:
        """Extract all 17 series.

        If *incremental* is True, only fetch data newer than what is already
        in the database.  Returns a summary dict with status, counts, and
        any errors encountered.
        """
        self._log.info(
            "fred_extraction_started",
            series_count=len(self.SERIES_IDS),
            incremental=incremental,
        )

        # Create extraction_log entry
        log_id = self._insert_extraction_log()

        total_records = 0
        series_processed = 0
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            self._client = client

            for series_id in self.SERIES_IDS:
                try:
                    start_date: date | None = None
                    if incremental:
                        start_date = await self._get_last_date(series_id)
                        if start_date:
                            self._log.debug(
                                "incremental_start",
                                series_id=series_id,
                                start_date=str(start_date),
                            )

                    count = await self.extract_series(series_id, start_date)
                    total_records += count
                    series_processed += 1

                    if count > 0:
                        self._log.info(
                            "series_extracted",
                            series_id=series_id,
                            records=count,
                        )
                    else:
                        self._log.debug("series_no_new_data", series_id=series_id)

                    # Update metadata for the series
                    await self._update_series_metadata(series_id)

                except Exception as exc:
                    msg = f"{series_id}: {exc}"
                    self._log.error(
                        "series_extraction_failed",
                        series_id=series_id,
                        error=str(exc),
                    )
                    errors.append(msg)

            self._client = None  # type: ignore[assignment]

        # Refresh materialized view
        self._refresh_materialized_view()

        # Finalize extraction_log
        status = "success" if not errors else "error"
        self._finalize_extraction_log(
            log_id, status, total_records, series_processed, incremental, errors
        )

        summary: dict[str, Any] = {
            "status": status,
            "series_processed": series_processed,
            "records_upserted": total_records,
            "errors": errors,
        }
        self._log.info("fred_extraction_complete", **summary)
        return summary

    async def extract_series(
        self, series_id: str, start_date: date | None = None
    ) -> int:
        """Fetch observations for a single series from the FRED API.

        If *start_date* is provided, only fetch observations from that date
        forward.  Returns the number of records upserted.
        """
        observations = await self._fetch_observations(series_id, start_date)
        if not observations:
            return 0

        return self._batch_upsert(series_id, observations)

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    async def _get_last_date(self, series_id: str) -> date | None:
        """Query database for MAX(date) of a series for incremental updates."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT MAX(date)::text FROM fred_timeseries WHERE series_id = :sid"
                ),
                {"sid": series_id},
            )
            row = result.fetchone()
            if row and row[0]:
                return date.fromisoformat(row[0])
        return None

    def _batch_upsert(self, series_id: str, records: list[dict]) -> int:
        """Upsert observations into fred_timeseries in chunks of BATCH_SIZE."""
        if not records:
            return 0

        upserted = 0
        for i in range(0, len(records), BATCH_SIZE):
            chunk = records[i : i + BATCH_SIZE]
            self._upsert_chunk(series_id, chunk)
            upserted += len(chunk)

        return upserted

    def _upsert_chunk(self, series_id: str, chunk: list[dict]) -> None:
        """Execute a batch upsert for a chunk of records."""
        if not chunk:
            return

        # Build a multi-row VALUES clause for efficient batch insert
        placeholders = []
        params: dict[str, Any] = {}
        for idx, rec in enumerate(chunk):
            placeholders.append(f"(:sid_{idx}, :dt_{idx}, :val_{idx})")
            params[f"sid_{idx}"] = series_id
            params[f"dt_{idx}"] = rec["date"]
            params[f"val_{idx}"] = rec["value"]

        values_clause = ", ".join(placeholders)
        sql = text(f"""
            INSERT INTO fred_timeseries (series_id, date, value)
            VALUES {values_clause}
            ON CONFLICT (series_id, date)
            DO UPDATE SET value = EXCLUDED.value, imported_at = NOW()
        """)

        with self._engine.begin() as conn:
            conn.execute(sql, params)

    # ------------------------------------------------------------------
    # FRED API calls
    # ------------------------------------------------------------------

    async def _fetch_observations(
        self, series_id: str, start_date: date | None = None
    ) -> list[dict]:
        """Call FRED API ``/fred/series/observations`` endpoint.

        Returns list of ``{date, value}`` dicts.  Rows where the FRED value
        is ``"."`` (missing) are silently skipped.
        """
        params: dict[str, str] = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "sort_order": "asc",
        }
        if start_date is not None:
            params["observation_start"] = start_date.isoformat()

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/series/observations", params=params
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            self._log.warning(
                "fred_api_http_error",
                series_id=series_id,
                status_code=exc.response.status_code,
            )
            return []
        except Exception as exc:
            self._log.error(
                "fred_api_request_error",
                series_id=series_id,
                error=str(exc),
            )
            return []

        # Rate limiting — sleep after every request
        await asyncio.sleep(REQUEST_DELAY)

        observations = data.get("observations", [])
        valid: list[dict] = []
        for obs in observations:
            val_str = obs.get("value", ".")
            if val_str == "." or val_str is None:
                continue
            try:
                val = float(val_str)
                valid.append({"date": obs["date"], "value": val})
            except (ValueError, TypeError):
                continue

        return valid

    async def _update_series_metadata(self, series_id: str) -> None:
        """Fetch and update ``fred_series_metadata`` table for a series."""
        params: dict[str, str] = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
        }

        try:
            response = await self._client.get(f"{self.BASE_URL}/series", params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            self._log.debug(
                "metadata_fetch_skipped",
                series_id=series_id,
                error=str(exc),
            )
            return

        await asyncio.sleep(REQUEST_DELAY)

        serieses = data.get("seriess", [])
        if not serieses:
            return

        meta = serieses[0]

        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO fred_series_metadata
                        (series_id, title, frequency, units, seasonal_adjustment,
                         observation_start, observation_end, last_updated)
                    VALUES
                        (:series_id, :title, :frequency, :units, :seasonal_adj,
                         :obs_start, :obs_end, :last_updated)
                    ON CONFLICT (series_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        frequency = EXCLUDED.frequency,
                        units = EXCLUDED.units,
                        seasonal_adjustment = EXCLUDED.seasonal_adjustment,
                        observation_start = EXCLUDED.observation_start,
                        observation_end = EXCLUDED.observation_end,
                        last_updated = EXCLUDED.last_updated,
                        imported_at = NOW()
                """),
                {
                    "series_id": series_id,
                    "title": meta.get("title"),
                    "frequency": meta.get("frequency_short"),
                    "units": meta.get("units"),
                    "seasonal_adj": meta.get("seasonal_adjustment_short"),
                    "obs_start": meta.get("observation_start"),
                    "obs_end": meta.get("observation_end"),
                    "last_updated": meta.get("last_updated"),
                },
            )

    # ------------------------------------------------------------------
    # Extraction log helpers
    # ------------------------------------------------------------------

    def _insert_extraction_log(self) -> int:
        """Insert a new extraction_log row with status='running'."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO extraction_log (source, status) "
                    "VALUES ('fred', 'running') RETURNING id"
                )
            )
            return result.scalar()  # type: ignore[return-value]

    def _finalize_extraction_log(
        self,
        log_id: int,
        status: str,
        records: int,
        series_processed: int,
        incremental: bool,
        errors: list[str],
    ) -> None:
        """Update the extraction_log row with final results."""
        import json

        details = json.dumps(
            {
                "series_processed": series_processed,
                "incremental": incremental,
            }
        )

        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE extraction_log
                    SET finished_at = NOW(),
                        status = :status,
                        records_upserted = :records,
                        error_message = :errors,
                        details = :details
                    WHERE id = :log_id
                """),
                {
                    "status": status,
                    "records": records,
                    "errors": "; ".join(errors) if errors else None,
                    "details": details,
                    "log_id": log_id,
                },
            )

    def _refresh_materialized_view(self) -> None:
        """Refresh the ``fred_latest`` materialized view."""
        try:
            with self._engine.begin() as conn:
                conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY fred_latest"))
            self._log.info("materialized_view_refreshed", view="fred_latest")
        except Exception as exc:
            self._log.warning(
                "materialized_view_concurrent_refresh_failed",
                error=str(exc),
            )
            # Fall back to non-concurrent refresh
            try:
                with self._engine.begin() as conn:
                    conn.execute(text("REFRESH MATERIALIZED VIEW fred_latest"))
                self._log.info(
                    "materialized_view_refreshed_non_concurrent",
                    view="fred_latest",
                )
            except Exception as fallback_exc:
                self._log.error(
                    "materialized_view_refresh_failed",
                    error=str(fallback_exc),
                )


# -----------------------------------------------------------------------
# Legacy functional API (backward compatibility)
# -----------------------------------------------------------------------


async def run_fred_extraction_async(engine=None, incremental: bool = True) -> dict:
    """Fetch all 17 FRED series and upsert into database.

    Thin wrapper around :class:`FREDExtractor` for backward compatibility
    with callers that used the old functional interface.
    """
    from app.core.config import settings

    api_key = settings.FRED_API_KEY
    db_url = settings.MARKET_ANALYSIS_DB_URL

    if not api_key:
        logger.error("FRED_API_KEY not configured")
        return {"status": "error", "message": "No FRED API key"}
    if not db_url:
        logger.error("MARKET_ANALYSIS_DB_URL not configured")
        return {"status": "error", "message": "No DB URL configured"}

    extractor = FREDExtractor(api_key=api_key, db_url=db_url)

    # Allow callers to inject an engine (used by scheduler / tests)
    if engine is not None:
        extractor._engine = engine

    return await extractor.extract_all(incremental=incremental)


def run_fred_extraction(engine=None, incremental: bool = True) -> dict:
    """Synchronous wrapper for :func:`run_fred_extraction_async`."""
    return asyncio.run(run_fred_extraction_async(engine, incremental))


# -----------------------------------------------------------------------
# Script entry-point
# -----------------------------------------------------------------------


async def main() -> None:
    """Run FRED extraction as a standalone script."""
    from app.core.config import settings

    incremental = "--incremental" in sys.argv

    extractor = FREDExtractor(
        api_key=settings.FRED_API_KEY,  # type: ignore[arg-type]
        db_url=settings.MARKET_ANALYSIS_DB_URL,  # type: ignore[arg-type]
    )
    result = await extractor.extract_all(incremental=incremental)
    print(f"FRED extraction complete: {result}")

    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    asyncio.run(main())
