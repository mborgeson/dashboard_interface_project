"""
Tests for the fallback mechanism — inline execution when Redis is unavailable.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("arq", reason="arq not installed (requires Redis)")


async def _sample_task(ctx: dict[str, Any], value: int = 10) -> dict[str, Any]:
    """A simple async task for testing."""
    return {"value": value, "doubled": value * 2}


async def _failing_task(ctx: dict[str, Any]) -> dict[str, Any]:
    """A task that always raises."""
    raise ValueError("Task exploded")


class TestEnqueueOrRunInline:
    """Tests for enqueue_or_run_inline()."""

    @pytest.fixture(autouse=True)
    def _reset_pool(self):
        """Reset the global pool before each test."""
        import app.tasks.registry as reg

        reg._pool = None
        yield
        reg._pool = None

    @pytest.mark.asyncio
    async def test_queues_when_redis_available(self):
        """Task is enqueued via ARQ when Redis is reachable."""
        with patch(
            "app.tasks.registry.enqueue_task",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.return_value = "queued-job-id"

            from app.tasks.fallback import enqueue_or_run_inline

            result = await enqueue_or_run_inline(_sample_task, value=42)

            assert result["mode"] == "queued"
            assert result["job_id"] == "queued-job-id"
            mock_enqueue.assert_called_once_with(
                "_sample_task",
                _job_id=None,
                value=42,
            )

    @pytest.mark.asyncio
    async def test_runs_inline_when_redis_unavailable(self):
        """Task runs inline when Redis connection fails."""
        with patch(
            "app.tasks.registry.enqueue_task",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.side_effect = ConnectionError("Redis down")

            from app.tasks.fallback import enqueue_or_run_inline

            result = await enqueue_or_run_inline(_sample_task, value=7)

            assert result["mode"] == "inline"
            assert result["result"] == {"value": 7, "doubled": 14}
            assert result["job_id"].startswith("inline-")

    @pytest.mark.asyncio
    async def test_inline_with_custom_job_id(self):
        """Custom job ID is used in inline fallback mode."""
        with patch(
            "app.tasks.registry.enqueue_task",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.side_effect = ConnectionError("Redis down")

            from app.tasks.fallback import enqueue_or_run_inline

            result = await enqueue_or_run_inline(
                _sample_task, value=5, _job_id="my-custom-id"
            )

            assert result["mode"] == "inline"
            assert result["job_id"] == "my-custom-id"
            assert result["result"]["value"] == 5

    @pytest.mark.asyncio
    async def test_inline_handles_task_failure(self):
        """When the inline task raises, the error is captured gracefully."""
        with patch(
            "app.tasks.registry.enqueue_task",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.side_effect = ConnectionError("Redis down")

            from app.tasks.fallback import enqueue_or_run_inline

            result = await enqueue_or_run_inline(_failing_task)

            assert result["mode"] == "inline"
            assert "error" in result
            assert "Task exploded" in result["error"]

    @pytest.mark.asyncio
    async def test_passes_ctx_with_job_id_to_inline_task(self):
        """Inline execution passes a ctx dict with job_id to the task."""
        received_ctx: dict[str, Any] = {}

        async def _capture_ctx_task(ctx: dict[str, Any], x: int = 0) -> dict[str, Any]:
            received_ctx.update(ctx)
            return {"x": x}

        with patch(
            "app.tasks.registry.enqueue_task",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.side_effect = ConnectionError("Redis down")

            from app.tasks.fallback import enqueue_or_run_inline

            result = await enqueue_or_run_inline(_capture_ctx_task, x=99)

            assert result["mode"] == "inline"
            assert "job_id" in received_ctx
            assert received_ctx["inline"] is True

    @pytest.mark.asyncio
    async def test_queued_mode_with_custom_job_id(self):
        """Custom job ID is forwarded to enqueue_task in queued mode."""
        with patch(
            "app.tasks.registry.enqueue_task",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.return_value = "custom-123"

            from app.tasks.fallback import enqueue_or_run_inline

            result = await enqueue_or_run_inline(
                _sample_task, _job_id="custom-123", value=1
            )

            assert result["mode"] == "queued"
            assert result["job_id"] == "custom-123"
            mock_enqueue.assert_called_once_with(
                "_sample_task",
                _job_id="custom-123",
                value=1,
            )
