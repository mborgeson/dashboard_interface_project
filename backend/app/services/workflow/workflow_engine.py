"""
Workflow Engine

Core execution engine for workflow automation.
"""

import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from .step_handlers import (
    StepHandlerRegistry,
    register_default_actions,
)
from .workflow_models import (
    ApprovalRequest,
    StepDefinition,
    StepExecution,
    StepStatus,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
)


class WorkflowEngine:
    """
    Core workflow execution engine.

    Features:
    - Workflow definition management
    - Instance creation and execution
    - Step handler coordination
    - State persistence
    - Approval workflow support
    - Event callbacks
    """

    def __init__(self):
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._instances: dict[str, WorkflowInstance] = {}
        self._approval_requests: dict[str, ApprovalRequest] = {}
        self._handler_registry = StepHandlerRegistry()
        self._event_callbacks: dict[str, list[Callable]] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._redis_client: Any = None
        self._use_redis = False

        # Register default actions
        register_default_actions(self._handler_registry.get_action_handler())

    async def initialize(self, redis_url: str | None = None) -> None:
        """
        Initialize the workflow engine.

        Args:
            redis_url: Optional Redis URL for persistence
        """
        if redis_url:
            try:
                from app.services.redis_service import get_redis_service

                self._redis_client = (await get_redis_service()).client
                if self._redis_client:
                    self._use_redis = True
                    await self._load_from_redis()
                    logger.info("Workflow engine initialized with Redis persistence")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")

        logger.info("Workflow engine initialized")

    async def _load_from_redis(self) -> None:
        """Load workflows and instances from Redis."""
        if not self._redis_client:
            return

        try:
            # Load definitions
            def_ids = await self._redis_client.smembers("workflow:definitions")
            for def_id in def_ids:
                data = await self._redis_client.hgetall(f"workflow:def:{def_id}")
                if data:
                    definition = WorkflowDefinition.from_dict(data)
                    self._definitions[definition.id] = definition

            # Load active instances
            inst_ids = await self._redis_client.smembers("workflow:instances:active")
            for inst_id in inst_ids:
                data = await self._redis_client.hgetall(f"workflow:inst:{inst_id}")
                if data:
                    instance = WorkflowInstance.from_dict(data)
                    self._instances[instance.id] = instance

            logger.info(
                f"Loaded {len(self._definitions)} definitions and "
                f"{len(self._instances)} instances from Redis"
            )
        except Exception as e:
            logger.error(f"Failed to load from Redis: {e}")

    async def _save_definition(self, definition: WorkflowDefinition) -> None:
        """Save workflow definition to Redis."""
        if not self._redis_client:
            return

        try:
            await self._redis_client.hset(
                f"workflow:def:{definition.id}",
                mapping=definition.to_dict(),
            )
            await self._redis_client.sadd("workflow:definitions", definition.id)
        except Exception as e:
            logger.error(f"Failed to save definition: {e}")

    async def _save_instance(self, instance: WorkflowInstance) -> None:
        """Save workflow instance to Redis."""
        if not self._redis_client:
            return

        try:
            await self._redis_client.hset(
                f"workflow:inst:{instance.id}",
                mapping=instance.to_dict(),
            )
            if instance.status in [
                WorkflowStatus.PENDING,
                WorkflowStatus.RUNNING,
                WorkflowStatus.PAUSED,
            ]:
                await self._redis_client.sadd("workflow:instances:active", instance.id)
            else:
                await self._redis_client.srem("workflow:instances:active", instance.id)
                await self._redis_client.sadd(
                    "workflow:instances:completed", instance.id
                )
        except Exception as e:
            logger.error(f"Failed to save instance: {e}")

    # =========================================================================
    # Definition Management
    # =========================================================================

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        """
        Register a workflow definition.

        Args:
            definition: Workflow definition to register
        """
        self._definitions[definition.id] = definition
        logger.info(f"Registered workflow: {definition.name} ({definition.id})")

        if self._use_redis:
            asyncio.create_task(self._save_definition(definition))

    def unregister_workflow(self, workflow_id: str) -> bool:
        """
        Unregister a workflow definition.

        Args:
            workflow_id: Workflow ID to unregister

        Returns:
            True if unregistered successfully
        """
        if workflow_id in self._definitions:
            del self._definitions[workflow_id]
            logger.info(f"Unregistered workflow: {workflow_id}")
            return True
        return False

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Get a workflow definition by ID."""
        return self._definitions.get(workflow_id)

    def list_workflows(self) -> list[WorkflowDefinition]:
        """List all registered workflow definitions."""
        return list(self._definitions.values())

    # =========================================================================
    # Instance Management
    # =========================================================================

    async def create_instance(
        self,
        workflow_id: str,
        variables: dict[str, Any] | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        """
        Create a new workflow instance.

        Args:
            workflow_id: ID of the workflow definition
            variables: Initial workflow variables
            created_by: User creating the instance
            metadata: Additional metadata

        Returns:
            Created workflow instance or None
        """
        definition = self._definitions.get(workflow_id)
        if not definition:
            logger.error(f"Workflow not found: {workflow_id}")
            return None

        # Merge default variables with provided ones
        merged_vars = {**definition.variables, **(variables or {})}

        instance = WorkflowInstance(
            workflow_id=workflow_id,
            workflow_name=definition.name,
            variables=merged_vars,
            created_by=created_by,
            metadata=metadata or {},
        )

        # Initialize step executions
        for step in definition.steps:
            instance.step_executions[step.id] = StepExecution(step_id=step.id)

        self._instances[instance.id] = instance
        await self._save_instance(instance)
        await self._emit_event("instance_created", instance)

        logger.info(f"Created workflow instance: {instance.id} for {definition.name}")
        return instance

    async def start_instance(self, instance_id: str) -> bool:
        """
        Start executing a workflow instance.

        Args:
            instance_id: Instance ID to start

        Returns:
            True if started successfully
        """
        instance = self._instances.get(instance_id)
        if not instance:
            logger.error(f"Instance not found: {instance_id}")
            return False

        if instance.status not in [WorkflowStatus.PENDING, WorkflowStatus.PAUSED]:
            logger.warning(f"Cannot start instance in status {instance.status}")
            return False

        definition = self._definitions.get(instance.workflow_id)
        if not definition:
            logger.error(f"Workflow definition not found: {instance.workflow_id}")
            return False

        instance.status = WorkflowStatus.RUNNING
        instance.started_at = instance.started_at or datetime.now(UTC)
        instance.current_step = definition.start_step

        await self._save_instance(instance)
        await self._emit_event("instance_started", instance)

        # Start execution in background
        task = asyncio.create_task(self._execute_workflow(instance, definition))
        self._running_tasks[instance_id] = task

        logger.info(f"Started workflow instance: {instance_id}")
        return True

    async def pause_instance(self, instance_id: str) -> bool:
        """Pause a running workflow instance."""
        instance = self._instances.get(instance_id)
        if not instance or instance.status != WorkflowStatus.RUNNING:
            return False

        instance.status = WorkflowStatus.PAUSED
        await self._save_instance(instance)
        await self._emit_event("instance_paused", instance)

        logger.info(f"Paused workflow instance: {instance_id}")
        return True

    async def resume_instance(self, instance_id: str) -> bool:
        """Resume a paused workflow instance."""
        return await self.start_instance(instance_id)

    async def cancel_instance(self, instance_id: str) -> bool:
        """Cancel a workflow instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        if instance.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
            return False

        # Cancel running task
        task = self._running_tasks.pop(instance_id, None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.now(UTC)
        await self._save_instance(instance)
        await self._emit_event("instance_cancelled", instance)

        logger.info(f"Cancelled workflow instance: {instance_id}")
        return True

    def get_instance(self, instance_id: str) -> WorkflowInstance | None:
        """Get a workflow instance by ID."""
        return self._instances.get(instance_id)

    def list_instances(
        self,
        workflow_id: str | None = None,
        status: WorkflowStatus | None = None,
    ) -> list[WorkflowInstance]:
        """List workflow instances with optional filtering."""
        instances = list(self._instances.values())

        if workflow_id:
            instances = [i for i in instances if i.workflow_id == workflow_id]

        if status:
            instances = [i for i in instances if i.status == status]

        return instances

    # =========================================================================
    # Execution Engine
    # =========================================================================

    async def _execute_workflow(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition,
    ) -> None:
        """Execute a workflow instance."""
        try:
            while instance.status == WorkflowStatus.RUNNING and instance.current_step:
                step = definition.get_step(instance.current_step)
                if not step:
                    logger.error(f"Step not found: {instance.current_step}")
                    instance.status = WorkflowStatus.FAILED
                    break

                # Execute step
                result = await self._execute_step(instance, step)

                # Handle result
                if result.get("waiting"):
                    # Step is waiting (e.g., for approval)
                    logger.info(f"Step {step.id} is waiting")
                    break

                if not result.get("success"):
                    # Handle error based on step configuration
                    if step.on_error == "skip":
                        execution = instance.get_step_execution(step.id)
                        if execution is not None:
                            execution.status = StepStatus.SKIPPED
                    elif (
                        step.on_error == "retry"
                        and result.get("retries", 0) < step.retry_count
                    ):
                        # Will retry
                        continue
                    else:
                        instance.status = WorkflowStatus.FAILED
                        break

                # Determine next step
                next_step = result.get("next_step")

                # Handle parallel execution
                if result.get("parallel"):
                    # Execute branches in parallel
                    branches = result.get("branches", [])
                    await self._execute_parallel_branches(
                        instance, definition, branches
                    )
                    next_step = result.get("next_step")

                instance.current_step = next_step

                if not next_step:
                    # No more steps - workflow completed
                    instance.status = WorkflowStatus.COMPLETED
                    instance.completed_at = datetime.now(UTC)

                await self._save_instance(instance)

            # Final status update
            if instance.status == WorkflowStatus.COMPLETED:
                await self._emit_event("instance_completed", instance)
                logger.info(f"Workflow instance completed: {instance.id}")
            elif instance.status == WorkflowStatus.FAILED:
                await self._emit_event("instance_failed", instance)
                logger.error(f"Workflow instance failed: {instance.id}")

        except asyncio.CancelledError:
            logger.info(f"Workflow execution cancelled: {instance.id}")
            raise
        except Exception as e:
            logger.exception(f"Workflow execution error: {e}")
            instance.status = WorkflowStatus.FAILED
            instance.completed_at = datetime.now(UTC)
            await self._save_instance(instance)
            await self._emit_event("instance_failed", instance)

        finally:
            self._running_tasks.pop(instance.id, None)

    async def _execute_step(
        self,
        instance: WorkflowInstance,
        step: StepDefinition,
    ) -> dict[str, Any]:
        """Execute a single workflow step."""
        execution = instance.get_step_execution(step.id)
        if execution is None:
            return {"success": False, "error": f"No execution found for step {step.id}"}
        execution.status = StepStatus.RUNNING
        execution.started_at = datetime.now(UTC)

        await self._emit_event("step_started", instance, step)

        try:
            handler = self._handler_registry.get(step.step_type)
            if not handler:
                raise ValueError(f"No handler for step type: {step.step_type}")

            # Execute with timeout
            result = await asyncio.wait_for(
                handler.execute(step, instance, {}),
                timeout=step.timeout_seconds,
            )

            if result.get("success"):
                execution.status = StepStatus.COMPLETED
                execution.result = result.get("result")
            elif result.get("waiting"):
                execution.status = StepStatus.WAITING
            else:
                execution.status = StepStatus.FAILED
                execution.error = result.get("error")

            execution.completed_at = datetime.now(UTC)
            await self._emit_event("step_completed", instance, step, result)

            return result

        except TimeoutError:
            execution.status = StepStatus.FAILED
            execution.error = f"Step timed out after {step.timeout_seconds} seconds"
            execution.completed_at = datetime.now(UTC)
            await self._emit_event("step_failed", instance, step)
            return {"success": False, "error": execution.error}

        except Exception as e:
            execution.status = StepStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(UTC)
            execution.retries += 1
            await self._emit_event("step_failed", instance, step)
            return {"success": False, "error": str(e), "retries": execution.retries}

    async def _execute_parallel_branches(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition,
        branches: list[str],
    ) -> None:
        """Execute parallel branches concurrently."""

        async def execute_branch(branch_step_id: str) -> None:
            step = definition.get_step(branch_step_id)
            if step:
                await self._execute_step(instance, step)

        await asyncio.gather(*[execute_branch(b) for b in branches])

    # =========================================================================
    # Approval Handling
    # =========================================================================

    async def approve_step(
        self,
        instance_id: str,
        step_id: str,
        approved_by: str,
        comment: str | None = None,
    ) -> bool:
        """
        Approve a waiting step.

        Args:
            instance_id: Workflow instance ID
            step_id: Step ID waiting for approval
            approved_by: User approving
            comment: Optional comment

        Returns:
            True if approved successfully
        """
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        execution = instance.get_step_execution(step_id)
        if not execution or execution.status != StepStatus.WAITING:
            return False

        definition = self._definitions.get(instance.workflow_id)
        if not definition:
            return False

        step = definition.get_step(step_id)
        if not step:
            return False

        # Update execution
        execution.status = StepStatus.COMPLETED
        execution.completed_at = datetime.now(UTC)
        execution.result = {"approved_by": approved_by, "comment": comment}

        # Set next step
        instance.current_step = step.next_steps[0] if step.next_steps else None

        await self._save_instance(instance)
        await self._emit_event("step_approved", instance, step)

        # Resume workflow if it was paused
        if instance.status == WorkflowStatus.RUNNING and instance.current_step:
            asyncio.create_task(self._execute_workflow(instance, definition))

        logger.info(f"Step {step_id} approved by {approved_by}")
        return True

    async def reject_step(
        self,
        instance_id: str,
        step_id: str,
        rejected_by: str,
        comment: str | None = None,
    ) -> bool:
        """Reject a waiting step, failing the workflow."""
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        execution = instance.get_step_execution(step_id)
        if not execution or execution.status != StepStatus.WAITING:
            return False

        execution.status = StepStatus.FAILED
        execution.completed_at = datetime.now(UTC)
        execution.error = f"Rejected by {rejected_by}: {comment or 'No reason given'}"

        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.now(UTC)

        await self._save_instance(instance)
        await self._emit_event("step_rejected", instance)

        logger.info(f"Step {step_id} rejected by {rejected_by}")
        return True

    # =========================================================================
    # Event System
    # =========================================================================

    def on_event(self, event: str, callback: Callable) -> None:
        """Register an event callback."""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)

    async def _emit_event(self, event: str, *args, **kwargs) -> None:
        """Emit an event to registered callbacks."""
        callbacks = self._event_callbacks.get(event, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Event callback error: {e}")

    # =========================================================================
    # Handler Registration
    # =========================================================================

    def register_action(self, name: str, handler: Callable) -> None:
        """Register a custom action handler."""
        action_handler = self._handler_registry.get_action_handler()
        action_handler.register_action(name, handler)

    def register_notification_channel(self, name: str, sender: Callable) -> None:
        """Register a notification channel."""
        notification_handler = self._handler_registry.get_notification_handler()
        notification_handler.register_channel(name, sender)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get workflow engine statistics."""
        instances = list(self._instances.values())

        status_counts = {}
        for status in WorkflowStatus:
            status_counts[status.value] = sum(
                1 for i in instances if i.status == status
            )

        return {
            "total_definitions": len(self._definitions),
            "total_instances": len(instances),
            "active_instances": len(self._running_tasks),
            "status_counts": status_counts,
            "use_redis": self._use_redis,
        }


# Singleton instance
_workflow_engine: WorkflowEngine | None = None


def get_workflow_engine() -> WorkflowEngine:
    """Get or create the workflow engine singleton."""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
