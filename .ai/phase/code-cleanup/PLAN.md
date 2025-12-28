# Phase: Code Cleanup

## Overview

**Phase ID:** CODE-001 through CODE-005, SESS-007
**Priority:** Critical to Medium (P0-P2)
**Estimated Effort:** 4-8 hours
**Target Version:** 1.8.1 or 1.9.0

## Problem Statement

Multiple code quality issues have accumulated that need cleanup:

1. **CODE-001 (P0):** ToolCategory enum is missing UTILITY value used in tests
2. **CODE-002 (P1):** WebConfig class is dead code - never instantiated
3. **CODE-003 (P1):** Version must be manually updated in 4 places
4. **CODE-004 (P2):** Mixed threading.Lock() and asyncio patterns
5. **CODE-005 (P2):** Magic numbers scattered across codebase
6. **SESS-007 (P2):** Session cleanup methods exist but are never called

## Scope

### In Scope
1. Add UTILITY to ToolCategory enum
2. Remove or integrate unused WebConfig
3. Implement single-source version using importlib.metadata
4. Audit and document lock usage decisions
5. Create constants module for common values
6. Wire up session cleanup methods

### Out of Scope
- Major architectural changes
- New features
- Performance optimizations beyond cleanup
- Configuration system consolidation (separate phase)

## Implementation Plan

### Step 1: Fix ToolCategory Enum (CODE-001)
**Priority:** Critical - Blocks test correctness

```python
# src/code_forge/tools/base.py
class ToolCategory(str, Enum):
    FILE = "file"
    EXECUTION = "execution"
    WEB = "web"
    TASK = "task"
    NOTEBOOK = "notebook"
    MCP = "mcp"
    UTILITY = "utility"  # ADD THIS
    OTHER = "other"
```

**Files:**
- `src/code_forge/tools/base.py` - Add enum value
- Verify `tests/conftest.py` works with change

### Step 2: Remove Dead WebConfig (CODE-002)
**Priority:** High

1. Verify WebConfig is truly unused:
   ```bash
   grep -r "WebConfig" src/code_forge/ --include="*.py"
   ```
2. If unused, delete `src/code_forge/web/config.py`
3. Remove any imports of WebConfig
4. Update `__init__.py` exports if needed

**Files:**
- `src/code_forge/web/config.py` - Delete or document why kept
- Any files importing WebConfig

### Step 3: Single-Source Version (CODE-003)
**Priority:** High

Replace manual version synchronization with importlib.metadata:

```python
# src/code_forge/__init__.py
"""Code-Forge - AI-powered CLI development assistant."""

try:
    from importlib.metadata import version
    __version__ = version("code-forge")
except Exception:
    __version__ = "0.0.0"  # Fallback for development

__all__ = ["__version__"]
```

**Files:**
- `src/code_forge/__init__.py` - Use importlib.metadata
- `.ai/START.md` - Remove version from here (derive from package)
- Update version update instructions

### Step 4: Audit Lock Usage (CODE-004)
**Priority:** Medium

Audit all uses of `threading.Lock()` in async code:

| File | Lock Usage | Decision |
|------|------------|----------|
| `llm/client.py` | `_usage_lock` | Keep - protects sync counters |
| `tools/registry.py` | `_lock` | Keep - singleton protection |
| `sessions/manager.py` | `_lock` | Audit needed |
| `hooks/registry.py` | `_lock` | Audit needed |

Document decisions in code comments.

### Step 5: Centralize Constants (CODE-005)
**Priority:** Medium

Create constants module:

```python
# src/code_forge/core/constants.py
"""Centralized constants for Code-Forge."""

# Timeouts (seconds)
DEFAULT_TIMEOUT = 120.0
TOOL_TIMEOUT = 30.0
COMMAND_TIMEOUT = 30.0
LLM_TIMEOUT = 300.0

# Retries
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0

# Limits
MAX_OUTPUT_SIZE = 100000
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ITERATIONS = 10

# Context
DEFAULT_CONTEXT_LIMIT = 128000
```

Gradually migrate hardcoded values to use constants.

### Step 6: Wire Session Cleanup (SESS-007)
**Priority:** Medium

Options:
1. Add `/session cleanup` command
2. Add cleanup on session manager close
3. Add configurable auto-cleanup

Recommended: Option 1 + 2

```python
# Add to session commands
class SessionCleanupCommand(Command):
    name = "session cleanup"
    description = "Remove old sessions and backups"

    async def execute(self, args, kwargs, context):
        storage = context.session_manager._storage
        deleted = storage.cleanup_old_sessions(max_age_days=30)
        backups = storage.cleanup_old_backups()
        return CommandResult.success(
            f"Cleaned up {deleted} sessions, {backups} backups"
        )
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/code_forge/tools/base.py` | Add UTILITY enum |
| `src/code_forge/web/config.py` | Delete or document |
| `src/code_forge/__init__.py` | Use importlib.metadata |
| `src/code_forge/core/constants.py` | New file |
| `src/code_forge/llm/client.py` | Document lock decision |
| `src/code_forge/commands/builtin/session_commands.py` | Add cleanup |
| `.ai/START.md` | Update version instructions |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking import changes | Low | High | Run full test suite |
| Version detection fails | Low | Medium | Fallback to "0.0.0" |
| Removing used code | Low | High | Grep verification |
| Lock changes cause race | Medium | High | Audit only, no changes |

## Success Metrics

1. All tests pass including conftest.py UTILITY usage
2. `grep -r "WebConfig" src/` returns 0 results (or documented)
3. Version automatically derived from pyproject.toml
4. Constants module created with at least 10 values
5. `/session cleanup` command works
