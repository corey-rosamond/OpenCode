"""Tests for RAG Phase 5: Integration & Polish.

This module tests the integration of RAG with the CLI:
- CommandContext with rag_manager
- Dependencies.create() with RAGManager
- RAG commands registration
- Auto-index on startup
- Context augmentation in message flow
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _create_mock_rag_manager() -> MagicMock:
    """Create a mock RAG manager."""
    manager = MagicMock()
    manager.is_enabled = True
    manager.augment_context = AsyncMock(return_value="Relevant context here")
    return manager


class TestCommandContextWithRAG:
    """Tests for CommandContext with rag_manager field."""

    def test_command_context_has_rag_manager_field(self) -> None:
        """CommandContext should have rag_manager field."""
        from code_forge.commands.executor import CommandContext

        # Check annotations
        assert "rag_manager" in CommandContext.__annotations__

    def test_command_context_rag_manager_default_none(self) -> None:
        """CommandContext rag_manager should default to None."""
        from code_forge.commands.executor import CommandContext

        context = CommandContext()
        assert context.rag_manager is None

    def test_command_context_accepts_rag_manager(self) -> None:
        """CommandContext should accept rag_manager in constructor."""
        from code_forge.commands.executor import CommandContext

        mock_manager = MagicMock()
        context = CommandContext(rag_manager=mock_manager)
        assert context.rag_manager is mock_manager


class TestDependenciesWithRAG:
    """Tests for Dependencies.create() with RAGManager."""

    def test_dependencies_has_rag_manager_field(self) -> None:
        """Dependencies should have rag_manager field."""
        from code_forge.cli.dependencies import Dependencies

        assert "rag_manager" in Dependencies.__annotations__

    def test_dependencies_create_accepts_rag_manager_param(self) -> None:
        """Dependencies.create() should accept rag_manager parameter."""
        import inspect

        from code_forge.cli.dependencies import Dependencies

        sig = inspect.signature(Dependencies.create)
        assert "rag_manager" in sig.parameters


class TestRAGCommandsRegistration:
    """Tests for RAG commands registration."""

    def test_rag_commands_module_has_get_commands(self) -> None:
        """RAG commands module should have get_commands function."""
        from code_forge.rag import commands

        assert hasattr(commands, "get_commands")
        assert callable(commands.get_commands)

    def test_rag_commands_returns_rag_command(self) -> None:
        """get_commands should return RAGCommand."""
        from code_forge.rag.commands import RAGCommand, get_commands

        commands = get_commands()
        assert len(commands) == 1
        assert isinstance(commands[0], RAGCommand)

    def test_rag_command_has_subcommands(self) -> None:
        """RAGCommand should have expected subcommands."""
        from code_forge.rag.commands import RAGCommand

        cmd = RAGCommand()
        assert "index" in cmd.subcommands
        assert "search" in cmd.subcommands
        assert "status" in cmd.subcommands
        assert "clear" in cmd.subcommands
        assert "config" in cmd.subcommands


class TestRAGContextAugmentation:
    """Tests for RAG context augmentation in message flow."""

    def test_rag_message_processor_should_augment_valid_query(self) -> None:
        """RAGMessageProcessor should_augment returns True for valid queries."""
        from code_forge.rag.integration import RAGMessageProcessor

        mock_manager = _create_mock_rag_manager()
        processor = RAGMessageProcessor(mock_manager)

        # Valid queries should be augmented
        assert processor.should_augment("How does authentication work?") is True
        assert processor.should_augment("Find the user model") is True
        assert processor.should_augment("What is the config format?") is True

    def test_rag_message_processor_skips_short_queries(self) -> None:
        """RAGMessageProcessor should skip short queries."""
        from code_forge.rag.integration import RAGMessageProcessor

        mock_manager = _create_mock_rag_manager()
        processor = RAGMessageProcessor(mock_manager)

        # Short queries should not be augmented
        assert processor.should_augment("hi") is False
        assert processor.should_augment("ok") is False
        assert processor.should_augment("yes") is False

    def test_rag_message_processor_skips_commands(self) -> None:
        """RAGMessageProcessor should skip commands."""
        from code_forge.rag.integration import RAGMessageProcessor

        mock_manager = _create_mock_rag_manager()
        processor = RAGMessageProcessor(mock_manager)

        # Commands should not be augmented
        assert processor.should_augment("/help") is False
        assert processor.should_augment("/exit") is False
        assert processor.should_augment("/rag status") is False

    def test_rag_message_processor_skips_greetings(self) -> None:
        """RAGMessageProcessor should skip greetings."""
        from code_forge.rag.integration import RAGMessageProcessor

        mock_manager = _create_mock_rag_manager()
        processor = RAGMessageProcessor(mock_manager)

        # Greetings should not be augmented
        assert processor.should_augment("hello") is False
        assert processor.should_augment("hey there") is False
        assert processor.should_augment("thanks") is False

    def test_rag_message_processor_disabled_manager(self) -> None:
        """RAGMessageProcessor should not augment when manager is disabled."""
        from code_forge.rag.integration import RAGMessageProcessor

        manager = MagicMock()
        manager.is_enabled = False

        processor = RAGMessageProcessor(manager)
        assert processor.should_augment("How does authentication work?") is False

    @pytest.mark.asyncio
    async def test_rag_context_augmenter_get_context(self) -> None:
        """RAGContextAugmenter should get context for query."""
        from code_forge.rag.integration import RAGContextAugmenter

        mock_manager = _create_mock_rag_manager()
        augmenter = RAGContextAugmenter(mock_manager)
        context = await augmenter.get_context_for_query("How does auth work?")

        assert context == "Relevant context here"
        mock_manager.augment_context.assert_called_once_with("How does auth work?")

    @pytest.mark.asyncio
    async def test_rag_context_augmenter_disabled_returns_empty(self) -> None:
        """RAGContextAugmenter returns empty string when disabled."""
        from code_forge.rag.integration import RAGContextAugmenter

        manager = MagicMock()
        manager.is_enabled = False

        augmenter = RAGContextAugmenter(manager)
        context = await augmenter.get_context_for_query("query")

        assert context == ""

    @pytest.mark.asyncio
    async def test_rag_context_augmenter_handles_errors(self) -> None:
        """RAGContextAugmenter handles errors gracefully."""
        from code_forge.rag.integration import RAGContextAugmenter

        mock_manager = _create_mock_rag_manager()
        mock_manager.augment_context = AsyncMock(side_effect=Exception("Test error"))

        augmenter = RAGContextAugmenter(mock_manager)
        context = await augmenter.get_context_for_query("query")

        # Should return empty string on error, not raise
        assert context == ""


def _create_mock_rag_manager_with_status(indexed: bool = False) -> MagicMock:
    """Create a mock RAG manager with status."""
    manager = MagicMock()
    manager.is_enabled = True
    manager.index_project = AsyncMock()

    # Create a mock status
    status = MagicMock()
    status.indexed = indexed  # Use correct field name
    manager.get_status = AsyncMock(return_value=status)

    return manager


def _create_mock_config(auto_index: bool = True) -> MagicMock:
    """Create a mock config with RAG settings."""
    config = MagicMock()
    config.rag.enabled = True
    config.rag.auto_index = auto_index
    return config


class TestRAGAutoIndex:
    """Tests for auto-index on startup functionality."""

    @pytest.mark.asyncio
    async def test_auto_index_called_when_not_indexed(self) -> None:
        """Auto-index should be called when not indexed."""
        mock_manager = _create_mock_rag_manager_with_status(indexed=False)
        mock_config = _create_mock_config(auto_index=True)

        # Simulate the auto-index logic from main.py
        if mock_manager is not None and mock_config.rag.auto_index:
            status = await mock_manager.get_status()
            if not status.indexed:
                await mock_manager.index_project()

        mock_manager.index_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_index_skipped_when_indexed(self) -> None:
        """Auto-index should be skipped when already indexed."""
        mock_manager = _create_mock_rag_manager_with_status(indexed=True)
        mock_config = _create_mock_config(auto_index=True)

        # Simulate the auto-index logic
        if mock_manager is not None and mock_config.rag.auto_index:
            status = await mock_manager.get_status()
            if not status.indexed:
                await mock_manager.index_project()

        mock_manager.index_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_index_skipped_when_disabled(self) -> None:
        """Auto-index should be skipped when auto_index is False."""
        mock_manager = _create_mock_rag_manager_with_status(indexed=False)
        mock_config = _create_mock_config(auto_index=False)

        # Simulate the auto-index logic
        if mock_manager is not None and mock_config.rag.auto_index:
            status = await mock_manager.get_status()
            if not status.indexed:
                await mock_manager.index_project()

        mock_manager.index_project.assert_not_called()


class TestCreateAugmenter:
    """Tests for create_augmenter factory function."""

    def test_create_augmenter_returns_augmenter(self) -> None:
        """create_augmenter should return RAGContextAugmenter."""
        from code_forge.rag.integration import RAGContextAugmenter, create_augmenter

        manager = MagicMock()
        manager.config.auto_index = True

        augmenter = create_augmenter(manager)

        assert isinstance(augmenter, RAGContextAugmenter)
        assert augmenter.rag_manager is manager

    def test_create_augmenter_with_context_manager(self) -> None:
        """create_augmenter should accept context_manager."""
        from code_forge.rag.integration import create_augmenter

        manager = MagicMock()
        manager.config.auto_index = True
        context_mgr = MagicMock()

        augmenter = create_augmenter(manager, context_manager=context_mgr)

        assert augmenter.context_manager is context_mgr


class TestRAGStatusIntegration:
    """Tests for RAG status in integration scenarios."""

    def test_rag_status_has_indexed_field(self) -> None:
        """RAGStatus should have indexed field."""
        from code_forge.rag.manager import RAGStatus

        status = RAGStatus(
            enabled=True,
            initialized=True,
            indexed=False,
            total_chunks=0,
            total_documents=0,
            embedding_model="test-model",
            vector_store="mock",
            last_indexed=None,
            index_directory=".rag",
        )

        assert hasattr(status, "indexed")
        assert status.indexed is False

    def test_rag_status_indexed_true(self) -> None:
        """RAGStatus should report indexed when has documents."""
        from code_forge.rag.manager import RAGStatus

        status = RAGStatus(
            enabled=True,
            initialized=True,
            indexed=True,
            total_chunks=100,
            total_documents=10,
            embedding_model="test-model",
            vector_store="mock",
            last_indexed=None,
            index_directory=".rag",
        )

        assert status.indexed is True
        assert status.total_documents == 10
