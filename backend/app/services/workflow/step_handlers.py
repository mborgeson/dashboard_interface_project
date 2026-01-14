"""
Workflow Step Handlers

Built-in handlers for common workflow step types.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger

from .workflow_models import (
    StepDefinition,
    StepType,
    WorkflowInstance,
)


class StepHandler(ABC):
    """
    Base class for step handlers.

    Handlers process specific step types and return results
    that determine workflow progression.
    """

    @abstractmethod
    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute the step.

        Args:
            step: Step definition
            instance: Current workflow instance
            context: Execution context and variables

        Returns:
            Result dictionary with 'success', 'result', and optional 'next_step'
        """
        pass

    @property
    @abstractmethod
    def step_type(self) -> StepType:
        """Return the step type this handler processes."""
        pass


class ActionHandler(StepHandler):
    """
    Handler for action steps.

    Executes registered action functions based on the step handler name.
    """

    def __init__(self):
        self._actions: dict[str, Callable] = {}

    def register_action(
        self,
        name: str,
        action: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register an action function."""
        self._actions[name] = action
        logger.debug(f"Registered action handler: {name}")

    def unregister_action(self, name: str) -> None:
        """Unregister an action function."""
        self._actions.pop(name, None)

    @property
    def step_type(self) -> StepType:
        return StepType.ACTION

    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the action."""
        action = self._actions.get(step.handler)
        if not action:
            return {
                "success": False,
                "error": f"Action handler not found: {step.handler}",
            }

        try:
            result = await action(
                step_config=step.config,
                variables=instance.variables,
                context=context,
            )
            return {
                "success": True,
                "result": result,
                "next_step": step.next_steps[0] if step.next_steps else None,
            }
        except Exception as e:
            logger.exception(f"Action handler {step.handler} failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class ConditionHandler(StepHandler):
    """
    Handler for condition steps.

    Evaluates conditions to determine the next step.
    """

    def __init__(self):
        self._evaluators: dict[str, Callable] = {}

    def register_evaluator(
        self,
        name: str,
        evaluator: Callable[..., Coroutine[Any, Any, bool]],
    ) -> None:
        """Register a condition evaluator."""
        self._evaluators[name] = evaluator

    @property
    def step_type(self) -> StepType:
        return StepType.CONDITION

    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate the condition and determine next step."""
        try:
            # Get evaluator or use default expression evaluation
            evaluator = self._evaluators.get(step.handler)

            if evaluator:
                result = await evaluator(
                    condition=step.condition,
                    variables=instance.variables,
                    context=context,
                )
            else:
                # Default: evaluate condition as Python expression
                result = self._evaluate_expression(step.condition, instance.variables)

            # Determine next step based on result
            # Expecting next_steps to have [true_branch, false_branch]
            if len(step.next_steps) >= 2:
                next_step = step.next_steps[0] if result else step.next_steps[1]
            elif step.next_steps:
                next_step = step.next_steps[0] if result else None
            else:
                next_step = None

            return {
                "success": True,
                "result": result,
                "next_step": next_step,
            }
        except Exception as e:
            logger.exception(f"Condition evaluation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _evaluate_expression(
        self,
        expression: str | None,
        variables: dict[str, Any],
    ) -> bool:
        """
        Safely evaluate a condition expression.

        Uses AST-based parsing to prevent code injection attacks.
        Only allows safe comparison and logical operators.
        """
        import ast
        import operator

        if not expression:
            return True

        # Safe operators whitelist
        SAFE_OPERATORS = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
            ast.Is: operator.is_,
            ast.IsNot: operator.is_not,
            ast.And: lambda a, b: a and b,
            ast.Or: lambda a, b: a or b,
            ast.Not: operator.not_,
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def safe_eval_node(node: ast.AST) -> Any:
            """Recursively evaluate AST nodes safely."""
            if isinstance(node, ast.Expression):
                return safe_eval_node(node.body)
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                if node.id in variables:
                    return variables[node.id]
                elif node.id == "True":
                    return True
                elif node.id == "False":
                    return False
                elif node.id == "None":
                    return None
                else:
                    raise ValueError(f"Unknown variable: {node.id}")
            elif isinstance(node, ast.Compare):
                left = safe_eval_node(node.left)
                for op, comparator in zip(node.ops, node.comparators, strict=False):
                    op_func = SAFE_OPERATORS.get(type(op))
                    if op_func is None:
                        raise ValueError(f"Unsupported operator: {type(op).__name__}")
                    right = safe_eval_node(comparator)
                    if not op_func(left, right):
                        return False
                    left = right
                return True
            elif isinstance(node, ast.BoolOp):
                op_func = SAFE_OPERATORS.get(type(node.op))
                if op_func is None:
                    raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
                result = safe_eval_node(node.values[0])
                for value in node.values[1:]:
                    result = op_func(result, safe_eval_node(value))
                return result
            elif isinstance(node, ast.UnaryOp):
                if isinstance(node.op, ast.Not):
                    return not safe_eval_node(node.operand)
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            elif isinstance(node, ast.BinOp):
                op_func = SAFE_OPERATORS.get(type(node.op))
                if op_func is None:
                    raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
                return op_func(safe_eval_node(node.left), safe_eval_node(node.right))
            elif isinstance(node, ast.Subscript):
                value = safe_eval_node(node.value)
                index = safe_eval_node(node.slice)
                return value[index]
            elif isinstance(node, ast.Attribute):
                # Only allow attribute access on dict-like objects via get
                raise ValueError("Attribute access not allowed for security")
            else:
                raise ValueError(f"Unsupported AST node: {type(node).__name__}")

        try:
            tree = ast.parse(expression, mode='eval')
            return bool(safe_eval_node(tree))
        except Exception as e:
            logger.warning(f"Expression evaluation failed: {expression} - {e}")
            return False


class ApprovalHandler(StepHandler):
    """
    Handler for approval steps.

    Creates approval requests and waits for user action.
    """

    def __init__(self):
        self._approval_callback: Callable | None = None

    def set_approval_callback(
        self,
        callback: Callable[..., Coroutine[Any, Any, None]],
    ) -> None:
        """Set callback for creating approval requests."""
        self._approval_callback = callback

    @property
    def step_type(self) -> StepType:
        return StepType.APPROVAL

    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create approval request and return waiting status."""
        approvers = step.config.get("approvers", [])
        message = step.config.get("message", f"Approval required for {step.name}")

        if self._approval_callback:
            try:
                await self._approval_callback(
                    workflow_instance_id=instance.id,
                    step_id=step.id,
                    approvers=approvers,
                    message=message,
                    metadata=step.config,
                )
            except Exception as e:
                logger.exception(f"Failed to create approval request: {e}")

        return {
            "success": True,
            "result": {"waiting_for_approval": True, "approvers": approvers},
            "waiting": True,  # Signal that this step is waiting
        }


class DelayHandler(StepHandler):
    """
    Handler for delay steps.

    Waits for a specified duration before proceeding.
    """

    @property
    def step_type(self) -> StepType:
        return StepType.DELAY

    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Wait for specified duration."""
        duration = step.config.get("duration_seconds", 0)

        if duration > 0:
            logger.debug(f"Delay step waiting for {duration} seconds")
            await asyncio.sleep(duration)

        return {
            "success": True,
            "result": {"delayed_seconds": duration},
            "next_step": step.next_steps[0] if step.next_steps else None,
        }


class NotificationHandler(StepHandler):
    """
    Handler for notification steps.

    Sends notifications via registered channels.
    """

    def __init__(self):
        self._channels: dict[str, Callable] = {}

    def register_channel(
        self,
        name: str,
        sender: Callable[..., Coroutine[Any, Any, bool]],
    ) -> None:
        """Register a notification channel."""
        self._channels[name] = sender

    @property
    def step_type(self) -> StepType:
        return StepType.NOTIFICATION

    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Send notification via configured channel."""
        channel = step.config.get("channel", "email")
        recipients = step.config.get("recipients", [])
        message = step.config.get("message", "")
        subject = step.config.get("subject", "Workflow Notification")

        sender = self._channels.get(channel)
        if not sender:
            logger.warning(f"Notification channel not found: {channel}")
            return {
                "success": True,  # Don't fail workflow for missing channel
                "result": {
                    "sent": False,
                    "reason": f"Channel {channel} not configured",
                },
                "next_step": step.next_steps[0] if step.next_steps else None,
            }

        try:
            # Interpolate variables in message
            formatted_message = self._format_message(message, instance.variables)

            await sender(
                recipients=recipients,
                subject=subject,
                message=formatted_message,
                variables=instance.variables,
            )

            return {
                "success": True,
                "result": {"sent": True, "channel": channel, "recipients": recipients},
                "next_step": step.next_steps[0] if step.next_steps else None,
            }
        except Exception as e:
            logger.exception(f"Notification failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _format_message(self, message: str, variables: dict[str, Any]) -> str:
        """Format message with variable interpolation."""
        try:
            return message.format(**variables)
        except (KeyError, ValueError):
            return message


class ParallelHandler(StepHandler):
    """
    Handler for parallel execution steps.

    Executes multiple sub-steps concurrently.
    """

    @property
    def step_type(self) -> StepType:
        return StepType.PARALLEL

    async def execute(
        self,
        step: StepDefinition,
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute parallel steps.

        Note: This handler coordinates with the workflow engine
        to execute multiple branches concurrently.
        """
        branches = step.config.get("branches", [])

        return {
            "success": True,
            "result": {"parallel_branches": branches},
            "parallel": True,
            "branches": branches,
            "next_step": step.next_steps[0] if step.next_steps else None,
        }


class StepHandlerRegistry:
    """
    Registry for step handlers.

    Manages registration and lookup of handlers by step type.
    """

    def __init__(self):
        self._handlers: dict[StepType, StepHandler] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default handlers."""
        self._handlers[StepType.ACTION] = ActionHandler()
        self._handlers[StepType.CONDITION] = ConditionHandler()
        self._handlers[StepType.APPROVAL] = ApprovalHandler()
        self._handlers[StepType.DELAY] = DelayHandler()
        self._handlers[StepType.NOTIFICATION] = NotificationHandler()
        self._handlers[StepType.PARALLEL] = ParallelHandler()

    def register(self, handler: StepHandler) -> None:
        """Register a custom handler."""
        self._handlers[handler.step_type] = handler

    def get(self, step_type: StepType) -> StepHandler | None:
        """Get handler for step type."""
        return self._handlers.get(step_type)

    def get_action_handler(self) -> ActionHandler:
        """Get the action handler for registering actions."""
        return self._handlers[StepType.ACTION]

    def get_condition_handler(self) -> ConditionHandler:
        """Get the condition handler for registering evaluators."""
        return self._handlers[StepType.CONDITION]

    def get_notification_handler(self) -> NotificationHandler:
        """Get the notification handler for registering channels."""
        return self._handlers[StepType.NOTIFICATION]

    def get_approval_handler(self) -> ApprovalHandler:
        """Get the approval handler for setting callbacks."""
        return self._handlers[StepType.APPROVAL]


# =============================================================================
# Built-in Action Handlers
# =============================================================================


async def log_action(
    step_config: dict[str, Any],
    variables: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Log a message."""
    message = step_config.get("message", "Log action executed")
    level = step_config.get("level", "info")

    # Format message with variables
    try:
        formatted = message.format(**variables)
    except (KeyError, ValueError):
        formatted = message

    getattr(logger, level, logger.info)(formatted)

    return {"logged": True, "message": formatted}


async def set_variable_action(
    step_config: dict[str, Any],
    variables: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Set a workflow variable."""
    name = step_config.get("name")
    value = step_config.get("value")

    if name:
        variables[name] = value
        return {"set": True, "name": name, "value": value}
    return {"set": False, "error": "No variable name provided"}


async def http_request_action(
    step_config: dict[str, Any],
    variables: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Make an HTTP request."""
    import contextlib

    import aiohttp

    url = step_config.get("url", "")
    method = step_config.get("method", "GET").upper()
    headers = step_config.get("headers", {})
    body = step_config.get("body")
    timeout = step_config.get("timeout", 30)

    # Format URL with variables
    with contextlib.suppress(KeyError, ValueError):
        url = url.format(**variables)

    async with (
        aiohttp.ClientSession() as session,
        session.request(
            method,
            url,
            headers=headers,
            json=body if body else None,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response,
    ):
        result = {
            "status": response.status,
            "headers": dict(response.headers),
        }
        try:
            result["body"] = await response.json()
        except Exception:
            result["body"] = await response.text()

        return result


async def transform_data_action(
    step_config: dict[str, Any],
    variables: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Transform data using a mapping."""
    source = step_config.get("source")
    target = step_config.get("target")
    mapping = step_config.get("mapping", {})

    source_data = variables.get(source, {})
    transformed = {}

    for target_key, source_key in mapping.items():
        if isinstance(source_key, str) and source_key.startswith("$"):
            # Reference to variable
            transformed[target_key] = variables.get(source_key[1:])
        else:
            # Direct mapping
            transformed[target_key] = source_data.get(source_key)

    variables[target] = transformed
    return {"transformed": True, "target": target, "data": transformed}


def register_default_actions(handler: ActionHandler) -> None:
    """Register default action handlers."""
    handler.register_action("log", log_action)
    handler.register_action("set_variable", set_variable_action)
    handler.register_action("http_request", http_request_action)
    handler.register_action("transform_data", transform_data_action)
    logger.info("Default workflow actions registered")
