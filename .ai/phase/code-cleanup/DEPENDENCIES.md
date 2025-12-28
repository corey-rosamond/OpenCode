# Dependencies: Code Cleanup

## Phase Dependencies

### Depends On (Blockers)
None. This phase can be started immediately.

### Blocks (Downstream)
- Future test improvements (enum must be fixed)
- Version automation (currently manual)

### Recommended Order
Complete DOC-001 (README fix) first to avoid documentation confusion, but not strictly required.

## Technical Dependencies

### Required Tools
- Python 3.11+
- pytest
- grep
- git

### Required Packages
- importlib.metadata (stdlib, Python 3.8+)
- No new dependencies

### Required Access
- Write access to repository
- Ability to run tests locally

## Knowledge Dependencies

### Required Understanding
- Python enum types
- importlib.metadata usage
- Threading vs asyncio locking semantics
- Session storage implementation

### Recommended Reading
- `src/code_forge/tools/base.py` - ToolCategory enum
- `src/code_forge/__init__.py` - Current version handling
- `src/code_forge/web/config.py` - WebConfig to audit
- `src/code_forge/sessions/storage.py` - Cleanup methods
- `tests/conftest.py` - UTILITY usage

## Integration Points

### Files to Coordinate With

| File | Reason |
|------|--------|
| `pyproject.toml` | Version source of truth |
| `tests/conftest.py` | Uses ToolCategory.UTILITY |
| `src/code_forge/web/__init__.py` | May export WebConfig |
| `src/code_forge/commands/builtin/session_commands.py` | Add cleanup |

### Singleton Registries Affected
- None directly (registry implementations unchanged)

### API Changes
- None (internal changes only)
- New command `/session cleanup` is additive

## Rollback Plan

Each change is independent and can be reverted separately:

1. **Enum change:** `git revert` the specific commit
2. **WebConfig removal:** Restore file from git history
3. **Version change:** Revert to hardcoded version
4. **Constants:** Remove new file, revert imports
5. **Session cleanup:** Remove new command

Low risk overall - changes are isolated and reversible.

## Testing Dependencies

### Tests That Must Pass
- `tests/conftest.py` - Uses UTILITY enum
- `tests/unit/tools/` - Tool tests
- `tests/unit/cli/` - CLI tests (version)
- `tests/commands/` - Command tests

### New Tests to Add
- Test for `/session cleanup` command
- Test for version from metadata
- Test for constants import
