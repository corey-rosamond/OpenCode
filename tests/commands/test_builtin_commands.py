"""Tests for built-in commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from code_forge.commands.executor import CommandContext
from code_forge.commands.parser import ParsedCommand
from code_forge.commands.registry import CommandRegistry


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset singleton before and after each test."""
    CommandRegistry.reset_instance()
    yield
    CommandRegistry.reset_instance()


class TestHelpCommand:
    """Tests for /help command."""

    @pytest.mark.asyncio
    async def test_help_general(self) -> None:
        """Test /help shows all commands."""
        from code_forge.commands.builtin.help_commands import HelpCommand
        from code_forge.commands.executor import register_builtin_commands

        register_builtin_commands()

        cmd = HelpCommand()
        parsed = ParsedCommand(name="help", args=[])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Code-Forge Commands" in result.output
        assert "help" in result.output.lower()

    @pytest.mark.asyncio
    async def test_help_specific_command(self) -> None:
        """Test /help <command> shows command help."""
        from code_forge.commands.builtin.help_commands import HelpCommand
        from code_forge.commands.executor import register_builtin_commands

        register_builtin_commands()

        cmd = HelpCommand()
        parsed = ParsedCommand(name="help", args=["exit"])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "exit" in result.output.lower()

    @pytest.mark.asyncio
    async def test_help_unknown_command(self) -> None:
        """Test /help <unknown> shows error."""
        from code_forge.commands.builtin.help_commands import HelpCommand

        cmd = HelpCommand()
        parsed = ParsedCommand(name="help", args=["nonexistent"])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Unknown command" in result.error


class TestCommandsCommand:
    """Tests for /commands command."""

    @pytest.mark.asyncio
    async def test_commands_list_all(self) -> None:
        """Test /commands lists all commands."""
        from code_forge.commands.builtin.help_commands import CommandsCommand
        from code_forge.commands.executor import register_builtin_commands

        register_builtin_commands()

        cmd = CommandsCommand()
        parsed = ParsedCommand(name="commands", args=[])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Available Commands" in result.output

    @pytest.mark.asyncio
    async def test_commands_filter_category(self) -> None:
        """Test /commands --category filters."""
        from code_forge.commands.builtin.help_commands import CommandsCommand
        from code_forge.commands.executor import register_builtin_commands

        register_builtin_commands()

        cmd = CommandsCommand()
        parsed = ParsedCommand(name="commands", kwargs={"category": "control"})
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "exit" in result.output.lower() or "clear" in result.output.lower()

    @pytest.mark.asyncio
    async def test_commands_invalid_category(self) -> None:
        """Test /commands with invalid category."""
        from code_forge.commands.builtin.help_commands import CommandsCommand

        cmd = CommandsCommand()
        parsed = ParsedCommand(name="commands", kwargs={"category": "invalid"})
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Unknown category" in result.error


class TestSessionCommand:
    """Tests for /session command."""

    @pytest.mark.asyncio
    async def test_session_no_manager(self) -> None:
        """Test /session without session manager."""
        from code_forge.commands.builtin.session_commands import SessionCommand

        cmd = SessionCommand()
        parsed = ParsedCommand(name="session", args=[])
        context = CommandContext(session_manager=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not available" in result.error

    @pytest.mark.asyncio
    async def test_session_no_active(self) -> None:
        """Test /session with no active session."""
        from code_forge.commands.builtin.session_commands import SessionCommand

        mock_manager = MagicMock()
        mock_manager.has_current = False

        cmd = SessionCommand()
        parsed = ParsedCommand(name="session", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "No active session" in result.output

    @pytest.mark.asyncio
    async def test_session_shows_info(self) -> None:
        """Test /session shows current session info."""
        from code_forge.commands.builtin.session_commands import SessionCommand

        mock_session = MagicMock()
        mock_session.id = "test-session-123"
        mock_session.title = "Test Session"
        mock_session.message_count = 5
        mock_session.total_tokens = 1000
        mock_session.created_at = "2024-01-01"
        mock_session.updated_at = "2024-01-02"
        mock_session.tags = ["test"]

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = SessionCommand()
        parsed = ParsedCommand(name="session", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "test-session-123" in result.output
        assert "Test Session" in result.output

    @pytest.mark.asyncio
    async def test_session_list(self) -> None:
        """Test /session list."""
        from code_forge.commands.builtin.session_commands import SessionListCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"
        mock_session.title = "Test"
        mock_session.message_count = 10
        mock_session.total_tokens = 500
        mock_session.updated_at = "2024-01-01"

        mock_manager = MagicMock()
        mock_manager.list_sessions.return_value = [mock_session]

        cmd = SessionListCommand()
        parsed = ParsedCommand(name="list", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "abc12345" in result.output

    @pytest.mark.asyncio
    async def test_session_new(self) -> None:
        """Test /session new."""
        from code_forge.commands.builtin.session_commands import SessionNewCommand

        mock_session = MagicMock()
        mock_session.id = "new-session-id"

        mock_manager = MagicMock()
        mock_manager.has_current = False
        mock_manager.create.return_value = mock_session

        cmd = SessionNewCommand()
        parsed = ParsedCommand(name="new", kwargs={"title": "My Title"})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Created" in result.output
        mock_manager.create.assert_called_once()


class TestControlCommands:
    """Tests for control commands."""

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test /clear command."""
        from code_forge.commands.builtin.control_commands import ClearCommand

        output_calls: list[str] = []
        cmd = ClearCommand()
        parsed = ParsedCommand(name="clear", args=[])
        context = CommandContext(output=lambda x: output_calls.append(x))

        result = await cmd.execute(parsed, context)
        assert result.success is True
        # Should have printed ANSI clear code
        assert len(output_calls) == 1
        assert "\033[2J" in output_calls[0]

    @pytest.mark.asyncio
    async def test_exit(self) -> None:
        """Test /exit command."""
        from code_forge.commands.builtin.control_commands import ExitCommand

        cmd = ExitCommand()
        parsed = ParsedCommand(name="exit", args=[])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert result.data == {"action": "exit"}
        assert "Goodbye" in result.output

    @pytest.mark.asyncio
    async def test_exit_saves_session(self) -> None:
        """Test /exit saves active session."""
        from code_forge.commands.builtin.control_commands import ExitCommand

        mock_manager = MagicMock()
        mock_manager.has_current = True

        cmd = ExitCommand()
        parsed = ParsedCommand(name="exit", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset(self) -> None:
        """Test /reset command."""
        from code_forge.commands.builtin.control_commands import ResetCommand

        mock_session = MagicMock()
        mock_session.id = "new-id"

        mock_session_manager = MagicMock()
        mock_session_manager.has_current = True
        mock_session_manager.create.return_value = mock_session

        mock_context_manager = MagicMock()

        cmd = ResetCommand()
        parsed = ParsedCommand(name="reset", args=[])
        context = CommandContext(
            session_manager=mock_session_manager,
            context_manager=mock_context_manager,
        )

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_session_manager.close.assert_called_once()
        mock_context_manager.reset.assert_called_once()
        mock_session_manager.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self) -> None:
        """Test /stop command."""
        from code_forge.commands.builtin.control_commands import StopCommand

        cmd = StopCommand()
        parsed = ParsedCommand(name="stop", args=[])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert result.data == {"action": "stop"}


class TestContextCommands:
    """Tests for context commands."""

    @pytest.mark.asyncio
    async def test_context_no_manager(self) -> None:
        """Test /context without context manager."""
        from code_forge.commands.builtin.context_commands import ContextCommand

        cmd = ContextCommand()
        parsed = ParsedCommand(name="context", args=[])
        context = CommandContext(context_manager=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not available" in result.error

    @pytest.mark.asyncio
    async def test_context_shows_status(self) -> None:
        """Test /context shows status."""
        from code_forge.commands.builtin.context_commands import ContextCommand

        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            "model": "test-model",
            "mode": "smart",
            "message_count": 10,
            "token_usage": 5000,
            "max_tokens": 100000,
            "effective_limit": 100000,
            "available_tokens": 95000,
            "usage_percentage": 5.0,
        }
        mock_manager.get_cache_stats.return_value = None

        cmd = ContextCommand()
        parsed = ParsedCommand(name="context", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Context Status" in result.output
        assert "test-model" in result.output

    @pytest.mark.asyncio
    async def test_context_reset(self) -> None:
        """Test /context reset."""
        from code_forge.commands.builtin.context_commands import ContextResetCommand

        mock_manager = MagicMock()

        cmd = ContextResetCommand()
        parsed = ParsedCommand(name="reset", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_manager.reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_mode_valid(self) -> None:
        """Test /context mode with valid mode."""
        from code_forge.commands.builtin.context_commands import ContextModeCommand
        from code_forge.context.manager import TruncationMode

        mock_manager = MagicMock()

        cmd = ContextModeCommand()
        parsed = ParsedCommand(name="mode", args=["smart"])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        # Verify mode and strategy were set directly
        assert mock_manager.mode == TruncationMode.SMART

    @pytest.mark.asyncio
    async def test_context_mode_invalid(self) -> None:
        """Test /context mode with invalid mode."""
        from code_forge.commands.builtin.context_commands import ContextModeCommand

        mock_manager = MagicMock()

        cmd = ContextModeCommand()
        parsed = ParsedCommand(name="mode", args=["invalid"])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Invalid mode" in result.error


class TestConfigCommands:
    """Tests for config commands."""

    @pytest.mark.asyncio
    async def test_config_no_config(self) -> None:
        """Test /config without config."""
        from code_forge.commands.builtin.config_commands import ConfigCommand

        cmd = ConfigCommand()
        parsed = ParsedCommand(name="config", args=[])
        context = CommandContext(config=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not available" in result.error

    @pytest.mark.asyncio
    async def test_model_show(self) -> None:
        """Test /model shows current model."""
        from code_forge.commands.builtin.config_commands import ModelCommand

        mock_config = MagicMock()
        mock_llm = MagicMock()
        mock_llm.model = "claude-3-opus"

        cmd = ModelCommand()
        parsed = ParsedCommand(name="model", args=[])
        context = CommandContext(config=mock_config, llm=mock_llm)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "claude-3-opus" in result.output

    @pytest.mark.asyncio
    async def test_model_set(self) -> None:
        """Test /model <name> sets model."""
        from code_forge.commands.builtin.config_commands import ModelCommand

        mock_config = MagicMock()
        mock_llm = MagicMock()
        mock_llm.model = "original-model"

        cmd = ModelCommand()
        parsed = ParsedCommand(name="model", args=["gpt-4"])
        context = CommandContext(config=mock_config, llm=mock_llm)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert mock_llm.model == "gpt-4"


class TestDebugCommands:
    """Tests for debug commands."""

    @pytest.mark.asyncio
    async def test_debug_toggle_on(self) -> None:
        """Test /debug toggles debug mode on."""
        from code_forge.commands.builtin.debug_commands import DebugCommand

        mock_repl = MagicMock()
        mock_repl.debug = False

        cmd = DebugCommand()
        parsed = ParsedCommand(name="debug", args=[])
        context = CommandContext(repl=mock_repl)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "enabled" in result.output
        assert mock_repl.debug is True

    @pytest.mark.asyncio
    async def test_debug_toggle_off(self) -> None:
        """Test /debug toggles debug mode off."""
        from code_forge.commands.builtin.debug_commands import DebugCommand

        mock_repl = MagicMock()
        mock_repl.debug = True

        cmd = DebugCommand()
        parsed = ParsedCommand(name="debug", args=[])
        context = CommandContext(repl=mock_repl)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "disabled" in result.output

    @pytest.mark.asyncio
    async def test_tokens(self) -> None:
        """Test /tokens shows token usage."""
        from code_forge.commands.builtin.debug_commands import TokensCommand

        mock_session = MagicMock()
        mock_session.total_prompt_tokens = 1000
        mock_session.total_completion_tokens = 500

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = TokensCommand()
        parsed = ParsedCommand(name="tokens", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Token Usage" in result.output
        assert "1,000" in result.output or "1000" in result.output

    @pytest.mark.asyncio
    async def test_history_no_session(self) -> None:
        """Test /history with no active session."""
        from code_forge.commands.builtin.debug_commands import HistoryCommand

        cmd = HistoryCommand()
        parsed = ParsedCommand(name="history", args=[])
        context = CommandContext(session_manager=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "No active session" in result.error


class TestConfigGetCommand:
    """Tests for /config get command."""

    @pytest.mark.asyncio
    async def test_config_get_no_key(self) -> None:
        """Test /config get without key."""
        from code_forge.commands.builtin.config_commands import ConfigGetCommand

        mock_config = MagicMock()
        cmd = ConfigGetCommand()
        parsed = ParsedCommand(name="get", args=[])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Key required" in result.error

    @pytest.mark.asyncio
    async def test_config_get_direct_attribute(self) -> None:
        """Test /config get for direct attribute."""
        from code_forge.commands.builtin.config_commands import ConfigGetCommand

        mock_config = MagicMock()
        mock_config.some_key = "some_value"

        cmd = ConfigGetCommand()
        parsed = ParsedCommand(name="get", args=["some_key"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "some_value" in result.output

    @pytest.mark.asyncio
    async def test_config_get_nested_attribute(self) -> None:
        """Test /config get for nested attribute like llm.model."""
        from code_forge.commands.builtin.config_commands import ConfigGetCommand

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4"
        mock_config = MagicMock(spec=[])  # Empty spec so getattr returns None
        mock_config.llm = mock_llm

        cmd = ConfigGetCommand()
        parsed = ParsedCommand(name="get", args=["llm.model"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "gpt-4" in result.output

    @pytest.mark.asyncio
    async def test_config_get_not_found(self) -> None:
        """Test /config get for non-existent key."""
        from code_forge.commands.builtin.config_commands import ConfigGetCommand

        mock_config = MagicMock(spec=[])  # Empty spec means no attributes

        cmd = ConfigGetCommand()
        parsed = ParsedCommand(name="get", args=["nonexistent"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestConfigSetCommand:
    """Tests for /config set command."""

    @pytest.mark.asyncio
    async def test_config_set_no_key(self) -> None:
        """Test /config set without key."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        mock_config = MagicMock()
        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=[])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Key required" in result.error

    @pytest.mark.asyncio
    async def test_config_set_no_value(self) -> None:
        """Test /config set without value."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        mock_config = MagicMock()
        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=["key"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Value required" in result.error

    @pytest.mark.asyncio
    async def test_config_set_string(self) -> None:
        """Test /config set with string value."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        mock_config = MagicMock()
        mock_config.key = "old_value"

        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=["key", "new_value"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Configuration updated" in result.output

    @pytest.mark.asyncio
    async def test_config_set_bool_true(self) -> None:
        """Test /config set with boolean true value."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        mock_config = MagicMock()
        mock_config.flag = False

        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=["flag", "true"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_config_set_int(self) -> None:
        """Test /config set with integer value."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        mock_config = MagicMock()
        mock_config.count = 10

        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=["count", "20"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_config_set_float(self) -> None:
        """Test /config set with float value."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        mock_config = MagicMock()
        mock_config.temperature = 0.7

        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=["temperature", "0.9"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True


class TestConfigDefaultCommand:
    """Tests for /config default behavior."""

    @pytest.mark.asyncio
    async def test_config_shows_current(self) -> None:
        """Test /config shows current config."""
        from code_forge.commands.builtin.config_commands import ConfigCommand

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4"
        mock_llm.temperature = 0.7
        mock_llm.max_tokens = 1000

        mock_config = MagicMock()
        mock_config.llm = mock_llm
        mock_config.debug = True

        cmd = ConfigCommand()
        parsed = ParsedCommand(name="config", args=[])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Configuration" in result.output


class TestContextCompactCommand:
    """Tests for /context compact command."""

    @pytest.mark.asyncio
    async def test_context_compact_saves_tokens(self) -> None:
        """Test /context compact saves tokens."""
        from code_forge.commands.builtin.context_commands import ContextCompactCommand

        mock_manager = MagicMock()
        mock_manager.get_stats.side_effect = [
            {"token_count": 1000},
            {"token_count": 500},
        ]
        mock_manager.compact_if_needed = AsyncMock()

        cmd = ContextCompactCommand()
        parsed = ParsedCommand(name="compact", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "compacted" in result.output.lower()

    @pytest.mark.asyncio
    async def test_context_compact_no_change(self) -> None:
        """Test /context compact when already compact."""
        from code_forge.commands.builtin.context_commands import ContextCompactCommand

        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            "message_count": 10,
            "token_usage": 100,
        }
        mock_manager.compact_if_needed = AsyncMock(return_value=False)

        cmd = ContextCompactCommand()
        parsed = ParsedCommand(name="compact", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "already compact" in result.output.lower()

    @pytest.mark.asyncio
    async def test_context_compact_error(self) -> None:
        """Test /context compact handles errors."""
        from code_forge.commands.builtin.context_commands import ContextCompactCommand

        mock_manager = MagicMock()
        mock_manager.get_stats.side_effect = Exception("Error")

        cmd = ContextCompactCommand()
        parsed = ParsedCommand(name="compact", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestContextModeCommand:
    """Tests for /context mode command."""

    @pytest.mark.asyncio
    async def test_context_mode_no_mode(self) -> None:
        """Test /context mode without mode arg."""
        from code_forge.commands.builtin.context_commands import ContextModeCommand

        mock_manager = MagicMock()
        cmd = ContextModeCommand()
        parsed = ParsedCommand(name="mode", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Mode required" in result.error


class TestSessionResumeCommand:
    """Tests for /session resume command."""

    @pytest.mark.asyncio
    async def test_session_resume_by_id(self) -> None:
        """Test /session resume with session ID."""
        from code_forge.commands.builtin.session_commands import SessionResumeCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"
        mock_session.title = "Test Session"

        mock_manager = MagicMock()
        mock_manager.has_current = False
        mock_manager.list_sessions.return_value = [mock_session]
        mock_manager.resume.return_value = mock_session

        cmd = SessionResumeCommand()
        parsed = ParsedCommand(name="resume", args=["abc1"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Resumed" in result.output

    @pytest.mark.asyncio
    async def test_session_resume_not_found(self) -> None:
        """Test /session resume with non-existent ID."""
        from code_forge.commands.builtin.session_commands import SessionResumeCommand

        mock_manager = MagicMock()
        mock_manager.list_sessions.return_value = []

        cmd = SessionResumeCommand()
        parsed = ParsedCommand(name="resume", args=["xyz"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_session_resume_latest(self) -> None:
        """Test /session resume with no ID resumes latest."""
        from code_forge.commands.builtin.session_commands import SessionResumeCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"
        mock_session.title = "Latest Session"

        mock_manager = MagicMock()
        mock_manager.resume_latest.return_value = mock_session

        cmd = SessionResumeCommand()
        parsed = ParsedCommand(name="resume", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Resumed" in result.output

    @pytest.mark.asyncio
    async def test_session_resume_latest_none(self) -> None:
        """Test /session resume when no sessions exist."""
        from code_forge.commands.builtin.session_commands import SessionResumeCommand

        mock_manager = MagicMock()
        mock_manager.resume_latest.return_value = None

        cmd = SessionResumeCommand()
        parsed = ParsedCommand(name="resume", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "No sessions" in result.error


class TestSessionDeleteCommand:
    """Tests for /session delete command."""

    @pytest.mark.asyncio
    async def test_session_delete_success(self) -> None:
        """Test /session delete with valid ID."""
        from code_forge.commands.builtin.session_commands import SessionDeleteCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"

        mock_manager = MagicMock()
        mock_manager.list_sessions.return_value = [mock_session]
        mock_manager.delete.return_value = True

        cmd = SessionDeleteCommand()
        parsed = ParsedCommand(name="delete", args=["abc1"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Deleted" in result.output

    @pytest.mark.asyncio
    async def test_session_delete_no_id(self) -> None:
        """Test /session delete without ID."""
        from code_forge.commands.builtin.session_commands import SessionDeleteCommand

        mock_manager = MagicMock()
        cmd = SessionDeleteCommand()
        parsed = ParsedCommand(name="delete", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "ID required" in result.error

    @pytest.mark.asyncio
    async def test_session_delete_not_found(self) -> None:
        """Test /session delete with non-existent ID."""
        from code_forge.commands.builtin.session_commands import SessionDeleteCommand

        mock_manager = MagicMock()
        mock_manager.list_sessions.return_value = []

        cmd = SessionDeleteCommand()
        parsed = ParsedCommand(name="delete", args=["xyz"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestSessionTitleCommand:
    """Tests for /session title command."""

    @pytest.mark.asyncio
    async def test_session_title_success(self) -> None:
        """Test /session title sets title."""
        from code_forge.commands.builtin.session_commands import SessionTitleCommand

        mock_manager = MagicMock()
        mock_manager.has_current = True

        cmd = SessionTitleCommand()
        parsed = ParsedCommand(name="title", args=["My", "New", "Title"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_manager.set_title.assert_called_with("My New Title")

    @pytest.mark.asyncio
    async def test_session_title_no_title(self) -> None:
        """Test /session title without title."""
        from code_forge.commands.builtin.session_commands import SessionTitleCommand

        mock_manager = MagicMock()
        mock_manager.has_current = True

        cmd = SessionTitleCommand()
        parsed = ParsedCommand(name="title", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Title required" in result.error

    @pytest.mark.asyncio
    async def test_session_title_no_session(self) -> None:
        """Test /session title with no active session."""
        from code_forge.commands.builtin.session_commands import SessionTitleCommand

        mock_manager = MagicMock()
        mock_manager.has_current = False

        cmd = SessionTitleCommand()
        parsed = ParsedCommand(name="title", args=["Title"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestSessionTagCommand:
    """Tests for /session tag command."""

    @pytest.mark.asyncio
    async def test_session_tag_add(self) -> None:
        """Test /session tag adds tag."""
        from code_forge.commands.builtin.session_commands import SessionTagCommand

        mock_session = MagicMock()
        mock_session.tags = []

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = SessionTagCommand()
        parsed = ParsedCommand(name="tag", args=["important"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "important" in mock_session.tags

    @pytest.mark.asyncio
    async def test_session_tag_duplicate(self) -> None:
        """Test /session tag with existing tag."""
        from code_forge.commands.builtin.session_commands import SessionTagCommand

        mock_session = MagicMock()
        mock_session.tags = ["important"]

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = SessionTagCommand()
        parsed = ParsedCommand(name="tag", args=["important"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_session_tag_no_name(self) -> None:
        """Test /session tag without tag name."""
        from code_forge.commands.builtin.session_commands import SessionTagCommand

        mock_manager = MagicMock()
        mock_manager.has_current = True

        cmd = SessionTagCommand()
        parsed = ParsedCommand(name="tag", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestSessionUntagCommand:
    """Tests for /session untag command."""

    @pytest.mark.asyncio
    async def test_session_untag_remove(self) -> None:
        """Test /session untag removes tag."""
        from code_forge.commands.builtin.session_commands import SessionUntagCommand

        mock_session = MagicMock()
        mock_session.tags = ["important", "todo"]

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = SessionUntagCommand()
        parsed = ParsedCommand(name="untag", args=["important"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "important" not in mock_session.tags

    @pytest.mark.asyncio
    async def test_session_untag_not_found(self) -> None:
        """Test /session untag with non-existent tag."""
        from code_forge.commands.builtin.session_commands import SessionUntagCommand

        mock_session = MagicMock()
        mock_session.tags = []

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = SessionUntagCommand()
        parsed = ParsedCommand(name="untag", args=["nonexistent"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestHistoryCommand:
    """Tests for /history command."""

    @pytest.mark.asyncio
    async def test_history_shows_messages(self) -> None:
        """Test /history shows message history."""
        from code_forge.commands.builtin.debug_commands import HistoryCommand

        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.content = "Hello"
        mock_msg1.tool_calls = None

        mock_msg2 = MagicMock()
        mock_msg2.role = "assistant"
        mock_msg2.content = "Hi there!"
        mock_msg2.tool_calls = None

        mock_session = MagicMock()
        mock_session.messages = [mock_msg1, mock_msg2]

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = HistoryCommand()
        parsed = ParsedCommand(name="history", args=[], kwargs={})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Message History" in result.output
        assert "user" in result.output
        assert "assistant" in result.output

    @pytest.mark.asyncio
    async def test_history_empty(self) -> None:
        """Test /history with no messages."""
        from code_forge.commands.builtin.debug_commands import HistoryCommand

        mock_session = MagicMock()
        mock_session.messages = []

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = HistoryCommand()
        parsed = ParsedCommand(name="history", args=[], kwargs={})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "No messages" in result.output

    @pytest.mark.asyncio
    async def test_history_with_limit(self) -> None:
        """Test /history with limit parameter."""
        from code_forge.commands.builtin.debug_commands import HistoryCommand

        messages = [MagicMock(role="user", content=f"msg{i}", tool_calls=None) for i in range(10)]

        mock_session = MagicMock()
        mock_session.messages = messages

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = HistoryCommand()
        parsed = ParsedCommand(name="history", args=[], kwargs={"limit": "5"})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "5 earlier messages not shown" in result.output

    @pytest.mark.asyncio
    async def test_history_with_tool_calls(self) -> None:
        """Test /history shows tool calls."""
        from code_forge.commands.builtin.debug_commands import HistoryCommand

        mock_msg = MagicMock()
        mock_msg.role = "assistant"
        mock_msg.content = "Let me check"
        mock_msg.tool_calls = [{"name": "read_file"}, {"name": "write_file"}]

        mock_session = MagicMock()
        mock_session.messages = [mock_msg]

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = mock_session

        cmd = HistoryCommand()
        parsed = ParsedCommand(name="history", args=[], kwargs={})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Tool calls" in result.output


class TestToolsCommand:
    """Tests for /tools command."""

    @pytest.mark.asyncio
    async def test_tools_lists_tools(self) -> None:
        """Test /tools lists available tools."""
        from code_forge.commands.builtin.debug_commands import ToolsCommand

        cmd = ToolsCommand()
        parsed = ParsedCommand(name="tools", args=[])
        context = CommandContext()

        result = await cmd.execute(parsed, context)
        # May pass or fail depending on whether ToolRegistry has tools
        # Either way, it should not error
        assert result.success is True or "not available" in result.error.lower()


class TestDebugNoRepl:
    """Tests for /debug without REPL."""

    @pytest.mark.asyncio
    async def test_debug_no_repl(self) -> None:
        """Test /debug fails without REPL."""
        from code_forge.commands.builtin.debug_commands import DebugCommand

        cmd = DebugCommand()
        parsed = ParsedCommand(name="debug", args=[])
        context = CommandContext(repl=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "REPL not available" in result.error


class TestModelCommand:
    """Tests for /model command."""

    @pytest.mark.asyncio
    async def test_model_no_config(self) -> None:
        """Test /model shows no model configured without config."""
        from code_forge.commands.builtin.config_commands import ModelCommand

        cmd = ModelCommand()
        parsed = ParsedCommand(name="model", args=[])
        context = CommandContext(config=None)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "No model configured" in result.output

    @pytest.mark.asyncio
    async def test_model_show_none(self) -> None:
        """Test /model shows no model configured when model.default is None."""
        from code_forge.commands.builtin.config_commands import ModelCommand

        mock_config = MagicMock()
        mock_config.model.default = None

        cmd = ModelCommand()
        parsed = ParsedCommand(name="model", args=[])
        context = CommandContext(config=mock_config, llm=None)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "No model configured" in result.output

    @pytest.mark.asyncio
    async def test_model_set_no_llm(self) -> None:
        """Test /model set fails without llm config."""
        from code_forge.commands.builtin.config_commands import ModelCommand

        mock_config = MagicMock()
        mock_config.llm = None

        cmd = ModelCommand()
        parsed = ParsedCommand(name="model", args=["gpt-4"])
        context = CommandContext(config=mock_config)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not available" in result.error.lower()


class TestContextShowStatus:
    """Tests for /context status (default behavior)."""

    @pytest.mark.asyncio
    async def test_context_shows_full_stats(self) -> None:
        """Test /context shows comprehensive stats."""
        from code_forge.commands.builtin.context_commands import ContextCommand

        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            "model": "gpt-4",
            "mode": "sliding_window",
            "message_count": 10,
            "token_usage": 5000,
            "max_tokens": 10000,
            "effective_limit": 10000,
            "available_tokens": 5000,
            "usage_percentage": 50.0,
            "system_tokens": 500,
            "tools_tokens": 200,
        }
        mock_manager.get_cache_stats.return_value = None

        cmd = ContextCommand()
        parsed = ParsedCommand(name="context", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Context Status" in result.output
        assert "gpt-4" in result.output
        assert "5,000" in result.output or "5000" in result.output

    @pytest.mark.asyncio
    async def test_context_error_handling(self) -> None:
        """Test /context handles errors gracefully."""
        from code_forge.commands.builtin.context_commands import ContextCommand

        mock_manager = MagicMock()
        mock_manager.get_stats.side_effect = Exception("Stats error")

        cmd = ContextCommand()
        parsed = ParsedCommand(name="context", args=[])
        context = CommandContext(context_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestTokensWithContextManager:
    """Tests for /tokens with context manager."""

    @pytest.mark.asyncio
    async def test_tokens_with_context_budget(self) -> None:
        """Test /tokens shows context budget info."""
        from code_forge.commands.builtin.debug_commands import TokensCommand

        mock_session = MagicMock()
        mock_session.total_prompt_tokens = 1000
        mock_session.total_completion_tokens = 500

        mock_session_manager = MagicMock()
        mock_session_manager.has_current = True
        mock_session_manager.current_session = mock_session

        mock_context_manager = MagicMock()
        mock_context_manager.get_stats.return_value = {
            "system_tokens": 100,
            "tools_tokens": 50,
            "token_count": 500,
            "max_tokens": 4000,
        }

        cmd = TokensCommand()
        parsed = ParsedCommand(name="tokens", args=[])
        context = CommandContext(
            session_manager=mock_session_manager,
            context_manager=mock_context_manager,
        )

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "Context Budget" in result.output
        assert "System Prompt" in result.output

    @pytest.mark.asyncio
    async def test_tokens_no_data(self) -> None:
        """Test /tokens when no token data available."""
        from code_forge.commands.builtin.debug_commands import TokensCommand

        mock_manager = MagicMock()
        mock_manager.has_current = False

        cmd = TokensCommand()
        parsed = ParsedCommand(name="tokens", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        assert "No token usage" in result.output


class TestHistoryInvalidLimit:
    """Tests for /history with invalid limit."""

    @pytest.mark.asyncio
    async def test_history_invalid_limit(self) -> None:
        """Test /history with non-numeric limit."""
        from code_forge.commands.builtin.debug_commands import HistoryCommand

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.current_session = MagicMock(messages=[])

        cmd = HistoryCommand()
        parsed = ParsedCommand(name="history", args=[], kwargs={"limit": "invalid"})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Invalid limit" in result.error


class TestSessionListLimit:
    """Tests for /session list with limit."""

    @pytest.mark.asyncio
    async def test_session_list_with_limit(self) -> None:
        """Test /session list with limit parameter."""
        from code_forge.commands.builtin.session_commands import SessionListCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345678"
        mock_session.title = "Test"
        mock_session.message_count = 5
        mock_session.total_tokens = 1000
        mock_session.updated_at = "2024-01-01"

        mock_manager = MagicMock()
        mock_manager.list_sessions.return_value = [mock_session]

        cmd = SessionListCommand()
        parsed = ParsedCommand(name="list", args=[], kwargs={"limit": "5"})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_manager.list_sessions.assert_called_with(limit=5)

    @pytest.mark.asyncio
    async def test_session_list_invalid_limit(self) -> None:
        """Test /session list with invalid limit."""
        from code_forge.commands.builtin.session_commands import SessionListCommand

        mock_manager = MagicMock()
        cmd = SessionListCommand()
        parsed = ParsedCommand(name="list", args=[], kwargs={"limit": "invalid"})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "Invalid limit" in result.error


class TestConfigEdgeCases:
    """Edge case tests for config commands."""

    @pytest.mark.asyncio
    async def test_config_get_no_config(self) -> None:
        """Test /config get without config."""
        from code_forge.commands.builtin.config_commands import ConfigGetCommand

        cmd = ConfigGetCommand()
        parsed = ParsedCommand(name="get", args=["key"])
        context = CommandContext(config=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not available" in result.error.lower()

    @pytest.mark.asyncio
    async def test_config_set_no_config(self) -> None:
        """Test /config set without config."""
        from code_forge.commands.builtin.config_commands import ConfigSetCommand

        cmd = ConfigSetCommand()
        parsed = ParsedCommand(name="set", args=["key", "value"])
        context = CommandContext(config=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False
        assert "not available" in result.error.lower()

    @pytest.mark.asyncio
    async def test_config_default_no_config(self) -> None:
        """Test /config without config."""
        from code_forge.commands.builtin.config_commands import ConfigCommand

        cmd = ConfigCommand()
        parsed = ParsedCommand(name="config", args=[])
        context = CommandContext(config=None)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestSessionEdgeCases:
    """Edge case tests for session commands."""

    @pytest.mark.asyncio
    async def test_session_new_closes_current(self) -> None:
        """Test /session new closes current session."""
        from code_forge.commands.builtin.session_commands import SessionNewCommand

        mock_session = MagicMock()
        mock_session.id = "new123456"

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.create.return_value = mock_session

        cmd = SessionNewCommand()
        parsed = ParsedCommand(name="new", args=[], kwargs={"title": "Test"})
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_tag_no_session(self) -> None:
        """Test /session tag with no active session."""
        from code_forge.commands.builtin.session_commands import SessionTagCommand

        mock_manager = MagicMock()
        mock_manager.has_current = False

        cmd = SessionTagCommand()
        parsed = ParsedCommand(name="tag", args=["important"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_session_untag_no_session(self) -> None:
        """Test /session untag with no active session."""
        from code_forge.commands.builtin.session_commands import SessionUntagCommand

        mock_manager = MagicMock()
        mock_manager.has_current = False

        cmd = SessionUntagCommand()
        parsed = ParsedCommand(name="untag", args=["important"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_session_untag_no_name(self) -> None:
        """Test /session untag without tag name."""
        from code_forge.commands.builtin.session_commands import SessionUntagCommand

        mock_manager = MagicMock()
        mock_manager.has_current = True

        cmd = SessionUntagCommand()
        parsed = ParsedCommand(name="untag", args=[])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestSessionResumeEdgeCases:
    """Edge case tests for session resume."""

    @pytest.mark.asyncio
    async def test_session_resume_closes_current(self) -> None:
        """Test /session resume closes current session."""
        from code_forge.commands.builtin.session_commands import SessionResumeCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"
        mock_session.title = "Test"

        mock_manager = MagicMock()
        mock_manager.has_current = True
        mock_manager.list_sessions.return_value = [mock_session]
        mock_manager.resume.return_value = mock_session

        cmd = SessionResumeCommand()
        parsed = ParsedCommand(name="resume", args=["abc1"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is True
        mock_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_resume_fails(self) -> None:
        """Test /session resume when resume returns None."""
        from code_forge.commands.builtin.session_commands import SessionResumeCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"

        mock_manager = MagicMock()
        mock_manager.has_current = False
        mock_manager.list_sessions.return_value = [mock_session]
        mock_manager.resume.return_value = None

        cmd = SessionResumeCommand()
        parsed = ParsedCommand(name="resume", args=["abc1"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False


class TestSessionDeleteEdgeCases:
    """Edge case tests for session delete."""

    @pytest.mark.asyncio
    async def test_session_delete_fails(self) -> None:
        """Test /session delete when delete returns False."""
        from code_forge.commands.builtin.session_commands import SessionDeleteCommand

        mock_session = MagicMock()
        mock_session.id = "abc12345"

        mock_manager = MagicMock()
        mock_manager.list_sessions.return_value = [mock_session]
        mock_manager.delete.return_value = False

        cmd = SessionDeleteCommand()
        parsed = ParsedCommand(name="delete", args=["abc1"])
        context = CommandContext(session_manager=mock_manager)

        result = await cmd.execute(parsed, context)
        assert result.success is False
