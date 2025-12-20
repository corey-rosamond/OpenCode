"""Integration tests for tool execution flow.

These tests verify that the tool system works correctly with all components:
- Tool registration and lookup
- Tool execution with parameters
- Integration with hooks system
- Permission checking (when applicable)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_forge.tools import (
    ExecutionContext,
    ToolExecutor,
    ToolRegistry,
    ToolResult,
    register_all_tools,
)


class TestToolExecutionFlow:
    """Test tool execution with all components."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_read_file_flow(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test Read tool through full pipeline."""
        result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
        )

        assert result.success
        assert "Sample module" in result.output
        assert "def hello" in result.output
        assert "def add" in result.output

    @pytest.mark.asyncio
    async def test_read_file_with_offset_and_limit(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test Read tool with offset and limit parameters."""
        result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
            offset=10,
            limit=5,
        )

        assert result.success
        # Should return limited lines
        lines = result.output.strip().split("\n")
        assert len(lines) <= 5

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test Read tool with nonexistent file."""
        result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(temp_project / "nonexistent.py"),
        )

        assert not result.success
        # Error message is in result.error for failures
        error_msg = (result.error or result.output or "").lower()
        assert "not found" in error_msg or "error" in error_msg

    @pytest.mark.asyncio
    async def test_write_creates_file(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test Write tool creates new file."""
        new_file = temp_project / "new_file.py"
        assert not new_file.exists()

        content = '''"""New file created by test."""

def test_function():
    return "test"
'''

        result = await tool_executor.execute(
            "Write",
            execution_context,
            file_path=str(new_file),
            content=content,
        )

        assert result.success
        assert new_file.exists()
        assert "New file created" in new_file.read_text()

    @pytest.mark.asyncio
    async def test_write_overwrites_file(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test Write tool overwrites existing file."""
        original_content = sample_file.read_text()
        new_content = "# Completely new content\n"

        result = await tool_executor.execute(
            "Write",
            execution_context,
            file_path=str(sample_file),
            content=new_content,
        )

        assert result.success
        assert sample_file.read_text() == new_content
        assert sample_file.read_text() != original_content

    @pytest.mark.asyncio
    async def test_edit_single_replacement(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test Edit tool with single replacement."""
        result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(sample_file),
            old_string='return f"Hello, {name}!"',
            new_string='return f"Greetings, {name}!"',
        )

        assert result.success

        # Verify change
        content = sample_file.read_text()
        assert "Greetings" in content
        assert 'return f"Hello, {name}!"' not in content

    @pytest.mark.asyncio
    async def test_edit_replace_all(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test Edit tool with replace_all option."""
        # Create file with multiple occurrences
        test_file = temp_project / "test_replace.py"
        test_file.write_text('''
def old_name():
    pass

def another_old_name():
    old_name()
''')

        result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(test_file),
            old_string="old_name",
            new_string="new_name",
            replace_all=True,
        )

        assert result.success

        content = test_file.read_text()
        assert "old_name" not in content
        assert content.count("new_name") == 3  # All occurrences replaced

    @pytest.mark.asyncio
    async def test_edit_string_not_found(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test Edit tool when string is not found."""
        result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(sample_file),
            old_string="nonexistent_string_xyz",
            new_string="replacement",
        )

        assert not result.success
        # Error message is in result.error for failures
        error_msg = (result.error or result.output or "").lower()
        assert "not found" in error_msg or "error" in error_msg

    @pytest.mark.asyncio
    async def test_glob_search_python_files(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        multiple_python_files: list[Path],
        temp_project: Path,
    ) -> None:
        """Test Glob tool for file searching."""
        result = await tool_executor.execute(
            "Glob",
            execution_context,
            pattern="**/*.py",
            path=str(temp_project),
        )

        assert result.success
        assert "main.py" in result.output
        assert "utils.py" in result.output
        assert "module.py" in result.output

    @pytest.mark.asyncio
    async def test_glob_no_matches(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test Glob tool with no matches."""
        result = await tool_executor.execute(
            "Glob",
            execution_context,
            pattern="**/*.xyz",
            path=str(temp_project),
        )

        # Should succeed but return empty or no matches message
        # Glob returns success with empty output if no matches, or may have message
        output = (result.output or "").lower() if isinstance(result.output, str) else ""
        assert result.success or "no matches" in output

    @pytest.mark.asyncio
    async def test_grep_search_pattern(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test Grep tool for content searching."""
        result = await tool_executor.execute(
            "Grep",
            execution_context,
            pattern=r"def \w+\(",
            path=str(sample_file),
        )

        assert result.success
        # Grep returns file paths by default (files_with_matches mode)
        assert "sample.py" in result.output

    @pytest.mark.asyncio
    async def test_grep_directory_search(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        multiple_python_files: list[Path],
        temp_project: Path,
    ) -> None:
        """Test Grep tool searching across directory."""
        result = await tool_executor.execute(
            "Grep",
            execution_context,
            pattern="def",
            path=str(temp_project),
        )

        assert result.success
        # Should find matches in multiple files
        output = str(result.output).lower()
        assert "main.py" in output or "utils.py" in output

    @pytest.mark.asyncio
    async def test_bash_echo(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test Bash tool with simple echo command."""
        result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="echo 'Hello, World!'",
        )

        assert result.success
        assert "Hello, World!" in result.output

    @pytest.mark.asyncio
    async def test_bash_working_directory(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test Bash tool respects working directory."""
        # Create a file in temp_project
        (temp_project / "test.txt").write_text("test content")

        result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="ls -la",
        )

        assert result.success
        assert "test.txt" in result.output

    @pytest.mark.asyncio
    async def test_bash_command_output(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test Bash tool captures command output."""
        result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="python3 -c \"print('test output')\"",
        )

        assert result.success
        assert "test output" in result.output


class TestToolExecutionPipeline:
    """Test multi-step tool execution pipelines."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_read_edit_verify_pipeline(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test read-edit-verify workflow."""
        # Step 1: Read file
        read_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
        )
        assert read_result.success
        assert "def hello" in read_result.output

        # Step 2: Edit file
        edit_result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(sample_file),
            old_string="def hello(name: str) -> str:",
            new_string="def greet(name: str) -> str:",
        )
        assert edit_result.success

        # Step 3: Verify change
        verify_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
        )
        assert verify_result.success
        assert "def greet" in verify_result.output
        assert "def hello" not in verify_result.output

    @pytest.mark.asyncio
    async def test_search_and_read_pipeline(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        multiple_python_files: list[Path],
        temp_project: Path,
    ) -> None:
        """Test search-then-read workflow."""
        # Step 1: Find files with a pattern
        glob_result = await tool_executor.execute(
            "Glob",
            execution_context,
            pattern="**/*.py",
            path=str(temp_project),
        )
        assert glob_result.success

        # Step 2: Search for specific content
        grep_result = await tool_executor.execute(
            "Grep",
            execution_context,
            pattern="helper",
            path=str(temp_project),
        )
        assert grep_result.success
        assert "utils.py" in grep_result.output

        # Step 3: Read the found file
        read_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(temp_project / "utils.py"),
        )
        assert read_result.success
        assert "def helper" in read_result.output

    @pytest.mark.asyncio
    async def test_write_then_bash_pipeline(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test write-then-execute workflow."""
        script_file = temp_project / "script.py"

        # Step 1: Write a Python script
        write_result = await tool_executor.execute(
            "Write",
            execution_context,
            file_path=str(script_file),
            content='print("Script executed successfully")\n',
        )
        assert write_result.success

        # Step 2: Execute the script
        bash_result = await tool_executor.execute(
            "Bash",
            execution_context,
            command=f"python3 {script_file}",
        )
        assert bash_result.success
        assert "Script executed successfully" in bash_result.output


class TestToolErrorHandling:
    """Test error handling in tool execution."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_unknown_tool(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test execution of unknown tool."""
        result = await tool_executor.execute(
            "NonexistentTool",
            execution_context,
        )
        assert not result.success
        assert "unknown" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameter(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test tool with missing required parameter."""
        # Read without file_path
        result = await tool_executor.execute(
            "Read",
            execution_context,
            # file_path is missing
        )

        assert not result.success

    @pytest.mark.asyncio
    async def test_invalid_path(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test tool with invalid path."""
        result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path="/nonexistent/path/to/file.py",
        )

        assert not result.success

    @pytest.mark.asyncio
    async def test_bash_command_failure(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test Bash tool with failing command."""
        result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="exit 1",
        )

        assert not result.success

    @pytest.mark.asyncio
    async def test_tool_recovery_after_error(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test that system recovers after tool error."""
        # First, cause an error
        error_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path="/nonexistent/file.py",
        )
        assert not error_result.success

        # Then, run a successful tool
        success_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
        )
        assert success_result.success


class TestToolRegistry:
    """Test tool registry functionality."""

    def test_registry_is_singleton(self, tool_registry: ToolRegistry) -> None:
        """Test that ToolRegistry is a singleton."""
        registry2 = ToolRegistry()  # Singleton via __new__
        assert registry2 is tool_registry

    def test_register_and_get_tool(self, tool_registry: ToolRegistry) -> None:
        """Test registering and retrieving a tool."""
        register_all_tools()

        tool = tool_registry.get("Read")
        assert tool.name == "Read"

    def test_list_tools(self, tool_registry: ToolRegistry) -> None:
        """Test listing all registered tools."""
        register_all_tools()

        tools = tool_registry.list_all()  # Correct method name
        tool_names = [t.name for t in tools]

        assert "Read" in tool_names
        assert "Write" in tool_names
        assert "Edit" in tool_names
        assert "Glob" in tool_names
        assert "Grep" in tool_names
        assert "Bash" in tool_names

    def test_get_nonexistent_tool(self, tool_registry: ToolRegistry) -> None:
        """Test getting a tool that doesn't exist."""
        tool = tool_registry.get("NonexistentTool")
        assert tool is None
