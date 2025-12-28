"""Tests for RAG retriever."""

import asyncio
from pathlib import Path

import pytest

from code_forge.rag.config import RAGConfig
from code_forge.rag.embeddings import MockEmbeddingProvider
from code_forge.rag.models import (
    Chunk,
    ChunkType,
    Document,
    DocumentType,
    SearchFilter,
    SearchResult,
)
from code_forge.rag.retriever import (
    RAGRetriever,
    RankerConfig,
    ResultRanker,
    RetrievalContext,
)
from code_forge.rag.vectorstore import MockVectorStore


def make_chunk(
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    content: str = "Test content",
    name: str | None = None,
    token_count: int = 50,
    chunk_type: ChunkType = ChunkType.GENERIC,
    embedding: list[float] | None = None,
) -> Chunk:
    """Create a test chunk."""
    if embedding is None:
        embedding = [0.5] * 384
    return Chunk(
        id=chunk_id,
        document_id=document_id,
        chunk_type=chunk_type,
        content=content,
        start_line=1,
        end_line=10,
        token_count=token_count,
        name=name,
        embedding=embedding,
        metadata={"file_path": "test.py"},
    )


def make_document(
    doc_id: str = "doc-1",
    path: str = "test.py",
    doc_type: DocumentType = DocumentType.CODE,
    language: str | None = "python",
) -> Document:
    """Create a test document."""
    return Document(
        id=doc_id,
        path=path,
        absolute_path=f"/project/{path}",
        document_type=doc_type,
        content_hash="abc123",
        file_size=1000,
        language=language,
    )


def make_search_result(
    chunk: Chunk | None = None,
    document: Document | None = None,
    score: float = 0.8,
    rank: int = 1,
) -> SearchResult:
    """Create a test search result."""
    if chunk is None:
        chunk = make_chunk()
    if document is None:
        document = make_document()

    return SearchResult(
        chunk=chunk,
        document=document,
        score=score,
        rank=rank,
        snippet=chunk.content[:100],
    )


class TestRankerConfig:
    """Tests for RankerConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RankerConfig()

        assert config.boost_exact_match == 1.2
        assert config.boost_name_match == 1.1
        assert config.boost_recent == 1.0
        assert config.decay_long_content == 0.95
        assert config.max_content_tokens == 2000

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RankerConfig(
            boost_exact_match=1.5,
            boost_name_match=1.3,
            max_content_tokens=1000,
        )

        assert config.boost_exact_match == 1.5
        assert config.boost_name_match == 1.3
        assert config.max_content_tokens == 1000


class TestResultRanker:
    """Tests for ResultRanker."""

    def test_rank_empty_results(self) -> None:
        """Test ranking empty results."""
        ranker = ResultRanker()
        results = ranker.rank([], "test query")
        assert results == []

    def test_rank_single_result(self) -> None:
        """Test ranking single result."""
        ranker = ResultRanker()
        result = make_search_result(score=0.7)

        ranked = ranker.rank([result], "test")

        assert len(ranked) == 1
        assert ranked[0].rank == 1

    def test_rank_boosts_exact_match(self) -> None:
        """Test exact match gets boosted."""
        ranker = ResultRanker(RankerConfig(boost_exact_match=1.5))

        # Result with exact query match
        chunk_with_match = make_chunk(content="This contains test query exactly")
        result_with_match = make_search_result(
            chunk=chunk_with_match, score=0.7
        )

        # Result without match
        chunk_without = make_chunk(content="This is different content")
        result_without = make_search_result(chunk=chunk_without, score=0.75)

        ranked = ranker.rank([result_without, result_with_match], "test query")

        # Result with exact match should be boosted
        assert ranked[0].chunk.content == chunk_with_match.content

    def test_rank_boosts_name_match(self) -> None:
        """Test name match gets boosted."""
        ranker = ResultRanker(RankerConfig(boost_name_match=1.3))

        # Result with name matching query term
        chunk_with_name = make_chunk(
            content="Some content",
            name="authentication_handler",
        )
        result_with_name = make_search_result(chunk=chunk_with_name, score=0.6)

        # Result without name match
        chunk_without = make_chunk(content="Other content", name="other_function")
        result_without = make_search_result(chunk=chunk_without, score=0.65)

        ranked = ranker.rank(
            [result_without, result_with_name], "authentication"
        )

        # Result with name match should be ranked higher
        assert ranked[0].chunk.name == "authentication_handler"

    def test_rank_decays_long_content(self) -> None:
        """Test long content gets decay applied."""
        config = RankerConfig(decay_long_content=0.5, max_content_tokens=100)
        ranker = ResultRanker(config)

        # Long content
        long_chunk = make_chunk(content="x" * 1000, token_count=500)
        long_result = make_search_result(chunk=long_chunk, score=0.8)

        # Short content
        short_chunk = make_chunk(content="short", token_count=50)
        short_result = make_search_result(chunk=short_chunk, score=0.75)

        ranked = ranker.rank([long_result, short_result], "test")

        # Short content should rank higher due to decay on long
        assert ranked[0].chunk.token_count < 100

    def test_rank_updates_rank_numbers(self) -> None:
        """Test that rank numbers are updated correctly."""
        ranker = ResultRanker()

        results = [
            make_search_result(score=0.5, rank=99),
            make_search_result(score=0.8, rank=99),
            make_search_result(score=0.6, rank=99),
        ]

        ranked = ranker.rank(results, "test")

        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3

    def test_rank_clamps_scores(self) -> None:
        """Test that scores are clamped to valid range."""
        config = RankerConfig(boost_exact_match=2.0)  # High boost
        ranker = ResultRanker(config)

        chunk = make_chunk(content="test query here")
        result = make_search_result(chunk=chunk, score=0.9)

        ranked = ranker.rank([result], "test query")

        # Score should be clamped to 1.0 max
        assert ranked[0].score <= 1.0
        assert ranked[0].score >= 0.0


class TestRetrievalContext:
    """Tests for RetrievalContext."""

    def test_initial_state(self) -> None:
        """Test initial context state."""
        ctx = RetrievalContext(query="test")

        assert ctx.query == "test"
        assert ctx.results == []
        assert ctx.total_tokens == 0
        assert ctx.max_tokens is None

    def test_can_add_result_no_limit(self) -> None:
        """Test can always add result when no token limit."""
        ctx = RetrievalContext(query="test", max_tokens=None)
        chunk = make_chunk(token_count=1000)

        assert ctx.can_add_result(chunk) is True

    def test_can_add_result_within_limit(self) -> None:
        """Test can add result when within token limit."""
        ctx = RetrievalContext(query="test", max_tokens=500)
        chunk = make_chunk(token_count=100)

        assert ctx.can_add_result(chunk) is True

    def test_can_add_result_exceeds_limit(self) -> None:
        """Test cannot add result when exceeds token limit."""
        ctx = RetrievalContext(query="test", max_tokens=100, total_tokens=80)
        chunk = make_chunk(token_count=50)

        assert ctx.can_add_result(chunk) is False

    def test_add_result_updates_state(self) -> None:
        """Test adding result updates context state."""
        ctx = RetrievalContext(query="test")
        chunk = make_chunk(token_count=100)
        result = make_search_result(chunk=chunk)

        ctx.add_result(result)

        assert len(ctx.results) == 1
        assert ctx.total_tokens == 100


class TestRAGRetriever:
    """Tests for RAGRetriever."""

    @pytest.fixture
    def retriever_setup(self):
        """Set up retriever with mock components."""
        config = RAGConfig(
            default_max_results=5,
            default_min_score=0.5,
            context_token_budget=4000,
        )
        provider = MockEmbeddingProvider(dimension=384)
        store = MockVectorStore()
        retriever = RAGRetriever(
            config=config,
            embedding_provider=provider,
            vector_store=store,
        )
        return retriever, config, provider, store

    def test_retriever_creation(self, retriever_setup) -> None:
        """Test retriever can be created."""
        retriever, config, provider, store = retriever_setup

        assert retriever.config == config
        assert retriever.embedding_provider == provider
        assert retriever.vector_store == store

    def test_search_empty_store(self, retriever_setup) -> None:
        """Test search on empty store returns empty list."""
        retriever, _, _, _ = retriever_setup

        results = asyncio.get_event_loop().run_until_complete(
            retriever.search("test query")
        )

        assert results == []

    def test_search_with_results(self, retriever_setup) -> None:
        """Test search returns results."""
        retriever, config, provider, store = retriever_setup

        # Get the embedding that the provider will generate for our query
        query = "Python function"
        query_embedding = asyncio.get_event_loop().run_until_complete(
            provider.embed(query)
        )

        # Add chunks to store with the same embedding as query will produce
        chunks = [
            make_chunk("chunk-1", "doc-1", "Python function definition", embedding=query_embedding),
            make_chunk("chunk-2", "doc-1", "JavaScript async await", embedding=query_embedding),
        ]
        asyncio.get_event_loop().run_until_complete(store.add(chunks))

        # Use a lower min_score to ensure results are returned
        filter = SearchFilter(min_score=0.0, max_results=10)
        results = asyncio.get_event_loop().run_until_complete(
            retriever.search(query, filter=filter)
        )

        assert len(results) > 0

    def test_search_respects_max_results(self, retriever_setup) -> None:
        """Test search respects max_results parameter."""
        retriever, _, _, store = retriever_setup

        # Add many chunks
        chunks = [
            make_chunk(f"chunk-{i}", "doc-1", f"Content {i}")
            for i in range(10)
        ]
        asyncio.get_event_loop().run_until_complete(store.add(chunks))

        results = asyncio.get_event_loop().run_until_complete(
            retriever.search("Content", max_results=3)
        )

        assert len(results) <= 3

    def test_search_respects_min_score(self, retriever_setup) -> None:
        """Test search filters by minimum score."""
        retriever, _, _, store = retriever_setup

        # Add chunk
        chunk = make_chunk("chunk-1", "doc-1", "Test content")
        asyncio.get_event_loop().run_until_complete(store.add([chunk]))

        # Search with high min_score
        filter = SearchFilter(min_score=0.99)
        results = asyncio.get_event_loop().run_until_complete(
            retriever.search("completely different query", filter=filter)
        )

        # Results below min_score should be filtered
        for result in results:
            assert result.score >= 0.99

    def test_search_by_type(self, retriever_setup) -> None:
        """Test search_by_type method."""
        retriever, _, _, store = retriever_setup

        chunk = make_chunk("chunk-1", "doc-1", "Test content")
        asyncio.get_event_loop().run_until_complete(store.add([chunk]))

        results = asyncio.get_event_loop().run_until_complete(
            retriever.search_by_type("Test", [DocumentType.CODE])
        )

        assert isinstance(results, list)

    def test_search_code(self, retriever_setup) -> None:
        """Test search_code method."""
        retriever, _, _, store = retriever_setup

        chunk = make_chunk("chunk-1", "doc-1", "def function():")
        asyncio.get_event_loop().run_until_complete(store.add([chunk]))

        results = asyncio.get_event_loop().run_until_complete(
            retriever.search_code("function", languages=["python"])
        )

        assert isinstance(results, list)

    def test_search_docs(self, retriever_setup) -> None:
        """Test search_docs method."""
        retriever, _, _, store = retriever_setup

        chunk = make_chunk("chunk-1", "doc-1", "# Documentation")
        asyncio.get_event_loop().run_until_complete(store.add([chunk]))

        results = asyncio.get_event_loop().run_until_complete(
            retriever.search_docs("Documentation")
        )

        assert isinstance(results, list)

    def test_format_results_for_context_empty(self, retriever_setup) -> None:
        """Test formatting empty results."""
        retriever, _, _, _ = retriever_setup

        formatted = retriever.format_results_for_context([])

        assert formatted == ""

    def test_format_results_for_context(self, retriever_setup) -> None:
        """Test formatting results for LLM context."""
        retriever, _, _, _ = retriever_setup

        chunk = make_chunk(content="def hello():\n    pass")
        doc = make_document(path="src/main.py", language="python")
        result = SearchResult(
            chunk=chunk,
            document=doc,
            score=0.85,
            rank=1,
            snippet="def hello():\n    pass",
        )

        formatted = retriever.format_results_for_context([result])

        assert "### Relevant Project Context" in formatted
        assert "src/main.py" in formatted
        assert "def hello():" in formatted
        assert "```python" in formatted

    def test_format_results_without_metadata(self, retriever_setup) -> None:
        """Test formatting results without metadata."""
        retriever, _, _, _ = retriever_setup

        chunk = make_chunk(content="Some code")
        doc = make_document()
        result = make_search_result(chunk=chunk, document=doc)

        formatted = retriever.format_results_for_context(
            [result], include_metadata=False
        )

        assert "lines" not in formatted
        assert "score:" not in formatted

    def test_clear_cache(self, retriever_setup) -> None:
        """Test clearing document cache."""
        retriever, _, _, _ = retriever_setup

        # Populate cache by reconstructing a document
        retriever._document_cache["doc-1"] = make_document()
        assert len(retriever._document_cache) > 0

        retriever.clear_cache()

        assert len(retriever._document_cache) == 0

    def test_reconstruct_chunk(self, retriever_setup) -> None:
        """Test reconstructing chunk from stored data."""
        retriever, _, _, _ = retriever_setup

        chunk_data = {
            "id": "chunk-1",
            "content": "Test content",
            "metadata": {
                "document_id": "doc-1",
                "chunk_type": "function",
                "start_line": 10,
                "end_line": 20,
                "token_count": 50,
                "name": "test_function",
                "file_path": "test.py",
            },
        }

        chunk = retriever._reconstruct_chunk(chunk_data)

        assert chunk.id == "chunk-1"
        assert chunk.content == "Test content"
        assert chunk.chunk_type == ChunkType.FUNCTION
        assert chunk.start_line == 10
        assert chunk.end_line == 20
        assert chunk.name == "test_function"

    def test_reconstruct_document(self, retriever_setup) -> None:
        """Test reconstructing document from chunk metadata."""
        retriever, _, _, _ = retriever_setup

        chunk_data = {
            "metadata": {
                "document_id": "doc-1",
                "file_path": "src/main.py",
                "language": "python",
            },
        }

        doc = retriever._reconstruct_document(chunk_data)

        assert doc.id == "doc-1"
        assert doc.path == "src/main.py"
        assert doc.document_type == DocumentType.CODE
        assert doc.language == "python"

    def test_reconstruct_document_caches(self, retriever_setup) -> None:
        """Test document reconstruction uses cache."""
        retriever, _, _, _ = retriever_setup

        chunk_data = {
            "metadata": {
                "document_id": "doc-1",
                "file_path": "test.py",
            },
        }

        # First call
        doc1 = retriever._reconstruct_document(chunk_data)
        # Second call should use cache
        doc2 = retriever._reconstruct_document(chunk_data)

        assert doc1 is doc2  # Same object from cache


class TestRAGRetrieverEdgeCases:
    """Edge case tests for RAGRetriever."""

    def test_handles_unknown_chunk_type(self) -> None:
        """Test handling of unknown chunk type."""
        config = RAGConfig()
        provider = MockEmbeddingProvider()
        store = MockVectorStore()
        retriever = RAGRetriever(config, provider, store)

        chunk_data = {
            "id": "chunk-1",
            "content": "Test",
            "metadata": {
                "chunk_type": "unknown_type",
                "document_id": "doc-1",
            },
        }

        chunk = retriever._reconstruct_chunk(chunk_data)

        assert chunk.chunk_type == ChunkType.GENERIC

    def test_handles_missing_metadata(self) -> None:
        """Test handling of missing metadata fields."""
        config = RAGConfig()
        provider = MockEmbeddingProvider()
        store = MockVectorStore()
        retriever = RAGRetriever(config, provider, store)

        chunk_data = {
            "id": "chunk-1",
            "content": "Test",
            "metadata": {},
        }

        chunk = retriever._reconstruct_chunk(chunk_data)

        assert chunk.id == "chunk-1"
        assert chunk.start_line == 1
        assert chunk.end_line == 1
        assert chunk.token_count == 0

    def test_custom_ranker(self) -> None:
        """Test using custom ranker."""
        config = RAGConfig()
        provider = MockEmbeddingProvider()
        store = MockVectorStore()
        custom_ranker = ResultRanker(RankerConfig(boost_exact_match=2.0))

        retriever = RAGRetriever(
            config, provider, store, ranker=custom_ranker
        )

        assert retriever.ranker.config.boost_exact_match == 2.0
