"""Configuration models for RAG system.

This module defines configuration options for the RAG system,
including embedding providers, vector stores, indexing settings,
and retrieval parameters.

Example:
    from code_forge.rag.config import RAGConfig

    # Create config with defaults
    config = RAGConfig()

    # Or customize
    config = RAGConfig(
        enabled=True,
        embedding_provider=EmbeddingProviderType.LOCAL,
        embedding_model="all-MiniLM-L6-v2",
        include_patterns=["**/*.py", "**/*.md"],
        chunk_size=1000,
    )
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmbeddingProviderType(str, Enum):
    """Embedding provider types.

    Attributes:
        LOCAL: Use local sentence-transformers models.
        OPENAI: Use OpenAI embeddings API.
    """

    LOCAL = "local"
    OPENAI = "openai"


class VectorStoreType(str, Enum):
    """Vector store backend types.

    Attributes:
        CHROMA: Use ChromaDB (default, pure Python).
        FAISS: Use FAISS (faster, requires additional deps).
    """

    CHROMA = "chroma"
    FAISS = "faiss"


# Default patterns for file inclusion
DEFAULT_INCLUDE_PATTERNS: list[str] = [
    "**/*.py",
    "**/*.js",
    "**/*.ts",
    "**/*.tsx",
    "**/*.jsx",
    "**/*.md",
    "**/*.rst",
    "**/*.txt",
    "**/*.yaml",
    "**/*.yml",
    "**/*.json",
    "**/*.toml",
]

# Default patterns for file exclusion
DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    "**/node_modules/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/.env/**",
    "**/dist/**",
    "**/build/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
    "**/htmlcov/**",
    "**/*.egg-info/**",
]


class RAGConfig(BaseModel):
    """RAG (Retrieval-Augmented Generation) configuration.

    This configuration controls all aspects of the RAG system including
    embedding generation, vector storage, file indexing, and retrieval.

    Attributes:
        enabled: Whether RAG is enabled for this project.
        auto_index: Automatically index project on startup.
        watch_files: Watch for file changes and auto-reindex.

        embedding_provider: Which embedding provider to use.
        embedding_model: Model name for local embeddings.
        openai_embedding_model: Model name for OpenAI embeddings.

        vector_store: Vector store backend to use.
        index_directory: Directory for storing index (relative to project).

        include_patterns: Glob patterns for files to include.
        exclude_patterns: Glob patterns for files to exclude.
        max_file_size_kb: Skip files larger than this (in KB).
        respect_gitignore: Whether to respect .gitignore patterns.

        chunk_size: Target tokens per chunk.
        chunk_overlap: Overlap tokens between chunks.

        default_max_results: Default max results for search.
        default_min_score: Default minimum similarity score.
        context_token_budget: Max tokens to add to context.
    """

    model_config = ConfigDict(validate_assignment=True)

    # Feature flags
    enabled: bool = True
    auto_index: bool = True
    watch_files: bool = True

    # Embedding configuration
    embedding_provider: EmbeddingProviderType = EmbeddingProviderType.LOCAL
    embedding_model: str = "all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    # Vector store configuration
    vector_store: VectorStoreType = VectorStoreType.CHROMA
    index_directory: str = ".forge/index"

    # Indexing configuration
    include_patterns: list[str] = Field(
        default_factory=lambda: DEFAULT_INCLUDE_PATTERNS.copy()
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: DEFAULT_EXCLUDE_PATTERNS.copy()
    )
    max_file_size_kb: int = Field(default=500, ge=1, le=10000)
    respect_gitignore: bool = True

    # Chunking configuration
    chunk_size: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap: int = Field(default=100, ge=0, le=500)

    # Retrieval configuration
    default_max_results: int = Field(default=5, ge=1, le=100)
    default_min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    context_token_budget: int = Field(default=4000, ge=100, le=50000)

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name is non-empty."""
        if not v or not v.strip():
            raise ValueError("Embedding model name must be non-empty")
        return v.strip()

    @field_validator("index_directory")
    @classmethod
    def validate_index_directory(cls, v: str) -> str:
        """Validate index directory path."""
        if not v or not v.strip():
            raise ValueError("Index directory must be non-empty")
        # Normalize path
        return str(Path(v.strip()))

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info: Any) -> int:
        """Validate chunk overlap is less than chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})"
            )
        return v

    def get_index_path(self, project_root: Path) -> Path:
        """Get absolute path to index directory.

        Args:
            project_root: Project root directory.

        Returns:
            Absolute path to index directory.
        """
        return project_root / self.index_directory

    def get_state_file_path(self, project_root: Path) -> Path:
        """Get path to index state file.

        Args:
            project_root: Project root directory.

        Returns:
            Path to state.json file.
        """
        return self.get_index_path(project_root) / "state.json"

    def should_include_file(self, relative_path: str) -> bool:
        """Check if a file should be included based on patterns.

        This is a simple check that doesn't handle gitignore.
        Use the full indexer for complete pattern matching.

        Args:
            relative_path: Relative path from project root.

        Returns:
            True if file matches include patterns and not exclude patterns.
        """
        import fnmatch
        from pathlib import PurePath

        path = PurePath(relative_path)
        path_str = str(path)
        parts = path.parts

        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            # Handle **/dir/** patterns by checking if dir is in path parts
            if pattern.startswith("**/") and pattern.endswith("/**"):
                dir_name = pattern[3:-3]  # Extract 'dir' from '**/dir/**'
                if dir_name in parts:
                    return False
            elif fnmatch.fnmatch(path_str, pattern):
                return False

        # Check include patterns - simpler extension-based matching
        for pattern in self.include_patterns:
            # For **/\*.ext patterns, just check extension
            if pattern.startswith("**/"):
                suffix_pattern = pattern[3:]  # Remove **/
                if fnmatch.fnmatch(path.name, suffix_pattern):
                    return True
            elif fnmatch.fnmatch(path_str, pattern):
                return True

        return False

    def to_display_dict(self) -> dict[str, Any]:
        """Convert config to display-friendly dictionary.

        Returns:
            Dictionary suitable for display (excludes defaults).
        """
        return {
            "enabled": self.enabled,
            "auto_index": self.auto_index,
            "watch_files": self.watch_files,
            "embedding_provider": self.embedding_provider.value,
            "embedding_model": (
                self.embedding_model
                if self.embedding_provider == EmbeddingProviderType.LOCAL
                else self.openai_embedding_model
            ),
            "vector_store": self.vector_store.value,
            "index_directory": self.index_directory,
            "include_patterns": len(self.include_patterns),
            "exclude_patterns": len(self.exclude_patterns),
            "chunk_size": self.chunk_size,
            "default_max_results": self.default_max_results,
            "context_token_budget": self.context_token_budget,
        }
