"""Core data models for workflow system.

This module defines the data structures used throughout the workflow system,
including workflow definitions, execution state, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from code_forge.agents.result import AgentResult


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Single step in a workflow.

    A step represents one agent execution within a workflow, including
    its configuration, dependencies, and execution conditions.

    Attributes:
        id: Unique identifier for this step
        agent: Agent type to execute (must exist in AgentTypeRegistry)
        description: Human-readable description of what this step does
        inputs: Input parameters to pass to the agent
        depends_on: List of step IDs that must complete before this step
        parallel_with: Hint that this step can run in parallel with others
        condition: Optional condition expression (evaluated at runtime)
        timeout: Optional step-specific timeout in seconds
        max_retries: Maximum retry attempts on failure (default: 0)
    """

    id: str
    agent: str
    description: str
    inputs: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    condition: str | None = None
    timeout: int | None = None
    max_retries: int = 0

    def __post_init__(self) -> None:
        """Validate step data after initialization."""
        if not self.id:
            raise ValueError("Step ID cannot be empty")
        if not self.agent:
            raise ValueError("Agent type cannot be empty")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class WorkflowDefinition:
    """Complete workflow definition.

    Defines a workflow with metadata, steps, and configuration. This is
    the primary input to the workflow execution system.

    Attributes:
        name: Unique workflow name (kebab-case recommended)
        description: Human-readable description
        version: Semantic version (e.g., "1.0.0")
        author: Workflow author (optional)
        steps: List of workflow steps
        metadata: Additional workflow metadata
    """

    name: str
    description: str
    version: str
    steps: list[WorkflowStep]
    author: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate workflow definition."""
        if not self.name:
            raise ValueError("Workflow name cannot be empty")
        if not self.steps:
            raise ValueError("Workflow must have at least one step")
        if not self.version:
            raise ValueError("Workflow version cannot be empty")

        # Validate step IDs are unique
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Step IDs must be unique")


@dataclass
class StepResult:
    """Result of a single workflow step execution.

    Captures the outcome of executing one step, including timing,
    success status, and the agent result.

    Attributes:
        step_id: ID of the step that was executed
        agent_type: Type of agent that was executed
        agent_result: Result from the agent execution
        start_time: When step execution started
        end_time: When step execution ended
        duration: Execution duration in seconds
        success: Whether the step succeeded
        error: Error message if step failed
        skipped: Whether step was skipped due to condition
        retry_count: Number of retries attempted
    """

    step_id: str
    agent_type: str
    agent_result: AgentResult | None
    start_time: datetime
    end_time: datetime
    duration: float
    success: bool
    error: str | None = None
    skipped: bool = False
    retry_count: int = 0


@dataclass
class WorkflowState:
    """Runtime state of a workflow execution.

    Tracks the current state of a running or completed workflow,
    including progress, results, and status.

    Attributes:
        workflow_id: Unique ID for this workflow execution
        definition: The workflow definition being executed
        status: Current execution status
        current_step: ID of currently executing step (if running)
        completed_steps: List of completed step IDs
        failed_steps: List of failed step IDs
        skipped_steps: List of skipped step IDs
        step_results: Map of step ID to step result
        start_time: When workflow execution started
        end_time: When workflow execution ended (if completed)
    """

    workflow_id: str
    definition: WorkflowDefinition
    status: WorkflowStatus
    start_time: datetime
    current_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    step_results: dict[str, StepResult] = field(default_factory=dict)
    end_time: datetime | None = None

    def mark_step_completed(self, step_id: str, result: StepResult) -> None:
        """Mark a step as completed.

        Args:
            step_id: ID of the completed step
            result: Step execution result
        """
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)
        self.step_results[step_id] = result
        self.current_step = None

    def mark_step_failed(self, step_id: str, result: StepResult) -> None:
        """Mark a step as failed.

        Args:
            step_id: ID of the failed step
            result: Step execution result
        """
        if step_id not in self.failed_steps:
            self.failed_steps.append(step_id)
        self.step_results[step_id] = result
        self.current_step = None

    def mark_step_skipped(self, step_id: str, result: StepResult) -> None:
        """Mark a step as skipped.

        Args:
            step_id: ID of the skipped step
            result: Step execution result
        """
        if step_id not in self.skipped_steps:
            self.skipped_steps.append(step_id)
        self.step_results[step_id] = result
        self.current_step = None


@dataclass
class WorkflowResult:
    """Final result of a workflow execution.

    Contains the complete outcome of a workflow execution, including
    all step results and aggregate statistics.

    Attributes:
        workflow_id: Unique ID for this workflow execution
        workflow_name: Name of the workflow that was executed
        success: Whether the overall workflow succeeded
        steps_completed: Number of steps that completed successfully
        steps_failed: Number of steps that failed
        steps_skipped: Number of steps that were skipped
        step_results: Map of step ID to step result
        duration: Total workflow execution time in seconds
        error: Error message if workflow failed
        start_time: When workflow started
        end_time: When workflow ended
    """

    workflow_id: str
    workflow_name: str
    success: bool
    steps_completed: int
    steps_failed: int
    steps_skipped: int
    step_results: dict[str, StepResult]
    duration: float
    start_time: datetime
    end_time: datetime
    error: str | None = None

    @classmethod
    def from_state(cls, state: WorkflowState) -> WorkflowResult:
        """Create a WorkflowResult from a WorkflowState.

        Args:
            state: The workflow state to convert

        Returns:
            WorkflowResult with data from the state
        """
        if state.end_time is None:
            raise ValueError("Cannot create result from incomplete workflow")

        duration = (state.end_time - state.start_time).total_seconds()

        return cls(
            workflow_id=state.workflow_id,
            workflow_name=state.definition.name,
            success=state.status == WorkflowStatus.COMPLETED,
            steps_completed=len(state.completed_steps),
            steps_failed=len(state.failed_steps),
            steps_skipped=len(state.skipped_steps),
            step_results=state.step_results,
            duration=duration,
            start_time=state.start_time,
            end_time=state.end_time,
            error=None if state.status == WorkflowStatus.COMPLETED else f"Workflow {state.status.value}",
        )
