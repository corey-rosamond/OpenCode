"""Tests for undo system data models."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from code_forge.undo.models import FileSnapshot, UndoEntry, UndoHistory


class TestFileSnapshot:
    """Tests for FileSnapshot."""

    def test_capture_text_file(self, tmp_path: Path) -> None:
        """Test capturing a text file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        snapshot = FileSnapshot.capture(str(test_file))

        assert snapshot is not None
        assert snapshot.file_path == str(test_file)
        assert snapshot.content == "Hello, World!"
        assert snapshot.encoding == "utf-8"
        assert snapshot.is_binary is False
        assert snapshot.existed is True
        assert snapshot.size_bytes == 13
        assert snapshot.checksum != ""

    def test_capture_nonexistent_file(self, tmp_path: Path) -> None:
        """Test capturing a non-existent file."""
        test_file = tmp_path / "nonexistent.txt"

        snapshot = FileSnapshot.capture(str(test_file))

        assert snapshot is not None
        assert snapshot.file_path == str(test_file)
        assert snapshot.content is None
        assert snapshot.existed is False
        assert snapshot.size_bytes == 0

    def test_capture_binary_file(self, tmp_path: Path) -> None:
        """Test capturing a binary file."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03\xff")

        snapshot = FileSnapshot.capture(str(test_file))

        assert snapshot is not None
        assert snapshot.is_binary is True
        assert snapshot.encoding == "binary"
        # Content is base64 encoded
        assert snapshot.content is not None

    def test_capture_large_file_rejected(self, tmp_path: Path) -> None:
        """Test that files larger than max_size are rejected."""
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 100)  # 100 bytes

        # With very small max_size
        snapshot = FileSnapshot.capture(str(test_file), max_size=50)

        assert snapshot is None

    def test_capture_directory_rejected(self, tmp_path: Path) -> None:
        """Test that directories are rejected."""
        snapshot = FileSnapshot.capture(str(tmp_path))
        assert snapshot is None

    def test_restore_text_file(self, tmp_path: Path) -> None:
        """Test restoring a text file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        # Capture before change
        snapshot = FileSnapshot.capture(str(test_file))
        assert snapshot is not None

        # Modify file
        test_file.write_text("modified content")
        assert test_file.read_text() == "modified content"

        # Restore
        success, message = snapshot.restore()

        assert success is True
        assert test_file.read_text() == "original content"

    def test_restore_deleted_file(self, tmp_path: Path) -> None:
        """Test restoring a file that was deleted."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content to restore")

        snapshot = FileSnapshot.capture(str(test_file))
        assert snapshot is not None

        # Delete file
        test_file.unlink()
        assert not test_file.exists()

        # Restore
        success, message = snapshot.restore()

        assert success is True
        assert test_file.exists()
        assert test_file.read_text() == "content to restore"

    def test_restore_nonexistent_deletes_file(self, tmp_path: Path) -> None:
        """Test that restoring a non-existent snapshot deletes the file."""
        test_file = tmp_path / "new.txt"

        # Capture before file exists
        snapshot = FileSnapshot.capture(str(test_file))
        assert snapshot is not None
        assert snapshot.existed is False

        # Create file
        test_file.write_text("new content")
        assert test_file.exists()

        # Restore (should delete)
        success, message = snapshot.restore()

        assert success is True
        assert not test_file.exists()

    def test_to_dict_from_dict(self) -> None:
        """Test serialization round-trip."""
        snapshot = FileSnapshot(
            file_path="/path/to/file.txt",
            content="test content",
            encoding="utf-8",
            is_binary=False,
            existed=True,
            size_bytes=12,
            checksum="abc123",
        )

        data = snapshot.to_dict()
        restored = FileSnapshot.from_dict(data)

        assert restored.file_path == snapshot.file_path
        assert restored.content == snapshot.content
        assert restored.encoding == snapshot.encoding
        assert restored.is_binary == snapshot.is_binary
        assert restored.existed == snapshot.existed
        assert restored.size_bytes == snapshot.size_bytes
        assert restored.checksum == snapshot.checksum


class TestUndoEntry:
    """Tests for UndoEntry."""

    def test_create_entry(self) -> None:
        """Test creating an undo entry."""
        snapshot = FileSnapshot(
            file_path="/path/to/file.txt",
            content="test",
            existed=True,
        )
        entry = UndoEntry(
            tool_name="Edit",
            description="Edit file.txt",
            snapshots=[snapshot],
        )

        assert entry.tool_name == "Edit"
        assert entry.description == "Edit file.txt"
        assert len(entry.snapshots) == 1
        assert entry.id != ""
        assert entry.command is None

    def test_entry_with_command(self) -> None:
        """Test entry with Bash command."""
        entry = UndoEntry(
            tool_name="Bash",
            description="Bash: echo hello > file.txt",
            snapshots=[],
            command="echo hello > file.txt",
        )

        assert entry.tool_name == "Bash"
        assert entry.command == "echo hello > file.txt"

    def test_total_size(self) -> None:
        """Test total size calculation."""
        snapshots = [
            FileSnapshot(file_path=f"/file{i}.txt", content="x" * 100)
            for i in range(3)
        ]
        entry = UndoEntry(
            tool_name="Write",
            description="Write files",
            snapshots=snapshots,
        )

        assert entry.total_size == 300

    def test_file_count(self) -> None:
        """Test file count."""
        snapshots = [
            FileSnapshot(file_path=f"/file{i}.txt", content="x")
            for i in range(5)
        ]
        entry = UndoEntry(
            tool_name="Write",
            description="Write files",
            snapshots=snapshots,
        )

        assert entry.file_count == 5

    def test_undo_restores_files(self, tmp_path: Path) -> None:
        """Test undo operation restores files."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")

        snapshot = FileSnapshot.capture(str(test_file))
        assert snapshot is not None

        entry = UndoEntry(
            tool_name="Edit",
            description="Edit test.txt",
            snapshots=[snapshot],
        )

        # Modify file
        test_file.write_text("modified")

        # Undo
        success, message, current_snapshots = entry.undo()

        assert success is True
        assert "Undone" in message
        assert test_file.read_text() == "original"
        assert len(current_snapshots) == 1

    def test_to_dict_from_dict(self) -> None:
        """Test serialization round-trip."""
        snapshot = FileSnapshot(
            file_path="/path/to/file.txt",
            content="test",
            existed=True,
        )
        entry = UndoEntry(
            tool_name="Edit",
            description="Edit file.txt",
            snapshots=[snapshot],
            command="some command",
        )

        data = entry.to_dict()
        restored = UndoEntry.from_dict(data)

        assert restored.id == entry.id
        assert restored.tool_name == entry.tool_name
        assert restored.description == entry.description
        assert restored.command == entry.command
        assert len(restored.snapshots) == 1


class TestUndoHistory:
    """Tests for UndoHistory."""

    def test_create_empty_history(self) -> None:
        """Test creating empty history."""
        history = UndoHistory()

        assert history.can_undo is False
        assert history.can_redo is False
        assert len(history.undo_stack) == 0
        assert len(history.redo_stack) == 0

    def test_push_entry(self) -> None:
        """Test pushing entries to undo stack."""
        history = UndoHistory()
        entry = UndoEntry(tool_name="Edit", description="Edit")

        history.push(entry)

        assert history.can_undo is True
        assert len(history.undo_stack) == 1

    def test_push_clears_redo(self) -> None:
        """Test that pushing new entry clears redo stack."""
        history = UndoHistory()
        entry1 = UndoEntry(tool_name="Edit", description="Edit 1")
        entry2 = UndoEntry(tool_name="Edit", description="Edit 2")

        history.push(entry1)
        # Simulate undo + redo scenario
        history.redo_stack.append(entry1)

        # New push should clear redo
        history.push(entry2)

        assert len(history.redo_stack) == 0

    def test_max_entries_eviction(self) -> None:
        """Test that old entries are evicted when max reached."""
        history = UndoHistory(max_entries=3)

        for i in range(5):
            history.push(UndoEntry(tool_name="Edit", description=f"Edit {i}"))

        assert len(history.undo_stack) == 3
        # Oldest entries should be gone
        assert history.undo_stack[0].description == "Edit 2"

    def test_pop_undo(self) -> None:
        """Test popping from undo stack."""
        history = UndoHistory()
        entry = UndoEntry(tool_name="Edit", description="Edit")
        history.push(entry)

        popped = history.pop_undo()

        assert popped is entry
        assert len(history.undo_stack) == 0

    def test_pop_undo_empty(self) -> None:
        """Test popping from empty undo stack."""
        history = UndoHistory()

        popped = history.pop_undo()

        assert popped is None

    def test_push_redo(self) -> None:
        """Test pushing to redo stack."""
        history = UndoHistory()
        entry = UndoEntry(tool_name="Edit", description="Edit")

        history.push_redo(entry)

        assert history.can_redo is True
        assert len(history.redo_stack) == 1

    def test_pop_redo(self) -> None:
        """Test popping from redo stack."""
        history = UndoHistory()
        entry = UndoEntry(tool_name="Edit", description="Edit")
        history.push_redo(entry)

        popped = history.pop_redo()

        assert popped is entry
        assert len(history.redo_stack) == 0

    def test_peek_undo(self) -> None:
        """Test peeking at next undo."""
        history = UndoHistory()
        entry = UndoEntry(tool_name="Edit", description="Edit")
        history.push(entry)

        peeked = history.peek_undo()

        assert peeked is entry
        # Should still be there
        assert len(history.undo_stack) == 1

    def test_peek_redo(self) -> None:
        """Test peeking at next redo."""
        history = UndoHistory()
        entry = UndoEntry(tool_name="Edit", description="Edit")
        history.push_redo(entry)

        peeked = history.peek_redo()

        assert peeked is entry
        assert len(history.redo_stack) == 1

    def test_clear(self) -> None:
        """Test clearing history."""
        history = UndoHistory()
        history.push(UndoEntry(tool_name="Edit", description="Edit 1"))
        history.push_redo(UndoEntry(tool_name="Edit", description="Edit 2"))

        history.clear()

        assert len(history.undo_stack) == 0
        assert len(history.redo_stack) == 0

    def test_total_size(self) -> None:
        """Test total size calculation."""
        history = UndoHistory()
        snapshot = FileSnapshot(file_path="/file.txt", content="x" * 100)
        entry = UndoEntry(
            tool_name="Edit",
            description="Edit",
            snapshots=[snapshot],
        )
        history.push(entry)

        assert history.total_size == 100

    def test_to_dict_from_dict(self) -> None:
        """Test serialization round-trip."""
        history = UndoHistory(max_entries=50)
        history.push(UndoEntry(tool_name="Edit", description="Edit 1"))
        history.push_redo(UndoEntry(tool_name="Edit", description="Edit 2"))

        data = history.to_dict()
        restored = UndoHistory.from_dict(data)

        assert len(restored.undo_stack) == 1
        assert len(restored.redo_stack) == 1
        assert restored.max_entries == 50
