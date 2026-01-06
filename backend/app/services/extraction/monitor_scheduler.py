"""
File Monitor Scheduler Service

Provides automated scheduling of SharePoint file monitoring checks using APScheduler.
Features:
- Cron-based scheduling for periodic monitoring
- Configurable check intervals
- Integration with file monitor service
- Automatic extraction triggering on changes
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = structlog.get_logger(__name__)


class MonitorSchedulerState:
    """
    Tracks file monitor scheduler state.

    Attributes:
        enabled: Whether monitoring is enabled
        interval_minutes: Check interval in minutes
        auto_extract: Whether to auto-trigger extraction
        last_check: Last check timestamp
        next_check: Next scheduled check time
        is_checking: Whether a check is in progress
        total_checks: Total number of checks performed
        last_changes_count: Number of changes found in last check
    """

    def __init__(
        self,
        enabled: bool = False,
        interval_minutes: int = 30,
        auto_extract: bool = True,
    ):
        self.enabled = enabled
        self.interval_minutes = interval_minutes
        self.auto_extract = auto_extract
        self.last_check: datetime | None = None
        self.next_check: datetime | None = None
        self.is_checking = False
        self.total_checks = 0
        self.last_changes_count = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "enabled": self.enabled,
            "interval_minutes": self.interval_minutes,
            "auto_extract": self.auto_extract,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "next_check": self.next_check.isoformat() if self.next_check else None,
            "is_checking": self.is_checking,
            "total_checks": self.total_checks,
            "last_changes_count": self.last_changes_count,
        }


class FileMonitorScheduler:
    """
    APScheduler-based file monitor scheduler.

    Manages automated file monitoring checks on a configurable schedule.
    Uses AsyncIOScheduler for async compatibility with FastAPI.
    """

    JOB_ID = "file_monitor_check"

    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._state = MonitorSchedulerState()
        self._initialized = False

    async def initialize(
        self,
        enabled: bool | None = None,
        interval_minutes: int | None = None,
        auto_extract: bool | None = None,
        timezone: str = "America/Phoenix",
    ) -> None:
        """
        Initialize the file monitor scheduler.

        Args:
            enabled: Whether to start with monitoring enabled (defaults to settings)
            interval_minutes: Check interval in minutes (defaults to settings)
            auto_extract: Auto-trigger extraction (defaults to settings)
            timezone: Timezone for scheduling
        """
        if self._initialized:
            logger.warning("File monitor scheduler already initialized")
            return

        # Use settings as defaults
        self._state = MonitorSchedulerState(
            enabled=enabled if enabled is not None else settings.FILE_MONITOR_ENABLED,
            interval_minutes=(
                interval_minutes
                if interval_minutes is not None
                else settings.FILE_MONITOR_INTERVAL_MINUTES
            ),
            auto_extract=(
                auto_extract
                if auto_extract is not None
                else settings.AUTO_EXTRACT_ON_CHANGE
            ),
        )

        # Create scheduler
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))

        # Start the scheduler (paused until enabled)
        self._scheduler.start(paused=True)

        self._initialized = True
        logger.info(
            "File monitor scheduler initialized",
            enabled=self._state.enabled,
            interval_minutes=self._state.interval_minutes,
            auto_extract=self._state.auto_extract,
        )

        # If enabled on init, add job and resume
        if self._state.enabled:
            await self._add_monitor_job()
            self._scheduler.resume()
            self._update_next_check()

    async def shutdown(self) -> None:
        """Shutdown the scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("File monitor scheduler shut down")
        self._initialized = False

    async def _run_monitoring_check(self) -> None:
        """
        Execute a scheduled monitoring check.

        This is called by APScheduler when a scheduled check is due.
        """
        if self._state.is_checking:
            logger.warning(
                "Skipping scheduled monitoring check - previous check still in progress"
            )
            return

        logger.info("Starting scheduled file monitoring check")
        self._state.is_checking = True
        self._state.last_check = datetime.utcnow()

        try:
            # Import here to avoid circular imports
            from app.db.session import AsyncSessionLocal
            from app.services.extraction.file_monitor import SharePointFileMonitor

            async with AsyncSessionLocal() as db:
                monitor = SharePointFileMonitor(db)
                result = await monitor.check_for_changes(
                    auto_trigger_extraction=self._state.auto_extract
                )

                self._state.last_changes_count = result.changes_detected
                self._state.total_checks += 1

                logger.info(
                    "Scheduled monitoring check completed",
                    changes_detected=result.changes_detected,
                    files_checked=result.files_checked,
                    duration_seconds=result.check_duration_seconds,
                )

        except Exception as e:
            logger.exception("Scheduled monitoring check failed", error=str(e))
        finally:
            self._state.is_checking = False
            self._update_next_check()

    async def _add_monitor_job(self) -> None:
        """Add the monitoring job to the scheduler."""
        if not self._scheduler:
            return

        # Remove existing job if present
        if self._scheduler.get_job(self.JOB_ID):
            self._scheduler.remove_job(self.JOB_ID)

        # Use interval trigger for periodic checks
        trigger = IntervalTrigger(minutes=self._state.interval_minutes)

        # Add the job
        self._scheduler.add_job(
            self._run_monitoring_check,
            trigger=trigger,
            id=self.JOB_ID,
            name="File Monitor Check",
            replace_existing=True,
            misfire_grace_time=300,  # 5 minute grace period
        )

        logger.info(
            "Monitor job added to scheduler",
            interval_minutes=self._state.interval_minutes,
        )

    def _update_next_check(self) -> None:
        """Update the next_check timestamp from the scheduler."""
        if not self._scheduler:
            self._state.next_check = None
            return

        job = self._scheduler.get_job(self.JOB_ID)
        if job and job.next_run_time:
            self._state.next_check = job.next_run_time
        else:
            self._state.next_check = None

    async def enable(self) -> dict[str, Any]:
        """
        Enable file monitoring.

        Returns:
            Current scheduler state
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        if self._state.enabled:
            logger.info("File monitor already enabled")
            return self.get_status()

        self._state.enabled = True

        # Add job and resume scheduler
        await self._add_monitor_job()
        if self._scheduler:
            self._scheduler.resume()

        self._update_next_check()

        logger.info(
            "File monitor enabled",
            next_check=(
                self._state.next_check.isoformat() if self._state.next_check else None
            ),
        )

        return self.get_status()

    async def disable(self) -> dict[str, Any]:
        """
        Disable file monitoring.

        Returns:
            Current scheduler state
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        if not self._state.enabled:
            logger.info("File monitor already disabled")
            return self.get_status()

        self._state.enabled = False

        # Remove job and pause scheduler
        if self._scheduler:
            if self._scheduler.get_job(self.JOB_ID):
                self._scheduler.remove_job(self.JOB_ID)
            self._scheduler.pause()

        self._state.next_check = None

        logger.info("File monitor disabled")

        return self.get_status()

    async def update_config(
        self,
        enabled: bool | None = None,
        interval_minutes: int | None = None,
        auto_extract: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update scheduler configuration.

        Args:
            enabled: Whether monitoring is enabled
            interval_minutes: Check interval in minutes
            auto_extract: Whether to auto-trigger extraction

        Returns:
            Updated scheduler state
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        # Update state
        if interval_minutes is not None:
            if interval_minutes < 5 or interval_minutes > 1440:
                raise ValueError("interval_minutes must be between 5 and 1440")
            self._state.interval_minutes = interval_minutes

        if auto_extract is not None:
            self._state.auto_extract = auto_extract

        # Handle enabled state change
        if enabled is not None:
            if enabled and not self._state.enabled:
                await self.enable()
            elif not enabled and self._state.enabled:
                await self.disable()
        elif self._state.enabled:
            # Reconfigure with new settings
            await self._add_monitor_job()
            self._update_next_check()

        logger.info(
            "File monitor configuration updated",
            enabled=self._state.enabled,
            interval_minutes=self._state.interval_minutes,
            auto_extract=self._state.auto_extract,
        )

        return self.get_status()

    async def trigger_check(self) -> dict[str, Any]:
        """
        Manually trigger a monitoring check.

        Returns:
            Check result dictionary
        """
        if not self._initialized:
            raise RuntimeError("Scheduler not initialized")

        if self._state.is_checking:
            raise RuntimeError("A check is already in progress")

        logger.info("Manual monitoring check triggered")

        # Run the check directly (not via scheduler)
        await self._run_monitoring_check()

        return {
            "message": "Monitoring check completed",
            "changes_detected": self._state.last_changes_count,
            "check_time": (
                self._state.last_check.isoformat() if self._state.last_check else None
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """
        Get current scheduler status.

        Returns:
            Dictionary with scheduler state
        """
        self._update_next_check()
        return self._state.to_dict()

    @property
    def is_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self._state.enabled

    @property
    def is_checking(self) -> bool:
        """Check if a check is in progress."""
        return self._state.is_checking


# Singleton instance
_monitor_scheduler: FileMonitorScheduler | None = None


def get_monitor_scheduler() -> FileMonitorScheduler:
    """Get or create the file monitor scheduler singleton."""
    global _monitor_scheduler
    if _monitor_scheduler is None:
        _monitor_scheduler = FileMonitorScheduler()
    return _monitor_scheduler
