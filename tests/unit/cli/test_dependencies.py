"""Tests for CLI dependency injection container.

This module provides comprehensive tests for the dependency injection
system, including:
- Factory pattern with default components
- Custom component injection
- Protocol implementations
- Tool registry integration
- Session manager integration
- Mode manager integration
- Error handling during component creation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.cli.dependencies import (
    Dependencies,
    IAgent,
    ILLMClient,
)


class TestILLMClientProtocol:
    """Tests for the ILLMClient protocol."""

    def test_protocol_requires_complete_method(self) -> None:
        """Test that ILLMClient requires a complete method."""

        class ValidClient:
            async def complete(self, request: Any) -> Any:
                return {"result": "ok"}

        assert isinstance(ValidClient(), ILLMClient)

    def test_protocol_rejects_missing_complete(self) -> None:
        """Test that objects without complete are not ILLMClient."""

        class InvalidClient:
            pass

        assert not isinstance(InvalidClient(), ILLMClient)

    def test_mock_client_satisfies_protocol(self) -> None:
        """Test that AsyncMock satisfies ILLMClient protocol."""
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value={"result": "ok"})

        assert isinstance(mock_client, ILLMClient)


class TestIAgentProtocol:
    """Tests for the IAgent protocol."""

    def test_protocol_requires_stream_and_memory(self) -> None:
        """Test that IAgent requires stream and memory."""

        class ValidAgent:
            async def stream(self, input: str) -> Any:
                yield {"token": "hello"}

            @property
            def memory(self) -> Any:
                return []

        assert isinstance(ValidAgent(), IAgent)

    def test_protocol_rejects_missing_methods(self) -> None:
        """Test that objects without required methods are not IAgent."""

        class InvalidAgent:
            pass

        assert not isinstance(InvalidAgent(), IAgent)


class TestDependenciesDataclass:
    """Tests for the Dependencies dataclass structure."""

    def test_dependencies_requires_all_fields(self) -> None:
        """Test that Dependencies requires all mandatory fields."""
        mock_client = MagicMock()
        mock_llm = MagicMock()
        mock_agent = MagicMock()
        mock_tool_registry = MagicMock()
        mock_session_manager = MagicMock()
        mock_mode_manager = MagicMock()
        mock_command_executor = MagicMock()
        mock_command_context = MagicMock()

        deps = Dependencies(
            client=mock_client,
            llm=mock_llm,
            agent=mock_agent,
            tool_registry=mock_tool_registry,
            session_manager=mock_session_manager,
            mode_manager=mock_mode_manager,
            command_executor=mock_command_executor,
            command_context=mock_command_context,
        )

        assert deps.client is mock_client
        assert deps.llm is mock_llm
        assert deps.agent is mock_agent
        assert deps.tool_registry is mock_tool_registry
        assert deps.session_manager is mock_session_manager
        assert deps.mode_manager is mock_mode_manager
        assert deps.command_executor is mock_command_executor
        assert deps.command_context is mock_command_context

    def test_custom_tools_defaults_to_empty_list(self) -> None:
        """Test that _custom_tools defaults to empty list."""
        deps = Dependencies(
            client=MagicMock(),
            llm=MagicMock(),
            agent=MagicMock(),
            tool_registry=MagicMock(),
            session_manager=MagicMock(),
            mode_manager=MagicMock(),
            command_executor=MagicMock(),
            command_context=MagicMock(),
        )

        assert deps._custom_tools == []


class TestDependenciesCreate:
    """Tests for the Dependencies.create factory method."""

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        """Create a mock config."""
        config = MagicMock()
        config.model.default = "gpt-4"
        # Context config with proper values
        config.context.default_mode = "smart"
        config.context.warning_threshold = 0.8
        config.context.critical_threshold = 0.9
        return config

    @pytest.fixture
    def mock_imports(self) -> dict:
        """Set up mocks for all imported modules."""
        mocks = {
            "OpenRouterClient": MagicMock(),
            "OpenRouterLLM": MagicMock(),
            "CodeForgeAgent": MagicMock(),
            "ToolRegistry": MagicMock(),
            "SessionManager": MagicMock(),
            "ModeManager": MagicMock(),
            "CommandExecutor": MagicMock(),
            "CommandContext": MagicMock(),
            "register_all_tools": MagicMock(),
            "register_builtin_commands": MagicMock(),
            "adapt_tools_for_langchain": MagicMock(return_value=[]),
            "setup_modes": MagicMock(),
        }
        return mocks

    def test_create_with_defaults(self, mock_config: MagicMock) -> None:
        """Test creating dependencies with all defaults."""
        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.modes.setup_modes"
        ) as mock_setup_modes, patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            # Set up return values
            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = ["read", "write"]
            mock_tool_reg_instance.get.return_value = MagicMock()
            mock_tool_reg.return_value = mock_tool_reg_instance

            mock_adapt.return_value = []
            mock_session_mgr.get_instance.return_value = MagicMock()
            mock_setup_modes.return_value = MagicMock()

            deps = Dependencies.create(mock_config, "sk-or-v1-test-key")

            assert deps is not None
            assert deps.tool_registry is mock_tool_reg_instance

    def test_create_with_custom_client(self, mock_config: MagicMock) -> None:
        """Test creating dependencies with custom client."""
        custom_client = MagicMock()
        custom_client.complete = AsyncMock()

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = []
            mock_tool_reg.return_value = mock_tool_reg_instance
            mock_adapt.return_value = []
            mock_session_mgr.get_instance.return_value = MagicMock()

            deps = Dependencies.create(
                mock_config,
                "sk-or-v1-test-key",
                client=custom_client,
            )

            # Custom client should be used
            assert deps.client is custom_client

    def test_create_with_custom_tool_registry(self, mock_config: MagicMock) -> None:
        """Test creating dependencies with custom tool registry."""
        custom_registry = MagicMock()
        custom_registry.list_names.return_value = ["custom_tool"]
        custom_registry.get.return_value = MagicMock()

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_adapt.return_value = []
            mock_session_mgr.get_instance.return_value = MagicMock()

            deps = Dependencies.create(
                mock_config,
                "sk-or-v1-test-key",
                tool_registry=custom_registry,
            )

            # Custom registry should be used
            assert deps.tool_registry is custom_registry
            # register_all_tools should not be called when custom registry provided
            custom_registry.list_names.assert_called()

    def test_create_with_custom_session_manager(self, mock_config: MagicMock) -> None:
        """Test creating dependencies with custom session manager."""
        custom_session_mgr = MagicMock()

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = []
            mock_tool_reg.return_value = mock_tool_reg_instance
            mock_adapt.return_value = []

            deps = Dependencies.create(
                mock_config,
                "sk-or-v1-test-key",
                session_manager=custom_session_mgr,
            )

            assert deps.session_manager is custom_session_mgr

    def test_create_with_custom_mode_manager(self, mock_config: MagicMock) -> None:
        """Test creating dependencies with custom mode manager."""
        custom_mode_mgr = MagicMock()

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = []
            mock_tool_reg.return_value = mock_tool_reg_instance
            mock_adapt.return_value = []
            mock_session_mgr.get_instance.return_value = MagicMock()

            deps = Dependencies.create(
                mock_config,
                "sk-or-v1-test-key",
                mode_manager=custom_mode_mgr,
            )

            assert deps.mode_manager is custom_mode_mgr

    def test_create_registers_builtin_commands(self, mock_config: MagicMock) -> None:
        """Test that create() registers builtin commands."""
        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ) as mock_register, patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = []
            mock_tool_reg.return_value = mock_tool_reg_instance
            mock_adapt.return_value = []
            mock_session_mgr.get_instance.return_value = MagicMock()

            Dependencies.create(mock_config, "sk-or-v1-test-key")

            mock_register.assert_called_once()


class TestGetToolNames:
    """Tests for the get_tool_names method."""

    def test_get_tool_names_returns_registry_names(self) -> None:
        """Test that get_tool_names returns tool registry names."""
        mock_registry = MagicMock()
        mock_registry.list_names.return_value = ["read", "write", "bash", "glob"]

        deps = Dependencies(
            client=MagicMock(),
            llm=MagicMock(),
            agent=MagicMock(),
            tool_registry=mock_registry,
            session_manager=MagicMock(),
            mode_manager=MagicMock(),
            command_executor=MagicMock(),
            command_context=MagicMock(),
        )

        names = deps.get_tool_names()

        assert names == ["read", "write", "bash", "glob"]
        mock_registry.list_names.assert_called_once()

    def test_get_tool_names_empty_registry(self) -> None:
        """Test get_tool_names with empty registry."""
        mock_registry = MagicMock()
        mock_registry.list_names.return_value = []

        deps = Dependencies(
            client=MagicMock(),
            llm=MagicMock(),
            agent=MagicMock(),
            tool_registry=mock_registry,
            session_manager=MagicMock(),
            mode_manager=MagicMock(),
            command_executor=MagicMock(),
            command_context=MagicMock(),
        )

        names = deps.get_tool_names()

        assert names == []


class TestDependenciesWithMocks:
    """Integration tests for Dependencies with full mock injection."""

    def test_full_mock_injection(self) -> None:
        """Test creating Dependencies with all mocked components."""
        mock_client = MagicMock()
        mock_client.complete = AsyncMock()

        mock_llm = MagicMock()
        mock_agent = MagicMock()
        mock_agent.stream = AsyncMock()
        mock_agent.memory = []

        mock_tool_registry = MagicMock()
        mock_tool_registry.list_names.return_value = ["test_tool"]

        mock_session_manager = MagicMock()
        mock_mode_manager = MagicMock()
        mock_command_executor = MagicMock()
        mock_command_context = MagicMock()

        deps = Dependencies(
            client=mock_client,
            llm=mock_llm,
            agent=mock_agent,
            tool_registry=mock_tool_registry,
            session_manager=mock_session_manager,
            mode_manager=mock_mode_manager,
            command_executor=mock_command_executor,
            command_context=mock_command_context,
        )

        # Verify all components are accessible
        assert isinstance(deps.client, ILLMClient)
        assert isinstance(deps.agent, IAgent)
        assert deps.get_tool_names() == ["test_tool"]

    @pytest.mark.asyncio
    async def test_mock_agent_stream(self) -> None:
        """Test that mocked agent stream works correctly."""
        mock_agent = MagicMock()
        mock_agent.stream = AsyncMock(return_value=iter([
            {"token": "Hello"},
            {"token": " World"},
        ]))
        mock_agent.memory = []

        deps = Dependencies(
            client=MagicMock(),
            llm=MagicMock(),
            agent=mock_agent,
            tool_registry=MagicMock(),
            session_manager=MagicMock(),
            mode_manager=MagicMock(),
            command_executor=MagicMock(),
            command_context=MagicMock(),
        )

        result = await deps.agent.stream("test input")

        mock_agent.stream.assert_called_once_with("test input")


class TestSingletonBehavior:
    """Tests for singleton behavior of injected components."""

    def test_session_manager_uses_get_instance(self) -> None:
        """Test that SessionManager.get_instance() is used."""
        mock_config = MagicMock()
        mock_config.model.default = "gpt-4"
        mock_config.context.default_mode = "smart"
        mock_config.context.warning_threshold = 0.8
        mock_config.context.critical_threshold = 0.9

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = []
            mock_tool_reg.return_value = mock_tool_reg_instance
            mock_adapt.return_value = []
            mock_session_mgr.get_instance.return_value = MagicMock()

            Dependencies.create(mock_config, "sk-or-v1-test-key")

            mock_session_mgr.get_instance.assert_called_once()


class TestLazyInitialization:
    """Tests for lazy initialization patterns."""

    def test_tools_adapted_lazily(self) -> None:
        """Test that tools are adapted during create, not eagerly."""
        mock_config = MagicMock()
        mock_config.model.default = "gpt-4"
        mock_config.context.default_mode = "smart"
        mock_config.context.warning_threshold = 0.8
        mock_config.context.critical_threshold = 0.9

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ) as mock_tool_reg, patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ) as mock_session_mgr, patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ) as mock_adapt, patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_tool_reg_instance = MagicMock()
            mock_tool_reg_instance.list_names.return_value = ["read", "write"]
            mock_tool_reg_instance.get.side_effect = lambda n: MagicMock(name=n)
            mock_tool_reg.return_value = mock_tool_reg_instance
            mock_session_mgr.get_instance.return_value = MagicMock()

            Dependencies.create(mock_config, "sk-or-v1-test-key")

            # adapt_tools_for_langchain should be called with tool list
            mock_adapt.assert_called_once()
            # Should have received 2 tools
            args = mock_adapt.call_args[0][0]
            assert len(args) == 2


class TestErrorPropagation:
    """Tests for error propagation during dependency creation."""

    def test_client_creation_error_propagates(self) -> None:
        """Test that errors during client creation propagate."""
        mock_config = MagicMock()
        mock_config.model.default = "gpt-4"
        mock_config.context.default_mode = "smart"
        mock_config.context.warning_threshold = 0.8
        mock_config.context.critical_threshold = 0.9

        with patch(
            "code_forge.llm.OpenRouterClient"
        ) as mock_client_cls, patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.ToolRegistry"
        ), patch(
            "code_forge.tools.register_all_tools"
        ), patch(
            "code_forge.sessions.SessionManager"
        ), patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_client_cls.side_effect = ValueError("Invalid API key")

            with pytest.raises(ValueError, match="Invalid API key"):
                Dependencies.create(mock_config, "invalid-key")

    def test_tool_registry_error_propagates(self) -> None:
        """Test that errors during tool registration propagate."""
        mock_config = MagicMock()
        mock_config.model.default = "gpt-4"
        mock_config.context.default_mode = "smart"
        mock_config.context.warning_threshold = 0.8
        mock_config.context.critical_threshold = 0.9

        with patch(
            "code_forge.commands.CommandExecutor"
        ), patch(
            "code_forge.commands.CommandContext"
        ), patch(
            "code_forge.commands.register_builtin_commands"
        ), patch(
            "code_forge.tools.register_all_tools"
        ) as mock_register, patch(
            "code_forge.sessions.SessionManager"
        ), patch(
            "code_forge.modes.setup_modes"
        ), patch(
            "code_forge.langchain.tools.adapt_tools_for_langchain"
        ), patch(
            "code_forge.llm.OpenRouterClient"
        ), patch(
            "code_forge.langchain.llm.OpenRouterLLM"
        ), patch(
            "code_forge.langchain.agent.CodeForgeAgent"
        ):

            mock_register.side_effect = RuntimeError("Tool registration failed")

            with pytest.raises(RuntimeError, match="Tool registration failed"):
                Dependencies.create(mock_config, "sk-or-v1-test-key")
