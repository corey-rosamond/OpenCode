"""Tests for BashTool."""

from __future__ import annotations

import pytest

from code_forge.tools.base import ExecutionContext, ToolCategory
from code_forge.tools.execution.bash import BashTool
from code_forge.tools.execution.shell_manager import ShellManager, ShellProcess


@pytest.fixture(autouse=True)
def reset_shell_manager() -> None:
    """Reset ShellManager singleton before each test."""
    ShellManager.reset()
    yield
    ShellManager.reset()


@pytest.fixture
def tool() -> BashTool:
    """Create BashTool instance."""
    return BashTool()


@pytest.fixture
def context(tmp_path: str) -> ExecutionContext:
    """Create ExecutionContext."""
    return ExecutionContext(working_dir=str(tmp_path))


class TestBashToolProperties:
    """Tests for BashTool properties."""

    def test_name(self, tool: BashTool) -> None:
        """Test tool name."""
        assert tool.name == "Bash"

    def test_description(self, tool: BashTool) -> None:
        """Test tool description."""
        assert "bash command" in tool.description.lower()
        assert "terminal operations" in tool.description.lower()

    def test_category(self, tool: BashTool) -> None:
        """Test tool category."""
        assert tool.category == ToolCategory.EXECUTION

    def test_parameters(self, tool: BashTool) -> None:
        """Test tool parameters."""
        params = tool.parameters
        param_names = [p.name for p in params]
        assert "command" in param_names
        assert "description" in param_names
        assert "timeout" in param_names
        assert "run_in_background" in param_names

    def test_command_param_required(self, tool: BashTool) -> None:
        """Test command parameter is required."""
        command_param = next(p for p in tool.parameters if p.name == "command")
        assert command_param.required is True

    def test_timeout_param_limits(self, tool: BashTool) -> None:
        """Test timeout parameter has correct limits."""
        timeout_param = next(p for p in tool.parameters if p.name == "timeout")
        assert timeout_param.minimum == 1000
        assert timeout_param.maximum == 600000


class TestBashToolExecution:
    """Tests for BashTool execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_command(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test executing a simple command."""
        result = await tool.execute(context, command="echo hello")
        assert result.success
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_execute_returns_exit_code(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test exit code is returned in metadata."""
        result = await tool.execute(context, command="echo hello")
        assert result.success
        assert result.metadata.get("exit_code") == 0

    @pytest.mark.asyncio
    async def test_execute_captures_stderr(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test stderr is captured."""
        result = await tool.execute(context, command="echo error >&2")
        assert result.success
        assert "[stderr]" in result.output
        assert "error" in result.output

    @pytest.mark.asyncio
    async def test_execute_command_failure(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test handling of command failure."""
        result = await tool.execute(context, command="exit 1")
        assert not result.success
        assert result.metadata.get("exit_code") == 1
        assert "exit code 1" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_nonexistent_command(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test handling of nonexistent command."""
        result = await tool.execute(context, command="nonexistent_command_xyz123")
        assert not result.success

    @pytest.mark.asyncio
    async def test_execute_with_working_dir(
        self, tool: BashTool, tmp_path: str
    ) -> None:
        """Test command runs in working directory."""
        import os

        context = ExecutionContext(working_dir=str(tmp_path))
        result = await tool.execute(context, command="pwd")
        assert result.success
        # Normalize paths for comparison
        assert os.path.realpath(str(tmp_path)) in os.path.realpath(result.output.strip())


class TestBashToolTimeout:
    """Tests for BashTool timeout handling."""

    @pytest.mark.asyncio
    async def test_execute_timeout(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test command timeout."""
        result = await tool.execute(
            context, command="sleep 100", timeout=1000  # 1 second
        )
        assert not result.success
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_exceeds_max_timeout(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test timeout exceeds maximum."""
        result = await tool.execute(
            context, command="echo hello", timeout=700000  # > 600000
        )
        assert not result.success
        # Error comes from parameter validation
        assert "maximum" in result.error.lower()

    @pytest.mark.asyncio
    async def test_default_timeout_used(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test default timeout is used when not specified."""
        # This just verifies the command runs without timeout issues
        result = await tool.execute(context, command="echo hello")
        assert result.success


class TestBashToolOutputTruncation:
    """Tests for BashTool output truncation."""

    @pytest.mark.asyncio
    async def test_output_truncation(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test large output is truncated."""
        # Generate output larger than MAX_OUTPUT_SIZE
        result = await tool.execute(
            context, command="yes | head -n 50000"  # Lots of 'y' lines
        )
        assert result.success
        assert result.metadata.get("truncated") is True
        assert "truncated" in result.output.lower()


class TestBashToolSecurity:
    """Tests for BashTool security features."""

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_root(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test rm -rf / is blocked."""
        result = await tool.execute(context, command="rm -rf /")
        assert not result.success
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_root_star(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test rm -rf /* is blocked."""
        result = await tool.execute(context, command="rm -rf /*")
        assert not result.success
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_blocks_mkfs(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test mkfs commands are blocked."""
        result = await tool.execute(context, command="mkfs.ext4 /dev/sda1")
        assert not result.success
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_blocks_dd_to_disk(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test dd to disk device is blocked."""
        result = await tool.execute(
            context, command="dd if=/dev/zero of=/dev/sda bs=1M"
        )
        assert not result.success
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_blocks_chmod_777_root(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test chmod -R 777 / is blocked."""
        result = await tool.execute(context, command="chmod -R 777 /")
        assert not result.success
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_allows_safe_commands(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test safe commands are allowed."""
        result = await tool.execute(context, command="echo hello")
        assert result.success

    @pytest.mark.asyncio
    async def test_allows_rm_in_safe_directory(
        self, tool: BashTool, tmp_path: str
    ) -> None:
        """Test rm is allowed in non-root directories."""
        import os

        # Create a test file
        test_file = os.path.join(str(tmp_path), "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        context = ExecutionContext(working_dir=str(tmp_path))
        result = await tool.execute(context, command=f"rm {test_file}")
        assert result.success


class TestBashToolBackground:
    """Tests for BashTool background execution."""

    @pytest.mark.asyncio
    async def test_run_in_background(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test background execution."""
        result = await tool.execute(
            context, command="echo background", run_in_background=True
        )
        assert result.success
        assert "bash_id" in result.metadata
        assert result.metadata["bash_id"].startswith("shell_")

    @pytest.mark.asyncio
    async def test_background_returns_instructions(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test background execution returns usage instructions."""
        result = await tool.execute(
            context, command="echo test", run_in_background=True
        )
        assert result.success
        assert "BashOutput" in result.output

    @pytest.mark.asyncio
    async def test_background_shell_created(
        self, tool: BashTool, context: ExecutionContext
    ) -> None:
        """Test background execution creates shell in manager."""
        result = await tool.execute(
            context, command="sleep 10", run_in_background=True
        )
        assert result.success
        bash_id = result.metadata["bash_id"]
        shell = ShellManager.get_shell(bash_id)
        assert isinstance(shell, ShellProcess)
        shell.kill()


class TestBashToolDryRun:
    """Tests for BashTool dry run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, tool: BashTool) -> None:
        """Test dry run mode doesn't execute command."""
        context = ExecutionContext(working_dir="/tmp", dry_run=True)
        result = await tool.execute(context, command="rm -rf /tmp/test")
        assert result.success
        assert "Dry Run" in result.output
        assert result.metadata.get("dry_run") is True


class TestBashToolSchemas:
    """Tests for BashTool schema generation."""

    def test_openai_schema(self, tool: BashTool) -> None:
        """Test OpenAI schema generation."""
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Bash"
        assert "command" in schema["function"]["parameters"]["required"]

    def test_anthropic_schema(self, tool: BashTool) -> None:
        """Test Anthropic schema generation."""
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "Bash"
        assert "command" in schema["input_schema"]["required"]

    def test_validate_params_missing_command(self, tool: BashTool) -> None:
        """Test parameter validation with missing command."""
        valid, error = tool.validate_params()
        assert not valid
        assert "command" in error.lower()

    def test_validate_params_valid(self, tool: BashTool) -> None:
        """Test parameter validation with valid params."""
        valid, error = tool.validate_params(command="echo hello")
        assert valid
        assert error is None
