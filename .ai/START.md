# Code-Forge AI Development Guide

**Read this file first when starting any development session.**

---

## Current Priority Tasks

**Check `UNDONE.md` immediately for the current priority order.**

The following tasks are ranked by priority and should be addressed in order:

### Critical (P0) - Do These First

| ID | Task | Phase Directory | Effort |
|----|------|-----------------|--------|
| DOC-001 | Fix README package references (`forge.` → `code_forge.`) | `.ai/phase/documentation-fix/` | 2-4h |
| CODE-001 | Fix ToolCategory enum (add UTILITY) | `.ai/phase/code-cleanup/` | 30min |
| CICD-001 | Create CI/CD pipeline (GitHub Actions) | `.ai/phase/cicd-setup/` | 4-6h |

### High Priority (P1) - Do After P0

| ID | Task | Phase Directory |
|----|------|-----------------|
| CODE-002 | Remove dead WebConfig code | `.ai/phase/code-cleanup/` |
| CODE-003 | Fix version synchronization (single source) | `.ai/phase/code-cleanup/` |
| SEC-022 | Address SSRF vulnerability | Needs phase created |
| ARCH-004 | Consolidate config patterns | Needs phase created |

**When starting work:**
1. Check `UNDONE.md` for the current highest-priority pending task
2. Read the corresponding phase directory's `PLAN.md`
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

**Version:** 1.8.0
**Status:** Production/Stable (with known issues - see UNDONE.md)
**Tests:** 4898 (85%+ coverage)

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

1. **Update version number** in these files:
   - `pyproject.toml` - `version = "X.Y.Z"`
   - `src/code_forge/__init__.py` - `__version__ = "X.Y.Z"`

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
