"""
Configuration agent for managing configuration files.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class ConfigurationAgent(Agent):
    """Agent specialized in configuration management.

    Manages configuration files including:
    - Syntax and schema validation
    - Environment configuration comparison
    - Configuration template generation
    - Format migration (YAML, TOML, JSON, ENV)
    - Configuration documentation
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize configuration agent.

        Args:
            task: The configuration management task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "configuration"

    async def execute(self) -> AgentResult:
        """Execute configuration management task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "ConfigurationAgent must be executed via AgentExecutor"
        )
