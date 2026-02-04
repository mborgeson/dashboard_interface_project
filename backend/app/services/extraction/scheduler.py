"""
Extraction Scheduler Service

Provides automated scheduling of extraction runs using APScheduler.
Features:
- Cron-based scheduling (configurable)
- Timezone-aware scheduling
- Prevents overlapping extraction runs
- Persistent scheduler state tracking
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger(__name__)


class ExtractionSchedulerState:
    """
    Tracks extraction scheduler state.

    Attributes:
        enabled: Whether the scheduler is enabled
        cron_expression: Cron expression for scheduling
        timezone: Timezone for scheduling
        next_run: Next scheduled run time
        last_run: Last run timestamp
        last_run_id: UUID of the last extraction run
        running: Whether an extraction is currently in progress
    """

    def __init__(
        self,
        enabled: bool = False,
        cron_expression: str = "0 2 * * *",
        timezone: str = "America/Phoenix",
    ):
        self.enabled = enabled
        self.cron_expression = cron_expression
        self.timezone = timezone
        self.next_run: datetime | None = None
        self.last_run: datetime | None = None
        self.last_run_id: str | None = None
        self.running = False

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "enabled": self.enabled,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_run_id": self.last_run_id,
            "running": self.running,
        }


class ExtractionScheduler:
    """
    APScheduler-based extraction scheduler.

    Manages automated extraction runs on a configurable schedule.
    Uses AsyncIOScheduler for async compatibility with FastAPI.
    """

    JOB_ID = "extraction_scheduled_run"

    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._state = ExtractionSchedulerState()
        self._extraction_callback: Any = None
        self._initialized = False

    async def initialize(
        self,
        enabled: bool = False,
        cron_expression: str = "0 2 * * *",
        timezone: str = "America/Phoenix",
    ) -> None:
        """
        Initialize the extraction scheduler.

        Args:
            enabled: Whether to start with scheduling enabled
            cron_expression: Cron expression for scheduling (default: daily at 2 AM)
            timezone: Timezone for scheduling (default: America/Phoenix)
        """
        if self._initialized:
            logger.warning("Extraction scheduler already initialized")
            return

        self._state = ExtractionSchedulerState(
            enabled=enabled,
            cron_expression=cron_expression,
            timezone=timezone,
        )

        # Create scheduler with timezone
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))

        # Start the scheduler (jobs are paused until enabled)
        self._scheduler.start(paused=True)

        self._initialized = True
        logger.info(
            "Extraction scheduler initialized",
            enabled=enabled,
            cron_expression=cron_expression,
            timezone=timezone,
        )

        # If enabled on init, add the job and resume
        if enabled:
            await self._add_extraction_job()
            self._scheduler.resume()
            self._update_next_run()

    async def shutdown(self) -> None:
        """Shutdown the extraction scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Extraction scheduler shut down")
        self._initialized = False

    def set_extraction_callback(self, callback: Any) -> None:
        """
        Set the callback function for running extractions.

        Args:
            callback: Async function to call for extraction runs
        """
        self._extraction_callback = callback
        logger.debug("Extraction callback registered")

    async def _run_scheduled_extraction(self) -> None:
        """
        Execute a scheduled extraction run.

        This is called by APScheduler when a scheduled run is due.
        Prevents overlapping runs by checking for currently running extractions.
        """
        if self._state.running:
            logger.warning(
                "Skipping scheduled extraction - previous run still in progress"
            )
            return

        if not self._extraction_callback:
            logger.error("No extraction callback registered")
            return

        logger.info("Starting scheduled extraction run")
        self._state.running = True
        self._state.last_run = datetime.now(ZoneInfo(self._state.timezone))

        try:
            # Import here to avoid circular imports
            from app.crud.extraction import ExtractionRunCRUD
            from app.db.session import SessionLocal

            db = SessionLocal()
            try:
                # Check if there's already a running extraction
                running_extraction = ExtractionRunCRUD.get_running(db)
                if running_extraction:
                    logger.warning(
                        "Skipping scheduled extraction - extraction already running",
                        run_id=str(running_extraction.id),
                    )
                    return

                # Run the extraction via callback
                run_id = await self._extraction_callback(
                    db=db,
                    trigger_type="scheduled",
                )

                self._state.last_run_id = str(run_id) if run_id else None
                logger.info(
                    "Scheduled extraction completed",
                    run_id=self._state.last_run_id,
                )

            finally:
                db.close()

        except Exception as e:
            logger.exception("Scheduled extraction failed", error=str(e))
        finally:
            self._state.running = False
            self._update_next_run()

    async def _add_extraction_job(self) -> None:
        """Add the extraction job to the scheduler."""
        if not self._scheduler:
            return

        # Remove existing job if present
        if self._scheduler.get_job(self.JOB_ID):
            self._scheduler.remove_job(self.JOB_ID)

        # Parse cron expression
        trigger = CronTrigger.from_crontab(
            self._state.cron_expression,
            timezone=ZoneInfo(self._state.timezone),
        )

        # Add the job
        self._scheduler.add_job(
            self._run_scheduled_extraction,
            trigger=trigger,
            id=self.JOB_ID,
            name="Scheduled Extraction Run",
            replace_existing=True,
            misfire_grace_time=3600,  # 1 hour grace period
        )

        logger.info(
            "Extraction job added to scheduler",
            cron_expression=self._state.cron_expression,
        )

    def _update_next_run(self) -> None:
        """Update the next_run timestamp from the scheduler."""
        if not self._scheduler:
            self._state.next_run = None
            return

        job = self._scheduler.get_job(self.JOB_ID)
        if job and job.next_run_time:
            self._state.next_run = job.next_run_time
        else:
            self._state.next_run = None

    async def enable(self) -> dict[str, Any]:
        """
        Enable scheduled extractions.

        Returns:
            Current scheduler state
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        if self._state.enabled:
            logger.info("Scheduler already enabled")
            return self.get_status()

        self._state.enabled = True

        # Add job and resume scheduler
        await self._add_extraction_job()
        if self._scheduler:
            self._scheduler.resume()

        self._update_next_run()

        logger.info(
            "Extraction scheduler enabled",
            next_run=self._state.next_run.isoformat() if self._state.next_run else None,
        )

        return self.get_status()

    async def disable(self) -> dict[str, Any]:
        """
        Disable scheduled extractions.

        Returns:
            Current scheduler state
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        if not self._state.enabled:
            logger.info("Scheduler already disabled")
            return self.get_status()

        self._state.enabled = False

        # Remove job and pause scheduler
        if self._scheduler:
            if self._scheduler.get_job(self.JOB_ID):
                self._scheduler.remove_job(self.JOB_ID)
            self._scheduler.pause()

        self._state.next_run = None

        logger.info("Extraction scheduler disabled")

        return self.get_status()

    async def update_config(
        self,
        enabled: bool | None = None,
        cron_expression: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        """
        Update scheduler configuration.

        Args:
            enabled: Whether scheduling is enabled
            cron_expression: New cron expression
            timezone: New timezone

        Returns:
            Updated scheduler state
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        # Update state
        if cron_expression is not None:
            # Validate cron expression by attempting to create trigger
            try:
                CronTrigger.from_crontab(
                    cron_expression,
                    timezone=ZoneInfo(timezone or self._state.timezone),
                )
            except ValueError as e:
                raise ValueError(f"Invalid cron expression: {e}") from e
            self._state.cron_expression = cron_expression

        if timezone is not None:
            # Validate timezone
            try:
                ZoneInfo(timezone)
            except Exception as e:
                raise ValueError(f"Invalid timezone: {e}") from e
            self._state.timezone = timezone

            # Recreate scheduler with new timezone if needed
            if self._scheduler:
                was_enabled = self._state.enabled
                self._scheduler.shutdown(wait=False)
                self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))
                self._scheduler.start(paused=not was_enabled)
                if was_enabled:
                    await self._add_extraction_job()

        # Handle enabled state change
        if enabled is not None:
            if enabled and not self._state.enabled:
                await self.enable()
            elif not enabled and self._state.enabled:
                await self.disable()
        elif self._state.enabled:
            # Reconfigure with new settings
            await self._add_extraction_job()
            self._update_next_run()

        logger.info(
            "Scheduler configuration updated",
            enabled=self._state.enabled,
            cron_expression=self._state.cron_expression,
            timezone=self._state.timezone,
        )

        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        """
        Get current scheduler status.

        Returns:
            Dictionary with scheduler state
        """
        self._update_next_run()
        return self._state.to_dict()

    @property
    def is_enabled(self) -> bool:
        """Check if scheduler is enabled."""
        return self._state.enabled

    @property
    def is_running(self) -> bool:
        """Check if an extraction is currently running."""
        return self._state.running


# Singleton instance
_extraction_scheduler: ExtractionScheduler | None = None


def get_extraction_scheduler() -> ExtractionScheduler:
    """Get or create the extraction scheduler singleton."""
    global _extraction_scheduler
    if _extraction_scheduler is None:
        _extraction_scheduler = ExtractionScheduler()
    return _extraction_scheduler


async def run_scheduled_extraction(
    db: Any, trigger_type: str = "scheduled"
) -> str | None:
    """
    Run an extraction as a scheduled task.

    This is the default extraction callback that creates and executes
    an extraction run via the existing extraction infrastructure.

    Args:
        db: Database session
        trigger_type: Type of trigger (default: "scheduled")

    Returns:
        Run ID if successful, None otherwise
    """
    from pathlib import Path

    from app.crud.extraction import ExtractionRunCRUD

    # Determine files to process (same logic as manual extraction)
    fixtures_dir = (
        Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "uw_models"
    )
    files_discovered = len(list(fixtures_dir.glob("*.xlsb")))

    # Create extraction run with scheduled trigger type
    run = ExtractionRunCRUD.create(
        db,
        trigger_type=trigger_type,
        files_discovered=files_discovered,
    )

    # Import and run the extraction task synchronously
    # (APScheduler handles async execution)
    from app.api.v1.endpoints.extraction import run_extraction_task

    try:
        run_extraction_task(run.id, "sharepoint", None)
        return str(run.id)
    except Exception as e:
        logger.exception("Scheduled extraction task failed", error=str(e))
        ExtractionRunCRUD.fail(db, run.id, {"error": str(e)})
        return str(run.id)
