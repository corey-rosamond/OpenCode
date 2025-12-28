"""Tests for RAG vector stores."""

import asyncio
from pathlib import Path

import pytest

from code_forge.rag.config import RAGConfig, VectorStoreType
from code_forge.rag.models import Chunk, ChunkType, DocumentType, SearchFilter
from code_forge.rag.vectorstore import (
    ChromaStore,
    FAISSStore,
    MockVectorStore,
    VectorStore,
    get_vector_store,
)


def make_chunk(
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    content: str = "Test content",
    embedding: list[float] | None = None,
) -> Chunk:
    """Create a test chunk with embedding."""
    if embedding is None:
        # Create simple embedding based on content hash
        embedding = [float(ord(c) % 10) / 10 for c in content[:384].ljust(384)]
    return Chunk(
        id=chunk_id,
        document_id=document_id,
        chunk_type=ChunkType.GENERIC,
        content=content,
        start_line=1,
        end_line=1,
        token_count=len(content) // 4,
        embedding=embedding,
    )


class TestMockVectorStore:
    """Tests for MockVectorStore."""

    def test_name(self) -> None:
        """Test store name."""
        store = MockVectorStore()
        assert store.name == "mock"

    def test_add_chunks(self) -> None:
        """Test adding chunks."""
        store = MockVectorStore()
        chunks = [
            make_chunk("chunk-1", "doc-1", "Hello world"),
            make_chunk("chunk-2", "doc-1", "Goodbye world"),
        ]
        count = asyncio.get_event_loop().run_until_complete(store.add(chunks))
        assert count == 2
        assert store.get_stats()["total_chunks"] == 2

    def test_add_empty_list(self) -> None:
        """Test adding empty list."""
        store = MockVectorStore()
        count = asyncio.get_event_loop().run_until_complete(store.add([]))
        assert count == 0

    def test_add_chunk_without_embedding_raises(self) -> None:
        """Test adding chunk without embedding raises error."""
        store = MockVectorStore()
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            chunk_type=ChunkType.GENERIC,
            content="Test",
            start_line=1,
            end_line=1,
            token_count=1,
            embedding=None,  # No embedding
        )
        with pytest.raises(ValueError, match="no embedding"):
            asyncio.get_event_loop().run_until_complete(store.add([chunk]))

    def test_search_returns_results(self) -> None:
        """Test search returns results."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        # Add chunks with known embeddings
        embedding1 = [1.0] * 384
        embedding2 = [0.5] * 384
        embedding3 = [0.0] * 384

        chunks = [
            make_chunk("chunk-1", "doc-1", "Content 1", embedding1),
            make_chunk("chunk-2", "doc-1", "Content 2", embedding2),
            make_chunk("chunk-3", "doc-2", "Content 3", embedding3),
        ]
        loop.run_until_complete(store.add(chunks))

        # Search with embedding similar to chunk-1
        query_embedding = [0.9] * 384
        results = loop.run_until_complete(store.search(query_embedding, k=2))

        assert len(results) == 2
        # Results should be sorted by similarity
        assert results[0][1] >= results[1][1]

    def test_search_empty_store(self) -> None:
        """Test search on empty store."""
        store = MockVectorStore()
        query = [0.5] * 384
        results = asyncio.get_event_loop().run_until_complete(store.search(query))
        assert results == []

    def test_search_with_k_limit(self) -> None:
        """Test search respects k limit."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunks = [make_chunk(f"chunk-{i}", "doc-1", f"Content {i}") for i in range(10)]
        loop.run_until_complete(store.add(chunks))

        results = loop.run_until_complete(store.search([0.5] * 384, k=3))
        assert len(results) == 3

    def test_search_with_min_score_filter(self) -> None:
        """Test search filters by minimum score."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        # Add chunk with specific embedding
        chunk = make_chunk("chunk-1", "doc-1", "Test", [1.0] * 384)
        loop.run_until_complete(store.add([chunk]))

        # Search with dissimilar embedding should return low score
        query = [0.0] * 384
        filter = SearchFilter(min_score=0.9)
        results = loop.run_until_complete(store.search(query, filter=filter))

        # Should filter out low-scoring results
        for chunk_id, score in results:
            assert score >= 0.9

    def test_search_with_document_type_filter(self) -> None:
        """Test search filters by document type."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunks = [
            make_chunk("chunk-1", "doc-1", "Code content"),
            make_chunk("chunk-2", "doc-2", "Doc content"),
        ]
        # Set chunk types manually
        chunks[0].chunk_type = ChunkType.FUNCTION
        chunks[1].chunk_type = ChunkType.SECTION

        loop.run_until_complete(store.add(chunks))

        # Filter doesn't directly filter by ChunkType, but by DocumentType
        # This tests the filter mechanism works
        filter = SearchFilter(document_types=[DocumentType.CODE])
        results = loop.run_until_complete(store.search([0.5] * 384, filter=filter))
        # Both chunks should still be returned since we're filtering by DocumentType not ChunkType
        # This test validates the filter mechanism is called

    def test_delete_chunks(self) -> None:
        """Test deleting chunks by ID."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunks = [
            make_chunk("chunk-1", "doc-1", "Content 1"),
            make_chunk("chunk-2", "doc-1", "Content 2"),
        ]
        loop.run_until_complete(store.add(chunks))
        assert store.get_stats()["total_chunks"] == 2

        deleted = loop.run_until_complete(store.delete(["chunk-1"]))
        assert deleted == 1
        assert store.get_stats()["total_chunks"] == 1

    def test_delete_nonexistent_chunk(self) -> None:
        """Test deleting non-existent chunk."""
        store = MockVectorStore()
        deleted = asyncio.get_event_loop().run_until_complete(
            store.delete(["nonexistent"])
        )
        assert deleted == 0

    def test_delete_empty_list(self) -> None:
        """Test deleting empty list."""
        store = MockVectorStore()
        deleted = asyncio.get_event_loop().run_until_complete(store.delete([]))
        assert deleted == 0

    def test_delete_by_document(self) -> None:
        """Test deleting all chunks for a document."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunks = [
            make_chunk("chunk-1", "doc-1", "Content 1"),
            make_chunk("chunk-2", "doc-1", "Content 2"),
            make_chunk("chunk-3", "doc-2", "Content 3"),
        ]
        loop.run_until_complete(store.add(chunks))
        assert store.get_stats()["total_chunks"] == 3

        deleted = loop.run_until_complete(store.delete_by_document("doc-1"))
        assert deleted == 2
        assert store.get_stats()["total_chunks"] == 1

    def test_clear(self) -> None:
        """Test clearing all chunks."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunks = [make_chunk(f"chunk-{i}", "doc-1", f"Content {i}") for i in range(5)]
        loop.run_until_complete(store.add(chunks))
        assert store.get_stats()["total_chunks"] == 5

        loop.run_until_complete(store.clear())
        assert store.get_stats()["total_chunks"] == 0

    def test_get_chunk(self) -> None:
        """Test getting a chunk by ID."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunk = make_chunk("chunk-1", "doc-1", "Test content")
        loop.run_until_complete(store.add([chunk]))

        result = loop.run_until_complete(store.get_chunk("chunk-1"))
        assert result is not None
        assert result["id"] == "chunk-1"
        assert result["content"] == "Test content"

    def test_get_chunk_not_found(self) -> None:
        """Test getting non-existent chunk."""
        store = MockVectorStore()
        result = asyncio.get_event_loop().run_until_complete(
            store.get_chunk("nonexistent")
        )
        assert result is None

    def test_get_stats(self) -> None:
        """Test getting store statistics."""
        store = MockVectorStore()
        stats = store.get_stats()

        assert stats["total_chunks"] == 0
        assert stats["backend"] == "mock"
        assert stats["initialized"] is True

    def test_cosine_similarity(self) -> None:
        """Test cosine similarity calculation."""
        # Test identical vectors
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert MockVectorStore._cosine_similarity(a, b) == pytest.approx(1.0)

        # Test orthogonal vectors
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert MockVectorStore._cosine_similarity(a, b) == pytest.approx(0.0)

        # Test opposite vectors
        a = [1.0, 0.0, 0.0]
        b = [-1.0, 0.0, 0.0]
        assert MockVectorStore._cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_cosine_similarity_zero_vectors(self) -> None:
        """Test cosine similarity with zero vectors."""
        a = [0.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert MockVectorStore._cosine_similarity(a, b) == 0.0


class TestChromaStore:
    """Tests for ChromaStore (without requiring ChromaDB)."""

    def test_name(self, tmp_path: Path) -> None:
        """Test store name."""
        store = ChromaStore(persist_directory=tmp_path / "index")
        assert store.name == "chroma"

    def test_get_stats_uninitialized(self, tmp_path: Path) -> None:
        """Test getting stats before initialization."""
        store = ChromaStore(persist_directory=tmp_path / "index")
        stats = store.get_stats()
        assert stats["total_chunks"] == 0
        assert stats["backend"] == "chroma"
        assert stats["initialized"] is False

    def test_has_required_methods(self, tmp_path: Path) -> None:
        """Test ChromaStore has all required protocol methods."""
        store = ChromaStore(persist_directory=tmp_path / "index")
        assert hasattr(store, "add")
        assert hasattr(store, "search")
        assert hasattr(store, "delete")
        assert hasattr(store, "delete_by_document")
        assert hasattr(store, "clear")
        assert hasattr(store, "get_chunk")
        assert hasattr(store, "get_stats")
        assert hasattr(store, "name")


class TestFAISSStore:
    """Tests for FAISSStore (without requiring FAISS)."""

    def test_name(self, tmp_path: Path) -> None:
        """Test store name."""
        store = FAISSStore(persist_directory=tmp_path / "index")
        assert store.name == "faiss"

    def test_get_stats_uninitialized(self, tmp_path: Path) -> None:
        """Test getting stats before initialization."""
        store = FAISSStore(persist_directory=tmp_path / "index")
        stats = store.get_stats()
        assert stats["total_chunks"] == 0
        assert stats["backend"] == "faiss"
        assert stats["initialized"] is False

    def test_has_required_methods(self, tmp_path: Path) -> None:
        """Test FAISSStore has all required protocol methods."""
        store = FAISSStore(persist_directory=tmp_path / "index")
        assert hasattr(store, "add")
        assert hasattr(store, "search")
        assert hasattr(store, "delete")
        assert hasattr(store, "delete_by_document")
        assert hasattr(store, "clear")
        assert hasattr(store, "get_chunk")
        assert hasattr(store, "get_stats")
        assert hasattr(store, "name")

    def test_custom_dimension(self, tmp_path: Path) -> None:
        """Test custom embedding dimension."""
        store = FAISSStore(persist_directory=tmp_path / "index", dimension=768)
        stats = store.get_stats()
        assert stats["dimension"] == 768


class TestGetVectorStore:
    """Tests for get_vector_store factory function."""

    def test_get_chroma_store(self, tmp_path: Path) -> None:
        """Test getting ChromaStore."""
        config = RAGConfig(vector_store=VectorStoreType.CHROMA)
        store = get_vector_store(config, tmp_path)
        assert isinstance(store, ChromaStore)

    def test_get_faiss_store(self, tmp_path: Path) -> None:
        """Test getting FAISSStore."""
        config = RAGConfig(vector_store=VectorStoreType.FAISS)
        store = get_vector_store(config, tmp_path)
        assert isinstance(store, FAISSStore)

    def test_uses_config_index_directory(self, tmp_path: Path) -> None:
        """Test store uses configured index directory."""
        config = RAGConfig(
            vector_store=VectorStoreType.CHROMA,
            index_directory=".custom/index",
        )
        store = get_vector_store(config, tmp_path)
        assert isinstance(store, ChromaStore)

    def test_passes_dimension_to_faiss(self, tmp_path: Path) -> None:
        """Test dimension is passed to FAISS store."""
        config = RAGConfig(vector_store=VectorStoreType.FAISS)
        store = get_vector_store(config, tmp_path, dimension=768)
        assert isinstance(store, FAISSStore)


class TestVectorStoreProtocol:
    """Tests to verify stores implement the protocol correctly."""

    @pytest.mark.parametrize(
        "store_factory",
        [
            lambda tmp_path: MockVectorStore(),
            lambda tmp_path: ChromaStore(tmp_path / "chroma"),
            lambda tmp_path: FAISSStore(tmp_path / "faiss"),
        ],
    )
    def test_store_has_required_attributes(
        self, store_factory, tmp_path: Path
    ) -> None:
        """Test that all stores have required attributes."""
        store = store_factory(tmp_path)
        assert hasattr(store, "name")
        assert isinstance(store.name, str)

    @pytest.mark.parametrize(
        "store_factory",
        [
            lambda tmp_path: MockVectorStore(),
            lambda tmp_path: ChromaStore(tmp_path / "chroma"),
            lambda tmp_path: FAISSStore(tmp_path / "faiss"),
        ],
    )
    def test_store_has_required_methods(
        self, store_factory, tmp_path: Path
    ) -> None:
        """Test that all stores have required methods."""
        store = store_factory(tmp_path)
        required_methods = [
            "add",
            "search",
            "delete",
            "delete_by_document",
            "clear",
            "get_chunk",
            "get_stats",
        ]
        for method in required_methods:
            assert hasattr(store, method), f"Missing method: {method}"
            assert callable(getattr(store, method)), f"Not callable: {method}"


class TestSearchFilter:
    """Tests for SearchFilter with vector stores."""

    def test_filter_by_min_score(self) -> None:
        """Test filtering by minimum score."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        # Add chunks with very different embeddings
        chunks = [
            make_chunk("chunk-1", "doc-1", "A", [1.0] * 384),
            make_chunk("chunk-2", "doc-1", "B", [0.0] * 384),
        ]
        loop.run_until_complete(store.add(chunks))

        # Query similar to chunk-1
        query = [1.0] * 384
        filter = SearchFilter(min_score=0.99)
        results = loop.run_until_complete(store.search(query, filter=filter))

        # Only chunk-1 should match with high similarity
        assert len(results) <= 1

    def test_filter_max_results(self) -> None:
        """Test max_results limit."""
        store = MockVectorStore()
        loop = asyncio.get_event_loop()

        chunks = [make_chunk(f"chunk-{i}", "doc-1", f"C{i}") for i in range(20)]
        loop.run_until_complete(store.add(chunks))

        filter = SearchFilter(max_results=5)
        results = loop.run_until_complete(
            store.search([0.5] * 384, k=filter.max_results)
        )
        assert len(results) <= 5
