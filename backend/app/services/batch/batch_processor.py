"""
Batch Data Processor

Handles bulk data operations with progress tracking and chunking.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar
from uuid import uuid4

from loguru import logger

T = TypeVar("T")
R = TypeVar("R")


class BatchStatus(StrEnum):
    """Batch processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class BatchProgress:
    """Tracks progress of a batch operation."""

    batch_id: str
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    status: BatchStatus = BatchStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def progress_percent(self) -> float:
        """Get progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100

    @property
    def duration_seconds(self) -> float | None:
        """Get processing duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "progress_percent": round(self.progress_percent, 2),
            "success_rate": round(self.success_rate, 2),
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors[-10:],  # Last 10 errors
        }


@dataclass
class BatchResult(Generic[R]):
    """Result of a batch operation."""

    batch_id: str
    progress: BatchProgress
    results: list[R] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BatchProcessor(Generic[T, R]):
    """
    Processes data in batches with progress tracking.

    Features:
    - Configurable chunk sizes
    - Progress callbacks
    - Error handling per item
    - Pause/resume support
    - Concurrent processing
    """

    def __init__(
        self,
        chunk_size: int = 100,
        max_concurrency: int = 5,
        continue_on_error: bool = True,
    ):
        """
        Initialize batch processor.

        Args:
            chunk_size: Items per processing chunk
            max_concurrency: Maximum concurrent operations
            continue_on_error: Continue processing on item errors
        """
        self._chunk_size = chunk_size
        self._max_concurrency = max_concurrency
        self._continue_on_error = continue_on_error
        self._active_batches: dict[str, BatchProgress] = {}
        self._pause_events: dict[str, asyncio.Event] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    async def process_batch(
        self,
        items: list[T],
        processor: Callable[[T], Any],
        on_progress: Callable[[BatchProgress], None] | None = None,
        batch_id: str | None = None,
    ) -> BatchResult:
        """
        Process a list of items in batches.

        Args:
            items: Items to process
            processor: Function to process each item (sync or async)
            on_progress: Callback for progress updates
            batch_id: Optional batch identifier

        Returns:
            BatchResult with progress and results
        """
        batch_id = batch_id or str(uuid4())
        progress = BatchProgress(
            batch_id=batch_id,
            total_items=len(items),
            status=BatchStatus.PROCESSING,
            started_at=datetime.utcnow(),
        )

        self._active_batches[batch_id] = progress
        self._pause_events[batch_id] = asyncio.Event()
        self._pause_events[batch_id].set()  # Not paused initially
        self._cancel_events[batch_id] = asyncio.Event()

        results: list[R] = []

        try:
            # Process in chunks
            for chunk_start in range(0, len(items), self._chunk_size):
                # Check for cancellation
                if self._cancel_events[batch_id].is_set():
                    progress.status = BatchStatus.CANCELLED
                    break

                # Wait if paused
                await self._pause_events[batch_id].wait()

                chunk = items[chunk_start : chunk_start + self._chunk_size]
                chunk_results = await self._process_chunk(
                    chunk, processor, progress, batch_id
                )
                results.extend(chunk_results)

                # Progress callback
                if on_progress:
                    on_progress(progress)

            # Set final status
            if progress.status == BatchStatus.PROCESSING:
                if progress.failed_items == 0:
                    progress.status = BatchStatus.COMPLETED
                elif progress.successful_items > 0:
                    progress.status = BatchStatus.COMPLETED  # Partial success
                else:
                    progress.status = BatchStatus.FAILED

        except Exception as e:
            logger.exception(f"Batch {batch_id} failed: {e}")
            progress.status = BatchStatus.FAILED
            progress.errors.append(
                {
                    "type": "batch_error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        finally:
            progress.completed_at = datetime.utcnow()
            self._cleanup_batch(batch_id)

        logger.info(
            f"Batch {batch_id} completed: "
            f"{progress.successful_items}/{progress.total_items} successful"
        )

        return BatchResult(
            batch_id=batch_id,
            progress=progress,
            results=results,
        )

    async def _process_chunk(
        self,
        chunk: list[T],
        processor: Callable[[T], Any],
        progress: BatchProgress,
        batch_id: str,
    ) -> list[R]:
        """Process a single chunk of items."""
        semaphore = asyncio.Semaphore(self._max_concurrency)
        results: list[R] = []

        async def process_item(item: T, index: int) -> R | None:
            async with semaphore:
                # Check for cancellation
                if self._cancel_events[batch_id].is_set():
                    return None

                try:
                    # Handle both sync and async processors
                    if asyncio.iscoroutinefunction(processor):
                        result = await processor(item)
                    else:
                        result = await asyncio.to_thread(processor, item)

                    progress.processed_items += 1
                    progress.successful_items += 1
                    return result

                except Exception as e:
                    progress.processed_items += 1
                    progress.failed_items += 1
                    progress.errors.append(
                        {
                            "item_index": index,
                            "message": str(e),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                    if not self._continue_on_error:
                        raise

                    return None

        # Process all items in chunk concurrently
        tasks = [process_item(item, i) for i, item in enumerate(chunk)]
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        for result in chunk_results:
            if result is not None and not isinstance(result, BaseException):
                results.append(result)  # type: ignore[arg-type]

        return results

    def _cleanup_batch(self, batch_id: str) -> None:
        """Clean up batch resources."""
        self._pause_events.pop(batch_id, None)
        self._cancel_events.pop(batch_id, None)

    async def pause_batch(self, batch_id: str) -> bool:
        """
        Pause a running batch.

        Args:
            batch_id: Batch identifier

        Returns:
            True if paused successfully
        """
        if batch_id in self._pause_events:
            self._pause_events[batch_id].clear()
            if batch_id in self._active_batches:
                self._active_batches[batch_id].status = BatchStatus.PAUSED
            logger.info(f"Batch {batch_id} paused")
            return True
        return False

    async def resume_batch(self, batch_id: str) -> bool:
        """
        Resume a paused batch.

        Args:
            batch_id: Batch identifier

        Returns:
            True if resumed successfully
        """
        if batch_id in self._pause_events:
            self._pause_events[batch_id].set()
            if batch_id in self._active_batches:
                self._active_batches[batch_id].status = BatchStatus.PROCESSING
            logger.info(f"Batch {batch_id} resumed")
            return True
        return False

    async def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a running batch.

        Args:
            batch_id: Batch identifier

        Returns:
            True if cancelled successfully
        """
        if batch_id in self._cancel_events:
            self._cancel_events[batch_id].set()
            # Also resume if paused to allow cancellation to proceed
            if batch_id in self._pause_events:
                self._pause_events[batch_id].set()
            logger.info(f"Batch {batch_id} cancellation requested")
            return True
        return False

    def get_batch_progress(self, batch_id: str) -> BatchProgress | None:
        """Get progress for a batch."""
        return self._active_batches.get(batch_id)

    def get_all_active_batches(self) -> dict[str, BatchProgress]:
        """Get all active batch progresses."""
        return dict(self._active_batches)

    async def process_stream(
        self,
        items: AsyncIterator[T],
        processor: Callable[[T], Any],
        on_progress: Callable[[BatchProgress], None] | None = None,
        batch_id: str | None = None,
        estimated_total: int = 0,
    ) -> BatchResult:
        """
        Process items from an async stream.

        Args:
            items: Async iterator of items
            processor: Function to process each item
            on_progress: Callback for progress updates
            batch_id: Optional batch identifier
            estimated_total: Estimated total items (for progress)

        Returns:
            BatchResult with progress and results
        """
        batch_id = batch_id or str(uuid4())
        progress = BatchProgress(
            batch_id=batch_id,
            total_items=estimated_total,
            status=BatchStatus.PROCESSING,
            started_at=datetime.utcnow(),
        )

        self._active_batches[batch_id] = progress
        self._pause_events[batch_id] = asyncio.Event()
        self._pause_events[batch_id].set()
        self._cancel_events[batch_id] = asyncio.Event()

        results: list[R] = []
        buffer: list[T] = []

        try:
            async for item in items:
                # Check for cancellation
                if self._cancel_events[batch_id].is_set():
                    progress.status = BatchStatus.CANCELLED
                    break

                # Wait if paused
                await self._pause_events[batch_id].wait()

                buffer.append(item)

                # Process when buffer is full
                if len(buffer) >= self._chunk_size:
                    chunk_results = await self._process_chunk(
                        buffer, processor, progress, batch_id
                    )
                    results.extend(chunk_results)
                    buffer = []

                    if on_progress:
                        on_progress(progress)

            # Process remaining items
            if buffer and not self._cancel_events[batch_id].is_set():
                chunk_results = await self._process_chunk(
                    buffer, processor, progress, batch_id
                )
                results.extend(chunk_results)

            # Update total items (now we know the actual count)
            progress.total_items = progress.processed_items

            # Set final status
            if progress.status == BatchStatus.PROCESSING:
                progress.status = (
                    BatchStatus.COMPLETED
                    if progress.failed_items == 0
                    else BatchStatus.COMPLETED
                )

        except Exception as e:
            logger.exception(f"Stream batch {batch_id} failed: {e}")
            progress.status = BatchStatus.FAILED
            progress.errors.append(
                {
                    "type": "stream_error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        finally:
            progress.completed_at = datetime.utcnow()
            self._cleanup_batch(batch_id)

        return BatchResult(
            batch_id=batch_id,
            progress=progress,
            results=results,
        )


# Singleton instance
_batch_processor: BatchProcessor | None = None


def get_batch_processor() -> BatchProcessor:
    """Get or create the batch processor singleton."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
