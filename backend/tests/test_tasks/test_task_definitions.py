"""
Tests for individual task definition functions.

Each task is tested with a mock context dict, verifying it calls
the correct underlying service function.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("arq", reason="arq not installed (requires Redis)")


class TestMarketDataTasks:
    """Tests for market data task wrappers."""

    @pytest.mark.asyncio
    async def test_refresh_fred_data_task(self):
        """FRED task calls scheduler.run_fred_extraction()."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_fred_extraction = AsyncMock(
            return_value={"records_inserted": 150}
        )

        with patch(
            "app.services.data_extraction.scheduler.get_market_data_scheduler",
            return_value=mock_scheduler,
        ):
            from app.tasks.market_data import refresh_fred_data_task

            ctx: dict[str, Any] = {"job_id": "test-fred-001"}
            result = await refresh_fred_data_task(ctx, incremental=True)

            assert result["source"] == "fred"
            assert result["incremental"] is True
            assert result["result"]["records_inserted"] == 150
            mock_scheduler.run_fred_extraction.assert_called_once_with(
                incremental=True
            )

    @pytest.mark.asyncio
    async def test_refresh_fred_data_task_full(self):
        """FRED task passes incremental=False correctly."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_fred_extraction = AsyncMock(
            return_value={"records_inserted": 500}
        )

        with patch(
            "app.services.data_extraction.scheduler.get_market_data_scheduler",
            return_value=mock_scheduler,
        ):
            from app.tasks.market_data import refresh_fred_data_task

            ctx: dict[str, Any] = {"job_id": "test-fred-002"}
            result = await refresh_fred_data_task(ctx, incremental=False)

            assert result["incremental"] is False
            mock_scheduler.run_fred_extraction.assert_called_once_with(
                incremental=False
            )

    @pytest.mark.asyncio
    async def test_refresh_costar_data_task(self):
        """CoStar task calls scheduler.run_costar_extraction()."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_costar_extraction = AsyncMock(
            return_value={"files_processed": 3}
        )

        with patch(
            "app.services.data_extraction.scheduler.get_market_data_scheduler",
            return_value=mock_scheduler,
        ):
            from app.tasks.market_data import refresh_costar_data_task

            ctx: dict[str, Any] = {"job_id": "test-costar-001"}
            result = await refresh_costar_data_task(ctx)

            assert result["source"] == "costar"
            mock_scheduler.run_costar_extraction.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_census_data_task(self):
        """Census task calls scheduler.run_census_extraction()."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_census_extraction = AsyncMock(
            return_value={"years_fetched": 10}
        )

        with patch(
            "app.services.data_extraction.scheduler.get_market_data_scheduler",
            return_value=mock_scheduler,
        ):
            from app.tasks.market_data import refresh_census_data_task

            ctx: dict[str, Any] = {"job_id": "test-census-001"}
            result = await refresh_census_data_task(ctx)

            assert result["source"] == "census"
            mock_scheduler.run_census_extraction.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_all_market_data_task(self):
        """All-sources task calls scheduler.run_all()."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_all = AsyncMock(
            return_value={"fred": "ok", "costar": "ok", "census": "ok"}
        )

        with patch(
            "app.services.data_extraction.scheduler.get_market_data_scheduler",
            return_value=mock_scheduler,
        ):
            from app.tasks.market_data import refresh_all_market_data_task

            ctx: dict[str, Any] = {"job_id": "test-all-001"}
            result = await refresh_all_market_data_task(ctx)

            assert result["source"] == "all"
            mock_scheduler.run_all.assert_called_once()


class TestReportTasks:
    """Tests for report generation task wrappers."""

    @pytest.mark.asyncio
    async def test_generate_report_task_not_found(self):
        """Task handles missing report gracefully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.db.session.AsyncSessionLocal",
            return_value=mock_session,
        ):
            from app.tasks.reports import generate_report_task

            ctx: dict[str, Any] = {"job_id": "test-report-001"}
            result = await generate_report_task(ctx, report_id=999)

            assert result["status"] == "not_found"
            assert result["report_id"] == 999

    @pytest.mark.asyncio
    async def test_generate_report_task_processes_report(self):
        """Task calls ReportWorker._process_one when report exists."""
        mock_report = MagicMock()
        mock_report.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_report

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_worker = MagicMock()
        mock_worker._process_one = AsyncMock()

        with (
            patch(
                "app.db.session.AsyncSessionLocal",
                return_value=mock_session,
            ),
            patch(
                "app.services.report_worker.ReportWorker",
                return_value=mock_worker,
            ),
        ):
            from app.tasks.reports import generate_report_task

            ctx: dict[str, Any] = {"job_id": "test-report-002"}
            result = await generate_report_task(ctx, report_id=1)

            assert result["status"] == "completed"
            assert result["report_id"] == 1
            mock_worker._process_one.assert_called_once_with(
                mock_session, mock_report
            )


class TestExtractionTasks:
    """Tests for proforma extraction task wrappers."""

    @pytest.mark.asyncio
    async def test_run_extraction_task(self):
        """Extraction task calls the existing run_extraction_task function."""
        mock_extract = AsyncMock()

        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task",
            mock_extract,
        ):
            from app.tasks.extraction import run_extraction_task

            ctx: dict[str, Any] = {"job_id": "test-extract-001"}
            result = await run_extraction_task(
                ctx,
                run_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                source="local",
                file_paths=["/tmp/file1.xlsb"],
            )

            assert result["run_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            assert result["source"] == "local"
            assert result["status"] == "completed"
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_extraction_task_no_file_paths(self):
        """Extraction task works with no explicit file paths (auto-discover)."""
        mock_extract = AsyncMock()

        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task",
            mock_extract,
        ):
            from app.tasks.extraction import run_extraction_task

            ctx: dict[str, Any] = {"job_id": "test-extract-002"}
            result = await run_extraction_task(
                ctx,
                run_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                source="sharepoint",
            )

            assert result["source"] == "sharepoint"
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_extraction_task_propagates_error(self):
        """Extraction errors propagate up to ARQ for retry handling."""
        mock_extract = AsyncMock(side_effect=RuntimeError("Extraction failed"))

        with patch(
            "app.api.v1.endpoints.extraction.common.run_extraction_task",
            mock_extract,
        ):
            from app.tasks.extraction import run_extraction_task

            ctx: dict[str, Any] = {"job_id": "test-extract-003"}
            with pytest.raises(RuntimeError, match="Extraction failed"):
                await run_extraction_task(
                    ctx,
                    run_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                )


class TestConfigModule:
    """Tests for the config module."""

    def test_get_redis_settings_parses_url(self):
        """Redis URL is parsed into host/port/database correctly."""
        with patch(
            "app.core.config.settings",
        ) as mock_settings:
            mock_settings.REDIS_URL = "redis://myhost:6380/2"

            from app.tasks.config import get_redis_settings

            rs = get_redis_settings()

            assert rs.host == "myhost"
            assert rs.port == 6380
            assert rs.database == 2

    def test_get_redis_settings_with_password(self):
        """Redis URL with password is parsed correctly."""
        with patch(
            "app.core.config.settings",
        ) as mock_settings:
            mock_settings.REDIS_URL = "redis://:secret@myhost:6379/0"

            from app.tasks.config import get_redis_settings

            rs = get_redis_settings()

            assert rs.host == "myhost"
            assert rs.password == "secret"

    def test_get_redis_settings_defaults_on_empty(self):
        """Default settings when REDIS_URL is empty."""
        with patch(
            "app.core.config.settings",
        ) as mock_settings:
            mock_settings.REDIS_URL = ""

            from app.tasks.config import get_redis_settings

            rs = get_redis_settings()

            # Empty URL falls through to default RedisSettings
            assert rs.host == "localhost"
            assert rs.port == 6379
