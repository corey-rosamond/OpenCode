"""Tests for WriteTool."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from code_forge.tools.base import ExecutionContext
from code_forge.tools.file.write import WriteTool


@pytest.fixture
def write_tool() -> WriteTool:
    """Create a WriteTool instance."""
    return WriteTool()


@pytest.fixture
def context(tmp_path: Path) -> ExecutionContext:
    """Create an execution context."""
    return ExecutionContext(working_dir=str(tmp_path))


@pytest.fixture
def dry_run_context(tmp_path: Path) -> ExecutionContext:
    """Create a dry-run execution context."""
    return ExecutionContext(working_dir=str(tmp_path), dry_run=True)


class TestWriteToolProperties:
    """Test WriteTool properties."""

    def test_name(self, write_tool: WriteTool) -> None:
        assert write_tool.name == "Write"

    def test_description(self, write_tool: WriteTool) -> None:
        assert "file_path" in write_tool.description
        assert "overwrite" in write_tool.description.lower()

    def test_category(self, write_tool: WriteTool) -> None:
        from code_forge.tools.base import ToolCategory

        assert write_tool.category == ToolCategory.FILE

    def test_parameters(self, write_tool: WriteTool) -> None:
        params = write_tool.parameters
        param_names = [p.name for p in params]
        assert "file_path" in param_names
        assert "content" in param_names


class TestWriteToolBasicOperations:
    """Test basic file writing operations."""

    @pytest.mark.asyncio
    async def test_write_new_file(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "new_file.txt"
        content = "Hello, World!"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        assert file_path.exists()
        assert file_path.read_text() == content
        assert result.metadata["created"] is True

    @pytest.mark.asyncio
    async def test_overwrite_existing_file(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "existing.txt"
        file_path.write_text("Original content")
        new_content = "New content"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=new_content
        )
        assert result.success
        assert file_path.read_text() == new_content
        assert result.metadata["created"] is False

    @pytest.mark.asyncio
    async def test_write_empty_file(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "empty.txt"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=""
        )
        assert result.success
        assert file_path.exists()
        assert file_path.read_text() == ""

    @pytest.mark.asyncio
    async def test_write_multiline_content(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3\n"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        assert file_path.read_text() == content

    @pytest.mark.asyncio
    async def test_write_unicode_content(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍 Привет"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        assert file_path.read_text() == content


class TestWriteToolDirectoryCreation:
    """Test automatic directory creation."""

    @pytest.mark.asyncio
    async def test_create_parent_directories(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "nested" / "dirs" / "file.txt"
        content = "Deep nested file"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        assert file_path.exists()
        assert file_path.read_text() == content


class TestWriteToolDryRun:
    """Test dry-run mode.

    Note: Dry run is handled in BaseTool.execute() before _execute() is called,
    so it returns a generic message with the kwargs.
    """

    @pytest.mark.asyncio
    async def test_dry_run_new_file(
        self, write_tool: WriteTool, dry_run_context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "new_file.txt"
        result = await write_tool.execute(
            dry_run_context, file_path=str(file_path), content="test"
        )
        assert result.success
        assert "Dry Run" in result.output
        assert "Write" in result.output  # Tool name in output
        assert not file_path.exists()  # File should NOT be created
        assert result.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_existing_file(
        self, write_tool: WriteTool, dry_run_context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "existing.txt"
        file_path.write_text("Original")
        result = await write_tool.execute(
            dry_run_context, file_path=str(file_path), content="New"
        )
        assert result.success
        assert "Dry Run" in result.output
        assert "Write" in result.output  # Tool name in output
        assert file_path.read_text() == "Original"  # Content unchanged
        assert result.metadata.get("dry_run") is True


class TestWriteToolErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "relative_path",
        [
            "relative/path.txt",
            "../parent/file.txt",
            "./current/file.py",
            "simple.txt",
        ]
    )
    async def test_relative_path_rejected(
        self, write_tool: WriteTool, context: ExecutionContext, relative_path: str
    ) -> None:
        result = await write_tool.execute(
            context, file_path=relative_path, content="test"
        )
        assert not result.success
        assert isinstance(result.error, str)
        assert "absolute path" in result.error.lower()

    @pytest.mark.asyncio
    async def test_permission_denied(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        file_path = readonly_dir / "test.txt"

        # Make directory read-only
        os.chmod(readonly_dir, 0o555)
        try:
            result = await write_tool.execute(
                context, file_path=str(file_path), content="test"
            )
            assert not result.success
            assert isinstance(result.error, str)
            assert "permission" in result.error.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)


class TestWriteToolMetadata:
    """Test result metadata."""

    @pytest.mark.asyncio
    async def test_bytes_written_metadata(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        assert result.metadata["bytes_written"] == len(content.encode("utf-8"))

    @pytest.mark.asyncio
    async def test_bytes_written_unicode(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "unicode.txt"
        content = "Hello 世界"  # Multi-byte characters
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        # UTF-8 encoding: "Hello " = 6 bytes, "世界" = 6 bytes (3 each)
        assert result.metadata["bytes_written"] == len(content.encode("utf-8"))


class TestWriteToolSecurityValidation:
    """Test path security validation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "malicious_suffix",
        [
            "../../../tmp/evil.txt",
            "/../../../etc/passwd",
            "/./../../etc/shadow",
            "/../../../../../root/.ssh/authorized_keys",
        ]
    )
    async def test_path_traversal_rejected(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path, malicious_suffix: str
    ) -> None:
        # Try to use path traversal
        result = await write_tool.execute(
            context,
            file_path=f"{tmp_path}/{malicious_suffix}",
            content="malicious",
        )
        assert not result.success
        assert isinstance(result.error, str)
        assert "traversal" in result.error.lower() or "invalid" in result.error.lower()


class TestWriteToolFileExtensions:
    """Test writing different file types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "extension,content",
        [
            (".txt", "Plain text content"),
            (".py", "def function():\n    pass"),
            (".js", "function test() { return true; }"),
            (".json", '{"key": "value"}'),
            (".md", "# Markdown Header\n\nContent here"),
            (".yaml", "key: value\nlist:\n  - item1"),
            (".xml", "<?xml version='1.0'?><root><item/></root>"),
            (".csv", "col1,col2\nval1,val2"),
        ]
    )
    async def test_write_various_file_types(
        self, write_tool: WriteTool, context: ExecutionContext, tmp_path: Path, extension: str, content: str
    ) -> None:
        file_path = tmp_path / f"test{extension}"
        result = await write_tool.execute(
            context, file_path=str(file_path), content=content
        )
        assert result.success
        assert file_path.exists()
        assert file_path.read_text() == content
