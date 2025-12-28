# Code-Forge: Current Work

**Last Updated:** 2025-12-27

---

## Active Tasks

_No active tasks._

---

## Backlog

### Critical Priority (P0)

#### CICD-001: Missing CI/CD Pipeline
**Status:** Pending
**Priority:** Critical
**Phase Directory:** `.ai/phase/cicd-setup/`
**Files:** `.github/workflows/` (missing)
**Issue:** `tests/README.md:254-259` references `.github/workflows/test.yml` but no `.github/` directory exists
**Impact:** No automated testing, no PR checks, no deployment automation

---

### High Priority (P1)

#### ARCH-004: Configuration System Fragmentation
**Status:** Deferred
**Phase Directory:** `.ai/phase/config-consolidation/` (to be created)
**Files:** `config/`, `mcp/config.py`, `hooks/config.py`, `permissions/config.py`, `web/config.py`
**Issue:** 6+ modules use different config patterns (Pydantic vs dataclass vs custom)
**Impact:** Inconsistent API, hard to compose/test configurations
**Note:** Large refactoring task requiring careful migration:
- config/models.py uses Pydantic (canonical)
- mcp/config.py uses dataclasses (MCPServerConfig duplicates Pydantic version)
- hooks/config.py and permissions/config.py use class methods
- web/config.py uses dataclasses (currently unused)
Migration plan: Create common base, migrate one module at a time with tests.

#### CODE-002: Dead Code - Unused WebConfig
**Status:** Pending
**Priority:** High
**Phase Directory:** `.ai/phase/code-cleanup/`
**Files:** `src/code_forge/web/config.py`
**Issue:** `WebConfig` class appears to be completely unused - never instantiated
**Impact:** Dead code increases maintenance burden and confusion

#### CODE-003: Version Synchronization Burden
**Status:** Pending
**Priority:** High
**Phase Directory:** `.ai/phase/code-cleanup/`
**Files:** `pyproject.toml`, `src/code_forge/__init__.py`, `.ai/START.md`
**Issue:** Version must be manually updated in 4 places
**Solution:** Use `importlib.metadata.version()` pattern to derive version from pyproject.toml
**Impact:** Risk of version mismatch, manual overhead

#### SEC-022: Race Condition in SSRF Check
**Status:** Documented
**Priority:** High
**Phase Directory:** `.ai/phase/security-hardening/` (to be created)
**File:** `src/code_forge/web/fetch/fetcher.py:38-58`
**Issue:** DNS validation at fetch time doesn't prevent TOCTOU (DNS rebinding)
**Note:** Added detailed SECURITY NOTE in docstring explaining the vulnerability and mitigation complexity. Full fix requires custom aiohttp connector with IP pinning.

---

### Medium Priority (P2)

#### CODE-004: Mixed Threading/Async Locking
**Status:** Pending
**Priority:** Medium
**Phase Directory:** `.ai/phase/code-cleanup/`
**Files:** `src/code_forge/llm/client.py`, various singletons
**Issue:** Uses `threading.Lock()` in async code (e.g., `OpenRouterClient._usage_lock`)
**Impact:** Potential blocking in async context, though current usage may be safe
**Note:** Audit all lock usage and determine if asyncio.Lock() is more appropriate

#### CODE-005: Magic Numbers Scattered
**Status:** Pending
**Priority:** Medium
**Phase Directory:** `.ai/phase/code-cleanup/`
**Files:** Multiple files
**Issue:** Hardcoded values like `max_retries: int = 3`, `timeout: float = 120.0` scattered across classes
**Solution:** Centralize in constants module or derive from config

#### CLI-002: No Output Format Options
**Status:** Deferred
**File:** `src/code_forge/cli/repl.py`
**Issue:** No `--json`, `--no-color`, `-q` quiet mode options
**Note:** Feature request requiring significant CLI restructuring.

#### SESS-002: Memory Leak in Token Counter Caching
**Status:** Deferred
**File:** `src/code_forge/context/tokens.py:257-353`
**Issue:** Cache default `max_cache_size=1000` could cause memory issues
**Note:** Feature request for cache statistics monitoring. Current size is reasonable for most use cases.

#### SESS-007: No Automatic Session Cleanup
**Status:** Pending
**Priority:** Medium
**Phase Directory:** `.ai/phase/code-cleanup/`
**File:** `src/code_forge/sessions/storage.py:329-369`
**Issue:** `cleanup_old_sessions()` and `cleanup_old_backups()` exist but never called
**Solution:** Add scheduled cleanup or CLI command

---

### Low Priority (P3)

#### TOOL-009: Edit Tool Doesn't Preserve File Encoding
**Status:** Deferred
**File:** `src/code_forge/tools/file/edit.py:119-120, 152`
**Issue:** Always uses UTF-8, losing original file encoding (latin-1, utf-16)
**Note:** Requires adding chardet as a dependency.

#### TOOL-010: Exception Details Leaked in Error Messages
**Status:** Deferred
**Files:** Multiple tool files
**Issue:** Raw exception strings may leak system information (paths, library versions)
**Note:** Requires systematic audit of all tools.

#### LLM-014: Thread Overhead Per Call
**Status:** Deferred
**File:** `src/code_forge/langchain/llm.py:246-260`
**Issue:** Creates new thread for every streaming operation
**Note:** Requires design work for module-level thread pool with proper lifecycle management.

#### MCP-016: No Circular Dependency Detection in Skills
**Status:** Deferred
**File:** `src/code_forge/skills/registry.py:255-278`
**Issue:** Skills can have circular dependencies via prompt references
**Impact:** Potential infinite loops

#### MCP-019: Inefficient Plugin Unregister
**Status:** Deferred
**File:** `src/code_forge/plugins/registry.py:153-168`
**Issue:** Dictionary comprehensions iterate entire collection for each type
**Reason:** Current O(n) per collection is acceptable for typical plugin counts.

#### MCP-020: Linear Search in Skills Registry
**Status:** Deferred
**File:** `src/code_forge/skills/registry.py:136-150`
**Issue:** `search()` iterates all skills
**Reason:** Linear search is acceptable for typical skill counts.

---

## Feature Requests

### FEAT-001: Per-Project RAG Support
**Status:** Proposed
**Priority:** High
**Description:** Add Retrieval-Augmented Generation (RAG) support on a per-project basis

**Benefits:**
- Index project-specific documentation, code comments, and patterns
- Semantic search over large codebases beyond context window limits
- Persistent knowledge across sessions
- Custom embeddings for domain-specific terminology
- Better understanding of project architecture and conventions

**Implementation Considerations:**
- Local vector database (ChromaDB, Qdrant, or FAISS)
- Configurable embedding models (local or API-based)
- Automatic indexing on project open/file changes
- Integration with context management system
- Project-specific `.forge/index/` directory for vector storage
- Support for multiple index types (code, docs, comments)

**Potential Components:**
- `src/code_forge/rag/indexer.py` - Code and document indexing
- `src/code_forge/rag/embeddings.py` - Embedding generation
- `src/code_forge/rag/retriever.py` - Semantic search
- `src/code_forge/rag/config.py` - Per-project RAG configuration

---

## Summary

### Remaining Work

| Priority | Pending | Deferred | Complete | Total |
|----------|---------|----------|----------|-------|
| **P0 Critical** | 1 | 0 | 2 | 3 |
| **P1 High** | 3 | 1 | 0 | 4 |
| **P2 Medium** | 3 | 2 | 0 | 5 |
| **P3 Low** | 0 | 6 | 0 | 6 |
| **Features** | 1 | 0 | 3 | 4 |
| **TOTAL** | **8** | **9** | **5** | **22** |

### Priority Order for Implementation

1. **CICD-001** - Add CI/CD pipeline (quality gate)
2. **CODE-002** - Remove dead WebConfig code
3. **CODE-003** - Fix version synchronization
4. **SEC-022** - Address SSRF vulnerability
5. **ARCH-004** - Consolidate config patterns
6. **CODE-004** - Audit threading/async locking
7. **CODE-005** - Centralize magic numbers
8. **SESS-007** - Implement session cleanup

---

## Completed Milestones

| Version | Date | Summary |
|---------|------|---------|
| 1.8.2 | 2025-12-27 | Code fix (CODE-001): Added UTILITY to ToolCategory enum |
| 1.8.1 | 2025-12-27 | Documentation fix (DOC-001): Fixed package references forge → code_forge |
| 1.8.0 | 2025-12-27 | Test coverage (FEAT-004): 4,898 tests, 85%+ coverage |
| 1.7.0 | 2025-12-22 | Workflow system (FEAT-003): Multi-step agent pipelines |
| 1.6.0 | 2025-12-21 | Specialized agent system (FEAT-002): 16 new agent types |
| 1.5.0 | 2025-12-21 | Technical debt cleanup (SESS-008, PERM-015/016/017) |
| 1.4.0 | 2025-12-21 | Test quality improvements (TEST-001, TEST-002, TEST-003) |
| 1.3.0 | 2025-12-17 | Streaming error handling fix |
| 1.2.0 | 2025-12-17 | Setup wizard, security fixes |
| 1.1.0 | 2025-12-09 | All 22 phases complete, production ready |
| 1.0.0 | 2025-12-09 | Initial release |
