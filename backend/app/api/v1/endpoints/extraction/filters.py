"""
File filter endpoints.

Endpoints for managing and testing file filter configuration.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter

from app.extraction.file_filter import get_file_filter
from app.schemas.extraction import (
    FileFilterConfig,
    FileFilterResponse,
)

router = APIRouter()


@router.get("/filters", response_model=FileFilterResponse)
async def get_filter_configuration():
    """
    Get current file filter configuration.

    Returns the active filter settings used to determine which files
    are processed during SharePoint discovery and extraction:

    - file_pattern: Regex pattern for matching UW model filenames
    - exclude_patterns: List of substrings that cause files to be skipped
    - valid_extensions: List of allowed file extensions
    - cutoff_date: Files older than this date are skipped
    - max_file_size_mb: Files larger than this are skipped

    These settings are loaded from environment variables or use defaults.
    Changes require updating environment variables and restarting the server.
    """
    file_filter = get_file_filter()
    config = file_filter.get_config()

    return FileFilterResponse(
        config=FileFilterConfig(
            file_pattern=config["file_pattern"],
            exclude_patterns=config["exclude_patterns"],
            valid_extensions=config["valid_extensions"],
            cutoff_date=config["cutoff_date"],
            max_file_size_mb=config["max_file_size_mb"],
        ),
        source="environment",
    )


@router.post("/filters/test")
async def test_file_filter(filename: str, size_mb: float = 1.0, days_old: int = 0):
    """
    Test if a file would be processed by the current filter configuration.

    Args:
        filename: The filename to test (e.g., "Property UW Model vCurrent.xlsb")
        size_mb: File size in MB (default 1.0)
        days_old: How many days old the file is (default 0 = today)

    Returns:
        Whether the file would be processed and the reason if skipped.
    """
    file_filter = get_file_filter()

    # Calculate modification date
    modified_date = datetime.now() - timedelta(days=days_old)
    size_bytes = int(size_mb * 1024 * 1024)

    result = file_filter.should_process(
        filename=filename,
        size_bytes=size_bytes,
        modified_date=modified_date,
    )

    return {
        "filename": filename,
        "size_mb": size_mb,
        "days_old": days_old,
        "would_process": result.should_process,
        "skip_reason": result.reason_message,
    }
