# Test Strategy: Code Cleanup

## Test Approach

This phase involves multiple independent changes, each with its own test strategy.

## Unit Tests

### T-1: ToolCategory Enum Tests
```python
# tests/unit/tools/test_base.py

def test_tool_category_has_utility():
    """Verify UTILITY enum value exists."""
    from code_forge.tools.base import ToolCategory

    assert hasattr(ToolCategory, 'UTILITY')
    assert ToolCategory.UTILITY.value == "utility"


def test_tool_category_all_values_are_strings():
    """Verify all enum values are lowercase strings."""
    from code_forge.tools.base import ToolCategory

    for category in ToolCategory:
        assert isinstance(category.value, str)
        assert category.value == category.value.lower()


def test_tool_category_values_are_unique():
    """Verify no duplicate enum values."""
    from code_forge.tools.base import ToolCategory

    values = [c.value for c in ToolCategory]
    assert len(values) == len(set(values))
```

### T-2: Version Tests
```python
# tests/unit/test_version.py

def test_version_is_string():
    """Verify __version__ is a string."""
    from code_forge import __version__

    assert isinstance(__version__, str)


def test_version_is_semver_format():
    """Verify version follows semantic versioning."""
    import re
    from code_forge import __version__

    # Matches X.Y.Z or X.Y.Z.devN or X.Y.ZaN etc
    pattern = r'^\d+\.\d+\.\d+.*$'
    assert re.match(pattern, __version__), f"Version {__version__} not semver"


def test_version_matches_pyproject():
    """Verify version matches pyproject.toml."""
    import tomllib
    from pathlib import Path
    from code_forge import __version__

    pyproject = Path(__file__).parents[2] / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        expected = data["project"]["version"]
        assert __version__ == expected
```

### T-3: Constants Tests
```python
# tests/unit/core/test_constants.py

def test_constants_module_exists():
    """Verify constants module can be imported."""
    from code_forge.core import constants

    assert constants is not None


def test_timeout_constants_are_positive():
    """Verify timeout values are positive numbers."""
    from code_forge.core.constants import (
        DEFAULT_TIMEOUT,
        TOOL_TIMEOUT,
        COMMAND_TIMEOUT,
    )

    assert DEFAULT_TIMEOUT > 0
    assert TOOL_TIMEOUT > 0
    assert COMMAND_TIMEOUT > 0


def test_retry_constants_are_reasonable():
    """Verify retry values are reasonable."""
    from code_forge.core.constants import (
        DEFAULT_MAX_RETRIES,
        DEFAULT_RETRY_DELAY,
    )

    assert 1 <= DEFAULT_MAX_RETRIES <= 10
    assert 0.1 <= DEFAULT_RETRY_DELAY <= 10.0
```

### T-4: Session Cleanup Tests
```python
# tests/commands/test_session_cleanup.py
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def old_session(session_storage, tmp_path):
    """Create an old session for cleanup testing."""
    from code_forge.sessions.models import Session

    session = Session(
        title="Old Session",
        created_at=datetime.now() - timedelta(days=60),
    )
    session_storage.save(session)
    return session


async def test_cleanup_command_exists(command_registry):
    """Verify cleanup command is registered."""
    cmd = command_registry.get("session")
    assert cmd is not None
    # Check subcommand or help mentions cleanup


async def test_cleanup_removes_old_sessions(
    session_manager, session_storage, old_session
):
    """Verify cleanup removes sessions older than threshold."""
    # Verify old session exists
    assert session_storage.load(old_session.id) is not None

    # Execute cleanup
    deleted = session_storage.cleanup_old_sessions(max_age_days=30)

    # Verify old session removed
    assert deleted >= 1
    assert session_storage.load(old_session.id) is None


async def test_cleanup_preserves_recent_sessions(
    session_manager, session_storage, session
):
    """Verify cleanup preserves recent sessions."""
    session_id = session.id

    # Execute cleanup
    session_storage.cleanup_old_sessions(max_age_days=30)

    # Verify recent session preserved
    assert session_storage.load(session_id) is not None
```

## Integration Tests

### T-5: Conftest Integration
```python
# tests/integration/test_conftest_fixtures.py

def test_sample_plugin_fixture_works(sample_plugin_dir):
    """Verify sample_plugin_dir fixture works with UTILITY enum."""
    plugin_file = sample_plugin_dir / "test_plugin.py"
    assert plugin_file.exists()

    # Import and verify
    import sys
    sys.path.insert(0, str(sample_plugin_dir))
    try:
        from test_plugin import EchoTool
        from code_forge.tools.base import ToolCategory

        tool = EchoTool()
        assert tool.category == ToolCategory.UTILITY
    finally:
        sys.path.remove(str(sample_plugin_dir))
```

## Regression Tests

### T-6: No Broken Imports
```python
# tests/integration/test_imports.py

def test_all_public_imports():
    """Verify all documented imports work."""
    # These should all work without error
    from code_forge.tools.base import BaseTool, ToolCategory, ToolResult
    from code_forge.tools.file import ReadTool, WriteTool
    from code_forge.permissions import PermissionChecker
    from code_forge.sessions import SessionManager
    from code_forge.hooks import HookRegistry
    from code_forge import __version__


def test_web_module_import_after_cleanup():
    """Verify web module imports work after WebConfig removal."""
    from code_forge.web import WebSearchTool, WebFetchTool
    # Should not raise ImportError
```

## Manual Verification

### M-1: CLI Version Check
```bash
# Verify CLI version works
forge --version
# Should output: forge X.Y.Z
```

### M-2: Cleanup Command Manual Test
```bash
# Create test session, wait, then cleanup
forge
> /session new --title "Test Cleanup"
> /exit

# Wait or manually age the session file, then:
forge
> /session cleanup
# Should show cleanup results
```

## Test Execution Order

1. T-1: Enum tests (verify fix)
2. T-5: Conftest integration (verify fixtures work)
3. T-2: Version tests
4. T-3: Constants tests
5. T-4: Cleanup tests
6. T-6: Import regression
7. M-1, M-2: Manual verification

## Success Criteria

- All unit tests pass
- All integration tests pass
- No new test failures
- Manual verification successful
- Full test suite: `pytest tests/ -v` passes
