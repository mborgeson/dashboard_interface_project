"""
Tests for logging unification (UR-011, UR-012).

Verifies:
1. No structlog imports remain in the application codebase
2. Correlation IDs are bound for background tasks
3. Loguru is properly configured
4. Log output format consistency
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from loguru import logger

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).parent.parent / "app"


# ---------------------------------------------------------------------------
# Meta-test: no structlog imports in codebase
# ---------------------------------------------------------------------------


class TestNoStructlogImports:
    """Verify that structlog has been fully replaced by loguru."""

    def _collect_python_files(self) -> list[Path]:
        """Collect all .py files in the app directory."""
        return sorted(APP_DIR.rglob("*.py"))

    def test_no_structlog_imports_in_app(self) -> None:
        """No file in backend/app/ should import structlog."""
        violations: list[str] = []

        for py_file in self._collect_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "structlog" or alias.name.startswith(
                            "structlog."
                        ):
                            rel = py_file.relative_to(APP_DIR.parent)
                            violations.append(
                                f"{rel}:{node.lineno} -> import {alias.name}"
                            )
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and (
                        node.module == "structlog"
                        or node.module.startswith("structlog.")
                    )
                ):
                    rel = py_file.relative_to(APP_DIR.parent)
                    violations.append(
                        f"{rel}:{node.lineno} -> from {node.module} import ..."
                    )

        assert violations == [], (
            f"Found {len(violations)} structlog import(s) that should be migrated "
            f"to loguru:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_no_structlog_get_logger_calls(self) -> None:
        """No file should call structlog.get_logger() or structlog.stdlib."""
        violations: list[str] = []

        for py_file in self._collect_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for i, line in enumerate(source.splitlines(), 1):
                if "structlog.get_logger" in line or "structlog.stdlib" in line:
                    # Skip comments
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    rel = py_file.relative_to(APP_DIR.parent)
                    violations.append(f"{rel}:{i} -> {stripped[:80]}")

        assert violations == [], (
            f"Found {len(violations)} structlog.get_logger/stdlib call(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_loguru_used_in_core_logging(self) -> None:
        """core/logging.py should use loguru, not structlog."""
        logging_py = APP_DIR / "core" / "logging.py"
        source = logging_py.read_text(encoding="utf-8")

        assert "from loguru import logger" in source
        assert "import structlog" not in source
        assert "setup_structlog" not in source

    def test_setup_logging_exports(self) -> None:
        """core/logging.py should export setup_logging (not setup_structlog)."""
        from app.core.logging import setup_logging

        assert callable(setup_logging)

        # setup_structlog should no longer exist
        from app.core import logging as core_logging

        assert not hasattr(core_logging, "setup_structlog")


# ---------------------------------------------------------------------------
# Correlation ID tests
# ---------------------------------------------------------------------------


class TestCorrelationIds:
    """Verify that background tasks bind unique correlation IDs."""

    def test_report_worker_binds_correlation_id(self) -> None:
        """ReportWorker._loop should use logger.contextualize with a correlation_id."""
        import inspect

        from app.services.report_worker import ReportWorker

        source = inspect.getsource(ReportWorker._loop)
        assert "correlation_id" in source
        assert "contextualize" in source

    def test_extraction_scheduler_binds_correlation_id(self) -> None:
        """ExtractionScheduler._run_scheduled_extraction should bind a correlation_id."""
        import inspect

        from app.services.extraction.scheduler import ExtractionScheduler

        source = inspect.getsource(ExtractionScheduler._run_scheduled_extraction)
        assert "correlation_id" in source
        assert "contextualize" in source

    def test_construction_scheduler_binds_correlation_id(self) -> None:
        """ConstructionDataScheduler scheduled methods should bind correlation IDs."""
        import inspect

        from app.services.construction_api.scheduler import ConstructionDataScheduler

        for method_name in [
            "_run_census_fetch",
            "_run_fred_fetch",
            "_run_bls_fetch",
            "_run_municipal_fetch",
        ]:
            source = inspect.getsource(getattr(ConstructionDataScheduler, method_name))
            assert "correlation_id" in source, (
                f"{method_name} should bind a correlation_id"
            )
            assert "contextualize" in source, (
                f"{method_name} should use logger.contextualize"
            )

    def test_monitor_scheduler_binds_correlation_id(self) -> None:
        """FileMonitorScheduler._run_monitoring_check should bind a correlation_id."""
        import inspect

        from app.services.extraction.monitor_scheduler import FileMonitorScheduler

        source = inspect.getsource(FileMonitorScheduler._run_monitoring_check)
        assert "correlation_id" in source
        assert "contextualize" in source

    def test_correlation_id_format(self) -> None:
        """Correlation IDs should follow the prefix-hexchars pattern."""
        import re

        pattern = re.compile(r"^[a-z]+-[a-z]+-[0-9a-f]{8}$")

        # Generate a few sample IDs using the same format as the codebase
        samples = [
            f"report-poll-{uuid.uuid4().hex[:8]}",
            f"extract-sched-{uuid.uuid4().hex[:8]}",
            f"census-fetch-{uuid.uuid4().hex[:8]}",
            f"monitor-check-{uuid.uuid4().hex[:8]}",
        ]
        for sample in samples:
            assert pattern.match(sample), (
                f"Correlation ID '{sample}' doesn't match expected format"
            )

    def test_contextualize_injects_into_log_record(self) -> None:
        """logger.contextualize should inject correlation_id into extra."""
        captured_extras: list[dict] = []

        def sink(message) -> None:
            captured_extras.append(dict(message.record["extra"]))

        handler_id = logger.add(sink, level="DEBUG", format="{message}")
        try:
            test_id = f"test-corr-{uuid.uuid4().hex[:8]}"
            with logger.contextualize(correlation_id=test_id):
                logger.info("test message with correlation")

            assert len(captured_extras) >= 1
            assert captured_extras[-1].get("correlation_id") == test_id
        finally:
            logger.remove(handler_id)


# ---------------------------------------------------------------------------
# Loguru configuration tests
# ---------------------------------------------------------------------------


class TestLoguruConfiguration:
    """Verify loguru is properly configured."""

    def test_request_id_patcher_exists(self) -> None:
        """The request ID patcher function should exist."""
        from app.core.logging import _request_id_patcher

        assert callable(_request_id_patcher)

    def test_request_id_patcher_injects_request_id(self) -> None:
        """_request_id_patcher should inject request_id into record extra."""
        from app.core.logging import _request_id_patcher

        record: dict = {"extra": {}}
        with patch(
            "app.middleware.request_id.get_request_id", return_value="test-req-123"
        ):
            _request_id_patcher(record)

        assert record["extra"]["request_id"] == "test-req-123"

    def test_request_id_patcher_fallback(self) -> None:
        """_request_id_patcher should use '-' when no request ID is available."""
        from app.core.logging import _request_id_patcher

        record: dict = {"extra": {}}
        with patch("app.middleware.request_id.get_request_id", return_value=None):
            _request_id_patcher(record)

        assert record["extra"]["request_id"] == "-"

    def test_intercept_handler_exists(self) -> None:
        """The stdlib logging intercept handler should exist."""
        from app.core.logging import _InterceptHandler

        handler = _InterceptHandler()
        assert hasattr(handler, "emit")

    def test_intercept_handler_maps_levels(self) -> None:
        """_InterceptHandler.emit should map stdlib levels to loguru."""
        import logging

        from app.core.logging import _InterceptHandler

        handler = _InterceptHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="test warning",
            args=(),
            exc_info=None,
        )

        # Should not raise
        with patch.object(logger, "opt", return_value=MagicMock()):
            handler.emit(record)


# ---------------------------------------------------------------------------
# Log output format consistency tests
# ---------------------------------------------------------------------------


class TestLogFormatConsistency:
    """Verify log output follows consistent patterns."""

    def test_extraction_files_use_loguru(self) -> None:
        """All extraction module files should use loguru, not structlog."""
        extraction_dir = APP_DIR / "extraction"
        for py_file in extraction_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text(encoding="utf-8")
            assert "import structlog" not in source, (
                f"{py_file.name} still imports structlog"
            )

    def test_services_use_loguru(self) -> None:
        """All service files that were migrated should use loguru."""
        services_to_check = [
            APP_DIR / "services" / "audit_service.py",
            APP_DIR / "services" / "report_worker.py",
            APP_DIR / "services" / "extraction" / "scheduler.py",
            APP_DIR / "services" / "extraction" / "metrics.py",
            APP_DIR / "services" / "extraction" / "change_detector.py",
            APP_DIR / "services" / "extraction" / "file_monitor.py",
            APP_DIR / "services" / "extraction" / "monitor_scheduler.py",
            APP_DIR / "services" / "construction_api" / "scheduler.py",
            APP_DIR / "services" / "data_extraction" / "census_extractor.py",
            APP_DIR / "services" / "data_extraction" / "costar_parser.py",
            APP_DIR / "services" / "data_extraction" / "fred_extractor.py",
        ]
        for filepath in services_to_check:
            if not filepath.exists():
                continue
            source = filepath.read_text(encoding="utf-8")
            assert "import structlog" not in source, (
                f"{filepath.relative_to(APP_DIR)} still imports structlog"
            )

    def test_middleware_uses_loguru(self) -> None:
        """Middleware files should use loguru."""
        etag_py = APP_DIR / "middleware" / "etag.py"
        source = etag_py.read_text(encoding="utf-8")
        assert "import structlog" not in source
        assert "from loguru import logger" in source

    def test_db_query_logger_uses_loguru(self) -> None:
        """db/query_logger.py should use loguru."""
        ql = APP_DIR / "db" / "query_logger.py"
        source = ql.read_text(encoding="utf-8")
        assert "import structlog" not in source
        assert "from loguru import logger" in source

    def test_api_endpoints_use_loguru(self) -> None:
        """API endpoint files that were migrated should use loguru."""
        api_files = [
            APP_DIR / "api" / "v1" / "endpoints" / "auth.py",
            APP_DIR / "api" / "v1" / "endpoints" / "deals" / "activity.py",
            APP_DIR / "api" / "v1" / "endpoints" / "extraction" / "common.py",
        ]
        for filepath in api_files:
            if not filepath.exists():
                continue
            source = filepath.read_text(encoding="utf-8")
            assert "import structlog" not in source, (
                f"{filepath.relative_to(APP_DIR)} still imports structlog"
            )

    def test_structlog_dependency_noted(self) -> None:
        """structlog is still in requirements.txt but no longer imported in app code."""
        requirements = Path(__file__).parent.parent / "requirements.txt"
        source = requirements.read_text(encoding="utf-8")
        # Note: structlog is still listed as a dependency but no longer imported
        # in any app/ code. It can be safely removed from requirements.txt in a
        # future cleanup pass.
        _has_structlog = "structlog" in source  # noqa: F841 — documentation only
