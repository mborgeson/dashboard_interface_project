"""
Task Executor

Processes jobs from the queue with configurable worker pools.
Supports task registration, timeout handling, and graceful shutdown.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional

from loguru import logger

from .job_queue import Job, JobQueue, JobStatus, get_job_queue


# Type alias for async task handlers
TaskHandler = Callable[[Job], Coroutine[Any, Any, Any]]


class TaskExecutor:
    """
    Executes jobs from the queue using registered task handlers.

    Features:
    - Configurable worker pool size
    - Task type registration
    - Timeout enforcement
    - Graceful shutdown
    - Error handling and retry coordination
    """

    def __init__(self, max_workers: int = 4, poll_interval: float = 1.0):
        """
        Initialize task executor.

        Args:
            max_workers: Maximum concurrent workers
            poll_interval: Queue polling interval in seconds
        """
        self._max_workers = max_workers
        self._poll_interval = poll_interval
        self._handlers: Dict[str, TaskHandler] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._job_queue: Optional[JobQueue] = None
        self._active_jobs: Dict[str, asyncio.Task] = {}

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Task type identifier
            handler: Async function to handle the task
        """
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    def unregister_handler(self, task_type: str) -> None:
        """
        Unregister a task handler.

        Args:
            task_type: Task type identifier
        """
        if task_type in self._handlers:
            del self._handlers[task_type]
            logger.info(f"Unregistered handler for task type: {task_type}")

    async def start(self, job_queue: Optional[JobQueue] = None) -> None:
        """
        Start the executor with worker pool.

        Args:
            job_queue: Job queue to process (uses singleton if not provided)
        """
        if self._running:
            logger.warning("Task executor already running")
            return

        self._job_queue = job_queue or get_job_queue()
        self._running = True
        self._shutdown_event.clear()

        # Start worker tasks
        for i in range(self._max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Task executor started with {self._max_workers} workers")

    async def stop(self, timeout: float = 30.0) -> None:
        """
        Stop the executor gracefully.

        Args:
            timeout: Maximum time to wait for workers to finish
        """
        if not self._running:
            return

        logger.info("Stopping task executor...")
        self._running = False
        self._shutdown_event.set()

        # Cancel active jobs
        for job_id, task in list(self._active_jobs.items()):
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Wait for workers to finish
        if self._workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for workers, cancelling...")
                for worker in self._workers:
                    worker.cancel()

        self._workers.clear()
        self._active_jobs.clear()
        logger.info("Task executor stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop that processes jobs from the queue.

        Args:
            worker_id: Worker identifier for logging
        """
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                # Check for shutdown
                if self._shutdown_event.is_set():
                    break

                # Try to get a job
                job = await self._job_queue.dequeue()
                if job:
                    await self._execute_job(job, worker_id)
                else:
                    # No job available, wait and retry
                    await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(self._poll_interval)

        logger.debug(f"Worker {worker_id} stopped")

    async def _execute_job(self, job: Job, worker_id: int) -> None:
        """
        Execute a single job.

        Args:
            job: Job to execute
            worker_id: Worker identifier
        """
        handler = self._handlers.get(job.task_type)
        if not handler:
            logger.error(f"No handler for task type: {job.task_type}")
            await self._job_queue.fail(job.id, f"No handler for task type: {job.task_type}")
            return

        logger.info(f"Worker {worker_id} executing job: {job.id} ({job.task_type})")

        try:
            # Create execution task with timeout
            task = asyncio.create_task(handler(job))
            self._active_jobs[job.id] = task

            # Execute with timeout
            result = await asyncio.wait_for(task, timeout=job.timeout)

            # Mark as completed
            await self._job_queue.complete(job.id, result)
            logger.info(f"Worker {worker_id} completed job: {job.id}")

        except asyncio.TimeoutError:
            error_msg = f"Job timed out after {job.timeout} seconds"
            logger.error(f"Worker {worker_id} timeout on job: {job.id}")
            await self._job_queue.fail(job.id, error_msg)

        except asyncio.CancelledError:
            logger.warning(f"Worker {worker_id} job cancelled: {job.id}")
            await self._job_queue.fail(job.id, "Job cancelled")
            raise

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Worker {worker_id} error on job {job.id}: {e}")
            await self._job_queue.fail(job.id, error_msg)

        finally:
            self._active_jobs.pop(job.id, None)

    async def execute_immediate(
        self,
        task_type: str,
        payload: Dict[str, Any],
        timeout: int = 300,
    ) -> Any:
        """
        Execute a task immediately without queueing.

        Args:
            task_type: Task type to execute
            payload: Task parameters
            timeout: Execution timeout

        Returns:
            Task result

        Raises:
            ValueError: If no handler is registered
            asyncio.TimeoutError: If execution times out
        """
        handler = self._handlers.get(task_type)
        if not handler:
            raise ValueError(f"No handler for task type: {task_type}")

        # Create a temporary job for the handler
        job = Job(
            task_type=task_type,
            payload=payload,
            timeout=timeout,
        )

        return await asyncio.wait_for(handler(job), timeout=timeout)

    def get_registered_handlers(self) -> list[str]:
        """Get list of registered task types."""
        return list(self._handlers.keys())

    async def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            "running": self._running,
            "max_workers": self._max_workers,
            "active_workers": len(self._workers),
            "active_jobs": len(self._active_jobs),
            "registered_handlers": len(self._handlers),
            "handler_types": list(self._handlers.keys()),
        }


# Singleton instance
_task_executor: Optional[TaskExecutor] = None


def get_task_executor() -> TaskExecutor:
    """Get or create the task executor singleton."""
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
    return _task_executor


# =============================================================================
# Built-in Task Handlers
# =============================================================================

async def report_generation_handler(job: Job) -> Dict[str, Any]:
    """
    Handle report generation tasks.

    Expected payload:
        report_type: Type of report (property, deal, portfolio)
        entity_id: ID of the entity to report on
        format: Output format (pdf, excel)
        options: Additional report options
    """
    from app.services.pdf_service import get_pdf_service
    from app.services.export_service import get_export_service

    report_type = job.payload.get("report_type")
    entity_id = job.payload.get("entity_id")
    output_format = job.payload.get("format", "pdf")
    options = job.payload.get("options", {})

    logger.info(f"Generating {report_type} report for entity {entity_id}")

    # Generate report based on type and format
    if output_format == "pdf":
        pdf_service = get_pdf_service()
        # Report generation would be implemented here
        result = {"format": "pdf", "status": "generated"}
    else:
        export_service = get_export_service()
        # Excel export would be implemented here
        result = {"format": "excel", "status": "generated"}

    return {
        "report_type": report_type,
        "entity_id": entity_id,
        "format": output_format,
        "generated_at": datetime.utcnow().isoformat(),
        **result,
    }


async def data_export_handler(job: Job) -> Dict[str, Any]:
    """
    Handle data export tasks.

    Expected payload:
        export_type: Type of data to export
        filters: Query filters
        format: Output format
        destination: Export destination
    """
    export_type = job.payload.get("export_type")
    filters = job.payload.get("filters", {})
    output_format = job.payload.get("format", "csv")

    logger.info(f"Exporting {export_type} data in {output_format} format")

    # Export implementation would go here
    return {
        "export_type": export_type,
        "format": output_format,
        "record_count": 0,  # Would be actual count
        "exported_at": datetime.utcnow().isoformat(),
    }


async def data_import_handler(job: Job) -> Dict[str, Any]:
    """
    Handle data import tasks.

    Expected payload:
        import_type: Type of data to import
        source: Data source (file path or URL)
        options: Import options
    """
    import_type = job.payload.get("import_type")
    source = job.payload.get("source")
    options = job.payload.get("options", {})

    logger.info(f"Importing {import_type} data from {source}")

    # Import implementation would go here
    return {
        "import_type": import_type,
        "source": source,
        "record_count": 0,  # Would be actual count
        "imported_at": datetime.utcnow().isoformat(),
    }


async def email_notification_handler(job: Job) -> Dict[str, Any]:
    """
    Handle email notification tasks.

    Expected payload:
        to: Recipient email(s)
        template: Email template name
        context: Template context variables
    """
    from app.services.email_service import get_email_service

    to = job.payload.get("to")
    template = job.payload.get("template")
    context = job.payload.get("context", {})

    logger.info(f"Sending email notification: {template} to {to}")

    email_service = get_email_service()
    # Email sending would be implemented here

    return {
        "template": template,
        "recipients": to if isinstance(to, list) else [to],
        "sent_at": datetime.utcnow().isoformat(),
    }


def register_default_handlers(executor: TaskExecutor) -> None:
    """Register built-in task handlers."""
    executor.register_handler("report_generation", report_generation_handler)
    executor.register_handler("data_export", data_export_handler)
    executor.register_handler("data_import", data_import_handler)
    executor.register_handler("email_notification", email_notification_handler)
    logger.info("Default task handlers registered")
