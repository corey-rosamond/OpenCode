"""
Debug agent for analyzing errors and finding root causes.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class DebugAgent(Agent):
    """Agent specialized in debugging and error analysis.

    Analyzes errors and suggests fixes:
    - Error message and stack trace analysis
    - Root cause identification
    - Fix suggestions with explanations
    - Reproduction steps
    - Prevention recommendations
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize debug agent.

        Args:
            task: The debugging task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "debug"

    async def execute(self) -> AgentResult:
        """Execute debugging task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "DebugAgent must be executed via AgentExecutor"
        )
