"""Async tests for SessionRepository.

Tests the async repository layer that wraps sync SessionStorage with
ThreadPoolExecutor for non-blocking I/O operations.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.sessions.repository import SessionRepository
from code_forge.sessions.storage import SessionStorage

if TYPE_CHECKING:
    from pathlib import Path


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock SessionStorage."""
    storage = MagicMock(spec=SessionStorage)
    storage.save = MagicMock()
    storage.load_or_none = MagicMock()
    storage.list_session_ids = MagicMock(return_value=[])
    storage.delete = MagicMock(return_value=True)
    storage.exists = MagicMock(return_value=True)
    return storage


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock Session."""
    session = MagicMock()
    session.id = "test-session-123"
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)
    return session


@pytest.fixture
def repository(mock_storage: MagicMock) -> SessionRepository:
    """Create repository with mock storage."""
    return SessionRepository(storage=mock_storage, max_workers=2)


# =============================================================================
# Test SessionRepository Initialization
# =============================================================================


class TestSessionRepositoryInit:
    """Tests for SessionRepository initialization."""

    def test_init_with_custom_storage(self, mock_storage: MagicMock) -> None:
        """Repository uses provided storage."""
        repo = SessionRepository(storage=mock_storage)
        assert repo.storage is mock_storage

    def test_init_creates_default_storage(self) -> None:
        """Repository creates default storage if none provided."""
        with patch("code_forge.sessions.repository.SessionStorage") as mock_cls:
            mock_cls.return_value = MagicMock()
            repo = SessionRepository()
            mock_cls.assert_called_once()
            assert repo.storage is mock_cls.return_value

    def test_init_with_custom_max_workers(self, mock_storage: MagicMock) -> None:
        """Repository uses custom max_workers."""
        repo = SessionRepository(storage=mock_storage, max_workers=8)
        assert repo._executor._max_workers == 8

    def test_storage_property_returns_storage(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Storage property returns underlying storage."""
        assert repository.storage is mock_storage


# =============================================================================
# Test Async Save Operation
# =============================================================================


class TestSessionRepositorySave:
    """Tests for async save operation."""

    @pytest.mark.asyncio
    async def test_save_delegates_to_storage(
        self, repository: SessionRepository, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Save delegates to storage in executor."""
        await repository.save(mock_session)
        mock_storage.save.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_save_runs_in_executor(
        self, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Save operation runs in thread pool executor."""
        executor = MagicMock(spec=ThreadPoolExecutor)
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_event_loop.run_in_executor = AsyncMock()
            mock_loop.return_value = mock_event_loop

            repo = SessionRepository(storage=mock_storage, max_workers=2)
            repo._executor = executor

            await repo.save(mock_session)

            mock_event_loop.run_in_executor.assert_called_once()
            call_args = mock_event_loop.run_in_executor.call_args
            assert call_args[0][0] is executor

    @pytest.mark.asyncio
    async def test_save_propagates_storage_error(
        self, repository: SessionRepository, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Save propagates errors from storage."""
        mock_storage.save.side_effect = RuntimeError("Storage error")
        with pytest.raises(RuntimeError, match="Storage error"):
            await repository.save(mock_session)

    @pytest.mark.asyncio
    async def test_concurrent_saves(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Multiple concurrent saves are handled correctly."""
        sessions = [MagicMock(id=f"session-{i}") for i in range(5)]

        await asyncio.gather(*[repository.save(s) for s in sessions])

        assert mock_storage.save.call_count == 5


# =============================================================================
# Test Async Load Operation
# =============================================================================


class TestSessionRepositoryLoad:
    """Tests for async load operation."""

    @pytest.mark.asyncio
    async def test_load_returns_session(
        self, repository: SessionRepository, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Load returns session from storage."""
        mock_storage.load_or_none.return_value = mock_session

        result = await repository.load("test-session-123")

        assert result is mock_session
        mock_storage.load_or_none.assert_called_once_with("test-session-123")

    @pytest.mark.asyncio
    async def test_load_returns_none_for_missing(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Load returns None for missing session."""
        mock_storage.load_or_none.return_value = None

        result = await repository.load("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_converts_session_id_to_string(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Load converts session ID to string."""
        from uuid import uuid4
        session_id = uuid4()

        await repository.load(session_id)

        mock_storage.load_or_none.assert_called_once_with(str(session_id))

    @pytest.mark.asyncio
    async def test_concurrent_loads(
        self, repository: SessionRepository, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Multiple concurrent loads are handled correctly."""
        mock_storage.load_or_none.return_value = mock_session
        session_ids = [f"session-{i}" for i in range(5)]

        results = await asyncio.gather(*[repository.load(sid) for sid in session_ids])

        assert len(results) == 5
        assert all(r is mock_session for r in results)


# =============================================================================
# Test Async List Recent Operation
# =============================================================================


class TestSessionRepositoryListRecent:
    """Tests for async list_recent operation."""

    @pytest.mark.asyncio
    async def test_list_recent_returns_empty_list(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """List recent returns empty list when no sessions."""
        mock_storage.list_session_ids.return_value = []

        result = await repository.list_recent()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_recent_loads_all_sessions(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """List recent loads all session IDs from storage."""
        mock_storage.list_session_ids.return_value = ["s1", "s2", "s3"]
        mock_storage.load_or_none.return_value = None

        await repository.list_recent()

        assert mock_storage.load_or_none.call_count == 3

    @pytest.mark.asyncio
    async def test_list_recent_sorts_by_updated_at(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """List recent sorts sessions by updated_at descending."""
        sessions = []
        for i, days in enumerate([1, 3, 2]):  # Not in order
            s = MagicMock()
            s.id = f"session-{i}"
            s.created_at = datetime.now(UTC)
            s.updated_at = datetime(2024, 1, days, tzinfo=UTC)
            sessions.append(s)

        mock_storage.list_session_ids.return_value = ["s0", "s1", "s2"]
        mock_storage.load_or_none.side_effect = sessions

        result = await repository.list_recent()

        # Should be sorted newest first: day 3, day 2, day 1
        assert result[0].updated_at == datetime(2024, 1, 3, tzinfo=UTC)
        assert result[1].updated_at == datetime(2024, 1, 2, tzinfo=UTC)
        assert result[2].updated_at == datetime(2024, 1, 1, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_list_recent_respects_limit(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """List recent respects the limit parameter."""
        sessions = []
        for i in range(10):
            s = MagicMock()
            s.id = f"session-{i}"
            s.created_at = datetime.now(UTC)
            s.updated_at = datetime(2024, 1, i + 1, tzinfo=UTC)
            sessions.append(s)

        mock_storage.list_session_ids.return_value = [f"s{i}" for i in range(10)]
        mock_storage.load_or_none.side_effect = sessions

        result = await repository.list_recent(limit=3)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_recent_skips_none_sessions(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """List recent skips sessions that return None."""
        s = MagicMock()
        s.id = "valid"
        s.created_at = datetime.now(UTC)
        s.updated_at = datetime.now(UTC)

        mock_storage.list_session_ids.return_value = ["valid", "corrupt", "missing"]
        mock_storage.load_or_none.side_effect = [s, None, None]

        result = await repository.list_recent()

        assert len(result) == 1


# =============================================================================
# Test Async Delete Operation
# =============================================================================


class TestSessionRepositoryDelete:
    """Tests for async delete operation."""

    @pytest.mark.asyncio
    async def test_delete_delegates_to_storage(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Delete delegates to storage."""
        mock_storage.delete.return_value = True

        result = await repository.delete("session-123")

        assert result is True
        mock_storage.delete.assert_called_once_with("session-123")

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Delete returns False for missing session."""
        mock_storage.delete.return_value = False

        result = await repository.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_converts_session_id_to_string(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Delete converts session ID to string."""
        from uuid import uuid4
        session_id = uuid4()

        await repository.delete(session_id)

        mock_storage.delete.assert_called_once_with(str(session_id))


# =============================================================================
# Test Async Exists Operation
# =============================================================================


class TestSessionRepositoryExists:
    """Tests for async exists operation."""

    @pytest.mark.asyncio
    async def test_exists_returns_true(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Exists returns True when session exists."""
        mock_storage.exists.return_value = True

        result = await repository.exists("session-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Exists returns False when session doesn't exist."""
        mock_storage.exists.return_value = False

        result = await repository.exists("nonexistent")

        assert result is False


# =============================================================================
# Test Context Manager
# =============================================================================


class TestSessionRepositoryContextManager:
    """Tests for async context manager protocol."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(
        self, repository: SessionRepository
    ) -> None:
        """Async context manager enter returns self."""
        async with repository as repo:
            assert repo is repository

    @pytest.mark.asyncio
    async def test_aexit_calls_close(
        self, repository: SessionRepository
    ) -> None:
        """Async context manager exit calls close."""
        with patch.object(repository, "close") as mock_close:
            async with repository:
                pass
            mock_close.assert_called_once()


# =============================================================================
# Test Close Operation
# =============================================================================


class TestSessionRepositoryClose:
    """Tests for close operation."""

    def test_close_shuts_down_executor(
        self, repository: SessionRepository
    ) -> None:
        """Close shuts down thread pool executor."""
        with patch.object(repository._executor, "shutdown") as mock_shutdown:
            repository.close()
            mock_shutdown.assert_called_once_with(wait=True)

    def test_close_waits_for_pending_tasks(
        self, mock_storage: MagicMock
    ) -> None:
        """Close waits for pending tasks to complete."""
        repo = SessionRepository(storage=mock_storage, max_workers=2)

        # Submit some work to the executor
        futures = [repo._executor.submit(lambda: None) for _ in range(3)]

        repo.close()

        # All futures should be done
        assert all(f.done() for f in futures)


# =============================================================================
# Test Concurrent Operations
# =============================================================================


class TestSessionRepositoryConcurrency:
    """Tests for concurrent operation handling."""

    @pytest.mark.asyncio
    async def test_interleaved_operations(
        self, repository: SessionRepository, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Interleaved save/load operations work correctly."""
        mock_storage.load_or_none.return_value = mock_session

        operations = []
        for i in range(5):
            s = MagicMock(id=f"session-{i}")
            operations.append(repository.save(s))
            operations.append(repository.load(f"session-{i}"))

        await asyncio.gather(*operations)

        assert mock_storage.save.call_count == 5
        assert mock_storage.load_or_none.call_count == 5

    @pytest.mark.asyncio
    async def test_error_in_one_operation_doesnt_affect_others(
        self, repository: SessionRepository, mock_storage: MagicMock
    ) -> None:
        """Error in one operation doesn't affect concurrent operations."""
        call_count = 0

        def mock_exists(session_id: str) -> bool:
            nonlocal call_count
            call_count += 1
            if session_id == "error":
                raise RuntimeError("Test error")
            return True

        mock_storage.exists.side_effect = mock_exists

        tasks = [
            repository.exists("ok-1"),
            repository.exists("error"),
            repository.exists("ok-2"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert results[0] is True
        assert isinstance(results[1], RuntimeError)
        assert results[2] is True

    @pytest.mark.asyncio
    async def test_executor_thread_limit(
        self, mock_storage: MagicMock
    ) -> None:
        """Executor respects max_workers limit."""
        import threading
        max_concurrent = 0
        current_concurrent = 0
        lock = threading.Lock()

        def slow_exists(session_id: str) -> bool:
            nonlocal max_concurrent, current_concurrent
            with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            import time
            time.sleep(0.01)  # Small delay to allow concurrency

            with lock:
                current_concurrent -= 1
            return True

        mock_storage.exists.side_effect = slow_exists

        repo = SessionRepository(storage=mock_storage, max_workers=2)

        try:
            tasks = [repo.exists(f"session-{i}") for i in range(10)]
            await asyncio.gather(*tasks)

            # Max concurrent should be at most 2 (max_workers)
            assert max_concurrent <= 2
        finally:
            repo.close()


# =============================================================================
# Test Thread Safety
# =============================================================================


class TestSessionRepositoryThreadSafety:
    """Tests for thread safety of repository operations."""

    @pytest.mark.asyncio
    async def test_rapid_save_load_cycle(
        self, mock_storage: MagicMock, mock_session: MagicMock
    ) -> None:
        """Rapid save/load cycles don't cause race conditions."""
        mock_storage.load_or_none.return_value = mock_session

        repo = SessionRepository(storage=mock_storage, max_workers=4)

        try:
            for _ in range(10):
                await asyncio.gather(
                    repo.save(mock_session),
                    repo.load(mock_session.id),
                    repo.exists(mock_session.id),
                )
        finally:
            repo.close()

        # Should complete without errors
        assert mock_storage.save.call_count == 10

    @pytest.mark.asyncio
    async def test_close_during_operations(
        self, mock_storage: MagicMock
    ) -> None:
        """Close during pending operations doesn't cause issues."""
        import threading
        operation_started = threading.Event()

        def slow_save(session: MagicMock) -> None:
            operation_started.set()
            import time
            time.sleep(0.1)

        mock_storage.save.side_effect = slow_save

        repo = SessionRepository(storage=mock_storage, max_workers=1)

        # Start a slow operation
        task = asyncio.create_task(repo.save(MagicMock(id="test")))

        # Wait for it to start
        await asyncio.sleep(0.01)

        # Close while operation is running
        repo.close()

        # Operation should complete (close waits)
        await task
