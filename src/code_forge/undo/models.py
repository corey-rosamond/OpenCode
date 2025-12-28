"""Undo system data models.

This module provides the core data models for the undo/redo system:
- FileSnapshot: Captures file state before modification
- UndoEntry: Single undoable operation with snapshots
- UndoHistory: Undo/redo stacks with size management

Example:
    # Capture file before edit
    snapshot = FileSnapshot.capture("/path/to/file.py")

    # Create undo entry
    entry = UndoEntry(
        tool_name="Edit",
        description="Edit config.py",
        snapshots=[snapshot],
    )

    # Manage history
    history = UndoHistory()
    history.push(entry)
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


@dataclass
class FileSnapshot:
    """Snapshot of a file's state before modification.

    Captures the complete state of a file including content, encoding,
    and metadata needed to restore it during an undo operation.

    Attributes:
        file_path: Absolute path to the file.
        content: File content (None if file didn't exist).
        encoding: Character encoding for text files.
        is_binary: Whether content is binary (base64 encoded).
        existed: Whether file existed before the operation.
        size_bytes: Original file size in bytes.
        checksum: SHA256 checksum for verification.
        timestamp: When the snapshot was captured.
    """

    file_path: str
    content: str | None = None
    encoding: str = "utf-8"
    is_binary: bool = False
    existed: bool = True
    size_bytes: int = 0
    checksum: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Size limits
    MAX_TEXT_SIZE: ClassVar[int] = 1_048_576  # 1MB for text files
    MAX_BINARY_SIZE: ClassVar[int] = 10_485_760  # 10MB for binary files

    @classmethod
    def capture(cls, file_path: str, max_size: int | None = None) -> FileSnapshot | None:
        """Capture current file state.

        Args:
            file_path: Path to the file to capture.
            max_size: Optional max size override in bytes.

        Returns:
            FileSnapshot if capture succeeded, None if file too large or error.
        """
        abs_path = os.path.abspath(file_path)

        # Handle non-existent files
        if not os.path.exists(abs_path):
            return cls(
                file_path=abs_path,
                content=None,
                existed=False,
                size_bytes=0,
            )

        # Check if it's a file (not directory)
        if not os.path.isfile(abs_path):
            logger.warning(f"Cannot capture non-file: {abs_path}")
            return None

        try:
            size = os.path.getsize(abs_path)

            # Try to read as text first
            try:
                with open(abs_path, encoding="utf-8") as f:
                    content = f.read()

                max_allowed = max_size or cls.MAX_TEXT_SIZE
                if size > max_allowed:
                    logger.warning(
                        f"File too large for undo: {abs_path} ({size} bytes > {max_allowed})"
                    )
                    return None

                return cls(
                    file_path=abs_path,
                    content=content,
                    encoding="utf-8",
                    is_binary=False,
                    existed=True,
                    size_bytes=size,
                    checksum=hashlib.sha256(content.encode()).hexdigest(),
                )

            except UnicodeDecodeError:
                # Binary file
                max_allowed = max_size or cls.MAX_BINARY_SIZE
                if size > max_allowed:
                    logger.warning(
                        f"Binary file too large for undo: {abs_path} ({size} bytes > {max_allowed})"
                    )
                    return None

                with open(abs_path, "rb") as f:
                    binary_content = f.read()

                # Encode as base64 for JSON serialization
                return cls(
                    file_path=abs_path,
                    content=base64.b64encode(binary_content).decode("ascii"),
                    encoding="binary",
                    is_binary=True,
                    existed=True,
                    size_bytes=size,
                    checksum=hashlib.sha256(binary_content).hexdigest(),
                )

        except OSError as e:
            logger.error(f"Error capturing file {abs_path}: {e}")
            return None

    def restore(self) -> tuple[bool, str]:
        """Restore file to this snapshot's state.

        Returns:
            Tuple of (success, message).
        """
        try:
            if not self.existed:
                # File was created by the operation, so delete it
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                    return True, f"Deleted {self.file_path}"
                return True, f"File already absent: {self.file_path}"

            if self.content is None:
                return False, f"No content to restore for {self.file_path}"

            # Ensure parent directory exists
            parent = os.path.dirname(self.file_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

            # Restore content
            if self.is_binary:
                binary_content = base64.b64decode(self.content)
                with open(self.file_path, "wb") as f:
                    f.write(binary_content)
            else:
                with open(self.file_path, "w", encoding=self.encoding) as f:
                    f.write(self.content)

            return True, f"Restored {self.file_path}"

        except PermissionError:
            return False, f"Permission denied: {self.file_path}"
        except OSError as e:
            return False, f"Error restoring {self.file_path}: {e}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation.
        """
        return {
            "file_path": self.file_path,
            "content": self.content,
            "encoding": self.encoding,
            "is_binary": self.is_binary,
            "existed": self.existed,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileSnapshot:
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            FileSnapshot instance.
        """
        timestamp_str = data.get("timestamp", "")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = datetime.now(UTC)

        return cls(
            file_path=data["file_path"],
            content=data.get("content"),
            encoding=data.get("encoding", "utf-8"),
            is_binary=data.get("is_binary", False),
            existed=data.get("existed", True),
            size_bytes=data.get("size_bytes", 0),
            checksum=data.get("checksum", ""),
            timestamp=timestamp,
        )


@dataclass
class UndoEntry:
    """Single undoable operation with one or more file snapshots.

    Represents a complete undoable unit of work, which may involve
    multiple files (e.g., a Bash command that modifies several files).

    Attributes:
        id: Unique identifier for this entry.
        tool_name: Name of the tool that created this entry.
        description: Human-readable description.
        snapshots: List of file snapshots for this operation.
        timestamp: When the operation occurred.
        command: For Bash operations, the command that was run.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    description: str = ""
    snapshots: list[FileSnapshot] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    command: str | None = None

    @property
    def total_size(self) -> int:
        """Total size of all snapshots in bytes.

        Returns:
            Sum of all snapshot content sizes.
        """
        return sum(
            len(s.content) if s.content else 0
            for s in self.snapshots
        )

    @property
    def file_count(self) -> int:
        """Number of files in this entry.

        Returns:
            Number of snapshots.
        """
        return len(self.snapshots)

    def undo(self) -> tuple[bool, str, list[FileSnapshot]]:
        """Perform undo by restoring all snapshots.

        Returns:
            Tuple of (success, message, current_snapshots).
            current_snapshots contains the current state for redo purposes.
        """
        current_snapshots: list[FileSnapshot] = []
        restored_snapshots: list[FileSnapshot] = []

        # First, capture current state for potential redo
        for snapshot in self.snapshots:
            current = FileSnapshot.capture(snapshot.file_path)
            if current:
                current_snapshots.append(current)

        # Now restore each snapshot
        for snapshot in self.snapshots:
            success, msg = snapshot.restore()
            if not success:
                # Rollback already-restored snapshots
                for prev in restored_snapshots:
                    # Find the current snapshot for this file
                    for curr in current_snapshots:
                        if curr.file_path == prev.file_path:
                            curr.restore()
                            break
                return False, f"Undo failed: {msg}", []

            restored_snapshots.append(snapshot)

        files_desc = ", ".join(
            os.path.basename(s.file_path) for s in self.snapshots[:3]
        )
        if len(self.snapshots) > 3:
            files_desc += f" (+{len(self.snapshots) - 3} more)"

        return True, f"Undone: {self.description} ({files_desc})", current_snapshots

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "description": self.description,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "timestamp": self.timestamp.isoformat(),
            "command": self.command,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UndoEntry:
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            UndoEntry instance.
        """
        timestamp_str = data.get("timestamp", "")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = datetime.now(UTC)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            tool_name=data.get("tool_name", ""),
            description=data.get("description", ""),
            snapshots=[
                FileSnapshot.from_dict(s) for s in data.get("snapshots", [])
            ],
            timestamp=timestamp,
            command=data.get("command"),
        )


@dataclass
class UndoHistory:
    """Complete undo/redo history for a session.

    Manages undo and redo stacks with size limits and eviction policy.

    Attributes:
        undo_stack: Stack of operations that can be undone.
        redo_stack: Stack of operations that can be redone.
        max_entries: Maximum number of entries to keep.
        max_size_bytes: Maximum total size in bytes.
    """

    undo_stack: list[UndoEntry] = field(default_factory=list)
    redo_stack: list[UndoEntry] = field(default_factory=list)
    max_entries: int = 100
    max_size_bytes: int = 52_428_800  # 50MB default

    @property
    def total_size(self) -> int:
        """Total size of all entries in bytes.

        Returns:
            Sum of all entry sizes.
        """
        undo_size = sum(e.total_size for e in self.undo_stack)
        redo_size = sum(e.total_size for e in self.redo_stack)
        return undo_size + redo_size

    @property
    def can_undo(self) -> bool:
        """Check if undo is available.

        Returns:
            True if undo stack is not empty.
        """
        return len(self.undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Check if redo is available.

        Returns:
            True if redo stack is not empty.
        """
        return len(self.redo_stack) > 0

    def push(self, entry: UndoEntry) -> None:
        """Push entry to undo stack.

        Clears the redo stack and enforces size/count limits.

        Args:
            entry: UndoEntry to push.
        """
        # Clear redo stack on new operation
        self.redo_stack.clear()

        # Add new entry
        self.undo_stack.append(entry)

        # Enforce max entries
        while len(self.undo_stack) > self.max_entries:
            self.undo_stack.pop(0)  # Remove oldest

        # Enforce max size
        while self.total_size > self.max_size_bytes and len(self.undo_stack) > 1:
            self.undo_stack.pop(0)  # Remove oldest

    def pop_undo(self) -> UndoEntry | None:
        """Pop from undo stack for undo operation.

        The entry is NOT automatically moved to redo stack.
        Caller should do that after successful undo.

        Returns:
            UndoEntry if available, None otherwise.
        """
        if not self.undo_stack:
            return None
        return self.undo_stack.pop()

    def push_redo(self, entry: UndoEntry) -> None:
        """Push entry to redo stack after successful undo.

        Args:
            entry: UndoEntry to push to redo stack.
        """
        self.redo_stack.append(entry)

    def pop_redo(self) -> UndoEntry | None:
        """Pop from redo stack for redo operation.

        Returns:
            UndoEntry if available, None otherwise.
        """
        if not self.redo_stack:
            return None
        return self.redo_stack.pop()

    def peek_undo(self) -> UndoEntry | None:
        """Peek at next undo operation without removing.

        Returns:
            Next UndoEntry to undo, or None.
        """
        if not self.undo_stack:
            return None
        return self.undo_stack[-1]

    def peek_redo(self) -> UndoEntry | None:
        """Peek at next redo operation without removing.

        Returns:
            Next UndoEntry to redo, or None.
        """
        if not self.redo_stack:
            return None
        return self.redo_stack[-1]

    def clear(self) -> None:
        """Clear both stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "undo_stack": [e.to_dict() for e in self.undo_stack],
            "redo_stack": [e.to_dict() for e in self.redo_stack],
            "max_entries": self.max_entries,
            "max_size_bytes": self.max_size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UndoHistory:
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            UndoHistory instance.
        """
        return cls(
            undo_stack=[
                UndoEntry.from_dict(e) for e in data.get("undo_stack", [])
            ],
            redo_stack=[
                UndoEntry.from_dict(e) for e in data.get("redo_stack", [])
            ],
            max_entries=data.get("max_entries", 100),
            max_size_bytes=data.get("max_size_bytes", 52_428_800),
        )
