"""Data models for RAG (Retrieval-Augmented Generation) system.

This module defines Pydantic models for documents, chunks, search results,
and related data structures used throughout the RAG system.

Example:
    from code_forge.rag.models import Document, Chunk, SearchResult

    # Create a document
    doc = Document(
        id="doc-123",
        path="src/main.py",
        absolute_path="/project/src/main.py",
        document_type=DocumentType.CODE,
        content_hash="abc123...",
        indexed_at=datetime.now(),
        file_size=1024,
        language="python",
    )

    # Create a chunk
    chunk = Chunk(
        id="chunk-456",
        document_id=doc.id,
        chunk_type=ChunkType.FUNCTION,
        content="def hello(): ...",
        start_line=10,
        end_line=15,
        token_count=50,
        name="hello",
    )
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    """Type of indexed document.

    Attributes:
        CODE: Source code files (.py, .js, .ts, etc.)
        DOCUMENTATION: Documentation files (.md, .rst, .txt)
        CONFIG: Configuration files (.json, .yaml, .toml)
        OTHER: Other file types
    """

    CODE = "code"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    OTHER = "other"


class ChunkType(str, Enum):
    """Type of chunk within a document.

    Attributes:
        FUNCTION: A function or method definition
        CLASS: A class definition
        MODULE: Module-level code (imports, constants)
        SECTION: A documentation section (header + content)
        PARAGRAPH: A paragraph of text
        GENERIC: Generic chunk without specific structure
    """

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    GENERIC = "generic"


class Document(BaseModel):
    """Represents an indexed document.

    A document corresponds to a single file that has been indexed.
    It tracks metadata about the file and when it was indexed.

    Attributes:
        id: Unique identifier (UUID).
        path: Relative path from project root.
        absolute_path: Absolute file path.
        document_type: Type of document (code, docs, config, etc.).
        content_hash: SHA256 hash of file content for change detection.
        indexed_at: Timestamp when the document was indexed.
        file_size: File size in bytes.
        language: Detected programming language (for code files).
        tags: User-defined tags for filtering.
        metadata: Additional metadata.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path: str
    absolute_path: str
    document_type: DocumentType
    content_hash: str
    indexed_at: datetime = Field(default_factory=datetime.now)
    file_size: int = Field(ge=0)
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert document to dictionary for serialization.

        Returns:
            Dictionary representation of the document.
        """
        return {
            "id": self.id,
            "path": self.path,
            "absolute_path": self.absolute_path,
            "document_type": self.document_type.value,
            "content_hash": self.content_hash,
            "indexed_at": self.indexed_at.isoformat(),
            "file_size": self.file_size,
            "language": self.language,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        """Create document from dictionary.

        Args:
            data: Dictionary with document data.

        Returns:
            Document instance.
        """
        data = data.copy()
        if isinstance(data.get("document_type"), str):
            data["document_type"] = DocumentType(data["document_type"])
        if isinstance(data.get("indexed_at"), str):
            data["indexed_at"] = datetime.fromisoformat(data["indexed_at"])
        return cls(**data)


class Chunk(BaseModel):
    """A chunk of a document with optional embedding.

    Chunks are the basic unit for indexing and retrieval. Each document
    is split into one or more chunks based on its structure (functions,
    classes, sections, etc.).

    Attributes:
        id: Unique identifier (UUID).
        document_id: Reference to parent Document.
        chunk_type: Type of chunk (function, class, section, etc.).
        content: The text content of the chunk.
        start_line: Starting line number in the source file (1-indexed).
        end_line: Ending line number in the source file (1-indexed).
        token_count: Estimated token count for the chunk.
        embedding: Vector embedding (set after embedding generation).
        metadata: Additional metadata.
        name: Name identifier (function/class name or section heading).
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    chunk_type: ChunkType
    content: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    token_count: int = Field(ge=0)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert chunk to dictionary for serialization.

        Returns:
            Dictionary representation of the chunk.
        """
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_type": self.chunk_type.value,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "token_count": self.token_count,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        """Create chunk from dictionary.

        Args:
            data: Dictionary with chunk data.

        Returns:
            Chunk instance.
        """
        data = data.copy()
        if isinstance(data.get("chunk_type"), str):
            data["chunk_type"] = ChunkType(data["chunk_type"])
        return cls(**data)


class SearchResult(BaseModel):
    """Result from semantic search.

    Represents a single search result with the matching chunk,
    its parent document, and relevance information.

    Attributes:
        chunk: The matching chunk.
        document: Parent document of the chunk.
        score: Similarity score (0.0 to 1.0, higher is better).
        rank: Position in search results (1-indexed).
        snippet: Formatted snippet for display.
    """

    model_config = ConfigDict(validate_assignment=True)

    chunk: Chunk
    document: Document
    score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    snippet: str

    @classmethod
    def create(
        cls,
        chunk: Chunk,
        document: Document,
        score: float,
        rank: int,
        max_snippet_length: int = 500,
    ) -> SearchResult:
        """Create a search result with auto-generated snippet.

        Args:
            chunk: The matching chunk.
            document: Parent document.
            score: Similarity score.
            rank: Position in results.
            max_snippet_length: Maximum snippet length.

        Returns:
            SearchResult instance.
        """
        content = chunk.content
        if len(content) > max_snippet_length:
            snippet = content[:max_snippet_length] + "..."
        else:
            snippet = content
        return cls(
            chunk=chunk,
            document=document,
            score=score,
            rank=rank,
            snippet=snippet,
        )


class SearchFilter(BaseModel):
    """Filters for search queries.

    Allows filtering search results by various criteria including
    file patterns, document types, languages, and score thresholds.

    Attributes:
        file_patterns: Glob patterns to match file paths.
        document_types: Filter by document types.
        languages: Filter by programming languages.
        tags: Filter by document tags.
        min_score: Minimum similarity score (0.0-1.0).
        max_results: Maximum number of results to return.
        max_tokens: Maximum total tokens in results (for context budget).
    """

    model_config = ConfigDict(validate_assignment=True)

    file_patterns: list[str] = Field(default_factory=list)
    document_types: list[DocumentType] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=100)
    max_tokens: int | None = Field(default=None, ge=1)


class IndexStats(BaseModel):
    """Statistics about the RAG index.

    Provides summary information about the indexed content.

    Attributes:
        total_documents: Number of indexed documents.
        total_chunks: Number of chunks across all documents.
        total_tokens: Estimated total tokens indexed.
        embedding_model: Name of the embedding model used.
        vector_store: Name of the vector store backend.
        last_indexed: Timestamp of last indexing operation.
        storage_size_bytes: Size of index storage on disk.
        documents_by_type: Count of documents by type.
    """

    model_config = ConfigDict(validate_assignment=True)

    total_documents: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    embedding_model: str
    vector_store: str
    last_indexed: datetime | None = None
    storage_size_bytes: int = Field(ge=0)
    documents_by_type: dict[str, int] = Field(default_factory=dict)

    def to_display_string(self) -> str:
        """Format stats for display.

        Returns:
            Human-readable statistics string.
        """
        lines = [
            "RAG Index Statistics:",
            f"  Documents: {self.total_documents}",
            f"  Chunks: {self.total_chunks}",
            f"  Total Tokens: {self.total_tokens:,}",
            f"  Embedding Model: {self.embedding_model}",
            f"  Vector Store: {self.vector_store}",
            f"  Storage Size: {self._format_bytes(self.storage_size_bytes)}",
        ]
        if self.last_indexed:
            lines.append(f"  Last Indexed: {self.last_indexed.isoformat()}")
        if self.documents_by_type:
            lines.append("  By Type:")
            for doc_type, count in sorted(self.documents_by_type.items()):
                lines.append(f"    {doc_type}: {count}")
        return "\n".join(lines)

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes as human-readable string."""
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size //= 1024
        return f"{size:.1f} TB"


class IndexState(BaseModel):
    """Tracks the state of indexed files for incremental updates.

    Stores file hashes to detect changes since last indexing.

    Attributes:
        files: Mapping of relative file paths to content hashes.
        last_full_index: Timestamp of last full index operation.
        embedding_model: Embedding model used (for compatibility check).
    """

    model_config = ConfigDict(validate_assignment=True)

    files: dict[str, str] = Field(default_factory=dict)
    last_full_index: datetime | None = None
    embedding_model: str | None = None

    def is_file_changed(self, path: str, content_hash: str) -> bool:
        """Check if a file has changed since last indexing.

        Args:
            path: Relative file path.
            content_hash: Current content hash.

        Returns:
            True if the file is new or has changed.
        """
        return self.files.get(path) != content_hash

    def update_file(self, path: str, content_hash: str) -> None:
        """Update the hash for a file.

        Args:
            path: Relative file path.
            content_hash: New content hash.
        """
        self.files[path] = content_hash

    def remove_file(self, path: str) -> None:
        """Remove a file from tracking.

        Args:
            path: Relative file path.
        """
        self.files.pop(path, None)

    def get_deleted_files(self, current_files: set[str]) -> set[str]:
        """Get files that were indexed but no longer exist.

        Args:
            current_files: Set of current file paths.

        Returns:
            Set of deleted file paths.
        """
        return set(self.files.keys()) - current_files

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "files": self.files,
            "last_full_index": (
                self.last_full_index.isoformat() if self.last_full_index else None
            ),
            "embedding_model": self.embedding_model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IndexState:
        """Create from dictionary."""
        data = data.copy()
        if data.get("last_full_index"):
            data["last_full_index"] = datetime.fromisoformat(data["last_full_index"])
        return cls(**data)
