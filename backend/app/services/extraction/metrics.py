"""
Structured extraction metrics for monitoring and observability.

Emits structured log events via structlog that can be consumed by
log aggregation systems (ELK, Datadog, CloudWatch, etc.) for:
- Per-run throughput and duration
- Per-file extraction statistics
- Error category breakdowns
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger().bind(component="extraction_metrics")


@dataclass
class FileMetrics:
    """Metrics collected for a single file extraction."""

    file_path: str
    deal_name: str
    status: str = "pending"  # pending, completed, failed, skipped
    values_count: int = 0
    error_count: int = 0
    error_categories: dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class RunMetrics:
    """Aggregated metrics for an extraction run."""

    files_total: int = 0
    files_completed: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    total_values: int = 0
    total_errors: int = 0
    error_categories: dict[str, int] = field(default_factory=dict)
    per_file: dict[str, FileMetrics] = field(default_factory=dict)
    _start_time: float = field(default_factory=time.monotonic)

    def record_file(self, fm: FileMetrics) -> None:
        """Record metrics for a single file."""
        self.per_file[fm.file_path] = fm
        if fm.status == "completed":
            self.files_completed += 1
            self.total_values += fm.values_count
        elif fm.status == "failed":
            self.files_failed += 1
        elif fm.status == "skipped":
            self.files_skipped += 1
        self.total_errors += fm.error_count
        for cat, count in fm.error_categories.items():
            self.error_categories[cat] = self.error_categories.get(cat, 0) + count

    @property
    def duration_seconds(self) -> float:
        return time.monotonic() - self._start_time

    @property
    def throughput_files_per_minute(self) -> float:
        elapsed = self.duration_seconds
        if elapsed > 0:
            return (self.files_completed + self.files_failed) / elapsed * 60
        return 0.0

    def emit_run_metrics(self, run_id: str) -> None:
        """Emit structured run-level metrics log."""
        logger.info(
            "extraction_run_metrics",
            run_id=run_id,
            duration_seconds=round(self.duration_seconds, 2),
            files_total=self.files_total,
            files_completed=self.files_completed,
            files_failed=self.files_failed,
            files_skipped=self.files_skipped,
            total_values=self.total_values,
            total_errors=self.total_errors,
            throughput_fpm=round(self.throughput_files_per_minute, 1),
            error_categories=self.error_categories or None,
        )

    def to_metadata(self) -> dict:
        """Convert to a JSON-serializable dict for storage on ExtractionRun.file_metadata."""
        per_file_summary = {}
        for path, fm in self.per_file.items():
            per_file_summary[path] = {
                "status": fm.status,
                "values_count": fm.values_count,
                "error_count": fm.error_count,
                "duration_ms": round(fm.duration_ms, 1),
            }
            if fm.error_categories:
                per_file_summary[path]["error_categories"] = fm.error_categories

        return {
            "duration_seconds": round(self.duration_seconds, 2),
            "files_total": self.files_total,
            "files_completed": self.files_completed,
            "files_failed": self.files_failed,
            "files_skipped": self.files_skipped,
            "total_values": self.total_values,
            "total_errors": self.total_errors,
            "throughput_fpm": round(self.throughput_files_per_minute, 1),
            "error_categories": self.error_categories or None,
            "per_file": per_file_summary,
        }
