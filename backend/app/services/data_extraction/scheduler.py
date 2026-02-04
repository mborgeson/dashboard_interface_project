"""
Extraction Scheduler — orchestrates automated data extraction.

Schedule (Phoenix timezone):
  - FRED: Daily at 2 AM (incremental)
  - CoStar: Monthly 15th at 3 AM (full re-parse from latest Excel)
  - Census: Annually Dec 15th at 4 AM

Also provides manual trigger functions for the admin API.
"""

from loguru import logger
from sqlalchemy import create_engine, text

from app.core.config import settings


def _get_engine():
    """Create sync engine for market_analysis DB."""
    db_url = settings.MARKET_ANALYSIS_DB_URL
    if not db_url:
        raise RuntimeError("MARKET_ANALYSIS_DB_URL not configured")
    return create_engine(db_url)


def trigger_fred_extraction(incremental: bool = True) -> dict:
    """Manually trigger FRED data extraction."""
    from app.services.data_extraction.fred_extractor import run_fred_extraction

    engine = _get_engine()
    return run_fred_extraction(engine=engine, incremental=incremental)


def trigger_costar_extraction() -> dict:
    """Manually trigger CoStar data extraction."""
    from app.services.data_extraction.costar_parser import run_costar_extraction

    engine = _get_engine()
    return run_costar_extraction(engine=engine)


def trigger_census_extraction() -> dict:
    """Manually trigger Census data extraction."""
    from app.services.data_extraction.census_extractor import run_census_extraction

    engine = _get_engine()
    return run_census_extraction(engine=engine)


def get_data_freshness() -> dict:
    """Get freshness status for all data sources."""
    try:
        engine = _get_engine()
    except RuntimeError:
        return {"status": "not_configured", "sources": {}}

    sources = {}
    with engine.connect() as conn:
        # CoStar freshness
        result = conn.execute(text("""
            SELECT MAX(date)::text, COUNT(*), MAX(imported_at)::text
            FROM costar_timeseries WHERE is_forecast = FALSE
        """))
        row = result.fetchone()
        sources["costar"] = {
            "latest_date": row[0],
            "record_count": row[1],
            "last_import": row[2],
        }

        # FRED freshness
        result = conn.execute(text("""
            SELECT MAX(date)::text, COUNT(*), MAX(imported_at)::text
            FROM fred_timeseries
        """))
        row = result.fetchone()
        sources["fred"] = {
            "latest_date": row[0],
            "record_count": row[1],
            "last_import": row[2],
        }

        # Census freshness
        result = conn.execute(text("""
            SELECT MAX(year), COUNT(*), MAX(imported_at)::text
            FROM census_timeseries
        """))
        row = result.fetchone()
        sources["census"] = {
            "latest_year": row[0],
            "record_count": row[1],
            "last_import": row[2],
        }

        # Recent extraction logs
        result = conn.execute(text("""
            SELECT source, status, started_at::text, finished_at::text,
                   records_upserted, error_message
            FROM extraction_log
            ORDER BY started_at DESC
            LIMIT 10
        """))
        logs = [
            {
                "source": r[0],
                "status": r[1],
                "started_at": r[2],
                "finished_at": r[3],
                "records_upserted": r[4],
                "error_message": r[5],
            }
            for r in result.fetchall()
        ]

    return {"status": "ok", "sources": sources, "recent_logs": logs}


def setup_scheduler(app):
    """
    Set up APScheduler jobs on FastAPI startup.

    Call this from app.main on startup if MARKET_DATA_EXTRACTION_ENABLED is True.
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

    scheduler = AsyncIOScheduler(timezone=settings.EXTRACTION_SCHEDULE_TIMEZONE)

    # Parse cron expressions from settings
    def _make_trigger(cron_expr: str) -> CronTrigger:
        parts = cron_expr.split()
        return CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=settings.EXTRACTION_SCHEDULE_TIMEZONE,
        )

    # FRED: daily incremental
    scheduler.add_job(
        trigger_fred_extraction,
        trigger=_make_trigger(settings.MARKET_FRED_SCHEDULE_CRON),
        kwargs={"incremental": True},
        id="fred_daily",
        replace_existing=True,
    )

    # CoStar: monthly full re-parse
    scheduler.add_job(
        trigger_costar_extraction,
        trigger=_make_trigger(settings.MARKET_COSTAR_SCHEDULE_CRON),
        id="costar_monthly",
        replace_existing=True,
    )

    # Census: annual
    scheduler.add_job(
        trigger_census_extraction,
        trigger=_make_trigger(settings.MARKET_CENSUS_SCHEDULE_CRON),
        id="census_annual",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Market data extraction scheduler started")

    # Store scheduler on app state for graceful shutdown
    app.state.market_scheduler = scheduler
