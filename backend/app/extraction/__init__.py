# Extraction module for B&R Capital Dashboard UW Model data extraction
"""
This module provides SharePoint to PostgreSQL data extraction pipeline.

Components:
- error_handler: Comprehensive error handling with 9 categories
- cell_mapping: Cell mapping parser and dataclass
- extractor: Excel data extraction for .xlsb and .xlsx files
- sharepoint: SharePoint discovery and file download
- file_filter: Configurable file filtering for discovery and extraction
- batch: Batch processing with parallel execution
- scheduler: APScheduler integration for nightly extraction
"""

from .cell_mapping import CellMapping, CellMappingParser
from .error_handler import ErrorCategory, ErrorHandler, ExtractionError
from .extractor import ExcelDataExtractor
from .file_filter import FileFilter, FilterResult, SkipReason, get_file_filter
from .sharepoint import (
    DiscoveryResult,
    SharePointClient,
    SharePointFile,
    SkippedFile,
    get_sharepoint_client,
)

__all__ = [
    # Error handling
    "ErrorHandler",
    "ErrorCategory",
    "ExtractionError",
    # Cell mapping
    "CellMapping",
    "CellMappingParser",
    # Extraction
    "ExcelDataExtractor",
    # File filtering
    "FileFilter",
    "FilterResult",
    "SkipReason",
    "get_file_filter",
    # SharePoint
    "SharePointClient",
    "SharePointFile",
    "SkippedFile",
    "DiscoveryResult",
    "get_sharepoint_client",
]
