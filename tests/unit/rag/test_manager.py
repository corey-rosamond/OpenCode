"""Tests for RAG manager."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_forge.rag.config import RAGConfig
from code_forge.rag.embeddings import MockEmbeddingProvider
from code_forge.rag.manager import RAGManager, RAGStatus
from code_forge.rag.vectorstore import MockVectorStore


class TestRAGStatus:
    """Tests for RAGStatus dataclass."""

    def test_create_status(self) -> None:
        """Test creating a RAGStatus."""
        status = RAGStatus(
            enabled=True,
            initialized=True,
            indexed=True,
            total_chunks=100,
            total_documents=20,
            embedding_model="test-model",
            vector_store="mock",
            last_indexed=None,
            index_directory=".forge/index",
        )

        assert status.enabled is True
        assert status.initialized is True
        assert status.indexed is True
        assert status.total_chunks == 100
        assert status.total_documents == 20
        assert status.embedding_model == "test-model"
        assert status.vector_store == "mock"

    def test_status_disabled(self) -> None:
        """Test status when disabled."""
        status = RAGStatus(
            enabled=False,
            initialized=False,
            indexed=False,
            total_chunks=0,
            total_documents=0,
            embedding_model="",
            vector_store="",
            last_indexed=None,
            index_directory=".forge/index",
        )

        assert status.enabled is False
        assert status.indexed is False


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


class TestRAGManager:
    """Tests for RAGManager."""

    @pytest.fixture
    def manager(self, tmp_path: Path, mock_providers: tuple) -> RAGManager:
        """Create a RAGManager for testing."""
        config = RAGConfig(
            enabled=True,
            include_patterns=["**/*.py"],
        )
        return RAGManager(project_root=tmp_path, config=config)

    @pytest.fixture
    def disabled_manager(self, tmp_path: Path) -> RAGManager:
        """Create a disabled RAGManager."""
        config = RAGConfig(enabled=False)
        return RAGManager(project_root=tmp_path, config=config)

    def test_manager_creation(self, manager: RAGManager, tmp_path: Path) -> None:
        """Test manager can be created."""
        assert manager.project_root == tmp_path
        assert manager.config is not None
        assert manager.is_enabled is True
        assert manager.is_initialized is False

    def test_disabled_manager(self, disabled_manager: RAGManager) -> None:
        """Test disabled manager properties."""
        assert disabled_manager.is_enabled is False

    def test_initialize_disabled(self, disabled_manager: RAGManager) -> None:
        """Test initialization skips when disabled."""
        asyncio.get_event_loop().run_until_complete(
            disabled_manager.initialize()
        )

        # Should remain not initialized
        assert disabled_manager.is_initialized is False

    def test_initialize_enabled(self, manager: RAGManager) -> None:
        """Test initialization when enabled."""
        asyncio.get_event_loop().run_until_complete(
            manager.initialize()
        )

        assert manager.is_initialized is True

    def test_index_project(self, manager: RAGManager, tmp_path: Path) -> None:
        """Test indexing a project."""
        # Create a Python file
        py_file = tmp_path / "main.py"
        py_file.write_text('''def hello():
    """Say hello."""
    print("Hello, world!")
    return True
''')

        stats = asyncio.get_event_loop().run_until_complete(
            manager.index_project()
        )

        assert stats.total_chunks >= 0

    def test_index_project_disabled(self, disabled_manager: RAGManager) -> None:
        """Test indexing fails when disabled."""
        with pytest.raises(RuntimeError, match="not enabled"):
            asyncio.get_event_loop().run_until_complete(
                disabled_manager.index_project()
            )

    def test_search_empty(self, manager: RAGManager) -> None:
        """Test search on empty index."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        results = asyncio.get_event_loop().run_until_complete(
            manager.search("test query")
        )

        assert results == []

    def test_search_disabled(self, disabled_manager: RAGManager) -> None:
        """Test search fails when disabled."""
        with pytest.raises(RuntimeError, match="not enabled"):
            asyncio.get_event_loop().run_until_complete(
                disabled_manager.search("test")
            )

    def test_search_code(self, manager: RAGManager) -> None:
        """Test search_code method."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        results = asyncio.get_event_loop().run_until_complete(
            manager.search_code("function", languages=["python"])
        )

        assert isinstance(results, list)

    def test_search_docs(self, manager: RAGManager) -> None:
        """Test search_docs method."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        results = asyncio.get_event_loop().run_until_complete(
            manager.search_docs("documentation")
        )

        assert isinstance(results, list)

    def test_augment_context_empty(self, manager: RAGManager) -> None:
        """Test augment_context on empty index."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        context = asyncio.get_event_loop().run_until_complete(
            manager.augment_context("test query")
        )

        assert context == ""

    def test_clear_index(self, manager: RAGManager, tmp_path: Path) -> None:
        """Test clearing the index."""
        # Index a file first
        py_file = tmp_path / "test.py"
        py_file.write_text('''def test():
    """Test function."""
    return True
''')

        asyncio.get_event_loop().run_until_complete(manager.index_project())

        # Clear the index
        count = asyncio.get_event_loop().run_until_complete(
            manager.clear_index()
        )

        assert count >= 0

    def test_get_status_disabled(self, disabled_manager: RAGManager) -> None:
        """Test getting status when disabled."""
        status = asyncio.get_event_loop().run_until_complete(
            disabled_manager.get_status()
        )

        assert status.enabled is False
        assert status.initialized is False

    def test_get_status_not_initialized(self, manager: RAGManager) -> None:
        """Test getting status before initialization."""
        status = asyncio.get_event_loop().run_until_complete(
            manager.get_status()
        )

        assert status.enabled is True
        assert status.initialized is False

    def test_get_status_initialized(self, manager: RAGManager) -> None:
        """Test getting status after initialization."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        status = asyncio.get_event_loop().run_until_complete(
            manager.get_status()
        )

        assert status.enabled is True
        assert status.initialized is True

    def test_format_status_disabled(self, manager: RAGManager) -> None:
        """Test formatting disabled status."""
        status = RAGStatus(
            enabled=False,
            initialized=False,
            indexed=False,
            total_chunks=0,
            total_documents=0,
            embedding_model="",
            vector_store="",
            last_indexed=None,
            index_directory=".forge/index",
        )

        formatted = manager.format_status(status)

        assert "disabled" in formatted.lower()

    def test_format_status_indexed(self, manager: RAGManager) -> None:
        """Test formatting indexed status."""
        status = RAGStatus(
            enabled=True,
            initialized=True,
            indexed=True,
            total_chunks=100,
            total_documents=20,
            embedding_model="test-model",
            vector_store="mock",
            last_indexed=None,
            index_directory=".forge/index",
        )

        formatted = manager.format_status(status)

        assert "100" in formatted
        assert "test-model" in formatted

    def test_index_file(self, manager: RAGManager, tmp_path: Path) -> None:
        """Test indexing a single file."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        py_file = tmp_path / "single.py"
        py_file.write_text('''def single():
    """Single function."""
    return True
''')

        count = asyncio.get_event_loop().run_until_complete(
            manager.index_file(py_file)
        )

        assert count >= 0

    def test_remove_file(self, manager: RAGManager, tmp_path: Path) -> None:
        """Test removing a file from index."""
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        py_file = tmp_path / "remove.py"
        py_file.write_text('''def remove():
    """To be removed."""
    return True
''')

        # Index and remove
        asyncio.get_event_loop().run_until_complete(manager.index_file(py_file))
        count = asyncio.get_event_loop().run_until_complete(
            manager.remove_file(py_file)
        )

        assert count >= 0


class TestRAGManagerEdgeCases:
    """Edge case tests for RAGManager."""

    def test_double_initialization(self, tmp_path: Path, mock_providers: tuple) -> None:
        """Test that double initialization is handled."""
        config = RAGConfig(enabled=True)
        manager = RAGManager(project_root=tmp_path, config=config)

        asyncio.get_event_loop().run_until_complete(manager.initialize())
        asyncio.get_event_loop().run_until_complete(manager.initialize())

        assert manager.is_initialized is True

    def test_index_empty_project(
        self, tmp_path: Path, mock_providers: tuple
    ) -> None:
        """Test indexing empty project."""
        config = RAGConfig(
            enabled=True,
            include_patterns=["**/*.py"],
        )
        manager = RAGManager(project_root=tmp_path, config=config)

        stats = asyncio.get_event_loop().run_until_complete(
            manager.index_project()
        )

        assert stats.total_chunks == 0

    def test_force_reindex(self, tmp_path: Path, mock_providers: tuple) -> None:
        """Test force reindexing."""
        config = RAGConfig(
            enabled=True,
            include_patterns=["**/*.py"],
        )
        manager = RAGManager(project_root=tmp_path, config=config)

        py_file = tmp_path / "main.py"
        py_file.write_text('''def main():
    """Main function."""
    return True
''')

        # Index twice, second with force
        asyncio.get_event_loop().run_until_complete(manager.index_project())
        asyncio.get_event_loop().run_until_complete(manager.index_project(force=True))

        # Should complete without error
        assert manager.is_initialized is True
