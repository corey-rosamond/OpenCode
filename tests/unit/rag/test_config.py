"""Tests for RAG configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from code_forge.rag.config import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDE_PATTERNS,
    EmbeddingProviderType,
    RAGConfig,
    VectorStoreType,
)


class TestEmbeddingProviderType:
    """Tests for EmbeddingProviderType enum."""

    def test_all_types_exist(self) -> None:
        """Test all provider types are defined."""
        assert EmbeddingProviderType.LOCAL.value == "local"
        assert EmbeddingProviderType.OPENAI.value == "openai"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert EmbeddingProviderType("local") == EmbeddingProviderType.LOCAL
        assert EmbeddingProviderType("openai") == EmbeddingProviderType.OPENAI


class TestVectorStoreType:
    """Tests for VectorStoreType enum."""

    def test_all_types_exist(self) -> None:
        """Test all store types are defined."""
        assert VectorStoreType.CHROMA.value == "chroma"
        assert VectorStoreType.FAISS.value == "faiss"


class TestDefaultPatterns:
    """Tests for default include/exclude patterns."""

    def test_include_patterns_has_common_extensions(self) -> None:
        """Test default include patterns have common file types."""
        assert "**/*.py" in DEFAULT_INCLUDE_PATTERNS
        assert "**/*.js" in DEFAULT_INCLUDE_PATTERNS
        assert "**/*.ts" in DEFAULT_INCLUDE_PATTERNS
        assert "**/*.md" in DEFAULT_INCLUDE_PATTERNS

    def test_exclude_patterns_has_common_dirs(self) -> None:
        """Test default exclude patterns have common dirs."""
        assert "**/node_modules/**" in DEFAULT_EXCLUDE_PATTERNS
        assert "**/.git/**" in DEFAULT_EXCLUDE_PATTERNS
        assert "**/__pycache__/**" in DEFAULT_EXCLUDE_PATTERNS
        assert "**/.venv/**" in DEFAULT_EXCLUDE_PATTERNS


class TestRAGConfig:
    """Tests for RAGConfig model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RAGConfig()
        assert config.enabled is True
        assert config.auto_index is True
        assert config.watch_files is True
        assert config.embedding_provider == EmbeddingProviderType.LOCAL
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.vector_store == VectorStoreType.CHROMA
        assert config.index_directory == ".forge/index"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 100
        assert config.default_max_results == 5
        assert config.default_min_score == 0.5
        assert config.context_token_budget == 4000

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RAGConfig(
            enabled=False,
            embedding_provider=EmbeddingProviderType.OPENAI,
            embedding_model="custom-model",
            chunk_size=500,
            default_max_results=10,
        )
        assert config.enabled is False
        assert config.embedding_provider == EmbeddingProviderType.OPENAI
        assert config.embedding_model == "custom-model"
        assert config.chunk_size == 500
        assert config.default_max_results == 10

    def test_embedding_model_validation(self) -> None:
        """Test embedding model name validation."""
        with pytest.raises(ValidationError):
            RAGConfig(embedding_model="")
        with pytest.raises(ValidationError):
            RAGConfig(embedding_model="   ")

    def test_embedding_model_stripped(self) -> None:
        """Test embedding model name is stripped."""
        config = RAGConfig(embedding_model="  model-name  ")
        assert config.embedding_model == "model-name"

    def test_index_directory_validation(self) -> None:
        """Test index directory validation."""
        with pytest.raises(ValidationError):
            RAGConfig(index_directory="")

    def test_chunk_size_validation(self) -> None:
        """Test chunk size validation."""
        with pytest.raises(ValidationError):
            RAGConfig(chunk_size=50)  # Too small
        with pytest.raises(ValidationError):
            RAGConfig(chunk_size=20000)  # Too large

    def test_chunk_overlap_validation(self) -> None:
        """Test chunk overlap must be less than chunk size."""
        with pytest.raises(ValidationError):
            RAGConfig(chunk_size=500, chunk_overlap=500)
        with pytest.raises(ValidationError):
            RAGConfig(chunk_size=500, chunk_overlap=600)

    def test_max_file_size_validation(self) -> None:
        """Test max file size validation."""
        with pytest.raises(ValidationError):
            RAGConfig(max_file_size_kb=0)
        with pytest.raises(ValidationError):
            RAGConfig(max_file_size_kb=20000)

    def test_min_score_validation(self) -> None:
        """Test min score validation."""
        with pytest.raises(ValidationError):
            RAGConfig(default_min_score=-0.1)
        with pytest.raises(ValidationError):
            RAGConfig(default_min_score=1.5)

    def test_max_results_validation(self) -> None:
        """Test max results validation."""
        with pytest.raises(ValidationError):
            RAGConfig(default_max_results=0)
        with pytest.raises(ValidationError):
            RAGConfig(default_max_results=200)

    def test_context_token_budget_validation(self) -> None:
        """Test context token budget validation."""
        with pytest.raises(ValidationError):
            RAGConfig(context_token_budget=50)  # Too small
        with pytest.raises(ValidationError):
            RAGConfig(context_token_budget=100000)  # Too large

    def test_get_index_path(self) -> None:
        """Test getting absolute index path."""
        config = RAGConfig(index_directory=".forge/index")
        project_root = Path("/project")
        index_path = config.get_index_path(project_root)
        assert index_path == Path("/project/.forge/index")

    def test_get_state_file_path(self) -> None:
        """Test getting state file path."""
        config = RAGConfig(index_directory=".forge/index")
        project_root = Path("/project")
        state_path = config.get_state_file_path(project_root)
        assert state_path == Path("/project/.forge/index/state.json")

    def test_should_include_file(self) -> None:
        """Test file inclusion check."""
        config = RAGConfig(
            include_patterns=["**/*.py", "**/*.md"],
            exclude_patterns=["**/tests/**"],
        )
        assert config.should_include_file("src/main.py")
        assert config.should_include_file("docs/README.md")
        assert not config.should_include_file("tests/test_main.py")
        assert not config.should_include_file("src/main.js")

    def test_to_display_dict(self) -> None:
        """Test display-friendly dict conversion."""
        config = RAGConfig(
            enabled=True,
            embedding_provider=EmbeddingProviderType.LOCAL,
            embedding_model="all-MiniLM-L6-v2",
        )
        display = config.to_display_dict()
        assert display["enabled"] is True
        assert display["embedding_provider"] == "local"
        assert display["embedding_model"] == "all-MiniLM-L6-v2"
        assert "include_patterns" in display
        assert "chunk_size" in display

    def test_include_patterns_default(self) -> None:
        """Test that include patterns defaults correctly."""
        config = RAGConfig()
        # Should have a copy, not the original list
        assert config.include_patterns == DEFAULT_INCLUDE_PATTERNS
        config.include_patterns.append("**/*.custom")
        # Original should be unchanged
        assert "**/*.custom" not in DEFAULT_INCLUDE_PATTERNS

    def test_exclude_patterns_default(self) -> None:
        """Test that exclude patterns defaults correctly."""
        config = RAGConfig()
        assert config.exclude_patterns == DEFAULT_EXCLUDE_PATTERNS
        config.exclude_patterns.append("**/custom/**")
        assert "**/custom/**" not in DEFAULT_EXCLUDE_PATTERNS
