# FEAT-001: Per-Project RAG Support - Completion Criteria

**Phase:** per-project-rag
**Version Target:** 1.9.0

---

## Phase 1: Core Models & Embedding

### 1.1 Data Models

- [ ] `DocumentType` enum defined with CODE, DOCUMENTATION, CONFIG, OTHER
- [ ] `ChunkType` enum defined with FUNCTION, CLASS, MODULE, SECTION, PARAGRAPH, GENERIC
- [ ] `Document` model with all required fields (id, path, content_hash, indexed_at, etc.)
- [ ] `Chunk` model with all required fields (id, document_id, content, embedding, etc.)
- [ ] `SearchResult` model with chunk, document, score, rank, snippet
- [ ] `IndexStats` model with statistics fields
- [ ] `SearchFilter` model with filtering options
- [ ] All models have proper Pydantic validators
- [ ] All models are exportable from `rag/__init__.py`

### 1.2 Configuration Model

- [ ] `EmbeddingProviderType` enum with LOCAL, OPENAI
- [ ] `VectorStoreType` enum with CHROMA, FAISS
- [ ] `RAGConfig` model with all configuration fields
- [ ] Default values for all optional fields
- [ ] `RAGConfig` integrated into `CodeForgeConfig`
- [ ] Configuration loadable from `.forge/settings.json`
- [ ] Environment variable overrides work (FORGE_RAG_*)

### 1.3 Embedding Provider

- [ ] `EmbeddingProvider` protocol defined
- [ ] `SentenceTransformerProvider` implemented
- [ ] Lazy loading of sentence-transformers model
- [ ] `embed()` method works asynchronously
- [ ] `embed_batch()` method works for multiple texts
- [ ] `model_name` property returns correct name
- [ ] `dimension` property returns correct dimension
- [ ] Optional `OpenAIProvider` implemented
- [ ] Graceful error handling when model loading fails

### 1.4 Phase 1 Tests

- [ ] Unit tests for all data models
- [ ] Unit tests for RAGConfig validation
- [ ] Unit tests for SentenceTransformerProvider
- [ ] Integration test for embedding generation
- [ ] >90% code coverage for phase 1 files

---

## Phase 2: Vector Store & Chunking

### 2.1 Vector Store

- [ ] `VectorStore` protocol defined with add, search, delete, clear methods
- [ ] `ChromaStore` implementation complete
- [ ] ChromaDB persistence to `.forge/index/` directory
- [ ] `add()` stores chunks with embeddings and metadata
- [ ] `search()` returns (chunk_id, score) pairs
- [ ] `search()` supports SearchFilter for filtering
- [ ] `delete()` removes chunks by ID
- [ ] `clear()` removes all data
- [ ] `get_stats()` returns storage statistics
- [ ] `FAISSStore` fallback implementation complete
- [ ] Thread-safe operations for concurrent access

### 2.2 Chunking Strategies

- [ ] `ChunkingStrategy` protocol defined
- [ ] `PythonCodeChunker` implemented with AST parsing
- [ ] Python chunker extracts functions as chunks
- [ ] Python chunker extracts classes as chunks
- [ ] Python chunker handles syntax errors gracefully
- [ ] `MarkdownChunker` implemented with section detection
- [ ] Markdown chunker splits on headers
- [ ] Markdown chunker preserves code blocks
- [ ] `GenericChunker` implemented for fallback
- [ ] Generic chunker respects chunk_size and overlap settings
- [ ] Chunker selection based on file extension
- [ ] Token counting for each chunk

### 2.3 Phase 2 Tests

- [ ] Unit tests for ChromaStore operations
- [ ] Unit tests for FAISSStore operations
- [ ] Unit tests for PythonCodeChunker
- [ ] Unit tests for MarkdownChunker
- [ ] Unit tests for GenericChunker
- [ ] Integration test for store + embedding workflow
- [ ] >90% code coverage for phase 2 files

---

## Phase 3: Indexer & Retriever

### 3.1 File Processing

- [ ] `FileProcessor` class implemented
- [ ] File type detection (code, docs, config, other)
- [ ] Language detection for code files
- [ ] Content hash calculation (SHA256)
- [ ] File size checking against max_file_size_kb
- [ ] Encoding detection and handling
- [ ] Async file reading with aiofiles

### 3.2 Index State Management

- [ ] `IndexState` class implemented
- [ ] Track file paths and content hashes
- [ ] Persist state to `.forge/index/state.json`
- [ ] Detect changed files (hash mismatch)
- [ ] Detect new files (not in state)
- [ ] Detect deleted files (in state but not on disk)
- [ ] Thread-safe state updates

### 3.3 Project Indexer

- [ ] `ProjectIndexer` class implemented
- [ ] `index_all()` indexes all matching files
- [ ] `index_file()` indexes single file
- [ ] `index_incremental()` only indexes changed files
- [ ] Respect include_patterns configuration
- [ ] Respect exclude_patterns configuration
- [ ] Respect .gitignore patterns (when enabled)
- [ ] Progress reporting during indexing
- [ ] Batch embedding for efficiency
- [ ] Force re-index option
- [ ] Return IndexStats on completion

### 3.4 RAG Retriever

- [ ] `RAGRetriever` class implemented
- [ ] `search()` accepts query string
- [ ] `search()` applies SearchFilter
- [ ] Embed query using embedding provider
- [ ] Search vector store for similar chunks
- [ ] Load full Document for each matching Chunk
- [ ] Apply min_score filtering
- [ ] Apply max_results limiting
- [ ] Apply max_tokens budget limiting
- [ ] `ResultRanker` for re-ranking results
- [ ] Format snippet for each result

### 3.5 Phase 3 Tests

- [ ] Unit tests for FileProcessor
- [ ] Unit tests for IndexState
- [ ] Unit tests for ProjectIndexer
- [ ] Unit tests for RAGRetriever
- [ ] Integration test for full index + search workflow
- [ ] Test incremental indexing
- [ ] Test gitignore pattern handling
- [ ] >90% code coverage for phase 3 files

---

## Phase 4: Manager & Commands

### 4.1 RAG Manager

- [ ] `RAGManager` class implemented
- [ ] Lazy initialization of all components
- [ ] `index_project()` orchestrates indexing
- [ ] `search()` orchestrates retrieval
- [ ] `augment_context()` formats results for LLM
- [ ] `start_watching()` starts file watcher
- [ ] `stop_watching()` stops file watcher
- [ ] File watcher triggers re-indexing on changes
- [ ] Proper cleanup on shutdown

### 4.2 CLI Commands

- [ ] `RAGCommand` (SubcommandHandler) implemented
- [ ] `/rag index` command indexes project
- [ ] `/rag index --force` forces full re-index
- [ ] `/rag search <query>` searches index
- [ ] `/rag search --limit N` limits results
- [ ] `/rag search --type code|docs` filters by type
- [ ] `/rag status` shows index statistics
- [ ] `/rag clear` clears the index
- [ ] `/rag config` shows/sets RAG configuration
- [ ] Commands registered in CommandRegistry
- [ ] Help text for all commands

### 4.3 Context Integration

- [ ] `RAGContextAugmenter` class implemented
- [ ] `augment_for_query()` adds RAG results to context
- [ ] Respects context_token_budget
- [ ] Formats results as system message
- [ ] Returns token count of added content

### 4.4 Phase 4 Tests

- [ ] Unit tests for RAGManager
- [ ] Unit tests for all RAG commands
- [ ] Unit tests for RAGContextAugmenter
- [ ] Integration test for command execution
- [ ] Integration test for context augmentation
- [ ] >90% code coverage for phase 4 files

---

## Phase 5: Integration & Polish

### 5.1 System Integration

- [ ] `rag_manager` added to `CommandContext`
- [ ] RAGManager initialized on REPL startup (when enabled)
- [ ] Auto-index on project open (when auto_index=true)
- [ ] Proper shutdown and cleanup
- [ ] RAG commands visible in `/help`

### 5.2 Configuration Integration

- [ ] `RAGConfig` field added to `CodeForgeConfig`
- [ ] RAG config loadable from all config sources
- [ ] Environment variable mapping for RAG settings
- [ ] Config validation at startup

### 5.3 Performance

- [ ] Indexing 1000 Python files < 60 seconds
- [ ] Indexing 5000 files < 5 minutes
- [ ] Search latency < 500ms
- [ ] Memory usage during indexing < 2GB
- [ ] Index storage size < 10% of source size

### 5.4 Error Handling

- [ ] Graceful handling when RAG dependencies not installed
- [ ] Clear error messages for missing dependencies
- [ ] Recovery from corrupted index
- [ ] Handling of permission errors on files
- [ ] Handling of encoding errors in files

### 5.5 Phase 5 Tests

- [ ] End-to-end integration tests
- [ ] Performance benchmarks pass
- [ ] Error scenario tests
- [ ] REPL integration tests
- [ ] All existing tests still pass (no regressions)

---

## Final Verification

### Code Quality

- [ ] All files pass `ruff check`
- [ ] All files pass `mypy` type checking
- [ ] No TODO comments left in code
- [ ] All public APIs have docstrings
- [ ] Code follows existing patterns

### Test Coverage

- [ ] >90% coverage for all RAG modules
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No regressions in existing tests
- [ ] pytest runs cleanly

### Documentation

- [ ] README updated with RAG feature
- [ ] Configuration documented
- [ ] Command help texts complete
- [ ] API documentation complete

### Dependencies

- [ ] `chromadb` added to optional dependencies
- [ ] `sentence-transformers` added to optional dependencies
- [ ] Installation instructions documented
- [ ] Dependencies version-pinned appropriately

---

## Phase Complete When

All checkboxes above are checked, and:

1. `pytest tests/` passes with no failures
2. `mypy src/code_forge/rag/` reports no errors
3. `ruff check src/code_forge/rag/` reports no issues
4. `/rag index` successfully indexes the Code-Forge project itself
5. `/rag search "context manager"` returns relevant results
6. Performance benchmarks pass

---

## Sign-Off

| Phase | Completed | Date | Notes |
|-------|-----------|------|-------|
| Phase 1 | [ ] | | |
| Phase 2 | [ ] | | |
| Phase 3 | [ ] | | |
| Phase 4 | [ ] | | |
| Phase 5 | [ ] | | |
| Final | [ ] | | |
