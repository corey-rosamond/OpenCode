"""
Diagram agent for creating visualizations.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class DiagramAgent(Agent):
    """Agent specialized in creating diagrams.

    Creates visual representations using Mermaid:
    - Architecture diagrams
    - Sequence diagrams
    - Flowcharts
    - Class diagrams
    - State machines
    - Entity-relationship diagrams
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize diagram agent.

        Args:
            task: The diagram creation task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "diagram"

    async def execute(self) -> AgentResult:
        """Execute diagram creation task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "DiagramAgent must be executed via AgentExecutor"
        )
