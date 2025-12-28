# FEAT-001: Per-Project RAG Support - BDD Scenarios

**Phase:** per-project-rag
**Version Target:** 1.9.0

---

## Feature: Project Indexing

### Scenario 1: Index a Python project

```gherkin
Given a project directory with Python files
And RAG is enabled in configuration
When I run "/rag index"
Then all Python files matching include_patterns are indexed
And the index is persisted to ".forge/index/"
And I see a summary of indexed documents and chunks
```

### Scenario 2: Index with exclude patterns

```gherkin
Given a project with "**/*.py" in include_patterns
And "**/tests/**" in exclude_patterns
When I run "/rag index"
Then files in the tests directory are not indexed
And files outside tests directory are indexed
```

### Scenario 3: Respect .gitignore patterns

```gherkin
Given a project with a .gitignore file
And ".gitignore" contains "*.log" and "build/"
And respect_gitignore is true in RAG config
When I run "/rag index"
Then .log files are not indexed
And files in build/ directory are not indexed
```

### Scenario 4: Skip large files

```gherkin
Given a project with max_file_size_kb set to 500
And a file "large_file.py" that is 600KB
When I run "/rag index"
Then "large_file.py" is skipped
And a warning is logged about the skipped file
```

### Scenario 5: Incremental indexing

```gherkin
Given a project that was previously indexed
And one file "changed.py" has been modified
And one file "new.py" has been added
When I run "/rag index"
Then only "changed.py" and "new.py" are re-indexed
And unchanged files are not re-processed
And the operation completes faster than full index
```

### Scenario 6: Force full re-index

```gherkin
Given a project that was previously indexed
When I run "/rag index --force"
Then all files are re-indexed regardless of changes
And the index is rebuilt from scratch
```

### Scenario 7: Index empty project

```gherkin
Given an empty project directory
When I run "/rag index"
Then I see a message "No files to index"
And no errors are raised
```

### Scenario 8: Handle syntax errors in Python files

```gherkin
Given a project with a Python file containing syntax errors
When I run "/rag index"
Then the file is indexed using generic chunking
And no errors are raised
And the file content is still searchable
```

---

## Feature: Semantic Search

### Scenario 9: Basic semantic search

```gherkin
Given a project with indexed Python files
And a file contains a function "calculate_total_price"
When I run "/rag search 'calculate price'"
Then results include the file with "calculate_total_price"
And results show relevance score
And results show file path and line numbers
```

### Scenario 10: Search with no results

```gherkin
Given a project with indexed files
When I run "/rag search 'xyznonexistent123'"
Then I see "No results found"
And no errors are raised
```

### Scenario 11: Search with result limit

```gherkin
Given a project with many indexed files
When I run "/rag search 'function' --limit 3"
Then at most 3 results are returned
And results are ordered by relevance
```

### Scenario 12: Search filtered by document type

```gherkin
Given a project with Python and Markdown files indexed
When I run "/rag search 'authentication' --type code"
Then only code files are in results
And documentation files are excluded
```

### Scenario 13: Search with minimum score threshold

```gherkin
Given a project with indexed files
And min_score is set to 0.7 in configuration
When I run "/rag search 'specific term'"
Then only results with score >= 0.7 are returned
```

### Scenario 14: Search respects token budget

```gherkin
Given a project with indexed files
And context_token_budget is set to 2000
When I run "/rag search 'common term'"
Then total tokens in results do not exceed 2000
And results are truncated if necessary
```

---

## Feature: RAG Commands

### Scenario 15: Show index status

```gherkin
Given a project with an existing index
When I run "/rag status"
Then I see total documents indexed
And I see total chunks created
And I see total tokens indexed
And I see embedding model used
And I see last indexed timestamp
And I see storage size
```

### Scenario 16: Clear index

```gherkin
Given a project with an existing index
When I run "/rag clear"
Then the index is deleted
And ".forge/index/" directory is cleaned
And I see confirmation message
```

### Scenario 17: Show RAG configuration

```gherkin
Given RAG is configured
When I run "/rag config"
Then I see current RAG configuration
And I see enabled status
And I see embedding provider
And I see include/exclude patterns
```

### Scenario 18: RAG not configured

```gherkin
Given a project without RAG configuration
And RAG dependencies are not installed
When I run "/rag index"
Then I see an error about missing dependencies
And I see installation instructions
```

---

## Feature: Chunking Strategies

### Scenario 19: Python AST-aware chunking

```gherkin
Given a Python file with multiple functions and classes
When the file is indexed
Then each function is extracted as a separate chunk
And each class is extracted as a separate chunk
And chunk metadata includes function/class name
And chunk metadata includes line numbers
```

### Scenario 20: Markdown section chunking

```gherkin
Given a Markdown file with multiple headers
When the file is indexed
Then each section (header + content) is a separate chunk
And code blocks are preserved in chunks
And chunk metadata includes section heading
```

### Scenario 21: Generic chunking fallback

```gherkin
Given a text file with no special structure
When the file is indexed
Then the file is split by character count
And chunks respect chunk_size configuration
And chunks have overlap as configured
```

### Scenario 22: Large function handling

```gherkin
Given a Python file with a function larger than chunk_size
When the file is indexed
Then the function is split into multiple chunks
And chunks maintain context with overlap
```

---

## Feature: Configuration

### Scenario 23: Per-project configuration

```gherkin
Given a project with ".forge/settings.json"
And the file contains RAG configuration
When I start a session in that project
Then RAG uses project-specific settings
And project settings override user defaults
```

### Scenario 24: Environment variable override

```gherkin
Given FORGE_RAG_ENABLED=false environment variable
When I start a session
Then RAG is disabled regardless of file config
```

### Scenario 25: Auto-index on project open

```gherkin
Given auto_index is true in configuration
And the project has not been indexed
When I start a session in the project
Then the project is automatically indexed
And I see indexing progress
```

### Scenario 26: Disable auto-index

```gherkin
Given auto_index is false in configuration
When I start a session in a new project
Then no automatic indexing occurs
And I can manually run "/rag index"
```

---

## Feature: Context Augmentation

### Scenario 27: Automatic context augmentation

```gherkin
Given a project with indexed files
And context augmentation is enabled
When I submit a query about "error handling"
Then relevant code snippets are added to context
And the snippets are formatted as a system message
And the LLM receives the augmented context
```

### Scenario 28: Context budget respected

```gherkin
Given context_token_budget is 4000 tokens
When context augmentation adds RAG results
Then the added content does not exceed 4000 tokens
And results are ranked by relevance
```

### Scenario 29: No results for augmentation

```gherkin
Given a project with indexed files
When I submit a query with no relevant matches
Then no RAG context is added
And the LLM receives the original context only
```

---

## Feature: File Watching

### Scenario 30: Auto-reindex on file change

```gherkin
Given a project with an index
And watch_files is true in configuration
When I modify a Python file
Then the file is automatically re-indexed
And the index is updated
```

### Scenario 31: Auto-index new files

```gherkin
Given a project with an index
And watch_files is true
When I create a new Python file
Then the file is automatically indexed
And the index includes the new file
```

### Scenario 32: Handle deleted files

```gherkin
Given a project with an index
And watch_files is true
When I delete an indexed file
Then the file is removed from the index
And search no longer returns results from that file
```

### Scenario 33: Ignore non-matching files

```gherkin
Given include_patterns contains "**/*.py"
And watch_files is true
When I create a new ".txt" file
Then the file is not indexed
And no indexing operation is triggered
```

---

## Feature: Embedding Providers

### Scenario 34: Local embedding provider

```gherkin
Given embedding_provider is "local"
And embedding_model is "all-MiniLM-L6-v2"
When I index a project
Then sentence-transformers is used for embeddings
And no external API calls are made
```

### Scenario 35: OpenAI embedding provider

```gherkin
Given embedding_provider is "openai"
And OPENAI_API_KEY is configured
When I index a project
Then OpenAI embeddings API is used
And embeddings are higher quality
```

### Scenario 36: Lazy loading of embedding model

```gherkin
Given RAG is enabled in configuration
When I start a session without indexing
Then the embedding model is not loaded
And memory is conserved
When I run "/rag index"
Then the embedding model is loaded on first use
```

---

## Feature: Vector Store

### Scenario 37: ChromaDB persistence

```gherkin
Given vector_store is "chroma"
When I index a project
Then the index is persisted to ".forge/index/"
And the index survives session restarts
```

### Scenario 38: FAISS fallback

```gherkin
Given vector_store is "faiss"
When I index a project
Then FAISS is used for vector storage
And the index is persisted to disk
```

### Scenario 39: Corrupted index recovery

```gherkin
Given a corrupted index in ".forge/index/"
When I start a session
Then I see a warning about corrupted index
And I am prompted to rebuild with "/rag index --force"
```

---

## Feature: Error Handling

### Scenario 40: Missing RAG dependencies

```gherkin
Given RAG optional dependencies are not installed
When I run "/rag index"
Then I see an error message
And I see "pip install code-forge[rag]" instruction
```

### Scenario 41: Permission denied on file

```gherkin
Given a file without read permissions
When I run "/rag index"
Then the file is skipped
And a warning is logged
And other files are indexed successfully
```

### Scenario 42: Encoding error in file

```gherkin
Given a file with invalid UTF-8 encoding
When I run "/rag index"
Then encoding is detected and handled
And the file is indexed if possible
Or skipped with a warning if not
```

### Scenario 43: Network error with OpenAI provider

```gherkin
Given embedding_provider is "openai"
And the network is unavailable
When I run "/rag index"
Then I see a network error message
And I am suggested to use local provider
```

---

## Feature: Performance

### Scenario 44: Batch embedding for efficiency

```gherkin
Given a project with 100 files to index
When I run "/rag index"
Then embeddings are generated in batches
And the operation is faster than individual calls
```

### Scenario 45: Progress reporting

```gherkin
Given a large project with many files
When I run "/rag index"
Then I see progress updates
And I see estimated completion time
```

### Scenario 46: Memory-efficient indexing

```gherkin
Given a project with 5000 files
When I run "/rag index"
Then memory usage stays below 2GB
And indexing completes successfully
```

---

## Edge Cases

### Scenario 47: Unicode file paths

```gherkin
Given a project with files having Unicode names
When I run "/rag index"
Then files are indexed correctly
And search results show correct file paths
```

### Scenario 48: Very long file paths

```gherkin
Given a project with deeply nested directories
When I run "/rag index"
Then files are indexed correctly
And file paths are handled properly
```

### Scenario 49: Empty files

```gherkin
Given a project with empty Python files
When I run "/rag index"
Then empty files are skipped
And no errors are raised
```

### Scenario 50: Binary files in include patterns

```gherkin
Given include_patterns accidentally matches binary files
When I run "/rag index"
Then binary files are detected and skipped
And a warning is logged
```
