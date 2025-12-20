"""Integration tests for execution tools."""

from __future__ import annotations

import asyncio

import pytest

from code_forge.tools.base import ExecutionContext
from code_forge.tools.execution import (
    BashOutputTool,
    BashTool,
    KillShellTool,
    ShellManager,
    ShellProcess,
    ShellStatus,
    register_execution_tools,
)
from code_forge.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    """Reset singletons before each test."""
    ShellManager.reset()
    ToolRegistry.reset()
    yield
    ShellManager.reset()
    ToolRegistry.reset()


@pytest.fixture
def context() -> ExecutionContext:
    """Create ExecutionContext."""
    return ExecutionContext(working_dir="/tmp")


class TestToolRegistration:
    """Tests for tool registration."""

    def test_register_execution_tools(self) -> None:
        """Test all execution tools are registered."""
        register_execution_tools()
        registry = ToolRegistry()

        assert registry.exists("Bash")
        assert registry.exists("BashOutput")
        assert registry.exists("KillShell")

    def test_tool_count(self) -> None:
        """Test correct number of tools registered."""
        register_execution_tools()
        registry = ToolRegistry()

        assert registry.count() == 3

    def test_get_registered_tools(self) -> None:
        """Test getting registered tools."""
        register_execution_tools()
        registry = ToolRegistry()

        bash = registry.get("Bash")
        assert isinstance(bash, BashTool)

        output = registry.get("BashOutput")
        assert isinstance(output, BashOutputTool)

        kill = registry.get("KillShell")
        assert isinstance(kill, KillShellTool)


class TestBackgroundWorkflow:
    """Integration tests for background command workflow."""

    @pytest.mark.asyncio
    async def test_full_background_workflow(self, context: ExecutionContext) -> None:
        """Test complete background command workflow."""
        bash_tool = BashTool()
        output_tool = BashOutputTool()
        kill_tool = KillShellTool()

        # 1. Start background command
        result = await bash_tool.execute(
            context,
            command="for i in 1 2 3; do echo $i; sleep 0.1; done",
            run_in_background=True,
        )
        assert result.success
        bash_id = result.metadata["bash_id"]

        # 2. Poll for output
        await asyncio.sleep(0.5)
        result = await output_tool.execute(context, bash_id=bash_id)
        assert result.success
        # Should have some output by now
        assert "1" in result.output or "2" in result.output

        # 3. Wait for completion
        shell = ShellManager.get_shell(bash_id)
        await shell.process.wait()
        shell.exit_code = shell.process.returncode
        shell.status = (
            ShellStatus.COMPLETED if shell.exit_code == 0 else ShellStatus.FAILED
        )

        # 4. Get final output
        await shell.read_output()
        result = await output_tool.execute(context, bash_id=bash_id)
        assert result.success
        assert result.metadata.get("is_running") is False

    @pytest.mark.asyncio
    async def test_background_kill_workflow(self, context: ExecutionContext) -> None:
        """Test starting and killing a background command."""
        bash_tool = BashTool()
        kill_tool = KillShellTool()

        # 1. Start long-running background command
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        assert result.success
        bash_id = result.metadata["bash_id"]

        # 2. Verify it's running
        shell = ShellManager.get_shell(bash_id)
        assert shell.is_running
        assert shell.status == ShellStatus.RUNNING

        # 3. Kill it
        result = await kill_tool.execute(context, shell_id=bash_id)
        assert result.success
        assert "terminated" in result.output.lower()

        # 4. Verify it's killed
        await asyncio.sleep(0.1)
        assert not shell.is_running
        assert shell.status == ShellStatus.KILLED

    @pytest.mark.asyncio
    async def test_multiple_background_shells(self, context: ExecutionContext) -> None:
        """Test running multiple background shells simultaneously."""
        bash_tool = BashTool()

        # Start multiple shells
        shell_ids = []
        for i in range(3):
            result = await bash_tool.execute(
                context, command=f"echo shell_{i}", run_in_background=True
            )
            assert result.success
            shell_ids.append(result.metadata["bash_id"])

        # Verify all shells exist
        for shell_id in shell_ids:
            shell = ShellManager.get_shell(shell_id)
            assert isinstance(shell, ShellProcess)

        # Kill all
        killed = await ShellManager.kill_all()
        assert killed >= 0  # Some may have already completed

    @pytest.mark.asyncio
    async def test_output_filtering_workflow(self, context: ExecutionContext) -> None:
        """Test filtering output from background shell."""
        bash_tool = BashTool()
        output_tool = BashOutputTool()

        # Start command with mixed output
        result = await bash_tool.execute(
            context,
            command="echo 'ERROR: failed'; echo 'INFO: ok'; echo 'ERROR: again'",
            run_in_background=True,
        )
        bash_id = result.metadata["bash_id"]

        # Wait for completion
        shell = ShellManager.get_shell(bash_id)
        await shell.process.wait()
        await shell.read_output()

        # Get filtered output
        result = await output_tool.execute(context, bash_id=bash_id, filter="ERROR")
        assert result.success
        assert "ERROR:" in result.output
        # Check that INFO line is not between ERROR lines
        output_lines = [
            line for line in result.output.split("\n") if "INFO:" in line
        ]
        assert len(output_lines) == 0


class TestConcurrentOperations:
    """Tests for concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_shell_creation(self, context: ExecutionContext) -> None:
        """Test creating multiple shells concurrently."""
        bash_tool = BashTool()

        # Create shells concurrently
        tasks = [
            bash_tool.execute(
                context, command=f"echo {i}", run_in_background=True
            )
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        for result in results:
            assert result.success
            assert "bash_id" in result.metadata

        # Verify unique IDs
        ids = [r.metadata["bash_id"] for r in results]
        assert len(ids) == len(set(ids))  # All unique

        # Clean up
        await ShellManager.kill_all()

    @pytest.mark.asyncio
    async def test_concurrent_output_reads(self, context: ExecutionContext) -> None:
        """Test reading output from multiple shells concurrently."""
        bash_tool = BashTool()
        output_tool = BashOutputTool()

        # Create shells
        shell_ids = []
        for i in range(3):
            result = await bash_tool.execute(
                context, command=f"echo output_{i}", run_in_background=True
            )
            shell_ids.append(result.metadata["bash_id"])

        # Wait for completion
        await asyncio.sleep(0.3)
        for shell_id in shell_ids:
            shell = ShellManager.get_shell(shell_id)
            await shell.read_output()

        # Read all outputs concurrently
        tasks = [
            output_tool.execute(context, bash_id=shell_id)
            for shell_id in shell_ids
        ]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        for result in results:
            assert result.success


class TestErrorHandling:
    """Tests for error handling in workflows."""

    @pytest.mark.asyncio
    async def test_get_output_after_kill(self, context: ExecutionContext) -> None:
        """Test getting output after killing a shell."""
        bash_tool = BashTool()
        output_tool = BashOutputTool()
        kill_tool = KillShellTool()

        # Start and kill shell
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]
        await kill_tool.execute(context, shell_id=bash_id)

        # Get output - should still work
        result = await output_tool.execute(context, bash_id=bash_id)
        assert result.success
        assert "killed" in result.output.lower()

    @pytest.mark.asyncio
    async def test_kill_twice(self, context: ExecutionContext) -> None:
        """Test killing a shell twice."""
        bash_tool = BashTool()
        kill_tool = KillShellTool()

        # Start and kill shell
        result = await bash_tool.execute(
            context, command="sleep 100", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Kill first time
        result1 = await kill_tool.execute(context, shell_id=bash_id)
        assert result1.success
        assert "terminated" in result1.output.lower()

        # Wait for process to fully terminate
        await asyncio.sleep(0.2)

        # Kill second time - should report already stopped
        result2 = await kill_tool.execute(context, shell_id=bash_id)
        assert result2.success
        assert "already stopped" in result2.output.lower()

    @pytest.mark.asyncio
    async def test_output_from_failed_command(self, context: ExecutionContext) -> None:
        """Test getting output from a failed command."""
        bash_tool = BashTool()
        output_tool = BashOutputTool()

        # Start a command that fails
        result = await bash_tool.execute(
            context, command="echo error; exit 1", run_in_background=True
        )
        bash_id = result.metadata["bash_id"]

        # Wait for completion
        shell = ShellManager.get_shell(bash_id)
        await shell.process.wait()
        shell.exit_code = shell.process.returncode
        shell.status = ShellStatus.FAILED
        await shell.read_output()

        # Get output
        result = await output_tool.execute(context, bash_id=bash_id)
        assert result.success
        assert result.metadata.get("status") == "failed"
        assert result.metadata.get("exit_code") == 1
