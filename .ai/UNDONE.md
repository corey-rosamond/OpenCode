# Code-Forge: Current Work

**Last Updated:** 2025-12-28

---

## Active Tasks

### FEAT-001: Per-Project RAG Support
**Status:** In Progress (Phase 1/5 Complete)
**Priority:** High
**Version Target:** 1.9.0
**Phase Directory:** `.ai/phase/per-project-rag/`

**Progress:**
- [x] Phase 1: Core Models & Embedding (Complete)
  - Created `src/code_forge/rag/` module
  - Data models: Document, Chunk, SearchResult, SearchFilter, IndexStats, IndexState
  - RAGConfig integrated into CodeForgeConfig
  - Embedding providers: SentenceTransformer (local), OpenAI, Mock
  - 72 unit tests passing
- [ ] Phase 2: Vector Store & Chunking
- [ ] Phase 3: Indexer & Retriever
- [ ] Phase 4: Manager & Commands
- [ ] Phase 5: Integration & Polish

**Files Created (Phase 1):**
- `src/code_forge/rag/__init__.py`
- `src/code_forge/rag/models.py`
- `src/code_forge/rag/config.py`
- `src/code_forge/rag/embeddings.py`
- `tests/unit/rag/test_models.py`
- `tests/unit/rag/test_config.py`
- `tests/unit/rag/test_embeddings.py`

---

## Backlog

### Critical Priority (P0)

_All critical issues resolved._

---

### High Priority (P1)

#### ~~ARCH-004: Configuration System Fragmentation~~
**Status:** ✅ Complete (v1.8.14)
**Files:** `config/models.py`, `mcp/config.py`, `hooks/registry.py`, `permissions/models.py`
**Resolution:** Migrated all config models to Pydantic BaseModel:
- MCP config models (MCPServerConfig, MCPSettings, MCPConfig) now use Pydantic
- Hook model now uses Pydantic with field validators
- PermissionRule now uses Pydantic
- Eliminated duplicate dataclass MCPServerConfig in mcp/config.py
- Loaders remain for file I/O; models use model_validate() and model_dump()

#### SEC-022: Race Condition in SSRF Check
**Status:** Documented
**Priority:** High
**Phase Directory:** `.ai/phase/security-hardening/` (to be created)
**File:** `src/code_forge/web/fetch/fetcher.py:38-58`
**Issue:** DNS validation at fetch time doesn't prevent TOCTOU (DNS rebinding)
**Note:** Added detailed SECURITY NOTE in docstring explaining the vulnerability and mitigation complexity. Full fix requires custom aiohttp connector with IP pinning.

---

### Medium Priority (P2)

#### ~~CLI-002: No Output Format Options~~
**Status:** ✅ Complete (v1.8.13)
**File:** `src/code_forge/cli/main.py`, `src/code_forge/cli/repl.py`, `src/code_forge/config/models.py`
**Resolution:** Added `--json`, `--no-color`, `-q`/`--quiet` CLI flags with corresponding `color`, `quiet`, `json_output` config options

#### ~~SESS-002: Memory Leak in Token Counter Caching~~
**Status:** ✅ Complete (v1.8.12)
**File:** `src/code_forge/context/tokens.py`, `src/code_forge/config/models.py`
**Resolution:** Added `token_cache_size` config option and `/session cache` command for monitoring and clearing cache

---

### Low Priority (P3)

#### ~~TOOL-009: Edit Tool Doesn't Preserve File Encoding~~
**Status:** ✅ Complete (v1.8.11)
**File:** `src/code_forge/tools/file/edit.py`
**Resolution:** Added chardet dependency and detect_file_encoding() function to detect and preserve file encoding during edit operations

#### ~~TOOL-010: Exception Details Leaked in Error Messages~~
**Status:** ✅ Complete (v1.8.10)
**Files:** Multiple tool files
**Resolution:** Sanitized exception messages in base.py, file/utils.py, bash.py, grep.py, glob.py, write.py, kill_shell.py to prevent leaking system information (paths, library versions)

#### LLM-014: Thread Overhead Per Call
**Status:** Deferred
**File:** `src/code_forge/langchain/llm.py:246-260`
**Issue:** Creates new thread for every streaming operation
**Note:** Requires design work for module-level thread pool with proper lifecycle management.

#### ~~MCP-016: No Circular Dependency Detection in Skills~~
**Status:** ✅ Complete (v1.8.9)
**File:** `src/code_forge/skills/registry.py`
**Resolution:** Added `dependencies` field to skills, implemented DFS-based circular dependency detection, added `CircularDependencyError` exception

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

_FEAT-001 moved to Active Tasks (in progress)._

---

## Summary

### Remaining Work

| Priority | Pending | In Progress | Deferred | Complete | Total |
|----------|---------|-------------|----------|----------|-------|
| **P0 Critical** | 0 | 0 | 0 | 3 | 3 |
| **P1 High** | 1 | 0 | 0 | 3 | 4 |
| **P2 Medium** | 0 | 0 | 0 | 5 | 5 |
| **P3 Low** | 0 | 0 | 3 | 3 | 6 |
| **Features** | 0 | 1 | 0 | 3 | 4 |
| **TOTAL** | **1** | **1** | **3** | **17** | **22** |

### Current Focus

1. **FEAT-001** - Per-Project RAG Support (Phase 1/5 complete)

### Priority Order for Remaining Work

1. **SEC-022** - Address SSRF vulnerability (documented, complex)

---

## Completed Milestones

| Version | Date | Summary |
|---------|------|---------|
| 1.8.15 | 2025-12-28 | Token counter fix (CLI-003): Fixed streaming token counter showing 0/200000 |
| 1.8.14 | 2025-12-28 | Config consolidation (ARCH-004): Unified config patterns to Pydantic |
| 1.8.13 | 2025-12-28 | Output options (CLI-002): Added --json, --no-color, -q CLI flags |
| 1.8.12 | 2025-12-28 | Cache monitoring (SESS-002): Token cache config and /session cache command |
| 1.8.11 | 2025-12-28 | File encoding (TOOL-009): Edit tool preserves file encoding |
| 1.8.10 | 2025-12-28 | Exception sanitization (TOOL-010): Sanitized error messages |
| 1.8.9 | 2025-12-28 | Skills dependencies (MCP-016): Added circular dependency detection |
| 1.8.8 | 2025-12-28 | Session cleanup (SESS-007): Added /session cleanup command |
| 1.8.7 | 2025-12-28 | Constants module (CODE-005): Created centralized constants for magic numbers |
| 1.8.6 | 2025-12-28 | Lock audit (CODE-004): Audited threading.Lock usage, documented decisions |
| 1.8.5 | 2025-12-27 | Version sync (CODE-003): Single-source version via importlib.metadata |
| 1.8.4 | 2025-12-27 | Dead code removal (CODE-002): Removed unused WebConfig and related classes |
| 1.8.3 | 2025-12-27 | CI/CD (CICD-001): Added GitHub Actions workflows for testing and releases |
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
