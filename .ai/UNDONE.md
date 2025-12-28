# Code-Forge: Current Work

**Last Updated:** 2025-12-28

---

## Active Tasks

### FEAT-004: Undo System & Conversational UX
**Status:** ✅ Complete (v1.12.0)
**Priority:** High (P1)
**Version Target:** 1.12.0
**Phase Directory:** `.ai/phase/undo-and-conversation/`

**Problem:**
- No undo/redo capability for file operations
- Tool execution feels mechanical vs conversational
- Error messages lack helpful suggestions

**Solution:**
- Undo system with FileSnapshot, UndoEntry, UndoHistory models
- UndoManager for capture/restore of Edit, Write, Bash operations
- BashFileDetector for detecting file-modifying shell commands
- ConversationalPresenter for natural language tool descriptions
- ErrorExplainer for friendly error messages with suggestions

**Progress:**
- [x] Core undo models (FileSnapshot, UndoEntry, UndoHistory)
- [x] UndoManager implementation
- [x] BashFileDetector for shell command analysis
- [x] Tool integration (Edit, Write, Bash)
- [x] Undo commands (/undo, /redo, /undo-history, /undo-clear)
- [x] ConversationalPresenter with ToolDescriptor
- [x] ReasoningExtractor and ErrorExplainer
- [x] Unit tests (113 new tests)
- [x] Full verification (5406 tests pass)

**Files Created:**
- `src/code_forge/undo/models.py` - Data models
- `src/code_forge/undo/manager.py` - UndoManager
- `src/code_forge/undo/bash_detector.py` - BashFileDetector
- `src/code_forge/undo/__init__.py` - Package init
- `src/code_forge/commands/builtin/undo_commands.py` - Commands
- `src/code_forge/cli/conversation.py` - ConversationalPresenter
- `tests/unit/undo/test_*.py` - 81 tests
- `tests/unit/cli/test_conversation.py` - 32 tests

---

### FEAT-002: Multi-Agent Tools & Web Search Integration
**Status:** ✅ Complete (v1.10.0)
**Priority:** Critical (P0)
**Version Target:** 1.10.0
**Phase Directory:** `.ai/phase/llm-tool-integration/`

**Problem:**
- LLM cannot spawn sub-agents (TaskTool missing)
- LLM cannot search web (WebSearchBaseTool missing)
- LLM cannot fetch URLs (WebFetchBaseTool missing)
- Agents don't have RAG access

**Solution:**
- Create TaskTool to expose 20+ agent types to LLM
- Create WebSearchBaseTool wrapping existing web search
- Create WebFetchBaseTool wrapping existing web fetch
- Pass RAGManager through ExecutionContext to agents

**Progress:**
- [x] Phase directory created with all standard files
- [x] TaskTool implementation
- [x] WebSearchBaseTool implementation
- [x] WebFetchBaseTool implementation
- [x] Tool registration
- [x] RAG integration for agents
- [x] Unit tests (49 new tests)
- [x] Full verification (5293 tests pass)

---

### FEAT-001: Per-Project RAG Support
**Status:** ✅ Complete (v1.9.0)
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
- [x] Phase 2: Vector Store & Chunking (Complete)
  - VectorStore abstraction with ChromaDB, FAISS, and Mock backends
  - Intelligent code chunking with AST-aware splitting
  - Language detection and syntax-aware chunking
  - 86 unit tests passing
- [x] Phase 3: Indexer & Retriever (Complete)
  - ProjectIndexer for file discovery and processing
  - RAGRetriever for semantic search with ranking
  - Incremental indexing with change detection
  - 234 tests, 90%+ coverage
- [x] Phase 4: Manager & Commands (Complete)
  - RAGManager as central coordinator
  - CLI commands: /rag index, search, status, clear, config
  - RAGContextAugmenter for LLM context integration
  - 325 tests, 92% coverage for Phase 4 modules
- [x] Phase 5: Integration & Polish (Complete)
  - RAGManager integrated with Dependencies and CommandContext
  - Auto-index on project open when enabled
  - Context augmentation in message flow
  - 348 total tests, 90%+ coverage

**Files Created:**
- Phase 1: models.py, config.py, embeddings.py
- Phase 2: vectorstore.py, chunking.py
- Phase 3: indexer.py, retriever.py
- Phase 4: manager.py, commands.py, integration.py
- Phase 5: Updated executor.py, dependencies.py, main.py
- Tests: test_*.py for each module (348 total tests)

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

### 🔴 CONV-001: Conversational Translation Layer
**Status:** Pending
**Priority:** Critical (P0)
**Impact:** 9.5/10
**Complexity:** High

**Problem:**
- Tools require exact parameters; LLM doesn't auto-infer intent
- "Replace all instances of X with Y" doesn't auto-set `replace_all=true`
- Natural language commands require manual tool parameter mapping

**Solution:**
Create a NaturalLanguageInterpreter that translates conversational requests into tool sequences with proper parameters.

**Phase Plan:**

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1: Intent Classification** | Build intent classifier for common patterns | IntentClassifier, pattern library |
| **Phase 2: Parameter Inference** | Auto-infer tool parameters from context | ParameterResolver, context extractor |
| **Phase 3: Tool Sequence Planning** | Chain multiple tools for complex requests | ToolSequencePlanner |
| **Phase 4: Prompt Engineering** | Enhance system prompt with translation guidance | Updated prompts, few-shot examples |
| **Phase 5: Integration** | Wire into main agent flow | Updated main.py, testing |

**Files to Create:**
- `src/code_forge/natural/__init__.py`
- `src/code_forge/natural/intent.py` - IntentClassifier
- `src/code_forge/natural/resolver.py` - ParameterResolver
- `src/code_forge/natural/planner.py` - ToolSequencePlanner
- `tests/unit/natural/test_*.py`

---

### 🔴 CONV-002: Workflow Orchestration
**Status:** Pending
**Priority:** Critical (P0)
**Impact:** 9.0/10
**Complexity:** Medium

**Problem:**
- No intelligent task sequencing for complex requests
- "Optimize this React component" requires manual multi-step execution
- WorkflowTool exists but lacks smart templates and auto-triggering

**Solution:**
Enhance WorkflowTool with intelligent templates and auto-sequencing based on request analysis.

**Phase Plan:**

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1: Template Library** | Create workflow templates for common tasks | 10+ workflow templates (refactor, test, deploy, etc.) |
| **Phase 2: Request Analyzer** | Detect workflow triggers from natural language | WorkflowMatcher, trigger patterns |
| **Phase 3: Auto-Sequencing** | Auto-compose workflows from request intent | WorkflowComposer |
| **Phase 4: Progress Tracking** | Real-time progress for multi-step workflows | WorkflowProgress, status updates |
| **Phase 5: Rollback Support** | Undo entire workflows on failure | WorkflowRollback using undo system |

**Files to Create/Modify:**
- `src/code_forge/workflows/templates/` - Template library
- `src/code_forge/workflows/matcher.py` - WorkflowMatcher
- `src/code_forge/workflows/composer.py` - WorkflowComposer
- `src/code_forge/workflows/progress.py` - Progress tracking

---

### 🟡 CONV-003: Context-Aware Error Recovery
**Status:** Pending
**Priority:** High (P1)
**Impact:** 8.5/10
**Complexity:** Low

**Problem:**
- Errors show raw messages without actionable suggestions
- No automatic retry with alternative approaches
- User must manually diagnose and fix issues

**Solution:**
Extend ErrorExplainer (already created) with auto-suggestions and recovery actions.

**Phase Plan:**

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1: Error Catalog Expansion** | Expand error patterns and suggestions | 50+ error patterns with suggestions |
| **Phase 2: Auto-Suggestion Integration** | Wire ErrorExplainer into main event loop | Updated main.py error handling |
| **Phase 3: Recovery Actions** | Implement automatic recovery attempts | RecoveryExecutor, retry logic |
| **Phase 4: Learning** | Track which suggestions work | ErrorMetrics, suggestion ranking |

**Files to Modify:**
- `src/code_forge/cli/conversation.py` - Expand ERROR_CATALOG
- `src/code_forge/cli/main.py` - Integrate error suggestions
- `src/code_forge/cli/recovery.py` - RecoveryExecutor (new)

---

### 🟡 CONV-004: Smart Project Type Detection
**Status:** Pending
**Priority:** High (P1)
**Impact:** 7.5/10
**Complexity:** Low

**Problem:**
- Generic responses regardless of project type (Python/Node/Rust/etc.)
- No language-specific suggestions or tool preferences
- System prompt doesn't adapt to project context

**Solution:**
Detect project type at session start and inject context into system prompt.

**Phase Plan:**

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1: Project Detector** | Analyze project files for type detection | ProjectTypeDetector (package.json, pyproject.toml, Cargo.toml, etc.) |
| **Phase 2: Context Profiles** | Create per-language context profiles | Language profiles with tool preferences |
| **Phase 3: Prompt Injection** | Add project context to system prompt | Updated prompt generation |
| **Phase 4: Tool Hints** | Suggest language-appropriate tools | ToolHinter based on project type |

**Files to Create:**
- `src/code_forge/context/project_detector.py`
- `src/code_forge/context/profiles.py` - Language profiles
- Update `src/code_forge/langchain/prompts.py`

---

### 🟡 CONV-005: Session Context Continuity
**Status:** Pending
**Priority:** High (P1)
**Impact:** 8.0/10
**Complexity:** Medium

**Problem:**
- Tools don't maintain conversational state
- "it" references don't resolve to previously mentioned files
- No tracking of "active file" or "last edited" context

**Solution:**
Track session context including active files, recent operations, and resolve pronouns.

**Phase Plan:**

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1: Context Tracker** | Track active file, last operation, mentioned entities | SessionContextTracker |
| **Phase 2: Pronoun Resolution** | Resolve "it", "that file", "the function" references | PronounResolver |
| **Phase 3: Context Injection** | Add context to tool calls automatically | ContextInjector |
| **Phase 4: Memory Integration** | Persist context across session restarts | Session metadata storage |

**Files to Create:**
- `src/code_forge/context/tracker.py` - SessionContextTracker
- `src/code_forge/context/resolver.py` - PronounResolver
- Update session metadata schema

---

### 🟢 CONV-006: Visual Interface Enhancements
**Status:** Pending
**Priority:** Medium (P2)
**Impact:** 6.0/10
**Complexity:** Medium

**Problem:**
- No visual diffs in terminal
- No inline code suggestions
- No interactive file tree exploration

**Solution:**
Add Rich-based visual enhancements for diffs, suggestions, and file browsing.

**Phase Plan:**

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| **Phase 1: Visual Diffs** | Show colored diffs for Edit operations | DiffPresenter using Rich |
| **Phase 2: Code Suggestions** | Inline syntax-highlighted suggestions | SuggestionPresenter |
| **Phase 3: File Tree** | Interactive file browser | FileTreeBrowser |
| **Phase 4: Progress Visualization** | Visual progress bars for long operations | ProgressVisualizer |

**Files to Create:**
- `src/code_forge/cli/visual/diff.py`
- `src/code_forge/cli/visual/suggestions.py`
- `src/code_forge/cli/visual/tree.py`
- `src/code_forge/cli/visual/progress.py`

---

## Summary

### Remaining Work

| Priority | Pending | In Progress | Deferred | Complete | Total |
|----------|---------|-------------|----------|----------|-------|
| **P0 Critical** | 2 | 0 | 0 | 4 | 6 |
| **P1 High** | 4 | 0 | 0 | 4 | 8 |
| **P2 Medium** | 1 | 0 | 0 | 5 | 6 |
| **P3 Low** | 0 | 0 | 3 | 3 | 6 |
| **Features** | 6 | 0 | 0 | 6 | 12 |
| **TOTAL** | **7** | **0** | **3** | **22** | **32** |

### Current Focus

**Conversational Intelligence Layer** - Making Code-Forge feel as natural as Claude Code.

---

## 🚀 Quick Wins

These features provide **high impact with low implementation effort** - ideal starting points:

### 1. CONV-003: Context-Aware Error Recovery
**Effort:** 1-2 days | **Impact:** 8.5/10 | **ROI:** Excellent

**Why it's a quick win:**
- ErrorExplainer already exists in `conversation.py`
- Just needs catalog expansion (50+ patterns) and main.py integration
- Immediate UX improvement visible to users

**Implementation:**
```
Day 1: Expand ERROR_CATALOG with 50+ common error patterns
Day 2: Integrate into main.py event loop, add recovery suggestions
```

### 2. CONV-004: Smart Project Type Detection
**Effort:** 1-2 days | **Impact:** 7.5/10 | **ROI:** Excellent

**Why it's a quick win:**
- Simple file existence checks (package.json, pyproject.toml, Cargo.toml)
- Inject detection results into system prompt
- No complex logic required

**Implementation:**
```
Day 1: Create ProjectTypeDetector with file pattern matching
Day 2: Create language profiles, inject into prompt generation
```

### 3. CONV-006 Phase 1: Visual Diffs
**Effort:** 1 day | **Impact:** 6.0/10 | **ROI:** Good

**Why it's a quick win:**
- Rich library already supports diff rendering
- Hooks into existing Edit tool completion
- High visibility improvement

**Implementation:**
```
Day 1: Create DiffPresenter, integrate with present_tool_end for Edit
```

---

## 📊 Recommended Implementation Order

Based on **impact × (1/effort)** analysis:

| Order | Feature | Impact | Effort | ROI Score | Rationale |
|-------|---------|--------|--------|-----------|-----------|
| **1** | CONV-003 | 8.5 | Low | ⭐⭐⭐⭐⭐ | Quick win, immediate UX improvement |
| **2** | CONV-004 | 7.5 | Low | ⭐⭐⭐⭐⭐ | Quick win, better context awareness |
| **3** | CONV-005 | 8.0 | Medium | ⭐⭐⭐⭐ | Enables pronoun resolution, foundational |
| **4** | CONV-001 | 9.5 | High | ⭐⭐⭐⭐ | Transformative, but complex |
| **5** | CONV-002 | 9.0 | Medium | ⭐⭐⭐ | Builds on existing workflow system |
| **6** | CONV-006 | 6.0 | Medium | ⭐⭐⭐ | Polish, nice-to-have |
| **7** | SEC-022 | N/A | High | ⭐⭐ | Security fix, complex implementation |

### Recommended Sprint Plan

**Sprint 1 (3-4 days): Quick Wins**
- [ ] CONV-003: Error Recovery Expansion
- [ ] CONV-004: Project Type Detection

**Sprint 2 (4-5 days): Context Foundation**
- [ ] CONV-005: Session Context Continuity
- [ ] CONV-006 Phase 1: Visual Diffs

**Sprint 3 (1 week): Intelligence Layer**
- [ ] CONV-001: Conversational Translation Layer

**Sprint 4 (1 week): Workflow Enhancement**
- [ ] CONV-002: Workflow Orchestration

---

## Priority Order (By Impact)

1. **CONV-001** - Conversational Translation Layer (P0, Impact 9.5)
2. **CONV-002** - Workflow Orchestration (P0, Impact 9.0)
3. **CONV-003** - Context-Aware Error Recovery (P1, Impact 8.5) ⚡ Quick Win
4. **CONV-005** - Session Context Continuity (P1, Impact 8.0)
5. **CONV-004** - Smart Project Type Detection (P1, Impact 7.5) ⚡ Quick Win
6. **CONV-006** - Visual Interface Enhancements (P2, Impact 6.0)
7. **SEC-022** - Address SSRF vulnerability (documented, complex)

---

## Completed Milestones

| Version | Date | Summary |
|---------|------|---------|
| 1.11.0 | 2025-12-28 | RAG UX (RAG-001): Hybrid search, scope indicator, low confidence warning, TOOL-011 edit fix |
| 1.10.0 | 2025-12-28 | Multi-Agent Tools (FEAT-002): TaskTool, WebSearchBaseTool, WebFetchBaseTool, RAG integration, 49 new tests |
| 1.9.0 | 2025-12-28 | RAG Support (FEAT-001): Per-project RAG with semantic search, 348 tests |
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
