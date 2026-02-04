"""
B&R Capital Dashboard - File Filter Module

Provides centralized file filtering logic for SharePoint discovery and extraction.
Applies configuration-based rules to determine which files should be processed.

Filter criteria:
- FILE_PATTERN: Regex pattern for matching UW model filenames
- EXCLUDE_PATTERNS: List of substrings to exclude from processing
- CUTOFF_DATE: Skip files older than this date
- MAX_FILE_SIZE_MB: Skip files larger than this size
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.core.config import Settings


class SkipReason(StrEnum):
    """Reasons why a file might be skipped during filtering."""

    PATTERN_MISMATCH = "filename_pattern_mismatch"
    EXCLUDED_PATTERN = "excluded_pattern_match"
    TOO_OLD = "older_than_cutoff_date"
    TOO_LARGE = "exceeds_max_file_size"
    INVALID_EXTENSION = "invalid_file_extension"


@dataclass
class FilterResult:
    """Result of file filter evaluation."""

    should_process: bool
    skip_reason: SkipReason | None = None
    skip_details: str | None = None

    @property
    def reason_message(self) -> str | None:
        """Human-readable skip reason message."""
        if self.should_process:
            return None
        if self.skip_details:
            return f"{self.skip_reason.value}: {self.skip_details}" if self.skip_reason is not None else self.skip_details
        return self.skip_reason.value if self.skip_reason is not None else None


class FileFilter:
    """
    Centralized file filtering for extraction pipeline.

    Applies configuration-based rules to determine whether files
    should be processed during SharePoint discovery and extraction.
    """

    # Supported file extensions for UW models
    SUPPORTED_EXTENSIONS = {".xlsb", ".xlsx", ".xlsm"}

    def __init__(self, settings: "Settings"):
        """
        Initialize file filter with application settings.

        Args:
            settings: Application settings containing filter configuration
        """
        self.logger = structlog.get_logger().bind(component="FileFilter")

        # Compile file pattern regex
        self.file_pattern = self._compile_pattern(settings.FILE_PATTERN)

        # Parse exclude patterns from comma-separated string
        self.exclude_patterns = self._parse_exclude_patterns(settings.EXCLUDE_PATTERNS)

        # Parse file extensions from comma-separated string
        self.valid_extensions = self._parse_extensions(settings.FILE_EXTENSIONS)

        # Parse cutoff date
        self.cutoff_date = self._parse_cutoff_date(settings.CUTOFF_DATE)

        # Max file size in bytes
        self.max_size_bytes = getattr(settings, "MAX_FILE_SIZE_MB", 100) * 1024 * 1024

        self.logger.info(
            "file_filter_initialized",
            pattern=settings.FILE_PATTERN,
            exclude_patterns=self.exclude_patterns,
            valid_extensions=list(self.valid_extensions),
            cutoff_date=self.cutoff_date.isoformat() if self.cutoff_date else None,
            max_size_mb=getattr(settings, "MAX_FILE_SIZE_MB", 100),
        )

    def _compile_pattern(self, pattern: str) -> re.Pattern | None:
        """Compile file pattern regex, handling both simple and regex patterns."""
        if not pattern:
            return None

        try:
            # Check if pattern looks like a regex (contains regex metacharacters)
            regex_chars = r".*+?^$[](){}|\\"
            if any(c in pattern for c in regex_chars):
                return re.compile(pattern, re.IGNORECASE)
            else:
                # Treat as simple substring match - escape and wrap
                escaped = re.escape(pattern)
                return re.compile(f".*{escaped}.*", re.IGNORECASE)
        except re.error as e:
            self.logger.warning(
                "invalid_pattern_using_literal",
                pattern=pattern,
                error=str(e),
            )
            # Fall back to literal match
            escaped = re.escape(pattern)
            return re.compile(f".*{escaped}.*", re.IGNORECASE)

    def _parse_exclude_patterns(self, patterns_str: str) -> list[str]:
        """Parse comma-separated exclude patterns into list."""
        if not patterns_str:
            return []
        return [p.strip().lower() for p in patterns_str.split(",") if p.strip()]

    def _parse_extensions(self, extensions_str: str) -> set[str]:
        """Parse comma-separated extensions into set."""
        if not extensions_str:
            return self.SUPPORTED_EXTENSIONS

        extensions = set()
        for ext in extensions_str.split(","):
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            if ext in self.SUPPORTED_EXTENSIONS:
                extensions.add(ext)

        return extensions if extensions else self.SUPPORTED_EXTENSIONS

    def _parse_cutoff_date(self, date_str: str) -> datetime | None:
        """Parse cutoff date string into datetime."""
        if not date_str:
            return None

        try:
            # Support multiple date formats
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            self.logger.warning("invalid_cutoff_date", date_str=date_str)
            return None

        except Exception as e:
            self.logger.warning(
                "cutoff_date_parse_error", date_str=date_str, error=str(e)
            )
            return None

    def should_process(
        self,
        filename: str,
        size_bytes: int = 0,
        modified_date: datetime | None = None,
    ) -> FilterResult:
        """
        Determine if a file should be processed based on filter criteria.

        Args:
            filename: Name of the file (not full path)
            size_bytes: File size in bytes
            modified_date: Last modified date of the file

        Returns:
            FilterResult indicating whether to process and skip reason if not
        """
        filename_lower = filename.lower()

        # Check file extension
        ext = self._get_extension(filename)
        if ext not in self.valid_extensions:
            self.logger.debug(
                "file_skipped",
                filename=filename,
                reason="invalid_extension",
                extension=ext,
            )
            return FilterResult(
                should_process=False,
                skip_reason=SkipReason.INVALID_EXTENSION,
                skip_details=f"extension '{ext}' not in {list(self.valid_extensions)}",
            )

        # Check exclude patterns
        for exclude_pattern in self.exclude_patterns:
            if exclude_pattern in filename_lower:
                self.logger.debug(
                    "file_skipped",
                    filename=filename,
                    reason="excluded_pattern",
                    pattern=exclude_pattern,
                )
                return FilterResult(
                    should_process=False,
                    skip_reason=SkipReason.EXCLUDED_PATTERN,
                    skip_details=f"matches exclude pattern '{exclude_pattern}'",
                )

        # Check filename pattern
        if self.file_pattern and not self.file_pattern.match(filename):
            self.logger.debug(
                "file_skipped",
                filename=filename,
                reason="pattern_mismatch",
            )
            return FilterResult(
                should_process=False,
                skip_reason=SkipReason.PATTERN_MISMATCH,
                skip_details=f"does not match pattern '{self.file_pattern.pattern}'",
            )

        # Check file size
        if size_bytes > 0 and size_bytes > self.max_size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            max_mb = self.max_size_bytes / (1024 * 1024)
            self.logger.debug(
                "file_skipped",
                filename=filename,
                reason="too_large",
                size_mb=round(size_mb, 2),
                max_mb=max_mb,
            )
            return FilterResult(
                should_process=False,
                skip_reason=SkipReason.TOO_LARGE,
                skip_details=f"size {size_mb:.1f}MB exceeds max {max_mb:.0f}MB",
            )

        # Check cutoff date
        if self.cutoff_date and modified_date:
            # Handle timezone-aware vs naive datetime comparison
            cutoff = self.cutoff_date
            mod_date = modified_date

            # Remove timezone info for comparison if needed
            if hasattr(mod_date, "tzinfo") and mod_date.tzinfo is not None:
                mod_date = mod_date.replace(tzinfo=None)

            if mod_date < cutoff:
                self.logger.debug(
                    "file_skipped",
                    filename=filename,
                    reason="too_old",
                    modified=mod_date.isoformat(),
                    cutoff=cutoff.isoformat(),
                )
                details = f"modified {mod_date.date()} before cutoff {cutoff.date()}"
                return FilterResult(
                    should_process=False,
                    skip_reason=SkipReason.TOO_OLD,
                    skip_details=details,
                )

        # File passes all filters
        self.logger.debug("file_accepted", filename=filename)
        return FilterResult(should_process=True)

    def _get_extension(self, filename: str) -> str:
        """Extract lowercase file extension from filename."""
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

    def get_config(self) -> dict:
        """Return current filter configuration as dictionary."""
        return {
            "file_pattern": self.file_pattern.pattern if self.file_pattern else None,
            "exclude_patterns": self.exclude_patterns,
            "valid_extensions": list(self.valid_extensions),
            "cutoff_date": self.cutoff_date.isoformat() if self.cutoff_date else None,
            "max_file_size_mb": self.max_size_bytes / (1024 * 1024),
        }


def get_file_filter() -> FileFilter:
    """Create FileFilter instance using application settings."""
    from app.core.config import settings

    return FileFilter(settings)
