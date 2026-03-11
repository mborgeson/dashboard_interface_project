"""
Tests for the report generation background worker.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_template import (
    QueuedReport,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
)
from app.services.report_worker import ReportWorker, _format_file_size

# ============================================================================
# Helpers
# ============================================================================


async def _create_template(db: AsyncSession, name: str = "Test Template") -> ReportTemplate:
    """Create a test report template."""
    template = ReportTemplate(
        name=name,
        description="Test template for worker tests",
        category="custom",
        sections=["summary"],
        export_formats=["pdf"],
        is_default=False,
        created_by="test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def _create_queued_report(
    db: AsyncSession,
    template_id: int,
    *,
    name: str = "Test Report",
    fmt: str = ReportFormat.PDF,
    status: str = ReportStatus.PENDING,
) -> QueuedReport:
    """Create a test queued report."""
    report = QueuedReport(
        name=name,
        template_id=template_id,
        format=fmt,
        requested_by="test_user",
        requested_at=datetime.now(UTC),
        status=status,
        progress=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


# ============================================================================
# Unit Tests
# ============================================================================


class TestFormatFileSize:
    """Tests for the _format_file_size helper."""

    def test_bytes(self):
        assert _format_file_size(500) == "500 B"

    def test_kilobytes(self):
        assert _format_file_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert _format_file_size(5 * 1024 * 1024) == "5.0 MB"

    def test_zero(self):
        assert _format_file_size(0) == "0 B"


class TestReportWorkerLifecycle:
    """Tests for worker start/stop."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        worker = ReportWorker()
        assert not worker._running

        with patch.object(worker, "_loop", new_callable=AsyncMock):
            await worker.start()
            assert worker._running
            assert worker._task is not None

            await worker.stop()
            assert not worker._running
            assert worker._task is None

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self):
        worker = ReportWorker()

        with patch.object(worker, "_loop", new_callable=AsyncMock):
            await worker.start()
            await worker.start()  # Should log warning but not crash
            assert worker._running

            await worker.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_safe(self):
        worker = ReportWorker()
        await worker.stop()  # Should be a no-op


class TestReportWorkerProcessing:
    """Tests for report processing logic."""

    @pytest.mark.asyncio
    async def test_process_pending_report_pdf(self, db_session: AsyncSession):
        """Test that a pending PDF report gets processed to completed."""
        from io import BytesIO

        template = await _create_template(db_session)
        report = await _create_queued_report(db_session, template.id, fmt=ReportFormat.PDF)

        worker = ReportWorker()

        # Mock the content generation to return a simple buffer
        mock_buffer = BytesIO(b"fake pdf content")

        with patch.object(
            worker, "_generate_content", new_callable=AsyncMock, return_value=mock_buffer
        ), patch("app.services.report_worker.AsyncSessionLocal") as mock_session_cls:
            # Make AsyncSessionLocal return our test session
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_ctx

            await worker._process_pending()

        # Refresh and check status
        await db_session.refresh(report)
        assert report.status == ReportStatus.COMPLETED
        assert report.progress == 100
        assert report.completed_at is not None
        assert report.download_url is not None
        assert report.file_size is not None
        assert report.error is None

    @pytest.mark.asyncio
    async def test_process_pending_report_excel(self, db_session: AsyncSession):
        """Test that a pending Excel report gets processed to completed."""
        from io import BytesIO

        template = await _create_template(db_session)
        report = await _create_queued_report(
            db_session, template.id, fmt=ReportFormat.EXCEL
        )

        worker = ReportWorker()

        mock_buffer = BytesIO(b"fake excel content")

        with patch.object(
            worker, "_generate_content", new_callable=AsyncMock, return_value=mock_buffer
        ), patch("app.services.report_worker.AsyncSessionLocal") as mock_session_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_ctx

            await worker._process_pending()

        await db_session.refresh(report)
        assert report.status == ReportStatus.COMPLETED
        assert report.download_url.endswith(".xlsx")

    @pytest.mark.asyncio
    async def test_process_report_failure_marks_failed(self, db_session: AsyncSession):
        """Test that a generation error marks the report as failed."""
        template = await _create_template(db_session)
        report = await _create_queued_report(db_session, template.id)

        worker = ReportWorker()

        with patch.object(
            worker,
            "_generate_content",
            new_callable=AsyncMock,
            side_effect=RuntimeError("PDF lib crashed"),
        ), patch("app.services.report_worker.AsyncSessionLocal") as mock_session_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_ctx

            await worker._process_pending()

        await db_session.refresh(report)
        assert report.status == ReportStatus.FAILED
        assert "PDF lib crashed" in report.error

    @pytest.mark.asyncio
    async def test_skips_non_pending_reports(self, db_session: AsyncSession):
        """Test that already-completed or generating reports are not reprocessed."""
        template = await _create_template(db_session)

        # Create a completed report
        completed = await _create_queued_report(
            db_session, template.id, name="Completed", status=ReportStatus.COMPLETED
        )
        # Create a generating report
        generating = await _create_queued_report(
            db_session, template.id, name="Generating", status=ReportStatus.GENERATING
        )

        worker = ReportWorker()

        with patch.object(
            worker, "_process_one", new_callable=AsyncMock
        ) as mock_process, patch(
            "app.services.report_worker.AsyncSessionLocal"
        ) as mock_session_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_ctx

            await worker._process_pending()

        # _process_one should not have been called
        mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_processes_multiple_pending_reports(self, db_session: AsyncSession):
        """Test that multiple pending reports are all processed."""
        template = await _create_template(db_session)

        r1 = await _create_queued_report(db_session, template.id, name="Report 1")
        r2 = await _create_queued_report(db_session, template.id, name="Report 2")

        worker = ReportWorker()

        from io import BytesIO
        mock_buffer = BytesIO(b"content")

        call_count = 0

        async def _mock_generate(**kwargs):
            nonlocal call_count
            call_count += 1
            return BytesIO(b"content")

        with patch.object(
            worker, "_generate_content", side_effect=_mock_generate
        ), patch("app.services.report_worker.AsyncSessionLocal") as mock_session_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_ctx

            await worker._process_pending()

        assert call_count == 2

        await db_session.refresh(r1)
        await db_session.refresh(r2)
        assert r1.status == ReportStatus.COMPLETED
        assert r2.status == ReportStatus.COMPLETED
