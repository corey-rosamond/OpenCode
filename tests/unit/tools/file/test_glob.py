"""Tests for GlobTool."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from code_forge.tools.base import ExecutionContext
from code_forge.tools.file.glob import GlobTool


@pytest.fixture
def glob_tool() -> GlobTool:
    """Create a GlobTool instance."""
    return GlobTool()


@pytest.fixture
def context(tmp_path: Path) -> ExecutionContext:
    """Create an execution context."""
    return ExecutionContext(working_dir=str(tmp_path))


@pytest.fixture
def sample_directory(tmp_path: Path) -> Path:
    """Create a sample directory structure."""
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("main code")
    (tmp_path / "src" / "utils.py").write_text("utils code")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("tests")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("readme")
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "setup.py").write_text("setup")
    return tmp_path


class TestGlobToolProperties:
    """Test GlobTool properties."""

    def test_name(self, glob_tool: GlobTool) -> None:
        assert glob_tool.name == "Glob"

    def test_description(self, glob_tool: GlobTool) -> None:
        assert "pattern" in glob_tool.description.lower()
        assert "**/*.js" in glob_tool.description

    def test_category(self, glob_tool: GlobTool) -> None:
        from code_forge.tools.base import ToolCategory

        assert glob_tool.category == ToolCategory.FILE

    def test_parameters(self, glob_tool: GlobTool) -> None:
        params = glob_tool.parameters
        param_names = [p.name for p in params]
        assert "pattern" in param_names
        assert "path" in param_names


class TestGlobToolBasicPatterns:
    """Test basic glob patterns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "pattern,expected_files,expected_count",
        [
            ("**/*.py", ["main.py", "utils.py", "test_main.py", "setup.py"], 4),
            ("src/*.py", ["main.py", "utils.py"], 2),
            ("**/README.md", ["README.md"], 1),
            ("**/*.json", ["config.json"], 1),
            ("**/*.md", ["README.md"], 1),
        ]
    )
    async def test_glob_patterns(
        self, glob_tool: GlobTool, context: ExecutionContext, sample_directory: Path,
        pattern: str, expected_files: list, expected_count: int
    ) -> None:
        result = await glob_tool.execute(
            context, pattern=pattern, path=str(sample_directory)
        )
        assert result.success
        for expected_file in expected_files:
            assert expected_file in result.output
        assert result.metadata["count"] == expected_count


class TestGlobToolDefaultExcludes:
    """Test default exclude patterns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exclude_dir,pattern,file_in_excluded,file_in_src",
        [
            ("node_modules", "**/*.js", "node_modules/pkg/index.js", "src/app.js"),
            (".venv", "**/*.py", ".venv/lib/python.py", "app.py"),
            (".git", "**/*", ".git/config", "file.txt"),
            ("__pycache__", "**/*", "__pycache__/module.cpython-311.pyc", "module.py"),
        ]
    )
    async def test_excluded_directories(
        self, glob_tool: GlobTool, context: ExecutionContext, tmp_path: Path,
        exclude_dir: str, pattern: str, file_in_excluded: str, file_in_src: str
    ) -> None:
        # Create files in excluded directory
        excluded_file = tmp_path / file_in_excluded
        excluded_file.parent.mkdir(parents=True, exist_ok=True)
        if file_in_excluded.endswith(".pyc"):
            excluded_file.write_bytes(b"")
        else:
            excluded_file.write_text("content")

        # Create normal file
        normal_file = tmp_path / file_in_src
        normal_file.parent.mkdir(parents=True, exist_ok=True)
        normal_file.write_text("content")

        result = await glob_tool.execute(
            context, pattern=pattern, path=str(tmp_path)
        )
        assert result.success
        assert exclude_dir not in result.output
        assert file_in_src.split('/')[-1] in result.output

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "extension",
        [".pyc", ".pyo", ".so", ".dylib"]
    )
    async def test_exclude_compiled_files(
        self, glob_tool: GlobTool, context: ExecutionContext, tmp_path: Path, extension: str
    ) -> None:
        (tmp_path / "module.py").write_text("code")
        (tmp_path / f"module{extension}").write_bytes(b"compiled")

        result = await glob_tool.execute(
            context, pattern="**/*", path=str(tmp_path)
        )
        assert result.success
        assert "module.py" in result.output
        assert extension not in result.output


class TestGlobToolSorting:
    """Test modification time sorting."""

    @pytest.mark.asyncio
    async def test_sorted_by_modification_time(
        self, glob_tool: GlobTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        # Create files with different modification times
        old_file = tmp_path / "old.txt"
        old_file.write_text("old content")
        time.sleep(0.1)
        new_file = tmp_path / "new.txt"
        new_file.write_text("new content")

        result = await glob_tool.execute(
            context, pattern="*.txt", path=str(tmp_path)
        )
        assert result.success
        # Newer file should come first
        lines = result.output.strip().split("\n")
        assert "new.txt" in lines[0]
        assert "old.txt" in lines[1]


class TestGlobToolNoMatches:
    """Test behavior when no files match."""

    @pytest.mark.asyncio
    async def test_no_matches(
        self, glob_tool: GlobTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        (tmp_path / "file.txt").write_text("content")
        result = await glob_tool.execute(
            context, pattern="**/*.xyz", path=str(tmp_path)
        )
        assert result.success
        assert "no matches" in result.output.lower()
        assert result.metadata["count"] == 0


class TestGlobToolErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_directory(
        self, glob_tool: GlobTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        result = await glob_tool.execute(
            context, pattern="*.txt", path=str(tmp_path / "nonexistent")
        )
        assert not result.success
        assert isinstance(result.error, str)
        assert "not found" in result.error.lower()


class TestGlobToolResultLimit:
    """Test result limiting."""

    @pytest.mark.asyncio
    async def test_results_limited(
        self, glob_tool: GlobTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        # Create many files
        for i in range(10):
            (tmp_path / f"file{i:03d}.txt").write_text(f"content {i}")

        result = await glob_tool.execute(
            context, pattern="*.txt", path=str(tmp_path)
        )
        assert result.success
        assert result.metadata["count"] == 10


class TestGlobToolDefaultPath:
    """Test using default working directory."""

    @pytest.mark.asyncio
    async def test_uses_working_dir_when_no_path(
        self, glob_tool: GlobTool, sample_directory: Path
    ) -> None:
        context = ExecutionContext(working_dir=str(sample_directory))
        result = await glob_tool.execute(
            context, pattern="**/*.py"
        )
        assert result.success
        assert result.metadata["count"] == 4
        assert result.metadata["base_path"] == str(sample_directory)
