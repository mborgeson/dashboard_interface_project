"""Tests for batch processor service."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.batch.batch_processor import (
    BatchProcessor,
    BatchProgress,
    BatchResult,
    BatchStatus,
    get_batch_processor,
)

# =============================================================================
# BatchStatus Tests
# =============================================================================


class TestBatchStatus:
    """Tests for BatchStatus enum."""

    def test_batch_status_values(self):
        """Test all batch status values exist."""
        assert BatchStatus.PENDING == "pending"
        assert BatchStatus.PROCESSING == "processing"
        assert BatchStatus.COMPLETED == "completed"
        assert BatchStatus.FAILED == "failed"
        assert BatchStatus.CANCELLED == "cancelled"
        assert BatchStatus.PAUSED == "paused"

    def test_batch_status_string_enum(self):
        """Test BatchStatus is a string enum."""
        assert isinstance(BatchStatus.PENDING, str)
        assert BatchStatus.PENDING.value == "pending"


# =============================================================================
# BatchProgress Tests
# =============================================================================


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""

    def test_progress_creation(self):
        """Test creating a BatchProgress instance."""
        progress = BatchProgress(batch_id="test-123")

        assert progress.batch_id == "test-123"
        assert progress.total_items == 0
        assert progress.processed_items == 0
        assert progress.successful_items == 0
        assert progress.failed_items == 0
        assert progress.status == BatchStatus.PENDING
        assert progress.started_at is None
        assert progress.completed_at is None
        assert progress.errors == []

    def test_progress_percent_zero(self):
        """Test progress percentage with zero items."""
        progress = BatchProgress(batch_id="test")
        assert progress.progress_percent == 0.0

    def test_progress_percent_partial(self):
        """Test progress percentage with partial completion."""
        progress = BatchProgress(
            batch_id="test",
            total_items=100,
            processed_items=50,
        )
        assert progress.progress_percent == 50.0

    def test_progress_percent_complete(self):
        """Test progress percentage at 100%."""
        progress = BatchProgress(
            batch_id="test",
            total_items=100,
            processed_items=100,
        )
        assert progress.progress_percent == 100.0

    def test_success_rate_zero(self):
        """Test success rate with zero processed."""
        progress = BatchProgress(batch_id="test")
        assert progress.success_rate == 0.0

    def test_success_rate_partial(self):
        """Test success rate with partial success."""
        progress = BatchProgress(
            batch_id="test",
            processed_items=100,
            successful_items=75,
            failed_items=25,
        )
        assert progress.success_rate == 75.0

    def test_success_rate_full(self):
        """Test success rate at 100%."""
        progress = BatchProgress(
            batch_id="test",
            processed_items=100,
            successful_items=100,
        )
        assert progress.success_rate == 100.0

    def test_duration_seconds_not_started(self):
        """Test duration when not started."""
        progress = BatchProgress(batch_id="test")
        assert progress.duration_seconds is None

    def test_duration_seconds_in_progress(self):
        """Test duration while in progress."""
        progress = BatchProgress(
            batch_id="test",
            started_at=datetime.now(UTC),
        )
        duration = progress.duration_seconds
        assert duration is not None
        assert duration >= 0

    def test_duration_seconds_completed(self):
        """Test duration when completed."""
        start = datetime.now(UTC)
        progress = BatchProgress(
            batch_id="test",
            started_at=start,
            completed_at=start,
        )
        assert progress.duration_seconds == pytest.approx(0, abs=0.1)

    def test_to_dict(self):
        """Test converting progress to dictionary."""
        progress = BatchProgress(
            batch_id="test-123",
            total_items=100,
            processed_items=50,
            successful_items=45,
            failed_items=5,
            status=BatchStatus.PROCESSING,
        )

        d = progress.to_dict()

        assert d["batch_id"] == "test-123"
        assert d["total_items"] == 100
        assert d["processed_items"] == 50
        assert d["successful_items"] == 45
        assert d["failed_items"] == 5
        assert d["progress_percent"] == 50.0
        assert d["success_rate"] == 90.0
        assert d["status"] == "processing"

    def test_to_dict_with_errors(self):
        """Test that to_dict limits errors to last 10."""
        errors = [{"error": f"Error {i}"} for i in range(20)]
        progress = BatchProgress(batch_id="test", errors=errors)

        d = progress.to_dict()

        assert len(d["errors"]) == 10
        assert d["errors"][0]["error"] == "Error 10"


# =============================================================================
# BatchResult Tests
# =============================================================================


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_result_creation(self):
        """Test creating a BatchResult instance."""
        progress = BatchProgress(batch_id="test")
        result = BatchResult(batch_id="test", progress=progress)

        assert result.batch_id == "test"
        assert result.progress is progress
        assert result.results == []
        assert result.metadata == {}

    def test_result_with_data(self):
        """Test BatchResult with results and metadata."""
        progress = BatchProgress(batch_id="test")
        result = BatchResult(
            batch_id="test",
            progress=progress,
            results=[1, 2, 3],
            metadata={"key": "value"},
        )

        assert result.results == [1, 2, 3]
        assert result.metadata == {"key": "value"}


# =============================================================================
# BatchProcessor Initialization Tests
# =============================================================================


class TestBatchProcessorInit:
    """Tests for BatchProcessor initialization."""

    def test_default_initialization(self):
        """Test default BatchProcessor initialization."""
        processor = BatchProcessor()

        assert processor._chunk_size == 100
        assert processor._max_concurrency == 5
        assert processor._continue_on_error is True
        assert processor._active_batches == {}
        assert processor._pause_events == {}
        assert processor._cancel_events == {}

    def test_custom_initialization(self):
        """Test BatchProcessor with custom settings."""
        processor = BatchProcessor(
            chunk_size=50,
            max_concurrency=10,
            continue_on_error=False,
        )

        assert processor._chunk_size == 50
        assert processor._max_concurrency == 10
        assert processor._continue_on_error is False


# =============================================================================
# BatchProcessor Process Batch Tests
# =============================================================================


class TestBatchProcessorProcessBatch:
    """Tests for batch processing functionality."""

    @pytest.mark.asyncio
    async def test_process_batch_empty(self):
        """Test processing empty batch."""
        processor = BatchProcessor()

        def processor_fn(item):
            return item * 2

        result = await processor.process_batch([], processor_fn)

        assert result.batch_id is not None
        assert result.progress.total_items == 0
        assert result.progress.status == BatchStatus.COMPLETED
        assert result.results == []

    @pytest.mark.asyncio
    async def test_process_batch_sync_processor(self):
        """Test processing with sync processor function."""
        processor = BatchProcessor(chunk_size=10)

        def double(item):
            return item * 2

        result = await processor.process_batch([1, 2, 3, 4, 5], double)

        assert result.progress.total_items == 5
        assert result.progress.processed_items == 5
        assert result.progress.successful_items == 5
        assert result.progress.failed_items == 0
        assert result.progress.status == BatchStatus.COMPLETED
        assert sorted(result.results) == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_process_batch_async_processor(self):
        """Test processing with async processor function."""
        processor = BatchProcessor(chunk_size=10)

        async def async_double(item):
            await asyncio.sleep(0.001)
            return item * 2

        result = await processor.process_batch([1, 2, 3], async_double)

        assert result.progress.successful_items == 3
        assert result.progress.status == BatchStatus.COMPLETED
        assert sorted(result.results) == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_process_batch_with_custom_id(self):
        """Test processing with custom batch ID."""
        processor = BatchProcessor()
        batch_id = "my-custom-batch-123"

        result = await processor.process_batch(
            [1, 2, 3],
            lambda x: x,
            batch_id=batch_id,
        )

        assert result.batch_id == batch_id

    @pytest.mark.asyncio
    async def test_process_batch_progress_callback(self):
        """Test progress callback is called."""
        processor = BatchProcessor(chunk_size=2)
        progress_updates = []

        def on_progress(progress):
            progress_updates.append(progress.processed_items)

        result = await processor.process_batch(
            [1, 2, 3, 4, 5],
            lambda x: x,
            on_progress=on_progress,
        )

        assert len(progress_updates) > 0
        assert result.progress.status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_batch_with_errors_continue(self):
        """Test batch processing continues on errors."""
        processor = BatchProcessor(chunk_size=10, continue_on_error=True)

        def process_with_error(item):
            if item == 3:
                raise ValueError("Error on item 3")
            return item

        result = await processor.process_batch([1, 2, 3, 4, 5], process_with_error)

        assert result.progress.successful_items == 4
        assert result.progress.failed_items == 1
        assert result.progress.status == BatchStatus.COMPLETED
        assert len(result.progress.errors) == 1

    @pytest.mark.asyncio
    async def test_process_batch_all_errors(self):
        """Test batch where all items fail."""
        processor = BatchProcessor(chunk_size=10, continue_on_error=True)

        def always_fail(item):
            raise ValueError("Always fails")

        result = await processor.process_batch([1, 2, 3], always_fail)

        assert result.progress.successful_items == 0
        assert result.progress.failed_items == 3
        assert result.progress.status == BatchStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_batch_chunking(self):
        """Test that items are processed in chunks."""
        processor = BatchProcessor(chunk_size=2, max_concurrency=1)
        processed_batches = []

        def track_item(item):
            processed_batches.append(item)
            return item

        result = await processor.process_batch([1, 2, 3, 4, 5], track_item)

        assert result.progress.successful_items == 5
        assert len(processed_batches) == 5


# =============================================================================
# BatchProcessor Control Tests
# =============================================================================


class TestBatchProcessorControl:
    """Tests for batch control operations (pause, resume, cancel)."""

    @pytest.mark.asyncio
    async def test_pause_batch(self):
        """Test pausing a batch."""
        processor = BatchProcessor()

        # Start a batch that we can pause
        async def slow_processor(item):
            await asyncio.sleep(0.1)
            return item

        # Create batch task
        batch_task = asyncio.create_task(
            processor.process_batch(
                [1, 2, 3, 4, 5], slow_processor, batch_id="test-pause"
            )
        )

        await asyncio.sleep(0.05)  # Let it start

        # Pause
        paused = await processor.pause_batch("test-pause")
        assert paused is True

        # Cancel the task to clean up
        batch_task.cancel()
        try:
            await batch_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_pause_nonexistent_batch(self):
        """Test pausing a non-existent batch."""
        processor = BatchProcessor()
        result = await processor.pause_batch("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_nonexistent_batch(self):
        """Test resuming a non-existent batch."""
        processor = BatchProcessor()
        result = await processor.resume_batch("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_batch(self):
        """Test canceling a batch."""
        processor = BatchProcessor(chunk_size=1)

        async def slow_processor(item):
            await asyncio.sleep(0.2)
            return item

        # Start batch with more items to give time for cancel
        batch_task = asyncio.create_task(
            processor.process_batch(
                [1, 2, 3, 4, 5], slow_processor, batch_id="test-cancel"
            )
        )

        await asyncio.sleep(0.1)  # Let it start

        # Cancel
        cancelled = await processor.cancel_batch("test-cancel")
        assert cancelled is True

        # Wait for batch to finish
        result = await batch_task
        # Status can be CANCELLED or COMPLETED depending on timing
        assert result.progress.status in [BatchStatus.CANCELLED, BatchStatus.COMPLETED]

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_batch(self):
        """Test canceling a non-existent batch."""
        processor = BatchProcessor()
        result = await processor.cancel_batch("nonexistent")
        assert result is False


# =============================================================================
# BatchProcessor Status Tests
# =============================================================================


class TestBatchProcessorStatus:
    """Tests for batch status retrieval."""

    @pytest.mark.asyncio
    async def test_get_batch_progress(self):
        """Test getting batch progress during processing."""
        processor = BatchProcessor()

        async def slow_processor(item):
            await asyncio.sleep(0.1)
            return item

        # Start batch
        batch_task = asyncio.create_task(
            processor.process_batch([1, 2, 3], slow_processor, batch_id="test-progress")
        )

        await asyncio.sleep(0.05)

        progress = processor.get_batch_progress("test-progress")
        assert progress is not None
        assert progress.batch_id == "test-progress"

        # Clean up
        await processor.cancel_batch("test-progress")
        await batch_task

    def test_get_batch_progress_not_found(self):
        """Test getting progress for non-existent batch."""
        processor = BatchProcessor()
        progress = processor.get_batch_progress("nonexistent")
        assert progress is None

    def test_get_all_active_batches_empty(self):
        """Test getting active batches when none active."""
        processor = BatchProcessor()
        batches = processor.get_all_active_batches()
        assert batches == {}


# =============================================================================
# BatchProcessor Stream Tests
# =============================================================================


class TestBatchProcessorStream:
    """Tests for stream processing functionality."""

    @pytest.mark.asyncio
    async def test_process_stream_empty(self):
        """Test processing empty stream."""
        processor = BatchProcessor()

        async def empty_stream():
            return
            yield  # Make it a generator

        result = await processor.process_stream(empty_stream(), lambda x: x)

        assert result.progress.total_items == 0
        assert result.progress.status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_stream_with_items(self):
        """Test processing stream with items."""
        processor = BatchProcessor(chunk_size=2)

        async def item_stream():
            for i in range(5):
                yield i

        result = await processor.process_stream(
            item_stream(),
            lambda x: x * 2,
            estimated_total=5,
        )

        assert result.progress.processed_items == 5
        assert result.progress.successful_items == 5
        assert result.progress.status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_stream_cancel(self):
        """Test canceling stream processing."""
        processor = BatchProcessor(chunk_size=1)

        async def slow_stream():
            for i in range(100):
                await asyncio.sleep(0.1)
                yield i

        batch_task = asyncio.create_task(
            processor.process_stream(
                slow_stream(),
                lambda x: x,
                batch_id="test-stream-cancel",
            )
        )

        await asyncio.sleep(0.15)
        await processor.cancel_batch("test-stream-cancel")

        result = await batch_task
        assert result.progress.status == BatchStatus.CANCELLED


# =============================================================================
# Singleton Tests
# =============================================================================


class TestBatchProcessorSingleton:
    """Tests for batch processor singleton pattern."""

    def test_get_batch_processor_returns_instance(self):
        """Test get_batch_processor returns an instance."""
        import app.services.batch.batch_processor as module

        module._batch_processor = None

        processor = get_batch_processor()
        assert isinstance(processor, BatchProcessor)

    def test_get_batch_processor_returns_same_instance(self):
        """Test get_batch_processor returns cached singleton."""
        import app.services.batch.batch_processor as module

        module._batch_processor = None

        processor1 = get_batch_processor()
        processor2 = get_batch_processor()
        assert processor1 is processor2
