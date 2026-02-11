"""Tests for the ConstructionDataScheduler."""

import pytest

from app.services.construction_api.scheduler import (
    ConstructionDataScheduler,
    ConstructionSchedulerState,
)


class TestConstructionSchedulerState:
    def test_default_state(self):
        state = ConstructionSchedulerState()
        assert state.enabled is False
        assert state.running is False
        assert state.last_census_run is None
        assert state.last_fred_run is None
        assert state.last_bls_run is None
        assert state.last_municipal_run is None
        assert state.municipal_cron == "0 6 16 * *"

    def test_to_dict(self):
        state = ConstructionSchedulerState(
            enabled=True,
            census_cron="0 4 15 * *",
            fred_cron="0 4 15 * *",
            bls_cron="0 5 15 * *",
            municipal_cron="0 6 16 * *",
        )
        d = state.to_dict()
        assert d["enabled"] is True
        assert d["census_cron"] == "0 4 15 * *"
        assert d["fred_cron"] == "0 4 15 * *"
        assert d["bls_cron"] == "0 5 15 * *"
        assert d["municipal_cron"] == "0 6 16 * *"
        assert d["running"] is False
        assert d["last_census_run"] is None
        assert d["last_municipal_run"] is None


class TestConstructionDataScheduler:
    def setup_method(self):
        # Reset singleton for each test
        ConstructionDataScheduler._instance = None

    def test_singleton(self):
        s1 = ConstructionDataScheduler()
        s2 = ConstructionDataScheduler()
        assert s1 is s2

    def test_configure(self):
        scheduler = ConstructionDataScheduler()
        scheduler.configure(
            enabled=True,
            census_cron="0 3 20 * *",
            fred_cron="0 3 20 * *",
            bls_cron="0 4 20 * *",
            municipal_cron="0 5 20 * *",
            timezone="US/Eastern",
        )
        assert scheduler.state.enabled is True
        assert scheduler.state.census_cron == "0 3 20 * *"
        assert scheduler.state.municipal_cron == "0 5 20 * *"
        assert scheduler.state.timezone == "US/Eastern"

    @pytest.mark.asyncio
    async def test_start_when_disabled(self):
        scheduler = ConstructionDataScheduler()
        scheduler.configure(enabled=False)
        await scheduler.start()
        # Should not create a scheduler when disabled
        assert scheduler._scheduler is None

    @pytest.mark.asyncio
    async def test_start_when_enabled(self):
        scheduler = ConstructionDataScheduler()
        scheduler.configure(enabled=True)
        await scheduler.start()
        assert scheduler._scheduler is not None
        assert scheduler._scheduler.running is True
        # Cleanup
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop(self):
        scheduler = ConstructionDataScheduler()
        scheduler.configure(enabled=True)
        await scheduler.start()
        assert scheduler._scheduler is not None
        await scheduler.stop()
        # After shutdown(wait=False), the scheduler object still exists
        # but should have been told to stop
        assert scheduler._scheduler is not None

    def test_get_status(self):
        scheduler = ConstructionDataScheduler()
        scheduler.configure(enabled=True)
        status = scheduler.get_status()
        assert status["enabled"] is True
        assert status["scheduler_running"] is False
