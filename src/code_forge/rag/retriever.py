"""Semantic search retrieval for RAG system.

This module provides retrieval functionality for semantic search:
- RAGRetriever: Main retrieval interface
- ResultRanker: Re-ranking and scoring logic

Example:
    from code_forge.rag.retriever import RAGRetriever
    from code_forge.rag.config import RAGConfig

    retriever = RAGRetriever(
        config=config,
        embedding_provider=provider,
        vector_store=store,
    )

    # Search for relevant content
    results = await retriever.search("authentication handler")
    for result in results:
        print(f"{result.document.path}: {result.score:.2f}")
        print(result.snippet)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import (
    Chunk,
    ChunkType,
    Document,
    DocumentType,
    SearchFilter,
    SearchResult,
)

if TYPE_CHECKING:
    from .config import RAGConfig
    from .embeddings import EmbeddingProvider
    from .vectorstore import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RankerConfig:
    """Configuration for result ranking.

    Attributes:
        boost_exact_match: Boost factor for exact query matches.
        boost_name_match: Boost factor for name/title matches.
        boost_recent: Boost factor for recently indexed content.
        decay_long_content: Decay factor for very long content.
    """

    boost_exact_match: float = 1.2
    boost_name_match: float = 1.1
    boost_recent: float = 1.0
    decay_long_content: float = 0.95
    max_content_tokens: int = 2000


class ResultRanker:
    """Re-rank and score search results.

    Applies additional scoring factors beyond vector similarity:
    - Boost for exact query matches
    - Boost for name/title matches
    - Decay for very long content

    Attributes:
        config: Ranker configuration.
    """

    def __init__(self, config: RankerConfig | None = None) -> None:
        """Initialize the ranker.

        Args:
            config: Ranker configuration. Uses defaults if not provided.
        """
        self.config = config or RankerConfig()

    def rank(
        self,
        results: list[SearchResult],
        query: str,
    ) -> list[SearchResult]:
        """Re-rank search results.

        Args:
            results: Initial search results.
            query: Original search query.

        Returns:
            Re-ranked results sorted by adjusted score.
        """
        if not results:
            return results

        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored_results: list[tuple[float, SearchResult]] = []

        for result in results:
            score = result.score

            # Boost for exact match in content
            content_lower = result.chunk.content.lower()
            if query_lower in content_lower:
                score *= self.config.boost_exact_match

            # Boost for name/title match
            if result.chunk.name:
                name_lower = result.chunk.name.lower()
                if any(term in name_lower for term in query_terms):
                    score *= self.config.boost_name_match

            # Decay for very long content
            if result.chunk.token_count > self.config.max_content_tokens:
                score *= self.config.decay_long_content

            # Clamp score to valid range
            score = min(1.0, max(0.0, score))

            scored_results.append((score, result))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Update result scores and ranks
        ranked_results: list[SearchResult] = []
        for rank, (new_score, result) in enumerate(scored_results, start=1):
            # Create new result with updated score and rank
            ranked_results.append(
                SearchResult(
                    chunk=result.chunk,
                    document=result.document,
                    score=new_score,
                    rank=rank,
                    snippet=result.snippet,
                )
            )

        return ranked_results


@dataclass
class RetrievalContext:
    """Context for a retrieval operation.

    Tracks token usage and results during retrieval.

    Attributes:
        query: The search query.
        results: Retrieved results.
        total_tokens: Total tokens in results.
        max_tokens: Maximum tokens allowed.
    """

    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_tokens: int = 0
    max_tokens: int | None = None

    def can_add_result(self, chunk: Chunk) -> bool:
        """Check if a result can be added within token budget.

        Args:
            chunk: Chunk to potentially add.

        Returns:
            True if the chunk fits within the budget.
        """
        if self.max_tokens is None:
            return True
        return self.total_tokens + chunk.token_count <= self.max_tokens

    def add_result(self, result: SearchResult) -> None:
        """Add a result to the context.

        Args:
            result: Result to add.
        """
        self.results.append(result)
        self.total_tokens += result.chunk.token_count


class RAGRetriever:
    """Semantic search retriever for RAG.

    Provides semantic search over indexed documents with:
    - Vector similarity search
    - Filtering by document type, language, patterns
    - Token-aware result limiting
    - Result re-ranking

    Attributes:
        config: RAG configuration.
        embedding_provider: Provider for generating query embeddings.
        vector_store: Storage backend for searching.
        ranker: Result re-ranker.
    """

    def __init__(
        self,
        config: RAGConfig,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        ranker: ResultRanker | None = None,
    ) -> None:
        """Initialize the retriever.

        Args:
            config: RAG configuration.
            embedding_provider: Provider for generating embeddings.
            vector_store: Storage backend for searching.
            ranker: Optional custom ranker.
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.ranker = ranker or ResultRanker()
        self._document_cache: dict[str, Document] = {}

    async def search(
        self,
        query: str,
        filter: SearchFilter | None = None,
        max_results: int | None = None,
        max_tokens: int | None = None,
    ) -> list[SearchResult]:
        """Search for relevant content.

        Args:
            query: Natural language search query.
            filter: Optional search filters.
            max_results: Maximum number of results (overrides config).
            max_tokens: Maximum tokens in results (overrides config).

        Returns:
            List of search results, ranked by relevance.
        """
        # Apply defaults from config
        if max_results is None:
            max_results = self.config.default_max_results
        if max_tokens is None:
            max_tokens = self.config.context_token_budget

        # Create search filter with defaults
        if filter is None:
            filter = SearchFilter(
                min_score=self.config.default_min_score,
                max_results=max_results,
                max_tokens=max_tokens,
            )
        else:
            # Override with explicit parameters
            if max_results:
                filter.max_results = max_results
            if max_tokens:
                filter.max_tokens = max_tokens

        # Generate query embedding
        query_embedding = await self.embedding_provider.embed(query)

        # Search vector store (get more than needed for filtering/ranking)
        search_k = min(filter.max_results * 3, 100)
        raw_results = await self.vector_store.search(
            query_embedding,
            k=search_k,
            filter=filter,
        )

        if not raw_results:
            return []

        # Build search results with documents
        context = RetrievalContext(
            query=query,
            max_tokens=filter.max_tokens,
        )

        search_results: list[SearchResult] = []
        for chunk_id, score in raw_results:
            # Skip if below minimum score
            if score < filter.min_score:
                continue

            # Get chunk data
            chunk_data = await self.vector_store.get_chunk(chunk_id)
            if chunk_data is None:
                continue

            # Reconstruct chunk and document
            chunk = self._reconstruct_chunk(chunk_data)
            document = self._reconstruct_document(chunk_data)

            # Check token budget
            if not context.can_add_result(chunk):
                break

            # Create search result
            result = SearchResult.create(
                chunk=chunk,
                document=document,
                score=score,
                rank=len(search_results) + 1,
            )

            search_results.append(result)
            context.add_result(result)

            # Check max results
            if len(search_results) >= filter.max_results:
                break

        # Re-rank results
        ranked_results = self.ranker.rank(search_results, query)

        logger.debug(
            f"Search '{query[:50]}...' returned {len(ranked_results)} results "
            f"({context.total_tokens} tokens)"
        )

        return ranked_results

    async def search_by_type(
        self,
        query: str,
        document_types: list[DocumentType],
        max_results: int | None = None,
    ) -> list[SearchResult]:
        """Search within specific document types.

        Args:
            query: Search query.
            document_types: Types of documents to search.
            max_results: Maximum number of results.

        Returns:
            List of search results.
        """
        filter = SearchFilter(
            document_types=document_types,
            min_score=self.config.default_min_score,
            max_results=max_results or self.config.default_max_results,
        )
        return await self.search(query, filter=filter)

    async def search_code(
        self,
        query: str,
        languages: list[str] | None = None,
        max_results: int | None = None,
    ) -> list[SearchResult]:
        """Search within code files.

        Args:
            query: Search query.
            languages: Optional list of languages to search.
            max_results: Maximum number of results.

        Returns:
            List of search results from code files.
        """
        filter = SearchFilter(
            document_types=[DocumentType.CODE],
            languages=languages or [],
            min_score=self.config.default_min_score,
            max_results=max_results or self.config.default_max_results,
        )
        return await self.search(query, filter=filter)

    async def search_docs(
        self,
        query: str,
        max_results: int | None = None,
    ) -> list[SearchResult]:
        """Search within documentation files.

        Args:
            query: Search query.
            max_results: Maximum number of results.

        Returns:
            List of search results from documentation.
        """
        filter = SearchFilter(
            document_types=[DocumentType.DOCUMENTATION],
            min_score=self.config.default_min_score,
            max_results=max_results or self.config.default_max_results,
        )
        return await self.search(query, filter=filter)

    def _reconstruct_chunk(self, chunk_data: dict[str, Any]) -> Chunk:
        """Reconstruct a Chunk from stored data.

        Args:
            chunk_data: Data from vector store.

        Returns:
            Chunk object.
        """
        metadata = chunk_data.get("metadata", {})

        # Map stored chunk_type string to enum
        chunk_type_str = metadata.get("chunk_type", "generic")
        try:
            chunk_type = ChunkType(chunk_type_str)
        except ValueError:
            chunk_type = ChunkType.GENERIC

        return Chunk(
            id=chunk_data.get("id", ""),
            document_id=metadata.get("document_id", ""),
            chunk_type=chunk_type,
            content=chunk_data.get("content", ""),
            start_line=metadata.get("start_line", 1),
            end_line=metadata.get("end_line", 1),
            token_count=metadata.get("token_count", 0),
            name=metadata.get("name"),
            metadata={
                k: v
                for k, v in metadata.items()
                if k
                not in {
                    "document_id",
                    "chunk_type",
                    "start_line",
                    "end_line",
                    "token_count",
                    "name",
                }
            },
        )

    def _reconstruct_document(self, chunk_data: dict[str, Any]) -> Document:
        """Reconstruct a Document from chunk metadata.

        Args:
            chunk_data: Data from vector store.

        Returns:
            Document object (minimal, reconstructed from chunk metadata).
        """
        metadata = chunk_data.get("metadata", {})
        file_path = metadata.get("file_path", "unknown")
        document_id = metadata.get("document_id", "")

        # Check cache
        if document_id in self._document_cache:
            return self._document_cache[document_id]

        # Detect document type from path
        from pathlib import Path

        path = Path(file_path)
        ext = path.suffix.lower()

        doc_type = DocumentType.OTHER
        if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs"}:
            doc_type = DocumentType.CODE
        elif ext in {".md", ".rst", ".txt"}:
            doc_type = DocumentType.DOCUMENTATION
        elif ext in {".json", ".yaml", ".yml", ".toml"}:
            doc_type = DocumentType.CONFIG

        document = Document(
            id=document_id,
            path=file_path,
            absolute_path=file_path,  # May not be accurate
            document_type=doc_type,
            content_hash="",  # Not available from chunk data
            file_size=0,
            language=metadata.get("language"),
        )

        # Cache for reuse
        self._document_cache[document_id] = document

        return document

    def format_results_for_context(
        self,
        results: list[SearchResult],
        include_metadata: bool = True,
    ) -> str:
        """Format search results for LLM context.

        Args:
            results: Search results to format.
            include_metadata: Whether to include file paths and line numbers.

        Returns:
            Formatted string suitable for LLM context.
        """
        if not results:
            return ""

        lines: list[str] = []
        lines.append("### Relevant Project Context")
        lines.append("")

        for result in results:
            if include_metadata:
                lines.append(
                    f"**{result.document.path}** "
                    f"(lines {result.chunk.start_line}-{result.chunk.end_line}, "
                    f"score: {result.score:.2f}):"
                )
            else:
                lines.append(f"**{result.document.path}**:")

            # Add code block with language hint
            lang = result.document.language or ""
            lines.append(f"```{lang}")
            lines.append(result.snippet)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def clear_cache(self) -> None:
        """Clear the document cache."""
        self._document_cache.clear()
