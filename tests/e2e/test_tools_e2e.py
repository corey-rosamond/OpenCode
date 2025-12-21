"""E2E tests for tool execution."""

from pathlib import Path

import pytest


class TestFileToolsE2E:
    """E2E tests for file manipulation tools."""

    @pytest.mark.asyncio
    async def test_read_tool_execution(self, tool_executor, execution_context, sample_file):
        """Given Read tool, reads file successfully"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        read_tool = registry.get_tool("Read")

        result = await read_tool.execute(
            context=execution_context,
            file_path=str(sample_file),
        )

        assert result.success
        assert "def hello(name: str)" in result.output

    @pytest.mark.asyncio
    async def test_write_tool_execution(self, tool_executor, execution_context, temp_project):
        """Given Write tool, creates file successfully"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        write_tool = registry.get_tool("Write")

        new_file = temp_project / "new_file.txt"
        content = "Hello from E2E test!"

        result = await write_tool.execute(
            context=execution_context,
            file_path=str(new_file),
            content=content,
        )

        assert result.success
        assert new_file.exists()
        assert new_file.read_text() == content

    @pytest.mark.asyncio
    async def test_edit_tool_execution(self, tool_executor, execution_context, sample_file):
        """Given Edit tool, modifies file successfully"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        edit_tool = registry.get_tool("Edit")

        result = await edit_tool.execute(
            context=execution_context,
            file_path=str(sample_file),
            old_string="def hello(name: str) -> str:",
            new_string="def greet(name: str) -> str:",
        )

        assert result.success
        content = sample_file.read_text()
        assert "def greet(name: str) -> str:" in content
        assert "def hello(name: str)" not in content

    @pytest.mark.asyncio
    async def test_glob_tool_execution(self, tool_executor, execution_context, multiple_python_files):
        """Given Glob tool, finds files by pattern"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        glob_tool = registry.get_tool("Glob")

        result = await glob_tool.execute(
            context=execution_context,
            pattern="**/*.py",
        )

        assert result.success
        assert "main.py" in result.output
        assert "utils.py" in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_execution(self, tool_executor, execution_context, sample_file):
        """Given Grep tool, searches file content"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        grep_tool = registry.get_tool("Grep")

        result = await grep_tool.execute(
            context=execution_context,
            pattern="hello",
            output_mode="content",
        )

        assert result.success
        assert "hello" in result.output.lower()


class TestExecutionToolsE2E:
    """E2E tests for execution tools."""

    @pytest.mark.asyncio
    async def test_bash_tool_execution(self, tool_executor, execution_context):
        """Given Bash tool, executes command successfully"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        bash_tool = registry.get_tool("Bash")

        result = await bash_tool.execute(
            context=execution_context,
            command="echo 'Hello from bash'",
        )

        assert result.success
        assert "Hello from bash" in result.output

    @pytest.mark.asyncio
    async def test_bash_tool_with_error(self, tool_executor, execution_context):
        """Given Bash tool with invalid command, returns error"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        bash_tool = registry.get_tool("Bash")

        result = await bash_tool.execute(
            context=execution_context,
            command="nonexistent_command_xyz",
        )

        assert not result.success
        assert result.error is not None


class TestToolChaining:
    """E2E tests for chaining multiple tools together."""

    @pytest.mark.asyncio
    async def test_write_then_read(self, tool_executor, execution_context, temp_project):
        """Given Write then Read, verifies file content"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        write_tool = registry.get_tool("Write")
        read_tool = registry.get_tool("Read")

        # Write file
        file_path = temp_project / "test.txt"
        content = "Test content for chaining"

        write_result = await write_tool.execute(
            context=execution_context,
            file_path=str(file_path),
            content=content,
        )
        assert write_result.success

        # Read file back
        read_result = await read_tool.execute(
            context=execution_context,
            file_path=str(file_path),
        )

        assert read_result.success
        assert content in read_result.output

    @pytest.mark.asyncio
    async def test_write_edit_read(self, tool_executor, execution_context, temp_project):
        """Given Write, Edit, then Read, verifies modifications"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        write_tool = registry.get_tool("Write")
        edit_tool = registry.get_tool("Edit")
        read_tool = registry.get_tool("Read")

        file_path = temp_project / "edit_test.py"

        # Write
        write_result = await write_tool.execute(
            context=execution_context,
            file_path=str(file_path),
            content="def old_function():\n    pass\n",
        )
        assert write_result.success

        # Edit
        edit_result = await edit_tool.execute(
            context=execution_context,
            file_path=str(file_path),
            old_string="old_function",
            new_string="new_function",
        )
        assert edit_result.success

        # Read and verify
        read_result = await read_tool.execute(
            context=execution_context,
            file_path=str(file_path),
        )
        assert read_result.success
        assert "new_function" in read_result.output
        assert "old_function" not in read_result.output

    @pytest.mark.asyncio
    async def test_bash_glob_workflow(self, tool_executor, execution_context, temp_project):
        """Given Bash to create files, Glob to find them"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        bash_tool = registry.get_tool("Bash")
        glob_tool = registry.get_tool("Glob")

        # Create files with bash
        bash_result = await bash_tool.execute(
            context=execution_context,
            command="touch file1.txt file2.txt file3.txt",
        )
        assert bash_result.success

        # Find with glob
        glob_result = await glob_tool.execute(
            context=execution_context,
            pattern="*.txt",
        )

        assert glob_result.success
        assert "file1.txt" in glob_result.output
        assert "file2.txt" in glob_result.output
        assert "file3.txt" in glob_result.output
