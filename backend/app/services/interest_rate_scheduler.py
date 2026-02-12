"""
Interest Rate Scheduler — fetches FRED interest rate series twice daily.

Schedule (Phoenix timezone, configurable via settings):
  - AM run: 8 AM daily     INTEREST_RATE_SCHEDULE_CRON_AM
  - PM run: 3 PM daily     INTEREST_RATE_SCHEDULE_CRON_PM

Fetches 14 key FRED series and upserts the last 5 observations per series
into the ``fred_timeseries`` table in the market analysis database.

Integration with app lifecycle (main.py lifespan):
    scheduler = InterestRateScheduler(settings)
    await scheduler.start()
    yield
    await scheduler.stop()
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import Settings, settings

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler


# FRED series to fetch (covers key rates + full yield curve)
INTEREST_RATE_SERIES = [
    "FEDFUNDS",
    "DPRIME",
    "DGS2",
    "DGS5",
    "DGS7",
    "DGS10",
    "DGS30",
    "SOFR",
    "MORTGAGE30US",
    "DGS1MO",
    "DGS3MO",
    "DGS6MO",
    "DGS1",
    "DGS20",
]

# Delay between FRED API calls to respect rate limits
REQUEST_DELAY = 0.6
OBSERVATIONS_PER_SERIES = 5


def _parse_cron_parts(cron_expr: str) -> dict[str, str]:
    """Parse a standard 5-field cron expression into APScheduler CronTrigger kwargs."""
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (expected 5 fields): {cron_expr!r}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def _get_engine(db_url: str | None = None) -> Engine:
    """Create a sync SQLAlchemy engine for the market_analysis DB."""
    url = db_url or settings.MARKET_ANALYSIS_DB_URL
    if not url:
        raise RuntimeError("MARKET_ANALYSIS_DB_URL not configured")
    return create_engine(url)


class InterestRateScheduler:
    """Schedules twice-daily FRED interest rate fetches.

    Uses APScheduler's AsyncIOScheduler to run two cron jobs (AM and PM)
    that fetch 14 FRED series and upsert the most recent observations
    into ``fred_timeseries``.
    """

    def __init__(self, app_settings: Settings | None = None) -> None:
        self.settings = app_settings or settings
        self.scheduler: AsyncIOScheduler | None = None
        self._running = False
        self._log = logger.bind(component="InterestRateScheduler")

    async def start(self) -> None:
        """Start the scheduler with AM and PM interest rate fetch jobs."""
        if not self.settings.INTEREST_RATE_SCHEDULE_ENABLED:
            self._log.info("interest_rate_scheduler_disabled")
            return

        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            self._log.warning(
                "apscheduler_not_installed",
                hint="pip install apscheduler>=3.10",
            )
            return

        tz = self.settings.EXTRACTION_SCHEDULE_TIMEZONE
        self.scheduler = AsyncIOScheduler(timezone=tz)

        # AM job
        am_cron = _parse_cron_parts(self.settings.INTEREST_RATE_SCHEDULE_CRON_AM)
        self.scheduler.add_job(
            self.run_interest_rate_fetch,
            trigger=CronTrigger(**am_cron, timezone=tz),
            id="interest_rate_am",
            name="Interest rate AM fetch",
            replace_existing=True,
        )

        # PM job
        pm_cron = _parse_cron_parts(self.settings.INTEREST_RATE_SCHEDULE_CRON_PM)
        self.scheduler.add_job(
            self.run_interest_rate_fetch,
            trigger=CronTrigger(**pm_cron, timezone=tz),
            id="interest_rate_pm",
            name="Interest rate PM fetch",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True
        self._log.info(
            "interest_rate_scheduler_started",
            am_cron=self.settings.INTEREST_RATE_SCHEDULE_CRON_AM,
            pm_cron=self.settings.INTEREST_RATE_SCHEDULE_CRON_PM,
            timezone=tz,
        )

    async def stop(self) -> None:
        """Gracefully shutdown the scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            self._log.info("interest_rate_scheduler_stopped")

    async def run_interest_rate_fetch(self) -> dict[str, Any]:
        """Fetch 14 FRED series and upsert into fred_timeseries.

        Fetches the last 5 observations per series with 0.6s delay
        between API calls to respect FRED rate limits.
        """
        self._log.info("interest_rate_fetch_started")
        fred_api_key = self.settings.FRED_API_KEY
        if not fred_api_key:
            self._log.warning("fred_api_key_not_set")
            return {"status": "error", "message": "FRED_API_KEY not configured"}

        try:
            engine = _get_engine()
        except RuntimeError as exc:
            self._log.error("db_not_configured", error=str(exc))
            return {"status": "error", "message": str(exc)}

        total_upserted = 0
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for series_id in INTEREST_RATE_SERIES:
                try:
                    response = await client.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            "series_id": series_id,
                            "api_key": fred_api_key,
                            "file_type": "json",
                            "sort_order": "desc",
                            "limit": OBSERVATIONS_PER_SERIES,
                        },
                    )
                    response.raise_for_status()
                    observations = response.json().get("observations", [])

                    # Upsert into fred_timeseries
                    records = []
                    for obs in observations:
                        val = obs.get("value", ".")
                        if val != ".":
                            records.append(
                                {
                                    "series_id": series_id,
                                    "date": obs["date"],
                                    "value": float(val),
                                }
                            )

                    if records:
                        with engine.begin() as conn:
                            for rec in records:
                                conn.execute(
                                    text("""
                                        INSERT INTO fred_timeseries
                                            (series_id, date, value)
                                        VALUES
                                            (:series_id, :date::date, :value)
                                        ON CONFLICT (series_id, date)
                                        DO UPDATE SET
                                            value = EXCLUDED.value,
                                            imported_at = NOW()
                                    """),
                                    rec,
                                )
                        total_upserted += len(records)

                except Exception as exc:
                    msg = f"{series_id}: {exc}"
                    self._log.warning(
                        "series_fetch_error", series=series_id, error=str(exc)
                    )
                    errors.append(msg)

                # Rate limiting between FRED API calls
                await asyncio.sleep(REQUEST_DELAY)

        status = "success" if not errors else "partial"
        self._log.info(
            "interest_rate_fetch_completed",
            status=status,
            records_upserted=total_upserted,
            errors=len(errors),
        )
        return {
            "status": status,
            "records_upserted": total_upserted,
            "series_count": len(INTEREST_RATE_SERIES),
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_scheduler_instance: InterestRateScheduler | None = None


def get_interest_rate_scheduler() -> InterestRateScheduler:
    """Return (or create) the module-level InterestRateScheduler singleton."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = InterestRateScheduler()
    return _scheduler_instance
