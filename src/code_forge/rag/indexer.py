"""Document indexing for RAG system.

This module provides document indexing functionality:
- FileProcessor: Read and preprocess files for indexing
- ProjectIndexer: Orchestrate indexing of entire projects

Example:
    from code_forge.rag.indexer import ProjectIndexer
    from code_forge.rag.config import RAGConfig
    from pathlib import Path

    config = RAGConfig()
    indexer = ProjectIndexer(
        project_root=Path.cwd(),
        config=config,
        embedding_provider=provider,
        vector_store=store,
    )

    # Index the project
    stats = await indexer.index_all()
    print(f"Indexed {stats.total_documents} documents")

    # Incremental update
    stats = await indexer.index_all(force=False)
"""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .chunking import detect_language, get_chunker
from .models import (
    Chunk,
    Document,
    DocumentType,
    IndexState,
    IndexStats,
)

if TYPE_CHECKING:
    from .config import RAGConfig
    from .embeddings import EmbeddingProvider
    from .vectorstore import VectorStore

logger = logging.getLogger(__name__)


class FileProcessor:
    """Process files for indexing.

    Handles reading files, detecting types, computing hashes,
    and creating Document objects.

    Attributes:
        project_root: Root directory of the project.
        config: RAG configuration.
    """

    # Extension to DocumentType mapping
    _DOC_TYPE_MAP: dict[str, DocumentType] = {
        ".py": DocumentType.CODE,
        ".pyi": DocumentType.CODE,
        ".js": DocumentType.CODE,
        ".jsx": DocumentType.CODE,
        ".ts": DocumentType.CODE,
        ".tsx": DocumentType.CODE,
        ".mjs": DocumentType.CODE,
        ".java": DocumentType.CODE,
        ".go": DocumentType.CODE,
        ".rs": DocumentType.CODE,
        ".c": DocumentType.CODE,
        ".cpp": DocumentType.CODE,
        ".h": DocumentType.CODE,
        ".hpp": DocumentType.CODE,
        ".rb": DocumentType.CODE,
        ".php": DocumentType.CODE,
        ".md": DocumentType.DOCUMENTATION,
        ".markdown": DocumentType.DOCUMENTATION,
        ".rst": DocumentType.DOCUMENTATION,
        ".txt": DocumentType.DOCUMENTATION,
        ".json": DocumentType.CONFIG,
        ".yaml": DocumentType.CONFIG,
        ".yml": DocumentType.CONFIG,
        ".toml": DocumentType.CONFIG,
        ".ini": DocumentType.CONFIG,
        ".cfg": DocumentType.CONFIG,
    }

    def __init__(self, project_root: Path, config: RAGConfig) -> None:
        """Initialize file processor.

        Args:
            project_root: Root directory of the project.
            config: RAG configuration.
        """
        self.project_root = project_root
        self.config = config
        self._gitignore_patterns: list[str] | None = None

    def should_process_file(self, file_path: Path) -> bool:
        """Check if a file should be processed.

        Args:
            file_path: Absolute path to the file.

        Returns:
            True if the file should be processed.
        """
        # Get relative path
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            return False

        rel_path_str = str(rel_path)

        # Check file size
        try:
            size_kb = file_path.stat().st_size / 1024
            if size_kb > self.config.max_file_size_kb:
                logger.debug(f"Skipping {rel_path}: file too large ({size_kb:.1f}KB)")
                return False
        except OSError:
            return False

        # Check config patterns
        if not self.config.should_include_file(rel_path_str):
            return False

        # Check gitignore patterns
        if self.config.respect_gitignore and self._is_gitignored(rel_path):
            logger.debug(f"Skipping {rel_path}: matches gitignore")
            return False

        return True

    def _is_gitignored(self, rel_path: Path) -> bool:
        """Check if a path matches gitignore patterns.

        Args:
            rel_path: Relative path from project root.

        Returns:
            True if the path is gitignored.
        """
        if self._gitignore_patterns is None:
            self._gitignore_patterns = self._load_gitignore()

        path_str = str(rel_path)
        path_parts = rel_path.parts

        for pattern in self._gitignore_patterns:
            # Handle directory patterns
            if pattern.endswith("/"):
                dir_pattern = pattern[:-1]
                if dir_pattern in path_parts:
                    return True
            # Handle glob patterns
            elif fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(rel_path.name, pattern):
                return True

        return False

    def _load_gitignore(self) -> list[str]:
        """Load patterns from .gitignore file.

        Returns:
            List of gitignore patterns.
        """
        gitignore_path = self.project_root / ".gitignore"
        patterns: list[str] = []

        if not gitignore_path.exists():
            return patterns

        try:
            content = gitignore_path.read_text(encoding="utf-8")
            for raw_line in content.splitlines():
                stripped = raw_line.strip()
                # Skip comments and empty lines
                if not stripped or stripped.startswith("#"):
                    continue
                patterns.append(stripped)
        except OSError as e:
            logger.warning(f"Failed to read .gitignore: {e}")

        return patterns

    def compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: File content.

        Returns:
            Hex-encoded SHA256 hash.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def detect_document_type(self, file_path: Path) -> DocumentType:
        """Detect document type from file extension.

        Args:
            file_path: Path to the file.

        Returns:
            DocumentType for the file.
        """
        ext = file_path.suffix.lower()
        return self._DOC_TYPE_MAP.get(ext, DocumentType.OTHER)

    async def read_file(self, file_path: Path) -> str | None:
        """Read file content asynchronously.

        Args:
            file_path: Path to the file.

        Returns:
            File content as string, or None if reading fails.
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, lambda: file_path.read_text(encoding="utf-8")
            )
            return content
        except UnicodeDecodeError:
            logger.debug(f"Skipping {file_path}: not valid UTF-8")
            return None
        except OSError as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    async def process_file(self, file_path: Path) -> Document | None:
        """Process a file and create a Document.

        Args:
            file_path: Absolute path to the file.

        Returns:
            Document object, or None if processing fails.
        """
        if not self.should_process_file(file_path):
            return None

        content = await self.read_file(file_path)
        if content is None:
            return None

        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            return None

        content_hash = self.compute_hash(content)
        doc_type = self.detect_document_type(file_path)
        language = detect_language(str(file_path))

        return Document(
            path=str(rel_path),
            absolute_path=str(file_path),
            document_type=doc_type,
            content_hash=content_hash,
            file_size=len(content.encode("utf-8")),
            language=language,
            metadata={"encoding": "utf-8"},
        )


class ProjectIndexer:
    """Index project files for RAG.

    Orchestrates the indexing of an entire project:
    - Discovers files to index
    - Tracks indexed file hashes for incremental updates
    - Chunks files and generates embeddings
    - Stores in vector database

    Attributes:
        project_root: Root directory of the project.
        config: RAG configuration.
        embedding_provider: Provider for generating embeddings.
        vector_store: Storage backend for embeddings.
    """

    def __init__(
        self,
        project_root: Path,
        config: RAGConfig,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        """Initialize the project indexer.

        Args:
            project_root: Root directory of the project.
            config: RAG configuration.
            embedding_provider: Provider for generating embeddings.
            vector_store: Storage backend for embeddings.
        """
        self.project_root = project_root
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self._file_processor = FileProcessor(project_root, config)
        self._index_state: IndexState | None = None

    async def index_all(self, force: bool = False) -> IndexStats:
        """Index all project files.

        Args:
            force: If True, reindex all files regardless of hash.

        Returns:
            Statistics about the indexing operation.
        """
        start_time = datetime.now()
        logger.info(f"Starting {'full' if force else 'incremental'} index of {self.project_root}")

        # Load or initialize index state
        state = await self._load_state()

        # Check if embedding model changed
        if state.embedding_model and state.embedding_model != self.embedding_provider.model_name:
            logger.info("Embedding model changed, forcing full reindex")
            force = True
            await self.vector_store.clear()
            state = IndexState(embedding_model=self.embedding_provider.model_name)

        # Discover files to process
        files_to_process = await self._discover_files()
        current_files = {str(f.relative_to(self.project_root)) for f in files_to_process}

        # Find deleted files
        deleted_files = state.get_deleted_files(current_files)
        if deleted_files:
            logger.info(f"Removing {len(deleted_files)} deleted files from index")
            for deleted_path in deleted_files:
                await self.vector_store.delete_by_document(deleted_path)
                state.remove_file(deleted_path)

        # Process files
        total_documents = 0
        total_chunks = 0
        total_tokens = 0
        documents_by_type: dict[str, int] = {}

        for file_path in files_to_process:
            rel_path = str(file_path.relative_to(self.project_root))

            # Check if file needs processing
            content = await self._file_processor.read_file(file_path)
            if content is None:
                continue

            content_hash = self._file_processor.compute_hash(content)

            if not force and not state.is_file_changed(rel_path, content_hash):
                # File unchanged, skip
                continue

            # Process the file
            doc = await self._file_processor.process_file(file_path)
            if doc is None:
                continue

            # Remove old chunks for this document
            await self.vector_store.delete_by_document(doc.id)

            # Chunk the document
            chunks = await self._chunk_document(doc, content)
            if not chunks:
                continue

            # Generate embeddings
            chunks = await self._embed_chunks(chunks)

            # Store in vector database
            await self.vector_store.add(chunks)

            # Update state
            state.update_file(rel_path, content_hash)

            # Update stats
            total_documents += 1
            total_chunks += len(chunks)
            total_tokens += sum(c.token_count for c in chunks)

            doc_type = doc.document_type.value
            documents_by_type[doc_type] = documents_by_type.get(doc_type, 0) + 1

            logger.debug(f"Indexed {rel_path}: {len(chunks)} chunks")

        # Update state
        state.last_full_index = datetime.now() if force else state.last_full_index
        state.embedding_model = self.embedding_provider.model_name
        await self._save_state(state)

        # Get final stats
        store_stats = self.vector_store.get_stats()
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Indexing complete: {total_documents} documents, "
            f"{total_chunks} chunks in {elapsed:.1f}s"
        )

        return IndexStats(
            total_documents=store_stats.get("total_chunks", 0) // 5,  # Approximate
            total_chunks=store_stats.get("total_chunks", 0),
            total_tokens=total_tokens,
            embedding_model=self.embedding_provider.model_name,
            vector_store=self.vector_store.name,
            last_indexed=datetime.now(),
            storage_size_bytes=store_stats.get("storage_size_bytes", 0),
            documents_by_type=documents_by_type,
        )

    async def index_file(self, file_path: Path) -> int:
        """Index a single file.

        Args:
            file_path: Path to the file to index.

        Returns:
            Number of chunks created.
        """
        doc = await self._file_processor.process_file(file_path)
        if doc is None:
            return 0

        content = await self._file_processor.read_file(file_path)
        if content is None:
            return 0

        # Remove old chunks
        await self.vector_store.delete_by_document(doc.id)

        # Chunk and embed
        chunks = await self._chunk_document(doc, content)
        if not chunks:
            return 0

        chunks = await self._embed_chunks(chunks)
        await self.vector_store.add(chunks)

        # Update state
        state = await self._load_state()
        rel_path = str(file_path.relative_to(self.project_root))
        content_hash = self._file_processor.compute_hash(content)
        state.update_file(rel_path, content_hash)
        await self._save_state(state)

        return len(chunks)

    async def remove_file(self, file_path: Path) -> int:
        """Remove a file from the index.

        Args:
            file_path: Path to the file to remove.

        Returns:
            Number of chunks removed.
        """
        try:
            rel_path = str(file_path.relative_to(self.project_root))
        except ValueError:
            return 0

        deleted = await self.vector_store.delete_by_document(rel_path)

        # Update state
        state = await self._load_state()
        state.remove_file(rel_path)
        await self._save_state(state)

        return deleted

    async def _discover_files(self) -> list[Path]:
        """Discover all files to index.

        Returns:
            List of file paths to process.
        """
        files: list[Path] = []

        def _scan() -> list[Path]:
            result: list[Path] = []
            for pattern in self.config.include_patterns:
                # Handle **/*.ext patterns
                if pattern.startswith("**/"):
                    for f in self.project_root.rglob(pattern[3:]):
                        if f.is_file():
                            result.append(f)
                else:
                    for f in self.project_root.glob(pattern):
                        if f.is_file():
                            result.append(f)
            return list(set(result))  # Remove duplicates

        loop = asyncio.get_event_loop()
        all_files = await loop.run_in_executor(None, _scan)

        # Filter files
        for f in all_files:
            if self._file_processor.should_process_file(f):
                files.append(f)

        logger.debug(f"Discovered {len(files)} files to index")
        return files

    async def _chunk_document(
        self, document: Document, content: str
    ) -> list[Chunk]:
        """Chunk a document.

        Args:
            document: Document to chunk.
            content: Document content.

        Returns:
            List of chunks.
        """
        chunker = get_chunker(
            language=document.language,
            file_extension=Path(document.path).suffix,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )

        chunks = chunker.chunk(content, document.path, document.id)
        return chunks

    async def _embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Generate embeddings for chunks.

        Args:
            chunks: Chunks to embed.

        Returns:
            Chunks with embeddings set.
        """
        if not chunks:
            return chunks

        # Extract text content
        texts = [c.content for c in chunks]

        # Generate embeddings in batch
        embeddings = await self.embedding_provider.embed_batch(texts)

        # Set embeddings on chunks
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding

        return chunks

    async def _load_state(self) -> IndexState:
        """Load index state from disk.

        Returns:
            Current index state.
        """
        if self._index_state is not None:
            return self._index_state

        state_path = self.config.get_state_file_path(self.project_root)

        if not state_path.exists():
            self._index_state = IndexState()
            return self._index_state

        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, lambda: state_path.read_text(encoding="utf-8")
            )
            data = json.loads(content)
            self._index_state = IndexState.from_dict(data)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load index state: {e}")
            self._index_state = IndexState()

        return self._index_state

    async def _save_state(self, state: IndexState) -> None:
        """Save index state to disk.

        Args:
            state: State to save.
        """
        state_path = self.config.get_state_file_path(self.project_root)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        data = state.to_dict()
        content = json.dumps(data, indent=2)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: state_path.write_text(content, encoding="utf-8")
        )

        self._index_state = state

    def get_stats(self) -> dict[str, Any]:
        """Get indexer statistics.

        Returns:
            Dictionary with indexer stats.
        """
        store_stats = self.vector_store.get_stats()
        return {
            "project_root": str(self.project_root),
            "embedding_model": self.embedding_provider.model_name,
            "vector_store": self.vector_store.name,
            **store_stats,
        }
