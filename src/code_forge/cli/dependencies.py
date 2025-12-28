"""Dependency injection container for CLI.

This module provides a clean way to inject dependencies into the CLI,
making it easier to test and swap implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from code_forge.agents.executor import AgentExecutor
    from code_forge.commands import CommandExecutor, CommandContext
    from code_forge.config import CodeForgeConfig
    from code_forge.langchain.agent import CodeForgeAgent
    from code_forge.langchain.llm import OpenRouterLLM
    from code_forge.llm import OpenRouterClient
    from code_forge.modes import ModeManager
    from code_forge.rag.manager import RAGManager
    from code_forge.sessions import SessionManager
    from code_forge.tools import ToolRegistry
    from code_forge.undo.manager import UndoManager


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
    agent_executor: AgentExecutor | None = None
    rag_manager: RAGManager | None = None
    undo_manager: UndoManager | None = None

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
        rag_manager: RAGManager | None = None,
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
            rag_manager: Optional custom RAG manager.

        Returns:
            Configured Dependencies container.
        """
        from pathlib import Path
        import logging

        from code_forge.agents.executor import AgentExecutor as AgentExec
        from code_forge.agents.manager import AgentManager
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
        from code_forge.rag.config import RAGConfig as RAGConfigFull
        from code_forge.rag.manager import RAGManager
        from code_forge.sessions import SessionManager as SessMgr
        from code_forge.tools import ToolRegistry as ToolReg, register_all_tools
        from code_forge.undo.manager import UndoManager as UndoMgr

        logger = logging.getLogger(__name__)

        # Create or use provided client
        actual_client = client or OpenRouterClient(api_key=api_key)

        # Create or use provided LLM
        actual_llm = llm or OpenRouterLLM(
            client=actual_client,
            model=config.model.default,
        )

        # Create or use provided session manager (needed early for undo manager)
        actual_session_manager = session_manager or SessMgr.get_instance()

        # Create or use provided mode manager
        actual_mode_manager = mode_manager or setup_modes()

        # Create or use provided tool registry
        if tool_registry is None:
            register_all_tools()
            tool_registry = ToolReg()

        # Create undo manager early (if enabled) so tools can use it
        from code_forge.tools.base import ExecutionContext
        actual_undo_manager: UndoMgr | None = None
        if config.undo.enabled:
            try:
                actual_undo_manager = UndoMgr(
                    session_manager=actual_session_manager,
                    max_entries=config.undo.max_entries,
                    max_size_bytes=config.undo.max_size_mb * 1024 * 1024,
                    max_file_size=config.undo.max_file_size_kb * 1024,
                    enabled=True,
                )
                logger.info("Undo manager created successfully")
            except Exception as e:
                logger.warning(f"Failed to create undo manager: {e}")
                actual_undo_manager = None

        # Create execution context with undo manager for tools
        tool_context = ExecutionContext(
            working_dir=str(Path.cwd()),
            metadata={"undo_manager": actual_undo_manager} if actual_undo_manager else {},
        )

        # Create agent with tools (pass context for undo support)
        raw_tools = [tool_registry.get(name) for name in tool_registry.list_names()]
        raw_tools = [t for t in raw_tools if t is not None]
        tools = adapt_tools_for_langchain(raw_tools, context=tool_context)
        agent = CodeForgeAgent(llm=actual_llm, tools=tools)

        # Register commands and create executor
        register_builtin_commands()
        actual_command_executor = command_executor or CmdExecutor()

        # Create or use provided RAG manager (if enabled)
        actual_rag_manager: RAGManager | None = rag_manager
        if actual_rag_manager is None and config.rag.enabled:
            try:
                project_root = Path.cwd()
                rag_config = config.rag
                full_config = RAGConfigFull(
                    enabled=rag_config.enabled,
                    auto_index=rag_config.auto_index,
                    watch_files=rag_config.watch_files,
                    embedding_model=rag_config.embedding_model,
                    openai_embedding_model=rag_config.openai_embedding_model,
                    index_directory=rag_config.index_directory,
                    include_patterns=rag_config.include_patterns or [],
                    exclude_patterns=rag_config.exclude_patterns or [],
                    max_file_size_kb=rag_config.max_file_size_kb,
                    respect_gitignore=rag_config.respect_gitignore,
                    chunk_size=rag_config.chunk_size,
                    chunk_overlap=rag_config.chunk_overlap,
                    default_max_results=rag_config.default_max_results,
                    default_min_score=rag_config.default_min_score,
                    context_token_budget=rag_config.context_token_budget,
                )
                actual_rag_manager = RAGManager(
                    project_root=project_root,
                    config=full_config,
                )
                logger.info("RAG manager created successfully")
            except Exception as e:
                logger.warning(f"Failed to create RAG manager: {e}")
                actual_rag_manager = None

        # Create command context
        cmd_context = CmdContext(
            session_manager=actual_session_manager,
            config=config,
            llm=actual_llm,
            rag_manager=actual_rag_manager,
            undo_manager=actual_undo_manager,
        )

        # Create agent executor and configure AgentManager
        # This allows TaskTool to spawn subagents
        actual_agent_executor = AgentExec(
            llm=actual_llm,
            tool_registry=tool_registry,
        )
        agent_manager = AgentManager.get_instance()
        agent_manager.set_executor(actual_agent_executor)
        logger.debug("AgentManager configured with executor")

        return cls(
            client=actual_client,
            llm=actual_llm,
            agent=agent,
            tool_registry=tool_registry,
            session_manager=actual_session_manager,
            mode_manager=actual_mode_manager,
            command_executor=actual_command_executor,
            command_context=cmd_context,
            agent_executor=actual_agent_executor,
            rag_manager=actual_rag_manager,
            undo_manager=actual_undo_manager,
        )

    def get_tool_names(self) -> list[str]:
        """Get list of available tool names."""
        return self.tool_registry.list_names()
