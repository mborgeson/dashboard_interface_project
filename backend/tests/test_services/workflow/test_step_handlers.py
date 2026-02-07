"""Tests for workflow step handlers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.workflow.step_handlers import (
    ActionHandler,
    ConditionHandler,
    NotificationHandler,
    ParallelHandler,
)
from app.services.workflow.workflow_models import (
    StepDefinition,
    StepType,
    WorkflowInstance,
    WorkflowStatus,
)

# =============================================================================
# ActionHandler Tests
# =============================================================================


class TestActionHandler:
    """Tests for ActionHandler."""

    def test_initialization(self):
        """Test ActionHandler initialization."""
        handler = ActionHandler()
        assert handler._actions == {}

    def test_step_type(self):
        """Test step_type property returns ACTION."""
        handler = ActionHandler()
        assert handler.step_type == StepType.ACTION

    def test_register_action(self):
        """Test registering an action."""
        handler = ActionHandler()

        async def my_action(**kwargs):
            pass

        handler.register_action("my_action", my_action)
        assert "my_action" in handler._actions

    def test_unregister_action(self):
        """Test unregistering an action."""
        handler = ActionHandler()

        async def my_action(**kwargs):
            pass

        handler.register_action("test", my_action)
        assert "test" in handler._actions

        handler.unregister_action("test")
        assert "test" not in handler._actions

    def test_unregister_nonexistent_action(self):
        """Test unregistering non-existent action doesn't error."""
        handler = ActionHandler()
        handler.unregister_action("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful action execution."""
        handler = ActionHandler()

        async def success_action(**kwargs):
            return {"message": "success"}

        handler.register_action("success", success_action)

        step = StepDefinition(
            id="step1",
            name="Test Step",
            step_type=StepType.ACTION,
            handler="success",
            config={"key": "value"},
            next_steps=["step2"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="step1",
            status=WorkflowStatus.RUNNING,
            variables={"var": "test"},
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"] == {"message": "success"}
        assert result["next_step"] == "step2"

    @pytest.mark.asyncio
    async def test_execute_no_handler(self):
        """Test execution with no registered handler."""
        handler = ActionHandler()

        step = StepDefinition(
            id="step1",
            name="Test Step",
            step_type=StepType.ACTION,
            handler="nonexistent",
            config={},
            next_steps=[],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="step1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_handler_error(self):
        """Test execution when handler raises error."""
        handler = ActionHandler()

        async def error_action(**kwargs):
            raise ValueError("Action failed")

        handler.register_action("error", error_action)

        step = StepDefinition(
            id="step1",
            name="Test Step",
            step_type=StepType.ACTION,
            handler="error",
            config={},
            next_steps=[],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="step1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is False
        assert "Action failed" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_no_next_steps(self):
        """Test execution with no next steps."""
        handler = ActionHandler()

        async def action(**kwargs):
            return {"done": True}

        handler.register_action("final", action)

        step = StepDefinition(
            id="step1",
            name="Final Step",
            step_type=StepType.ACTION,
            handler="final",
            config={},
            next_steps=[],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="step1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["next_step"] is None


# =============================================================================
# ConditionHandler Tests
# =============================================================================


class TestConditionHandler:
    """Tests for ConditionHandler."""

    def test_initialization(self):
        """Test ConditionHandler initialization."""
        handler = ConditionHandler()
        assert handler._evaluators == {}

    def test_step_type(self):
        """Test step_type property returns CONDITION."""
        handler = ConditionHandler()
        assert handler.step_type == StepType.CONDITION

    def test_register_evaluator(self):
        """Test registering an evaluator."""
        handler = ConditionHandler()

        async def my_evaluator(**kwargs):
            return True

        handler.register_evaluator("my_eval", my_evaluator)
        assert "my_eval" in handler._evaluators

    @pytest.mark.asyncio
    async def test_execute_with_evaluator_true(self):
        """Test condition execution when evaluator returns True."""
        handler = ConditionHandler()

        async def true_evaluator(**kwargs):
            return True

        handler.register_evaluator("check", true_evaluator)

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="check",
            config={"true_step": "on_true", "false_step": "on_false"},
            next_steps=["on_true", "on_false"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"] is True
        assert result["next_step"] == "on_true"

    @pytest.mark.asyncio
    async def test_execute_with_evaluator_false(self):
        """Test condition execution when evaluator returns False."""
        handler = ConditionHandler()

        async def false_evaluator(**kwargs):
            return False

        handler.register_evaluator("check_false", false_evaluator)

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="check_false",
            config={"true_step": "on_true", "false_step": "on_false"},
            next_steps=["on_true", "on_false"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"] is False
        assert result["next_step"] == "on_false"

    @pytest.mark.asyncio
    async def test_execute_default_expression_true(self):
        """Test condition with default expression evaluation returning True."""
        handler = ConditionHandler()

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="unknown",  # No registered evaluator
            config={},
            next_steps=["on_true", "on_false"],
            condition="value > 10",
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
            variables={"value": 15},
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"] is True
        assert result["next_step"] == "on_true"

    @pytest.mark.asyncio
    async def test_execute_default_expression_false(self):
        """Test condition with default expression evaluation returning False."""
        handler = ConditionHandler()

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="unknown",
            config={},
            next_steps=["on_true", "on_false"],
            condition="value > 100",
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
            variables={"value": 50},
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"] is False
        assert result["next_step"] == "on_false"

    @pytest.mark.asyncio
    async def test_execute_single_next_step_true(self):
        """Test condition with single next step when true."""
        handler = ConditionHandler()

        async def true_eval(**kwargs):
            return True

        handler.register_evaluator("check", true_eval)

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="check",
            config={},
            next_steps=["only_step"],  # Single next step
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["next_step"] == "only_step"

    @pytest.mark.asyncio
    async def test_execute_single_next_step_false(self):
        """Test condition with single next step when false."""
        handler = ConditionHandler()

        async def false_eval(**kwargs):
            return False

        handler.register_evaluator("check", false_eval)

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="check",
            config={},
            next_steps=["only_step"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["next_step"] is None

    @pytest.mark.asyncio
    async def test_execute_no_next_steps(self):
        """Test condition with no next steps."""
        handler = ConditionHandler()

        async def check_eval(**kwargs):
            return True

        handler.register_evaluator("check", check_eval)

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="check",
            config={},
            next_steps=[],  # No next steps
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["next_step"] is None

    @pytest.mark.asyncio
    async def test_execute_evaluator_error(self):
        """Test condition when evaluator raises an error."""
        handler = ConditionHandler()

        async def error_eval(**kwargs):
            raise ValueError("Evaluation failed")

        handler.register_evaluator("error_check", error_eval)

        step = StepDefinition(
            id="cond1",
            name="Condition Step",
            step_type=StepType.CONDITION,
            handler="error_check",
            config={},
            next_steps=["on_true", "on_false"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="cond1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is False
        assert "Evaluation failed" in result["error"]

    def test_evaluate_expression_none(self):
        """Test _evaluate_expression with None returns True."""
        handler = ConditionHandler()
        result = handler._evaluate_expression(None, {})
        assert result is True

    def test_evaluate_expression_empty_string(self):
        """Test _evaluate_expression with empty string returns True."""
        handler = ConditionHandler()
        result = handler._evaluate_expression("", {})
        assert result is True

    def test_evaluate_expression_simple_comparison(self):
        """Test _evaluate_expression with simple comparison."""
        handler = ConditionHandler()
        result = handler._evaluate_expression("x > 5", {"x": 10})
        assert result is True

    def test_evaluate_expression_invalid(self):
        """Test _evaluate_expression with invalid expression returns False."""
        handler = ConditionHandler()
        result = handler._evaluate_expression("invalid.attr.access", {})
        assert result is False


# =============================================================================
# NotificationHandler Tests
# =============================================================================


class TestNotificationHandler:
    """Tests for NotificationHandler."""

    def test_initialization(self):
        """Test NotificationHandler initialization."""
        handler = NotificationHandler()
        assert handler._channels == {}

    def test_step_type(self):
        """Test step_type property returns NOTIFICATION."""
        handler = NotificationHandler()
        assert handler.step_type == StepType.NOTIFICATION

    def test_register_channel(self):
        """Test registering a notification channel."""
        handler = NotificationHandler()

        async def email_sender(**kwargs):
            return True

        handler.register_channel("email", email_sender)
        assert "email" in handler._channels

    @pytest.mark.asyncio
    async def test_execute_no_channel(self):
        """Test execution when channel is not registered."""
        handler = NotificationHandler()

        step = StepDefinition(
            id="notif1",
            name="Notification Step",
            step_type=StepType.NOTIFICATION,
            handler="notification",
            config={
                "channel": "slack",
                "recipients": ["user@example.com"],
                "message": "Test notification",
            },
            next_steps=["next_step"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="notif1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"]["sent"] is False
        assert "not configured" in result["result"]["reason"]
        assert result["next_step"] == "next_step"

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful notification execution."""
        handler = NotificationHandler()

        async def mock_sender(**kwargs):
            return True

        handler.register_channel("email", mock_sender)

        step = StepDefinition(
            id="notif1",
            name="Notification Step",
            step_type=StepType.NOTIFICATION,
            handler="notification",
            config={
                "channel": "email",
                "recipients": ["user@example.com"],
                "message": "Hello {name}!",
                "subject": "Test Subject",
            },
            next_steps=["next_step"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="notif1",
            status=WorkflowStatus.RUNNING,
            variables={"name": "World"},
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["result"]["sent"] is True
        assert result["result"]["channel"] == "email"
        assert result["next_step"] == "next_step"

    @pytest.mark.asyncio
    async def test_execute_sender_error(self):
        """Test execution when sender raises an error."""
        handler = NotificationHandler()

        async def error_sender(**kwargs):
            raise ValueError("Sender failed")

        handler.register_channel("email", error_sender)

        step = StepDefinition(
            id="notif1",
            name="Notification Step",
            step_type=StepType.NOTIFICATION,
            handler="notification",
            config={
                "channel": "email",
                "recipients": ["user@example.com"],
                "message": "Test",
            },
            next_steps=[],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="notif1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is False
        assert "Sender failed" in result["error"]

    def test_format_message_success(self):
        """Test message formatting with variables."""
        handler = NotificationHandler()
        result = handler._format_message("Hello {name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_format_message_missing_key(self):
        """Test message formatting with missing key returns original."""
        handler = NotificationHandler()
        result = handler._format_message("Hello {name}!", {})
        assert result == "Hello {name}!"


# =============================================================================
# ParallelHandler Tests
# =============================================================================


class TestParallelHandler:
    """Tests for ParallelHandler."""

    def test_step_type(self):
        """Test step_type property returns PARALLEL."""
        handler = ParallelHandler()
        assert handler.step_type == StepType.PARALLEL

    @pytest.mark.asyncio
    async def test_execute_with_branches(self):
        """Test parallel execution with branches."""
        handler = ParallelHandler()

        step = StepDefinition(
            id="parallel1",
            name="Parallel Step",
            step_type=StepType.PARALLEL,
            handler="parallel",
            config={
                "branches": ["branch_a", "branch_b", "branch_c"],
            },
            next_steps=["join_step"],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="parallel1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["parallel"] is True
        assert result["branches"] == ["branch_a", "branch_b", "branch_c"]
        assert result["next_step"] == "join_step"

    @pytest.mark.asyncio
    async def test_execute_no_branches(self):
        """Test parallel execution with no branches."""
        handler = ParallelHandler()

        step = StepDefinition(
            id="parallel1",
            name="Parallel Step",
            step_type=StepType.PARALLEL,
            handler="parallel",
            config={},
            next_steps=[],
        )

        instance = WorkflowInstance(
            id="instance1",
            workflow_id="def1",
            current_step="parallel1",
            status=WorkflowStatus.RUNNING,
        )

        result = await handler.execute(step, instance, {})

        assert result["success"] is True
        assert result["parallel"] is True
        assert result["branches"] == []
        assert result["next_step"] is None
