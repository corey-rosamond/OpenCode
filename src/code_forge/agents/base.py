"""
Base classes for the subagent system.

Provides foundational classes for creating and managing
autonomous subagents that execute specialized tasks.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .result import AgentResult


class AgentState(Enum):
    """Agent lifecycle states."""

    PENDING = "pending"  # Created but not started
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Finished with error
    CANCELLED = "cancelled"  # Manually cancelled


@dataclass
class ResourceLimits:
    """Resource limits for agent execution.

    Attributes:
        max_tokens: Maximum tokens for LLM calls.
        max_time_seconds: Maximum execution time.
        max_tool_calls: Maximum tool invocations.
        max_iterations: Maximum agent loop iterations.
    """

    max_tokens: int = 50000
    max_time_seconds: int = 300
    max_tool_calls: int = 100
    max_iterations: int = 50

    def __post_init__(self) -> None:
        """Validate limits are positive."""
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.max_time_seconds <= 0:
            raise ValueError("max_time_seconds must be positive")
        if self.max_tool_calls <= 0:
            raise ValueError("max_tool_calls must be positive")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")


@dataclass
class ResourceUsage:
    """Tracked resource usage during execution.

    Attributes:
        tokens_used: Total tokens consumed.
        time_seconds: Execution time.
        tool_calls: Number of tool invocations.
        iterations: Number of agent loop iterations.
        cost_usd: Estimated API cost.
    """

    tokens_used: int = 0
    time_seconds: float = 0.0
    tool_calls: int = 0
    iterations: int = 0
    cost_usd: float = 0.0

    def exceeds(self, limits: ResourceLimits) -> str | None:
        """Check if usage exceeds any limit.

        Args:
            limits: Resource limits to check against.

        Returns:
            Name of exceeded limit, or None if within limits.
        """
        if self.tokens_used > limits.max_tokens:
            return "max_tokens"
        if self.time_seconds > limits.max_time_seconds:
            return "max_time_seconds"
        if self.tool_calls > limits.max_tool_calls:
            return "max_tool_calls"
        if self.iterations > limits.max_iterations:
            return "max_iterations"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "tokens_used": self.tokens_used,
            "time_seconds": self.time_seconds,
            "tool_calls": self.tool_calls,
            "iterations": self.iterations,
            "cost_usd": self.cost_usd,
        }


@dataclass
class AgentConfig:
    """Configuration for an agent.

    Attributes:
        agent_type: Type identifier (explore, plan, etc.).
        description: Human-readable description.
        prompt_addition: Additional system prompt text.
        tools: Tool names to allow (None = all).
        inherit_context: Whether to include parent context.
        limits: Resource limits.
        model: Specific model to use (None = default).
    """

    agent_type: str
    description: str = ""
    prompt_addition: str = ""
    tools: list[str] | None = None
    inherit_context: bool = False
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    model: str | None = None

    @classmethod
    def for_type(cls, agent_type: str, **overrides: Any) -> AgentConfig:
        """Create config for a known agent type.

        Args:
            agent_type: Type identifier.
            **overrides: Config field overrides.

        Returns:
            Configured AgentConfig instance.
        """
        # Import here to avoid circular imports
        from .types import AgentTypeRegistry

        registry = AgentTypeRegistry.get_instance()
        type_def = registry.get(agent_type)

        if type_def is None:
            return cls(agent_type=agent_type, **overrides)

        config = cls(
            agent_type=agent_type,
            description=type_def.description,
            prompt_addition=type_def.prompt_template,
            tools=type_def.default_tools.copy() if type_def.default_tools else None,
            limits=ResourceLimits(
                max_tokens=type_def.default_max_tokens,
                max_time_seconds=type_def.default_max_time,
            ),
        )

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "agent_type": self.agent_type,
            "description": self.description,
            "prompt_addition": self.prompt_addition,
            "tools": self.tools,
            "inherit_context": self.inherit_context,
            "limits": {
                "max_tokens": self.limits.max_tokens,
                "max_time_seconds": self.limits.max_time_seconds,
                "max_tool_calls": self.limits.max_tool_calls,
                "max_iterations": self.limits.max_iterations,
            },
            "model": self.model,
        }


@dataclass
class AgentContext:
    """Execution context for an agent.

    Attributes:
        parent_messages: Messages from parent context.
        working_directory: Working directory path.
        environment: Environment variables.
        metadata: Additional context data.
        parent_id: ID of parent agent (if any).
    """

    parent_messages: list[dict[str, Any]] = field(default_factory=list)
    working_directory: str = "."
    environment: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "parent_messages": self.parent_messages,
            "working_directory": self.working_directory,
            "environment": self.environment,
            "metadata": self.metadata,
            "parent_id": str(self.parent_id) if self.parent_id else None,
        }


class Agent(ABC):
    """Base class for subagents.

    Agents are autonomous execution units that perform specific
    tasks and return structured results.
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            task: The task description.
            config: Agent configuration.
            context: Execution context.
        """
        self.id: UUID = uuid4()
        self.task = task
        self.config = config
        self.context = context or AgentContext()
        self.state = AgentState.PENDING
        self.created_at = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

        self._result: AgentResult | None = None
        self._usage = ResourceUsage()
        self._messages: list[dict[str, Any]] = []
        self._on_progress: list[Callable[[str], None]] = []
        self._cancelled = False

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return agent type identifier."""
        ...

    @abstractmethod
    async def execute(self) -> AgentResult:
        """Execute the agent task.

        Returns:
            AgentResult with execution outcome.
        """
        ...

    def cancel(self) -> bool:
        """Request cancellation of agent execution.

        Returns:
            True if cancellation was applied, False if agent already complete.
        """
        # Validate state transition - can only cancel PENDING or RUNNING agents
        if self.state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED):
            logger.warning(
                "Cannot cancel agent %s: already in terminal state %s",
                self.id,
                self.state.value,
            )
            return False

        self._cancelled = True
        if self.state == AgentState.RUNNING:
            self.state = AgentState.CANCELLED
            self.completed_at = datetime.now()
        return True

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation requested."""
        return self._cancelled

    @property
    def is_complete(self) -> bool:
        """Check if agent has finished."""
        return self.state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
        )

    @property
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self.state == AgentState.RUNNING

    @property
    def result(self) -> AgentResult | None:
        """Get agent result if complete."""
        return self._result

    @property
    def usage(self) -> ResourceUsage:
        """Get current resource usage."""
        return self._usage

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Get agent message history."""
        return self._messages.copy()

    def on_progress(self, callback: Callable[[str], None]) -> None:
        """Register progress callback.

        Args:
            callback: Function to call with progress messages.
        """
        self._on_progress.append(callback)

    def _report_progress(self, message: str) -> None:
        """Report progress to callbacks.

        Args:
            message: Progress message to report.
        """
        import contextlib

        for callback in self._on_progress:
            with contextlib.suppress(Exception):
                callback(message)

    def _start_execution(self) -> None:
        """Mark execution as started."""
        self.state = AgentState.RUNNING
        self.started_at = datetime.now()

    def _complete_execution(
        self,
        result: AgentResult,
        success: bool = True,
    ) -> None:
        """Mark execution as complete.

        Args:
            result: The execution result.
            success: Whether execution succeeded.
        """
        self.state = AgentState.COMPLETED if success else AgentState.FAILED
        self.completed_at = datetime.now()
        self._result = result

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent state.

        Returns:
            Dictionary representation of agent state.
        """
        return {
            "id": str(self.id),
            "agent_type": self.agent_type,
            "task": self.task,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "usage": self._usage.to_dict(),
            "result": self._result.to_dict() if self._result else None,
            "config": self.config.to_dict(),
            "context": self.context.to_dict(),
        }
