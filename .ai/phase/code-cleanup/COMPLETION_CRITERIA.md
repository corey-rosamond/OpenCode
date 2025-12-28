# Completion Criteria: Code Cleanup

## Must Have (Required for Completion)

### CR-1: ToolCategory Enum Fixed (CODE-001)
- [ ] `ToolCategory.UTILITY` exists in `src/code_forge/tools/base.py`
- [ ] `tests/conftest.py` runs without AttributeError
- [ ] All tests pass with new enum value

### CR-2: Dead Code Removed (CODE-002)
- [ ] `WebConfig` usage audited and documented
- [ ] If unused: `src/code_forge/web/config.py` deleted
- [ ] If kept: Comment explaining why it's retained
- [ ] No broken imports from removal

### CR-3: Single-Source Version (CODE-003)
- [ ] `__version__` derived from `importlib.metadata`
- [ ] `pyproject.toml` is single source of truth
- [ ] `src/code_forge/__init__.py` updated
- [ ] Fallback for development mode works
- [ ] `forge --version` still works correctly

### CR-4: Tests Pass
- [ ] `pytest tests/` passes
- [ ] No new test failures introduced
- [ ] Existing tests don't break

## Should Have (Expected but not blocking)

### CR-5: Lock Usage Documented (CODE-004)
- [ ] All `threading.Lock()` usages audited
- [ ] Each lock has comment explaining why threading vs asyncio
- [ ] No changes to lock implementation (audit only)

### CR-6: Constants Module (CODE-005)
- [ ] `src/code_forge/core/constants.py` created
- [ ] At least 5 constants migrated
- [ ] Imports updated to use constants

### CR-7: Session Cleanup Wired (SESS-007)
- [ ] `/session cleanup` command added
- [ ] Command removes old sessions
- [ ] Command removes old backups
- [ ] Success message shows counts

## Could Have (Nice to have)

### CR-8: Auto-Cleanup on Close
- [ ] Session manager calls cleanup on close
- [ ] Configurable max age for sessions

### CR-9: Constants Documentation
- [ ] Constants module has docstrings
- [ ] Each constant documented with units

## Won't Have (Explicitly out of scope)

- asyncio.Lock() migration (audit only)
- Performance optimization
- Configuration consolidation (ARCH-004)
- Thread pool implementation (LLM-014)

## Definition of Done

This phase is complete when:
1. All CR-1 through CR-4 items are checked
2. Full test suite passes
3. No new warnings or errors introduced
4. Changes committed with descriptive messages

## Verification Commands

```bash
# Verify enum fix
python -c "from code_forge.tools.base import ToolCategory; print(ToolCategory.UTILITY)"

# Verify version
python -c "from code_forge import __version__; print(__version__)"

# Verify WebConfig removal
grep -r "WebConfig" src/code_forge/ || echo "WebConfig removed successfully"

# Run tests
pytest tests/ -v

# Verify session cleanup command
forge /session cleanup --help  # Should show help
```
