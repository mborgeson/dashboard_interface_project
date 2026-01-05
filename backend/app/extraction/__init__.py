# Extraction module for B&R Capital Dashboard UW Model data extraction
"""
This module provides SharePoint to PostgreSQL data extraction pipeline.

Components:
- error_handler: Comprehensive error handling with 9 categories
- cell_mapping: Cell mapping parser and dataclass
- extractor: Excel data extraction for .xlsb and .xlsx files
- sharepoint: SharePoint discovery and file download
- batch: Batch processing with parallel execution
- scheduler: APScheduler integration for nightly extraction
"""

from .cell_mapping import CellMapping, CellMappingParser
from .error_handler import ErrorCategory, ErrorHandler, ExtractionError
from .extractor import ExcelDataExtractor
from .sharepoint import SharePointClient, SharePointFile, get_sharepoint_client

__all__ = [
    "ErrorHandler",
    "ErrorCategory",
    "ExtractionError",
    "CellMapping",
    "CellMappingParser",
    "ExcelDataExtractor",
    "SharePointClient",
    "SharePointFile",
    "get_sharepoint_client",
]
