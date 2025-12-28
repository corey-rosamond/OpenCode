# FEAT-001: Per-Project RAG Support - Dependencies

**Phase:** per-project-rag
**Version Target:** 1.9.0

---

## New External Dependencies

### Required (Optional Install)

These dependencies are added to `[project.optional-dependencies]` in `pyproject.toml`:

```toml
[project.optional-dependencies]
rag = [
    "chromadb>=0.4,<1.0",
    "sentence-transformers>=2.0,<3.0",
]
```

| Package | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `chromadb` | >=0.4,<1.0 | Vector database for storing embeddings | Pure Python, local-first |
| `sentence-transformers` | >=2.0,<3.0 | Local embedding generation | Includes torch dependency |

### Optional

| Package | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `openai` | >=1.0 | OpenAI embeddings API | Already in base dependencies |
| `faiss-cpu` | >=1.7 | Alternative vector store | For performance-critical use |

---

## Existing Dependencies Used

These are already in Code-Forge's dependencies:

| Package | Purpose in RAG |
|---------|----------------|
| `pydantic` | Data models (Document, Chunk, RAGConfig, etc.) |
| `aiofiles` | Async file reading during indexing |
| `watchdog` | File system watching for auto-reindex |
| `tiktoken` | Token counting for chunks and results |
| `pathspec` | .gitignore pattern matching |

---

## Internal Dependencies

### Modules RAG Depends On

| Module | Dependency |
|--------|------------|
| `code_forge.config` | RAGConfig integrated into CodeForgeConfig |
| `code_forge.context` | ContextManager for augmentation, TokenCounter for counting |
| `code_forge.commands` | Command base classes, CommandContext, registry |
| `code_forge.sessions` | Session awareness for retrieval |

### Modules That Will Depend on RAG

| Module | Dependency |
|--------|------------|
| `code_forge.cli.main` | Initialize RAGManager on startup |
| `code_forge.commands.executor` | Add rag_manager to CommandContext |
| `code_forge.config.models` | Add RAGConfig to CodeForgeConfig |

---

## Dependency Graph

```
RAG Module Dependencies:

rag/models.py
  └── pydantic

rag/config.py
  └── pydantic
  └── config/models.py (for integration)

rag/embeddings.py
  └── sentence-transformers (lazy load)
  └── openai (optional, lazy load)

rag/chunking.py
  └── ast (stdlib)
  └── tiktoken (token counting)

rag/vectorstore.py
  └── chromadb (lazy load)
  └── faiss-cpu (optional, lazy load)

rag/indexer.py
  └── rag/embeddings.py
  └── rag/chunking.py
  └── rag/vectorstore.py
  └── aiofiles
  └── pathspec (gitignore)

rag/retriever.py
  └── rag/embeddings.py
  └── rag/vectorstore.py
  └── rag/models.py

rag/manager.py
  └── rag/indexer.py
  └── rag/retriever.py
  └── rag/config.py
  └── watchdog

rag/integration.py
  └── rag/manager.py
  └── context/manager.py

rag/commands.py
  └── rag/manager.py
  └── commands/base.py
```

---

## Installation Requirements

### Full RAG Support

```bash
pip install code-forge[rag]
```

### Minimal RAG (ChromaDB only, no sentence-transformers)

For use with OpenAI embeddings only:

```bash
pip install code-forge
pip install chromadb>=0.4
```

Then configure:
```json
{
  "rag": {
    "embedding_provider": "openai"
  }
}
```

---

## Platform Considerations

### Linux/macOS

- Full support for all dependencies
- sentence-transformers works out of the box

### Windows

- ChromaDB works on Windows
- sentence-transformers may require Visual C++ build tools for some models
- Alternative: Use OpenAI embeddings to avoid local model dependencies

### ARM (Apple Silicon, Raspberry Pi)

- sentence-transformers has ARM support
- ChromaDB works on ARM
- FAISS may have limited ARM support

---

## Size Impact

| Package | Approximate Size |
|---------|------------------|
| `chromadb` | ~50 MB |
| `sentence-transformers` | ~100 MB (+ model download) |
| Model `all-MiniLM-L6-v2` | ~90 MB (downloaded on first use) |
| Total (with model) | ~240 MB |

---

## Lazy Loading Strategy

To minimize startup impact:

1. **Import on first use**: Don't import chromadb/sentence-transformers at module level
2. **Model loading deferred**: Load embedding model only when first embedding is needed
3. **Vector store lazy init**: Initialize ChromaDB only when indexing/searching

Example pattern:
```python
class SentenceTransformerProvider:
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None  # Lazy

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model
```

---

## Compatibility Matrix

| Code-Forge Version | ChromaDB | sentence-transformers | Python |
|--------------------|----------|----------------------|--------|
| 1.9.0 | 0.4.x - 0.5.x | 2.x | 3.10+ |

---

## Pre-Implementation Checklist

- [ ] Verify chromadb 0.4+ works with Python 3.10, 3.11, 3.12
- [ ] Verify sentence-transformers 2.x works on all platforms
- [ ] Test lazy loading pattern doesn't affect startup time
- [ ] Confirm model download location is configurable
- [ ] Test offline mode (pre-downloaded models)
