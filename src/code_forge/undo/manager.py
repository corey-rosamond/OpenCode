"""Undo manager for file operations.

This module provides the UndoManager class that coordinates
capture, storage, and restoration of file state for undo/redo.

Example:
    from code_forge.undo.manager import UndoManager

    # Create manager
    manager = UndoManager()

    # Before modifying a file, capture its state
    manager.capture_before("/path/to/file.py")

    # After modification, commit the undo entry
    manager.commit("Edit", "Edit file.py", ["/path/to/file.py"])

    # Later, undo the change
    success, message = manager.undo()
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from .models import FileSnapshot, UndoEntry, UndoHistory

if TYPE_CHECKING:
    from code_forge.sessions.manager import SessionManager

logger = logging.getLogger(__name__)


class UndoManager:
    """Central manager for undo/redo operations.

    Coordinates file state capture before modifications and provides
    undo/redo functionality with session persistence.

    Attributes:
        max_entries: Maximum undo history entries.
        max_size_bytes: Maximum total size of undo data.
        max_file_size: Maximum single file size to capture.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        max_entries: int = 100,
        max_size_bytes: int = 52_428_800,  # 50MB
        max_file_size: int = 1_048_576,  # 1MB
        enabled: bool = True,
    ) -> None:
        """Initialize the undo manager.

        Args:
            session_manager: Optional session manager for persistence.
            max_entries: Maximum undo history entries.
            max_size_bytes: Maximum total size in bytes.
            max_file_size: Maximum single file size to capture.
            enabled: Whether undo is enabled.
        """
        self._session_manager = session_manager
        self._history = UndoHistory(
            max_entries=max_entries,
            max_size_bytes=max_size_bytes,
        )
        self._max_file_size = max_file_size
        self._enabled = enabled

        # Pending captures before commit
        self._pending_captures: dict[str, FileSnapshot] = {}

    @property
    def enabled(self) -> bool:
        """Check if undo is enabled.

        Returns:
            True if undo functionality is enabled.
        """
        return self._enabled

    @property
    def can_undo(self) -> bool:
        """Check if undo is available.

        Returns:
            True if there are operations to undo.
        """
        return self._enabled and self._history.can_undo

    @property
    def can_redo(self) -> bool:
        """Check if redo is available.

        Returns:
            True if there are operations to redo.
        """
        return self._enabled and self._history.can_redo

    @property
    def undo_count(self) -> int:
        """Get number of undoable operations.

        Returns:
            Number of entries in undo stack.
        """
        return len(self._history.undo_stack)

    @property
    def redo_count(self) -> int:
        """Get number of redoable operations.

        Returns:
            Number of entries in redo stack.
        """
        return len(self._history.redo_stack)

    def capture_before(self, file_path: str) -> bool:
        """Capture file state before modification.

        Should be called BEFORE any file modification.
        Captured state is held pending until commit() is called.

        Args:
            file_path: Path to the file to capture.

        Returns:
            True if capture succeeded, False otherwise.
        """
        if not self._enabled:
            return False

        abs_path = os.path.abspath(file_path)

        # Don't capture same file twice in same operation
        if abs_path in self._pending_captures:
            return True

        snapshot = FileSnapshot.capture(abs_path, max_size=self._max_file_size)
        if snapshot is None:
            logger.warning(f"Could not capture file for undo: {abs_path}")
            return False

        self._pending_captures[abs_path] = snapshot
        logger.debug(f"Captured file for undo: {abs_path}")
        return True

    def capture_multiple(self, file_paths: list[str]) -> dict[str, bool]:
        """Capture multiple files before modification.

        Args:
            file_paths: List of file paths to capture.

        Returns:
            Dictionary mapping file paths to success status.
        """
        return {path: self.capture_before(path) for path in file_paths}

    def commit(
        self,
        tool_name: str,
        description: str,
        file_paths: list[str] | None = None,
        command: str | None = None,
    ) -> UndoEntry | None:
        """Commit pending captures as a single undo entry.

        Creates an UndoEntry from captured file states and adds it
        to the undo history.

        Args:
            tool_name: Name of the tool (Edit, Write, Bash).
            description: Human-readable description.
            file_paths: If provided, only commit these files.
            command: For Bash operations, the command that was run.

        Returns:
            Created UndoEntry, or None if no captures to commit.
        """
        if not self._enabled:
            return None

        if not self._pending_captures:
            logger.debug("No pending captures to commit")
            return None

        # Determine which captures to include
        if file_paths:
            snapshots = []
            for path in file_paths:
                abs_path = os.path.abspath(path)
                if abs_path in self._pending_captures:
                    snapshots.append(self._pending_captures.pop(abs_path))
        else:
            snapshots = list(self._pending_captures.values())
            self._pending_captures.clear()

        if not snapshots:
            return None

        # Create entry
        entry = UndoEntry(
            tool_name=tool_name,
            description=description,
            snapshots=snapshots,
            command=command,
        )

        # Add to history
        self._history.push(entry)

        logger.info(
            f"Committed undo entry: {description} ({len(snapshots)} files)"
        )

        # Auto-save to session if available
        self._auto_save()

        return entry

    def discard_pending(self) -> int:
        """Discard all pending captures without committing.

        Returns:
            Number of captures discarded.
        """
        count = len(self._pending_captures)
        self._pending_captures.clear()
        return count

    def undo(self) -> tuple[bool, str]:
        """Perform undo operation.

        Restores files to their state before the last operation
        and moves that operation to the redo stack.

        Returns:
            Tuple of (success, message).
        """
        if not self._enabled:
            return False, "Undo is disabled"

        if not self._history.can_undo:
            return False, "Nothing to undo"

        # Pop entry from undo stack
        entry = self._history.pop_undo()
        if entry is None:
            return False, "Nothing to undo"

        # Perform undo (restore files)
        success, message, current_snapshots = entry.undo()

        if success:
            # Create redo entry with current state
            redo_entry = UndoEntry(
                tool_name=entry.tool_name,
                description=entry.description,
                snapshots=current_snapshots,
                command=entry.command,
            )
            self._history.push_redo(redo_entry)

            logger.info(f"Undo: {message}")
            self._auto_save()
        else:
            # Put entry back on undo stack
            self._history.undo_stack.append(entry)
            logger.error(f"Undo failed: {message}")

        return success, message

    def redo(self) -> tuple[bool, str]:
        """Perform redo operation.

        Re-applies the last undone operation.

        Returns:
            Tuple of (success, message).
        """
        if not self._enabled:
            return False, "Redo is disabled"

        if not self._history.can_redo:
            return False, "Nothing to redo"

        # Pop entry from redo stack
        entry = self._history.pop_redo()
        if entry is None:
            return False, "Nothing to redo"

        # Perform redo (restore files to post-operation state)
        success, message, current_snapshots = entry.undo()

        if success:
            # Create undo entry with current state
            undo_entry = UndoEntry(
                tool_name=entry.tool_name,
                description=entry.description,
                snapshots=current_snapshots,
                command=entry.command,
            )
            # Push directly to undo stack (don't clear redo)
            self._history.undo_stack.append(undo_entry)

            message = message.replace("Undone:", "Redone:")
            logger.info(f"Redo: {message}")
            self._auto_save()
        else:
            # Put entry back on redo stack
            self._history.redo_stack.append(entry)
            logger.error(f"Redo failed: {message}")

        return success, message

    def get_undo_description(self) -> str | None:
        """Get description of next undo operation.

        Returns:
            Description string, or None if nothing to undo.
        """
        entry = self._history.peek_undo()
        return entry.description if entry else None

    def get_redo_description(self) -> str | None:
        """Get description of next redo operation.

        Returns:
            Description string, or None if nothing to redo.
        """
        entry = self._history.peek_redo()
        return entry.description if entry else None

    def get_undo_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get summary of undo history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of entry summaries (most recent first).
        """
        entries = []
        for entry in reversed(self._history.undo_stack[-limit:]):
            entries.append({
                "id": entry.id,
                "tool": entry.tool_name,
                "description": entry.description,
                "files": entry.file_count,
                "timestamp": entry.timestamp.isoformat(),
            })
        return entries

    def get_redo_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get summary of redo history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of entry summaries (most recent first).
        """
        entries = []
        for entry in reversed(self._history.redo_stack[-limit:]):
            entries.append({
                "id": entry.id,
                "tool": entry.tool_name,
                "description": entry.description,
                "files": entry.file_count,
                "timestamp": entry.timestamp.isoformat(),
            })
        return entries

    def clear(self) -> None:
        """Clear all undo/redo history."""
        self._history.clear()
        self._pending_captures.clear()
        self._auto_save()

    def save_to_session(self) -> None:
        """Save undo history to session metadata."""
        if self._session_manager is None:
            return

        session = self._session_manager.current_session
        if session is None:
            return

        session.metadata["undo_history"] = self._history.to_dict()

        # Trigger session save
        try:
            self._session_manager.save()
        except Exception as e:
            logger.error(f"Failed to save undo history: {e}")

    def load_from_session(self) -> bool:
        """Load undo history from session metadata.

        Returns:
            True if history was loaded, False otherwise.
        """
        if self._session_manager is None:
            return False

        session = self._session_manager.current_session
        if session is None:
            return False

        history_data = session.metadata.get("undo_history")
        if history_data:
            try:
                self._history = UndoHistory.from_dict(history_data)
                logger.info(
                    f"Loaded undo history: {len(self._history.undo_stack)} entries"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to load undo history: {e}")

        return False

    def _auto_save(self) -> None:
        """Auto-save to session if session manager is available."""
        if self._session_manager is not None:
            self.save_to_session()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about undo history.

        Returns:
            Dictionary with undo statistics.
        """
        return {
            "enabled": self._enabled,
            "undo_count": len(self._history.undo_stack),
            "redo_count": len(self._history.redo_stack),
            "total_size_bytes": self._history.total_size,
            "max_entries": self._history.max_entries,
            "max_size_bytes": self._history.max_size_bytes,
            "pending_captures": len(self._pending_captures),
        }
