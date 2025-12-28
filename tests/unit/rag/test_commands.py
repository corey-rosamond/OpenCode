"""Tests for RAG commands."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from code_forge.rag.commands import (
    RAGClearCommand,
    RAGCommand,
    RAGConfigCommand,
    RAGConfigDisableCommand,
    RAGConfigEnableCommand,
    RAGConfigShowCommand,
    RAGIndexCommand,
    RAGSearchCommand,
    RAGStatusCommand,
    get_commands,
)
from code_forge.rag.config import RAGConfig


@dataclass
class MockParsedCommand:
    """Mock parsed command for testing."""

    name: str = ""
    subcommand: str | None = None
    args: list[str] | None = None
    kwargs: dict[str, str] | None = None
    flags: set[str] | None = None
    raw: str = ""
    rest_args: list[str] | None = None

    def __post_init__(self) -> None:
        if self.args is None:
            self.args = []
        if self.kwargs is None:
            self.kwargs = {}
        if self.flags is None:
            self.flags = set()
        if self.rest_args is None:
            self.rest_args = []

    def get_arg(self, index: int) -> str | None:
        if self.args and index < len(self.args):
            return self.args[index]
        return None


@dataclass
class MockCodeForgeConfig:
    """Mock CodeForge configuration."""

    rag: RAGConfig


@dataclass
class MockCommandContext:
    """Mock command context for testing."""

    config: MockCodeForgeConfig | None = None
    rag_manager: Any = None

    def print(self, text: str) -> None:
        pass


class TestRAGCommand:
    """Tests for RAGCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGCommand()

        assert cmd.name == "rag"
        assert "r" in cmd.aliases
        assert cmd.description != ""
        assert "index" in cmd.subcommands
        assert "search" in cmd.subcommands
        assert "status" in cmd.subcommands
        assert "clear" in cmd.subcommands
        assert "config" in cmd.subcommands

    def test_get_help(self) -> None:
        """Test getting help text."""
        cmd = RAGCommand()
        help_text = cmd.get_help()

        assert "/rag" in help_text
        assert "index" in help_text
        assert "search" in help_text


class TestRAGIndexCommand:
    """Tests for RAGIndexCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGIndexCommand()

        assert cmd.name == "index"
        assert "Index" in cmd.description

    def test_execute_no_manager(self) -> None:
        """Test execute when no manager available."""
        cmd = RAGIndexCommand()
        parsed = MockParsedCommand()
        context = MockCommandContext(config=None)

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "not available" in result.error.lower()


class TestRAGSearchCommand:
    """Tests for RAGSearchCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGSearchCommand()

        assert cmd.name == "search"
        assert len(cmd.arguments) > 0

    def test_execute_no_query(self, tmp_path: Path) -> None:
        """Test execute without query."""
        cmd = RAGSearchCommand()
        parsed = MockParsedCommand(args=[])
        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "query required" in result.error.lower()


class TestRAGStatusCommand:
    """Tests for RAGStatusCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGStatusCommand()

        assert cmd.name == "status"

    def test_execute_no_manager(self) -> None:
        """Test execute when no manager available."""
        cmd = RAGStatusCommand()
        parsed = MockParsedCommand()
        context = MockCommandContext(config=None)

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False


class TestRAGClearCommand:
    """Tests for RAGClearCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGClearCommand()

        assert cmd.name == "clear"

    def test_execute_no_manager(self) -> None:
        """Test execute when no manager available."""
        cmd = RAGClearCommand()
        parsed = MockParsedCommand()
        context = MockCommandContext(config=None)

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False


class TestRAGConfigCommand:
    """Tests for RAGConfigCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGConfigCommand()

        assert cmd.name == "config"
        assert "enable" in cmd.subcommands
        assert "disable" in cmd.subcommands
        assert "show" in cmd.subcommands


class TestRAGConfigEnableCommand:
    """Tests for RAGConfigEnableCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGConfigEnableCommand()

        assert cmd.name == "enable"

    def test_execute(self) -> None:
        """Test enabling RAG."""
        cmd = RAGConfigEnableCommand()
        parsed = MockParsedCommand()
        rag_config = RAGConfig(enabled=False)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is True
        assert context.config.rag.enabled is True

    def test_execute_no_config(self) -> None:
        """Test execute without config."""
        cmd = RAGConfigEnableCommand()
        parsed = MockParsedCommand()
        context = MockCommandContext(config=None)

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False


class TestRAGConfigDisableCommand:
    """Tests for RAGConfigDisableCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGConfigDisableCommand()

        assert cmd.name == "disable"

    def test_execute(self) -> None:
        """Test disabling RAG."""
        cmd = RAGConfigDisableCommand()
        parsed = MockParsedCommand()
        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is True
        assert context.config.rag.enabled is False


class TestRAGConfigShowCommand:
    """Tests for RAGConfigShowCommand."""

    def test_command_attributes(self) -> None:
        """Test command has correct attributes."""
        cmd = RAGConfigShowCommand()

        assert cmd.name == "show"

    def test_execute(self) -> None:
        """Test showing config."""
        cmd = RAGConfigShowCommand()
        parsed = MockParsedCommand()
        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is True
        assert "Enabled" in result.output
        assert "Chunk Size" in result.output

    def test_execute_no_config(self) -> None:
        """Test execute without config."""
        cmd = RAGConfigShowCommand()
        parsed = MockParsedCommand()
        context = MockCommandContext(config=None)

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False


class TestGetCommands:
    """Tests for get_commands function."""

    def test_get_commands(self) -> None:
        """Test getting all RAG commands."""
        commands = get_commands()

        assert len(commands) == 1
        assert commands[0].name == "rag"


class TestRAGCommandsWithMockManager:
    """Tests for RAG commands with a mock manager."""

    @pytest.fixture
    def mock_manager(self) -> MagicMock:
        """Create a mock RAG manager."""
        from unittest.mock import AsyncMock

        manager = MagicMock()
        manager.is_enabled = True
        manager.is_initialized = True

        # Mock async methods
        manager.index_project = AsyncMock(return_value=MagicMock(
            total_documents=5,
            total_chunks=10,
            total_tokens=1000,
            embedding_model="test-model",
            documents_by_type={"python": 5},
        ))
        manager.search = AsyncMock(return_value=[])
        manager.get_status = AsyncMock(return_value=MagicMock(
            enabled=True,
            initialized=True,
            indexed=True,
            total_chunks=10,
            total_documents=5,
            embedding_model="test-model",
            vector_store="mock",
            last_indexed=None,
            index_directory=".forge/index",
        ))
        manager.clear_index = AsyncMock(return_value=10)
        manager.format_status = MagicMock(return_value="Status: OK")

        return manager

    @pytest.fixture
    def context_with_manager(self, mock_manager: MagicMock) -> MockCommandContext:
        """Create a context with a mock manager."""
        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=mock_manager,
        )
        return context

    def test_index_command_success(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test index command executes successfully."""
        cmd = RAGIndexCommand()
        parsed = MockParsedCommand(flags=set())

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context_with_manager)
        )

        assert result.success is True
        assert "5" in result.output  # total_documents
        assert "10" in result.output  # total_chunks

    def test_index_command_with_force_flag(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test index command with force flag."""
        cmd = RAGIndexCommand()
        parsed = MockParsedCommand(flags={"force"})

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context_with_manager)
        )

        assert result.success is True
        # Verify force was passed
        context_with_manager.rag_manager.index_project.assert_called_with(force=True)

    def test_search_command_no_results(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test search command with no results."""
        # Mock search_hybrid to return empty results
        context_with_manager.rag_manager.search_hybrid = AsyncMock(return_value=([], False))

        cmd = RAGSearchCommand()
        parsed = MockParsedCommand(args=["test", "query"])

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context_with_manager)
        )

        assert result.success is True
        assert "No matches found" in result.output

    def test_search_command_with_results(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test search command with results."""
        # Create mock search result
        mock_result = MagicMock()
        mock_result.document = MagicMock(path="test.py")
        mock_result.chunk = MagicMock(start_line=1, end_line=10)
        mock_result.score = 0.95
        mock_result.snippet = "def test_function(): pass"

        # Mock search_hybrid to return results
        context_with_manager.rag_manager.search_hybrid = AsyncMock(
            return_value=([mock_result], False)
        )

        cmd = RAGSearchCommand()
        parsed = MockParsedCommand(args=["test"])

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context_with_manager)
        )

        assert result.success is True
        assert "1 results" in result.output
        assert "test.py" in result.output

    def test_status_command_success(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test status command executes successfully."""
        cmd = RAGStatusCommand()
        parsed = MockParsedCommand()

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context_with_manager)
        )

        assert result.success is True
        assert "OK" in result.output

    def test_clear_command_success(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test clear command executes successfully."""
        cmd = RAGClearCommand()
        parsed = MockParsedCommand()

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context_with_manager)
        )

        assert result.success is True
        assert "10" in result.output  # Number cleared

    def test_rag_command_default_shows_status(
        self, context_with_manager: MockCommandContext
    ) -> None:
        """Test /rag without subcommand shows status."""
        cmd = RAGCommand()
        parsed = MockParsedCommand(subcommand=None)

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute_default(parsed, context_with_manager)
        )

        assert result.success is True

    def test_config_command_default_shows_config(self) -> None:
        """Test /rag config without subcommand shows config."""
        cmd = RAGConfigCommand()
        parsed = MockParsedCommand(subcommand=None)
        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute_default(parsed, context)
        )

        assert result.success is True


class TestRAGCommandsErrorHandling:
    """Tests for RAG commands error handling."""

    def test_index_command_disabled(self) -> None:
        """Test index command when RAG is disabled."""
        cmd = RAGIndexCommand()
        parsed = MockParsedCommand()

        manager = MagicMock()
        manager.is_enabled = False

        rag_config = RAGConfig(enabled=False)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_search_command_disabled(self) -> None:
        """Test search command when RAG is disabled."""
        cmd = RAGSearchCommand()
        parsed = MockParsedCommand(args=["test"])

        manager = MagicMock()
        manager.is_enabled = False

        rag_config = RAGConfig(enabled=False)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_clear_command_disabled(self) -> None:
        """Test clear command when RAG is disabled."""
        cmd = RAGClearCommand()
        parsed = MockParsedCommand()

        manager = MagicMock()
        manager.is_enabled = False

        rag_config = RAGConfig(enabled=False)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_index_command_exception(self) -> None:
        """Test index command handles exceptions."""
        from unittest.mock import AsyncMock

        cmd = RAGIndexCommand()
        parsed = MockParsedCommand(flags=set())

        manager = MagicMock()
        manager.is_enabled = True
        manager.index_project = AsyncMock(side_effect=Exception("Index error"))

        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "failed" in result.error.lower()

    def test_search_command_exception(self) -> None:
        """Test search command handles exceptions."""
        from unittest.mock import AsyncMock

        cmd = RAGSearchCommand()
        parsed = MockParsedCommand(args=["test"])

        manager = MagicMock()
        manager.is_enabled = True
        manager.search = AsyncMock(side_effect=Exception("Search error"))

        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "failed" in result.error.lower()

    def test_status_command_exception(self) -> None:
        """Test status command handles exceptions."""
        from unittest.mock import AsyncMock

        cmd = RAGStatusCommand()
        parsed = MockParsedCommand()

        manager = MagicMock()
        manager.get_status = AsyncMock(side_effect=Exception("Status error"))

        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "failed" in result.error.lower()

    def test_clear_command_exception(self) -> None:
        """Test clear command handles exceptions."""
        from unittest.mock import AsyncMock

        cmd = RAGClearCommand()
        parsed = MockParsedCommand()

        manager = MagicMock()
        manager.is_enabled = True
        manager.clear_index = AsyncMock(side_effect=Exception("Clear error"))

        rag_config = RAGConfig(enabled=True)
        context = MockCommandContext(
            config=MockCodeForgeConfig(rag=rag_config),
            rag_manager=manager,
        )

        result = asyncio.get_event_loop().run_until_complete(
            cmd.execute(parsed, context)
        )

        assert result.success is False
        assert "failed" in result.error.lower()
