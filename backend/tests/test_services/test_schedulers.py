"""Tests for scheduler services: InterestRateScheduler, MarketDataScheduler, ExtractionScheduler.

Covers lifecycle (start/stop), job registration, error handling,
and disabled/missing-dependency paths. All APScheduler internals are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helper: _parse_cron_parts (shared by interest_rate and data_extraction)
# ---------------------------------------------------------------------------


class TestParseCronParts:
    """Tests for _parse_cron_parts in both scheduler modules."""

    def test_valid_5_field_expression(self) -> None:
        from app.services.interest_rate_scheduler import _parse_cron_parts

        result = _parse_cron_parts("0 8 * * *")
        assert result == {
            "minute": "0",
            "hour": "8",
            "day": "*",
            "month": "*",
            "day_of_week": "*",
        }

    def test_invalid_expression_raises(self) -> None:
        from app.services.interest_rate_scheduler import _parse_cron_parts

        with pytest.raises(ValueError, match="expected 5 fields"):
            _parse_cron_parts("0 8 *")

    def test_six_fields_raises(self) -> None:
        from app.services.data_extraction.scheduler import _parse_cron_parts

        with pytest.raises(ValueError, match="expected 5 fields"):
            _parse_cron_parts("0 8 * * * *")

    def test_whitespace_trimmed(self) -> None:
        from app.services.interest_rate_scheduler import _parse_cron_parts

        result = _parse_cron_parts("  30 14 * * 1  ")
        assert result == {
            "minute": "30",
            "hour": "14",
            "day": "*",
            "month": "*",
            "day_of_week": "1",
        }


# ---------------------------------------------------------------------------
# InterestRateScheduler
# ---------------------------------------------------------------------------


class TestInterestRateScheduler:
    """Tests for InterestRateScheduler lifecycle and job registration."""

    def _make_settings(self, **overrides) -> MagicMock:
        s = MagicMock()
        s.INTEREST_RATE_SCHEDULE_ENABLED = True
        s.EXTRACTION_SCHEDULE_TIMEZONE = "America/Phoenix"
        s.INTEREST_RATE_SCHEDULE_CRON_AM = "0 8 * * *"
        s.INTEREST_RATE_SCHEDULE_CRON_PM = "0 15 * * *"
        s.FRED_API_KEY = "test_key"
        s.MARKET_ANALYSIS_DB_URL = "sqlite://"
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    @pytest.mark.asyncio
    async def test_start_disabled_does_nothing(self) -> None:
        from app.services.interest_rate_scheduler import InterestRateScheduler

        sched = InterestRateScheduler(
            app_settings=self._make_settings(INTEREST_RATE_SCHEDULE_ENABLED=False)
        )
        await sched.start()
        assert sched.scheduler is None
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_start_creates_scheduler_and_two_jobs(self) -> None:
        from app.services.interest_rate_scheduler import InterestRateScheduler

        mock_scheduler_instance = MagicMock()
        mock_scheduler_cls = MagicMock(return_value=mock_scheduler_instance)
        mock_cron_cls = MagicMock()

        mock_async_mod = MagicMock()
        mock_async_mod.AsyncIOScheduler = mock_scheduler_cls
        mock_cron_mod = MagicMock()
        mock_cron_mod.CronTrigger = mock_cron_cls

        with patch.dict("sys.modules", {
            "apscheduler": MagicMock(),
            "apscheduler.schedulers": MagicMock(),
            "apscheduler.schedulers.asyncio": mock_async_mod,
            "apscheduler.triggers": MagicMock(),
            "apscheduler.triggers.cron": mock_cron_mod,
        }):
            sched = InterestRateScheduler(app_settings=self._make_settings())
            await sched.start()

        assert sched._running is True
        assert sched.scheduler is mock_scheduler_instance
        mock_scheduler_instance.start.assert_called_once()

        # Two jobs: AM and PM
        assert mock_scheduler_instance.add_job.call_count == 2
        job_ids = [
            call.kwargs["id"]
            for call in mock_scheduler_instance.add_job.call_args_list
        ]
        assert "interest_rate_am" in job_ids
        assert "interest_rate_pm" in job_ids

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self) -> None:
        from app.services.interest_rate_scheduler import InterestRateScheduler

        mock_scheduler_instance = MagicMock()
        mock_async_mod = MagicMock()
        mock_async_mod.AsyncIOScheduler = MagicMock(return_value=mock_scheduler_instance)
        mock_cron_mod = MagicMock()

        with patch.dict("sys.modules", {
            "apscheduler": MagicMock(),
            "apscheduler.schedulers": MagicMock(),
            "apscheduler.schedulers.asyncio": mock_async_mod,
            "apscheduler.triggers": MagicMock(),
            "apscheduler.triggers.cron": mock_cron_mod,
        }):
            sched = InterestRateScheduler(app_settings=self._make_settings())
            await sched.start()
            await sched.stop()

        mock_scheduler_instance.shutdown.assert_called_once_with(wait=False)
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_noop(self) -> None:
        from app.services.interest_rate_scheduler import InterestRateScheduler

        sched = InterestRateScheduler(app_settings=self._make_settings())
        # Never started — stop should not raise
        await sched.stop()
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_start_without_apscheduler_installed(self) -> None:
        """If apscheduler is not installed, start() logs a warning and returns."""
        from app.services.interest_rate_scheduler import InterestRateScheduler

        sched = InterestRateScheduler(app_settings=self._make_settings())

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "apscheduler" in name:
                raise ImportError("No module named 'apscheduler'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            await sched.start()

        assert sched.scheduler is None
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_run_fetch_no_api_key(self) -> None:
        """run_interest_rate_fetch returns error when FRED_API_KEY is not set."""
        from app.services.interest_rate_scheduler import InterestRateScheduler

        sched = InterestRateScheduler(
            app_settings=self._make_settings(FRED_API_KEY=None)
        )
        result = await sched.run_interest_rate_fetch()
        assert result["status"] == "error"
        assert "FRED_API_KEY" in result["message"]

    @pytest.mark.asyncio
    async def test_run_fetch_no_db_url(self) -> None:
        """run_interest_rate_fetch returns error when DB is not configured."""
        from app.services.interest_rate_scheduler import InterestRateScheduler

        sched = InterestRateScheduler(app_settings=self._make_settings())

        with patch(
            "app.services.interest_rate_scheduler._get_engine",
            side_effect=RuntimeError("DB not configured"),
        ):
            result = await sched.run_interest_rate_fetch()

        assert result["status"] == "error"
        assert "DB not configured" in result["message"]


# ---------------------------------------------------------------------------
# MarketDataScheduler
# ---------------------------------------------------------------------------


class TestMarketDataScheduler:
    """Tests for MarketDataScheduler lifecycle and job registration."""

    def _make_settings(self, **overrides) -> MagicMock:
        s = MagicMock()
        s.MARKET_DATA_EXTRACTION_ENABLED = True
        s.EXTRACTION_SCHEDULE_TIMEZONE = "America/Phoenix"
        s.MARKET_FRED_SCHEDULE_CRON = "0 10 * * *"
        s.MARKET_COSTAR_SCHEDULE_CRON = "0 10 15 * *"
        s.MARKET_CENSUS_SCHEDULE_CRON = "0 10 15 1 *"
        s.MARKET_ANALYSIS_DB_URL = "sqlite://"
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    @pytest.mark.asyncio
    async def test_start_disabled_does_nothing(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(
            app_settings=self._make_settings(MARKET_DATA_EXTRACTION_ENABLED=False)
        )
        await sched.start()
        assert sched.scheduler is None
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_start_creates_scheduler_and_three_jobs(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        mock_scheduler_instance = MagicMock()
        mock_async_mod = MagicMock()
        mock_async_mod.AsyncIOScheduler = MagicMock(return_value=mock_scheduler_instance)
        mock_cron_mod = MagicMock()

        with patch.dict("sys.modules", {
            "apscheduler": MagicMock(),
            "apscheduler.schedulers": MagicMock(),
            "apscheduler.schedulers.asyncio": mock_async_mod,
            "apscheduler.triggers": MagicMock(),
            "apscheduler.triggers.cron": mock_cron_mod,
        }):
            sched = MarketDataScheduler(app_settings=self._make_settings())
            await sched.start()

        assert sched._running is True
        mock_scheduler_instance.start.assert_called_once()

        # Three jobs: FRED, CoStar, Census
        assert mock_scheduler_instance.add_job.call_count == 3
        job_ids = [
            call.kwargs["id"]
            for call in mock_scheduler_instance.add_job.call_args_list
        ]
        assert "market_fred_daily" in job_ids
        assert "market_costar_monthly" in job_ids
        assert "market_census_annual" in job_ids

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        mock_scheduler_instance = MagicMock()
        mock_async_mod = MagicMock()
        mock_async_mod.AsyncIOScheduler = MagicMock(return_value=mock_scheduler_instance)
        mock_cron_mod = MagicMock()

        with patch.dict("sys.modules", {
            "apscheduler": MagicMock(),
            "apscheduler.schedulers": MagicMock(),
            "apscheduler.schedulers.asyncio": mock_async_mod,
            "apscheduler.triggers": MagicMock(),
            "apscheduler.triggers.cron": mock_cron_mod,
        }):
            sched = MarketDataScheduler(app_settings=self._make_settings())
            await sched.start()
            await sched.stop()

        mock_scheduler_instance.shutdown.assert_called_once_with(wait=False)
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_noop(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(app_settings=self._make_settings())
        await sched.stop()
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_run_costar_returns_reminder(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(app_settings=self._make_settings())
        result = await sched.run_costar_extraction()
        assert result["status"] == "reminder"
        assert "REMINDER" in result["message"]

    @pytest.mark.asyncio
    async def test_run_fred_extraction_error_handling(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(app_settings=self._make_settings())

        with patch(
            "app.services.data_extraction.scheduler._get_engine",
            side_effect=RuntimeError("no db"),
        ):
            result = await sched.run_fred_extraction()

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_run_census_extraction_error_handling(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(app_settings=self._make_settings())

        with patch(
            "app.services.data_extraction.scheduler._get_engine",
            side_effect=RuntimeError("no db"),
        ):
            result = await sched.run_census_extraction()

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_start_without_apscheduler_graceful(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(app_settings=self._make_settings())

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "apscheduler" in name:
                raise ImportError("No module named 'apscheduler'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            await sched.start()

        assert sched.scheduler is None
        assert sched._running is False

    @pytest.mark.asyncio
    async def test_run_fred_extraction_success(self) -> None:
        from app.services.data_extraction.scheduler import MarketDataScheduler

        sched = MarketDataScheduler(app_settings=self._make_settings())
        mock_engine = MagicMock()
        expected = {"status": "success", "records": 100}

        with (
            patch(
                "app.services.data_extraction.scheduler._get_engine",
                return_value=mock_engine,
            ),
            patch(
                "app.services.data_extraction.fred_extractor.run_fred_extraction_async",
                new_callable=AsyncMock,
                return_value=expected,
            ),
        ):
            result = await sched.run_fred_extraction()

        assert result == expected


# ---------------------------------------------------------------------------
# ExtractionScheduler
# ---------------------------------------------------------------------------


class TestExtractionScheduler:
    """Tests for the ExtractionScheduler (proforma extraction scheduling)."""

    @pytest.mark.asyncio
    async def test_initialize_sets_state(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()

        with patch(
            "app.services.extraction.scheduler.AsyncIOScheduler"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            await sched.initialize(
                enabled=False, cron_expression="30 3 * * *", timezone="UTC"
            )

        assert sched._initialized is True
        status = sched.get_status()
        assert status["enabled"] is False
        assert status["cron_expression"] == "30 3 * * *"
        assert status["timezone"] == "UTC"
        mock_instance.start.assert_called_once_with(paused=True)

    @pytest.mark.asyncio
    async def test_initialize_enabled_adds_job_and_resumes(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()

        mock_instance = MagicMock()
        mock_instance.get_job.return_value = None  # No existing job

        with (
            patch(
                "app.services.extraction.scheduler.AsyncIOScheduler",
                return_value=mock_instance,
            ),
            patch("app.services.extraction.scheduler.CronTrigger"),
        ):
            await sched.initialize(enabled=True)

        mock_instance.start.assert_called_once_with(paused=True)
        mock_instance.resume.assert_called_once()
        mock_instance.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_double_initialize_is_noop(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()

        with patch("app.services.extraction.scheduler.AsyncIOScheduler"):
            await sched.initialize(enabled=False)
            # Second call should be a no-op
            await sched.initialize(enabled=False)

        assert sched._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown_stops_scheduler(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        mock_instance = MagicMock()
        mock_instance.running = True

        with patch(
            "app.services.extraction.scheduler.AsyncIOScheduler",
            return_value=mock_instance,
        ):
            await sched.initialize(enabled=False)
            await sched.shutdown()

        mock_instance.shutdown.assert_called_once_with(wait=False)
        assert sched._initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_without_init_is_safe(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        await sched.shutdown()  # Should not raise
        assert sched._initialized is False

    @pytest.mark.asyncio
    async def test_enable_without_init_raises(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        with pytest.raises(RuntimeError, match="not initialized"):
            await sched.enable()

    @pytest.mark.asyncio
    async def test_disable_without_init_raises(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        with pytest.raises(RuntimeError, match="not initialized"):
            await sched.disable()

    @pytest.mark.asyncio
    async def test_enable_adds_job(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        mock_instance = MagicMock()
        mock_instance.get_job.return_value = None

        with (
            patch(
                "app.services.extraction.scheduler.AsyncIOScheduler",
                return_value=mock_instance,
            ),
            patch("app.services.extraction.scheduler.CronTrigger"),
        ):
            await sched.initialize(enabled=False)
            result = await sched.enable()

        assert result["enabled"] is True
        mock_instance.resume.assert_called()
        mock_instance.add_job.assert_called()

    @pytest.mark.asyncio
    async def test_disable_removes_job(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        mock_instance = MagicMock()
        mock_job = MagicMock()
        mock_instance.get_job.return_value = mock_job

        with (
            patch(
                "app.services.extraction.scheduler.AsyncIOScheduler",
                return_value=mock_instance,
            ),
            patch("app.services.extraction.scheduler.CronTrigger"),
        ):
            await sched.initialize(enabled=True)
            result = await sched.disable()

        assert result["enabled"] is False
        mock_instance.pause.assert_called()
        mock_instance.remove_job.assert_called()

    @pytest.mark.asyncio
    async def test_enable_already_enabled_returns_status(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        mock_instance = MagicMock()
        mock_instance.get_job.return_value = None

        with (
            patch(
                "app.services.extraction.scheduler.AsyncIOScheduler",
                return_value=mock_instance,
            ),
            patch("app.services.extraction.scheduler.CronTrigger"),
        ):
            await sched.initialize(enabled=True)
            # Already enabled — should return status without re-adding
            result = await sched.enable()

        assert result["enabled"] is True

    def test_set_extraction_callback(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        callback = AsyncMock()
        sched.set_extraction_callback(callback)
        assert sched._extraction_callback is callback

    def test_is_enabled_and_is_running_properties(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        assert sched.is_enabled is False
        assert sched.is_running is False

    @pytest.mark.asyncio
    async def test_run_scheduled_extraction_skips_if_running(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        sched._state.running = True

        callback = AsyncMock()
        sched.set_extraction_callback(callback)

        await sched._run_scheduled_extraction()
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_scheduled_extraction_no_callback(self) -> None:
        from app.services.extraction.scheduler import ExtractionScheduler

        sched = ExtractionScheduler()
        sched._extraction_callback = None

        # Should not raise, just log error
        await sched._run_scheduled_extraction()
        assert sched._state.running is False

    @pytest.mark.asyncio
    async def test_state_to_dict(self) -> None:
        from app.services.extraction.scheduler import ExtractionSchedulerState

        state = ExtractionSchedulerState(
            enabled=True, cron_expression="0 2 * * *", timezone="UTC"
        )
        d = state.to_dict()
        assert d["enabled"] is True
        assert d["cron_expression"] == "0 2 * * *"
        assert d["timezone"] == "UTC"
        assert d["next_run"] is None
        assert d["last_run"] is None
        assert d["last_run_id"] is None
        assert d["running"] is False


# ---------------------------------------------------------------------------
# Singleton factories
# ---------------------------------------------------------------------------


class TestSingletonFactories:
    """Tests for get_*_scheduler() singleton helpers."""

    def test_interest_rate_singleton(self) -> None:
        from app.services import interest_rate_scheduler as mod

        # Reset singleton
        mod._scheduler_instance = None
        s1 = mod.get_interest_rate_scheduler()
        s2 = mod.get_interest_rate_scheduler()
        assert s1 is s2
        # Cleanup
        mod._scheduler_instance = None

    def test_market_data_singleton(self) -> None:
        from app.services.data_extraction import scheduler as mod

        mod._scheduler_instance = None
        s1 = mod.get_market_data_scheduler()
        s2 = mod.get_market_data_scheduler()
        assert s1 is s2
        mod._scheduler_instance = None

    def test_extraction_singleton(self) -> None:
        from app.services.extraction import scheduler as mod

        mod._extraction_scheduler = None
        s1 = mod.get_extraction_scheduler()
        s2 = mod.get_extraction_scheduler()
        assert s1 is s2
        mod._extraction_scheduler = None
