"""RAG Manager - Central coordinator for RAG functionality.

This module provides the RAGManager class that coordinates all RAG
components: indexing, retrieval, and context augmentation.

Example:
    from code_forge.rag.manager import RAGManager
    from code_forge.rag.config import RAGConfig

    # Create manager for a project
    manager = RAGManager(project_root=Path.cwd())

    # Index the project
    stats = await manager.index_project()
    print(f"Indexed {stats.total_chunks} chunks")

    # Search for relevant content
    results = await manager.search("authentication handler")
    for result in results:
        print(f"{result.document.path}: {result.snippet}")

    # Augment context for a query
    context_text = await manager.augment_context("how does auth work?")
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import RAGConfig
from .embeddings import EmbeddingProvider, get_embedding_provider
from .indexer import ProjectIndexer
from .models import IndexStats, SearchFilter, SearchResult
from .retriever import RAGRetriever
from .vectorstore import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RAGStatus:
    """Status information for RAG system.

    Attributes:
        enabled: Whether RAG is enabled.
        initialized: Whether the manager is initialized.
        indexed: Whether the project has been indexed.
        total_chunks: Number of indexed chunks.
        total_documents: Approximate number of indexed documents.
        embedding_model: Name of the embedding model.
        vector_store: Name of the vector store.
        last_indexed: Timestamp of last indexing.
        index_directory: Path to the index directory.
    """

    enabled: bool
    initialized: bool
    indexed: bool
    total_chunks: int
    total_documents: int
    embedding_model: str
    vector_store: str
    last_indexed: datetime | None
    index_directory: str


class RAGManager:
    """Central coordinator for RAG functionality.

    Manages the lifecycle of RAG components and provides a unified
    interface for indexing, searching, and context augmentation.

    Attributes:
        project_root: Root directory of the project.
        config: RAG configuration.
    """

    def __init__(
        self,
        project_root: Path,
        config: RAGConfig | None = None,
    ) -> None:
        """Initialize the RAG manager.

        Args:
            project_root: Root directory of the project.
            config: RAG configuration. Uses defaults if not provided.
        """
        self.project_root = project_root
        self.config = config or RAGConfig()

        # Components are lazily initialized
        self._embedding_provider: EmbeddingProvider | None = None
        self._vector_store: VectorStore | None = None
        self._indexer: ProjectIndexer | None = None
        self._retriever: RAGRetriever | None = None

        self._initialized = False
        self._lock = asyncio.Lock()

    @property
    def is_enabled(self) -> bool:
        """Check if RAG is enabled.

        Returns:
            True if RAG is enabled in configuration.
        """
        return self.config.enabled

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized.

        Returns:
            True if components have been initialized.
        """
        return self._initialized

    async def initialize(self) -> None:
        """Initialize RAG components.

        Lazily initializes embedding provider, vector store,
        indexer, and retriever components.

        Raises:
            RuntimeError: If initialization fails.
        """
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            if not self.config.enabled:
                logger.info("RAG is disabled, skipping initialization")
                return

            try:
                logger.info(f"Initializing RAG for {self.project_root}")

                # Initialize embedding provider
                self._embedding_provider = get_embedding_provider(self.config)

                # Initialize vector store
                self._vector_store = get_vector_store(
                    self.config,
                    self.project_root,
                )

                # Initialize indexer
                self._indexer = ProjectIndexer(
                    project_root=self.project_root,
                    config=self.config,
                    embedding_provider=self._embedding_provider,
                    vector_store=self._vector_store,
                )

                # Initialize retriever
                self._retriever = RAGRetriever(
                    config=self.config,
                    embedding_provider=self._embedding_provider,
                    vector_store=self._vector_store,
                )

                self._initialized = True
                logger.info("RAG initialization complete")

            except Exception as e:
                logger.error(f"RAG initialization failed: {e}")
                raise RuntimeError(f"Failed to initialize RAG: {e}") from e

    async def index_project(self, force: bool = False) -> IndexStats:
        """Index the entire project.

        Args:
            force: If True, reindex all files regardless of changes.

        Returns:
            Statistics about the indexing operation.

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._indexer is None:
            raise RuntimeError("Indexer not initialized")

        logger.info(f"Indexing project: {self.project_root}")
        stats = await self._indexer.index_all(force=force)
        logger.info(
            f"Indexing complete: {stats.total_chunks} chunks, "
            f"{stats.total_documents} documents"
        )

        return stats

    async def index_file(self, file_path: Path) -> int:
        """Index a single file.

        Args:
            file_path: Path to the file to index.

        Returns:
            Number of chunks created.

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._indexer is None:
            raise RuntimeError("Indexer not initialized")

        return await self._indexer.index_file(file_path)

    async def remove_file(self, file_path: Path) -> int:
        """Remove a file from the index.

        Args:
            file_path: Path to the file to remove.

        Returns:
            Number of chunks removed.

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._indexer is None:
            raise RuntimeError("Indexer not initialized")

        return await self._indexer.remove_file(file_path)

    async def search(
        self,
        query: str,
        filter: SearchFilter | None = None,
        max_results: int | None = None,
    ) -> list[SearchResult]:
        """Search for relevant content.

        Args:
            query: Natural language search query.
            filter: Optional search filters.
            max_results: Maximum number of results.

        Returns:
            List of search results, ranked by relevance.

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        return await self._retriever.search(
            query=query,
            filter=filter,
            max_results=max_results,
        )

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

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        return await self._retriever.search_code(
            query=query,
            languages=languages,
            max_results=max_results,
        )

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

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        return await self._retriever.search_docs(
            query=query,
            max_results=max_results,
        )

    async def augment_context(self, query: str) -> str:
        """Get relevant context for a query.

        Searches for relevant content and formats it for
        inclusion in the LLM context.

        Args:
            query: User query or message.

        Returns:
            Formatted context string, or empty string if no results.

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._retriever is None:
            raise RuntimeError("Retriever not initialized")

        results = await self._retriever.search(
            query=query,
            max_results=self.config.default_max_results,
            max_tokens=self.config.context_token_budget,
        )

        if not results:
            return ""

        return self._retriever.format_results_for_context(results)

    async def clear_index(self) -> int:
        """Clear all indexed data.

        Returns:
            Number of chunks cleared.

        Raises:
            RuntimeError: If RAG is not enabled or initialized.
        """
        await self._ensure_initialized()

        if self._vector_store is None:
            raise RuntimeError("Vector store not initialized")

        # Get current count before clearing
        stats = self._vector_store.get_stats()
        count: int = stats.get("total_chunks", 0)

        await self._vector_store.clear()

        # Clear retriever cache
        if self._retriever is not None:
            self._retriever.clear_cache()

        logger.info(f"Cleared {count} chunks from index")
        return count

    async def get_status(self) -> RAGStatus:
        """Get RAG system status.

        Returns:
            Status information about the RAG system.
        """
        if not self.config.enabled:
            return RAGStatus(
                enabled=False,
                initialized=False,
                indexed=False,
                total_chunks=0,
                total_documents=0,
                embedding_model="",
                vector_store="",
                last_indexed=None,
                index_directory=str(self.config.get_index_path(self.project_root)),
            )

        if not self._initialized:
            return RAGStatus(
                enabled=True,
                initialized=False,
                indexed=False,
                total_chunks=0,
                total_documents=0,
                embedding_model=self.config.embedding_model,
                vector_store=self.config.vector_store.value,
                last_indexed=None,
                index_directory=str(self.config.get_index_path(self.project_root)),
            )

        # Get stats from components
        store_stats: dict[str, Any] = {}
        if self._vector_store is not None:
            store_stats = self._vector_store.get_stats()

        indexer_stats: dict[str, Any] = {}
        if self._indexer is not None:
            indexer_stats = self._indexer.get_stats()

        total_chunks = store_stats.get("total_chunks", 0)
        indexed = total_chunks > 0

        return RAGStatus(
            enabled=True,
            initialized=True,
            indexed=indexed,
            total_chunks=total_chunks,
            total_documents=total_chunks // 5,  # Approximate
            embedding_model=indexer_stats.get(
                "embedding_model", self.config.embedding_model
            ),
            vector_store=indexer_stats.get(
                "vector_store", self.config.vector_store.value
            ),
            last_indexed=indexer_stats.get("last_indexed"),
            index_directory=str(self.config.get_index_path(self.project_root)),
        )

    async def _ensure_initialized(self) -> None:
        """Ensure manager is initialized.

        Raises:
            RuntimeError: If RAG is disabled or initialization fails.
        """
        if not self.config.enabled:
            raise RuntimeError("RAG is not enabled")

        if not self._initialized:
            await self.initialize()

    def format_status(self, status: RAGStatus) -> str:
        """Format status for display.

        Args:
            status: RAG status to format.

        Returns:
            Formatted status string.
        """
        lines = ["### RAG Status", ""]

        if not status.enabled:
            lines.append("RAG is **disabled**")
            lines.append("")
            lines.append("Enable with: `/rag config enable`")
            return "\n".join(lines)

        lines.append(f"**Status:** {'Initialized' if status.initialized else 'Not initialized'}")
        lines.append(f"**Indexed:** {'Yes' if status.indexed else 'No'}")
        lines.append("")

        if status.indexed:
            lines.append(f"**Chunks:** {status.total_chunks}")
            lines.append(f"**Documents:** ~{status.total_documents}")
            lines.append("")

        lines.append(f"**Embedding Model:** {status.embedding_model}")
        lines.append(f"**Vector Store:** {status.vector_store}")
        lines.append(f"**Index Directory:** {status.index_directory}")

        if status.last_indexed:
            lines.append(f"**Last Indexed:** {status.last_indexed.isoformat()}")

        return "\n".join(lines)
