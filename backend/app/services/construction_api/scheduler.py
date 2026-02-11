"""
Construction data scheduler.

Manages scheduled monthly API fetches for Census BPS, FRED, BLS,
and municipal permit data (Mesa, Tempe, Gilbert).
Mirrors the ExtractionScheduler pattern with APScheduler AsyncIOScheduler.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger(__name__)


class ConstructionSchedulerState:
    """Tracks construction data scheduler state."""

    def __init__(
        self,
        enabled: bool = False,
        census_cron: str = "0 4 15 * *",
        fred_cron: str = "0 4 15 * *",
        bls_cron: str = "0 5 15 * *",
        municipal_cron: str = "0 6 16 * *",
        timezone: str = "America/Phoenix",
    ):
        self.enabled = enabled
        self.census_cron = census_cron
        self.fred_cron = fred_cron
        self.bls_cron = bls_cron
        self.municipal_cron = municipal_cron
        self.timezone = timezone
        self.last_census_run: datetime | None = None
        self.last_fred_run: datetime | None = None
        self.last_bls_run: datetime | None = None
        self.last_municipal_run: datetime | None = None
        self.running: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "enabled": self.enabled,
            "census_cron": self.census_cron,
            "fred_cron": self.fred_cron,
            "bls_cron": self.bls_cron,
            "municipal_cron": self.municipal_cron,
            "timezone": self.timezone,
            "last_census_run": (
                self.last_census_run.isoformat() if self.last_census_run else None
            ),
            "last_fred_run": (
                self.last_fred_run.isoformat() if self.last_fred_run else None
            ),
            "last_bls_run": (
                self.last_bls_run.isoformat() if self.last_bls_run else None
            ),
            "last_municipal_run": (
                self.last_municipal_run.isoformat() if self.last_municipal_run else None
            ),
            "running": self.running,
        }


class ConstructionDataScheduler:
    """Singleton scheduler for construction pipeline data fetches.

    Manages four cron jobs:
      1. Census BPS — monthly, 15th at 4 AM Phoenix time
      2. FRED permits — monthly, 15th at 4 AM Phoenix time
      3. BLS employment — monthly, 15th at 5 AM Phoenix time
      4. Municipal permits (Mesa, Tempe, Gilbert) — monthly, 16th at 6 AM

    Disabled by default via CONSTRUCTION_API_ENABLED=False.
    """

    _instance: "ConstructionDataScheduler | None" = None
    _initialized: bool = False

    def __new__(cls) -> "ConstructionDataScheduler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._scheduler: AsyncIOScheduler | None = None
        self.state = ConstructionSchedulerState()

    def configure(
        self,
        enabled: bool = False,
        census_cron: str = "0 4 15 * *",
        fred_cron: str = "0 4 15 * *",
        bls_cron: str = "0 5 15 * *",
        municipal_cron: str = "0 6 16 * *",
        timezone: str = "America/Phoenix",
    ) -> None:
        """Configure scheduler state from settings."""
        self.state.enabled = enabled
        self.state.census_cron = census_cron
        self.state.fred_cron = fred_cron
        self.state.bls_cron = bls_cron
        self.state.municipal_cron = municipal_cron
        self.state.timezone = timezone

    async def start(self) -> None:
        """Start the scheduler with configured cron jobs."""
        if not self.state.enabled:
            logger.info("construction_scheduler_disabled")
            return

        if self._scheduler and self._scheduler.running:
            logger.info("construction_scheduler_already_running")
            return

        self._scheduler = AsyncIOScheduler()

        # Census BPS job
        self._scheduler.add_job(
            self._run_census_fetch,
            CronTrigger.from_crontab(
                self.state.census_cron,
                timezone=self.state.timezone,
            ),
            id="construction_census_bps",
            name="Census BPS Permit Fetch",
            replace_existing=True,
            max_instances=1,
        )

        # FRED job
        self._scheduler.add_job(
            self._run_fred_fetch,
            CronTrigger.from_crontab(
                self.state.fred_cron,
                timezone=self.state.timezone,
            ),
            id="construction_fred_permits",
            name="FRED Permit Series Fetch",
            replace_existing=True,
            max_instances=1,
        )

        # BLS job
        self._scheduler.add_job(
            self._run_bls_fetch,
            CronTrigger.from_crontab(
                self.state.bls_cron,
                timezone=self.state.timezone,
            ),
            id="construction_bls_employment",
            name="BLS Employment Fetch",
            replace_existing=True,
            max_instances=1,
        )

        # Municipal permits job (Mesa, Tempe, Gilbert)
        self._scheduler.add_job(
            self._run_municipal_fetch,
            CronTrigger.from_crontab(
                self.state.municipal_cron,
                timezone=self.state.timezone,
            ),
            id="construction_municipal_permits",
            name="Municipal Permit Fetch (Mesa/Tempe/Gilbert)",
            replace_existing=True,
            max_instances=1,
        )

        self._scheduler.start()
        logger.info(
            "construction_scheduler_started",
            census_cron=self.state.census_cron,
            fred_cron=self.state.fred_cron,
            bls_cron=self.state.bls_cron,
            municipal_cron=self.state.municipal_cron,
        )

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("construction_scheduler_stopped")

    async def _run_census_fetch(self) -> None:
        """Execute Census BPS fetch. Called by scheduler."""
        if self.state.running:
            logger.warning("construction_fetch_skipped_already_running")
            return

        self.state.running = True
        try:
            from app.core.config import settings
            from app.services.construction_api.census_bps import (
                fetch_census_bps,
                save_census_bps_records,
            )

            if not settings.CENSUS_API_KEY:
                logger.warning("census_api_key_not_configured")
                return

            result = await fetch_census_bps(settings.CENSUS_API_KEY)
            if result["records"]:
                from app.db.session import SessionLocal

                with SessionLocal() as db:
                    save_census_bps_records(
                        db,
                        result["records"],
                        result.get("api_response_code"),
                        result.get("errors"),
                    )

            self.state.last_census_run = datetime.now(UTC)
            logger.info(
                "census_bps_scheduled_fetch_complete",
                records=len(result["records"]),
            )
        except Exception:
            logger.exception("census_bps_scheduled_fetch_error")
        finally:
            self.state.running = False

    async def _run_fred_fetch(self) -> None:
        """Execute FRED permits fetch. Called by scheduler."""
        if self.state.running:
            logger.warning("construction_fetch_skipped_already_running")
            return

        self.state.running = True
        try:
            from app.core.config import settings
            from app.services.construction_api.fred_permits import (
                fetch_fred_permits,
                save_fred_records,
            )

            if not settings.FRED_API_KEY:
                logger.warning("fred_api_key_not_configured")
                return

            result = await fetch_fred_permits(settings.FRED_API_KEY)
            if result["records"]:
                from app.db.session import SessionLocal

                with SessionLocal() as db:
                    save_fred_records(
                        db,
                        result["records"],
                        result.get("api_response_code"),
                        result.get("errors"),
                    )

            self.state.last_fred_run = datetime.now(UTC)
            logger.info(
                "fred_scheduled_fetch_complete",
                records=len(result["records"]),
            )
        except Exception:
            logger.exception("fred_scheduled_fetch_error")
        finally:
            self.state.running = False

    async def _run_bls_fetch(self) -> None:
        """Execute BLS employment fetch. Called by scheduler."""
        if self.state.running:
            logger.warning("construction_fetch_skipped_already_running")
            return

        self.state.running = True
        try:
            from app.core.config import settings
            from app.services.construction_api.bls_employment import (
                fetch_bls_employment,
                save_bls_records,
            )

            result = await fetch_bls_employment(api_key=settings.BLS_API_KEY)
            if result["records"]:
                from app.db.session import SessionLocal

                with SessionLocal() as db:
                    save_bls_records(
                        db,
                        result["records"],
                        result.get("api_response_code"),
                        result.get("errors"),
                    )

            self.state.last_bls_run = datetime.now(UTC)
            logger.info(
                "bls_scheduled_fetch_complete",
                records=len(result["records"]),
            )
        except Exception:
            logger.exception("bls_scheduled_fetch_error")
        finally:
            self.state.running = False

    async def _run_municipal_fetch(self) -> None:
        """Execute municipal permit fetches (Mesa, Tempe, Gilbert). Called by scheduler."""
        if self.state.running:
            logger.warning("construction_fetch_skipped_already_running")
            return

        self.state.running = True
        total_records = 0
        try:
            from app.db.session import SessionLocal

            # Mesa SODA
            try:
                from app.services.construction_api.mesa_soda import (
                    fetch_mesa_permits,
                    save_mesa_records,
                )

                result = await fetch_mesa_permits()
                if result["records"]:
                    with SessionLocal() as db:
                        save_mesa_records(db, result["records"])
                total_records += len(result["records"])
                logger.info(
                    "mesa_scheduled_fetch_complete", records=len(result["records"])
                )
            except Exception:
                logger.exception("mesa_scheduled_fetch_error")

            # Tempe BLDS
            try:
                from app.services.construction_api.tempe_blds import (
                    fetch_tempe_permits,
                    save_tempe_records,
                )

                result = await fetch_tempe_permits()
                if result["records"]:
                    with SessionLocal() as db:
                        save_tempe_records(db, result["records"])
                total_records += len(result["records"])
                logger.info(
                    "tempe_scheduled_fetch_complete", records=len(result["records"])
                )
            except Exception:
                logger.exception("tempe_scheduled_fetch_error")

            # Gilbert ArcGIS
            try:
                from app.services.construction_api.gilbert_arcgis import (
                    fetch_gilbert_permits,
                    save_gilbert_records,
                )

                result = await fetch_gilbert_permits()
                if result["records"]:
                    with SessionLocal() as db:
                        save_gilbert_records(db, result["records"])
                total_records += len(result["records"])
                logger.info(
                    "gilbert_scheduled_fetch_complete", records=len(result["records"])
                )
            except Exception:
                logger.exception("gilbert_scheduled_fetch_error")

            self.state.last_municipal_run = datetime.now(UTC)
            logger.info(
                "municipal_scheduled_fetch_complete",
                total_records=total_records,
            )
        except Exception:
            logger.exception("municipal_scheduled_fetch_error")
        finally:
            self.state.running = False

    def get_status(self) -> dict[str, Any]:
        """Get current scheduler status."""
        return {
            **self.state.to_dict(),
            "scheduler_running": (
                self._scheduler.running if self._scheduler else False
            ),
        }
