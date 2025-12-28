# FEAT-001: Per-Project RAG Support - Implementation Plan

**Phase:** per-project-rag
**Version Target:** 1.9.0
**Created:** 2025-12-28
**Status:** Planning

---

## Overview

Implement a Retrieval-Augmented Generation (RAG) system for per-project semantic search over code, documentation, and project-specific knowledge. This enables Code-Forge to understand project context beyond the LLM's context window limits by indexing project files into a local vector database with semantic search capabilities.

### Current Limitation

Code-Forge can only include content that fits within the model's context window. Large codebases require users to manually specify which files to include, and there's no persistent knowledge across sessions about project-specific patterns, conventions, or documentation.

### Goal

Create a RAG system that:
- Indexes code files, documentation, and comments into a local vector store
- Supports semantic search with relevance scoring
- Persists indexes across sessions in `.forge/index/`
- Supports incremental updates on file changes
- Integrates seamlessly with ContextManager for context augmentation
- Provides `/rag` command for management and search
- Configures per-project via `.forge/settings.json`

---

## Requirements Analysis

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Index code files with AST-aware chunking | Must Have |
| FR-2 | Index markdown/documentation with section-based chunking | Must Have |
| FR-3 | Persist index to `.forge/index/` directory | Must Have |
| FR-4 | Support incremental updates via file hash tracking | Must Have |
| FR-5 | Semantic similarity search with relevance scoring | Must Have |
| FR-6 | Filter by file type, path patterns, tags | Must Have |
| FR-7 | Token-aware result limiting | Must Have |
| FR-8 | `/rag` command with subcommands | Must Have |
| FR-9 | Per-project configuration in `.forge/settings.json` | Must Have |
| FR-10 | Respect `.gitignore` patterns | Must Have |
| FR-11 | Auto-index on project open | Should Have |
| FR-12 | File watching for auto-reindex | Should Have |
| FR-13 | Context augmentation (automatic RAG for queries) | Should Have |
| FR-14 | OpenAI embeddings option | Should Have |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Indexing large projects (<10k files) | < 5 minutes |
| NFR-2 | Search latency | < 500ms |
| NFR-3 | Memory usage during indexing | < 2GB |
| NFR-4 | Index storage size | < 10% of source size |
| NFR-5 | Test coverage | > 90% |

---

## Architecture

### Component Overview

```
src/code_forge/rag/
├── __init__.py              # Package exports
├── models.py                # Data models (Pydantic)
│   ├── Document             # Indexed document representation
│   ├── Chunk                # Document chunk with embeddings
│   ├── SearchResult         # Search result with relevance
│   ├── IndexStats           # Index statistics
│   └── RAGConfig            # Configuration model
├── embeddings.py            # Embedding generation
│   ├── EmbeddingProvider    # Abstract base (Protocol)
│   ├── SentenceTransformerProvider  # Local embeddings
│   └── OpenAIProvider       # API-based embeddings
├── chunking.py              # Text chunking strategies
│   ├── ChunkingStrategy     # Abstract base
│   ├── CodeChunker          # AST-aware code chunking
│   ├── MarkdownChunker      # Section-based markdown chunking
│   └── GenericChunker       # Fallback character-based chunking
├── vectorstore.py           # Vector storage abstraction
│   ├── VectorStore          # Abstract base (Protocol)
│   ├── ChromaStore          # ChromaDB implementation
│   └── FAISSStore           # FAISS implementation (fallback)
├── indexer.py               # Document indexing
│   ├── ProjectIndexer       # Main indexing orchestrator
│   ├── FileProcessor        # File reading and preprocessing
│   └── IndexState           # Track indexed files (hashes)
├── retriever.py             # Semantic search
│   ├── RAGRetriever         # Main retrieval interface
│   ├── SearchFilter         # Filter configuration
│   └── ResultRanker         # Re-ranking logic
├── manager.py               # Central RAG coordinator
│   └── RAGManager           # Lifecycle and coordination
├── integration.py           # ContextManager integration
│   └── RAGContextAugmenter  # Add RAG results to context
└── commands.py              # CLI commands
    └── RAGCommand           # /rag command with subcommands
```

### Data Flow

```
1. Indexing Flow:
   File → FileProcessor → Chunker → Embeddings → VectorStore
         ↓
   IndexState (tracks hashes for incremental updates)

2. Retrieval Flow:
   Query → Embeddings → VectorStore.search() → ResultRanker → SearchResult[]
                                                      ↓
                                              RAGContextAugmenter
                                                      ↓
                                              ContextManager

3. Context Augmentation Flow:
   User Query → RAGRetriever.search() → Format Results → Prepend to Context
```

---

## Data Models

### Core Models

```python
# src/code_forge/rag/models.py

class DocumentType(str, Enum):
    """Type of indexed document."""
    CODE = "code"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    OTHER = "other"

class ChunkType(str, Enum):
    """Type of chunk within a document."""
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    GENERIC = "generic"

class Document(BaseModel):
    """Represents an indexed document."""
    id: str  # UUID
    path: str  # Relative path from project root
    absolute_path: str
    document_type: DocumentType
    content_hash: str  # SHA256 for change detection
    indexed_at: datetime
    file_size: int
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class Chunk(BaseModel):
    """A chunk of a document with embedding."""
    id: str  # UUID
    document_id: str  # Reference to parent Document
    chunk_type: ChunkType
    content: str
    start_line: int
    end_line: int
    token_count: int
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None  # Function/class name or section heading

class SearchResult(BaseModel):
    """Result from semantic search."""
    chunk: Chunk
    document: Document
    score: float  # Similarity score (0-1)
    rank: int
    snippet: str  # Highlighted/trimmed content

class IndexStats(BaseModel):
    """Statistics about the index."""
    total_documents: int
    total_chunks: int
    total_tokens: int
    embedding_model: str
    vector_store: str
    last_indexed: datetime | None
    storage_size_bytes: int
    documents_by_type: dict[str, int]

class SearchFilter(BaseModel):
    """Filters for search queries."""
    file_patterns: list[str] = Field(default_factory=list)
    document_types: list[DocumentType] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    min_score: float = 0.5
    max_results: int = 10
    max_tokens: int | None = None
```

### Configuration Model

```python
# src/code_forge/rag/config.py

class EmbeddingProviderType(str, Enum):
    LOCAL = "local"  # sentence-transformers
    OPENAI = "openai"

class VectorStoreType(str, Enum):
    CHROMA = "chroma"
    FAISS = "faiss"

class RAGConfig(BaseModel):
    """RAG configuration for .forge/settings.json."""
    enabled: bool = True
    auto_index: bool = True
    watch_files: bool = True

    # Embedding settings
    embedding_provider: EmbeddingProviderType = EmbeddingProviderType.LOCAL
    embedding_model: str = "all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    # Vector store settings
    vector_store: VectorStoreType = VectorStoreType.CHROMA
    index_directory: str = ".forge/index"

    # Indexing settings
    include_patterns: list[str] = Field(default_factory=lambda: [
        "**/*.py", "**/*.js", "**/*.ts", "**/*.tsx",
        "**/*.md", "**/*.rst", "**/*.txt",
        "**/*.yaml", "**/*.yml", "**/*.json", "**/*.toml"
    ])
    exclude_patterns: list[str] = Field(default_factory=lambda: [
        "**/node_modules/**", "**/.git/**", "**/__pycache__/**",
        "**/.venv/**", "**/venv/**", "**/.env/**",
        "**/dist/**", "**/build/**", "**/*.min.js"
    ])
    max_file_size_kb: int = 500
    respect_gitignore: bool = True

    # Chunking settings
    chunk_size: int = 1000  # Target tokens per chunk
    chunk_overlap: int = 100

    # Retrieval settings
    default_max_results: int = 5
    default_min_score: float = 0.5
    context_token_budget: int = 4000
```

---

## Key Components

### 1. Embedding Provider (Protocol Pattern)

```python
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerProvider:
    """Local embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model: Any = None  # Lazy load

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, model.encode, texts)
        return [e.tolist() for e in embeddings]
```

### 2. Vector Store (Protocol Pattern)

```python
class VectorStore(Protocol):
    """Protocol for vector store backends."""

    async def add(self, chunks: list[Chunk]) -> None: ...

    async def search(
        self,
        embedding: list[float],
        k: int = 10,
        filter: SearchFilter | None = None,
    ) -> list[tuple[str, float]]: ...

    async def delete(self, chunk_ids: list[str]) -> None: ...

    async def clear(self) -> None: ...

    def get_stats(self) -> dict[str, Any]: ...


class ChromaStore:
    """ChromaDB vector store implementation."""

    def __init__(self, persist_directory: Path):
        self._persist_dir = persist_directory
        self._client: Any = None
        self._collection: Any = None

    def _ensure_initialized(self) -> None:
        if self._client is None:
            import chromadb
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir)
            )
            self._collection = self._client.get_or_create_collection(
                name="code_forge_index",
                metadata={"hnsw:space": "cosine"}
            )
```

### 3. Code Chunker (AST-aware)

```python
class PythonCodeChunker:
    """AST-aware chunking for Python code."""

    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, content: str, file_path: str) -> list[Chunk]:
        chunks = []
        try:
            tree = ast.parse(content)
            chunks.extend(self._extract_functions(tree, content, file_path))
            chunks.extend(self._extract_classes(tree, content, file_path))
            if not chunks:
                chunks = self._generic_chunk(content, file_path)
        except SyntaxError:
            chunks = self._generic_chunk(content, file_path)
        return chunks
```

### 4. RAG Manager (Coordinator)

```python
class RAGManager:
    """Central coordinator for RAG operations."""

    def __init__(
        self,
        project_root: Path,
        config: RAGConfig,
        context_manager: ContextManager | None = None,
    ):
        self.project_root = project_root
        self.config = config
        self.context_manager = context_manager
        self._embedding_provider: EmbeddingProvider | None = None
        self._vector_store: VectorStore | None = None
        self._indexer: ProjectIndexer | None = None
        self._retriever: RAGRetriever | None = None

    async def index_project(self, force: bool = False) -> IndexStats:
        """Index all project files."""
        indexer = self._get_indexer()
        return await indexer.index_all(force=force)

    async def search(
        self,
        query: str,
        filter: SearchFilter | None = None,
    ) -> list[SearchResult]:
        """Search the index."""
        retriever = self._get_retriever()
        return await retriever.search(query, filter)

    async def augment_context(self, query: str) -> str:
        """Search and format results for context augmentation."""
        results = await self.search(
            query,
            SearchFilter(
                max_results=self.config.default_max_results,
                max_tokens=self.config.context_token_budget,
            ),
        )
        if not results:
            return ""
        # Format results for context
        lines = ["### Relevant Project Context", ""]
        for r in results:
            lines.append(f"**{r.document.path}** (lines {r.chunk.start_line}-{r.chunk.end_line}):")
            lines.append(f"```\n{r.snippet}\n```")
            lines.append("")
        return "\n".join(lines)
```

### 5. RAG Commands

```python
class RAGCommand(SubcommandHandler):
    """RAG management."""
    name = "rag"
    aliases = ["r"]
    description = "RAG (Retrieval-Augmented Generation) management"
    usage = "/rag [subcommand]"
    category = CommandCategory.CONTEXT
    subcommands = {
        "index": RAGIndexCommand(),
        "search": RAGSearchCommand(),
        "status": RAGStatusCommand(),
        "clear": RAGClearCommand(),
        "config": RAGConfigCommand(),
    }
```

---

## Integration Points

### 1. Configuration Integration

Extend `CodeForgeConfig` in `config/models.py`:

```python
class CodeForgeConfig(BaseModel):
    # ... existing fields ...
    rag: RAGConfig = Field(default_factory=RAGConfig)
```

### 2. CommandContext Integration

Extend `CommandContext` in `commands/executor.py`:

```python
@dataclass
class CommandContext:
    # ... existing fields ...
    rag_manager: RAGManager | None = None
```

### 3. ContextManager Integration

```python
class RAGContextAugmenter:
    """Augments context with RAG results."""

    def __init__(
        self,
        rag_manager: RAGManager,
        context_manager: ContextManager,
    ):
        self.rag_manager = rag_manager
        self.context_manager = context_manager

    async def augment_for_query(self, query: str) -> int:
        """Add relevant context for a query. Returns tokens added."""
        augmented_text = await self.rag_manager.augment_context(query)
        if not augmented_text:
            return 0

        token_count = self.context_manager.counter.count(augmented_text)
        self.context_manager.add_message({
            "role": "system",
            "content": f"[RAG Context]\n{augmented_text}",
        })
        return token_count
```

---

## Implementation Phases

### Phase 1: Core Models & Embedding (Foundation)

**Duration:** 3-4 days

**Files:**
- `rag/__init__.py` - Package setup
- `rag/models.py` - All data models
- `rag/config.py` - RAGConfig
- `rag/embeddings.py` - EmbeddingProvider, SentenceTransformerProvider

**Tasks:**
1. Define all Pydantic models (Document, Chunk, SearchResult, etc.)
2. Create RAGConfig model
3. Implement SentenceTransformerProvider with lazy loading
4. Add optional OpenAIProvider
5. Unit tests for all models and providers

**Deliverables:**
- [ ] All Pydantic models defined and tested
- [ ] RAGConfig integrated with CodeForgeConfig
- [ ] SentenceTransformerProvider working
- [ ] 90%+ test coverage for phase

---

### Phase 2: Vector Store & Chunking

**Duration:** 3-4 days

**Files:**
- `rag/vectorstore.py` - VectorStore protocol, ChromaStore, FAISSStore
- `rag/chunking.py` - ChunkingStrategy, PythonCodeChunker, MarkdownChunker, GenericChunker

**Tasks:**
1. Implement ChromaStore with persistence
2. Implement FAISS fallback store
3. Create AST-aware Python chunker
4. Create section-based Markdown chunker
5. Create generic character-based chunker
6. Unit tests for stores and chunkers

**Deliverables:**
- [ ] ChromaStore fully functional
- [ ] FAISS fallback working
- [ ] Python/Markdown/Generic chunkers implemented
- [ ] 90%+ test coverage for phase

---

### Phase 3: Indexer & Retriever

**Duration:** 4-5 days

**Files:**
- `rag/indexer.py` - ProjectIndexer, FileProcessor, IndexState
- `rag/retriever.py` - RAGRetriever, ResultRanker

**Tasks:**
1. Implement FileProcessor with file type detection
2. Implement IndexState for tracking file hashes
3. Implement ProjectIndexer with incremental updates
4. Add gitignore pattern support
5. Implement RAGRetriever with filtering
6. Add result ranking logic
7. Integration tests

**Deliverables:**
- [ ] Full project indexing working
- [ ] Incremental updates functional
- [ ] Semantic search returning ranked results
- [ ] gitignore patterns respected
- [ ] 90%+ test coverage for phase

---

### Phase 4: Manager & Commands

**Duration:** 3-4 days

**Files:**
- `rag/manager.py` - RAGManager
- `rag/commands.py` - RAGCommand and subcommands
- `rag/integration.py` - RAGContextAugmenter

**Tasks:**
1. Implement RAGManager as central coordinator
2. Add file watching for auto-reindex
3. Implement all /rag subcommands (index, search, status, clear, config)
4. Integrate with CommandContext
5. Add RAGContextAugmenter for context augmentation
6. Integration tests

**Deliverables:**
- [ ] RAGManager coordinating all components
- [ ] All /rag commands working
- [ ] File watching functional
- [ ] 90%+ test coverage for phase

---

### Phase 5: Integration & Polish

**Duration:** 2-3 days

**Files:**
- Update `config/models.py` - Add rag field
- Update `commands/executor.py` - Add rag_manager to CommandContext
- Update REPL initialization

**Tasks:**
1. Integrate RAGManager with REPL startup
2. Auto-index on project open (if configured)
3. Add context augmentation to message flow
4. End-to-end integration tests
5. Performance testing and optimization
6. Documentation

**Deliverables:**
- [ ] RAG fully integrated with REPL
- [ ] Auto-index working
- [ ] All integration tests passing
- [ ] Performance targets met
- [ ] Documentation complete

---

## Risks & Mitigations

### Risk 1: Dependency Size

**Problem:** sentence-transformers and ChromaDB add significant dependencies

**Mitigation:**
- Make RAG an optional feature (opt-in)
- Lazy-load all RAG dependencies
- Add to `[project.optional-dependencies]` as `rag` extra
- Provide clear installation instructions

### Risk 2: Performance Impact

**Problem:** Indexing large codebases may be slow

**Mitigation:**
- Incremental indexing (only changed files)
- Background indexing with progress reporting
- Configurable file size limits
- Batch embedding operations
- Progress bar for long operations

### Risk 3: Memory Usage

**Problem:** Vector stores can consume significant memory

**Mitigation:**
- Use disk-backed ChromaDB (default)
- Configurable chunk size limits
- Clear unused indexes
- Memory monitoring

### Risk 4: Embedding Quality

**Problem:** Local embeddings may not match project terminology

**Mitigation:**
- Option to use OpenAI embeddings (higher quality)
- Configurable embedding model
- Future: fine-tuned embeddings per-project

### Risk 5: Context Budget Overflow

**Problem:** RAG results may overflow context budget

**Mitigation:**
- Token-aware result limiting
- Integrate with ContextBudget
- Configurable max tokens for RAG context
- Truncation strategies

---

## Configuration Example

```json
{
  "rag": {
    "enabled": true,
    "auto_index": true,
    "watch_files": true,
    "embedding_provider": "local",
    "embedding_model": "all-MiniLM-L6-v2",
    "vector_store": "chroma",
    "include_patterns": [
      "**/*.py",
      "**/*.md",
      "docs/**/*.rst"
    ],
    "exclude_patterns": [
      "**/tests/**",
      "**/.venv/**"
    ],
    "chunk_size": 1000,
    "default_max_results": 5,
    "context_token_budget": 4000
  }
}
```

---

## Critical Files for Modification

| File | Changes |
|------|---------|
| `src/code_forge/config/models.py` | Add `rag: RAGConfig` field to CodeForgeConfig |
| `src/code_forge/context/manager.py` | Integration point for context augmentation |
| `src/code_forge/commands/executor.py` | Add `rag_manager` to CommandContext |
| `src/code_forge/commands/builtin/__init__.py` | Register RAG commands |
| `pyproject.toml` | Add optional `rag` dependencies |

---

## Dependencies

### New Dependencies (pyproject.toml)

```toml
[project.optional-dependencies]
rag = [
    "chromadb>=0.4,<1.0",
    "sentence-transformers>=2.0,<3.0",
]
```

### Existing Dependencies Used

- pydantic (models)
- watchdog (file watching)
- tiktoken (token counting)
- aiofiles (async file reading)

---

## Future Enhancements

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| Multiple indexes | Support multiple named indexes per project | Medium |
| Cross-project search | Search across multiple project indexes | Low |
| Custom embedding models | Support user-provided embedding models | Low |
| Hybrid search | Combine semantic + keyword search | Medium |
| LLM re-ranking | Use LLM to re-rank search results | Low |
| Code navigation | Jump to definition from search results | Medium |
| Index compression | Reduce storage size for large indexes | Low |

---

## References

- Existing patterns: `src/code_forge/context/`, `src/code_forge/sessions/`
- Config system: `src/code_forge/config/`
- Command patterns: `src/code_forge/commands/`
- Storage patterns: `SessionStorage` in `sessions/storage.py`
- ChromaDB: https://docs.trychroma.com/
- sentence-transformers: https://www.sbert.net/
