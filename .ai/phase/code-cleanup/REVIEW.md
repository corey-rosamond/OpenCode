# Code Review Checklist: Code Cleanup

## Pre-Review Verification

Before requesting review, verify:
- [ ] All tests pass locally
- [ ] No new warnings from mypy
- [ ] No new warnings from ruff
- [ ] Changes are logically grouped into commits

## Review Checklist

### CODE-001: ToolCategory Enum

#### Implementation
- [ ] UTILITY value added to ToolCategory enum
- [ ] Value is lowercase string "utility"
- [ ] Enum ordering is logical
- [ ] No duplicate values

#### Tests
- [ ] Test for UTILITY existence added
- [ ] Conftest fixtures still work

### CODE-002: WebConfig Removal

#### Verification
- [ ] Grep confirms no usage of WebConfig
- [ ] Or: Clear documentation why it's kept
- [ ] No broken imports after removal

#### Clean Removal
- [ ] File deleted cleanly
- [ ] No orphaned imports
- [ ] No references in __init__.py

### CODE-003: Single-Source Version

#### Implementation
- [ ] Uses importlib.metadata.version()
- [ ] Has fallback for development mode
- [ ] Fallback doesn't raise exception
- [ ] Package name in version() call is correct ("code-forge")

#### Verification
- [ ] `python -c "from code_forge import __version__; print(__version__)"` works
- [ ] `forge --version` works
- [ ] Version matches pyproject.toml

### CODE-004: Lock Documentation (if done)

#### Documentation Quality
- [ ] Each lock has explanatory comment
- [ ] Comments explain why threading.Lock not asyncio.Lock
- [ ] No actual lock implementation changes

### CODE-005: Constants Module (if done)

#### Module Quality
- [ ] Located at `src/code_forge/core/constants.py`
- [ ] Constants have descriptive names
- [ ] Units documented (e.g., "seconds", "bytes")
- [ ] Values are reasonable

#### Migration
- [ ] At least one file updated to use constants
- [ ] Import style is consistent

### SESS-007: Session Cleanup (if done)

#### Command Implementation
- [ ] Command registered correctly
- [ ] Handles edge cases (no old sessions)
- [ ] Returns meaningful output

#### Safety
- [ ] Doesn't delete recent sessions
- [ ] Logs what was deleted

## Commit Quality

### Message Format
- [ ] Clear, descriptive subject line
- [ ] References issue ID (CODE-001, etc.)
- [ ] Body explains what and why

### Scope
- [ ] Each commit is atomic
- [ ] Related changes grouped together
- [ ] Unrelated changes in separate commits

## Testing Verification

### Automated
- [ ] `pytest tests/` passes
- [ ] `mypy src/code_forge/` passes
- [ ] `ruff check src/code_forge/` passes

### Manual
- [ ] `forge --version` works
- [ ] Import statements work in fresh Python

## Review Questions

### For Reviewer

1. Is the ToolCategory.UTILITY placement logical?
2. Is WebConfig truly unused (or should it be documented)?
3. Is the version fallback appropriate for development?
4. Are the constants well-named and reasonable?
5. Is the cleanup command safe enough?

### Known Issues to Ignore

- Deferred items (ARCH-004, threading optimization)
- Existing code style in unchanged files

## Post-Review Actions

After approval:
1. Squash related commits if needed
2. Update CHANGELOG.md
3. Update UNDONE.md (mark items complete)
4. Merge to main
5. Verify nothing broke

## Sign-Off

- [ ] All checklist items verified
- [ ] Code reviewed and approved
- [ ] Ready to merge
