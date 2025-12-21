"""E2E test fixtures and utilities."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def e2e_temp_dir() -> Generator[Path, None, None]:
    """Create isolated temp directory for e2e tests."""
    with tempfile.TemporaryDirectory(prefix="forge-e2e-") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def e2e_home(e2e_temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create isolated home directory for e2e tests."""
    home = e2e_temp_dir / "home"
    home.mkdir(parents=True)

    # Set environment variables
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))

    # Create forge directories
    forge_config = home / ".config" / "forge"
    forge_config.mkdir(parents=True)
    forge_data = home / ".local" / "share" / "forge"
    forge_data.mkdir(parents=True)

    return home


@pytest.fixture
def e2e_project(e2e_temp_dir: Path) -> Path:
    """Create isolated project directory for e2e tests."""
    project = e2e_temp_dir / "project"
    project.mkdir(parents=True)
    return project


@pytest.fixture
def e2e_forge_config(e2e_home: Path) -> Path:
    """Create minimal forge configuration for e2e tests."""
    config_dir = e2e_home / ".config" / "forge"
    config_file = config_dir / "settings.json"

    # Minimal config with mock API key
    config_file.write_text("""{
  "llm": {
    "api_key": "test-api-key-for-e2e-tests",
    "default_model": "anthropic/claude-3-sonnet"
  },
  "display": {
    "theme": "dark"
  }
}""")

    return config_file


@pytest.fixture
def mock_openrouter_for_e2e():
    """Mock OpenRouter API for e2e tests to avoid real API calls."""
    with patch("code_forge.llm.client.OpenRouterClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful response
        async def mock_complete(*args, **kwargs):
            from langchain_core.messages import AIMessage
            return AIMessage(content="E2E test response", tool_calls=[])

        async def mock_stream(*args, **kwargs):
            from langchain_core.messages import AIMessage
            yield {"content": "E", "done": False}
            yield {"content": "2", "done": False}
            yield {"content": "E", "done": False}
            yield {"content": " ", "done": False}
            yield {"content": "test", "done": False}
            yield {"done": True, "message": AIMessage(content="E2E test", tool_calls=[])}

        mock_client.complete = AsyncMock(side_effect=mock_complete)
        mock_client.stream = AsyncMock(side_effect=mock_stream)

        yield mock_client


@pytest.fixture
def forge_runner(e2e_home: Path, e2e_project: Path, e2e_forge_config: Path):
    """Create utility for running forge CLI commands in e2e tests."""

    class ForgeRunner:
        """Utility for running forge CLI in e2e tests."""

        def __init__(self, home: Path, project: Path):
            self.home = home
            self.project = project
            self.env = os.environ.copy()
            self.env["HOME"] = str(home)
            self.env["USERPROFILE"] = str(home)
            self.env["XDG_CONFIG_HOME"] = str(home / ".config")
            self.env["XDG_DATA_HOME"] = str(home / ".local" / "share")

        def run(
            self,
            args: list[str] | None = None,
            input_text: str | None = None,
            cwd: Path | None = None,
            timeout: int = 30,
            check: bool = True,
        ) -> subprocess.CompletedProcess:
            """Run forge CLI command.

            Args:
                args: Command line arguments
                input_text: Text to pipe to stdin
                cwd: Working directory (defaults to project dir)
                timeout: Timeout in seconds
                check: Raise on non-zero exit

            Returns:
                CompletedProcess result
            """
            cmd = ["forge"] + (args or [])

            result = subprocess.run(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                cwd=cwd or self.project,
                env=self.env,
                timeout=timeout,
                check=check,
            )

            return result

        def run_interactive(
            self,
            commands: list[str],
            cwd: Path | None = None,
            timeout: int = 30,
        ) -> subprocess.CompletedProcess:
            """Run forge in interactive mode with commands.

            Args:
                commands: List of commands to execute
                cwd: Working directory
                timeout: Timeout in seconds

            Returns:
                CompletedProcess result
            """
            # Join commands with newlines and add exit
            input_text = "\n".join(commands + ["/exit"])

            return self.run(
                args=[],
                input_text=input_text,
                cwd=cwd,
                timeout=timeout,
                check=False,  # Interactive may have non-zero exit
            )

    return ForgeRunner(e2e_home, e2e_project)


@pytest.fixture
def sample_python_project(e2e_project: Path) -> Path:
    """Create a sample Python project for e2e tests."""
    # Create package structure
    src = e2e_project / "src"
    src.mkdir()

    pkg = src / "mypackage"
    pkg.mkdir()

    # __init__.py
    (pkg / "__init__.py").write_text('''"""My package."""

__version__ = "1.0.0"

from .core import hello

__all__ = ["hello", "__version__"]
''')

    # core.py
    (pkg / "core.py").write_text('''"""Core functionality."""


def hello(name: str) -> str:
    """Greet someone.

    Args:
        name: Name to greet

    Returns:
        Greeting message
    """
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum
    """
    return a + b
''')

    # utils.py
    (pkg / "utils.py").write_text('''"""Utility functions."""


def format_output(text: str) -> str:
    """Format output text.

    Args:
        text: Text to format

    Returns:
        Formatted text
    """
    return f"[OUTPUT] {text}"
''')

    # tests
    tests = e2e_project / "tests"
    tests.mkdir()

    (tests / "test_core.py").write_text('''"""Core tests."""
import pytest
from mypackage.core import hello, add


def test_hello():
    assert hello("World") == "Hello, World!"


def test_add():
    assert add(1, 2) == 3
    assert add(0, 0) == 0
''')

    # README
    (e2e_project / "README.md").write_text('''# My Package

A sample Python package for testing.

## Installation

```bash
pip install -e .
```

## Usage

```python
from mypackage import hello
print(hello("World"))
```
''')

    # pyproject.toml
    (e2e_project / "pyproject.toml").write_text('''[project]
name = "mypackage"
version = "1.0.0"
description = "Sample package"

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
''')

    return e2e_project


@pytest.fixture
def git_project(sample_python_project: Path) -> Path:
    """Create git repository from sample project."""
    subprocess.run(
        ["git", "init"],
        cwd=sample_python_project,
        check=True,
        capture_output=True,
    )

    subprocess.run(
        ["git", "config", "user.email", "test@e2e.com"],
        cwd=sample_python_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=sample_python_project,
        check=True,
        capture_output=True,
    )

    subprocess.run(
        ["git", "add", "."],
        cwd=sample_python_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=sample_python_project,
        check=True,
        capture_output=True,
    )

    return sample_python_project
