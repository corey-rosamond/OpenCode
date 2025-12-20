# Code-Forge: Current Work

**Last Updated:** 2025-12-21

---

## Active Tasks

_No active tasks._

---

## Backlog

### Critical Priority (P0)

_All critical issues have been addressed._

---

### High Priority (P1)

#### ARCH-004: Configuration System Fragmentation
**Status:** Deferred
**Files:** `config/`, `mcp/config.py`, `hooks/config.py`, `permissions/config.py`, `web/config.py`
**Issue:** 6+ modules use different config patterns (Pydantic vs dataclass vs custom)
**Impact:** Inconsistent API, hard to compose/test configurations
**Note:** Large refactoring task requiring careful migration:
- config/models.py uses Pydantic (canonical)
- mcp/config.py uses dataclasses (MCPServerConfig duplicates Pydantic version)
- hooks/config.py and permissions/config.py use class methods
- web/config.py uses dataclasses (currently unused)
Migration plan: Create common base, migrate one module at a time with tests. Deferred to avoid breaking changes.

#### SEC-022: Race Condition in SSRF Check
**Status:** Documented
**File:** `src/code_forge/web/fetch/fetcher.py:38-58`
**Issue:** DNS validation at fetch time doesn't prevent TOCTOU (DNS rebinding)
**Note:** Added detailed SECURITY NOTE in docstring explaining the vulnerability and mitigation complexity. Full fix requires custom aiohttp connector with IP pinning - deferred to future work.

---

### Medium Priority (P2)

#### CLI-002: No Output Format Options
**Status:** Deferred
**File:** `src/code_forge/cli/repl.py`
**Issue:** No `--json`, `--no-color`, `-q` quiet mode options
**Note:** Feature request requiring significant CLI restructuring. Deferred to future enhancement.

#### SESS-002: Memory Leak in Token Counter Caching
**Status:** Deferred
**File:** `src/code_forge/context/tokens.py:257-353`
**Issue:** Cache default `max_cache_size=1000` could cause memory issues
**Note:** Feature request for cache statistics monitoring. Current size is reasonable for most use cases.

#### SESS-007: No Automatic Session Cleanup
**Status:** Deferred
**File:** `src/code_forge/sessions/storage.py:329-369`
**Issue:** `cleanup_old_sessions()` and `cleanup_old_backups()` exist but never called
**Note:** Feature request - requires implementing scheduled cleanup or CLI command.

#### SESS-008: No Conflict Detection for Concurrent Access
**Status:** Fixed (2025-12-21)
**File:** `src/code_forge/sessions/storage.py`
**Fix:** Implemented cross-platform file locking with timeout support, automatic lock cleanup
**Commit:** 6e8c07b

---

### Low Priority (P3)

#### TOOL-009: Edit Tool Doesn't Preserve File Encoding
**Status:** Deferred
**File:** `src/code_forge/tools/file/edit.py:119-120, 152`
**Issue:** Always uses UTF-8, losing original file encoding (latin-1, utf-16)
**Note:** Requires adding chardet as a dependency. Deferred to future enhancement.

#### TOOL-010: Exception Details Leaked in Error Messages
**Status:** Deferred
**Files:** Multiple tool files
**Issue:** Raw exception strings may leak system information (paths, library versions)
**Note:** Requires systematic audit of all tools. Deferred to future security pass.

#### LLM-014: Thread Overhead Per Call
**Status:** Deferred
**File:** `src/code_forge/langchain/llm.py:246-260`
**Issue:** Creates new thread for every streaming operation
**Note:** Requires design work for module-level thread pool with proper lifecycle management. Deferred to future optimization pass.

#### MCP-016: No Circular Dependency Detection in Skills
**Status:** Deferred
**File:** `src/code_forge/skills/registry.py:255-278`
**Issue:** Skills can have circular dependencies via prompt references
**Impact:** Potential infinite loops
**Reason:** Requires building full dependency graph - substantial feature addition

#### MCP-019: Inefficient Plugin Unregister
**Status:** Deferred
**File:** `src/code_forge/plugins/registry.py:153-168`
**Issue:** Dictionary comprehensions iterate entire collection for each type
**Reason:** Current O(n) per collection is acceptable for typical plugin counts. Reverse indexing adds complexity for marginal gains.

#### MCP-020: Linear Search in Skills Registry
**Status:** Deferred
**File:** `src/code_forge/skills/registry.py:136-150`
**Issue:** `search()` iterates all skills
**Reason:** Linear search is acceptable for typical skill counts. Search indexing would add complexity for marginal gains.

#### PERM-015: No Rate Limiting on Permission Denials
**Status:** Fixed (2025-12-21)
**File:** `src/code_forge/permissions/checker.py`
**Fix:** Added sliding window rate limiter (10 denials/60s), 5-minute backoff, thread-safe tracking
**Commit:** 7fac204

#### PERM-016: No Hook Error Recovery
**Status:** Fixed (2025-12-21)
**File:** `src/code_forge/hooks/executor.py`
**Fix:** Added retry logic with exponential backoff for transient errors (max_retries=2 default)
**Commit:** 4018e02

#### PERM-017: No Dry-Run Mode for Hooks
**Status:** Fixed (2025-12-21)
**File:** `src/code_forge/hooks/executor.py`
**Fix:** Added dry_run parameter that simulates execution without running commands
**Commit:** 4018e02

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

### FEAT-002: Specialized Task Agents
**Status:** Complete (v1.6.0)
**Priority:** High
**Description:** Create different specialized agents for different tasks instead of one general-purpose agent

**Benefits:**
- Better focused prompts for specific tasks
- Specialized tool access per agent type
- Improved output quality for domain-specific work
- Parallel agent execution for complex workflows

**Proposed Agent Types:**

1. **Code Review Agent**
   - Specialized in analyzing diffs and code changes
   - Security vulnerability detection
   - Code style and best practices checking
   - Performance issue identification

2. **Test Generation Agent**
   - Creates test cases from code
   - Identifies edge cases and boundary conditions
   - Generates unit, integration, and e2e tests
   - Maintains test coverage metrics

3. **Documentation Agent**
   - Extracts and generates documentation
   - Creates README files and API docs
   - Updates docstrings and comments
   - Generates architecture diagrams (mermaid)

4. **Refactoring Agent**
   - Identifies code smells and anti-patterns
   - Suggests and implements refactoring
   - Modernizes legacy code patterns
   - Optimizes performance bottlenecks

5. **Planning Agent**
   - Breaks down complex tasks into steps
   - Creates implementation plans
   - Estimates complexity and dependencies
   - Generates task trees and milestones

6. **Debug Agent**
   - Analyzes error messages and stack traces
   - Identifies root causes
   - Suggests fixes with explanations
   - Creates reproduction steps

**Implementation Considerations:**
- Agent registry with metadata and capabilities
- Agent-specific system prompts and tool restrictions
- Agent orchestration for multi-agent workflows
- Shared context between agents
- Agent selection heuristics based on user intent

**Potential Structure:**
```
src/code_forge/agents/
├── specialized/
│   ├── code_review.py
│   ├── test_generation.py
│   ├── documentation.py
│   ├── refactoring.py
│   ├── planning.py
│   └── debug.py
├── orchestrator.py      # Multi-agent coordination
└── selector.py          # Automatic agent selection
```

---

### FEAT-003: Agent Workflow System
**Status:** Proposed
**Priority:** Medium
**Description:** Enable chaining multiple specialized agents together for complex workflows

**Example Workflows:**
- "Full PR Review": Planning → Code Review → Test Generation → Documentation
- "Bug Fix": Debug → Code Review → Test Generation
- "Feature Implementation": Planning → Implementation → Test → Documentation

**Features:**
- Workflow definition via YAML or code
- Conditional agent execution based on results
- Parallel agent execution where possible
- Workflow templates for common tasks
- Progress tracking and resumability

---

## Summary

### Remaining Work

| Priority | Pending | Deferred | Total |
|----------|---------|----------|-------|
| **P0 Critical** | 0 | 0 | 0 |
| **P1 High** | 0 | 2 | 2 |
| **P2 Medium** | 0 | 3 | 3 |
| **P3 Low** | 0 | 6 | 6 |
| **Features** | 2 | 0 | 2 |
| **TOTAL** | **2** | **11** | **13** |

### Breakdown

**Pending Items (2):**
- FEAT-001: Per-Project RAG Support
- FEAT-003: Agent Workflow System

**Deferred Items (12):**
- Technical debt and optimizations that don't block functionality
- Feature enhancements requiring significant refactoring
- Performance optimizations with marginal gains
- Security hardening for edge cases

---

## Completed Milestones

| Version | Date | Summary |
|---------|------|---------|
| 1.6.0 | 2025-12-21 | Specialized agent system (FEAT-002): 16 new agent types |
| 1.5.0 | 2025-12-21 | Technical debt cleanup (SESS-008, PERM-015/016/017) |
| 1.4.0 | 2025-12-21 | Test quality improvements (TEST-001, TEST-002, TEST-003) |
| 1.3.0 | 2025-12-17 | Streaming error handling fix |
| 1.2.0 | 2025-12-17 | Setup wizard, security fixes |
| 1.1.0 | 2025-12-09 | All 22 phases complete, production ready |
| 1.0.0 | 2025-12-09 | Initial release |
