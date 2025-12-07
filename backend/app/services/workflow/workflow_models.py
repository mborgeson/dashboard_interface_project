"""
Workflow Data Models

Defines the data structures for workflow definitions and instances.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class WorkflowStatus(str, Enum):
    """Workflow instance status."""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Workflow step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"  # Waiting for approval or external event


class StepType(str, Enum):
    """Types of workflow steps."""
    ACTION = "action"           # Execute an action
    CONDITION = "condition"     # Branch based on condition
    APPROVAL = "approval"       # Wait for approval
    PARALLEL = "parallel"       # Execute steps in parallel
    DELAY = "delay"             # Wait for specified duration
    NOTIFICATION = "notification"  # Send notification
    SUBPROCESS = "subprocess"   # Run another workflow


@dataclass
class StepDefinition:
    """
    Defines a single step in a workflow.

    Attributes:
        id: Unique step identifier
        name: Human-readable step name
        step_type: Type of step (action, condition, etc.)
        handler: Handler name for executing the step
        config: Step configuration and parameters
        next_steps: List of possible next step IDs
        condition: Condition for conditional branching
        timeout_seconds: Maximum execution time
        retry_count: Number of retries on failure
        on_error: Error handling strategy
    """
    id: str
    name: str
    step_type: StepType = StepType.ACTION
    handler: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    timeout_seconds: int = 300
    retry_count: int = 0
    on_error: str = "fail"  # fail, skip, retry

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "step_type": self.step_type.value,
            "handler": self.handler,
            "config": self.config,
            "next_steps": self.next_steps,
            "condition": self.condition,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "on_error": self.on_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepDefinition":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            step_type=StepType(data.get("step_type", "action")),
            handler=data.get("handler", ""),
            config=data.get("config", {}),
            next_steps=data.get("next_steps", []),
            condition=data.get("condition"),
            timeout_seconds=data.get("timeout_seconds", 300),
            retry_count=data.get("retry_count", 0),
            on_error=data.get("on_error", "fail"),
        )


@dataclass
class WorkflowDefinition:
    """
    Defines a complete workflow.

    Attributes:
        id: Unique workflow definition ID
        name: Human-readable workflow name
        description: Workflow description
        version: Workflow version
        steps: List of step definitions
        start_step: ID of the first step
        variables: Default workflow variables
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: List[StepDefinition] = field(default_factory=list)
    start_step: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """Get step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps],
            "start_step": self.start_step,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            steps=[StepDefinition.from_dict(s) for s in data.get("steps", [])],
            start_step=data.get("start_step", ""),
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


@dataclass
class StepExecution:
    """
    Tracks execution of a single step.

    Attributes:
        step_id: Reference to step definition
        status: Current execution status
        started_at: Execution start time
        completed_at: Execution completion time
        result: Step result data
        error: Error message if failed
        retries: Number of retry attempts made
    """
    step_id: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
        }


@dataclass
class WorkflowInstance:
    """
    Represents a running or completed workflow instance.

    Attributes:
        id: Unique instance ID
        workflow_id: Reference to workflow definition
        workflow_name: Name of the workflow
        status: Current instance status
        current_step: Current step being executed
        variables: Workflow variables (context)
        step_executions: Execution records for each step
        created_at: Instance creation time
        started_at: Execution start time
        completed_at: Execution completion time
        created_by: User who created the instance
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    workflow_name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    step_executions: Dict[str, StepExecution] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_step_execution(self, step_id: str) -> Optional[StepExecution]:
        """Get execution record for a step."""
        return self.step_executions.get(step_id)

    def set_step_execution(self, step_id: str, execution: StepExecution) -> None:
        """Set execution record for a step."""
        self.step_executions[step_id] = execution

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    @property
    def progress_percent(self) -> float:
        """Get completion percentage based on completed steps."""
        if not self.step_executions:
            return 0.0
        completed = sum(
            1 for e in self.step_executions.values()
            if e.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
        )
        return (completed / len(self.step_executions)) * 100 if self.step_executions else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "current_step": self.current_step,
            "variables": self.variables,
            "step_executions": {k: v.to_dict() for k, v in self.step_executions.items()},
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "metadata": self.metadata,
            "duration_seconds": self.duration_seconds,
            "progress_percent": round(self.progress_percent, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowInstance":
        """Create from dictionary."""
        step_executions = {}
        for k, v in data.get("step_executions", {}).items():
            step_executions[k] = StepExecution(
                step_id=v["step_id"],
                status=StepStatus(v.get("status", "pending")),
                started_at=datetime.fromisoformat(v["started_at"]) if v.get("started_at") else None,
                completed_at=datetime.fromisoformat(v["completed_at"]) if v.get("completed_at") else None,
                result=v.get("result"),
                error=v.get("error"),
                retries=v.get("retries", 0),
            )

        return cls(
            id=data.get("id", str(uuid4())),
            workflow_id=data.get("workflow_id", ""),
            workflow_name=data.get("workflow_name", ""),
            status=WorkflowStatus(data.get("status", "pending")),
            current_step=data.get("current_step"),
            variables=data.get("variables", {}),
            step_executions=step_executions,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            created_by=data.get("created_by"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ApprovalRequest:
    """
    Represents a pending approval request.

    Attributes:
        id: Unique request ID
        workflow_instance_id: Associated workflow instance
        step_id: Step waiting for approval
        approvers: List of user IDs who can approve
        requested_at: When approval was requested
        approved_at: When approval was granted
        approved_by: User who approved
        status: Approval status
        comment: Approval comment
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_instance_id: str = ""
    step_id: str = ""
    approvers: List[str] = field(default_factory=list)
    requested_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "workflow_instance_id": self.workflow_instance_id,
            "step_id": self.step_id,
            "approvers": self.approvers,
            "requested_at": self.requested_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "status": self.status,
            "comment": self.comment,
            "metadata": self.metadata,
        }
