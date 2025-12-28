# FEAT-001: Per-Project RAG Support - Test Strategy

**Phase:** per-project-rag
**Version Target:** 1.9.0

---

## Test Structure

```
tests/
├── unit/
│   └── rag/
│       ├── __init__.py
│       ├── test_models.py           # Data model tests
│       ├── test_config.py           # Configuration tests
│       ├── test_embeddings.py       # Embedding provider tests
│       ├── test_chunking.py         # Chunking strategy tests
│       ├── test_vectorstore.py      # Vector store tests
│       ├── test_indexer.py          # Indexer tests
│       ├── test_retriever.py        # Retriever tests
│       ├── test_manager.py          # Manager tests
│       ├── test_integration.py      # Context integration tests
│       └── test_commands.py         # Command tests
├── integration/
│   └── rag/
│       ├── __init__.py
│       ├── test_full_workflow.py    # End-to-end indexing/search
│       ├── test_incremental.py      # Incremental update tests
│       ├── test_context_augment.py  # Context augmentation tests
│       └── test_commands.py         # Command execution tests
└── fixtures/
    └── rag/
        ├── sample_project/          # Sample project for testing
        │   ├── src/
        │   │   ├── main.py
        │   │   ├── utils.py
        │   │   └── models.py
        │   ├── docs/
        │   │   ├── README.md
        │   │   └── API.md
        │   └── .gitignore
        └── embeddings/              # Mock embeddings for testing
            └── mock_vectors.json
```

---

## Unit Tests

### test_models.py

```python
"""Tests for RAG data models."""

class TestDocument:
    def test_document_creation(self):
        """Document can be created with required fields."""

    def test_document_content_hash(self):
        """Document tracks content hash correctly."""

    def test_document_serialization(self):
        """Document serializes to/from dict."""

class TestChunk:
    def test_chunk_creation(self):
        """Chunk can be created with required fields."""

    def test_chunk_with_embedding(self):
        """Chunk stores embedding vector."""

    def test_chunk_metadata(self):
        """Chunk preserves metadata."""

class TestSearchResult:
    def test_search_result_ordering(self):
        """SearchResults can be sorted by score."""

    def test_snippet_generation(self):
        """Snippet is truncated appropriately."""

class TestSearchFilter:
    def test_filter_defaults(self):
        """SearchFilter has sensible defaults."""

    def test_filter_validation(self):
        """SearchFilter validates min_score range."""

class TestIndexStats:
    def test_stats_aggregation(self):
        """IndexStats correctly aggregates counts."""
```

### test_config.py

```python
"""Tests for RAG configuration."""

class TestRAGConfig:
    def test_default_values(self):
        """RAGConfig has correct defaults."""

    def test_pattern_validation(self):
        """Include/exclude patterns are validated."""

    def test_chunk_size_validation(self):
        """Chunk size must be positive."""

    def test_integration_with_code_forge_config(self):
        """RAGConfig integrates with CodeForgeConfig."""

    def test_environment_variable_override(self):
        """FORGE_RAG_* variables override config."""
```

### test_embeddings.py

```python
"""Tests for embedding providers."""

class TestSentenceTransformerProvider:
    def test_lazy_loading(self):
        """Model is not loaded until first use."""

    def test_embed_single(self):
        """Single text embedding works."""

    def test_embed_batch(self):
        """Batch embedding is efficient."""

    def test_dimension_property(self):
        """Dimension returns correct value."""

    def test_model_not_found(self):
        """Graceful error for invalid model name."""

class TestOpenAIProvider:
    def test_api_key_required(self):
        """Error when API key not configured."""

    @pytest.mark.skipif(not HAS_OPENAI_KEY)
    def test_embed_with_api(self):
        """Embedding works with real API."""

class TestEmbeddingProviderFactory:
    def test_create_local_provider(self):
        """Factory creates local provider."""

    def test_create_openai_provider(self):
        """Factory creates OpenAI provider."""
```

### test_chunking.py

```python
"""Tests for chunking strategies."""

class TestPythonCodeChunker:
    def test_extract_functions(self):
        """Functions are extracted as chunks."""

    def test_extract_classes(self):
        """Classes are extracted as chunks."""

    def test_nested_functions(self):
        """Nested functions are handled."""

    def test_async_functions(self):
        """Async functions are extracted."""

    def test_syntax_error_fallback(self):
        """Falls back to generic on syntax error."""

    def test_large_function_splitting(self):
        """Large functions are split with overlap."""

class TestMarkdownChunker:
    def test_split_on_headers(self):
        """Markdown splits on headers."""

    def test_preserve_code_blocks(self):
        """Code blocks are kept intact."""

    def test_nested_headers(self):
        """Nested headers create hierarchy."""

class TestGenericChunker:
    def test_character_based_split(self):
        """Splits by character count."""

    def test_overlap(self):
        """Chunks have configured overlap."""

    def test_respect_boundaries(self):
        """Tries to split on word boundaries."""

class TestChunkerSelection:
    def test_python_file_uses_python_chunker(self):
        """*.py files use PythonCodeChunker."""

    def test_markdown_uses_markdown_chunker(self):
        """*.md files use MarkdownChunker."""

    def test_unknown_uses_generic(self):
        """Unknown extensions use GenericChunker."""
```

### test_vectorstore.py

```python
"""Tests for vector store implementations."""

class TestChromaStore:
    def test_initialization(self):
        """ChromaStore initializes correctly."""

    def test_add_chunks(self):
        """Chunks can be added to store."""

    def test_search(self):
        """Search returns similar chunks."""

    def test_search_with_filter(self):
        """Search respects filters."""

    def test_delete(self):
        """Chunks can be deleted."""

    def test_clear(self):
        """Store can be cleared."""

    def test_persistence(self):
        """Data persists across restarts."""

    def test_get_stats(self):
        """Stats are accurate."""

class TestFAISSStore:
    def test_initialization(self):
        """FAISSStore initializes correctly."""

    def test_add_and_search(self):
        """Basic add/search works."""

    def test_persistence(self):
        """Index persists to disk."""
```

### test_indexer.py

```python
"""Tests for project indexer."""

class TestFileProcessor:
    def test_detect_file_type(self):
        """File type detection works."""

    def test_detect_language(self):
        """Language detection works."""

    def test_calculate_hash(self):
        """Content hash is consistent."""

    def test_skip_large_files(self):
        """Large files are skipped."""

    def test_encoding_detection(self):
        """Non-UTF8 files are handled."""

class TestIndexState:
    def test_track_file(self):
        """Files are tracked in state."""

    def test_detect_changes(self):
        """Changed files are detected."""

    def test_detect_new_files(self):
        """New files are detected."""

    def test_detect_deleted_files(self):
        """Deleted files are detected."""

    def test_persistence(self):
        """State persists to disk."""

class TestProjectIndexer:
    def test_index_all(self):
        """Full project indexing works."""

    def test_incremental_index(self):
        """Incremental indexing works."""

    def test_respect_include_patterns(self):
        """Include patterns filter files."""

    def test_respect_exclude_patterns(self):
        """Exclude patterns filter files."""

    def test_respect_gitignore(self):
        """Gitignore patterns are respected."""

    def test_force_reindex(self):
        """Force flag rebuilds everything."""

    def test_returns_stats(self):
        """Returns accurate IndexStats."""
```

### test_retriever.py

```python
"""Tests for RAG retriever."""

class TestRAGRetriever:
    def test_basic_search(self):
        """Basic search returns results."""

    def test_apply_filters(self):
        """Filters are applied correctly."""

    def test_min_score_filtering(self):
        """Low-score results are filtered."""

    def test_max_results_limiting(self):
        """Results are limited."""

    def test_token_budget_limiting(self):
        """Token budget is respected."""

    def test_result_ranking(self):
        """Results are ranked by score."""

class TestResultRanker:
    def test_rerank_by_score(self):
        """Results are reranked."""

    def test_diversity_boosting(self):
        """Diverse results are boosted."""
```

### test_manager.py

```python
"""Tests for RAG manager."""

class TestRAGManager:
    def test_initialization(self):
        """Manager initializes correctly."""

    def test_lazy_component_loading(self):
        """Components are lazily loaded."""

    def test_index_project(self):
        """Project indexing works."""

    def test_search(self):
        """Search works through manager."""

    def test_augment_context(self):
        """Context augmentation works."""

    def test_start_watching(self):
        """File watching starts."""

    def test_stop_watching(self):
        """File watching stops."""

    def test_cleanup(self):
        """Resources are cleaned up."""
```

### test_commands.py

```python
"""Tests for RAG commands."""

class TestRAGIndexCommand:
    async def test_index_command(self):
        """Index command works."""

    async def test_index_force_flag(self):
        """Force flag is passed through."""

    async def test_index_no_rag_manager(self):
        """Error when RAG not configured."""

class TestRAGSearchCommand:
    async def test_search_command(self):
        """Search command works."""

    async def test_search_with_limit(self):
        """Limit flag works."""

    async def test_search_no_query(self):
        """Error when no query provided."""

class TestRAGStatusCommand:
    async def test_status_command(self):
        """Status command works."""

    async def test_status_no_index(self):
        """Shows 'not indexed' status."""

class TestRAGClearCommand:
    async def test_clear_command(self):
        """Clear command works."""

class TestRAGCommand:
    def test_subcommand_routing(self):
        """Subcommands are routed correctly."""

    def test_help_text(self):
        """Help text is accurate."""
```

---

## Integration Tests

### test_full_workflow.py

```python
"""End-to-end RAG workflow tests."""

class TestFullWorkflow:
    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create sample project structure."""

    async def test_index_and_search(self, sample_project):
        """Full index → search workflow."""

    async def test_find_function_by_description(self, sample_project):
        """Search finds function by semantic description."""

    async def test_find_documentation(self, sample_project):
        """Search finds relevant documentation."""

    async def test_cross_file_search(self, sample_project):
        """Search works across multiple files."""
```

### test_incremental.py

```python
"""Incremental indexing tests."""

class TestIncrementalIndexing:
    async def test_changed_file_reindexed(self):
        """Changed files are re-indexed."""

    async def test_new_file_indexed(self):
        """New files are indexed."""

    async def test_deleted_file_removed(self):
        """Deleted files are removed from index."""

    async def test_unchanged_files_skipped(self):
        """Unchanged files are not re-processed."""

    async def test_performance_improvement(self):
        """Incremental is faster than full."""
```

### test_context_augment.py

```python
"""Context augmentation tests."""

class TestContextAugmentation:
    async def test_augment_adds_context(self):
        """Relevant context is added."""

    async def test_respects_token_budget(self):
        """Token budget is not exceeded."""

    async def test_formats_correctly(self):
        """Context is formatted properly."""

    async def test_no_results_no_augmentation(self):
        """No augmentation when no results."""
```

---

## Test Fixtures

### Sample Project

```
fixtures/rag/sample_project/
├── src/
│   ├── main.py           # Entry point with main()
│   ├── utils.py          # Utility functions
│   └── models.py         # Data models
├── docs/
│   ├── README.md         # Project documentation
│   └── API.md            # API documentation
├── tests/
│   └── test_main.py      # Test file (should be excluded)
└── .gitignore            # Git ignore patterns
```

### Mock Embeddings

For fast unit tests without loading real models:

```python
class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        # Deterministic mock embedding based on text hash
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        return [int(c, 16) / 15.0 for c in h[:self._dimension]]
```

---

## Test Coverage Targets

| Module | Target Coverage |
|--------|-----------------|
| `rag/models.py` | 100% |
| `rag/config.py` | 100% |
| `rag/embeddings.py` | 90% |
| `rag/chunking.py` | 95% |
| `rag/vectorstore.py` | 90% |
| `rag/indexer.py` | 90% |
| `rag/retriever.py` | 90% |
| `rag/manager.py` | 85% |
| `rag/integration.py` | 90% |
| `rag/commands.py` | 95% |
| **Overall** | **>90%** |

---

## Test Commands

```bash
# Run all RAG tests
pytest tests/unit/rag tests/integration/rag -v

# Run with coverage
pytest tests/unit/rag tests/integration/rag --cov=src/code_forge/rag --cov-report=term-missing

# Run only unit tests (fast, no real models)
pytest tests/unit/rag -v

# Run integration tests (slower, uses real components)
pytest tests/integration/rag -v

# Run specific test file
pytest tests/unit/rag/test_chunking.py -v
```

---

## CI Integration

Add to GitHub Actions workflow:

```yaml
rag-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -e ".[rag,dev]"
    - name: Run RAG tests
      run: |
        pytest tests/unit/rag tests/integration/rag \
          --cov=src/code_forge/rag \
          --cov-report=xml \
          -v
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## Performance Benchmarks

```python
"""Performance benchmarks for RAG."""

class TestPerformance:
    @pytest.mark.benchmark
    def test_indexing_1000_files(self, benchmark, large_project):
        """Indexing 1000 files < 60 seconds."""
        result = benchmark(index_project, large_project)
        assert result.total_time < 60

    @pytest.mark.benchmark
    def test_search_latency(self, benchmark, indexed_project):
        """Search latency < 500ms."""
        result = benchmark(search, "authentication")
        assert result.mean < 0.5

    @pytest.mark.benchmark
    def test_embedding_batch(self, benchmark):
        """Batch embedding is efficient."""
        texts = ["text"] * 100
        result = benchmark(embed_batch, texts)
        assert result.mean < 5  # 5 seconds for 100 texts
```
