# Code-Forge AI Development Guide

**Read this file first when starting any development session.**

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
- Full CLI with tools, permissions, sessions, and extensibility

**Version:** 1.1.0
**Status:** Production/Stable
**Tests:** 3400+ (90%+ coverage)

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/code_forge/` | All implementation code |
| `tests/` | Test suite (mirrors src structure) |
| `docs/` | User and developer documentation |

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

---

## Document Reference

| File | Size | Purpose |
|------|------|---------|
| `START.md` | - | This file - entry point |
| `PERSONA.md` | 6KB | Developer mindset, principles, BDD approach |
| `GUARDRAILS.md` | 13KB | Code quality do's/don'ts with examples |
| `ARCHITECTURE.md` | 5KB | System design, components, data flow |
| `MAP.md` | 9KB | Complete source tree, "where is X?" |
| `PATTERNS.md` | 8KB | How to add tools, commands, agents, skills |
| `CONVENTIONS.md` | 6KB | Naming, types, testing, style rules |
| `UNDONE.md` | 1KB | Current tasks, backlog, milestones |
