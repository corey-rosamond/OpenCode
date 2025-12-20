"""
Communication agent for drafting professional messages.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class CommunicationAgent(Agent):
    """Agent specialized in professional communication.

    Drafts clear, contextually appropriate communications:
    - Pull request descriptions
    - Issue comments and responses
    - Release announcements
    - Professional emails
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize communication agent.

        Args:
            task: The communication task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "communication"

    async def execute(self) -> AgentResult:
        """Execute communication task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "CommunicationAgent must be executed via AgentExecutor"
        )
