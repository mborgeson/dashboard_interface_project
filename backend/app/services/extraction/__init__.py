"""
Extraction Service Package

Provides services for automated data extraction from SharePoint/Excel files:
- ExtractionScheduler: APScheduler-based scheduling for automated extraction runs
- SharePointFileMonitor: Polling-based monitoring for file changes
- FileMonitorScheduler: Scheduler for automated file monitoring
"""

from .file_monitor import (
    FileChange,
    MonitorCheckResult,
    SharePointFileMonitor,
    get_file_monitor,
)
from .monitor_scheduler import (
    FileMonitorScheduler,
    MonitorSchedulerState,
    get_monitor_scheduler,
)
from .scheduler import (
    ExtractionScheduler,
    ExtractionSchedulerState,
    get_extraction_scheduler,
    run_scheduled_extraction,
)

__all__ = [
    # Extraction Scheduler
    "ExtractionScheduler",
    "ExtractionSchedulerState",
    "get_extraction_scheduler",
    "run_scheduled_extraction",
    # File Monitor
    "SharePointFileMonitor",
    "FileChange",
    "MonitorCheckResult",
    "get_file_monitor",
    # Monitor Scheduler
    "FileMonitorScheduler",
    "MonitorSchedulerState",
    "get_monitor_scheduler",
]
