"""
FRED API Extractor — fetches Federal Reserve Economic Data series.

17 series covering interest rates, Phoenix economic indicators, and national CPI.
Supports full-history first run and incremental updates.

Usage:
  python -m app.services.data_extraction.fred_extractor
"""

import asyncio
import sys
import time

import httpx
from loguru import logger
from sqlalchemy import create_engine, text

from app.core.config import settings

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# All 17 FRED series to extract
FRED_SERIES = [
    "FEDFUNDS",
    "DPRIME",
    "DGS1MO",
    "DGS3MO",
    "DGS6MO",
    "DGS1",
    "DGS2",
    "DGS5",
    "DGS7",
    "DGS10",
    "DGS20",
    "DGS30",
    "SOFR",
    "MORTGAGE30US",
    "PHOE004UR",
    "PHOE004NA",
    "CPIAUCSL",
]

# Rate limit: 120 requests per minute for FRED API
REQUEST_DELAY = 0.6  # seconds between requests


async def fetch_series(
    client: httpx.AsyncClient,
    series_id: str,
    api_key: str,
    observation_start: str | None = None,
) -> list[dict]:
    """Fetch observations for a single FRED series."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "asc",
    }
    if observation_start:
        params["observation_start"] = observation_start

    try:
        response = await client.get(FRED_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        observations = data.get("observations", [])

        # Filter out missing values (FRED uses "." for missing)
        valid = []
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
    except httpx.HTTPStatusError as e:
        logger.warning(f"FRED API HTTP error for {series_id}: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Error fetching FRED series {series_id}: {e}")
        return []


def _get_max_date(engine, series_id: str) -> str | None:
    """Get the latest date for a series in the database."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT MAX(date)::text FROM fred_timeseries WHERE series_id = :sid"),
            {"sid": series_id},
        )
        row = result.fetchone()
        return row[0] if row and row[0] else None


def _batch_upsert_fred(engine, series_id: str, records: list[dict]) -> int:
    """Upsert FRED observations into fred_timeseries."""
    if not records:
        return 0

    with engine.begin() as conn:
        for rec in records:
            conn.execute(
                text("""
                    INSERT INTO fred_timeseries (series_id, date, value)
                    VALUES (:series_id, :date, :value)
                    ON CONFLICT (series_id, date)
                    DO UPDATE SET value = EXCLUDED.value, imported_at = NOW()
                """),
                {"series_id": series_id, "date": rec["date"], "value": rec["value"]},
            )
    return len(records)


async def run_fred_extraction_async(engine=None, incremental: bool = True) -> dict:
    """
    Fetch all 17 FRED series and upsert into database.

    Args:
        engine: SQLAlchemy engine (created from settings if None)
        incremental: If True, only fetch data newer than what's in DB

    Returns extraction summary.
    """
    api_key = settings.FRED_API_KEY
    if not api_key:
        logger.error("FRED_API_KEY not configured")
        return {"status": "error", "message": "No FRED API key"}

    if engine is None:
        db_url = settings.MARKET_ANALYSIS_DB_URL
        if not db_url:
            logger.error("MARKET_ANALYSIS_DB_URL not configured")
            return {"status": "error", "message": "No DB URL configured"}
        engine = create_engine(db_url)

    # Log extraction start
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO extraction_log (source, status) VALUES ('fred', 'running') RETURNING id"
            ),
        )
        log_id = result.scalar()

    total_records = 0
    series_processed = 0
    errors = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for series_id in FRED_SERIES:
            try:
                # Determine start date for incremental fetch
                start_date = None
                if incremental:
                    max_date = _get_max_date(engine, series_id)
                    if max_date:
                        start_date = max_date
                        logger.debug(f"  {series_id}: incremental from {start_date}")

                observations = await fetch_series(
                    client, series_id, api_key, start_date
                )

                if observations:
                    count = _batch_upsert_fred(engine, series_id, observations)
                    total_records += count
                    logger.info(f"  {series_id}: {count} records")
                else:
                    logger.debug(f"  {series_id}: no new data")

                series_processed += 1

                # Rate limiting
                time.sleep(REQUEST_DELAY)

            except Exception as e:
                logger.error(f"Error processing FRED series {series_id}: {e}")
                errors.append(f"{series_id}: {e}")

    # Refresh materialized view
    try:
        with engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY fred_latest"))
    except Exception as e:
        logger.warning(f"Could not refresh fred_latest view: {e}")
        try:
            with engine.begin() as conn:
                conn.execute(text("REFRESH MATERIALIZED VIEW fred_latest"))
        except Exception:
            pass

    # Update extraction log
    status = "success" if not errors else "error"
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE extraction_log
                SET finished_at = NOW(), status = :status, records_upserted = :records,
                    error_message = :errors,
                    details = :details
                WHERE id = :log_id
            """),
            {
                "status": status,
                "records": total_records,
                "errors": "; ".join(errors) if errors else None,
                "details": f'{{"series_processed": {series_processed}, "incremental": {str(incremental).lower()}}}',
                "log_id": log_id,
            },
        )

    summary = {
        "status": status,
        "series_processed": series_processed,
        "records_upserted": total_records,
        "errors": errors,
    }
    logger.info(f"FRED extraction complete: {summary}")
    return summary


def run_fred_extraction(engine=None, incremental: bool = True) -> dict:
    """Synchronous wrapper for run_fred_extraction_async."""
    return asyncio.run(run_fred_extraction_async(engine, incremental))


if __name__ == "__main__":
    # First run: full history (incremental=False)
    incremental = "--incremental" in sys.argv
    result = run_fred_extraction(incremental=incremental)
    print(result)
    sys.exit(0 if result["status"] == "success" else 1)
