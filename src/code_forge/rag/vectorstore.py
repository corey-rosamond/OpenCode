"""Vector store backends for RAG system.

This module provides vector storage abstractions for storing and
searching document embeddings:

- ChromaStore: ChromaDB backend (default, pure Python, persistent)
- FAISSStore: FAISS backend (faster, requires faiss-cpu)
- MockVectorStore: In-memory store for testing

Example:
    from code_forge.rag.vectorstore import get_vector_store
    from code_forge.rag.config import RAGConfig
    from pathlib import Path

    config = RAGConfig()
    store = get_vector_store(config, Path("/project"))

    # Add chunks with embeddings
    await store.add(chunks)

    # Search for similar content
    results = await store.search(query_embedding, k=5)
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import RAGConfig
    from .models import Chunk, SearchFilter

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector store backends.

    All vector stores must implement this interface for consistent
    behavior across different backends (ChromaDB, FAISS, etc.).
    """

    @abstractmethod
    async def add(self, chunks: list[Chunk]) -> int:
        """Add chunks with embeddings to the store.

        Args:
            chunks: List of chunks with embeddings set.

        Returns:
            Number of chunks added.

        Raises:
            ValueError: If chunks don't have embeddings.
        """
        ...

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        k: int = 10,
        filter: SearchFilter | None = None,
    ) -> list[tuple[str, float]]:
        """Search for similar chunks.

        Args:
            embedding: Query embedding vector.
            k: Maximum number of results.
            filter: Optional search filters.

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending.
        """
        ...

    @abstractmethod
    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by ID.

        Args:
            chunk_ids: List of chunk IDs to delete.

        Returns:
            Number of chunks deleted.
        """
        ...

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID whose chunks should be deleted.

        Returns:
            Number of chunks deleted.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Delete all chunks from the store."""
        ...

    @abstractmethod
    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get a chunk by ID.

        Args:
            chunk_id: The chunk ID.

        Returns:
            Chunk data as dictionary, or None if not found.
        """
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Dictionary with stats like total_chunks, storage_size, etc.
        """
        ...

    @abstractmethod
    async def get_all_chunk_ids(self) -> list[str]:
        """Get all chunk IDs in the store.

        Returns:
            List of all chunk IDs.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the store backend name."""
        ...


class ChromaStore(VectorStore):
    """ChromaDB vector store implementation.

    Uses ChromaDB for persistent vector storage with cosine similarity search.
    ChromaDB is a pure Python library that doesn't require external services.

    Attributes:
        persist_directory: Directory for persistent storage.
        collection_name: Name of the ChromaDB collection.
    """

    def __init__(
        self,
        persist_directory: Path,
        collection_name: str = "code_forge_index",
    ) -> None:
        """Initialize ChromaDB store.

        Args:
            persist_directory: Directory to persist the database.
            collection_name: Name for the collection.
        """
        self._persist_dir = persist_directory
        self._collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Get the store backend name."""
        return "chroma"

    def _ensure_initialized_sync(self) -> None:
        """Initialize ChromaDB client and collection (synchronous).

        Raises:
            ImportError: If chromadb is not installed.
        """
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            raise ImportError(
                "chromadb is required for ChromaStore. "
                "Install with: pip install 'code-forge[rag]'"
            ) from e

        # Create persist directory
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize client with persistence
        settings = Settings(
            persist_directory=str(self._persist_dir),
            anonymized_telemetry=False,
        )
        self._client = chromadb.Client(settings)

        # Get or create collection with cosine similarity
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"ChromaDB initialized at {self._persist_dir} "
            f"with {self._collection.count()} chunks"
        )

    async def _ensure_initialized(self) -> None:
        """Initialize ChromaDB client and collection (async, thread-safe)."""
        if self._client is not None:
            return

        async with self._lock:
            if self._client is not None:
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._ensure_initialized_sync)

    async def add(self, chunks: list[Chunk]) -> int:
        """Add chunks with embeddings to ChromaDB.

        Args:
            chunks: List of chunks with embeddings.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        # Validate all chunks have embeddings
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")

        await self._ensure_initialized()

        # Prepare data for ChromaDB
        ids = [chunk.id for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": chunk.document_id,
                "chunk_type": chunk.chunk_type.value,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "token_count": chunk.token_count,
                "name": chunk.name or "",
                **{k: str(v) for k, v in chunk.metadata.items()},
            }
            for chunk in chunks
        ]

        def _add() -> None:
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _add)

        logger.debug(f"Added {len(chunks)} chunks to ChromaDB")
        return len(chunks)

    async def search(
        self,
        embedding: list[float],
        k: int = 10,
        filter: SearchFilter | None = None,
    ) -> list[tuple[str, float]]:
        """Search for similar chunks in ChromaDB.

        Args:
            embedding: Query embedding vector.
            k: Maximum number of results.
            filter: Optional search filters.

        Returns:
            List of (chunk_id, similarity_score) tuples.
        """
        await self._ensure_initialized()

        # Build ChromaDB where clause from filter
        where: dict[str, Any] | None = None
        if filter:
            where = self._build_where_clause(filter)

        def _search() -> dict[str, Any]:
            result: dict[str, Any] = self._collection.query(
                query_embeddings=[embedding],
                n_results=k,
                where=where,
                include=["distances"],
            )
            return result

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search)

        # Convert distances to similarity scores
        # ChromaDB returns L2 distance for cosine space (actually 1 - similarity)
        chunk_ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Convert distance to similarity (cosine distance = 1 - similarity)
        scores = [1.0 - d for d in distances]

        return list(zip(chunk_ids, scores, strict=True))

    def _build_where_clause(self, filter: SearchFilter) -> dict[str, Any] | None:
        """Build ChromaDB where clause from SearchFilter.

        Args:
            filter: Search filter configuration.

        Returns:
            ChromaDB where clause dict, or None if no filters.
        """
        conditions: list[dict[str, Any]] = []

        # Filter by document types
        if filter.document_types:
            type_values = [dt.value for dt in filter.document_types]
            if len(type_values) == 1:
                conditions.append({"chunk_type": {"$eq": type_values[0]}})
            else:
                conditions.append({"chunk_type": {"$in": type_values}})

        # Filter by languages
        if filter.languages:
            if len(filter.languages) == 1:
                conditions.append({"language": {"$eq": filter.languages[0]}})
            else:
                conditions.append({"language": {"$in": filter.languages}})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by ID.

        Args:
            chunk_ids: List of chunk IDs to delete.

        Returns:
            Number of chunks deleted.
        """
        if not chunk_ids:
            return 0

        await self._ensure_initialized()

        def _delete() -> None:
            self._collection.delete(ids=chunk_ids)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _delete)

        logger.debug(f"Deleted {len(chunk_ids)} chunks from ChromaDB")
        return len(chunk_ids)

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID whose chunks should be deleted.

        Returns:
            Number of chunks deleted.
        """
        await self._ensure_initialized()

        def _delete() -> int:
            # Get chunks for this document
            results = self._collection.get(
                where={"document_id": {"$eq": document_id}},
                include=[],
            )
            chunk_ids = results.get("ids", [])

            if chunk_ids:
                self._collection.delete(ids=chunk_ids)

            return len(chunk_ids)

        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(None, _delete)

        logger.debug(f"Deleted {count} chunks for document {document_id}")
        return count

    async def clear(self) -> None:
        """Delete all chunks from the store."""
        await self._ensure_initialized()

        def _clear() -> None:
            # Delete and recreate collection
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _clear)

        logger.info("Cleared all chunks from ChromaDB")

    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get a chunk by ID.

        Args:
            chunk_id: The chunk ID.

        Returns:
            Chunk data as dictionary, or None if not found.
        """
        await self._ensure_initialized()

        def _get() -> dict[str, Any] | None:
            results = self._collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas", "embeddings"],
            )

            if not results["ids"]:
                return None

            return {
                "id": results["ids"][0],
                "content": results["documents"][0],
                "metadata": results["metadatas"][0],
                "embedding": results["embeddings"][0] if results["embeddings"] else None,
            }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get)

    def get_stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Dictionary with storage stats.
        """
        if self._collection is None:
            return {
                "total_chunks": 0,
                "storage_size_bytes": 0,
                "backend": "chroma",
                "initialized": False,
            }

        total_chunks = self._collection.count()

        # Estimate storage size from directory
        storage_size = 0
        if self._persist_dir.exists():
            for file in self._persist_dir.rglob("*"):
                if file.is_file():
                    storage_size += file.stat().st_size

        return {
            "total_chunks": total_chunks,
            "storage_size_bytes": storage_size,
            "backend": "chroma",
            "persist_directory": str(self._persist_dir),
            "collection_name": self._collection_name,
            "initialized": True,
        }

    async def get_all_chunk_ids(self) -> list[str]:
        """Get all chunk IDs in the store.

        Returns:
            List of all chunk IDs.
        """
        await self._ensure_initialized()

        def _get_ids() -> list[str]:
            # Get all IDs from collection
            results = self._collection.get(include=[])
            return results.get("ids", [])

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_ids)


class FAISSStore(VectorStore):
    """FAISS vector store implementation.

    Uses FAISS for fast similarity search. More efficient than ChromaDB
    for large indexes but requires the faiss-cpu package.

    Stores index and metadata in separate files for persistence.

    Attributes:
        persist_directory: Directory for persistent storage.
        dimension: Embedding dimension.
    """

    def __init__(
        self,
        persist_directory: Path,
        dimension: int = 384,
    ) -> None:
        """Initialize FAISS store.

        Args:
            persist_directory: Directory to persist the index.
            dimension: Embedding dimension (must match embedding provider).
        """
        self._persist_dir = persist_directory
        self._dimension = dimension
        self._index: Any = None
        self._metadata: dict[str, dict[str, Any]] = {}  # chunk_id -> metadata
        self._id_to_idx: dict[str, int] = {}  # chunk_id -> FAISS index position
        self._idx_to_id: dict[int, str] = {}  # FAISS index position -> chunk_id
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def name(self) -> str:
        """Get the store backend name."""
        return "faiss"

    def _ensure_initialized_sync(self) -> None:
        """Initialize FAISS index (synchronous).

        Raises:
            ImportError: If faiss is not installed.
        """
        if self._initialized:
            return

        try:
            import faiss
        except ImportError as e:
            raise ImportError(
                "faiss-cpu is required for FAISSStore. "
                "Install with: pip install faiss-cpu"
            ) from e

        self._persist_dir.mkdir(parents=True, exist_ok=True)

        index_path = self._persist_dir / "index.faiss"
        metadata_path = self._persist_dir / "metadata.json"

        if index_path.exists() and metadata_path.exists():
            # Load existing index
            self._index = faiss.read_index(str(index_path))
            with metadata_path.open() as f:
                data = json.load(f)
                self._metadata = data.get("metadata", {})
                self._id_to_idx = data.get("id_to_idx", {})
                self._idx_to_id = {int(k): v for k, v in data.get("idx_to_id", {}).items()}

            logger.info(
                f"FAISS index loaded from {self._persist_dir} "
                f"with {self._index.ntotal} vectors"
            )
        else:
            # Create new index with inner product (for normalized vectors = cosine)
            self._index = faiss.IndexFlatIP(self._dimension)
            logger.info(f"Created new FAISS index with dimension {self._dimension}")

        self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Initialize FAISS index (async, thread-safe)."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._ensure_initialized_sync)

    def _save_sync(self) -> None:
        """Save index and metadata to disk."""
        import faiss

        index_path = self._persist_dir / "index.faiss"
        metadata_path = self._persist_dir / "metadata.json"

        faiss.write_index(self._index, str(index_path))

        with metadata_path.open("w") as f:
            json.dump(
                {
                    "metadata": self._metadata,
                    "id_to_idx": self._id_to_idx,
                    "idx_to_id": {str(k): v for k, v in self._idx_to_id.items()},
                },
                f,
            )

    async def _save(self) -> None:
        """Save index and metadata to disk (async)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_sync)

    async def add(self, chunks: list[Chunk]) -> int:
        """Add chunks with embeddings to FAISS.

        Args:
            chunks: List of chunks with embeddings.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        import numpy as np

        # Validate embeddings
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")

        await self._ensure_initialized()

        # Prepare embeddings as numpy array
        embeddings = np.array(
            [chunk.embedding for chunk in chunks], dtype=np.float32
        )

        # Normalize for cosine similarity
        faiss = __import__("faiss")
        faiss.normalize_L2(embeddings)

        def _add() -> None:
            # Get current index size
            start_idx = self._index.ntotal

            # Add to FAISS index
            self._index.add(embeddings)

            # Update mappings
            for i, chunk in enumerate(chunks):
                idx = start_idx + i
                self._id_to_idx[chunk.id] = idx
                self._idx_to_id[idx] = chunk.id
                self._metadata[chunk.id] = {
                    "document_id": chunk.document_id,
                    "chunk_type": chunk.chunk_type.value,
                    "content": chunk.content,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "token_count": chunk.token_count,
                    "name": chunk.name,
                    **chunk.metadata,
                }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _add)
        await self._save()

        logger.debug(f"Added {len(chunks)} chunks to FAISS")
        return len(chunks)

    async def search(
        self,
        embedding: list[float],
        k: int = 10,
        filter: SearchFilter | None = None,
    ) -> list[tuple[str, float]]:
        """Search for similar chunks in FAISS.

        Args:
            embedding: Query embedding vector.
            k: Maximum number of results.
            filter: Optional search filters (applied post-search).

        Returns:
            List of (chunk_id, similarity_score) tuples.
        """
        import numpy as np

        await self._ensure_initialized()

        if self._index.ntotal == 0:
            return []

        # Prepare query
        query = np.array([embedding], dtype=np.float32)
        faiss = __import__("faiss")
        faiss.normalize_L2(query)

        # Search more than k if we have filters (we'll filter post-search)
        search_k = min(k * 3, self._index.ntotal) if filter else min(k, self._index.ntotal)

        def _search() -> tuple[Any, Any]:
            result: tuple[Any, Any] = self._index.search(query, search_k)
            return result

        loop = asyncio.get_event_loop()
        scores, indices = await loop.run_in_executor(None, _search)

        # Convert to results
        results: list[tuple[str, float]] = []
        for idx, score in zip(indices[0], scores[0], strict=True):
            if idx == -1:  # FAISS returns -1 for missing results
                continue

            chunk_id = self._idx_to_id.get(int(idx))
            if not chunk_id:
                continue

            # Apply filters if present
            if filter:
                metadata = self._metadata.get(chunk_id, {})
                if not self._matches_filter(metadata, filter):
                    continue

                if score < filter.min_score:
                    continue

            results.append((chunk_id, float(score)))

            if len(results) >= k:
                break

        return results

    def _matches_filter(
        self,
        metadata: dict[str, Any],
        filter: SearchFilter,
    ) -> bool:
        """Check if metadata matches filter criteria.

        Args:
            metadata: Chunk metadata.
            filter: Search filter.

        Returns:
            True if metadata matches all filter criteria.
        """
        # Check document types
        if filter.document_types:
            chunk_type = metadata.get("chunk_type")
            type_values = [dt.value for dt in filter.document_types]
            if chunk_type not in type_values:
                return False

        # Check languages
        if filter.languages:
            language = metadata.get("language")
            if language not in filter.languages:
                return False

        return True

    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by ID.

        Note: FAISS doesn't support deletion efficiently. We rebuild the index
        without the deleted chunks. For frequent deletions, consider using
        ChromaStore instead.

        Args:
            chunk_ids: List of chunk IDs to delete.

        Returns:
            Number of chunks deleted.
        """
        if not chunk_ids:
            return 0

        await self._ensure_initialized()

        deleted = 0

        # Remove from metadata and mappings
        for chunk_id in chunk_ids:
            if chunk_id in self._metadata:
                del self._metadata[chunk_id]
                deleted += 1

            if chunk_id in self._id_to_idx:
                idx = self._id_to_idx.pop(chunk_id)
                self._idx_to_id.pop(idx, None)

        # Rebuild index without deleted chunks (expensive but FAISS limitation)
        # For production, consider using IndexIVF with remove_ids
        if deleted > 0:
            await self._rebuild_index()

        return deleted

    async def _rebuild_index(self) -> None:
        """Rebuild FAISS index from remaining chunks."""
        if not self._metadata:
            # Empty index
            faiss = __import__("faiss")
            self._index = faiss.IndexFlatIP(self._dimension)
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            await self._save()
            return

        # This would require storing embeddings, which we don't currently do
        # For now, log a warning - a full implementation would store embeddings
        logger.warning(
            "FAISS index rebuild requires stored embeddings. "
            "Consider using ChromaStore for frequent deletions."
        )

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID whose chunks should be deleted.

        Returns:
            Number of chunks deleted.
        """
        # Find chunks for this document
        chunk_ids = [
            chunk_id
            for chunk_id, meta in self._metadata.items()
            if meta.get("document_id") == document_id
        ]

        return await self.delete(chunk_ids)

    async def clear(self) -> None:
        """Delete all chunks from the store."""
        await self._ensure_initialized()

        faiss = __import__("faiss")
        self._index = faiss.IndexFlatIP(self._dimension)
        self._metadata.clear()
        self._id_to_idx.clear()
        self._idx_to_id.clear()

        await self._save()
        logger.info("Cleared all chunks from FAISS")

    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get a chunk by ID.

        Args:
            chunk_id: The chunk ID.

        Returns:
            Chunk data as dictionary, or None if not found.
        """
        await self._ensure_initialized()

        metadata = self._metadata.get(chunk_id)
        if not metadata:
            return None

        return {
            "id": chunk_id,
            "content": metadata.get("content", ""),
            "metadata": metadata,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Dictionary with storage stats.
        """
        if not self._initialized:
            return {
                "total_chunks": 0,
                "storage_size_bytes": 0,
                "backend": "faiss",
                "dimension": self._dimension,
                "initialized": False,
            }

        # Calculate storage size
        storage_size = 0
        if self._persist_dir.exists():
            for file in self._persist_dir.rglob("*"):
                if file.is_file():
                    storage_size += file.stat().st_size

        return {
            "total_chunks": self._index.ntotal,
            "storage_size_bytes": storage_size,
            "backend": "faiss",
            "dimension": self._dimension,
            "persist_directory": str(self._persist_dir),
            "initialized": True,
        }

    async def get_all_chunk_ids(self) -> list[str]:
        """Get all chunk IDs in the store.

        Returns:
            List of all chunk IDs.
        """
        await self._ensure_initialized()
        return list(self._id_to_idx.keys())


class MockVectorStore(VectorStore):
    """In-memory vector store for testing.

    Stores chunks in memory and performs simple cosine similarity search.
    Useful for unit tests without requiring ChromaDB or FAISS.
    """

    def __init__(self) -> None:
        """Initialize mock store."""
        self._chunks: dict[str, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        """Get the store backend name."""
        return "mock"

    async def add(self, chunks: list[Chunk]) -> int:
        """Add chunks to mock store.

        Args:
            chunks: List of chunks with embeddings.

        Returns:
            Number of chunks added.
        """
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")

            self._chunks[chunk.id] = {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "chunk_type": chunk.chunk_type.value,
                "content": chunk.content,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "token_count": chunk.token_count,
                "name": chunk.name,
                "embedding": chunk.embedding,
                "metadata": chunk.metadata,
            }

        return len(chunks)

    async def search(
        self,
        embedding: list[float],
        k: int = 10,
        filter: SearchFilter | None = None,
    ) -> list[tuple[str, float]]:
        """Search for similar chunks using cosine similarity.

        Args:
            embedding: Query embedding vector.
            k: Maximum number of results.
            filter: Optional search filters.

        Returns:
            List of (chunk_id, similarity_score) tuples.
        """
        results: list[tuple[str, float]] = []

        for chunk_id, data in self._chunks.items():
            chunk_embedding = data.get("embedding", [])
            if not chunk_embedding:
                continue

            # Apply filters
            if filter:
                if filter.document_types:
                    type_values = [dt.value for dt in filter.document_types]
                    if data.get("chunk_type") not in type_values:
                        continue

                if filter.languages:
                    lang = data.get("metadata", {}).get("language")
                    if lang not in filter.languages:
                        continue

            # Compute cosine similarity
            score = self._cosine_similarity(embedding, chunk_embedding)

            if filter and score < filter.min_score:
                continue

            results.append((chunk_id, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:k]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity (0 to 1).
        """
        import math

        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by ID.

        Args:
            chunk_ids: List of chunk IDs to delete.

        Returns:
            Number of chunks deleted.
        """
        deleted = 0
        for chunk_id in chunk_ids:
            if chunk_id in self._chunks:
                del self._chunks[chunk_id]
                deleted += 1
        return deleted

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID whose chunks should be deleted.

        Returns:
            Number of chunks deleted.
        """
        chunk_ids = [
            chunk_id
            for chunk_id, data in self._chunks.items()
            if data.get("document_id") == document_id
        ]
        return await self.delete(chunk_ids)

    async def clear(self) -> None:
        """Delete all chunks from the store."""
        self._chunks.clear()

    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get a chunk by ID.

        Args:
            chunk_id: The chunk ID.

        Returns:
            Chunk data as dictionary, or None if not found.
        """
        return self._chunks.get(chunk_id)

    def get_stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Dictionary with storage stats.
        """
        return {
            "total_chunks": len(self._chunks),
            "storage_size_bytes": 0,
            "backend": "mock",
            "initialized": True,
        }

    async def get_all_chunk_ids(self) -> list[str]:
        """Get all chunk IDs in the store.

        Returns:
            List of all chunk IDs.
        """
        return list(self._chunks.keys())


def get_vector_store(
    config: RAGConfig,
    project_root: Path,
    dimension: int = 384,
) -> VectorStore:
    """Get the appropriate vector store based on configuration.

    Args:
        config: RAG configuration.
        project_root: Project root directory.
        dimension: Embedding dimension (for FAISS).

    Returns:
        Configured vector store instance.

    Raises:
        ValueError: If an unknown store type is specified.
    """
    from .config import VectorStoreType

    persist_dir = config.get_index_path(project_root)

    if config.vector_store == VectorStoreType.CHROMA:
        return ChromaStore(persist_directory=persist_dir)
    elif config.vector_store == VectorStoreType.FAISS:
        return FAISSStore(persist_directory=persist_dir, dimension=dimension)
    else:
        raise ValueError(f"Unknown vector store type: {config.vector_store}")
