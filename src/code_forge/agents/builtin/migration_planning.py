"""
Migration planning agent for guiding code migrations.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class MigrationPlanningAgent(Agent):
    """Agent specialized in migration planning.

    Plans and guides migrations including:
    - Language version upgrades
    - Framework migrations
    - Library replacements
    - Architecture refactoring
    - Database schema migrations
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize migration planning agent.

        Args:
            task: The migration planning task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "migration-planning"

    async def execute(self) -> AgentResult:
        """Execute migration planning task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "MigrationPlanningAgent must be executed via AgentExecutor"
        )
