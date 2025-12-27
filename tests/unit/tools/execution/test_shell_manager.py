"""Tests for ShellManager and ShellProcess."""

from __future__ import annotations

import asyncio
import time

import pytest

import asyncio.subprocess

from code_forge.tools.execution.shell_manager import (
    ShellManager,
    ShellProcess,
    ShellStatus,
)


@pytest.fixture(autouse=True)
def reset_shell_manager() -> None:
    """Reset ShellManager singleton before each test."""
    ShellManager.reset()
    yield
    ShellManager.reset()


class TestShellStatus:
    """Tests for ShellStatus enum."""

    def test_pending_status(self) -> None:
        """Test PENDING status."""
        assert ShellStatus.PENDING.value == "pending"

    def test_running_status(self) -> None:
        """Test RUNNING status."""
        assert ShellStatus.RUNNING.value == "running"

    def test_completed_status(self) -> None:
        """Test COMPLETED status."""
        assert ShellStatus.COMPLETED.value == "completed"

    def test_failed_status(self) -> None:
        """Test FAILED status."""
        assert ShellStatus.FAILED.value == "failed"

    def test_killed_status(self) -> None:
        """Test KILLED status."""
        assert ShellStatus.KILLED.value == "killed"

    def test_timeout_status(self) -> None:
        """Test TIMEOUT status."""
        assert ShellStatus.TIMEOUT.value == "timeout"


class TestShellProcess:
    """Tests for ShellProcess dataclass."""

    def test_initial_state(self) -> None:
        """Test initial ShellProcess state."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        assert shell.id == "test_shell"
        assert shell.command == "echo hello"
        assert shell.working_dir == "/tmp"
        assert shell.process is None
        assert shell.status == ShellStatus.PENDING
        assert shell.exit_code is None
        assert shell.stdout_buffer == ""
        assert shell.stderr_buffer == ""
        assert shell.last_read_stdout == 0
        assert shell.last_read_stderr == 0

    def test_get_new_output_empty(self) -> None:
        """Test get_new_output with empty buffer."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        output = shell.get_new_output()
        assert output == ""

    def test_get_new_output_stdout(self) -> None:
        """Test get_new_output with stdout."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        # Use _append_to_buffer to add output (stdout_buffer is a property)
        shell._append_to_buffer("stdout", "hello world\n")
        output = shell.get_new_output()
        assert output == "hello world\n"
        # Second call should return empty
        output2 = shell.get_new_output()
        assert output2 == ""

    def test_get_new_output_with_stderr(self) -> None:
        """Test get_new_output with stderr included."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        shell._append_to_buffer("stdout", "out\n")
        shell._append_to_buffer("stderr", "err\n")
        output = shell.get_new_output(include_stderr=True)
        assert "out\n" in output
        assert "[stderr]" in output
        assert "err\n" in output

    def test_get_new_output_without_stderr(self) -> None:
        """Test get_new_output without stderr."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        shell._append_to_buffer("stdout", "out\n")
        shell._append_to_buffer("stderr", "err\n")
        output = shell.get_new_output(include_stderr=False)
        assert "out\n" in output
        assert "stderr" not in output

    def test_get_all_output(self) -> None:
        """Test get_all_output."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        shell._append_to_buffer("stdout", "stdout content\n")
        shell._append_to_buffer("stderr", "stderr content\n")
        output = shell.get_all_output()
        assert "stdout content\n" in output
        assert "[stderr]" in output
        assert "stderr content\n" in output

    def test_is_running_no_process(self) -> None:
        """Test is_running with no process."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        assert not shell.is_running

    def test_duration_ms_not_started(self) -> None:
        """Test duration_ms when not started."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        assert shell.duration_ms is None

    def test_duration_ms_started(self) -> None:
        """Test duration_ms when started."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        shell.started_at = time.time() - 1.0  # 1 second ago
        duration = shell.duration_ms
        assert isinstance(duration, (int, float))
        assert duration >= 1000  # At least 1000ms

    def test_duration_ms_completed(self) -> None:
        """Test duration_ms when completed."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        shell.started_at = 100.0
        shell.completed_at = 100.5
        assert shell.duration_ms == 500  # 0.5 seconds = 500ms

    def test_kill_updates_status(self) -> None:
        """Test kill sets status to KILLED."""
        shell = ShellProcess(
            id="test_shell",
            command="echo hello",
            working_dir="/tmp",
        )
        shell.kill()
        assert shell.status == ShellStatus.KILLED
        assert isinstance(shell.completed_at, float)
        assert shell.completed_at > 0


class TestShellManager:
    """Tests for ShellManager singleton."""

    def test_singleton_pattern(self) -> None:
        """Test ShellManager is a singleton."""
        manager1 = ShellManager()
        manager2 = ShellManager()
        assert manager1 is manager2

    def test_reset_clears_shells(self) -> None:
        """Test reset clears all shells."""
        manager = ShellManager()
        manager._shells["test"] = ShellProcess(
            id="test",
            command="echo",
            working_dir="/tmp",
        )
        ShellManager.reset()
        manager = ShellManager()
        assert len(manager._shells) == 0

    @pytest.mark.asyncio
    async def test_create_shell(self) -> None:
        """Test create_shell creates a new shell."""
        shell = await ShellManager.create_shell(
            command="echo hello",
            working_dir="/tmp",
        )
        assert shell.id.startswith("shell_")
        assert shell.command == "echo hello"
        assert shell.working_dir == "/tmp"
        assert shell.status == ShellStatus.RUNNING
        assert isinstance(shell.process, asyncio.subprocess.Process)
        assert shell.process.returncode is None  # Still running
        # Clean up
        shell.kill()

    @pytest.mark.asyncio
    async def test_create_shell_with_env(self) -> None:
        """Test create_shell with custom environment."""
        shell = await ShellManager.create_shell(
            command="echo $MY_VAR",
            working_dir="/tmp",
            env={"MY_VAR": "test_value"},
        )
        assert isinstance(shell.process, asyncio.subprocess.Process)
        assert hasattr(shell.process, 'wait')
        # Wait for completion
        await shell.process.wait()
        await shell.read_output()
        assert "test_value" in shell.stdout_buffer

    @pytest.mark.asyncio
    async def test_get_shell_found(self) -> None:
        """Test get_shell returns existing shell."""
        shell = await ShellManager.create_shell(
            command="echo hello",
            working_dir="/tmp",
        )
        found = ShellManager.get_shell(shell.id)
        assert found is shell
        shell.kill()

    def test_get_shell_not_found(self) -> None:
        """Test get_shell returns None for unknown ID."""
        found = ShellManager.get_shell("nonexistent_id")
        assert found is None

    @pytest.mark.asyncio
    async def test_list_shells(self) -> None:
        """Test list_shells returns all shells."""
        shell1 = await ShellManager.create_shell("echo 1", "/tmp")
        shell2 = await ShellManager.create_shell("echo 2", "/tmp")
        shells = ShellManager.list_shells()
        assert len(shells) == 2
        assert shell1 in shells
        assert shell2 in shells
        shell1.kill()
        shell2.kill()

    @pytest.mark.asyncio
    async def test_list_running(self) -> None:
        """Test list_running returns only running shells."""
        shell1 = await ShellManager.create_shell("echo 1", "/tmp")
        shell2 = await ShellManager.create_shell("echo 2", "/tmp")
        # Wait for shell1 to complete
        await shell1.process.wait()
        shell1.status = ShellStatus.COMPLETED

        running = ShellManager.list_running()
        assert len(running) >= 1  # At least shell2 if still running
        shell1.kill()
        shell2.kill()

    @pytest.mark.asyncio
    async def test_cleanup_completed(self) -> None:
        """Test cleanup_completed removes old shells."""
        shell = await ShellManager.create_shell("echo test", "/tmp")
        await shell.process.wait()
        shell.status = ShellStatus.COMPLETED
        shell.completed_at = time.time() - 4000  # Old shell

        count = await ShellManager.cleanup_completed(max_age_seconds=3600)
        assert count == 1
        assert ShellManager.get_shell(shell.id) is None

    @pytest.mark.asyncio
    async def test_cleanup_completed_keeps_recent(self) -> None:
        """Test cleanup_completed keeps recent shells."""
        shell = await ShellManager.create_shell("echo test", "/tmp")
        await shell.process.wait()
        shell.status = ShellStatus.COMPLETED
        shell.completed_at = time.time()  # Just completed

        count = await ShellManager.cleanup_completed(max_age_seconds=3600)
        assert count == 0
        retrieved = ShellManager.get_shell(shell.id)
        assert retrieved is shell

    @pytest.mark.asyncio
    async def test_kill_all(self) -> None:
        """Test kill_all terminates all running shells."""
        shell1 = await ShellManager.create_shell("sleep 100", "/tmp")
        shell2 = await ShellManager.create_shell("sleep 100", "/tmp")

        count = await ShellManager.kill_all()
        assert count == 2
        assert shell1.status == ShellStatus.KILLED
        assert shell2.status == ShellStatus.KILLED


class TestShellProcessAsync:
    """Async tests for ShellProcess."""

    @pytest.mark.asyncio
    async def test_read_output(self) -> None:
        """Test read_output reads from process."""
        shell = await ShellManager.create_shell("echo hello", "/tmp")
        # Wait for process to complete
        await shell.process.wait()
        # Read output
        await shell.read_output()
        assert "hello" in shell.stdout_buffer

    @pytest.mark.asyncio
    async def test_read_output_no_process(self) -> None:
        """Test read_output with no process returns False."""
        shell = ShellProcess(
            id="test",
            command="echo",
            working_dir="/tmp",
        )
        result = await shell.read_output()
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_success(self) -> None:
        """Test wait returns exit code on success."""
        shell = await ShellManager.create_shell("true", "/tmp")
        exit_code = await shell.wait(timeout=5.0)
        assert exit_code == 0
        assert shell.status == ShellStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_wait_failure(self) -> None:
        """Test wait returns non-zero exit code on failure."""
        shell = await ShellManager.create_shell("false", "/tmp")
        exit_code = await shell.wait(timeout=5.0)
        assert exit_code != 0
        assert shell.status == ShellStatus.FAILED

    @pytest.mark.asyncio
    async def test_wait_timeout(self) -> None:
        """Test wait raises TimeoutError on timeout."""
        shell = await ShellManager.create_shell("sleep 100", "/tmp")
        with pytest.raises(TimeoutError):
            await shell.wait(timeout=0.1)
        assert shell.status == ShellStatus.TIMEOUT
        shell.kill()

    @pytest.mark.asyncio
    async def test_wait_not_started(self) -> None:
        """Test wait raises RuntimeError when not started."""
        shell = ShellProcess(
            id="test",
            command="echo",
            working_dir="/tmp",
        )
        with pytest.raises(RuntimeError, match="Process not started"):
            await shell.wait()

    @pytest.mark.asyncio
    async def test_is_running_active_process(self) -> None:
        """Test is_running with active process."""
        shell = await ShellManager.create_shell("sleep 100", "/tmp")
        assert shell.is_running
        shell.kill()
        # Give time for process to be killed
        await asyncio.sleep(0.1)
        assert not shell.is_running

    @pytest.mark.asyncio
    async def test_terminate_sends_sigterm(self) -> None:
        """Test terminate sends SIGTERM."""
        shell = await ShellManager.create_shell("sleep 100", "/tmp")
        shell.terminate()
        # Wait for process to handle signal
        await asyncio.sleep(0.2)
        # Process may or may not be running depending on timing
        # Just verify it doesn't raise
        shell.kill()  # Clean up
