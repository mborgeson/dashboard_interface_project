"""
Job Queue Management

Provides a priority-based job queue for background task processing.
Supports both in-memory and Redis-backed storage.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from heapq import heappop, heappush
from typing import Any

from loguru import logger


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobPriority(int, Enum):
    """Job priority levels (lower number = higher priority)."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class Job:
    """
    Represents a background job.

    Attributes:
        id: Unique job identifier
        name: Human-readable job name
        task_type: Type of task to execute
        payload: Task parameters and data
        priority: Job priority level
        status: Current execution status
        created_at: Job creation timestamp
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        result: Task result (on success)
        error: Error message (on failure)
        retry_count: Number of retry attempts
        max_retries: Maximum retry attempts
        timeout: Job timeout in seconds
        metadata: Additional job metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # 5 minutes default
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Job") -> bool:
        """Compare jobs by priority for heap ordering."""
        return (self.priority.value, self.created_at) < (other.priority.value, other.created_at)

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Create job from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            task_type=data.get("task_type", ""),
            payload=data.get("payload", {}),
            priority=JobPriority(data.get("priority", JobPriority.NORMAL)),
            status=JobStatus(data.get("status", JobStatus.PENDING)),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timeout=data.get("timeout", 300),
            metadata=data.get("metadata", {}),
        )


class JobQueue:
    """
    Priority-based job queue with in-memory and Redis support.

    Features:
    - Priority-based ordering
    - Job status tracking
    - Retry handling
    - Timeout management
    - Job history
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize job queue.

        Args:
            max_history: Maximum number of completed jobs to retain
        """
        self._queue: list[Job] = []  # Priority heap
        self._jobs: dict[str, Job] = {}  # All jobs by ID
        self._history: list[Job] = []  # Completed jobs
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._redis_client = None
        self._use_redis = False

    async def initialize(self, redis_url: str | None = None) -> None:
        """
        Initialize queue with optional Redis backing.

        Args:
            redis_url: Redis connection URL for persistence
        """
        if redis_url:
            try:
                from app.services.redis_service import get_redis_client
                self._redis_client = await get_redis_client()
                if self._redis_client:
                    self._use_redis = True
                    await self._load_from_redis()
                    logger.info("Job queue initialized with Redis backing")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, using in-memory queue: {e}")
        else:
            logger.info("Job queue initialized with in-memory storage")

    async def _load_from_redis(self) -> None:
        """Load pending jobs from Redis."""
        if not self._redis_client:
            return

        try:
            job_ids = await self._redis_client.smembers("job_queue:pending")
            for job_id in job_ids:
                job_data = await self._redis_client.hgetall(f"job:{job_id}")
                if job_data:
                    job = Job.from_dict(job_data)
                    self._jobs[job.id] = job
                    if job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RETRY]:
                        heappush(self._queue, job)
        except Exception as e:
            logger.error(f"Failed to load jobs from Redis: {e}")

    async def _save_to_redis(self, job: Job) -> None:
        """Save job to Redis."""
        if not self._redis_client:
            return

        try:
            await self._redis_client.hset(f"job:{job.id}", mapping=job.to_dict())
            if job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RETRY]:
                await self._redis_client.sadd("job_queue:pending", job.id)
            else:
                await self._redis_client.srem("job_queue:pending", job.id)
                await self._redis_client.sadd("job_queue:completed", job.id)
        except Exception as e:
            logger.error(f"Failed to save job to Redis: {e}")

    async def enqueue(
        self,
        task_type: str,
        payload: dict[str, Any],
        name: str | None = None,
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        timeout: int = 300,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        """
        Add a new job to the queue.

        Args:
            task_type: Type of task to execute
            payload: Task parameters
            name: Human-readable job name
            priority: Job priority level
            max_retries: Maximum retry attempts
            timeout: Job timeout in seconds
            metadata: Additional job metadata

        Returns:
            Created job instance
        """
        job = Job(
            name=name or task_type,
            task_type=task_type,
            payload=payload,
            priority=priority,
            status=JobStatus.QUEUED,
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata or {},
        )

        async with self._lock:
            self._jobs[job.id] = job
            heappush(self._queue, job)

            if self._use_redis:
                await self._save_to_redis(job)

        logger.info(f"Job enqueued: {job.id} ({job.task_type})")
        return job

    async def dequeue(self) -> Job | None:
        """
        Get the next job from the queue.

        Returns:
            Next job or None if queue is empty
        """
        async with self._lock:
            while self._queue:
                job = heappop(self._queue)

                # Skip cancelled jobs
                if job.status == JobStatus.CANCELLED:
                    continue

                # Refresh from storage
                stored_job = self._jobs.get(job.id)
                if stored_job and stored_job.status in [JobStatus.QUEUED, JobStatus.RETRY]:
                    stored_job.status = JobStatus.RUNNING
                    stored_job.started_at = datetime.utcnow()

                    if self._use_redis:
                        await self._save_to_redis(stored_job)

                    return stored_job

            return None

    async def complete(self, job_id: str, result: Any = None) -> Job | None:
        """
        Mark a job as completed.

        Args:
            job_id: Job identifier
            result: Task result

        Returns:
            Updated job or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result

            # Add to history
            self._history.append(job)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            if self._use_redis:
                await self._save_to_redis(job)

            logger.info(f"Job completed: {job.id} ({job.task_type})")
            return job

    async def fail(self, job_id: str, error: str) -> Job | None:
        """
        Mark a job as failed.

        Args:
            job_id: Job identifier
            error: Error message

        Returns:
            Updated job or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            job.error = error
            job.retry_count += 1

            if job.retry_count < job.max_retries:
                # Schedule retry
                job.status = JobStatus.RETRY
                heappush(self._queue, job)
                logger.warning(f"Job failed, scheduling retry {job.retry_count}/{job.max_retries}: {job.id}")
            else:
                # Max retries exceeded
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                self._history.append(job)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
                logger.error(f"Job failed permanently: {job.id} - {error}")

            if self._use_redis:
                await self._save_to_redis(job)

            return job

    async def cancel(self, job_id: str) -> Job | None:
        """
        Cancel a pending job.

        Args:
            job_id: Job identifier

        Returns:
            Updated job or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RETRY]:
                logger.warning(f"Cannot cancel job in status {job.status}: {job.id}")
                return job

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()

            if self._use_redis:
                await self._save_to_redis(job)

            logger.info(f"Job cancelled: {job.id}")
            return job

    async def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def get_pending_jobs(self) -> list[Job]:
        """Get all pending/queued jobs."""
        return [
            j for j in self._jobs.values()
            if j.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RETRY]
        ]

    async def get_running_jobs(self) -> list[Job]:
        """Get all currently running jobs."""
        return [j for j in self._jobs.values() if j.status == JobStatus.RUNNING]

    async def get_history(self, limit: int = 100) -> list[Job]:
        """Get completed job history."""
        return self._history[-limit:]

    async def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = sum(
                1 for j in self._jobs.values() if j.status == status
            )

        return {
            "queue_size": len(self._queue),
            "total_jobs": len(self._jobs),
            "history_size": len(self._history),
            "status_counts": status_counts,
            "use_redis": self._use_redis,
        }

    async def clear_completed(self, older_than: timedelta | None = None) -> int:
        """
        Clear completed jobs from memory.

        Args:
            older_than: Only clear jobs older than this duration

        Returns:
            Number of jobs cleared
        """
        cutoff = datetime.utcnow() - older_than if older_than else None
        cleared = 0

        async with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if cutoff is None or (job.completed_at and job.completed_at < cutoff):
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                cleared += 1

        logger.info(f"Cleared {cleared} completed jobs from queue")
        return cleared


# Singleton instance
_job_queue: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """Get or create the job queue singleton."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue
