"""
Market Data Extraction Scheduler — orchestrates automated data extraction.

Schedule (Phoenix timezone, configurable via settings):
  - FRED: Daily at 2 AM (incremental)       MARKET_FRED_SCHEDULE_CRON
  - CoStar: Monthly 15th at 3 AM (full)     MARKET_COSTAR_SCHEDULE_CRON
  - Census: Annually Dec 15th at 4 AM       MARKET_CENSUS_SCHEDULE_CRON

Also provides manual trigger functions for the admin API.

Integration with app lifecycle (main.py lifespan):
    scheduler = MarketDataScheduler(settings)
    await scheduler.start()
    yield
    await scheduler.stop()
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import Settings, settings

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler


def _get_engine(db_url: str | None = None) -> Engine:
    """Create a sync SQLAlchemy engine for the market_analysis DB."""
    url = db_url or settings.MARKET_ANALYSIS_DB_URL
    if not url:
        raise RuntimeError("MARKET_ANALYSIS_DB_URL not configured")
    return create_engine(url)


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


class MarketDataScheduler:
    """Schedules and orchestrates market data extraction jobs.

    Uses APScheduler's AsyncIOScheduler to run extraction jobs on cron
    schedules defined in application settings. Each job wraps the
    corresponding extractor in error handling and logs results to the
    ``extraction_log`` table.

    Attributes:
        scheduler: The underlying APScheduler instance (created on start).
        settings: Application settings with cron schedules and feature flags.
    """

    def __init__(self, app_settings: Settings | None = None) -> None:
        self.settings = app_settings or settings
        self.scheduler: AsyncIOScheduler | None = None  # Lazy init — created in start()
        self._running = False
        self._log = logger.bind(component="MarketDataScheduler")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler with configured extraction jobs.

        If ``MARKET_DATA_EXTRACTION_ENABLED`` is False the scheduler
        will not start and all scheduled jobs are skipped.  Manual
        triggers via the admin API still work independently.
        """
        if not self.settings.MARKET_DATA_EXTRACTION_ENABLED:
            self._log.info("market_data_extraction_disabled")
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

        # --- FRED: daily incremental ---
        fred_cron = _parse_cron_parts(self.settings.MARKET_FRED_SCHEDULE_CRON)
        self.scheduler.add_job(
            self.run_fred_extraction,
            trigger=CronTrigger(**fred_cron, timezone=tz),
            id="market_fred_daily",
            name="FRED daily incremental extraction",
            replace_existing=True,
        )

        # --- CoStar: monthly full re-parse ---
        costar_cron = _parse_cron_parts(self.settings.MARKET_COSTAR_SCHEDULE_CRON)
        self.scheduler.add_job(
            self.run_costar_extraction,
            trigger=CronTrigger(**costar_cron, timezone=tz),
            id="market_costar_monthly",
            name="CoStar monthly full extraction",
            replace_existing=True,
        )

        # --- Census: annual ---
        census_cron = _parse_cron_parts(self.settings.MARKET_CENSUS_SCHEDULE_CRON)
        self.scheduler.add_job(
            self.run_census_extraction,
            trigger=CronTrigger(**census_cron, timezone=tz),
            id="market_census_annual",
            name="Census annual extraction",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True
        self._log.info(
            "scheduler_started",
            fred_cron=self.settings.MARKET_FRED_SCHEDULE_CRON,
            costar_cron=self.settings.MARKET_COSTAR_SCHEDULE_CRON,
            census_cron=self.settings.MARKET_CENSUS_SCHEDULE_CRON,
            timezone=tz,
        )

    async def stop(self) -> None:
        """Gracefully shutdown the scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            self._log.info("scheduler_stopped")

    # ------------------------------------------------------------------
    # Individual extraction jobs
    # ------------------------------------------------------------------

    async def run_fred_extraction(self, incremental: bool = True) -> dict[str, Any]:
        """Run FRED extraction job.

        Delegates to the async FRED extractor, refreshes the
        ``fred_latest`` materialized view, and logs the outcome.
        """
        self._log.info("fred_extraction_started", incremental=incremental)
        try:
            from app.services.data_extraction.fred_extractor import (
                run_fred_extraction_async,
            )

            engine = _get_engine()
            result = await run_fred_extraction_async(
                engine=engine, incremental=incremental
            )

            # Materialized view refresh is handled inside run_fred_extraction_async
            self._log.info("fred_extraction_completed", result=result)
            return result
        except Exception as exc:
            self._log.error("fred_extraction_failed", error=str(exc))
            return {"status": "error", "message": str(exc)}

    async def run_costar_extraction(self) -> dict[str, Any]:
        """Log a reminder that CoStar data extraction is due.

        CoStar data requires manual Excel file placement. This scheduled
        job serves as a reminder rather than running automated extraction.
        """
        self._log.info(
            "costar_extraction_reminder",
            message="REMINDER: CoStar data extraction is due. "
            "Place updated Excel files in the CoStar data directory "
            "and trigger extraction manually via the admin API.",
        )
        return {
            "status": "reminder",
            "message": "REMINDER: CoStar data extraction is due. "
            "Place updated Excel files in the CoStar data directory "
            "and trigger extraction manually via the admin API.",
        }

    async def run_census_extraction(self) -> dict[str, Any]:
        """Run Census extraction job.

        Delegates to the sync Census extractor via ``asyncio.to_thread``
        and logs the outcome.
        """
        self._log.info("census_extraction_started")
        try:
            from app.services.data_extraction.census_extractor import (
                run_census_extraction,
            )

            engine = _get_engine()
            # Census extractor is synchronous — run in thread pool
            result = await asyncio.to_thread(run_census_extraction, engine=engine)

            self._log.info("census_extraction_completed", result=result)
            return result
        except Exception as exc:
            self._log.error("census_extraction_failed", error=str(exc))
            return {"status": "error", "message": str(exc)}

    async def run_all(self) -> dict[str, Any]:
        """Run all extractions sequentially (FRED -> CoStar -> Census).

        Returns a combined summary with results from each source.
        """
        self._log.info("all_extractions_started")
        results: dict[str, Any] = {}

        results["fred"] = await self.run_fred_extraction(incremental=True)
        results["costar"] = await self.run_costar_extraction()
        results["census"] = await self.run_census_extraction()

        all_ok = all(r.get("status") == "success" for r in results.values())
        results["overall_status"] = "success" if all_ok else "partial_failure"

        self._log.info("all_extractions_completed", overall=results["overall_status"])
        return results

    # ------------------------------------------------------------------
    # Materialized view refresh
    # ------------------------------------------------------------------

    async def refresh_materialized_views(self) -> dict[str, str]:
        """Manually refresh all materialized views.

        Attempts ``REFRESH MATERIALIZED VIEW CONCURRENTLY`` first, then
        falls back to a non-concurrent refresh if a unique index is
        missing.

        Returns a dict mapping view name to 'refreshed' or an error message.
        """
        views = ["costar_latest", "fred_latest"]
        results: dict[str, str] = {}

        try:
            engine = _get_engine()
        except RuntimeError as exc:
            return {v: str(exc) for v in views}

        for view_name in views:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                    )
                results[view_name] = "refreshed"
                self._log.info("materialized_view_refreshed", view=view_name)
            except Exception as exc:
                self._log.warning(
                    "concurrent_refresh_failed",
                    view=view_name,
                    error=str(exc),
                )
                # Fallback to non-concurrent refresh
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
                    results[view_name] = "refreshed (non-concurrent)"
                except Exception as fallback_exc:
                    results[view_name] = f"error: {fallback_exc}"
                    self._log.error(
                        "materialized_view_refresh_failed",
                        view=view_name,
                        error=str(fallback_exc),
                    )

        return results

    # ------------------------------------------------------------------
    # Status / freshness
    # ------------------------------------------------------------------

    async def get_status(self) -> dict[str, Any]:
        """Return extraction status including data freshness and schedule info.

        Queries the ``extraction_log`` table for the latest run per source,
        and reports record counts and next scheduled run times.
        """
        try:
            engine = _get_engine()
        except RuntimeError:
            return {
                "scheduler_running": self._running,
                "status": "not_configured",
                "message": "MARKET_ANALYSIS_DB_URL not set",
                "sources": {},
            }

        sources: dict[str, Any] = {}

        try:
            with engine.connect() as conn:
                # CoStar freshness
                row = conn.execute(
                    text("""
                        SELECT MAX(date)::text, COUNT(*), MAX(imported_at)::text
                        FROM costar_timeseries WHERE is_forecast = FALSE
                    """)
                ).fetchone()
                sources["costar"] = {
                    "latest_date": row[0] if row else None,
                    "record_count": row[1] if row else 0,
                    "last_import": row[2] if row else None,
                }

                # FRED freshness
                row = conn.execute(
                    text("""
                        SELECT MAX(date)::text, COUNT(*), MAX(imported_at)::text
                        FROM fred_timeseries
                    """)
                ).fetchone()
                sources["fred"] = {
                    "latest_date": row[0] if row else None,
                    "record_count": row[1] if row else 0,
                    "last_import": row[2] if row else None,
                }

                # Census freshness
                row = conn.execute(
                    text("""
                        SELECT MAX(year), COUNT(*), MAX(imported_at)::text
                        FROM census_timeseries
                    """)
                ).fetchone()
                sources["census"] = {
                    "latest_year": row[0] if row else None,
                    "record_count": row[1] if row else 0,
                    "last_import": row[2] if row else None,
                }

                # Recent extraction logs
                log_rows = conn.execute(
                    text("""
                        SELECT source, status, started_at::text, finished_at::text,
                               records_upserted, error_message
                        FROM extraction_log
                        ORDER BY started_at DESC
                        LIMIT 10
                    """)
                ).fetchall()

                recent_logs = [
                    {
                        "source": r[0],
                        "status": r[1],
                        "started_at": r[2],
                        "finished_at": r[3],
                        "records_upserted": r[4],
                        "error_message": r[5],
                    }
                    for r in log_rows
                ]

        except Exception as exc:
            self._log.error("status_query_failed", error=str(exc))
            return {
                "scheduler_running": self._running,
                "status": "error",
                "message": str(exc),
                "sources": {},
            }

        # Next scheduled run times
        next_runs: dict[str, str | None] = {}
        if self.scheduler and self._running:
            for job_id, source in [
                ("market_fred_daily", "fred"),
                ("market_costar_monthly", "costar"),
                ("market_census_annual", "census"),
            ]:
                job = self.scheduler.get_job(job_id)
                if job and job.next_run_time:
                    next_runs[source] = job.next_run_time.isoformat()
                else:
                    next_runs[source] = None
        else:
            next_runs = {"fred": None, "costar": None, "census": None}

        return {
            "scheduler_running": self._running,
            "extraction_enabled": self.settings.MARKET_DATA_EXTRACTION_ENABLED,
            "timezone": self.settings.EXTRACTION_SCHEDULE_TIMEZONE,
            "status": "ok",
            "sources": sources,
            "next_scheduled_runs": next_runs,
            "recent_logs": recent_logs,
        }


# ---------------------------------------------------------------------------
# Module-level singleton & legacy helpers
# ---------------------------------------------------------------------------

_scheduler_instance: MarketDataScheduler | None = None


def get_market_data_scheduler() -> MarketDataScheduler:
    """Return (or create) the module-level MarketDataScheduler singleton."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = MarketDataScheduler()
    return _scheduler_instance


# Legacy synchronous trigger helpers (kept for backward compatibility)


def trigger_fred_extraction(incremental: bool = True) -> dict:
    """Synchronous wrapper — manually trigger FRED data extraction."""
    from app.services.data_extraction.fred_extractor import run_fred_extraction

    engine = _get_engine()
    return run_fred_extraction(engine=engine, incremental=incremental)


def trigger_costar_extraction() -> dict:
    """Synchronous wrapper — manually trigger CoStar data extraction."""
    from app.services.data_extraction.costar_parser import run_costar_extraction_sync

    return run_costar_extraction_sync()


def trigger_census_extraction() -> dict:
    """Synchronous wrapper — manually trigger Census data extraction."""
    from app.services.data_extraction.census_extractor import run_census_extraction

    engine = _get_engine()
    return run_census_extraction(engine=engine)


def get_data_freshness() -> dict:
    """Synchronous wrapper — get freshness status for all data sources."""
    try:
        engine = _get_engine()
    except RuntimeError:
        return {"status": "not_configured", "sources": {}}

    sources = {}
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT MAX(date)::text, COUNT(*), MAX(imported_at)::text
                FROM costar_timeseries WHERE is_forecast = FALSE
            """)
        ).fetchone()
        sources["costar"] = {
            "latest_date": row[0] if row else None,
            "record_count": row[1] if row else 0,
            "last_import": row[2] if row else None,
        }

        row = conn.execute(
            text("""
                SELECT MAX(date)::text, COUNT(*), MAX(imported_at)::text
                FROM fred_timeseries
            """)
        ).fetchone()
        sources["fred"] = {
            "latest_date": row[0] if row else None,
            "record_count": row[1] if row else 0,
            "last_import": row[2] if row else None,
        }

        row = conn.execute(
            text("""
                SELECT MAX(year), COUNT(*), MAX(imported_at)::text
                FROM census_timeseries
            """)
        ).fetchone()
        sources["census"] = {
            "latest_year": row[0] if row else None,
            "record_count": row[1] if row else 0,
            "last_import": row[2] if row else None,
        }

        log_rows = conn.execute(
            text("""
                SELECT source, status, started_at::text, finished_at::text,
                       records_upserted, error_message
                FROM extraction_log
                ORDER BY started_at DESC
                LIMIT 10
            """)
        ).fetchall()
        recent_logs = [
            {
                "source": r[0],
                "status": r[1],
                "started_at": r[2],
                "finished_at": r[3],
                "records_upserted": r[4],
                "error_message": r[5],
            }
            for r in log_rows
        ]

    return {"status": "ok", "sources": sources, "recent_logs": recent_logs}


def setup_scheduler(app):
    """Legacy helper — set up APScheduler jobs on FastAPI app state.

    Prefer using ``MarketDataScheduler`` directly in the lifespan context
    manager instead of this function.
    """
    if not settings.MARKET_DATA_EXTRACTION_ENABLED:
        logger.info("Market data extraction scheduler disabled")
        return

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed — skipping market data scheduler")
        return

    tz = settings.EXTRACTION_SCHEDULE_TIMEZONE
    scheduler = AsyncIOScheduler(timezone=tz)

    def _make_trigger(cron_expr: str) -> CronTrigger:
        parts = _parse_cron_parts(cron_expr)
        return CronTrigger(**parts, timezone=tz)

    scheduler.add_job(
        trigger_fred_extraction,
        trigger=_make_trigger(settings.MARKET_FRED_SCHEDULE_CRON),
        kwargs={"incremental": True},
        id="fred_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        trigger_costar_extraction,
        trigger=_make_trigger(settings.MARKET_COSTAR_SCHEDULE_CRON),
        id="costar_monthly",
        replace_existing=True,
    )
    scheduler.add_job(
        trigger_census_extraction,
        trigger=_make_trigger(settings.MARKET_CENSUS_SCHEDULE_CRON),
        id="census_annual",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Market data extraction scheduler started (legacy)")
    app.state.market_scheduler = scheduler
