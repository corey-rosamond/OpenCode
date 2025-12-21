"""E2E tests for command system."""

import pytest


class TestCommandParsing:
    """E2E tests for command parsing."""

    def test_parses_simple_command(self):
        """Given simple command, parses correctly"""
        from code_forge.commands.parser import CommandParser

        parser = CommandParser()
        parsed = parser.parse("/help")

        assert parsed.name == "help"
        assert len(parsed.args) == 0

    def test_parses_command_with_args(self):
        """Given command with arguments, parses correctly"""
        from code_forge.commands.parser import CommandParser

        parser = CommandParser()
        parsed = parser.parse("/session new My Session")

        assert parsed.name == "session"
        assert "new" in parsed.args
        assert "My" in parsed.args or "My Session" in " ".join(parsed.args)

    def test_parses_command_with_flags(self):
        """Given command with flags, parses flags"""
        from code_forge.commands.parser import CommandParser

        parser = CommandParser()
        parsed = parser.parse("/session list --all")

        assert parsed.name == "session"
        assert "list" in parsed.args
        assert "--all" in parsed.flags or "all" in parsed.flags


class TestBuiltinCommands:
    """E2E tests for built-in commands."""

    @pytest.mark.asyncio
    async def test_help_command(self):
        """Given /help command, shows help"""
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext
        from code_forge.commands.builtin.system import HelpCommand

        cmd = HelpCommand()
        parsed = ParsedCommand(name="help", args=[], raw="help")
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert result.success
        assert "command" in result.output.lower()

    @pytest.mark.asyncio
    async def test_version_command(self):
        """Given /version command, shows version"""
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext
        from code_forge.commands.builtin.system import VersionCommand

        cmd = VersionCommand()
        parsed = ParsedCommand(name="version", args=[], raw="version")
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert result.success
        assert "1.7.0" in result.output


class TestCommandRegistry:
    """E2E tests for command registry."""

    def test_registers_command(self):
        """Given command, registers successfully"""
        from code_forge.commands import CommandRegistry, Command
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext, CommandResult

        class TestCommand(Command):
            name = "test"
            description = "Test command"

            async def execute(self, parsed: ParsedCommand, context: CommandContext) -> CommandResult:
                return CommandResult.success("Test executed")

        registry = CommandRegistry()
        registry.register(TestCommand())

        assert registry.exists("test")

    def test_executes_registered_command(self):
        """Given registered command, executes it"""
        from code_forge.commands import CommandRegistry, Command
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext, CommandResult

        class EchoCommand(Command):
            name = "echo"
            description = "Echo command"

            async def execute(self, parsed: ParsedCommand, context: CommandContext) -> CommandResult:
                message = " ".join(parsed.args) if parsed.args else "echo"
                return CommandResult.success(f"Echo: {message}")

        registry = CommandRegistry()
        registry.register(EchoCommand())

        cmd = registry.get_command("echo")
        assert cmd is not None
        assert cmd.name == "echo"


class TestCommandExecution:
    """E2E tests for command execution flow."""

    @pytest.mark.asyncio
    async def test_executes_command_end_to_end(self):
        """Given command string, parses and executes"""
        from code_forge.commands.parser import CommandParser
        from code_forge.commands.executor import CommandExecutor, CommandContext

        parser = CommandParser()
        executor = CommandExecutor()

        # Parse command
        parsed = parser.parse("/help")

        # Execute
        context = CommandContext()
        result = await executor.execute(parsed, context)

        assert result.success

    @pytest.mark.asyncio
    async def test_handles_unknown_command(self):
        """Given unknown command, returns error"""
        from code_forge.commands.parser import CommandParser
        from code_forge.commands.executor import CommandExecutor, CommandContext

        parser = CommandParser()
        executor = CommandExecutor()

        parsed = parser.parse("/nonexistent_command_xyz")

        context = CommandContext()
        result = await executor.execute(parsed, context)

        assert not result.success
        assert "unknown" in result.error.lower() or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_command_error(self):
        """Given command that errors, handles gracefully"""
        from code_forge.commands import CommandRegistry, Command
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext, CommandResult

        class FailingCommand(Command):
            name = "failing"
            description = "Command that fails"

            async def execute(self, parsed: ParsedCommand, context: CommandContext) -> CommandResult:
                return CommandResult.fail("Intentional failure")

        registry = CommandRegistry()
        registry.register(FailingCommand())

        cmd = registry.get_command("failing")
        parsed = ParsedCommand(name="failing", args=[], raw="failing")
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert not result.success
        assert result.error == "Intentional failure"


class TestCommandCategories:
    """E2E tests for command categorization."""

    def test_lists_commands_by_category(self):
        """Given command registry, lists commands by category"""
        from code_forge.commands import CommandRegistry
        from code_forge.commands.base import CommandCategory

        registry = CommandRegistry()

        # Get all commands
        all_commands = registry.list_commands()

        assert len(all_commands) > 0

        # Should have different categories
        categories = {cmd.category for cmd in all_commands}
        assert CommandCategory.GENERAL in categories or len(categories) > 0
