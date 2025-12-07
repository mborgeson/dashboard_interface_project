"""
Workflow Automation Service Package

Provides workflow definition, execution, and management for:
- Multi-step business process automation
- Approval workflows with user integration
- Conditional branching and parallel execution
- Notification and integration actions
"""

from .workflow_models import (
    WorkflowStatus,
    StepStatus,
    StepType,
    StepDefinition,
    WorkflowDefinition,
    StepExecution,
    WorkflowInstance,
    ApprovalRequest,
)
from .step_handlers import (
    StepHandler,
    ActionHandler,
    ConditionHandler,
    ApprovalHandler,
    DelayHandler,
    NotificationHandler,
    ParallelHandler,
    StepHandlerRegistry,
    log_action,
    set_variable_action,
    http_request_action,
    transform_data_action,
    register_default_actions,
)
from .workflow_engine import WorkflowEngine, get_workflow_engine

__all__ = [
    # Status Enums
    "WorkflowStatus",
    "StepStatus",
    "StepType",
    # Data Models
    "StepDefinition",
    "WorkflowDefinition",
    "StepExecution",
    "WorkflowInstance",
    "ApprovalRequest",
    # Step Handlers
    "StepHandler",
    "ActionHandler",
    "ConditionHandler",
    "ApprovalHandler",
    "DelayHandler",
    "NotificationHandler",
    "ParallelHandler",
    "StepHandlerRegistry",
    # Built-in Actions
    "log_action",
    "set_variable_action",
    "http_request_action",
    "transform_data_action",
    "register_default_actions",
    # Engine
    "WorkflowEngine",
    "get_workflow_engine",
]
