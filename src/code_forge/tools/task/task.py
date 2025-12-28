"""Task tool for spawning subagents.

Allows the LLM to spawn specialized agents to handle complex tasks
such as code exploration, planning, code review, security audits, etc.
"""

from __future__ import annotations

from typing import Any

from code_forge.agents.base import AgentContext
from code_forge.agents.manager import AgentManager
from code_forge.agents.types import AgentTypeRegistry
from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


class TaskTool(BaseTool):
    """Spawn specialized agents to handle complex tasks.

    The TaskTool enables the LLM to delegate work to specialized agents
    that are optimized for specific types of tasks like:
    - explore: Navigate codebases and find information
    - plan: Create implementation plans
    - code-review: Review code for quality and issues
    - security-audit: Identify security vulnerabilities
    - test-generation: Generate test cases
    - And many more (20+ agent types available)
    """

    @property
    def name(self) -> str:
        """Return unique tool identifier."""
        return "Task"

    @property
    def description(self) -> str:
        """Return human-readable description for LLM."""
        return (
            "Spawn a specialized agent to handle a complex task. "
            "Available agent types include: explore (search codebase), "
            "plan (create implementation plans), code-review (review code), "
            "security-audit (find vulnerabilities), test-generation (create tests), "
            "and many more. Use this when you need specialized expertise."
        )

    @property
    def category(self) -> ToolCategory:
        """Return tool category for grouping."""
        return ToolCategory.TASK

    @property
    def parameters(self) -> list[ToolParameter]:
        """Return list of accepted parameters."""
        return [
            ToolParameter(
                name="agent_type",
                type="string",
                description=(
                    "Type of agent to spawn. Options include: "
                    "explore, plan, code-review, security-audit, "
                    "test-generation, documentation, refactoring, "
                    "performance-analysis, debug, research, and more."
                ),
                required=True,
            ),
            ToolParameter(
                name="task",
                type="string",
                description="Task description for the agent to execute.",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="wait",
                type="boolean",
                description="Wait for agent to complete (default: true).",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="use_rag",
                type="boolean",
                description="Enable RAG context for the agent (default: true).",
                required=False,
                default=True,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        """Execute the tool by spawning an agent.

        Args:
            context: Execution context with working directory, metadata, etc.
            **kwargs: Tool parameters (agent_type, task, wait, use_rag).

        Returns:
            ToolResult with agent output or error message.
        """
        agent_type = kwargs["agent_type"]
        task = kwargs["task"]
        wait = kwargs.get("wait", True)
        use_rag = kwargs.get("use_rag", True)

        # Validate agent type
        registry = AgentTypeRegistry.get_instance()
        type_def = registry.get(agent_type)

        if type_def is None:
            available = registry.list_types()
            return ToolResult.fail(
                f"Unknown agent type: '{agent_type}'. "
                f"Available types: {', '.join(available)}"
            )

        # Build agent context
        agent_context = AgentContext(
            working_directory=context.working_dir,
            metadata=self._build_metadata(context, use_rag),
        )

        # Spawn agent via AgentManager
        try:
            manager = AgentManager.get_instance()
            agent = await manager.spawn(
                agent_type=agent_type,
                task=task,
                context=agent_context,
                wait=wait,
            )

            if wait:
                # Return agent result
                if agent.result is not None:
                    return ToolResult.ok(
                        agent.result.output,
                        agent_id=str(agent.id),
                        agent_type=agent_type,
                        tokens_used=agent.usage.tokens_used,
                    )
                else:
                    return ToolResult.fail(
                        f"Agent {agent_type} completed without result"
                    )
            else:
                # Return immediately with agent ID for tracking
                return ToolResult.ok(
                    f"Agent spawned in background. ID: {agent.id}",
                    agent_id=str(agent.id),
                    agent_type=agent_type,
                    background=True,
                )

        except RuntimeError as e:
            # No executor configured
            return ToolResult.fail(f"Agent execution failed: {e}")
        except Exception as e:
            return ToolResult.fail(f"Failed to spawn agent: {e}")

    def _build_metadata(
        self, context: ExecutionContext, use_rag: bool
    ) -> dict[str, Any]:
        """Build metadata for agent context.

        Args:
            context: Execution context.
            use_rag: Whether to include RAG manager.

        Returns:
            Metadata dictionary for agent context.
        """
        metadata: dict[str, Any] = {}

        # Pass RAG manager if available and requested
        if use_rag:
            rag_manager = context.metadata.get("rag_manager")
            if rag_manager is not None:
                metadata["rag_manager"] = rag_manager

        # Copy relevant metadata from parent context
        if context.session_id:
            metadata["parent_session_id"] = context.session_id
        if context.agent_id:
            metadata["parent_agent_id"] = context.agent_id

        return metadata
