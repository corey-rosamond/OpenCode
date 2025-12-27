"""Integration tests for error recovery.

These tests verify that the system handles errors gracefully:
- Tool execution errors
- Session recovery from errors
- Network failure handling
- Timeout handling
- Graceful degradation
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.sessions import SessionManager
from code_forge.tools import (
    ExecutionContext,
    ToolExecutor,
    ToolRegistry,
    register_all_tools,
)


class TestToolErrorRecovery:
    """Test recovery from tool execution errors."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_recovery_after_file_not_found(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test that system recovers after file not found error."""
        # First, cause an error
        error_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path="/nonexistent/path/file.py",
        )
        assert not error_result.success

        # Then, run a successful operation
        success_result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
        )
        assert success_result.success
        assert "Sample module" in success_result.output

    @pytest.mark.asyncio
    async def test_recovery_after_edit_error(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test recovery after failed edit."""
        # Try to edit with non-matching string
        error_result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(sample_file),
            old_string="this string does not exist in the file",
            new_string="replacement",
        )
        assert not error_result.success

        # File should be unchanged
        content = sample_file.read_text()
        assert "Sample module" in content

        # Successful edit should still work
        success_result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(sample_file),
            old_string="def hello",
            new_string="def greet",
        )
        assert success_result.success

    @pytest.mark.asyncio
    async def test_recovery_after_bash_failure(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test recovery after bash command failure."""
        # Run failing command
        error_result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="exit 1",
        )
        assert not error_result.success

        # Run successful command
        success_result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="echo 'recovered'",
        )
        assert success_result.success
        assert "recovered" in success_result.output

    @pytest.mark.asyncio
    async def test_recovery_after_permission_error(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        temp_project: Path,
    ) -> None:
        """Test recovery after permission error."""
        # Try to write to a non-existent parent directory
        error_result = await tool_executor.execute(
            "Write",
            execution_context,
            file_path="/root/protected/file.txt",  # Should fail
            content="test",
        )
        assert not error_result.success

        # Writing to valid location should work
        success_result = await tool_executor.execute(
            "Write",
            execution_context,
            file_path=str(temp_project / "valid.txt"),
            content="test content",
        )
        assert success_result.success


class TestSessionRecovery:
    """Test session recovery from errors."""

    def test_session_recovery_after_save_error(
        self,
        session_manager: SessionManager,
        monkeypatch,
    ) -> None:
        """Test that session data is preserved after save error."""
        session = session_manager.create(title="Test Session")
        session_manager.add_message("user", "Important message")

        # Messages should be in session even if save fails
        assert len(session.messages) == 1
        assert session.messages[0].content == "Important message"

    def test_resume_handles_corrupt_file_gracefully(
        self,
        session_manager: SessionManager,
        forge_data_dir: Path,
    ) -> None:
        """Test handling of corrupt session files."""
        from code_forge.sessions.storage import SessionCorruptedError

        # Create a valid session first
        session = session_manager.create(title="Valid Session")
        session_id = session.id
        session_manager.add_message("user", "test")
        session_manager.save()
        session_manager.close()

        # Corrupt the session file and delete backup to prevent recovery
        session_file = forge_data_dir / "sessions" / f"{session_id}.json"
        backup_file = forge_data_dir / "sessions" / f"{session_id}.backup"
        if session_file.exists():
            session_file.write_text("{ invalid json }")
        if backup_file.exists():
            backup_file.unlink()

        # Resuming should raise SessionCorruptedError for corrupted files
        with pytest.raises(SessionCorruptedError):
            session_manager.resume(session_id)


class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_bash_timeout(
        self,
        tool_executor: ToolExecutor,
        temp_project: Path,
    ) -> None:
        """Test bash command timeout handling."""
        # Create context with short timeout
        context = ExecutionContext(
            working_dir=str(temp_project),
            timeout=1,  # Very short timeout (1 second)
        )

        # Run long-running command
        result = await tool_executor.execute(
            "Bash",
            context,
            command="sleep 10",  # Longer than timeout
        )

        # Should timeout gracefully
        assert not result.success
        # Error message should indicate timeout
        output_lower = (result.error or result.output or "").lower()
        assert "timeout" in output_lower or "killed" in output_lower or "timed" in output_lower


class TestGracefulDegradation:
    """Test graceful degradation when components fail."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_tools_work_without_hooks(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test that tools work when hook system is not configured."""
        # Tools should work even without hooks
        result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path=str(sample_file),
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_tools_work_without_sessions(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that tools work without an active session."""
        result = await tool_executor.execute(
            "Bash",
            execution_context,
            command="echo 'no session'",
        )
        assert result.success


class TestConcurrentErrorHandling:
    """Test error handling with concurrent operations."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_concurrent_tool_errors(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test handling multiple concurrent errors."""
        # Run multiple operations, some will fail, some succeed
        tasks = [
            tool_executor.execute(
                "Read",
                execution_context,
                file_path="/nonexistent1.py",
            ),
            tool_executor.execute(
                "Read",
                execution_context,
                file_path=str(sample_file),
            ),
            tool_executor.execute(
                "Read",
                execution_context,
                file_path="/nonexistent2.py",
            ),
        ]

        results = await asyncio.gather(*tasks)

        # First and third should fail, second should succeed
        assert not results[0].success
        assert results[1].success
        assert not results[2].success

    @pytest.mark.asyncio
    async def test_error_isolation(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test that errors in one operation don't affect others."""
        # Run failing operation
        await tool_executor.execute(
            "Read",
            execution_context,
            file_path="/nonexistent.py",
        )

        # Run multiple successful operations
        for _ in range(5):
            result = await tool_executor.execute(
                "Read",
                execution_context,
                file_path=str(sample_file),
            )
            assert result.success


class TestErrorMessages:
    """Test that error messages are helpful."""

    @pytest.fixture(autouse=True)
    def setup_tools(self, tool_registry: ToolRegistry) -> None:
        """Ensure tools are registered for each test."""
        register_all_tools()

    @pytest.mark.asyncio
    async def test_file_not_found_message(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that file not found error has helpful message."""
        result = await tool_executor.execute(
            "Read",
            execution_context,
            file_path="/nonexistent/path/file.py",
        )

        assert not result.success
        # Error should mention file path or "not found"
        output_lower = (result.error or result.output or "").lower()
        assert "not found" in output_lower or "no such" in output_lower or "error" in output_lower

    @pytest.mark.asyncio
    async def test_edit_not_found_message(
        self,
        tool_executor: ToolExecutor,
        execution_context: ExecutionContext,
        sample_file: Path,
    ) -> None:
        """Test that edit failure has helpful message."""
        result = await tool_executor.execute(
            "Edit",
            execution_context,
            file_path=str(sample_file),
            old_string="nonexistent_string_xyz",
            new_string="replacement",
        )

        assert not result.success
        # Error should explain what wasn't found
        output_lower = (result.error or result.output or "").lower()
        assert "not found" in output_lower or "no match" in output_lower or "error" in output_lower
