"""Tests for skill commands."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from code_forge.skills.base import Skill, SkillConfig, SkillDefinition, SkillMetadata
from code_forge.skills.commands import (
    SkillCommand,
    SkillInfoCommand,
    SkillListCommand,
    SkillReloadCommand,
    SkillSearchCommand,
    get_skill_command,
)
from code_forge.skills.registry import SkillRegistry


def create_test_skill(
    name: str,
    description: str = "Test skill",
    tags: list[str] | None = None,
    aliases: list[str] | None = None,
    is_builtin: bool = False,
) -> Skill:
    """Create a test skill."""
    metadata = SkillMetadata(
        name=name,
        description=description,
        tags=tags or [],
        aliases=aliases or [],
    )
    definition = SkillDefinition(
        metadata=metadata,
        prompt=f"You are the {name} assistant.",
        is_builtin=is_builtin,
    )
    return Skill(definition)


class MockParsedCommand:
    """Mock ParsedCommand for testing."""

    def __init__(
        self,
        name: str = "skill",
        args: list[str] | None = None,
        kwargs: dict[str, str] | None = None,
        flags: set[str] | None = None,
    ) -> None:
        self.name = name
        self.args = args or []
        self.kwargs = kwargs or {}
        self.flags = flags or set()
        self.raw = f"/{name}"

    @property
    def has_args(self) -> bool:
        return len(self.args) > 0

    def get_arg(self, index: int, default: str | None = None) -> str | None:
        if 0 <= index < len(self.args):
            return self.args[index]
        return default

    def get_kwarg(self, name: str, default: str | None = None) -> str | None:
        return self.kwargs.get(name, default)

    def has_flag(self, name: str) -> bool:
        return name in self.flags

    @property
    def subcommand(self) -> str | None:
        return self.get_arg(0)

    @property
    def rest_args(self) -> list[str]:
        return self.args[1:]


class MockContext:
    """Mock CommandContext for testing."""

    pass


class TestSkillListCommand:
    """Tests for SkillListCommand."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    @pytest.fixture
    def command(self) -> SkillListCommand:
        """Create command instance."""
        return SkillListCommand()

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Get registry with test skills."""
        registry = SkillRegistry.get_instance()
        registry.register(create_test_skill("pdf", tags=["documents"]))
        registry.register(create_test_skill("excel", tags=["data"]))
        return registry

    @pytest.mark.asyncio
    async def test_list_all_skills(
        self, command: SkillListCommand, registry: SkillRegistry
    ) -> None:
        """Test listing all skills."""
        parsed = MockParsedCommand(args=[])
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "pdf" in result.output
        assert "excel" in result.output

    @pytest.mark.asyncio
    async def test_list_by_tag(
        self, command: SkillListCommand, registry: SkillRegistry
    ) -> None:
        """Test listing skills by tag."""
        parsed = MockParsedCommand(kwargs={"tag": "documents"})
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "pdf" in result.output
        assert "excel" not in result.output

    @pytest.mark.asyncio
    async def test_list_empty(self, command: SkillListCommand) -> None:
        """Test listing when no skills registered."""
        parsed = MockParsedCommand()
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "No skills available" in result.output

    @pytest.mark.asyncio
    async def test_list_no_matches(
        self, command: SkillListCommand, registry: SkillRegistry
    ) -> None:
        """Test listing with no matching tag."""
        parsed = MockParsedCommand(kwargs={"tag": "nonexistent"})
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "No skills found" in result.output

    @pytest.mark.asyncio
    async def test_list_shows_active(
        self, command: SkillListCommand, registry: SkillRegistry
    ) -> None:
        """Test that active skill is marked."""
        registry.activate("pdf")
        parsed = MockParsedCommand()
        result = await command.execute(parsed, MockContext())

        assert "(active)" in result.output

    @pytest.mark.asyncio
    async def test_list_shows_builtin(self, command: SkillListCommand) -> None:
        """Test that builtin skills are marked."""
        registry = SkillRegistry.get_instance()
        registry.register(create_test_skill("builtin", is_builtin=True))

        parsed = MockParsedCommand()
        result = await command.execute(parsed, MockContext())

        assert "[builtin]" in result.output


class TestSkillInfoCommand:
    """Tests for SkillInfoCommand."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    @pytest.fixture
    def command(self) -> SkillInfoCommand:
        """Create command instance."""
        return SkillInfoCommand()

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Get registry with test skills."""
        registry = SkillRegistry.get_instance()
        registry.register(create_test_skill("pdf", description="PDF analysis"))
        return registry

    @pytest.mark.asyncio
    async def test_show_info(
        self, command: SkillInfoCommand, registry: SkillRegistry
    ) -> None:
        """Test showing skill info."""
        parsed = MockParsedCommand(args=["pdf"])
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "pdf" in result.output
        assert "PDF analysis" in result.output

    @pytest.mark.asyncio
    async def test_info_not_found(self, command: SkillInfoCommand) -> None:
        """Test info for nonexistent skill."""
        parsed = MockParsedCommand(args=["nonexistent"])
        result = await command.execute(parsed, MockContext())

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_info_no_name(self, command: SkillInfoCommand) -> None:
        """Test info without skill name."""
        parsed = MockParsedCommand(args=[])
        result = await command.execute(parsed, MockContext())

        assert not result.success
        assert "Usage" in result.error


class TestSkillSearchCommand:
    """Tests for SkillSearchCommand."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    @pytest.fixture
    def command(self) -> SkillSearchCommand:
        """Create command instance."""
        return SkillSearchCommand()

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Get registry with test skills."""
        registry = SkillRegistry.get_instance()
        registry.register(create_test_skill("pdf", description="PDF documents"))
        registry.register(create_test_skill("excel", description="Spreadsheet data"))
        return registry

    @pytest.mark.asyncio
    async def test_search_found(
        self, command: SkillSearchCommand, registry: SkillRegistry
    ) -> None:
        """Test searching and finding skills."""
        parsed = MockParsedCommand(args=["pdf"])
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "pdf" in result.output
        assert "excel" not in result.output

    @pytest.mark.asyncio
    async def test_search_not_found(
        self, command: SkillSearchCommand, registry: SkillRegistry
    ) -> None:
        """Test searching with no results."""
        parsed = MockParsedCommand(args=["nonexistent"])
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "No skills matching" in result.output

    @pytest.mark.asyncio
    async def test_search_no_query(self, command: SkillSearchCommand) -> None:
        """Test searching without query."""
        parsed = MockParsedCommand(args=[])
        result = await command.execute(parsed, MockContext())

        assert not result.success
        assert "Usage" in result.error

    @pytest.mark.asyncio
    async def test_search_multi_word(
        self, command: SkillSearchCommand, registry: SkillRegistry
    ) -> None:
        """Test searching with multi-word query."""
        parsed = MockParsedCommand(args=["PDF", "documents"])
        result = await command.execute(parsed, MockContext())

        assert result.success


class TestSkillReloadCommand:
    """Tests for SkillReloadCommand."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    @pytest.fixture
    def command(self) -> SkillReloadCommand:
        """Create command instance."""
        return SkillReloadCommand()

    @pytest.mark.asyncio
    async def test_reload(self, command: SkillReloadCommand) -> None:
        """Test reload command."""
        parsed = MockParsedCommand()
        result = await command.execute(parsed, MockContext())

        assert result.success
        assert "Reloaded" in result.output


class TestSkillCommand:
    """Tests for SkillCommand (main command with subcommands)."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    @pytest.fixture
    def command(self) -> SkillCommand:
        """Create command instance."""
        return SkillCommand()

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Get registry with test skills."""
        registry = SkillRegistry.get_instance()
        registry.register(create_test_skill("pdf"))
        registry.register(create_test_skill("excel"))
        return registry

    def test_command_attributes(self, command: SkillCommand) -> None:
        """Test command attributes."""
        assert command.name == "skill"
        assert "sk" in command.aliases
        assert command.description != ""

    def test_subcommands_registered(self, command: SkillCommand) -> None:
        """Test that subcommands are registered."""
        assert "list" in command.subcommands
        assert "info" in command.subcommands
        assert "search" in command.subcommands
        assert "reload" in command.subcommands

    @pytest.mark.asyncio
    async def test_default_no_active(self, command: SkillCommand) -> None:
        """Test default behavior with no active skill."""
        parsed = MockParsedCommand(args=[])
        result = await command.execute_default(parsed, MockContext())

        assert result.success
        assert "No skill active" in result.output

    @pytest.mark.asyncio
    async def test_default_with_active(
        self, command: SkillCommand, registry: SkillRegistry
    ) -> None:
        """Test default behavior with active skill."""
        registry.activate("pdf")
        parsed = MockParsedCommand(args=[])
        result = await command.execute_default(parsed, MockContext())

        assert result.success
        assert "Active skill: pdf" in result.output

    @pytest.mark.asyncio
    async def test_activate_by_name(
        self, command: SkillCommand, registry: SkillRegistry
    ) -> None:
        """Test activating skill by name."""
        parsed = MockParsedCommand(args=["pdf"])
        result = await command.execute_default(parsed, MockContext())

        assert result.success
        assert "Activated" in result.output
        assert isinstance(registry.active_skill, Skill)
        assert registry.active_skill.name == "pdf"

    @pytest.mark.asyncio
    async def test_activate_nonexistent(
        self, command: SkillCommand, registry: SkillRegistry
    ) -> None:
        """Test activating nonexistent skill."""
        parsed = MockParsedCommand(args=["nonexistent"])
        result = await command.execute_default(parsed, MockContext())

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_deactivate(
        self, command: SkillCommand, registry: SkillRegistry
    ) -> None:
        """Test deactivating skill."""
        registry.activate("pdf")
        parsed = MockParsedCommand(args=["off"])
        result = await command.execute_default(parsed, MockContext())

        assert result.success
        assert "Deactivated" in result.output
        assert registry.active_skill is None

    @pytest.mark.asyncio
    async def test_deactivate_when_none_active(
        self, command: SkillCommand
    ) -> None:
        """Test deactivating when no skill active."""
        parsed = MockParsedCommand(args=["off"])
        result = await command.execute_default(parsed, MockContext())

        assert result.success
        assert "No skill was active" in result.output

    def test_get_help(self, command: SkillCommand) -> None:
        """Test help text generation."""
        help_text = command.get_help()

        assert "/skill" in help_text
        assert "list" in help_text
        assert "info" in help_text
        assert "search" in help_text
        assert "off" in help_text


class TestGetSkillCommand:
    """Tests for get_skill_command function."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    def test_returns_skill_command(self) -> None:
        """Test that function returns SkillCommand instance."""
        cmd = get_skill_command()
        assert isinstance(cmd, SkillCommand)

    def test_subcommands_initialized(self) -> None:
        """Test that subcommands are initialized."""
        cmd = get_skill_command()
        assert len(cmd.subcommands) > 0
