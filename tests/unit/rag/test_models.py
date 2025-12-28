"""Tests for RAG data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from code_forge.rag.models import (
    Chunk,
    ChunkType,
    Document,
    DocumentType,
    IndexState,
    IndexStats,
    SearchFilter,
    SearchResult,
)


class TestDocumentType:
    """Tests for DocumentType enum."""

    def test_all_types_exist(self) -> None:
        """Test all document types are defined."""
        assert DocumentType.CODE.value == "code"
        assert DocumentType.DOCUMENTATION.value == "documentation"
        assert DocumentType.CONFIG.value == "config"
        assert DocumentType.OTHER.value == "other"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert DocumentType("code") == DocumentType.CODE
        assert DocumentType("documentation") == DocumentType.DOCUMENTATION


class TestChunkType:
    """Tests for ChunkType enum."""

    def test_all_types_exist(self) -> None:
        """Test all chunk types are defined."""
        assert ChunkType.FUNCTION.value == "function"
        assert ChunkType.CLASS.value == "class"
        assert ChunkType.MODULE.value == "module"
        assert ChunkType.SECTION.value == "section"
        assert ChunkType.PARAGRAPH.value == "paragraph"
        assert ChunkType.GENERIC.value == "generic"


class TestDocument:
    """Tests for Document model."""

    def test_document_creation(self) -> None:
        """Test creating a document with required fields."""
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
        )
        assert doc.path == "src/main.py"
        assert doc.absolute_path == "/project/src/main.py"
        assert doc.document_type == DocumentType.CODE
        assert doc.content_hash == "abc123"
        assert doc.file_size == 1024
        assert doc.language is None
        assert doc.tags == []
        assert doc.metadata == {}

    def test_document_with_optional_fields(self) -> None:
        """Test creating a document with optional fields."""
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
            language="python",
            tags=["core", "important"],
            metadata={"author": "test"},
        )
        assert doc.language == "python"
        assert doc.tags == ["core", "important"]
        assert doc.metadata == {"author": "test"}

    def test_document_auto_generates_id(self) -> None:
        """Test that document ID is auto-generated."""
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
        )
        assert doc.id is not None
        assert len(doc.id) > 0

    def test_document_auto_generates_timestamp(self) -> None:
        """Test that indexed_at is auto-generated."""
        before = datetime.now()
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
        )
        after = datetime.now()
        assert before <= doc.indexed_at <= after

    def test_document_file_size_validation(self) -> None:
        """Test that negative file size is rejected."""
        with pytest.raises(ValidationError):
            Document(
                path="src/main.py",
                absolute_path="/project/src/main.py",
                document_type=DocumentType.CODE,
                content_hash="abc123",
                file_size=-1,
            )

    def test_document_to_dict(self) -> None:
        """Test document serialization to dict."""
        doc = Document(
            id="test-id",
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
            language="python",
        )
        data = doc.to_dict()
        assert data["id"] == "test-id"
        assert data["path"] == "src/main.py"
        assert data["document_type"] == "code"
        assert data["language"] == "python"

    def test_document_from_dict(self) -> None:
        """Test document deserialization from dict."""
        data = {
            "id": "test-id",
            "path": "src/main.py",
            "absolute_path": "/project/src/main.py",
            "document_type": "code",
            "content_hash": "abc123",
            "indexed_at": "2025-01-01T12:00:00",
            "file_size": 1024,
            "language": "python",
            "tags": [],
            "metadata": {},
        }
        doc = Document.from_dict(data)
        assert doc.id == "test-id"
        assert doc.document_type == DocumentType.CODE
        assert doc.indexed_at == datetime.fromisoformat("2025-01-01T12:00:00")


class TestChunk:
    """Tests for Chunk model."""

    def test_chunk_creation(self) -> None:
        """Test creating a chunk with required fields."""
        chunk = Chunk(
            document_id="doc-123",
            chunk_type=ChunkType.FUNCTION,
            content="def hello(): pass",
            start_line=10,
            end_line=15,
            token_count=50,
        )
        assert chunk.document_id == "doc-123"
        assert chunk.chunk_type == ChunkType.FUNCTION
        assert chunk.content == "def hello(): pass"
        assert chunk.start_line == 10
        assert chunk.end_line == 15
        assert chunk.token_count == 50
        assert chunk.embedding is None
        assert chunk.name is None

    def test_chunk_with_embedding(self) -> None:
        """Test creating a chunk with embedding."""
        embedding = [0.1, 0.2, 0.3]
        chunk = Chunk(
            document_id="doc-123",
            chunk_type=ChunkType.FUNCTION,
            content="def hello(): pass",
            start_line=10,
            end_line=15,
            token_count=50,
            embedding=embedding,
        )
        assert chunk.embedding == embedding

    def test_chunk_with_name(self) -> None:
        """Test creating a chunk with name."""
        chunk = Chunk(
            document_id="doc-123",
            chunk_type=ChunkType.FUNCTION,
            content="def hello(): pass",
            start_line=10,
            end_line=15,
            token_count=50,
            name="hello",
        )
        assert chunk.name == "hello"

    def test_chunk_line_validation(self) -> None:
        """Test that line numbers must be positive."""
        with pytest.raises(ValidationError):
            Chunk(
                document_id="doc-123",
                chunk_type=ChunkType.FUNCTION,
                content="content",
                start_line=0,
                end_line=10,
                token_count=50,
            )

    def test_chunk_to_dict(self) -> None:
        """Test chunk serialization to dict."""
        chunk = Chunk(
            id="chunk-id",
            document_id="doc-123",
            chunk_type=ChunkType.FUNCTION,
            content="def hello(): pass",
            start_line=10,
            end_line=15,
            token_count=50,
            name="hello",
        )
        data = chunk.to_dict()
        assert data["id"] == "chunk-id"
        assert data["chunk_type"] == "function"
        assert data["name"] == "hello"

    def test_chunk_from_dict(self) -> None:
        """Test chunk deserialization from dict."""
        data = {
            "id": "chunk-id",
            "document_id": "doc-123",
            "chunk_type": "function",
            "content": "def hello(): pass",
            "start_line": 10,
            "end_line": 15,
            "token_count": 50,
            "embedding": None,
            "metadata": {},
            "name": "hello",
        }
        chunk = Chunk.from_dict(data)
        assert chunk.id == "chunk-id"
        assert chunk.chunk_type == ChunkType.FUNCTION


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_search_result_creation(self) -> None:
        """Test creating a search result."""
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
        )
        chunk = Chunk(
            document_id=doc.id,
            chunk_type=ChunkType.FUNCTION,
            content="def hello(): pass",
            start_line=10,
            end_line=15,
            token_count=50,
        )
        result = SearchResult(
            chunk=chunk,
            document=doc,
            score=0.85,
            rank=1,
            snippet="def hello(): pass",
        )
        assert result.score == 0.85
        assert result.rank == 1
        assert result.snippet == "def hello(): pass"

    def test_search_result_score_validation(self) -> None:
        """Test score validation."""
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
        )
        chunk = Chunk(
            document_id=doc.id,
            chunk_type=ChunkType.FUNCTION,
            content="content",
            start_line=1,
            end_line=1,
            token_count=10,
        )
        with pytest.raises(ValidationError):
            SearchResult(
                chunk=chunk,
                document=doc,
                score=1.5,  # Invalid: > 1.0
                rank=1,
                snippet="content",
            )

    def test_search_result_create_factory(self) -> None:
        """Test SearchResult.create factory method."""
        doc = Document(
            path="src/main.py",
            absolute_path="/project/src/main.py",
            document_type=DocumentType.CODE,
            content_hash="abc123",
            file_size=1024,
        )
        chunk = Chunk(
            document_id=doc.id,
            chunk_type=ChunkType.FUNCTION,
            content="a" * 600,  # Long content
            start_line=10,
            end_line=15,
            token_count=50,
        )
        result = SearchResult.create(
            chunk=chunk,
            document=doc,
            score=0.85,
            rank=1,
            max_snippet_length=100,
        )
        assert len(result.snippet) <= 103  # 100 + "..."
        assert result.snippet.endswith("...")


class TestSearchFilter:
    """Tests for SearchFilter model."""

    def test_default_values(self) -> None:
        """Test default filter values."""
        filter = SearchFilter()
        assert filter.file_patterns == []
        assert filter.document_types == []
        assert filter.languages == []
        assert filter.tags == []
        assert filter.min_score == 0.5
        assert filter.max_results == 10
        assert filter.max_tokens is None

    def test_custom_values(self) -> None:
        """Test custom filter values."""
        filter = SearchFilter(
            file_patterns=["**/*.py"],
            document_types=[DocumentType.CODE],
            languages=["python"],
            min_score=0.7,
            max_results=5,
            max_tokens=2000,
        )
        assert filter.file_patterns == ["**/*.py"]
        assert filter.document_types == [DocumentType.CODE]
        assert filter.min_score == 0.7
        assert filter.max_tokens == 2000

    def test_score_validation(self) -> None:
        """Test min_score validation."""
        with pytest.raises(ValidationError):
            SearchFilter(min_score=1.5)
        with pytest.raises(ValidationError):
            SearchFilter(min_score=-0.1)

    def test_max_results_validation(self) -> None:
        """Test max_results validation."""
        with pytest.raises(ValidationError):
            SearchFilter(max_results=0)
        with pytest.raises(ValidationError):
            SearchFilter(max_results=101)


class TestIndexStats:
    """Tests for IndexStats model."""

    def test_index_stats_creation(self) -> None:
        """Test creating index stats."""
        stats = IndexStats(
            total_documents=100,
            total_chunks=500,
            total_tokens=50000,
            embedding_model="all-MiniLM-L6-v2",
            vector_store="chroma",
            storage_size_bytes=1024000,
        )
        assert stats.total_documents == 100
        assert stats.total_chunks == 500
        assert stats.total_tokens == 50000

    def test_index_stats_display_string(self) -> None:
        """Test stats display formatting."""
        stats = IndexStats(
            total_documents=100,
            total_chunks=500,
            total_tokens=50000,
            embedding_model="all-MiniLM-L6-v2",
            vector_store="chroma",
            storage_size_bytes=1024000,
            documents_by_type={"code": 80, "documentation": 20},
        )
        display = stats.to_display_string()
        assert "Documents: 100" in display
        assert "Chunks: 500" in display
        assert "all-MiniLM-L6-v2" in display
        assert "code: 80" in display


class TestIndexState:
    """Tests for IndexState model."""

    def test_index_state_creation(self) -> None:
        """Test creating index state."""
        state = IndexState()
        assert state.files == {}
        assert state.last_full_index is None
        assert state.embedding_model is None

    def test_is_file_changed(self) -> None:
        """Test file change detection."""
        state = IndexState(files={"src/main.py": "hash123"})
        assert not state.is_file_changed("src/main.py", "hash123")
        assert state.is_file_changed("src/main.py", "hash456")
        assert state.is_file_changed("src/new.py", "hash789")

    def test_update_file(self) -> None:
        """Test updating file hash."""
        state = IndexState()
        state.update_file("src/main.py", "hash123")
        assert state.files["src/main.py"] == "hash123"

    def test_remove_file(self) -> None:
        """Test removing file from tracking."""
        state = IndexState(files={"src/main.py": "hash123"})
        state.remove_file("src/main.py")
        assert "src/main.py" not in state.files
        # Removing non-existent file should not raise
        state.remove_file("nonexistent.py")

    def test_get_deleted_files(self) -> None:
        """Test detecting deleted files."""
        state = IndexState(
            files={
                "src/main.py": "hash1",
                "src/old.py": "hash2",
                "src/also_old.py": "hash3",
            }
        )
        current = {"src/main.py", "src/new.py"}
        deleted = state.get_deleted_files(current)
        assert deleted == {"src/old.py", "src/also_old.py"}

    def test_index_state_serialization(self) -> None:
        """Test state serialization and deserialization."""
        state = IndexState(
            files={"src/main.py": "hash123"},
            last_full_index=datetime(2025, 1, 1, 12, 0, 0),
            embedding_model="all-MiniLM-L6-v2",
        )
        data = state.to_dict()
        restored = IndexState.from_dict(data)
        assert restored.files == state.files
        assert restored.last_full_index == state.last_full_index
        assert restored.embedding_model == state.embedding_model
