"""Session repository implementing the ISessionRepository interface.

This module provides an async repository layer on top of the sync SessionStorage.
It implements the ISessionRepository interface for dependency injection and testing.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING

from code_forge.core.interfaces import ISessionRepository
from code_forge.core.types import SessionId

from .index import SessionSummary
from .storage import SessionStorage

if TYPE_CHECKING:
    from code_forge.core.types import SessionSummary as CoreSessionSummary

    from .models import Session


class SessionRepository(ISessionRepository):
    """Async repository for session persistence.

    Wraps SessionStorage to provide an async interface that implements
    ISessionRepository. Uses a thread pool for non-blocking I/O operations.

    Attributes:
        storage: The underlying sync storage instance.
    """

    def __init__(
        self,
        storage: SessionStorage | None = None,
        max_workers: int = 4,
    ) -> None:
        """Initialize session repository.

        Args:
            storage: SessionStorage instance. Creates default if None.
            max_workers: Maximum thread pool workers for async operations.
        """
        self._storage = storage or SessionStorage()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    @property
    def storage(self) -> SessionStorage:
        """Get underlying storage instance."""
        return self._storage

    async def save(self, session: Session) -> None:
        """Persist session to storage.

        Args:
            session: The session to save.

        Raises:
            SessionStorageError: If save fails.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor,
            partial(self._storage.save, session),
        )

    async def load(self, session_id: SessionId) -> Session | None:
        """Load session by ID.

        Args:
            session_id: The ID of the session to load.

        Returns:
            The session if found, None otherwise.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(self._storage.load_or_none, str(session_id)),
        )

    async def list_recent(self, limit: int = 10) -> list[SessionSummary]:
        """List recent sessions with summaries.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of session summaries, sorted by last activity (newest first).
        """
        loop = asyncio.get_running_loop()

        # Get all session IDs
        session_ids = await loop.run_in_executor(
            self._executor,
            self._storage.list_session_ids,
        )

        # Load sessions and build summaries
        summaries: list[SessionSummary] = []
        for session_id in session_ids:
            session = await loop.run_in_executor(
                self._executor,
                partial(self._storage.load_or_none, session_id),
            )
            if session is not None:
                summaries.append(SessionSummary.from_session(session))

        # Sort by updated_at (newest first) and limit
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries[:limit]

    async def delete(self, session_id: SessionId) -> bool:
        """Delete session.

        Args:
            session_id: The ID of the session to delete.

        Returns:
            True if deleted, False if not found.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(self._storage.delete, str(session_id)),
        )

    async def exists(self, session_id: SessionId) -> bool:
        """Check if session exists.

        Args:
            session_id: The ID to check.

        Returns:
            True if session exists.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(self._storage.exists, str(session_id)),
        )

    def close(self) -> None:
        """Shutdown the thread pool executor."""
        self._executor.shutdown(wait=True)

    async def __aenter__(self) -> SessionRepository:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        self.close()
