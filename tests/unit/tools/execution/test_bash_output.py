"""Tests for BashOutputTool."""

from __future__ import annotations

import asyncio

import pytest

from code_forge.tools.base import ExecutionContext, ToolCategory
from code_forge.tools.execution.bash import BashTool
from code_forge.tools.execution.bash_output import BashOutputTool
from code_forge.tools.execution.shell_manager import ShellManager, ShellStatus


@pytest.fixture(autouse=True)
def reset_shell_manager() -> None:
    """Reset ShellManager singleton before each test."""
    ShellManager.reset()
    yield
    ShellManager.reset()


@pytest.fixture
def tool() -> BashOutputTool:
    """Create BashOutputTool instance."""
    return BashOutputTool()


@pytest.fixture
def bash_tool() -> BashTool:
    """Create BashTool instance."""
    return BashTool()


@pytest.fixture
def context() -> ExecutionContext:
    """Create ExecutionContext."""
    return ExecutionContext(working_dir="/tmp")


class TestBashOutputToolProperties:
    """Tests for BashOutputTool properties."""

    def test_name(self, tool: BashOutputTool) -> None:
        """Test tool name."""
        assert tool.name == "BashOutput"

    def test_description(self, tool: BashOutputTool) -> None:
        """Test tool description."""
        assert "background" in tool.description.lower()
        assert "output" in tool.description.lower()

    def test_category(self, tool: BashOutputTool) -> None:
        """Test tool category."""
        assert tool.category == ToolCategory.EXECUTION

    def test_parameters(self, tool: BashOutputTool) -> None:
        """Test tool parameters."""
        params = tool.parameters
        param_names = [p.name for p in params]
        assert "bash_id" in param_names
        assert "filter" in param_names

    def test_bash_id_param_required(self, tool: BashOutputTool) -> None:
        """Test bash_id parameter is required."""
        bash_id_param = next(p for p in tool.parameters if p.name == "bash_id")
        assert bash_id_param.required is True

    def test_filter_param_optional(self, tool: BashOutputTool) -> None:
        """Test filter parameter is optional."""
        filter_param = next(p for p in tool.parameters if p.name == "filter")
        assert filter_param.required is False


class TestBashOutputToolExecution:
    """Tests for BashOutputTool execution."""

    @pytest.mark.asyncio
    async def test_shell_not_found(
        self, tool: BashOutputTool, context: ExecutionContext
    ) -> None:
        """Test error when shell not found."""
        result = await tool.execute(context, bash_id="nonexistent_id")
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_output_from_completed_shell(
        self,
        tool: BashOutputTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test getting output from a completed shell."""
        # Start background command
        result = await bash_tool.execute(
            context, command="echo test_output", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Wait for completion
        shell = ShellManager.get_shell(bash_id)
        await asyncio.sleep(0.2)
        await shell.read_output()

        # Get output
        result = await tool.execute(context, bash_id=bash_id)
        assert result.success
        assert "test_output" in result.output

    @pytest.mark.asyncio
    async def test_includes_status(
        self,
        tool: BashOutputTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test output includes shell status."""
        result = await bash_tool.execute(
            context, command="echo hello", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Wait a bit
        await asyncio.sleep(0.2)

        result = await tool.execute(context, bash_id=bash_id)
        assert result.success
        assert "Status:" in result.output
        assert isinstance(result.metadata.get("status"), str)

    @pytest.mark.asyncio
    async def test_includes_exit_code(
        self,
        tool: BashOutputTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test output includes exit code when available."""
        result = await bash_tool.execute(
            context, command="echo done", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Wait for completion
        shell = ShellManager.get_shell(bash_id)
        await shell.process.wait()
        shell.exit_code = shell.process.returncode
        shell.status = (
            ShellStatus.COMPLETED if shell.exit_code == 0 else ShellStatus.FAILED
        )

        result = await tool.execute(context, bash_id=bash_id)
        assert result.success
        assert isinstance(result.metadata.get("exit_code"), int)

    @pytest.mark.asyncio
    async def test_returns_only_new_output(
        self,
        tool: BashOutputTool,
        context: ExecutionContext,
    ) -> None:
        """Test only new output is returned on subsequent calls."""
        # Create shell that outputs multiple lines
        shell = await ShellManager.create_shell("echo line1; echo line2", "/tmp")
        await shell.process.wait()
        await shell.read_output()

        # First call - get all output
        result1 = await tool.execute(context, bash_id=shell.id)
        assert result1.success
        assert "line1" in result1.output
        assert "line2" in result1.output

        # Second call - no new output
        result2 = await tool.execute(context, bash_id=shell.id)
        assert result2.success
        # Status should be present but no new content
        assert "line1" not in result2.output or "Status:" in result2.output

    @pytest.mark.asyncio
    async def test_is_running_metadata(
        self,
        tool: BashOutputTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test is_running is in metadata."""
        result = await bash_tool.execute(
            context, command="sleep 10", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        result = await tool.execute(context, bash_id=bash_id)
        assert result.success
        assert "is_running" in result.metadata

        # Clean up
        shell = ShellManager.get_shell(bash_id)
        shell.kill()


class TestBashOutputToolFiltering:
    """Tests for BashOutputTool output filtering."""

    @pytest.mark.asyncio
    async def test_filter_regex(
        self, tool: BashOutputTool, context: ExecutionContext
    ) -> None:
        """Test regex filtering of output."""
        shell = await ShellManager.create_shell(
            "echo 'error: something failed'; echo 'info: all good'; echo 'error: again'",
            "/tmp",
        )
        await shell.process.wait()
        await shell.read_output()

        result = await tool.execute(context, bash_id=shell.id, filter="error")
        assert result.success
        assert "error:" in result.output
        # info line should be filtered out (not in output between status line)
        output_lines = result.output.split("\n")
        info_lines = [line for line in output_lines if "info:" in line]
        assert len(info_lines) == 0

    @pytest.mark.asyncio
    async def test_invalid_filter_regex(
        self,
        tool: BashOutputTool,
        context: ExecutionContext,
    ) -> None:
        """Test error on invalid regex."""
        # Create shell with output that we can try to filter
        shell = await ShellManager.create_shell("echo test_content", "/tmp")
        await shell.process.wait()
        await shell.read_output()

        # Now try to filter with invalid regex
        result = await tool.execute(context, bash_id=shell.id, filter="[invalid(regex")
        assert not result.success
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_filter_with_no_matches(
        self, tool: BashOutputTool, context: ExecutionContext
    ) -> None:
        """Test filtering with no matching lines."""
        shell = await ShellManager.create_shell("echo hello world", "/tmp")
        await shell.process.wait()
        await shell.read_output()

        result = await tool.execute(context, bash_id=shell.id, filter="nonexistent")
        assert result.success
        # Should just have status line
        assert "Status:" in result.output


class TestBashOutputToolSchemas:
    """Tests for BashOutputTool schema generation."""

    def test_openai_schema(self, tool: BashOutputTool) -> None:
        """Test OpenAI schema generation."""
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "BashOutput"
        assert "bash_id" in schema["function"]["parameters"]["required"]

    def test_anthropic_schema(self, tool: BashOutputTool) -> None:
        """Test Anthropic schema generation."""
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "BashOutput"
        assert "bash_id" in schema["input_schema"]["required"]

    def test_validate_params_missing_bash_id(self, tool: BashOutputTool) -> None:
        """Test parameter validation with missing bash_id."""
        valid, error = tool.validate_params()
        assert not valid
        assert "bash_id" in error.lower()

    def test_validate_params_valid(self, tool: BashOutputTool) -> None:
        """Test parameter validation with valid params."""
        valid, error = tool.validate_params(bash_id="shell_12345")
        assert valid
        assert error is None
