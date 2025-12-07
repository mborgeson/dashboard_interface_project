"""
Task Scheduler

Provides cron-like scheduling for recurring tasks.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4

from loguru import logger


class ScheduleInterval(str, Enum):
    """Common schedule intervals."""
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledTask:
    """
    Represents a scheduled task.

    Attributes:
        id: Unique task identifier
        name: Human-readable task name
        task_type: Type of task to execute
        payload: Task parameters
        interval_seconds: Execution interval in seconds
        last_run: Last execution timestamp
        next_run: Next scheduled execution
        enabled: Whether the task is active
        run_count: Number of executions
        error_count: Number of failed executions
        last_error: Last error message
        created_at: Task creation time
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    interval_seconds: int = 3600  # Default 1 hour
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "payload": self.payload,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "enabled": self.enabled,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            task_type=data.get("task_type", ""),
            payload=data.get("payload", {}),
            interval_seconds=data.get("interval_seconds", 3600),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            enabled=data.get("enabled", True),
            run_count=data.get("run_count", 0),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )

    def calculate_next_run(self) -> datetime:
        """Calculate next run time based on interval."""
        base_time = self.last_run or datetime.utcnow()
        return base_time + timedelta(seconds=self.interval_seconds)


class TaskScheduler:
    """
    Cron-like task scheduler.

    Features:
    - Configurable intervals
    - Task persistence
    - Error handling and retry
    - Enable/disable tasks
    - Statistics tracking
    """

    def __init__(self, check_interval: float = 60.0):
        """
        Initialize scheduler.

        Args:
            check_interval: How often to check for due tasks (seconds)
        """
        self._check_interval = check_interval
        self._tasks: Dict[str, ScheduledTask] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._redis_client = None
        self._use_redis = False

    async def initialize(self, redis_url: Optional[str] = None) -> None:
        """
        Initialize scheduler with optional Redis persistence.

        Args:
            redis_url: Redis connection URL
        """
        if redis_url:
            try:
                from app.services.redis_service import get_redis_client
                self._redis_client = await get_redis_client()
                if self._redis_client:
                    self._use_redis = True
                    await self._load_from_redis()
                    logger.info("Scheduler initialized with Redis persistence")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")

        logger.info("Task scheduler initialized")

    async def _load_from_redis(self) -> None:
        """Load scheduled tasks from Redis."""
        if not self._redis_client:
            return

        try:
            task_ids = await self._redis_client.smembers("scheduler:tasks")
            for task_id in task_ids:
                task_data = await self._redis_client.hgetall(f"scheduler:task:{task_id}")
                if task_data:
                    task = ScheduledTask.from_dict(task_data)
                    self._tasks[task.id] = task
            logger.info(f"Loaded {len(self._tasks)} scheduled tasks from Redis")
        except Exception as e:
            logger.error(f"Failed to load tasks from Redis: {e}")

    async def _save_to_redis(self, task: ScheduledTask) -> None:
        """Save task to Redis."""
        if not self._redis_client:
            return

        try:
            await self._redis_client.hset(
                f"scheduler:task:{task.id}",
                mapping=task.to_dict()
            )
            await self._redis_client.sadd("scheduler:tasks", task.id)
        except Exception as e:
            logger.error(f"Failed to save task to Redis: {e}")

    async def _delete_from_redis(self, task_id: str) -> None:
        """Delete task from Redis."""
        if not self._redis_client:
            return

        try:
            await self._redis_client.delete(f"scheduler:task:{task_id}")
            await self._redis_client.srem("scheduler:tasks", task_id)
        except Exception as e:
            logger.error(f"Failed to delete task from Redis: {e}")

    def register_handler(
        self,
        task_type: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Task type identifier
            handler: Async function to execute
        """
        self._handlers[task_type] = handler
        logger.info(f"Registered scheduler handler: {task_type}")

    async def add_task(
        self,
        name: str,
        task_type: str,
        interval: ScheduleInterval | int,
        payload: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        run_immediately: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """
        Add a new scheduled task.

        Args:
            name: Human-readable task name
            task_type: Type of task (must have registered handler)
            interval: Execution interval
            payload: Task parameters
            enabled: Whether task is active
            run_immediately: Run task immediately after adding
            metadata: Additional task metadata

        Returns:
            Created scheduled task
        """
        # Convert interval enum to seconds
        if isinstance(interval, ScheduleInterval):
            interval_seconds = {
                ScheduleInterval.MINUTE: 60,
                ScheduleInterval.HOURLY: 3600,
                ScheduleInterval.DAILY: 86400,
                ScheduleInterval.WEEKLY: 604800,
                ScheduleInterval.MONTHLY: 2592000,  # 30 days
            }.get(interval, 3600)
        else:
            interval_seconds = interval

        task = ScheduledTask(
            name=name,
            task_type=task_type,
            payload=payload or {},
            interval_seconds=interval_seconds,
            enabled=enabled,
            metadata=metadata or {},
        )

        # Calculate first run time
        if run_immediately:
            task.next_run = datetime.utcnow()
        else:
            task.next_run = task.calculate_next_run()

        self._tasks[task.id] = task

        if self._use_redis:
            await self._save_to_redis(task)

        logger.info(f"Scheduled task added: {task.name} ({task.id})")
        return task

    async def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            task_id: Task identifier

        Returns:
            True if removed successfully
        """
        if task_id not in self._tasks:
            return False

        del self._tasks[task_id]

        if self._use_redis:
            await self._delete_from_redis(task_id)

        logger.info(f"Scheduled task removed: {task_id}")
        return True

    async def enable_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Enable a scheduled task."""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = True
            task.next_run = task.calculate_next_run()
            if self._use_redis:
                await self._save_to_redis(task)
            logger.info(f"Task enabled: {task_id}")
        return task

    async def disable_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Disable a scheduled task."""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = False
            if self._use_redis:
                await self._save_to_redis(task)
            logger.info(f"Task disabled: {task_id}")
        return task

    async def run_task_now(self, task_id: str) -> bool:
        """
        Run a scheduled task immediately.

        Args:
            task_id: Task identifier

        Returns:
            True if task was executed
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        await self._execute_task(task)
        return True

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Task scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.utcnow()

                # Find due tasks
                due_tasks = [
                    task for task in self._tasks.values()
                    if task.enabled and task.next_run and task.next_run <= now
                ]

                # Execute due tasks
                for task in due_tasks:
                    asyncio.create_task(self._execute_task(task))

                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Scheduler loop error: {e}")
                await asyncio.sleep(self._check_interval)

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        handler = self._handlers.get(task.task_type)
        if not handler:
            logger.error(f"No handler for scheduled task type: {task.task_type}")
            task.last_error = f"No handler registered for task type: {task.task_type}"
            task.error_count += 1
            return

        logger.info(f"Executing scheduled task: {task.name} ({task.id})")

        try:
            await handler(task.payload)
            task.run_count += 1
            task.last_run = datetime.utcnow()
            task.next_run = task.calculate_next_run()
            task.last_error = None
            logger.info(f"Scheduled task completed: {task.name}")

        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            task.last_run = datetime.utcnow()
            task.next_run = task.calculate_next_run()
            logger.exception(f"Scheduled task failed: {task.name} - {e}")

        if self._use_redis:
            await self._save_to_redis(task)

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        return list(self._tasks.values())

    def get_enabled_tasks(self) -> List[ScheduledTask]:
        """Get all enabled tasks."""
        return [t for t in self._tasks.values() if t.enabled]

    async def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        tasks = list(self._tasks.values())
        return {
            "running": self._running,
            "total_tasks": len(tasks),
            "enabled_tasks": sum(1 for t in tasks if t.enabled),
            "disabled_tasks": sum(1 for t in tasks if not t.enabled),
            "total_runs": sum(t.run_count for t in tasks),
            "total_errors": sum(t.error_count for t in tasks),
            "registered_handlers": list(self._handlers.keys()),
            "use_redis": self._use_redis,
        }


# Singleton instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get or create the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


# =============================================================================
# Built-in Scheduled Task Handlers
# =============================================================================

async def cleanup_old_jobs_handler(payload: Dict[str, Any]) -> None:
    """Clean up old completed jobs from the queue."""
    from .job_queue import get_job_queue
    from datetime import timedelta

    max_age_hours = payload.get("max_age_hours", 24)
    queue = get_job_queue()
    cleared = await queue.clear_completed(
        older_than=timedelta(hours=max_age_hours)
    )
    logger.info(f"Cleaned up {cleared} old jobs")


async def system_health_check_handler(payload: Dict[str, Any]) -> None:
    """Perform periodic system health checks."""
    from app.services.monitoring.collectors import get_collector_registry

    registry = get_collector_registry()
    metrics = await registry.collect_all()

    # Log any concerning metrics
    system = metrics.get("system", {})
    if system.get("memory", {}).get("percent", 0) > 85:
        logger.warning(f"High memory usage: {system['memory']['percent']}%")
    if system.get("disk", {}).get("percent", 0) > 90:
        logger.warning(f"High disk usage: {system['disk']['percent']}%")


async def database_maintenance_handler(payload: Dict[str, Any]) -> None:
    """Perform database maintenance tasks."""
    # This would include things like:
    # - Vacuum analyze
    # - Index maintenance
    # - Statistics update
    logger.info("Database maintenance task executed")


def register_default_scheduled_tasks(scheduler: TaskScheduler) -> None:
    """Register default scheduled task handlers."""
    scheduler.register_handler("cleanup_old_jobs", cleanup_old_jobs_handler)
    scheduler.register_handler("system_health_check", system_health_check_handler)
    scheduler.register_handler("database_maintenance", database_maintenance_handler)
    logger.info("Default scheduled task handlers registered")
