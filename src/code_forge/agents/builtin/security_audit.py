"""
Security audit agent for vulnerability scanning.
"""

from __future__ import annotations

from ..base import Agent, AgentConfig, AgentContext
from ..result import AgentResult


class SecurityAuditAgent(Agent):
    """Agent specialized in security auditing.

    Performs comprehensive security analysis:
    - OWASP Top 10 vulnerability scanning
    - SQL injection and XSS detection
    - Authentication and authorization flaws
    - Sensitive data exposure
    - Dependency vulnerability scanning
    """

    def __init__(
        self,
        task: str,
        config: AgentConfig,
        context: AgentContext | None = None,
    ) -> None:
        """Initialize security audit agent.

        Args:
            task: The security audit task.
            config: Agent configuration.
            context: Execution context.
        """
        super().__init__(task, config, context)

    @property
    def agent_type(self) -> str:
        """Return agent type identifier."""
        return "security-audit"

    async def execute(self) -> AgentResult:
        """Execute security audit task.

        This method is called by the executor with proper
        LLM and tool integration.

        Returns:
            AgentResult indicating must use AgentExecutor.
        """
        # Actual execution is handled by AgentExecutor
        # This is called as a fallback or for testing
        return AgentResult.fail(
            "SecurityAuditAgent must be executed via AgentExecutor"
        )
