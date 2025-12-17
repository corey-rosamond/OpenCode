"""Tests for EditTool."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_forge.tools.base import ExecutionContext
from code_forge.tools.file.edit import EditTool


@pytest.fixture
def edit_tool() -> EditTool:
    """Create an EditTool instance."""
    return EditTool()


@pytest.fixture
def context(tmp_path: Path) -> ExecutionContext:
    """Create an execution context."""
    return ExecutionContext(working_dir=str(tmp_path))


@pytest.fixture
def dry_run_context(tmp_path: Path) -> ExecutionContext:
    """Create a dry-run execution context."""
    return ExecutionContext(working_dir=str(tmp_path), dry_run=True)


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample file for editing."""
    file_path = tmp_path / "sample.py"
    file_path.write_text("""def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye, World!")
""")
    return file_path


class TestEditToolProperties:
    """Test EditTool properties."""

    def test_name(self, edit_tool: EditTool) -> None:
        assert edit_tool.name == "Edit"

    def test_description(self, edit_tool: EditTool) -> None:
        assert "replace" in edit_tool.description.lower()
        assert "old_string" in edit_tool.description

    def test_category(self, edit_tool: EditTool) -> None:
        from code_forge.tools.base import ToolCategory

        assert edit_tool.category == ToolCategory.FILE

    def test_parameters(self, edit_tool: EditTool) -> None:
        params = edit_tool.parameters
        param_names = [p.name for p in params]
        assert "file_path" in param_names
        assert "old_string" in param_names
        assert "new_string" in param_names
        assert "replace_all" in param_names


class TestEditToolBasicOperations:
    """Test basic edit operations."""

    @pytest.mark.asyncio
    async def test_simple_replacement(
        self, edit_tool: EditTool, context: ExecutionContext, sample_file: Path
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path=str(sample_file),
            old_string='print("Hello, World!")',
            new_string='print("Hi, World!")',
        )
        assert result.success
        content = sample_file.read_text()
        assert 'print("Hi, World!")' in content
        assert 'print("Hello, World!")' not in content
        assert result.metadata["replacements"] == 1

    @pytest.mark.asyncio
    async def test_multiline_replacement(
        self, edit_tool: EditTool, context: ExecutionContext, sample_file: Path
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path=str(sample_file),
            old_string="""def hello():
    print("Hello, World!")""",
            new_string="""def greet(name):
    print(f"Hello, {name}!")""",
        )
        assert result.success
        content = sample_file.read_text()
        assert "def greet(name):" in content
        assert "def hello():" not in content

    @pytest.mark.asyncio
    async def test_whitespace_preservation(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "test.py"
        file_path.write_text("    def foo():\n        pass\n")
        result = await edit_tool.execute(
            context,
            file_path=str(file_path),
            old_string="    def foo():",
            new_string="    def bar():",
        )
        assert result.success
        content = file_path.read_text()
        assert "    def bar():" in content
        # Verify indentation is preserved
        assert content.startswith("    def bar():")


class TestEditToolReplaceAll:
    """Test replace_all functionality."""

    @pytest.mark.asyncio
    async def test_replace_all_occurrences(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("foo bar foo baz foo")
        result = await edit_tool.execute(
            context,
            file_path=str(file_path),
            old_string="foo",
            new_string="qux",
            replace_all=True,
        )
        assert result.success
        content = file_path.read_text()
        assert "foo" not in content
        assert content == "qux bar qux baz qux"
        assert result.metadata["replacements"] == 3

    @pytest.mark.asyncio
    async def test_multiple_occurrences_without_replace_all_fails(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("foo bar foo baz foo")
        result = await edit_tool.execute(
            context,
            file_path=str(file_path),
            old_string="foo",
            new_string="qux",
        )
        assert not result.success
        assert isinstance(result.error, str) and len(result.error) > 0
        assert "3 times" in result.error or "found 3" in result.error.lower()
        # File should be unchanged
        assert file_path.read_text() == "foo bar foo baz foo"


class TestEditToolDryRun:
    """Test dry-run mode.

    Note: Dry run is handled in BaseTool.execute() before _execute() is called,
    so it returns a generic message with the kwargs.
    """

    @pytest.mark.asyncio
    async def test_dry_run_single_replacement(
        self, edit_tool: EditTool, dry_run_context: ExecutionContext, sample_file: Path
    ) -> None:
        original_content = sample_file.read_text()
        result = await edit_tool.execute(
            dry_run_context,
            file_path=str(sample_file),
            old_string='print("Hello, World!")',
            new_string='print("Hi, World!")',
        )
        assert result.success
        assert "Dry Run" in result.output
        assert "Edit" in result.output  # Tool name in output
        # File should be unchanged
        assert sample_file.read_text() == original_content
        assert result.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_replace_all(
        self, edit_tool: EditTool, dry_run_context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("foo bar foo")
        result = await edit_tool.execute(
            dry_run_context,
            file_path=str(file_path),
            old_string="foo",
            new_string="qux",
            replace_all=True,
        )
        assert result.success
        assert "Dry Run" in result.output
        assert "Edit" in result.output  # Tool name in output
        # File should be unchanged
        assert file_path.read_text() == "foo bar foo"
        assert result.metadata.get("dry_run") is True


class TestEditToolErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_file_not_found(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path=str(tmp_path / "nonexistent.txt"),
            old_string="foo",
            new_string="bar",
        )
        assert not result.success
        assert isinstance(result.error, str) and len(result.error) > 0
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_old_string_not_found(
        self, edit_tool: EditTool, context: ExecutionContext, sample_file: Path
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path=str(sample_file),
            old_string="nonexistent string",
            new_string="replacement",
        )
        assert not result.success
        assert isinstance(result.error, str) and len(result.error) > 0
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_same_old_and_new_string(
        self, edit_tool: EditTool, context: ExecutionContext, sample_file: Path
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path=str(sample_file),
            old_string="hello",
            new_string="hello",
        )
        assert not result.success
        assert isinstance(result.error, str) and len(result.error) > 0
        assert "different" in result.error.lower()

    @pytest.mark.asyncio
    async def test_relative_path_rejected(
        self, edit_tool: EditTool, context: ExecutionContext
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path="relative/path.txt",
            old_string="foo",
            new_string="bar",
        )
        assert not result.success
        assert isinstance(result.error, str) and len(result.error) > 0
        assert "absolute path" in result.error.lower()


class TestEditToolEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_empty_old_string_edge_case(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")
        result = await edit_tool.execute(
            context,
            file_path=str(file_path),
            old_string="",
            new_string="prefix",
        )
        # Empty string appears "infinite" times, should fail validation
        assert not result.success

    @pytest.mark.asyncio
    async def test_replacement_creates_new_occurrence(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        # Edge case where replacement creates new match
        file_path = tmp_path / "test.txt"
        file_path.write_text("foobar")
        result = await edit_tool.execute(
            context,
            file_path=str(file_path),
            old_string="bar",
            new_string="barbar",
        )
        assert result.success
        assert file_path.read_text() == "foobarbar"


class TestEditToolSecurityValidation:
    """Test path security validation."""

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(
        self, edit_tool: EditTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        result = await edit_tool.execute(
            context,
            file_path=f"{tmp_path}/../../../etc/passwd",
            old_string="root",
            new_string="admin",
        )
        assert not result.success
        assert isinstance(result.error, str) and len(result.error) > 0
        assert "traversal" in result.error.lower() or "not found" in result.error.lower()
