"""Dependency injection container for CLI.

This module provides a clean way to inject dependencies into the CLI,
making it easier to test and swap implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from code_forge.commands import CommandExecutor, CommandContext
    from code_forge.config import CodeForgeConfig
    from code_forge.langchain.agent import CodeForgeAgent
    from code_forge.langchain.llm import OpenRouterLLM
    from code_forge.llm import OpenRouterClient
    from code_forge.modes import ModeManager
    from code_forge.sessions import SessionManager
    from code_forge.tools import ToolRegistry


@runtime_checkable
class ILLMClient(Protocol):
    """Protocol for LLM client implementations."""

    async def complete(self, request: Any) -> Any:
        """Complete a chat request."""
        ...


@runtime_checkable
class IAgent(Protocol):
    """Protocol for agent implementations."""

    async def stream(self, input: str) -> Any:
        """Stream agent execution."""
        ...

    @property
    def memory(self) -> Any:
        """Access agent memory."""
        ...


@dataclass
class Dependencies:
    """Container for CLI dependencies.

    This allows for easy dependency injection and testing by
    providing a single place to configure all dependencies.

    Example:
        ```python
        # Production use (auto-creates dependencies)
        deps = Dependencies.create(config, api_key)

        # Testing (inject mocks)
        deps = Dependencies(
            client=mock_client,
            llm=mock_llm,
            agent=mock_agent,
            ...
        )
        ```
    """

    client: ILLMClient
    llm: OpenRouterLLM
    agent: CodeForgeAgent
    tool_registry: ToolRegistry
    session_manager: SessionManager
    mode_manager: ModeManager
    command_executor: CommandExecutor
    command_context: CommandContext

    # Optional overrides for specific components
    _custom_tools: list[Any] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        config: CodeForgeConfig,
        api_key: str,
        *,
        client: ILLMClient | None = None,
        llm: OpenRouterLLM | None = None,
        tool_registry: ToolRegistry | None = None,
        session_manager: SessionManager | None = None,
        mode_manager: ModeManager | None = None,
        command_executor: CommandExecutor | None = None,
    ) -> Dependencies:
        """Create dependencies with defaults for production use.

        Args:
            config: Application configuration.
            api_key: OpenRouter API key.
            client: Optional custom LLM client (for testing).
            llm: Optional custom LLM (for testing).
            tool_registry: Optional custom tool registry.
            session_manager: Optional custom session manager.
            mode_manager: Optional custom mode manager.
            command_executor: Optional custom command executor.

        Returns:
            Configured Dependencies container.
        """
        from code_forge.commands import (
            CommandExecutor as CmdExecutor,
            CommandContext as CmdContext,
            register_builtin_commands,
        )
        from code_forge.langchain.agent import CodeForgeAgent
        from code_forge.langchain.llm import OpenRouterLLM
        from code_forge.langchain.tools import adapt_tools_for_langchain
        from code_forge.llm import OpenRouterClient
        from code_forge.modes import setup_modes
        from code_forge.sessions import SessionManager as SessMgr
        from code_forge.tools import ToolRegistry as ToolReg, register_all_tools

        # Create or use provided client
        actual_client = client or OpenRouterClient(api_key=api_key)

        # Create or use provided LLM
        actual_llm = llm or OpenRouterLLM(
            client=actual_client,
            model=config.model.default,
        )

        # Create or use provided tool registry
        if tool_registry is None:
            register_all_tools()
            tool_registry = ToolReg()

        # Create agent with tools
        raw_tools = [tool_registry.get(name) for name in tool_registry.list_names()]
        raw_tools = [t for t in raw_tools if t is not None]
        tools = adapt_tools_for_langchain(raw_tools)
        agent = CodeForgeAgent(llm=actual_llm, tools=tools)

        # Create or use provided session manager
        actual_session_manager = session_manager or SessMgr.get_instance()

        # Create or use provided mode manager
        actual_mode_manager = mode_manager or setup_modes()

        # Register commands and create executor
        register_builtin_commands()
        actual_command_executor = command_executor or CmdExecutor()

        # Create command context
        cmd_context = CmdContext(
            session_manager=actual_session_manager,
            config=config,
            llm=actual_llm,
        )

        return cls(
            client=actual_client,
            llm=actual_llm,
            agent=agent,
            tool_registry=tool_registry,
            session_manager=actual_session_manager,
            mode_manager=actual_mode_manager,
            command_executor=actual_command_executor,
            command_context=cmd_context,
        )

    def get_tool_names(self) -> list[str]:
        """Get list of available tool names."""
        return self.tool_registry.list_names()
