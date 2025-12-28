# Code-Forge AI Development Guide

**Read this file first when starting any development session.**

---

## Current Status

**Core features complete. Now focused on Conversational Intelligence Layer.**

Check `UNDONE.md` for the full roadmap and priorities.

### Active Development

**CTX-001: Context Compression Visibility & Control** ⭐ TOP PRIORITY
- No notification when context is compressed/truncated
- Token counter doesn't update after compression
- No warning when approaching context limit
- **Effort:** 1-2 days | **Impact:** 9.0/10

**Conversational UX Gap Analysis** - 6 features identified:
- CONV-001: Conversational Translation Layer (P0)
- CONV-002: Workflow Orchestration (P0)
- CONV-003: Context-Aware Error Recovery (P1) ⚡ Quick Win
- CONV-004: Smart Project Type Detection (P1) ⚡ Quick Win
- CONV-005: Session Context Continuity (P1)
- CONV-006: Visual Interface Enhancements (P2)

### Recently Completed

**FEAT-004: Undo System & Conversational UX** - ✅ Complete (v1.12.0)
- Undo/Redo for Edit, Write, Bash file operations
- BashFileDetector for shell command analysis
- ConversationalPresenter for natural language tool descriptions
- ErrorExplainer for friendly error messages
- Commands: /undo, /redo, /undo-history, /undo-clear
- 113 new tests, 5406 total tests pass

**RAG-001: RAG Search UX Enhancements** - ✅ Complete (v1.11.0)
- Hybrid search combining vector + text search fallback
- Scope indicator showing project root when searching
- Low confidence warning for vector scores < 0.3

**FEAT-002: Multi-Agent Tools & Web Search** - ✅ Complete (v1.10.0)
- TaskTool, WebSearchBaseTool, WebFetchBaseTool
- RAG integration for agents

**FEAT-001: Per-Project RAG Support** - ✅ Complete (v1.9.0)
- All 5 phases complete with 348 tests

### Remaining Work

| Priority | Status | Items |
|----------|--------|-------|
| P0 Critical | 3 pending | CTX-001, CONV-001, CONV-002 |
| P1 High | 4 pending | CONV-003/004/005, SEC-022 |
| P2 Medium | 1 pending | CONV-006 |
| P3 Low | 3 deferred | Minor improvements |
| Features | 7 pending | See UNDONE.md for details |

### Other Recent Completions (v1.8.1 - v1.9.0)

- FEAT-001: Per-Project RAG Support (v1.9.0)
- DOC-001: Fixed README package references
- CODE-001: Added UTILITY to ToolCategory enum
- CICD-001: Created GitHub Actions CI/CD pipeline
- CODE-002: Removed dead WebConfig code
- CODE-003: Single-source version via importlib.metadata
- CODE-004: Audited threading.Lock usage
- CODE-005: Created centralized constants module
- SESS-007: Added `/session cleanup` command
- MCP-016: Added circular dependency detection to skills
- TOOL-010: Sanitized exception messages to prevent info leakage
- TOOL-009: Edit tool preserves file encoding
- SESS-002: Token cache monitoring and config
- CLI-002: Added `--json`, `--no-color`, `-q`/`--quiet` CLI flags
- ARCH-004: Unified config patterns to Pydantic BaseModel
- CLI-003: Fixed streaming token counter showing 0/200000

**When starting new work:**
1. Check `UNDONE.md` for deferred items or feature requests
2. Read the corresponding phase directory's `PLAN.md` if one exists
3. Follow `COMPLETION_CRITERIA.md` to know when you're done
4. Use `TESTS.md` to verify your work
5. Follow `REVIEW.md` before committing

---

## Quick Start

1. **Read governance docs** (if unfamiliar):
   - `PERSONA.md` - Working style and principles
   - `GUARDRAILS.md` - Code quality standards with examples

2. **Understand the system** (if unfamiliar):
   - `ARCHITECTURE.md` - System design and components
   - `MAP.md` - Where to find things in the codebase

3. **Before making changes**:
   - `PATTERNS.md` - How to extend tools, commands, agents, etc.
   - `CONVENTIONS.md` - Naming, testing, and style conventions

4. **Track work**:
   - `UNDONE.md` - Current tasks and future work

---

## Project Overview

**Code-Forge** is an AI-powered CLI development assistant providing:
- Access to 400+ AI models via OpenRouter API
- LangChain integration for agent orchestration
- 21 specialized agent types for focused tasks
- Workflow system for multi-step agent pipelines
- Full CLI with tools, permissions, sessions, and extensibility

**Version:** 1.12.0 (derived from pyproject.toml)
**Status:** Production/Stable
**Tests:** 5406+ (85%+ coverage)

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/code_forge/` | All implementation code |
| `tests/` | Test suite (mirrors src structure) |
| `docs/` | User and developer documentation |
| `.ai/phase/` | Phase planning documentation |

---

## Phase Directory Structure

Each active task has a phase directory with:

```
.ai/phase/<phase-name>/
├── PLAN.md                 # What to do and how
├── COMPLETION_CRITERIA.md  # What "done" means
├── GHERKIN.md              # BDD test scenarios
├── DEPENDENCIES.md         # What this depends on
├── TESTS.md                # Test strategy
└── REVIEW.md               # Code review checklist
```

**Always read `PLAN.md` before starting work on a phase.**

---

## Verification Before Claiming Done

```bash
# Run tests
pytest tests/ -v

# Type checking
mypy src/code_forge/

# Linting
ruff check src/code_forge/

# All must pass before any PR
```

---

## Version and Changelog Management

**When completing any milestone or significant work:**

1. **Update version number** in `pyproject.toml`:
   - `version = "X.Y.Z"`
   - Note: `__version__` in `src/code_forge/__init__.py` is derived automatically from pyproject.toml

2. **Update CHANGELOG.md** with changes:
   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD

   ### Added
   - New features

   ### Fixed
   - Bug fixes

   ### Improved
   - Enhancements
   ```

3. **Version numbering guide** (Semantic Versioning):
   - **Major (X.0.0)**: Breaking changes, major rewrites
   - **Minor (0.X.0)**: New features, significant improvements
   - **Patch (0.0.X)**: Bug fixes, small improvements

4. **Update UNDONE.md** to mark the task as complete

**Note:** Version in `.ai/START.md` is informational only - do not rely on it being accurate. The source of truth is `pyproject.toml`.

---

## Git Commit Rules

**NEVER add any of the following to commit messages:**
- "Generated with Claude Code" or any AI tool references
- "Co-Authored-By" headers with AI names
- Any attribution suggesting AI authorship
- Links to claude.com or any AI service

**Commits are authored by the human developer, not AI assistants.**

---

## Remember

> "The code is the source of truth. Read it before changing it."

> "Tests prove it works. No tests = not done."

> "Check UNDONE.md first. Fix the highest priority issue."

---

## Document Reference

| File | Purpose |
|------|---------|
| `START.md` | This file - entry point |
| `UNDONE.md` | **Current tasks and priorities - check this first** |
| `PERSONA.md` | Developer mindset, principles, BDD approach |
| `GUARDRAILS.md` | Code quality do's/don'ts with examples |
| `ARCHITECTURE.md` | System design, components, data flow |
| `MAP.md` | Complete source tree, "where is X?" |
| `PATTERNS.md` | How to add tools, commands, agents, skills |
| `CONVENTIONS.md` | Naming, types, testing, style rules |
| `phase/*/PLAN.md` | Implementation plans for each phase |
