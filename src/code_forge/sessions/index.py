"""Session index for fast listing and search."""

from __future__ import annotations

import builtins
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Session
    from .storage import SessionStorage

# Alias builtins.list to avoid shadowing by method
_list = builtins.list

logger = logging.getLogger(__name__)


@dataclass
class SessionSummary:
    """Summary of a session for listing.

    Contains key metadata without full message history.
    """

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int
    tags: list[str] = field(default_factory=list)
    working_dir: str = ""
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "tags": self.tags,
            "working_dir": self.working_dir,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSummary:
        """Deserialize from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(UTC)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now(UTC)

        return cls(
            id=data["id"],
            title=data.get("title", ""),
            created_at=created_at,
            updated_at=updated_at,
            message_count=data.get("message_count", 0),
            total_tokens=data.get("total_tokens", 0),
            tags=data.get("tags", []),
            working_dir=data.get("working_dir", ""),
            model=data.get("model", ""),
        )

    @classmethod
    def from_session(cls, session: Session) -> SessionSummary:
        """Create summary from a full Session.

        Args:
            session: The session to summarize.

        Returns:
            SessionSummary instance.
        """
        return cls(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            total_tokens=session.total_tokens,
            tags=list(session.tags),
            working_dir=session.working_dir,
            model=session.model,
        )


class SessionIndex:
    """Index of sessions for fast lookup and filtering.

    Maintains an in-memory index backed by a JSON file for
    fast session listing without loading full session files.

    Attributes:
        storage: The SessionStorage instance.
        _index: In-memory index data.
        _dirty: Whether index needs to be saved.
    """

    INDEX_FILE = "index.json"
    INDEX_VERSION = 1
    SAVE_DEBOUNCE_SECONDS = 5.0  # Minimum seconds between saves

    def __init__(self, storage: SessionStorage) -> None:
        """Initialize session index.

        Args:
            storage: SessionStorage instance to use.
        """
        self.storage = storage
        self._index: dict[str, SessionSummary] = {}
        self._dirty = False
        self._last_save_time: float = 0.0
        self._load_index()

    @property
    def index_path(self) -> Path:
        """Path to the index file."""
        return self.storage.storage_dir / self.INDEX_FILE

    def _load_index(self) -> None:
        """Load index from disk."""
        if not self.index_path.exists():
            logger.debug("No index file, starting fresh")
            return

        try:
            with self.index_path.open(encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("version", 0)
            if version != self.INDEX_VERSION:
                logger.info("Index version mismatch, rebuilding")
                self.rebuild()
                return

            sessions = data.get("sessions", {})
            for session_id, summary_data in sessions.items():
                summary_data["id"] = session_id
                self._index[session_id] = SessionSummary.from_dict(summary_data)

            logger.debug(f"Loaded index with {len(self._index)} sessions")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load index, rebuilding: {e}")
            self.rebuild()

    def _save_index(self) -> None:
        """Save index to disk."""
        data = {
            "version": self.INDEX_VERSION,
            "sessions": {
                sid: summary.to_dict() for sid, summary in self._index.items()
            },
        }

        try:
            with self.index_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._dirty = False
            logger.debug(f"Saved index with {len(self._index)} sessions")
        except OSError as e:
            logger.error(f"Failed to save index: {e}")

    def rebuild(self) -> None:
        """Rebuild the index from session files.

        Reads all session files to create fresh index data.
        Logs warnings for any corrupted sessions that cannot be loaded.
        """
        self._index.clear()
        corrupted_count = 0

        for session_id in self.storage.list_session_ids():
            session = self.storage.load_or_none(session_id)
            if session:
                self._index[session_id] = SessionSummary.from_session(session)
            else:
                # Session file exists but couldn't be loaded (corrupted)
                corrupted_count += 1
                logger.warning(
                    f"Skipped corrupted session during rebuild: {session_id}"
                )

        self._dirty = True
        self._save_index()

        if corrupted_count > 0:
            logger.warning(
                f"Rebuilt index with {len(self._index)} sessions "
                f"({corrupted_count} corrupted sessions skipped)"
            )
        else:
            logger.info(f"Rebuilt index with {len(self._index)} sessions")

    def add(self, session: Session) -> None:
        """Add or update a session in the index.

        Args:
            session: The session to add.
        """
        self._index[session.id] = SessionSummary.from_session(session)
        self._dirty = True

    def update(self, session: Session) -> None:
        """Update a session in the index.

        Args:
            session: The session to update.
        """
        self.add(session)  # Same operation

    def remove(self, session_id: str) -> bool:
        """Remove a session from the index.

        Args:
            session_id: The session ID to remove.

        Returns:
            True if session was in index.
        """
        if session_id in self._index:
            del self._index[session_id]
            self._dirty = True
            return True
        return False

    def get(self, session_id: str) -> SessionSummary | None:
        """Get a session summary by ID.

        Args:
            session_id: The session ID.

        Returns:
            SessionSummary or None if not found.
        """
        return self._index.get(session_id)

    def count(self) -> int:
        """Get the number of indexed sessions.

        Returns:
            Number of sessions.
        """
        return len(self._index)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        descending: bool = True,
        tags: _list[str] | None = None,
        search: str | None = None,
        working_dir: str | None = None,
    ) -> _list[SessionSummary]:
        """List sessions with filtering and pagination.

        Args:
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.
            sort_by: Field to sort by (updated_at, created_at, title).
            descending: Sort in descending order.
            tags: Filter to sessions with all these tags.
            search: Search string for title matching.
            working_dir: Filter to sessions in this directory.

        Returns:
            List of SessionSummary objects.
        """
        # Filter sessions
        summaries = _list(self._index.values())

        if tags:
            summaries = [
                s for s in summaries if all(tag in s.tags for tag in tags)
            ]

        if search:
            search_lower = search.lower()
            summaries = [s for s in summaries if search_lower in s.title.lower()]

        if working_dir:
            summaries = [s for s in summaries if s.working_dir == working_dir]

        # Sort
        sort_key = {
            "updated_at": lambda s: s.updated_at,
            "created_at": lambda s: s.created_at,
            "title": lambda s: s.title.lower(),
            "message_count": lambda s: s.message_count,
            "total_tokens": lambda s: s.total_tokens,
        }.get(sort_by, lambda s: s.updated_at)

        summaries.sort(key=sort_key, reverse=descending)

        # Paginate
        return summaries[offset : offset + limit]

    def get_recent(self, count: int = 10) -> _list[SessionSummary]:
        """Get the most recently updated sessions.

        Args:
            count: Number of sessions to return.

        Returns:
            List of SessionSummary objects.
        """
        return self.list(limit=count, sort_by="updated_at", descending=True)

    def get_by_working_dir(self, working_dir: str) -> _list[SessionSummary]:
        """Get sessions for a specific working directory.

        Args:
            working_dir: The working directory path.

        Returns:
            List of SessionSummary objects.
        """
        return self.list(working_dir=working_dir, limit=1000)

    def save_if_dirty(self, force: bool = False) -> bool:
        """Save the index if modified and debounce period has passed.

        Uses debouncing to avoid excessive disk I/O when multiple
        operations happen in quick succession.

        Args:
            force: If True, save immediately regardless of debounce.

        Returns:
            True if index was saved, False if skipped.
        """
        if not self._dirty:
            return False

        current_time = time.monotonic()
        time_since_last = current_time - self._last_save_time

        if not force and time_since_last < self.SAVE_DEBOUNCE_SECONDS:
            logger.debug(
                "Skipping index save (%.1fs since last save, debounce=%.1fs)",
                time_since_last,
                self.SAVE_DEBOUNCE_SECONDS,
            )
            return False

        self._save_index()
        self._last_save_time = current_time
        return True

    def force_save(self) -> bool:
        """Force save the index immediately, bypassing debounce.

        Returns:
            True if index was saved, False if not dirty.
        """
        return self.save_if_dirty(force=True)

    def __len__(self) -> int:
        """Number of indexed sessions."""
        return len(self._index)

    def __contains__(self, session_id: str) -> bool:
        """Check if session is in index."""
        return session_id in self._index
