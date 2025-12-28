"""RAG (Retrieval-Augmented Generation) package.

This package provides semantic search over project files using
vector embeddings. It enables Code-Forge to understand project
context beyond the LLM's context window limits.

Features:
- Index code files with AST-aware chunking
- Index documentation with section-based chunking
- Semantic search with relevance scoring
- Per-project configuration and storage
- Integration with ContextManager for context augmentation

Example:
    from code_forge.rag import RAGConfig, RAGManager

    # Create RAG manager for a project
    config = RAGConfig(enabled=True)
    manager = RAGManager(project_root=Path.cwd(), config=config)

    # Index the project
    stats = await manager.index_project()
    print(f"Indexed {stats.total_documents} documents")

    # Search for relevant content
    results = await manager.search("authentication handler")
    for result in results:
        print(f"{result.document.path}: {result.snippet}")

Installation:
    RAG support requires optional dependencies:
    pip install 'code-forge[rag]'

Configuration:
    Add to .forge/settings.json:
    {
        "rag": {
            "enabled": true,
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "include_patterns": ["**/*.py", "**/*.md"],
            "chunk_size": 1000
        }
    }
"""

from .chunking import (
    ChunkingStrategy,
    GenericChunker,
    JavaScriptChunker,
    MarkdownChunker,
    PythonCodeChunker,
    detect_language,
    get_chunker,
)
from .config import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDE_PATTERNS,
    EmbeddingProviderType,
    RAGConfig,
    VectorStoreType,
)
from .embeddings import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformerProvider,
    get_embedding_provider,
)
from .indexer import (
    FileProcessor,
    ProjectIndexer,
)
from .integration import (
    RAGContextAugmenter,
    RAGMessageProcessor,
    create_augmenter,
)
from .manager import (
    RAGManager,
    RAGStatus,
)
from .models import (
    Chunk,
    ChunkType,
    Document,
    DocumentType,
    IndexState,
    IndexStats,
    SearchFilter,
    SearchResult,
)
from .retriever import (
    RAGRetriever,
    RankerConfig,
    ResultRanker,
    RetrievalContext,
)
from .vectorstore import (
    ChromaStore,
    FAISSStore,
    MockVectorStore,
    VectorStore,
    get_vector_store,
)

__all__ = [
    # Chunking
    "ChunkingStrategy",
    "GenericChunker",
    "JavaScriptChunker",
    "MarkdownChunker",
    "PythonCodeChunker",
    "detect_language",
    "get_chunker",
    # Config
    "DEFAULT_EXCLUDE_PATTERNS",
    "DEFAULT_INCLUDE_PATTERNS",
    "EmbeddingProviderType",
    "RAGConfig",
    "VectorStoreType",
    # Embeddings
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "SentenceTransformerProvider",
    "get_embedding_provider",
    # Models
    "Chunk",
    "ChunkType",
    "Document",
    "DocumentType",
    "IndexState",
    "IndexStats",
    "SearchFilter",
    "SearchResult",
    # Indexer
    "FileProcessor",
    "ProjectIndexer",
    # Retriever
    "RAGRetriever",
    "RankerConfig",
    "ResultRanker",
    "RetrievalContext",
    # Vector Stores
    "ChromaStore",
    "FAISSStore",
    "MockVectorStore",
    "VectorStore",
    "get_vector_store",
    # Manager
    "RAGManager",
    "RAGStatus",
    # Integration
    "RAGContextAugmenter",
    "RAGMessageProcessor",
    "create_augmenter",
]
