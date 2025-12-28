"""Shared test fixtures for Code-Forge tests.

This module provides comprehensive fixtures for:
- Unit tests (temp directories, sample files)
- Integration tests (tool registry, session manager, hooks)
- End-to-end tests (full component setup)
- Performance tests (benchmarking utilities)

Fixture Dependency Hierarchy
============================

The fixtures are organized in a dependency tree. When using a fixture,
all its dependencies are automatically created and cleaned up.

::

    temp_dir (base temporary directory)
    ├── temp_home (isolated HOME with XDG paths)
    │   ├── forge_data_dir (~/.local/share/forge)
    │   │   └── session_storage
    │   │       └── session_manager
    │   │           └── session
    │   ├── forge_config_dir (~/.config/forge)
    │   ├── sample_plugin_dir (~/.forge/plugins/test-plugin)
    │   ├── broken_plugin_dir (~/.forge/plugins/broken-plugin)
    │   └── minimal_config
    │
    └── temp_project (isolated project directory)
        ├── sample_file (sample.py)
        ├── sample_config_file (config.yaml)
        ├── sample_json_file (data.json)
        ├── multiple_python_files (main.py, utils.py, package/)
        ├── execution_context
        ├── minimal_config
        └── git_repo (initialized git repository)
            └── git_repo_with_changes (uncommitted changes)

    tool_registry (singleton-aware)
    └── tool_registry_with_tools (all built-in tools registered)
        └── tool_executor

    hook_registry (singleton-aware, preserves state)

    mock_llm_response (factory function)
    mock_openrouter_client (MagicMock)
    benchmark_timer (Timer class factory)
    event_loop (fresh asyncio loop)

Notes:
- Fixtures with `temp_` prefix create isolated filesystem locations
- Fixtures ending with `_with_*` extend base fixtures with additional setup
- Singleton fixtures (tool_registry, hook_registry, session_manager) preserve
  and restore original state to avoid test pollution
- Async fixtures (session) must be used with pytest-asyncio
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from code_forge.config import CodeForgeConfig
    from code_forge.hooks import HookRegistry
    from code_forge.plugins import PluginManager
    from code_forge.sessions import Session, SessionManager
    from code_forge.tools import ToolExecutor, ToolRegistry


# ============================================================
# Basic Fixtures
# ============================================================


@pytest.fixture
def sample_project_path() -> str:
    """Return a sample project path for testing."""
    return "/test/project"


@pytest.fixture
def sample_session_id() -> str:
    """Return a sample session ID for testing."""
    return "session-abc123"


# ============================================================
# Directory Fixtures
# ============================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests.

    Yields:
        Path to temporary directory that is cleaned up after the test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_home(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary home directory.

    Sets HOME and USERPROFILE environment variables to the temp directory.

    Args:
        temp_dir: Base temporary directory.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        Path to temporary home directory.
    """
    home = temp_dir / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    # Also set XDG directories
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    return home


@pytest.fixture
def temp_project(temp_dir: Path) -> Path:
    """Create a temporary project directory.

    Args:
        temp_dir: Base temporary directory.

    Returns:
        Path to temporary project directory.
    """
    project = temp_dir / "project"
    project.mkdir(parents=True)
    return project


@pytest.fixture
def forge_data_dir(temp_home: Path) -> Path:
    """Create Code-Forge data directory.

    Args:
        temp_home: Temporary home directory.

    Returns:
        Path to Code-Forge data directory.
    """
    data_dir = temp_home / ".local" / "share" / "forge"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def forge_config_dir(temp_home: Path) -> Path:
    """Create Code-Forge config directory.

    Args:
        temp_home: Temporary home directory.

    Returns:
        Path to Code-Forge config directory.
    """
    config_dir = temp_home / ".config" / "forge"
    config_dir.mkdir(parents=True)
    return config_dir


# ============================================================
# File Fixtures
# ============================================================


@pytest.fixture
def sample_file(temp_project: Path) -> Path:
    """Create a sample Python file for testing.

    Args:
        temp_project: Temporary project directory.

    Returns:
        Path to sample Python file.
    """
    file_path = temp_project / "sample.py"
    file_path.write_text('''"""Sample module for testing."""


def hello(name: str) -> str:
    """Say hello to someone.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Sum of a and b.
    """
    return a + b


class Calculator:
    """Simple calculator class."""

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
''')
    return file_path


@pytest.fixture
def sample_config_file(temp_project: Path) -> Path:
    """Create a sample config file.

    Args:
        temp_project: Temporary project directory.

    Returns:
        Path to sample config file.
    """
    config_path = temp_project / "config.yaml"
    config_path.write_text("""
# Sample configuration
model:
  default: "anthropic/claude-3-sonnet"
  max_tokens: 4096

display:
  theme: dark
""")
    return config_path


@pytest.fixture
def sample_json_file(temp_project: Path) -> Path:
    """Create a sample JSON file.

    Args:
        temp_project: Temporary project directory.

    Returns:
        Path to sample JSON file.
    """
    json_path = temp_project / "data.json"
    json_path.write_text('{"name": "test", "values": [1, 2, 3]}')
    return json_path


@pytest.fixture
def multiple_python_files(temp_project: Path) -> list[Path]:
    """Create multiple Python files for testing.

    Args:
        temp_project: Temporary project directory.

    Returns:
        List of paths to created files.
    """
    files = []

    # Main module
    main = temp_project / "main.py"
    main.write_text('''"""Main module."""
from utils import helper

def main():
    helper()

if __name__ == "__main__":
    main()
''')
    files.append(main)

    # Utils module
    utils = temp_project / "utils.py"
    utils.write_text('''"""Utilities module."""

def helper():
    """Helper function."""
    return "helped"

def old_function():
    """Old function to be replaced."""
    pass
''')
    files.append(utils)

    # Subpackage
    pkg = temp_project / "package"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('"""Package init."""\n')
    files.append(pkg / "__init__.py")

    module = pkg / "module.py"
    module.write_text('''"""Subpackage module."""

class MyClass:
    """Sample class."""

    def method(self):
        """Sample method."""
        pass
''')
    files.append(module)

    return files


# ============================================================
# Git Fixtures
# ============================================================


@pytest.fixture
def git_repo(temp_project: Path) -> Path:
    """Initialize a git repository in the temp project.

    Creates a git repository with:
    - Initial commit with README.md
    - User configured (test@test.com / Test User)

    Args:
        temp_project: Temporary project directory.

    Returns:
        Path to git repository.
    """
    # Initialize repo
    subprocess.run(
        ["git", "init"],
        cwd=temp_project,
        check=True,
        capture_output=True,
    )

    # Configure user
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_project,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    readme = temp_project / "README.md"
    readme.write_text("# Test Project\n\nA test project for integration tests.\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=temp_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_project,
        check=True,
        capture_output=True,
    )

    return temp_project


@pytest.fixture
def git_repo_with_changes(git_repo: Path) -> Path:
    """Create a git repo with uncommitted changes.

    Args:
        git_repo: Git repository path.

    Returns:
        Path to git repository with changes.
    """
    # Modify existing file
    readme = git_repo / "README.md"
    readme.write_text("# Test Project\n\nUpdated content.\n")

    # Add new file
    new_file = git_repo / "new_file.py"
    new_file.write_text("# New file\nprint('hello')\n")

    return git_repo


# ============================================================
# Tool System Fixtures
# ============================================================


@pytest.fixture
def tool_registry() -> Generator["ToolRegistry", None, None]:
    """Create a fresh tool registry.

    Yields:
        Fresh ToolRegistry instance.
    """
    from code_forge.tools import ToolRegistry

    registry = ToolRegistry()  # Singleton via __new__
    # Store original tools
    original_tools = dict(registry._tools)

    yield registry

    # Restore original state
    registry._tools.clear()
    registry._tools.update(original_tools)


@pytest.fixture
def tool_registry_with_tools(tool_registry: "ToolRegistry") -> "ToolRegistry":
    """Create a tool registry with all built-in tools registered.

    Args:
        tool_registry: Base tool registry.

    Returns:
        Registry with tools registered.
    """
    from code_forge.tools import register_all_tools

    # Only register if not already registered (singleton may have tools)
    if not tool_registry.exists("Read"):
        register_all_tools()
    return tool_registry


@pytest.fixture
def tool_executor(tool_registry_with_tools: "ToolRegistry") -> "ToolExecutor":
    """Create a tool executor with all tools.

    Args:
        tool_registry_with_tools: Registry with tools.

    Returns:
        ToolExecutor instance.
    """
    from code_forge.tools import ToolExecutor

    return ToolExecutor(tool_registry_with_tools)


@pytest.fixture
def execution_context(temp_project: Path):
    """Create an execution context for tools.

    Args:
        temp_project: Temporary project directory.

    Returns:
        ExecutionContext instance.
    """
    from code_forge.tools import ExecutionContext

    return ExecutionContext(
        working_dir=str(temp_project),
        timeout=30,
    )


# ============================================================
# Session Fixtures
# ============================================================


@pytest.fixture
def session_storage(forge_data_dir: Path):
    """Create a session storage instance.

    Args:
        forge_data_dir: Code-Forge data directory.

    Returns:
        SessionStorage instance.
    """
    from code_forge.sessions import SessionStorage

    return SessionStorage(forge_data_dir / "sessions")


@pytest.fixture
def session_manager(session_storage, monkeypatch) -> Generator["SessionManager", None, None]:
    """Create a session manager instance.

    Args:
        session_storage: Session storage instance.
        monkeypatch: Pytest monkeypatch fixture.

    Yields:
        SessionManager instance.
    """
    from code_forge.sessions import SessionManager

    # Reset singleton and create fresh instance with custom storage
    SessionManager._instance = None
    manager = SessionManager(storage=session_storage)
    SessionManager._instance = manager
    yield manager

    # Cleanup
    SessionManager._instance = None


@pytest.fixture
async def session(session_manager: "SessionManager") -> AsyncGenerator["Session", None]:
    """Create a test session.

    Args:
        session_manager: Session manager instance.

    Yields:
        Session instance.
    """
    session = session_manager.create(title="Test Session")
    yield session

    # Cleanup
    try:
        session_manager.close()
    except Exception:
        pass


# ============================================================
# Hook Fixtures
# ============================================================


@pytest.fixture
def hook_registry() -> Generator["HookRegistry", None, None]:
    """Create a fresh hook registry.

    Yields:
        Fresh HookRegistry instance.
    """
    from code_forge.hooks import HookRegistry

    registry = HookRegistry.get_instance()
    # Store original hooks
    original_hooks = list(registry._hooks)

    yield registry

    # Restore original state
    registry._hooks.clear()
    registry._hooks.extend(original_hooks)


# ============================================================
# Plugin Fixtures
# ============================================================


@pytest.fixture
def sample_plugin_dir(temp_home: Path) -> Path:
    """Create a sample plugin directory with a test plugin.

    Args:
        temp_home: Temporary home directory.

    Returns:
        Path to plugin directory.
    """
    plugin_dir = temp_home / ".forge" / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True)

    # Create manifest
    manifest = plugin_dir / "plugin.yaml"
    manifest.write_text("""
name: test-plugin
version: 1.0.0
description: Test plugin for integration tests
author: Test Author
entry_point: test_plugin:TestPlugin
capabilities:
  tools: true
  commands: false
  hooks: false
""")

    # Create plugin module
    module = plugin_dir / "test_plugin.py"
    module.write_text('''"""Test plugin for integration tests."""

from code_forge.plugins import Plugin, PluginMetadata, PluginCapabilities
from code_forge.tools import BaseTool, ToolParameter, ToolResult, ToolCategory


class EchoTool(BaseTool):
    """Echo tool that returns input."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo the input message back"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="message",
                type="string",
                description="Message to echo",
                required=True,
            )
        ]

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message", "")
        return ToolResult(
            success=True,
            output=f"Echo: {message}",
        )


class TestPlugin(Plugin):
    """Test plugin implementation."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin for integration tests",
            author="Test Author",
        )

    @property
    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(tools=True)

    def register_tools(self) -> list:
        return [EchoTool()]
''')

    return plugin_dir


@pytest.fixture
def broken_plugin_dir(temp_home: Path) -> Path:
    """Create a broken plugin that fails to load.

    Args:
        temp_home: Temporary home directory.

    Returns:
        Path to broken plugin directory.
    """
    plugin_dir = temp_home / ".forge" / "plugins" / "broken-plugin"
    plugin_dir.mkdir(parents=True)

    # Create manifest
    manifest = plugin_dir / "plugin.yaml"
    manifest.write_text("""
name: broken-plugin
version: 1.0.0
description: Broken plugin that fails to load
entry_point: broken:BrokenPlugin
""")

    # Create broken module
    module = plugin_dir / "broken.py"
    module.write_text("""
# This module intentionally raises an error on import
raise ImportError("Intentional error for testing")
""")

    return plugin_dir


# ============================================================
# Mock Fixtures
# ============================================================


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response factory.

    Returns:
        Factory function for creating mock responses.
    """

    def _create(content: str, tool_calls: list | None = None):
        """Create a mock LLM response.

        Args:
            content: Response content.
            tool_calls: Optional list of tool calls.

        Returns:
            Mock AIMessage.
        """
        from langchain_core.messages import AIMessage

        return AIMessage(
            content=content,
            tool_calls=tool_calls or [],
        )

    return _create


@pytest.fixture
def mock_openrouter_client():
    """Create a mock OpenRouter client.

    Returns:
        Mock OpenRouterClient.
    """
    mock = MagicMock()
    mock.complete = AsyncMock()
    mock.stream = AsyncMock()
    return mock


# ============================================================
# Configuration Fixtures
# ============================================================


@pytest.fixture
def minimal_config(temp_home: Path, temp_project: Path) -> "CodeForgeConfig":
    """Create a minimal configuration.

    Args:
        temp_home: Temporary home directory.
        temp_project: Temporary project directory.

    Returns:
        Minimal CodeForgeConfig instance.
    """
    from code_forge.config import CodeForgeConfig

    return CodeForgeConfig()


# ============================================================
# Performance Testing Fixtures
# ============================================================


@pytest.fixture
def benchmark_timer():
    """Create a benchmark timer utility.

    Returns:
        Timer class for benchmarking.
    """
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()
            self.elapsed = self.end_time - self.start_time

    return Timer


# ============================================================
# Async Utilities
# ============================================================


@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for async tests.

    This fixture ensures each test gets a fresh event loop.
    Uses a policy-based approach to work around WSL source code inspection issues.

    Yields:
        Event loop instance.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)


# Configure pytest-asyncio to use our event_loop fixture
def pytest_configure(config):
    """Configure pytest for async tests."""
    # Register custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow running")


@pytest.fixture(scope="session")
def session_event_loop():
    """Session-scoped event loop for fixtures that need it.

    Yields:
        Event loop instance that persists for the test session.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)
