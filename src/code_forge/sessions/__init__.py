"""Session management package.

This package provides session persistence and management for Code-Forge.
Sessions store conversation history, tool invocations, and metadata.

Example:
    from code_forge.sessions import SessionManager

    manager = SessionManager.get_instance()

    # Create new session
    session = manager.create(title="My session", model="anthropic/claude-3-opus")

    # Add messages
    manager.add_message("user", "Hello!")
    manager.add_message("assistant", "Hi there!")

    # Save and close
    manager.close()

    # Later, resume
    session = manager.resume(session.id)
"""

from .index import SessionIndex, SessionSummary
from .manager import SessionManager
from .models import Session, SessionMessage, ToolInvocation
from .repository import SessionRepository
from .storage import (
    SessionCorruptedError,
    SessionNotFoundError,
    SessionStorage,
    SessionStorageError,
)

__all__ = [
    "Session",
    "SessionCorruptedError",
    "SessionIndex",
    "SessionManager",
    "SessionMessage",
    "SessionNotFoundError",
    "SessionRepository",
    "SessionStorage",
    "SessionStorageError",
    "SessionSummary",
    "ToolInvocation",
]
