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
from .error_handler import (
    ErrorCategory,
    ErrorHandler,
    ExtractionError,
    NullValue,
    is_null_value,
)
from .extractor import ExcelDataExtractor
from .file_filter import (
    CandidateFileFilter,
    FileFilter,
    FilterResult,
    SkipReason,
    get_candidate_file_filter,
    get_file_filter,
)
from .fingerprint import FileFingerprint, SheetFingerprint, fingerprint_file
from .group_pipeline import GroupExtractionPipeline
from .grouping import FileGroup, GroupingResult, compute_structural_overlap
from .reconciliation_checks import (
    ReconciliationResult,
    check_noi_reconciliation,
    run_reconciliation_checks,
)
from .reference_mapper import (
    GroupReferenceMapping,
    MappingMatch,
    PropertyMatch,
    generate_tier1b_report,
    load_field_synonyms,
    validate_domain_ranges,
)
from .sharepoint import (
    DiscoveryResult,
    SharePointClient,
    SharePointFile,
    SkippedFile,
    compute_content_hash,
    compute_content_hash_bytes,
    get_sharepoint_client,
    is_file_locked,
)

__all__ = [
    # Error handling
    "ErrorHandler",
    "ErrorCategory",
    "ExtractionError",
    "NullValue",
    "is_null_value",
    # Cell mapping
    "CellMapping",
    "CellMappingParser",
    # Extraction
    "ExcelDataExtractor",
    # File filtering
    "FileFilter",
    "CandidateFileFilter",
    "FilterResult",
    "SkipReason",
    "get_file_filter",
    "get_candidate_file_filter",
    # Fingerprinting
    "FileFingerprint",
    "SheetFingerprint",
    "fingerprint_file",
    # Grouping
    "FileGroup",
    "GroupingResult",
    "compute_structural_overlap",
    # Reference mapping
    "GroupReferenceMapping",
    "MappingMatch",
    "PropertyMatch",
    "generate_tier1b_report",
    "load_field_synonyms",
    "validate_domain_ranges",
    # Pipeline
    "GroupExtractionPipeline",
    # Reconciliation
    "ReconciliationResult",
    "check_noi_reconciliation",
    "run_reconciliation_checks",
    # SharePoint
    "SharePointClient",
    "SharePointFile",
    "SkippedFile",
    "DiscoveryResult",
    "get_sharepoint_client",
    "is_file_locked",
    "compute_content_hash",
    "compute_content_hash_bytes",
]
