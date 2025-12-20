"""Tests for GrepTool."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_forge.tools.base import ExecutionContext
from code_forge.tools.file.grep import GrepTool


@pytest.fixture
def grep_tool() -> GrepTool:
    """Create a GrepTool instance."""
    return GrepTool()


@pytest.fixture
def context(tmp_path: Path) -> ExecutionContext:
    """Create an execution context."""
    return ExecutionContext(working_dir=str(tmp_path))


@pytest.fixture
def sample_codebase(tmp_path: Path) -> Path:
    """Create a sample codebase for searching."""
    # Python files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("""def main():
    print("Hello, World!")
    return 0

def helper():
    print("Helper function")
""")
    (tmp_path / "src" / "utils.py").write_text("""import logging

logger = logging.getLogger(__name__)

def log_error(message):
    logger.error(message)

def log_info(message):
    logger.info(message)
""")

    # JavaScript files
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "app.js").write_text("""function main() {
    console.log("Hello, World!");
}

function helper() {
    console.log("Helper");
}
""")

    # Config file
    (tmp_path / "config.json").write_text('{"debug": true, "port": 8080}')

    return tmp_path


class TestGrepToolProperties:
    """Test GrepTool properties."""

    def test_name(self, grep_tool: GrepTool) -> None:
        assert grep_tool.name == "Grep"

    def test_description(self, grep_tool: GrepTool) -> None:
        assert "regex" in grep_tool.description.lower()
        assert "ripgrep" in grep_tool.description.lower()

    def test_category(self, grep_tool: GrepTool) -> None:
        from code_forge.tools.base import ToolCategory

        assert grep_tool.category == ToolCategory.FILE

    def test_parameters(self, grep_tool: GrepTool) -> None:
        params = grep_tool.parameters
        param_names = [p.name for p in params]
        assert "pattern" in param_names
        assert "path" in param_names
        assert "output_mode" in param_names
        assert "-i" in param_names
        assert "-A" in param_names
        assert "-B" in param_names
        assert "-C" in param_names


class TestGrepToolFilesWithMatchesMode:
    """Test files_with_matches output mode (default)."""

    @pytest.mark.asyncio
    async def test_find_files_with_pattern(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context, pattern="Hello", path=str(sample_codebase)
        )
        assert result.success
        assert "main.py" in result.output
        assert "app.js" in result.output
        # utils.py doesn't have "Hello"
        assert "utils.py" not in result.output

    @pytest.mark.asyncio
    async def test_regex_pattern(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context, pattern="def\\s+\\w+", path=str(sample_codebase)
        )
        assert result.success
        assert "main.py" in result.output
        assert "utils.py" in result.output


class TestGrepToolContentMode:
    """Test content output mode."""

    @pytest.mark.asyncio
    async def test_content_mode_shows_lines(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="Hello",
            path=str(sample_codebase),
            output_mode="content",
        )
        assert result.success
        assert "Hello, World!" in result.output

    @pytest.mark.asyncio
    async def test_content_mode_with_line_numbers(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="Hello",
            path=str(sample_codebase),
            output_mode="content",
            **{"-n": True},
        )
        assert result.success
        # Line numbers should be included
        assert ":2:" in result.output or "2:" in result.output

    @pytest.mark.asyncio
    async def test_content_mode_without_line_numbers(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="Hello",
            path=str(sample_codebase),
            output_mode="content",
            **{"-n": False},
        )
        assert result.success
        assert "Hello, World!" in result.output


class TestGrepToolCountMode:
    """Test count output mode."""

    @pytest.mark.asyncio
    async def test_count_mode(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="log",
            path=str(sample_codebase),
            output_mode="count",
        )
        assert result.success
        # utils.py should have multiple occurrences
        assert "utils.py" in result.output


class TestGrepToolContextLines:
    """Test context line options."""

    @pytest.mark.asyncio
    async def test_after_context(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="def main",
            path=str(sample_codebase),
            output_mode="content",
            **{"-A": 2},
        )
        assert result.success
        # Should include lines after the match
        assert "print" in result.output

    @pytest.mark.asyncio
    async def test_before_context(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="return 0",
            path=str(sample_codebase),
            output_mode="content",
            **{"-B": 2},
        )
        assert result.success
        # Should include lines before the match
        assert "print" in result.output

    @pytest.mark.asyncio
    async def test_both_context(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="return 0",
            path=str(sample_codebase),
            output_mode="content",
            **{"-C": 2},
        )
        assert result.success


class TestGrepToolCaseInsensitive:
    """Test case-insensitive search."""

    @pytest.mark.asyncio
    async def test_case_sensitive_default(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context, pattern="HELLO", path=str(sample_codebase)
        )
        assert result.success
        assert "No matches" in result.output

    @pytest.mark.asyncio
    async def test_case_insensitive_search(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="HELLO",
            path=str(sample_codebase),
            **{"-i": True},
        )
        assert result.success
        assert "main.py" in result.output


class TestGrepToolFileFiltering:
    """Test file type and glob filtering."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "glob_pattern,expected_file,excluded_file",
        [
            ("*.js", "app.js", "main.py"),
            ("*.py", "main.py", "app.js"),
            ("*.json", "config.json", "main.py"),
            ("src/*.py", "main.py", "app.js"),
        ]
    )
    async def test_glob_filter(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path,
        glob_pattern: str, expected_file: str, excluded_file: str
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="\\w+",  # Match any word
            path=str(sample_codebase),
            glob=glob_pattern,
        )
        assert result.success
        assert expected_file in result.output
        assert excluded_file not in result.output

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "file_type,expected_pattern,expected_file",
        [
            ("py", "def", "main.py"),
            ("js", "function", "app.js"),
            ("json", "debug", "config.json"),
        ]
    )
    async def test_type_filter(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path,
        file_type: str, expected_pattern: str, expected_file: str
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern=expected_pattern,
            path=str(sample_codebase),
            type=file_type,
        )
        assert result.success
        assert expected_file in result.output


class TestGrepToolSingleFile:
    """Test searching a single file."""

    @pytest.mark.asyncio
    async def test_search_single_file(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="Hello",
            path=str(sample_codebase / "src" / "main.py"),
        )
        assert result.success
        assert "main.py" in result.output


class TestGrepToolNoMatches:
    """Test behavior when no matches found."""

    @pytest.mark.asyncio
    async def test_no_matches(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context, pattern="xyznonexistent", path=str(sample_codebase)
        )
        assert result.success
        assert "no matches" in result.output.lower()


class TestGrepToolInvalidPattern:
    """Test invalid regex pattern handling."""

    @pytest.mark.asyncio
    async def test_invalid_regex(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context, pattern="[invalid", path=str(sample_codebase)
        )
        assert not result.success
        assert isinstance(result.error, str)
        assert "invalid" in result.error.lower() or "error" in result.error.lower()


class TestGrepToolPagination:
    """Test offset and limit functionality."""

    @pytest.mark.asyncio
    async def test_head_limit(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="\\w+",  # Matches everything
            path=str(sample_codebase),
            head_limit=2,
        )
        assert result.success
        # Should be limited
        assert result.metadata["returned_matches"] <= 2

    @pytest.mark.asyncio
    async def test_offset(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="\\w+",
            path=str(sample_codebase),
            offset=1,
            head_limit=100,
        )
        assert result.success
        # Should skip first result
        assert result.metadata["offset"] == 1


class TestGrepToolDefaultPath:
    """Test using default working directory."""

    @pytest.mark.asyncio
    async def test_uses_working_dir_when_no_path(
        self, grep_tool: GrepTool, sample_codebase: Path
    ) -> None:
        context = ExecutionContext(working_dir=str(sample_codebase))
        result = await grep_tool.execute(
            context, pattern="Hello"
        )
        assert result.success
        assert result.metadata["total_matches"] >= 2


class TestGrepToolBinaryFiles:
    """Test binary file handling."""

    @pytest.mark.asyncio
    async def test_skips_binary_files(
        self, grep_tool: GrepTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        # Create a binary file with null bytes
        (tmp_path / "binary.dat").write_bytes(b"\x00\x01\x02hello\x00")
        (tmp_path / "text.txt").write_text("hello world")

        result = await grep_tool.execute(
            context, pattern="hello", path=str(tmp_path)
        )
        assert result.success
        assert "text.txt" in result.output
        assert "binary.dat" not in result.output


class TestGrepToolOutputModes:
    """Test different output modes."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "output_mode,expected_in_output",
        [
            ("files_with_matches", "main.py"),
            ("content", "Hello, World!"),
            ("count", "main.py"),
        ]
    )
    async def test_output_modes(
        self, grep_tool: GrepTool, context: ExecutionContext, sample_codebase: Path,
        output_mode: str, expected_in_output: str
    ) -> None:
        result = await grep_tool.execute(
            context,
            pattern="Hello",
            path=str(sample_codebase),
            output_mode=output_mode,
        )
        assert result.success
        assert expected_in_output in result.output
