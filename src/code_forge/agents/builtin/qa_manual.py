"""
QA manual agent for creating manual testing procedures.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class QAManualAgent(Agent):
    """Agent specialized in manual testing procedures.

    Creates comprehensive test scenarios:
    - User acceptance test scenarios
    - Exploratory testing guides
    - Test case matrices
    - Manual regression test suites
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize QA manual agent.

        Args:
            task: The QA manual testing task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "qa-manual"

    async def execute(self) -> AgentResult:
        """Execute QA manual testing task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "QAManualAgent must be executed via AgentExecutor"
        )
