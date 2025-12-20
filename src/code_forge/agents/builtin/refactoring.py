"""
Refactoring agent for improving code quality.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class RefactoringAgent(Agent):
    """Agent specialized in code refactoring.

    Identifies and fixes code smells and anti-patterns:
    - SOLID principle violations
    - Code duplication
    - Long methods and classes
    - Complex conditionals
    - Performance bottlenecks
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize refactoring agent.

        Args:
            task: The refactoring task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "refactoring"

    async def execute(self) -> AgentResult:
        """Execute refactoring task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "RefactoringAgent must be executed via AgentExecutor"
        )
