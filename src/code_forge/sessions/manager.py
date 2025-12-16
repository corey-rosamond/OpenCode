"""Session lifecycle management."""

from __future__ import annotations

import asyncio
import atexit
import logging
import threading
import weakref
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .index import SessionIndex, SessionSummary
from .models import Session, SessionMessage, ToolInvocation
from .storage import SessionNotFoundError, SessionStorage

logger = logging.getLogger(__name__)

# Track active managers for cleanup at exit
_active_managers: weakref.WeakSet[SessionManager] = weakref.WeakSet()


def _cleanup_managers() -> None:
    """Cleanup all active session managers at exit."""
    for manager in list(_active_managers):
        try:
            if manager.current_session:
                manager.save()
                logger.debug(f"Saved session {manager.current_session.id} at exit")
        except Exception as e:
            logger.warning(f"Failed to save session at exit: {e}")


atexit.register(_cleanup_managers)


class SessionManager:
    """Manages session lifecycle.

    Central manager for creating, resuming, saving, and listing
    sessions. Provides auto-save functionality and session hooks.

    Attributes:
        storage: SessionStorage instance.
        index: SessionIndex instance.
        current_session: Currently active session, if any.
    """

    _instance: SessionManager | None = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        storage: SessionStorage | None = None,
        auto_save_interval: float = 60.0,
    ) -> None:
        """Initialize session manager.

        Args:
            storage: SessionStorage instance. Creates default if None.
            auto_save_interval: Auto-save interval in seconds. 0 to disable.
        """
        self.storage = storage or SessionStorage()
        self.index = SessionIndex(self.storage)
        self.current_session: Session | None = None

        self._auto_save_interval = auto_save_interval
        self._auto_save_task: asyncio.Task[None] | None = None
        self._hooks: dict[str, list[Callable[..., Any]]] = {
            "session:start": [],
            "session:end": [],
            "session:message": [],
            "session:save": [],
        }

        # Register for cleanup at exit
        _active_managers.add(self)

    @classmethod
    def get_instance(cls) -> SessionManager:
        """Get the singleton SessionManager instance.

        Returns:
            The SessionManager singleton.
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None

    def create(
        self,
        *,
        title: str = "",
        working_dir: str | None = None,
        model: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            title: Session title. Auto-generated if empty.
            working_dir: Working directory. Uses cwd if None.
            model: LLM model to use.
            tags: Initial tags.
            metadata: Initial metadata.

        Returns:
            The new Session.
        """
        if working_dir is None:
            working_dir = str(Path.cwd())

        session = Session(
            title=title,
            working_dir=working_dir,
            model=model,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Save immediately
        self.storage.save(session)
        self.index.add(session)
        self.index.save_if_dirty()

        # Set as current and start auto-save
        self.current_session = session
        self._start_auto_save()

        # Fire hooks
        self._fire_hook("session:start", session)

        logger.info(f"Created session {session.id}")
        return session

    def resume(self, session_id: str) -> Session:
        """Resume an existing session.

        Args:
            session_id: The session ID to resume.

        Returns:
            The resumed Session.

        Raises:
            SessionNotFoundError: If session doesn't exist.
        """
        session = self.storage.load(session_id)

        # Update access time
        session._mark_updated()
        self.storage.save(session)
        self.index.update(session)
        self.index.save_if_dirty()

        # Set as current and start auto-save
        self.current_session = session
        self._start_auto_save()

        # Fire hooks
        self._fire_hook("session:start", session)

        logger.info(f"Resumed session {session.id}")
        return session

    def resume_latest(self) -> Session | None:
        """Resume the most recently updated session.

        Returns:
            The resumed Session, or None if no sessions exist.
        """
        recent = self.index.get_recent(count=1)
        if not recent:
            return None

        try:
            return self.resume(recent[0].id)
        except SessionNotFoundError:
            # Index was stale, rebuild and try again
            self.index.rebuild()
            recent = self.index.get_recent(count=1)
            if recent:
                return self.resume(recent[0].id)
            return None

    def resume_or_create(
        self,
        *,
        working_dir: str | None = None,
        model: str = "",
    ) -> Session:
        """Resume the latest session or create a new one.

        Args:
            working_dir: Working directory for new session.
            model: Model for new session.

        Returns:
            A Session (existing or new).
        """
        session = self.resume_latest()
        if session is None:
            session = self.create(working_dir=working_dir, model=model)
        return session

    def save(self, session: Session | None = None) -> None:
        """Save a session.

        Args:
            session: The session to save. Uses current if None.
        """
        if session is None:
            session = self.current_session

        if session is None:
            logger.warning("No session to save")
            return

        self.storage.save(session)
        self.index.update(session)
        self.index.save_if_dirty()

        self._fire_hook("session:save", session)
        logger.debug(f"Saved session {session.id}")

    def close(self, session: Session | None = None) -> None:
        """Close a session.

        Saves the session and stops auto-save if it's the current session.

        Args:
            session: The session to close. Uses current if None.
        """
        if session is None:
            session = self.current_session

        if session is None:
            return

        # Save final state
        self.save(session)

        # Fire hooks
        self._fire_hook("session:end", session)

        # Stop auto-save if closing current session
        if session is self.current_session:
            self._stop_auto_save()
            self.current_session = None

        logger.info(f"Closed session {session.id}")

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if session was deleted.
        """
        # Close if it's the current session
        if self.current_session and self.current_session.id == session_id:
            self._stop_auto_save()
            self.current_session = None

        # Remove from storage and index
        deleted = self.storage.delete(session_id)
        self.index.remove(session_id)
        self.index.save_if_dirty()

        if deleted:
            logger.info(f"Deleted session {session_id}")

        return deleted

    def list_sessions(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        descending: bool = True,
        tags: list[str] | None = None,
        search: str | None = None,
    ) -> list[SessionSummary]:
        """List sessions with filtering and pagination.

        Args:
            limit: Maximum number of sessions.
            offset: Number to skip.
            sort_by: Sort field.
            descending: Sort direction.
            tags: Filter by tags.
            search: Search string.

        Returns:
            List of SessionSummary objects.
        """
        return self.index.list(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            descending=descending,
            tags=tags,
            search=search,
        )

    def get_session(self, session_id: str) -> Session | None:
        """Get a full session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The Session, or None if not found.
        """
        return self.storage.load_or_none(session_id)

    def add_message(
        self,
        role: str,
        content: str,
        session: Session | None = None,
        **kwargs: Any,
    ) -> SessionMessage:
        """Add a message to a session.

        Args:
            role: Message role.
            content: Message content.
            session: Target session. Uses current if None.
            **kwargs: Additional message fields.

        Returns:
            The created SessionMessage.

        Raises:
            ValueError: If no session is available.
        """
        if session is None:
            session = self.current_session

        if session is None:
            raise ValueError("No session available")

        message = session.add_message_from_dict(role, content, **kwargs)

        self._fire_hook("session:message", session, message)

        return message

    def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None = None,
        duration: float = 0.0,
        success: bool = True,
        error: str | None = None,
        session: Session | None = None,
    ) -> ToolInvocation:
        """Record a tool invocation.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.
            result: Tool result.
            duration: Execution duration.
            success: Whether successful.
            error: Error message if failed.
            session: Target session. Uses current if None.

        Returns:
            The created ToolInvocation.

        Raises:
            ValueError: If no session is available.
        """
        if session is None:
            session = self.current_session

        if session is None:
            raise ValueError("No session available")

        return session.record_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            duration=duration,
            success=success,
            error=error,
        )

    def update_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        session: Session | None = None,
    ) -> None:
        """Update token usage.

        Args:
            prompt_tokens: Prompt tokens used.
            completion_tokens: Completion tokens used.
            session: Target session. Uses current if None.
        """
        if session is None:
            session = self.current_session

        if session:
            session.update_usage(prompt_tokens, completion_tokens)

    def generate_title(self, session: Session) -> str:
        """Generate a title for a session.

        Uses the first user message to generate a title.
        Falls back to timestamp-based title.

        Args:
            session: The session to title.

        Returns:
            The generated title.
        """
        # Find first user message
        for msg in session.messages:
            if msg.role == "user" and msg.content:
                # Use first line, truncated
                title = msg.content.split("\n")[0]
                if len(title) > 50:
                    title = title[:47] + "..."
                return title

        # Fallback to timestamp
        return f"Session {session.created_at.strftime('%Y-%m-%d %H:%M')}"

    def set_title(self, title: str, session: Session | None = None) -> None:
        """Set session title.

        Args:
            title: The new title.
            session: Target session. Uses current if None.
        """
        if session is None:
            session = self.current_session

        if session:
            session.title = title
            session._mark_updated()

    def add_tag(self, tag: str, session: Session | None = None) -> None:
        """Add a tag to a session.

        Args:
            tag: The tag to add.
            session: Target session. Uses current if None.
        """
        if session is None:
            session = self.current_session

        if session and tag not in session.tags:
            session.tags.append(tag)
            session._mark_updated()

    def remove_tag(self, tag: str, session: Session | None = None) -> bool:
        """Remove a tag from a session.

        Args:
            tag: The tag to remove.
            session: Target session. Uses current if None.

        Returns:
            True if tag was removed.
        """
        if session is None:
            session = self.current_session

        if session and tag in session.tags:
            session.tags.remove(tag)
            session._mark_updated()
            return True
        return False

    @property
    def has_current(self) -> bool:
        """Check if there's a current session."""
        return self.current_session is not None

    def register_hook(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a session lifecycle hook.

        Args:
            event: Event name (session:start, session:end, etc.)
            callback: Callback function.
        """
        if event in self._hooks:
            self._hooks[event].append(callback)

    def unregister_hook(self, event: str, callback: Callable[..., Any]) -> bool:
        """Unregister a session lifecycle hook.

        Args:
            event: Event name.
            callback: Callback to remove.

        Returns:
            True if callback was removed.
        """
        if event in self._hooks and callback in self._hooks[event]:
            self._hooks[event].remove(callback)
            return True
        return False

    def _fire_hook(self, event: str, *args: Any) -> None:
        """Fire registered hooks for an event.

        Args:
            event: Event name.
            *args: Arguments to pass to callbacks.
        """
        for callback in self._hooks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Hook error for {event}: {e}")

    def _start_auto_save(self) -> None:
        """Start the auto-save task."""
        if self._auto_save_interval <= 0:
            return

        self._stop_auto_save()

        async def auto_save_loop() -> None:
            try:
                while True:
                    await asyncio.sleep(self._auto_save_interval)
                    if self.current_session:
                        try:
                            self.save(self.current_session)
                        except Exception as e:
                            # Log but don't crash auto-save loop
                            logger.warning(f"Auto-save failed: {e}")
            except asyncio.CancelledError:
                # Clean cancellation is expected
                pass

        try:
            loop = asyncio.get_running_loop()
            self._auto_save_task = loop.create_task(auto_save_loop())
        except RuntimeError:
            # No running loop, skip auto-save
            pass

    def _stop_auto_save(self) -> None:
        """Stop the auto-save task."""
        if self._auto_save_task:
            self._auto_save_task.cancel()
            # Don't await - could block, and cancellation is fire-and-forget
            self._auto_save_task = None

    def __del__(self) -> None:
        """Cleanup: ensure auto-save is stopped and session is saved.

        Attempts a synchronous save as a last resort if session wasn't
        closed properly. The atexit handler provides more reliable cleanup.
        """
        self._stop_auto_save()
        # Attempt sync save as last resort (atexit handler is more reliable)
        try:
            if self.current_session:
                self.save()
        except Exception:
            # Can't do much in __del__ - atexit handler should have saved
            pass
