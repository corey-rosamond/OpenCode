"""Tests for RAG integration module."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_forge.rag.config import RAGConfig
from code_forge.rag.embeddings import MockEmbeddingProvider
from code_forge.rag.integration import (
    RAGContextAugmenter,
    RAGMessageProcessor,
    create_augmenter,
)
from code_forge.rag.manager import RAGManager
from code_forge.rag.vectorstore import MockVectorStore


@pytest.fixture
def mock_providers():
    """Patch the provider factory functions to use mock implementations."""
    with patch(
        "code_forge.rag.manager.get_embedding_provider",
        return_value=MockEmbeddingProvider(),
    ) as mock_embed, patch(
        "code_forge.rag.manager.get_vector_store",
        return_value=MockVectorStore(),
    ) as mock_store:
        yield mock_embed, mock_store


class TestRAGContextAugmenter:
    """Tests for RAGContextAugmenter."""

    @pytest.fixture
    def mock_manager(
        self, tmp_path: Path, mock_providers: tuple
    ) -> RAGManager:
        """Create a mock RAG manager."""
        config = RAGConfig(enabled=True)
        manager = RAGManager(project_root=tmp_path, config=config)
        return manager

    @pytest.fixture
    def disabled_manager(self, tmp_path: Path) -> RAGManager:
        """Create a disabled RAG manager."""
        config = RAGConfig(enabled=False)
        return RAGManager(project_root=tmp_path, config=config)

    def test_augmenter_creation(self, mock_manager: RAGManager) -> None:
        """Test augmenter can be created."""
        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        assert augmenter.rag_manager == mock_manager
        assert augmenter.context_manager is None
        assert augmenter.auto_augment is True

    def test_is_enabled_when_rag_enabled(self, mock_manager: RAGManager) -> None:
        """Test is_enabled when RAG is enabled."""
        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            auto_augment=True,
        )

        assert augmenter.is_enabled is True

    def test_is_enabled_when_rag_disabled(self, disabled_manager: RAGManager) -> None:
        """Test is_enabled when RAG is disabled."""
        augmenter = RAGContextAugmenter(
            rag_manager=disabled_manager,
            auto_augment=True,
        )

        assert augmenter.is_enabled is False

    def test_is_enabled_when_auto_augment_off(self, mock_manager: RAGManager) -> None:
        """Test is_enabled when auto_augment is off."""
        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            auto_augment=False,
        )

        assert augmenter.is_enabled is False

    def test_augment_for_query_disabled(self, disabled_manager: RAGManager) -> None:
        """Test augmentation when disabled."""
        augmenter = RAGContextAugmenter(rag_manager=disabled_manager)

        tokens = asyncio.get_event_loop().run_until_complete(
            augmenter.augment_for_query("test query")
        )

        assert tokens == 0

    def test_augment_for_query_no_results(self, mock_manager: RAGManager) -> None:
        """Test augmentation with no results."""
        asyncio.get_event_loop().run_until_complete(mock_manager.initialize())
        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        tokens = asyncio.get_event_loop().run_until_complete(
            augmenter.augment_for_query("test query")
        )

        assert tokens == 0

    def test_get_context_for_query_disabled(
        self, disabled_manager: RAGManager
    ) -> None:
        """Test getting context when disabled."""
        augmenter = RAGContextAugmenter(rag_manager=disabled_manager)

        context = asyncio.get_event_loop().run_until_complete(
            augmenter.get_context_for_query("test query")
        )

        assert context == ""

    def test_get_last_augmentation_stats(self, mock_manager: RAGManager) -> None:
        """Test getting augmentation stats."""
        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        stats = augmenter.get_last_augmentation_stats()

        assert "last_query" in stats
        assert "tokens_added" in stats
        assert stats["last_query"] is None
        assert stats["tokens_added"] == 0

    def test_set_context_manager(self, mock_manager: RAGManager) -> None:
        """Test setting context manager."""
        augmenter = RAGContextAugmenter(rag_manager=mock_manager)
        mock_context = MagicMock()

        augmenter.set_context_manager(mock_context)

        assert augmenter.context_manager == mock_context

    def test_count_tokens_without_context_manager(
        self, mock_manager: RAGManager
    ) -> None:
        """Test token counting without context manager."""
        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        # Use internal method
        count = augmenter._count_tokens("Hello, world!")

        # Should return estimate (len / 4)
        assert count > 0

    def test_count_tokens_with_context_manager(
        self, mock_manager: RAGManager
    ) -> None:
        """Test token counting with context manager."""
        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        # Mock context manager with counter
        mock_context = MagicMock()
        mock_context.counter.count.return_value = 42
        augmenter.context_manager = mock_context

        count = augmenter._count_tokens("test")

        assert count == 42


class TestRAGMessageProcessor:
    """Tests for RAGMessageProcessor."""

    @pytest.fixture
    def processor(
        self, tmp_path: Path, mock_providers: tuple
    ) -> RAGMessageProcessor:
        """Create a message processor."""
        config = RAGConfig(enabled=True)
        manager = RAGManager(project_root=tmp_path, config=config)
        return RAGMessageProcessor(rag_manager=manager)

    @pytest.fixture
    def disabled_processor(self, tmp_path: Path) -> RAGMessageProcessor:
        """Create a processor with disabled RAG."""
        config = RAGConfig(enabled=False)
        manager = RAGManager(project_root=tmp_path, config=config)
        return RAGMessageProcessor(rag_manager=manager)

    def test_processor_creation(self, processor: RAGMessageProcessor) -> None:
        """Test processor can be created."""
        assert processor.min_query_length == 10
        assert len(processor.skip_patterns) > 0

    def test_should_augment_disabled(
        self, disabled_processor: RAGMessageProcessor
    ) -> None:
        """Test should_augment when disabled."""
        assert disabled_processor.should_augment("some query text") is False

    def test_should_augment_short_message(
        self, processor: RAGMessageProcessor
    ) -> None:
        """Test should_augment with short message."""
        assert processor.should_augment("hi") is False
        assert processor.should_augment("test") is False

    def test_should_augment_command(self, processor: RAGMessageProcessor) -> None:
        """Test should_augment with command."""
        assert processor.should_augment("/help") is False
        assert processor.should_augment("/rag status") is False

    def test_should_augment_greeting(self, processor: RAGMessageProcessor) -> None:
        """Test should_augment with greeting."""
        assert processor.should_augment("hello") is False
        assert processor.should_augment("hi there") is False

    def test_should_augment_acknowledgment(
        self, processor: RAGMessageProcessor
    ) -> None:
        """Test should_augment with acknowledgment."""
        assert processor.should_augment("yes") is False
        assert processor.should_augment("no") is False
        assert processor.should_augment("ok") is False
        assert processor.should_augment("thanks") is False

    def test_should_augment_valid_query(
        self, processor: RAGMessageProcessor
    ) -> None:
        """Test should_augment with valid query."""
        assert processor.should_augment("How does authentication work?") is True
        assert processor.should_augment("Find the user login function") is True
        assert processor.should_augment("Where is the API endpoint defined?") is True

    def test_extract_query(self, processor: RAGMessageProcessor) -> None:
        """Test extracting query from message."""
        query = processor.extract_query("  How does auth work?  ")

        assert query == "How does auth work?"


class TestRAGContextAugmenterWithContext:
    """Tests for RAGContextAugmenter with context manager integration."""

    @pytest.fixture
    def mock_manager(
        self, tmp_path: Path, mock_providers: tuple
    ) -> RAGManager:
        """Create a mock RAG manager."""
        config = RAGConfig(enabled=True)
        manager = RAGManager(project_root=tmp_path, config=config)
        return manager

    def test_augment_for_query_with_context_manager(
        self, mock_manager: RAGManager
    ) -> None:
        """Test augmentation adds to context manager."""
        # Mock context manager
        mock_context = MagicMock()
        mock_context.counter.count.return_value = 50
        mock_context.add_message = MagicMock()

        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=mock_context,
        )

        # Initialize manager
        asyncio.get_event_loop().run_until_complete(mock_manager.initialize())

        tokens = asyncio.get_event_loop().run_until_complete(
            augmenter.augment_for_query("test query")
        )

        # Should return 0 since no results in empty index
        assert tokens == 0

    def test_get_context_for_query_with_results(
        self, mock_manager: RAGManager, tmp_path: Path
    ) -> None:
        """Test getting context with initialized manager."""
        asyncio.get_event_loop().run_until_complete(mock_manager.initialize())

        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        context = asyncio.get_event_loop().run_until_complete(
            augmenter.get_context_for_query("test query")
        )

        # Empty index returns empty context
        assert context == ""

    def test_add_to_context_called(
        self, mock_manager: RAGManager
    ) -> None:
        """Test _add_to_context method is called when context manager exists."""
        mock_context = MagicMock()
        mock_context.counter.count.return_value = 10
        mock_context.add_message = MagicMock()

        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=mock_context,
        )

        # Call _add_to_context directly
        augmenter._add_to_context("test context")

        # Verify add_message was called
        mock_context.add_message.assert_called_once()
        call_args = mock_context.add_message.call_args[0][0]
        assert call_args["role"] == "system"
        assert "[RAG Context]" in call_args["content"]

    def test_add_to_context_handles_exception(
        self, mock_manager: RAGManager
    ) -> None:
        """Test _add_to_context handles exceptions gracefully."""
        mock_context = MagicMock()
        mock_context.add_message.side_effect = Exception("Context error")

        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=mock_context,
        )

        # Should not raise
        augmenter._add_to_context("test context")

    def test_add_to_context_none_manager(
        self, mock_manager: RAGManager
    ) -> None:
        """Test _add_to_context with no context manager."""
        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=None,
        )

        # Should not raise
        augmenter._add_to_context("test context")

    def test_count_tokens_exception_handling(
        self, mock_manager: RAGManager
    ) -> None:
        """Test token counting handles exceptions."""
        mock_context = MagicMock()
        mock_context.counter.count.side_effect = Exception("Count error")

        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=mock_context,
        )

        # Should fall back to estimate
        count = augmenter._count_tokens("test text here")
        assert count > 0  # len("test text here") // 4 = 3

    def test_augment_for_query_with_results(
        self, mock_manager: RAGManager
    ) -> None:
        """Test augmentation when results are found."""
        from unittest.mock import AsyncMock

        # Mock augment_context to return actual content
        mock_manager.augment_context = AsyncMock(return_value="Relevant code context")

        mock_context = MagicMock()
        mock_context.counter.count.return_value = 25
        mock_context.add_message = MagicMock()

        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=mock_context,
        )

        tokens = asyncio.get_event_loop().run_until_complete(
            augmenter.augment_for_query("how does auth work?")
        )

        assert tokens == 25
        assert augmenter._last_query == "how does auth work?"
        assert augmenter._last_tokens_added == 25
        mock_context.add_message.assert_called_once()

    def test_augment_for_query_exception_handling(
        self, mock_manager: RAGManager
    ) -> None:
        """Test augmentation handles exceptions."""
        from unittest.mock import AsyncMock

        # Mock augment_context to raise
        mock_manager.augment_context = AsyncMock(side_effect=Exception("RAG error"))

        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        tokens = asyncio.get_event_loop().run_until_complete(
            augmenter.augment_for_query("test query")
        )

        # Should return 0 on error
        assert tokens == 0

    def test_get_context_for_query_exception_handling(
        self, mock_manager: RAGManager
    ) -> None:
        """Test get_context_for_query handles exceptions."""
        from unittest.mock import AsyncMock

        # Mock augment_context to raise
        mock_manager.augment_context = AsyncMock(side_effect=Exception("RAG error"))

        augmenter = RAGContextAugmenter(rag_manager=mock_manager)

        context = asyncio.get_event_loop().run_until_complete(
            augmenter.get_context_for_query("test query")
        )

        # Should return empty on error
        assert context == ""

    def test_augment_for_query_without_adding_to_context(
        self, mock_manager: RAGManager
    ) -> None:
        """Test augmentation without adding to context manager."""
        from unittest.mock import AsyncMock

        # Mock augment_context to return content
        mock_manager.augment_context = AsyncMock(return_value="Code context")

        mock_context = MagicMock()
        mock_context.counter.count.return_value = 20

        augmenter = RAGContextAugmenter(
            rag_manager=mock_manager,
            context_manager=mock_context,
        )

        tokens = asyncio.get_event_loop().run_until_complete(
            augmenter.augment_for_query("test", add_to_context=False)
        )

        # Should count but not add to context
        assert tokens == 20
        mock_context.add_message.assert_not_called()


class TestCreateAugmenter:
    """Tests for create_augmenter factory function."""

    def test_create_augmenter(
        self, tmp_path: Path, mock_providers: tuple
    ) -> None:
        """Test creating augmenter with factory function."""
        config = RAGConfig(enabled=True, auto_index=True)
        manager = RAGManager(project_root=tmp_path, config=config)

        augmenter = create_augmenter(manager)

        assert augmenter.rag_manager == manager
        assert augmenter.auto_augment is True

    def test_create_augmenter_with_context_manager(
        self, tmp_path: Path, mock_providers: tuple
    ) -> None:
        """Test creating augmenter with context manager."""
        config = RAGConfig(enabled=True)
        manager = RAGManager(project_root=tmp_path, config=config)
        mock_context = MagicMock()

        augmenter = create_augmenter(manager, context_manager=mock_context)

        assert augmenter.context_manager == mock_context

    def test_create_augmenter_auto_augment_from_config(
        self, tmp_path: Path, mock_providers: tuple
    ) -> None:
        """Test that auto_augment is set from config.auto_index."""
        config = RAGConfig(enabled=True, auto_index=False)
        manager = RAGManager(project_root=tmp_path, config=config)

        augmenter = create_augmenter(manager)

        assert augmenter.auto_augment is False
