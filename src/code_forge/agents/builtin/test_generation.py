"""
Test generation agent for creating comprehensive test cases.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class TestGenerationAgent(Agent):
    """Agent specialized in generating test cases.

    Analyzes code and creates comprehensive test suites covering:
    - Happy path scenarios
    - Edge cases and boundary conditions
    - Error handling
    - Integration points
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize test generation agent.

        Args:
            task: The test generation task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "test-generation"

    async def execute(self) -> AgentResult:
        """Execute test generation task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "TestGenerationAgent must be executed via AgentExecutor"
        )
