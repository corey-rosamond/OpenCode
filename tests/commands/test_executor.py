"""Tests for command executor."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from code_forge.commands.base import Command, CommandCategory, CommandResult
from code_forge.commands.executor import CommandContext, CommandExecutor
from code_forge.commands.parser import CommandParser, ParsedCommand
from code_forge.commands.registry import CommandRegistry


class TestCommandContext:
    """Tests for CommandContext dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic CommandContext creation."""
        context = CommandContext()
        assert context.session_manager is None
        assert context.context_manager is None
        assert context.config is None
        assert context.llm is None
        assert context.repl is None
        assert callable(context.output)

    def test_with_components(self) -> None:
        """Test CommandContext with components."""
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_config = MagicMock()

        context = CommandContext(
            session_manager=mock_session,
            context_manager=mock_context,
            config=mock_config,
        )

        assert context.session_manager is mock_session
        assert context.context_manager is mock_context
        assert context.config is mock_config

    def test_print_calls_output(self) -> None:
        """Test print method calls output function."""
        output_calls: list[str] = []
        context = CommandContext(output=lambda x: output_calls.append(x))

        context.print("Hello")
        assert output_calls == ["Hello"]

    def test_default_output_is_print(self) -> None:
        """Test default output function works."""
        context = CommandContext()
        # Should not raise
        context.print("test")


class TestCommandExecutor:
    """Tests for CommandExecutor class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before and after each test."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    class SimpleCommand(Command):
        name = "simple"
        aliases = ["s"]
        description = "Simple command"
        usage = "/simple"

        async def execute(
            self, parsed: ParsedCommand, context: CommandContext
        ) -> CommandResult:
            return CommandResult.ok("Simple executed")

    class RequiredArgCommand(Command):
        name = "required"
        description = "Requires argument"
        usage = "/required <arg>"

        from code_forge.commands.base import CommandArgument

        arguments = [CommandArgument(name="arg", description="Required arg")]

        async def execute(
            self, parsed: ParsedCommand, context: CommandContext
        ) -> CommandResult:
            return CommandResult.ok(f"Got: {parsed.get_arg(0)}")

    class FailingCommand(Command):
        name = "failing"
        description = "Fails"

        async def execute(
            self, parsed: ParsedCommand, context: CommandContext
        ) -> CommandResult:
            raise RuntimeError("Command crashed")

    def test_init_defaults(self) -> None:
        """Test executor initializes with defaults."""
        executor = CommandExecutor()
        assert isinstance(executor.registry, CommandRegistry)
        assert isinstance(executor.parser, CommandParser)

    def test_init_custom(self) -> None:
        """Test executor with custom registry and parser."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry=registry, parser=parser)
        assert executor.registry is registry
        assert executor.parser is parser

    @pytest.mark.asyncio
    async def test_execute_valid_command(self) -> None:
        """Test executing valid command."""
        registry = CommandRegistry()
        registry.register(self.SimpleCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/simple", CommandContext())
        assert result.success is True
        assert result.output == "Simple executed"

    @pytest.mark.asyncio
    async def test_execute_with_alias(self) -> None:
        """Test executing command by alias."""
        registry = CommandRegistry()
        registry.register(self.SimpleCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/s", CommandContext())
        assert result.success is True
        assert result.output == "Simple executed"

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self) -> None:
        """Test executing unknown command returns error."""
        registry = CommandRegistry()
        registry.register(self.SimpleCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/unknown", CommandContext())
        assert result.success is False
        assert "Unknown command" in result.error

    @pytest.mark.asyncio
    async def test_execute_unknown_with_suggestion(self) -> None:
        """Test unknown command shows suggestion."""
        registry = CommandRegistry()
        registry.register(self.SimpleCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/simpl", CommandContext())
        assert result.success is False
        assert "simple" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_invalid_parse(self) -> None:
        """Test executing invalid command text."""
        executor = CommandExecutor()
        result = await executor.execute("not a command", CommandContext())
        assert result.success is False
        assert "Not a valid command" in result.error

    @pytest.mark.asyncio
    async def test_execute_validation_error(self) -> None:
        """Test executing command with validation error."""
        registry = CommandRegistry()
        registry.register(self.RequiredArgCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/required", CommandContext())
        assert result.success is False
        assert "Missing required argument" in result.error

    @pytest.mark.asyncio
    async def test_execute_validation_passes(self) -> None:
        """Test executing command with valid arguments."""
        registry = CommandRegistry()
        registry.register(self.RequiredArgCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/required myarg", CommandContext())
        assert result.success is True
        assert "myarg" in result.output

    @pytest.mark.asyncio
    async def test_execute_command_exception(self) -> None:
        """Test command exception is caught."""
        registry = CommandRegistry()
        registry.register(self.FailingCommand())
        executor = CommandExecutor(registry=registry)

        result = await executor.execute("/failing", CommandContext())
        assert result.success is False
        assert "Command failed" in result.error

    def test_can_execute_true(self) -> None:
        """Test can_execute returns True for registered command."""
        registry = CommandRegistry()
        registry.register(self.SimpleCommand())
        executor = CommandExecutor(registry=registry)

        assert executor.can_execute("simple") is True
        assert executor.can_execute("s") is True

    def test_can_execute_false(self) -> None:
        """Test can_execute returns False for unregistered."""
        executor = CommandExecutor()
        assert executor.can_execute("unknown") is False

    def test_is_command_true(self) -> None:
        """Test is_command returns True for command."""
        executor = CommandExecutor()
        assert executor.is_command("/help") is True

    def test_is_command_false(self) -> None:
        """Test is_command returns False for non-command."""
        executor = CommandExecutor()
        assert executor.is_command("hello") is False


class TestRegisterBuiltinCommands:
    """Tests for register_builtin_commands function."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before and after each test."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    def test_registers_commands(self) -> None:
        """Test builtin commands are registered."""
        from code_forge.commands.executor import register_builtin_commands

        registry = CommandRegistry()
        register_builtin_commands(registry)

        # Check some expected commands are registered
        assert "help" in registry
        assert "session" in registry
        assert "context" in registry
        assert "exit" in registry
        assert "config" in registry
        assert "debug" in registry

    def test_registers_to_singleton(self) -> None:
        """Test registers to singleton when no registry provided."""
        from code_forge.commands.executor import register_builtin_commands

        register_builtin_commands()
        registry = CommandRegistry.get_instance()

        assert "help" in registry

    def test_aliases_work(self) -> None:
        """Test command aliases are registered."""
        from code_forge.commands.executor import register_builtin_commands

        registry = CommandRegistry()
        register_builtin_commands(registry)

        # Check aliases
        assert "?" in registry  # help alias
        assert "q" in registry  # exit alias
        assert "s" in registry  # session alias
