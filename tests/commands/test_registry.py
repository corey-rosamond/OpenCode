"""Tests for command registry."""

from __future__ import annotations

import pytest

from code_forge.commands.base import Command, CommandCategory, CommandResult
from code_forge.commands.executor import CommandContext
from code_forge.commands.parser import ParsedCommand
from code_forge.commands.registry import CommandRegistry


class DummyCommand(Command):
    """Dummy command for testing."""

    name = "dummy"
    aliases = ["d", "dum"]
    description = "Dummy command"
    category = CommandCategory.GENERAL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        return CommandResult.ok("Dummy executed")


class AnotherCommand(Command):
    """Another command for testing."""

    name = "another"
    aliases = ["a"]
    description = "Another command"
    category = CommandCategory.SESSION

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        return CommandResult.ok("Another executed")


class TestCommandRegistry:
    """Tests for CommandRegistry class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before and after each test."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    def test_get_instance_singleton(self) -> None:
        """Test get_instance returns same instance."""
        reg1 = CommandRegistry.get_instance()
        reg2 = CommandRegistry.get_instance()
        assert reg1 is reg2

    def test_reset_instance(self) -> None:
        """Test reset_instance clears singleton."""
        reg1 = CommandRegistry.get_instance()
        CommandRegistry.reset_instance()
        reg2 = CommandRegistry.get_instance()
        assert reg1 is not reg2

    def test_register_command(self) -> None:
        """Test registering a command."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        assert isinstance(registry.get("dummy"), Command)
        assert len(registry) == 1

    def test_register_adds_aliases(self) -> None:
        """Test register adds aliases."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        assert isinstance(registry.resolve("d"), Command)
        assert isinstance(registry.resolve("dum"), Command)

    def test_register_duplicate_raises(self) -> None:
        """Test registering duplicate name raises ValueError."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummyCommand())

    def test_register_alias_conflict(self) -> None:
        """Test alias conflicting with command name."""
        registry = CommandRegistry()

        class ConflictCommand(Command):
            name = "d"  # Same as DummyCommand alias
            aliases = []
            description = "Conflict"

            async def execute(
                self, parsed: ParsedCommand, context: CommandContext
            ) -> CommandResult:
                return CommandResult.ok()

        registry.register(DummyCommand())
        with pytest.raises(ValueError, match="conflicts with alias"):
            registry.register(ConflictCommand())

    def test_unregister_command(self) -> None:
        """Test unregistering a command."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        assert registry.unregister("dummy") is True
        assert registry.get("dummy") is None
        assert len(registry) == 0

    def test_unregister_removes_aliases(self) -> None:
        """Test unregister removes aliases."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.unregister("dummy")
        assert registry.resolve("d") is None
        assert registry.resolve("dum") is None

    def test_unregister_nonexistent(self) -> None:
        """Test unregistering nonexistent command returns False."""
        registry = CommandRegistry()
        assert registry.unregister("nonexistent") is False

    def test_get_by_name(self) -> None:
        """Test getting command by exact name."""
        registry = CommandRegistry()
        cmd = DummyCommand()
        registry.register(cmd)
        assert registry.get("dummy") is cmd

    def test_get_nonexistent(self) -> None:
        """Test getting nonexistent command returns None."""
        registry = CommandRegistry()
        assert registry.get("nonexistent") is None

    def test_get_case_insensitive(self) -> None:
        """Test get is case-insensitive."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        assert isinstance(registry.get("DUMMY"), Command)
        assert isinstance(registry.get("Dummy"), Command)

    def test_resolve_by_name(self) -> None:
        """Test resolving command by name."""
        registry = CommandRegistry()
        cmd = DummyCommand()
        registry.register(cmd)
        assert registry.resolve("dummy") is cmd

    def test_resolve_by_alias(self) -> None:
        """Test resolving command by alias."""
        registry = CommandRegistry()
        cmd = DummyCommand()
        registry.register(cmd)
        assert registry.resolve("d") is cmd
        assert registry.resolve("dum") is cmd

    def test_resolve_nonexistent(self) -> None:
        """Test resolving nonexistent returns None."""
        registry = CommandRegistry()
        assert registry.resolve("nonexistent") is None

    def test_list_commands_all(self) -> None:
        """Test listing all commands."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.register(AnotherCommand())
        commands = registry.list_commands()
        assert len(commands) == 2
        # Should be sorted by name
        assert commands[0].name == "another"
        assert commands[1].name == "dummy"

    def test_list_commands_by_category(self) -> None:
        """Test listing commands by category."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.register(AnotherCommand())

        general = registry.list_commands(category=CommandCategory.GENERAL)
        assert len(general) == 1
        assert general[0].name == "dummy"

        session = registry.list_commands(category=CommandCategory.SESSION)
        assert len(session) == 1
        assert session[0].name == "another"

    def test_list_names(self) -> None:
        """Test listing all command names including aliases."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        names = registry.list_names()
        assert "dummy" in names
        assert "d" in names
        assert "dum" in names
        # Should be sorted
        assert names == sorted(names)

    def test_search_by_name(self) -> None:
        """Test searching by name."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.register(AnotherCommand())

        results = registry.search("dum")
        assert len(results) == 1
        assert results[0].name == "dummy"

    def test_search_by_description(self) -> None:
        """Test searching by description."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.register(AnotherCommand())

        results = registry.search("another")
        assert len(results) == 1
        assert results[0].name == "another"

    def test_search_by_alias(self) -> None:
        """Test searching by alias."""
        registry = CommandRegistry()
        registry.register(DummyCommand())

        results = registry.search("dum")
        assert len(results) == 1

    def test_search_case_insensitive(self) -> None:
        """Test search is case-insensitive."""
        registry = CommandRegistry()
        registry.register(DummyCommand())

        results = registry.search("DUMMY")
        assert len(results) == 1

    def test_get_categories(self) -> None:
        """Test getting commands grouped by category."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.register(AnotherCommand())

        categories = registry.get_categories()
        assert CommandCategory.GENERAL in categories
        assert CommandCategory.SESSION in categories
        assert len(categories[CommandCategory.GENERAL]) == 1
        assert len(categories[CommandCategory.SESSION]) == 1

    def test_len(self) -> None:
        """Test __len__ returns command count."""
        registry = CommandRegistry()
        assert len(registry) == 0
        registry.register(DummyCommand())
        assert len(registry) == 1
        registry.register(AnotherCommand())
        assert len(registry) == 2

    def test_contains_by_name(self) -> None:
        """Test __contains__ by name."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        assert "dummy" in registry
        assert "nonexistent" not in registry

    def test_contains_by_alias(self) -> None:
        """Test __contains__ by alias."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        assert "d" in registry
        assert "dum" in registry

    def test_iter(self) -> None:
        """Test __iter__ over commands."""
        registry = CommandRegistry()
        registry.register(DummyCommand())
        registry.register(AnotherCommand())

        commands = list(registry)
        assert len(commands) == 2
        names = [c.name for c in commands]
        assert "dummy" in names
        assert "another" in names

    def test_thread_safety_register(self) -> None:
        """Test thread-safe registration."""
        import threading

        registry = CommandRegistry()
        errors: list[Exception] = []

        def register_commands() -> None:
            for i in range(10):
                try:

                    class TempCommand(Command):
                        name = f"temp_{threading.current_thread().name}_{i}"
                        aliases = []
                        description = "Temp"

                        async def execute(
                            self, parsed: ParsedCommand, context: CommandContext
                        ) -> CommandResult:
                            return CommandResult.ok()

                    registry.register(TempCommand())
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=register_commands) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
