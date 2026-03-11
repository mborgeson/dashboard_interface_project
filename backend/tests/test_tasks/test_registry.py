"""
Tests for the task registry — enqueue, status check, and pool management.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

arq = pytest.importorskip("arq", reason="arq not installed (requires Redis)")
from arq.jobs import JobStatus  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_pool():
    """Reset the global pool before each test."""
    import app.tasks.registry as reg

    reg._pool = None
    yield
    reg._pool = None


class TestGetTaskPool:
    """Tests for get_task_pool()."""

    @pytest.mark.asyncio
    async def test_creates_pool_on_first_call(self):
        """Pool is created lazily on first call."""
        mock_pool = AsyncMock()

        with patch(
            "app.tasks.registry.create_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            from app.tasks.registry import get_task_pool

            pool = await get_task_pool()
            assert pool is mock_pool

    @pytest.mark.asyncio
    async def test_reuses_existing_pool(self):
        """Subsequent calls return the same pool."""
        mock_pool = AsyncMock()

        with patch(
            "app.tasks.registry.create_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            from app.tasks.registry import get_task_pool

            pool1 = await get_task_pool()
            pool2 = await get_task_pool()

            assert pool1 is pool2


class TestCloseTaskPool:
    """Tests for close_task_pool()."""

    @pytest.mark.asyncio
    async def test_closes_existing_pool(self):
        """Closing a pool calls aclose and resets to None."""
        import app.tasks.registry as reg

        mock_pool = AsyncMock()
        reg._pool = mock_pool

        from app.tasks.registry import close_task_pool

        await close_task_pool()

        mock_pool.aclose.assert_called_once()
        assert reg._pool is None

    @pytest.mark.asyncio
    async def test_noop_when_no_pool(self):
        """Closing when no pool exists does not raise."""
        from app.tasks.registry import close_task_pool

        await close_task_pool()


class TestEnqueueTask:
    """Tests for enqueue_task()."""

    @pytest.mark.asyncio
    async def test_enqueue_returns_job_id(self):
        """Enqueuing a task returns the job ID."""
        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

        with patch(
            "app.tasks.registry.get_task_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            from app.tasks.registry import enqueue_task

            job_id = await enqueue_task("my_task", "arg1", key="value")

            assert job_id == "test-job-123"
            mock_pool.enqueue_job.assert_called_once()

            call_args = mock_pool.enqueue_job.call_args
            assert call_args[0][0] == "my_task"
            assert call_args[0][1] == "arg1"
            assert call_args[1]["key"] == "value"

    @pytest.mark.asyncio
    async def test_enqueue_with_custom_job_id(self):
        """Custom job ID is passed to ARQ for deduplication."""
        mock_job = MagicMock()
        mock_job.job_id = "custom-id"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

        with patch(
            "app.tasks.registry.get_task_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            from app.tasks.registry import enqueue_task

            job_id = await enqueue_task("my_task", _job_id="custom-id")

            assert job_id == "custom-id"
            call_kwargs = mock_pool.enqueue_job.call_args[1]
            assert call_kwargs["_job_id"] == "custom-id"

    @pytest.mark.asyncio
    async def test_enqueue_handles_duplicate_job(self):
        """When ARQ returns None (duplicate job), returns the provided job ID."""
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=None)

        with patch(
            "app.tasks.registry.get_task_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            from app.tasks.registry import enqueue_task

            job_id = await enqueue_task("my_task", _job_id="dup-id")

            assert job_id == "dup-id"

    @pytest.mark.asyncio
    async def test_enqueue_propagates_redis_error(self):
        """Redis connection errors propagate to the caller."""
        with patch(
            "app.tasks.registry.get_task_pool",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ):
            from app.tasks.registry import enqueue_task

            with pytest.raises(ConnectionError, match="Redis down"):
                await enqueue_task("my_task")


class TestGetTaskStatus:
    """Tests for get_task_status()."""

    @pytest.mark.asyncio
    async def test_returns_status_dict(self):
        """Status includes job_id and status field."""
        mock_info = MagicMock()
        mock_info.start_time = None
        mock_info.finish_time = None
        mock_info.success = None
        mock_info.function = "my_task"
        mock_info.queue_name = "arq:queue"
        mock_info.result = None

        mock_job_instance = AsyncMock()
        # Return an actual JobStatus enum value so isinstance() works
        mock_job_instance.status = AsyncMock(return_value=JobStatus.queued)
        mock_job_instance.info = AsyncMock(return_value=mock_info)

        mock_pool = AsyncMock()

        with (
            patch(
                "app.tasks.registry.get_task_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
            patch(
                "app.tasks.registry.Job",
                return_value=mock_job_instance,
            ),
        ):
            from app.tasks.registry import get_task_status

            status = await get_task_status("job-456")

            assert status["job_id"] == "job-456"
            assert status["status"] == "queued"
            assert status["function"] == "my_task"

    @pytest.mark.asyncio
    async def test_returns_result_for_completed_job(self):
        """Completed jobs include the result in the status response."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)

        mock_info = MagicMock()
        mock_info.start_time = now
        mock_info.finish_time = now
        mock_info.success = True
        mock_info.result = {"records": 42}
        mock_info.function = "my_task"
        mock_info.queue_name = "arq:queue"

        mock_job_instance = AsyncMock()
        mock_job_instance.status = AsyncMock(return_value=JobStatus.complete)
        mock_job_instance.info = AsyncMock(return_value=mock_info)

        mock_pool = AsyncMock()

        with (
            patch(
                "app.tasks.registry.get_task_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
            patch(
                "app.tasks.registry.Job",
                return_value=mock_job_instance,
            ),
        ):
            from app.tasks.registry import get_task_status

            status = await get_task_status("completed-job")

            assert status["status"] == "complete"
            assert status["success"] is True
            assert status["result"] == {"records": 42}
            assert status["start_time"] is not None
            assert status["finish_time"] is not None

    @pytest.mark.asyncio
    async def test_unknown_job_returns_minimal_status(self):
        """Unknown jobs return status with no info fields."""
        mock_job_instance = AsyncMock()
        mock_job_instance.status = AsyncMock(return_value=JobStatus.not_found)
        mock_job_instance.info = AsyncMock(return_value=None)

        mock_pool = AsyncMock()

        with (
            patch(
                "app.tasks.registry.get_task_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
            patch(
                "app.tasks.registry.Job",
                return_value=mock_job_instance,
            ),
        ):
            from app.tasks.registry import get_task_status

            status = await get_task_status("nonexistent")

            assert status["job_id"] == "nonexistent"
            assert status["status"] == "not_found"
            assert "result" not in status
