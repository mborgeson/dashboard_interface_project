"""Tests for task scheduler service."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.batch.scheduler import (
    ScheduledTask,
    ScheduleInterval,
    TaskScheduler,
    get_scheduler,
)

# =============================================================================
# ScheduleInterval Tests
# =============================================================================


class TestScheduleInterval:
    """Tests for ScheduleInterval enum."""

    def test_interval_values(self):
        """Test all interval values exist."""
        assert ScheduleInterval.MINUTE == "minute"
        assert ScheduleInterval.HOURLY == "hourly"
        assert ScheduleInterval.DAILY == "daily"
        assert ScheduleInterval.WEEKLY == "weekly"
        assert ScheduleInterval.MONTHLY == "monthly"


# =============================================================================
# ScheduledTask Tests
# =============================================================================


class TestScheduledTask:
    """Tests for ScheduledTask dataclass."""

    def test_task_creation_defaults(self):
        """Test creating a task with defaults."""
        task = ScheduledTask()

        assert task.id is not None
        assert task.name == ""
        assert task.task_type == ""
        assert task.payload == {}
        assert task.interval_seconds == 3600
        assert task.last_run is None
        assert task.next_run is None
        assert task.enabled is True
        assert task.run_count == 0
        assert task.error_count == 0
        assert task.last_error is None

    def test_task_creation_custom(self):
        """Test creating a task with custom values."""
        task = ScheduledTask(
            id="custom-task",
            name="My Task",
            task_type="cleanup",
            payload={"key": "value"},
            interval_seconds=300,
            enabled=False,
        )

        assert task.id == "custom-task"
        assert task.name == "My Task"
        assert task.task_type == "cleanup"
        assert task.interval_seconds == 300
        assert task.enabled is False

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = ScheduledTask(
            id="test-task",
            name="Test Task",
            task_type="test",
            interval_seconds=60,
        )

        d = task.to_dict()

        assert d["id"] == "test-task"
        assert d["name"] == "Test Task"
        assert d["task_type"] == "test"
        assert d["interval_seconds"] == 60
        assert d["enabled"] is True

    def test_task_to_dict_with_timestamps(self):
        """Test to_dict includes formatted timestamps."""
        now = datetime.utcnow()
        task = ScheduledTask(last_run=now, next_run=now)

        d = task.to_dict()

        assert d["last_run"] == now.isoformat()
        assert d["next_run"] == now.isoformat()

    def test_task_from_dict(self):
        """Test creating task from dictionary."""
        data = {
            "id": "from-dict-task",
            "name": "From Dict Task",
            "task_type": "import",
            "payload": {"file": "data.csv"},
            "interval_seconds": 7200,
            "enabled": False,
            "run_count": 5,
            "error_count": 1,
        }

        task = ScheduledTask.from_dict(data)

        assert task.id == "from-dict-task"
        assert task.name == "From Dict Task"
        assert task.task_type == "import"
        assert task.interval_seconds == 7200
        assert task.enabled is False
        assert task.run_count == 5
        assert task.error_count == 1

    def test_task_from_dict_with_timestamps(self):
        """Test creating task from dict with timestamps."""
        now = datetime.utcnow()
        data = {
            "last_run": now.isoformat(),
            "next_run": now.isoformat(),
            "created_at": now.isoformat(),
        }

        task = ScheduledTask.from_dict(data)

        assert task.last_run == now
        assert task.next_run == now

    def test_task_from_dict_minimal(self):
        """Test creating task from minimal dictionary."""
        data = {}
        task = ScheduledTask.from_dict(data)

        assert task.id is not None
        assert task.interval_seconds == 3600
        assert task.enabled is True

    def test_calculate_next_run_no_last_run(self):
        """Test calculating next run without last run."""
        task = ScheduledTask(interval_seconds=3600)
        before = datetime.utcnow()

        next_run = task.calculate_next_run()

        assert next_run >= before + timedelta(seconds=3600)

    def test_calculate_next_run_with_last_run(self):
        """Test calculating next run with last run."""
        last = datetime(2025, 1, 1, 12, 0, 0)
        task = ScheduledTask(interval_seconds=3600, last_run=last)

        next_run = task.calculate_next_run()

        expected = datetime(2025, 1, 1, 13, 0, 0)
        assert next_run == expected


# =============================================================================
# TaskScheduler Initialization Tests
# =============================================================================


class TestTaskSchedulerInit:
    """Tests for TaskScheduler initialization."""

    def test_default_initialization(self):
        """Test default TaskScheduler initialization."""
        scheduler = TaskScheduler()

        assert scheduler._check_interval == 60.0
        assert scheduler._tasks == {}
        assert scheduler._handlers == {}
        assert scheduler._running is False
        assert scheduler._scheduler_task is None
        assert scheduler._use_redis is False

    def test_custom_check_interval(self):
        """Test TaskScheduler with custom check interval."""
        scheduler = TaskScheduler(check_interval=30.0)
        assert scheduler._check_interval == 30.0

    @pytest.mark.asyncio
    async def test_initialize_without_redis(self):
        """Test initialization without Redis."""
        scheduler = TaskScheduler()
        await scheduler.initialize()

        assert scheduler._use_redis is False


# =============================================================================
# Handler Registration Tests
# =============================================================================


class TestHandlerRegistration:
    """Tests for registering task handlers."""

    def test_register_handler(self):
        """Test registering a task handler."""
        scheduler = TaskScheduler()

        async def my_handler(payload):
            pass

        scheduler.register_handler("my_task", my_handler)

        assert "my_task" in scheduler._handlers
        assert scheduler._handlers["my_task"] is my_handler

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers."""
        scheduler = TaskScheduler()

        async def handler1(payload):
            pass

        async def handler2(payload):
            pass

        scheduler.register_handler("task1", handler1)
        scheduler.register_handler("task2", handler2)

        assert len(scheduler._handlers) == 2


# =============================================================================
# Task Management Tests
# =============================================================================


class TestTaskManagement:
    """Tests for task management operations."""

    @pytest.mark.asyncio
    async def test_add_task_basic(self):
        """Test adding a basic scheduled task."""
        scheduler = TaskScheduler()

        task = await scheduler.add_task(
            name="Test Task",
            task_type="test",
            interval=ScheduleInterval.HOURLY,
        )

        assert task is not None
        assert task.name == "Test Task"
        assert task.task_type == "test"
        assert task.interval_seconds == 3600
        assert task.enabled is True
        assert task.id in scheduler._tasks

    @pytest.mark.asyncio
    async def test_add_task_with_interval_seconds(self):
        """Test adding task with custom interval in seconds."""
        scheduler = TaskScheduler()

        task = await scheduler.add_task(
            name="Custom Interval",
            task_type="test",
            interval=120,  # 2 minutes
        )

        assert task.interval_seconds == 120

    @pytest.mark.asyncio
    async def test_add_task_disabled(self):
        """Test adding a disabled task."""
        scheduler = TaskScheduler()

        task = await scheduler.add_task(
            name="Disabled Task",
            task_type="test",
            interval=ScheduleInterval.DAILY,
            enabled=False,
        )

        assert task.enabled is False

    @pytest.mark.asyncio
    async def test_add_task_run_immediately(self):
        """Test adding task with run immediately flag."""
        scheduler = TaskScheduler()
        before = datetime.utcnow()

        task = await scheduler.add_task(
            name="Immediate Task",
            task_type="test",
            interval=ScheduleInterval.HOURLY,
            run_immediately=True,
        )

        assert task.next_run is not None
        assert task.next_run >= before
        # Should be close to now, not hour from now
        assert (task.next_run - before).total_seconds() < 10

    @pytest.mark.asyncio
    async def test_add_task_with_payload_and_metadata(self):
        """Test adding task with payload and metadata."""
        scheduler = TaskScheduler()

        task = await scheduler.add_task(
            name="Full Task",
            task_type="test",
            interval=ScheduleInterval.DAILY,
            payload={"key": "value"},
            metadata={"source": "test"},
        )

        assert task.payload == {"key": "value"}
        assert task.metadata == {"source": "test"}

    @pytest.mark.asyncio
    async def test_remove_task(self):
        """Test removing a scheduled task."""
        scheduler = TaskScheduler()
        task = await scheduler.add_task("Test", "test", ScheduleInterval.HOURLY)

        result = await scheduler.remove_task(task.id)

        assert result is True
        assert task.id not in scheduler._tasks

    @pytest.mark.asyncio
    async def test_remove_nonexistent_task(self):
        """Test removing non-existent task returns False."""
        scheduler = TaskScheduler()

        result = await scheduler.remove_task("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_enable_task(self):
        """Test enabling a disabled task."""
        scheduler = TaskScheduler()
        task = await scheduler.add_task(
            "Test", "test", ScheduleInterval.HOURLY, enabled=False
        )

        enabled = await scheduler.enable_task(task.id)

        assert enabled is not None
        assert enabled.enabled is True
        assert enabled.next_run is not None

    @pytest.mark.asyncio
    async def test_enable_nonexistent_task(self):
        """Test enabling non-existent task returns None."""
        scheduler = TaskScheduler()

        result = await scheduler.enable_task("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_disable_task(self):
        """Test disabling an enabled task."""
        scheduler = TaskScheduler()
        task = await scheduler.add_task("Test", "test", ScheduleInterval.HOURLY)

        disabled = await scheduler.disable_task(task.id)

        assert disabled is not None
        assert disabled.enabled is False

    @pytest.mark.asyncio
    async def test_disable_nonexistent_task(self):
        """Test disabling non-existent task returns None."""
        scheduler = TaskScheduler()

        result = await scheduler.disable_task("nonexistent")

        assert result is None


# =============================================================================
# Task Query Tests
# =============================================================================


class TestTaskQueries:
    """Tests for task query methods."""

    @pytest.mark.asyncio
    async def test_get_task(self):
        """Test getting a task by ID."""
        scheduler = TaskScheduler()
        task = await scheduler.add_task("Test", "test", ScheduleInterval.HOURLY)

        found = scheduler.get_task(task.id)

        assert found is task

    def test_get_task_not_found(self):
        """Test getting non-existent task returns None."""
        scheduler = TaskScheduler()

        found = scheduler.get_task("nonexistent")

        assert found is None

    @pytest.mark.asyncio
    async def test_get_all_tasks(self):
        """Test getting all tasks."""
        scheduler = TaskScheduler()
        await scheduler.add_task("Task1", "test", ScheduleInterval.HOURLY)
        await scheduler.add_task("Task2", "test", ScheduleInterval.DAILY)

        tasks = scheduler.get_all_tasks()

        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_get_enabled_tasks(self):
        """Test getting only enabled tasks."""
        scheduler = TaskScheduler()
        await scheduler.add_task("Enabled", "test", ScheduleInterval.HOURLY)
        await scheduler.add_task(
            "Disabled", "test", ScheduleInterval.DAILY, enabled=False
        )

        enabled = scheduler.get_enabled_tasks()

        assert len(enabled) == 1
        assert enabled[0].name == "Enabled"


# =============================================================================
# Scheduler Control Tests
# =============================================================================


class TestSchedulerControl:
    """Tests for scheduler start/stop control."""

    @pytest.mark.asyncio
    async def test_start_scheduler(self):
        """Test starting the scheduler."""
        scheduler = TaskScheduler(check_interval=0.1)

        await scheduler.start()
        await asyncio.sleep(0.05)

        assert scheduler._running is True
        assert scheduler._scheduler_task is not None

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting already running scheduler."""
        scheduler = TaskScheduler(check_interval=0.1)

        await scheduler.start()
        await scheduler.start()  # Should not error

        assert scheduler._running is True

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        scheduler = TaskScheduler(check_interval=0.1)
        await scheduler.start()

        await scheduler.stop()

        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stopping scheduler that's not running."""
        scheduler = TaskScheduler()

        await scheduler.stop()  # Should not error

        assert scheduler._running is False


# =============================================================================
# Task Execution Tests
# =============================================================================


class TestTaskExecution:
    """Tests for task execution."""

    @pytest.mark.asyncio
    async def test_run_task_now(self):
        """Test running a task immediately."""
        scheduler = TaskScheduler()
        executed = []

        async def test_handler(payload):
            executed.append(payload)

        scheduler.register_handler("test", test_handler)
        task = await scheduler.add_task("Test", "test", ScheduleInterval.HOURLY)

        result = await scheduler.run_task_now(task.id)

        assert result is True
        assert len(executed) == 1

    @pytest.mark.asyncio
    async def test_run_task_now_nonexistent(self):
        """Test running non-existent task returns False."""
        scheduler = TaskScheduler()

        result = await scheduler.run_task_now("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_execute_task_no_handler(self):
        """Test executing task with no registered handler."""
        scheduler = TaskScheduler()
        task = await scheduler.add_task("Test", "unknown_type", ScheduleInterval.HOURLY)

        await scheduler._execute_task(task)

        assert task.error_count == 1
        assert "No handler" in task.last_error

    @pytest.mark.asyncio
    async def test_execute_task_handler_error(self):
        """Test executing task when handler raises error."""
        scheduler = TaskScheduler()

        async def failing_handler(payload):
            raise ValueError("Handler error")

        scheduler.register_handler("fail", failing_handler)
        task = await scheduler.add_task("Test", "fail", ScheduleInterval.HOURLY)

        await scheduler._execute_task(task)

        assert task.error_count == 1
        assert "Handler error" in task.last_error

    @pytest.mark.asyncio
    async def test_execute_task_updates_stats(self):
        """Test task execution updates run count."""
        scheduler = TaskScheduler()
        call_count = [0]

        async def counting_handler(payload):
            call_count[0] += 1

        scheduler.register_handler("count", counting_handler)
        task = await scheduler.add_task("Test", "count", ScheduleInterval.HOURLY)

        await scheduler._execute_task(task)

        assert task.run_count == 1
        assert task.last_run is not None
        assert task.last_error is None


# =============================================================================
# Statistics Tests
# =============================================================================


class TestSchedulerStats:
    """Tests for scheduler statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        """Test stats on empty scheduler."""
        scheduler = TaskScheduler()

        stats = await scheduler.get_stats()

        assert stats["running"] is False
        assert stats["total_tasks"] == 0
        assert stats["enabled_tasks"] == 0
        assert stats["disabled_tasks"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_tasks(self):
        """Test stats with tasks."""
        scheduler = TaskScheduler()
        await scheduler.add_task("Task1", "test", ScheduleInterval.HOURLY)
        await scheduler.add_task("Task2", "test", ScheduleInterval.DAILY, enabled=False)

        async def handler(p):
            pass

        scheduler.register_handler("test", handler)

        stats = await scheduler.get_stats()

        assert stats["total_tasks"] == 2
        assert stats["enabled_tasks"] == 1
        assert stats["disabled_tasks"] == 1
        assert "test" in stats["registered_handlers"]


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSchedulerSingleton:
    """Tests for scheduler singleton pattern."""

    def test_get_scheduler_returns_instance(self):
        """Test get_scheduler returns an instance."""
        import app.services.batch.scheduler as module

        module._scheduler = None

        scheduler = get_scheduler()
        assert isinstance(scheduler, TaskScheduler)

    def test_get_scheduler_returns_same_instance(self):
        """Test get_scheduler returns cached singleton."""
        import app.services.batch.scheduler as module

        module._scheduler = None

        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()
        assert scheduler1 is scheduler2
