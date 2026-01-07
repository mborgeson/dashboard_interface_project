"""
Extraction API endpoints for SharePoint UW model data extraction.

This module provides a modular structure for extraction-related endpoints:
- extract.py: Start and cancel extraction operations
- status.py: Status, history, and property data queries
- scheduler.py: Scheduled extraction management
- filters.py: File filter configuration
- monitor.py: File monitoring and change detection

Endpoints:
- POST /extraction/start - Start a new extraction
- GET /extraction/status - Get current extraction status
- GET /extraction/history - List past extractions
- POST /extraction/cancel - Cancel running extraction
- GET /extraction/properties - List extracted properties
- GET /extraction/properties/{name} - Get property data
- GET /extraction/scheduler/status - Get scheduler status
- POST /extraction/scheduler/enable - Enable scheduled extraction
- POST /extraction/scheduler/disable - Disable scheduled extraction
- PUT /extraction/scheduler/config - Update schedule configuration
- GET /extraction/filters - Get file filter configuration
- POST /extraction/filters/test - Test file filter
- GET /extraction/monitor/status - Get monitor status
- GET /extraction/monitor/changes - Get recent file changes
- POST /extraction/monitor/check - Trigger manual check
- GET /extraction/monitor/files - List monitored files
- POST /extraction/monitor/enable - Enable monitoring
- POST /extraction/monitor/disable - Disable monitoring
- PUT /extraction/monitor/config - Update monitor configuration
"""

from fastapi import APIRouter

from app.core.config import settings  # noqa: F401
from app.extraction.file_filter import get_file_filter  # noqa: F401
from app.services.extraction.scheduler import get_extraction_scheduler  # noqa: F401

# Re-export commonly used items for backward compatibility
# These are needed for test mocking and external imports
from .common import run_extraction_task  # noqa: F401
from .extract import router as extract_router
from .filters import router as filters_router
from .monitor import router as monitor_router
from .scheduler import router as scheduler_router
from .status import router as status_router

# Create main router that combines all sub-routers
router = APIRouter()

# Include all endpoint routers
# Note: Routes are included without prefix since the main router
# is already mounted at /extraction in the API router
router.include_router(extract_router)
router.include_router(status_router)
router.include_router(scheduler_router)
router.include_router(filters_router)
router.include_router(monitor_router)

__all__ = [
    "router",
    "run_extraction_task",
    "settings",
    "get_extraction_scheduler",
    "get_file_filter",
]
