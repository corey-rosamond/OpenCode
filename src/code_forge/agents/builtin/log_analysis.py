"""
Log analysis agent for finding patterns and issues in logs.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class LogAnalysisAgent(Agent):
    """Agent specialized in log analysis.

    Analyzes log files to identify:
    - Recurring errors and frequencies
    - Performance issues and bottlenecks
    - Security incidents or anomalies
    - System health patterns
    - Root causes of failures
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize log analysis agent.

        Args:
            task: The log analysis task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "log-analysis"

    async def execute(self) -> AgentResult:
        """Execute log analysis task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "LogAnalysisAgent must be executed via AgentExecutor"
        )
