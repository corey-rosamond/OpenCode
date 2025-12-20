"""Tests for KillShellTool."""

from __future__ import annotations

import asyncio

import pytest

from code_forge.tools.base import ExecutionContext, ToolCategory
from code_forge.tools.execution.bash import BashTool
from code_forge.tools.execution.kill_shell import KillShellTool
from code_forge.tools.execution.shell_manager import ShellManager, ShellStatus


@pytest.fixture(autouse=True)
def reset_shell_manager() -> None:
    """Reset ShellManager singleton before each test."""
    ShellManager.reset()
    yield
    ShellManager.reset()


@pytest.fixture
def tool() -> KillShellTool:
    """Create KillShellTool instance."""
    return KillShellTool()


@pytest.fixture
def bash_tool() -> BashTool:
    """Create BashTool instance."""
    return BashTool()


@pytest.fixture
def context() -> ExecutionContext:
    """Create ExecutionContext."""
    return ExecutionContext(working_dir="/tmp")


class TestKillShellToolProperties:
    """Tests for KillShellTool properties."""

    def test_name(self, tool: KillShellTool) -> None:
        """Test tool name."""
        assert tool.name == "KillShell"

    def test_description(self, tool: KillShellTool) -> None:
        """Test tool description."""
        assert "kill" in tool.description.lower()
        assert "background" in tool.description.lower()

    def test_category(self, tool: KillShellTool) -> None:
        """Test tool category."""
        assert tool.category == ToolCategory.EXECUTION

    def test_parameters(self, tool: KillShellTool) -> None:
        """Test tool parameters."""
        params = tool.parameters
        param_names = [p.name for p in params]
        assert "shell_id" in param_names

    def test_shell_id_param_required(self, tool: KillShellTool) -> None:
        """Test shell_id parameter is required."""
        shell_id_param = next(p for p in tool.parameters if p.name == "shell_id")
        assert shell_id_param.required is True


class TestKillShellToolExecution:
    """Tests for KillShellTool execution."""

    @pytest.mark.asyncio
    async def test_shell_not_found(
        self, tool: KillShellTool, context: ExecutionContext
    ) -> None:
        """Test error when shell not found."""
        result = await tool.execute(context, shell_id="nonexistent_id")
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_kill_running_shell(
        self,
        tool: KillShellTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test killing a running shell."""
        # Start a long-running background command
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Kill it
        result = await tool.execute(context, shell_id=bash_id)
        assert result.success
        assert "terminated" in result.output.lower()

        # Verify it's killed
        shell = ShellManager.get_shell(bash_id)
        assert shell.status == ShellStatus.KILLED

    @pytest.mark.asyncio
    async def test_kill_already_stopped_shell(
        self,
        tool: KillShellTool,
        context: ExecutionContext,
    ) -> None:
        """Test killing an already stopped shell."""
        # Create and complete a shell
        shell = await ShellManager.create_shell("echo done", "/tmp")
        await shell.process.wait()
        shell.status = ShellStatus.COMPLETED

        result = await tool.execute(context, shell_id=shell.id)
        assert result.success
        assert "already stopped" in result.output.lower()
        assert result.metadata.get("already_stopped") is True

    @pytest.mark.asyncio
    async def test_returns_command_in_metadata(
        self,
        tool: KillShellTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test command is returned in metadata."""
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        result = await tool.execute(context, shell_id=bash_id)
        assert result.success
        assert result.metadata.get("command") == "sleep 100"

    @pytest.mark.asyncio
    async def test_returns_duration_in_metadata(
        self,
        tool: KillShellTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test duration is returned in metadata."""
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Wait a bit so there's some duration
        await asyncio.sleep(0.1)

        result = await tool.execute(context, shell_id=bash_id)
        assert result.success
        assert isinstance(result.metadata.get("duration_ms"), (int, float))
        assert result.metadata["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_returns_shell_id_in_metadata(
        self,
        tool: KillShellTool,
        bash_tool: BashTool,
        context: ExecutionContext,
    ) -> None:
        """Test shell_id is returned in metadata."""
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        result = await tool.execute(context, shell_id=bash_id)
        assert result.success
        assert result.metadata.get("shell_id") == bash_id


class TestKillShellToolSchemas:
    """Tests for KillShellTool schema generation."""

    def test_openai_schema(self, tool: KillShellTool) -> None:
        """Test OpenAI schema generation."""
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "KillShell"
        assert "shell_id" in schema["function"]["parameters"]["required"]

    def test_anthropic_schema(self, tool: KillShellTool) -> None:
        """Test Anthropic schema generation."""
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "KillShell"
        assert "shell_id" in schema["input_schema"]["required"]

    def test_validate_params_missing_shell_id(self, tool: KillShellTool) -> None:
        """Test parameter validation with missing shell_id."""
        valid, error = tool.validate_params()
        assert not valid
        assert "shell_id" in error.lower()

    def test_validate_params_valid(self, tool: KillShellTool) -> None:
        """Test parameter validation with valid params."""
        valid, error = tool.validate_params(shell_id="shell_12345")
        assert valid
        assert error is None
