# Code-Forge AI Development Guide

**Read this file first when starting any development session.**

---

## Current Status

**Conversational Intelligence Layer complete. Polish and security work remaining.**

Check `UNDONE.md` for the full roadmap and priorities.

### Active Development

**CONV-006: Visual Interface Enhancements** ⭐ NEXT PRIORITY
- Phase 1 (Visual Diffs) complete
- Phases 2-4 pending: Code Suggestions, File Tree, Progress Visualization
- **Effort:** Medium | **Impact:** 6.0/10

**SEC-022: SSRF Check Race Condition**
- DNS rebinding vulnerability in web fetcher
- Documented, requires custom aiohttp connector

### Recently Completed (v1.13.0 - v1.20.0)

**CONV-002: Workflow Orchestration** - ✅ Complete (v1.20.0)
- WorkflowMatcher with 7 built-in trigger patterns
- WorkflowComposer for auto-sequencing
- WorkflowProgressTracker with observer pattern
- WorkflowRollback using undo system
- 95 new tests

**CONV-001: Conversational Translation Layer** - ✅ Complete (v1.19.0)
- IntentClassifier with 20+ intent types, 40+ patterns
- ParameterResolver with context-aware inference
- ToolSequencePlanner with 7 templates
- NaturalLanguageMiddleware for request preprocessing
- 94 new tests

**CONV-005: Session Context Continuity** - ✅ Complete (v1.18.0)
- SessionContextTracker for file/operation tracking
- PronounResolver for "it"/"that file" resolution
- Session metadata persistence

**CONV-006 Phase 1: Visual Diffs** - ✅ Complete (v1.17.0)
- DiffPresenter with Rich rendering
- Unified and minimal diff styles

**CONV-004: Smart Project Type Detection** - ✅ Complete (v1.15.0)
**CONV-003: Context-Aware Error Recovery** - ✅ Complete (v1.14.0)
**CTX-001: Context Compression Visibility** - ✅ Complete (v1.13.0)

### Remaining Work

| Priority | Status | Items |
|----------|--------|-------|
| P0 Critical | 0 pending | All complete |
| P1 High | 1 pending | SEC-022 |
| P2 Medium | 1 pending | CONV-006 (Phases 2-4) |
| P3 Low | 3 deferred | Minor improvements |

### Previous Completions (v1.8.1 - v1.12.0)

- FEAT-004: Undo System & Conversational UX (v1.12.0)
- RAG-001: RAG Search UX Enhancements (v1.11.0)
- FEAT-002: Multi-Agent Tools & Web Search (v1.10.0)
- FEAT-001: Per-Project RAG Support (v1.9.0)

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

**Version:** 1.20.1 (derived from pyproject.toml)
**Status:** Production/Stable
**Tests:** 5600+ (85%+ coverage)

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
