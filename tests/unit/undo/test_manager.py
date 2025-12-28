"""Tests for UndoManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from code_forge.undo.manager import UndoManager


class TestUndoManager:
    """Tests for UndoManager."""

    def test_create_manager(self) -> None:
        """Test creating an undo manager."""
        manager = UndoManager()

        assert manager.enabled is True
        assert manager.can_undo is False
        assert manager.can_redo is False

    def test_create_disabled_manager(self) -> None:
        """Test creating a disabled undo manager."""
        manager = UndoManager(enabled=False)

        assert manager.enabled is False

    def test_capture_before(self, tmp_path: Path) -> None:
        """Test capturing file state before modification."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        result = manager.capture_before(str(test_file))

        assert result is True
        assert len(manager._pending_captures) == 1

    def test_capture_before_disabled(self, tmp_path: Path) -> None:
        """Test capture fails when disabled."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager(enabled=False)
        result = manager.capture_before(str(test_file))

        assert result is False
        assert len(manager._pending_captures) == 0

    def test_capture_same_file_twice(self, tmp_path: Path) -> None:
        """Test capturing same file twice only captures once."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        manager.capture_before(str(test_file))

        assert len(manager._pending_captures) == 1

    def test_capture_multiple(self, tmp_path: Path) -> None:
        """Test capturing multiple files."""
        files = [tmp_path / f"file{i}.txt" for i in range(3)]
        for f in files:
            f.write_text("content")

        manager = UndoManager()
        results = manager.capture_multiple([str(f) for f in files])

        assert all(results.values())
        assert len(manager._pending_captures) == 3

    def test_commit_creates_entry(self, tmp_path: Path) -> None:
        """Test committing captures creates undo entry."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        manager.capture_before(str(test_file))

        entry = manager.commit("Edit", "Edit test.txt")

        assert entry is not None
        assert entry.tool_name == "Edit"
        assert entry.description == "Edit test.txt"
        assert len(entry.snapshots) == 1
        assert manager.can_undo is True

    def test_commit_clears_pending(self, tmp_path: Path) -> None:
        """Test commit clears pending captures."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        manager.commit("Edit", "Edit test.txt")

        assert len(manager._pending_captures) == 0

    def test_commit_nothing_pending(self) -> None:
        """Test commit with nothing pending returns None."""
        manager = UndoManager()
        entry = manager.commit("Edit", "Edit test.txt")

        assert entry is None

    def test_discard_pending(self, tmp_path: Path) -> None:
        """Test discarding pending captures."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        manager.capture_before(str(test_file))

        count = manager.discard_pending()

        assert count == 1
        assert len(manager._pending_captures) == 0

    def test_undo_restores_file(self, tmp_path: Path) -> None:
        """Test undo restores file to previous state."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        test_file.write_text("modified content")
        manager.commit("Edit", "Edit test.txt")

        success, message = manager.undo()

        assert success is True
        assert "Undone" in message
        assert test_file.read_text() == "original content"

    def test_undo_nothing_to_undo(self) -> None:
        """Test undo with nothing to undo."""
        manager = UndoManager()
        success, message = manager.undo()

        assert success is False
        assert "Nothing to undo" in message

    def test_undo_disabled(self, tmp_path: Path) -> None:
        """Test undo when disabled."""
        manager = UndoManager(enabled=False)
        success, message = manager.undo()

        assert success is False
        assert "disabled" in message.lower()

    def test_redo_restores_file(self, tmp_path: Path) -> None:
        """Test redo restores file after undo."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        test_file.write_text("modified content")
        manager.commit("Edit", "Edit test.txt")

        # Undo
        manager.undo()
        assert test_file.read_text() == "original content"

        # Redo
        success, message = manager.redo()

        assert success is True
        assert "Redone" in message
        assert test_file.read_text() == "modified content"

    def test_redo_nothing_to_redo(self) -> None:
        """Test redo with nothing to redo."""
        manager = UndoManager()
        success, message = manager.redo()

        assert success is False
        assert "Nothing to redo" in message

    def test_new_commit_clears_redo(self, tmp_path: Path) -> None:
        """Test new commit clears redo stack."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        test_file.write_text("modified")
        manager.commit("Edit", "Edit 1")

        manager.undo()
        assert manager.can_redo is True

        # New operation
        manager.capture_before(str(test_file))
        test_file.write_text("new change")
        manager.commit("Edit", "Edit 2")

        assert manager.can_redo is False

    def test_get_undo_description(self, tmp_path: Path) -> None:
        """Test getting next undo description."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        manager.commit("Edit", "Edit file.txt")

        desc = manager.get_undo_description()

        assert desc == "Edit file.txt"

    def test_get_redo_description(self, tmp_path: Path) -> None:
        """Test getting next redo description."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        test_file.write_text("modified")
        manager.commit("Edit", "Edit file.txt")
        manager.undo()

        desc = manager.get_redo_description()

        assert desc == "Edit file.txt"

    def test_get_undo_history(self, tmp_path: Path) -> None:
        """Test getting undo history summary."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = UndoManager()
        for i in range(3):
            manager.capture_before(str(test_file))
            test_file.write_text(f"content {i}")
            manager.commit("Edit", f"Edit {i}")

        history = manager.get_undo_history(limit=2)

        assert len(history) == 2
        assert history[0]["description"] == "Edit 2"
        assert history[1]["description"] == "Edit 1"

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing history."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        manager.commit("Edit", "Edit")

        manager.clear()

        assert manager.can_undo is False

    def test_get_stats(self) -> None:
        """Test getting statistics."""
        manager = UndoManager()
        stats = manager.get_stats()

        assert "enabled" in stats
        assert "undo_count" in stats
        assert "redo_count" in stats
        assert "total_size_bytes" in stats

    def test_undo_count(self, tmp_path: Path) -> None:
        """Test undo count property."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = UndoManager()
        assert manager.undo_count == 0

        manager.capture_before(str(test_file))
        manager.commit("Edit", "Edit")

        assert manager.undo_count == 1

    def test_redo_count(self, tmp_path: Path) -> None:
        """Test redo count property."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = UndoManager()
        manager.capture_before(str(test_file))
        test_file.write_text("modified")
        manager.commit("Edit", "Edit")

        assert manager.redo_count == 0

        manager.undo()

        assert manager.redo_count == 1


class TestUndoManagerPersistence:
    """Tests for UndoManager session persistence."""

    def test_save_to_session(self, tmp_path: Path) -> None:
        """Test saving undo history to session."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Mock session manager
        mock_session = MagicMock()
        mock_session.metadata = {}
        mock_session_manager = MagicMock()
        mock_session_manager.current_session = mock_session

        manager = UndoManager(session_manager=mock_session_manager)
        manager.capture_before(str(test_file))
        manager.commit("Edit", "Edit")

        manager.save_to_session()

        assert "undo_history" in mock_session.metadata
        mock_session_manager.save.assert_called()

    def test_load_from_session(self) -> None:
        """Test loading undo history from session."""
        # Mock session with existing history
        mock_session = MagicMock()
        mock_session.metadata = {
            "undo_history": {
                "undo_stack": [
                    {
                        "id": "test-id",
                        "tool_name": "Edit",
                        "description": "Edit file",
                        "snapshots": [],
                        "timestamp": "2025-01-01T00:00:00+00:00",
                        "command": None,
                    }
                ],
                "redo_stack": [],
                "max_entries": 100,
                "max_size_bytes": 52428800,
            }
        }
        mock_session_manager = MagicMock()
        mock_session_manager.current_session = mock_session

        manager = UndoManager(session_manager=mock_session_manager)
        result = manager.load_from_session()

        assert result is True
        assert manager.undo_count == 1
        assert manager.get_undo_description() == "Edit file"

    def test_load_from_session_no_history(self) -> None:
        """Test loading when no history exists."""
        mock_session = MagicMock()
        mock_session.metadata = {}
        mock_session_manager = MagicMock()
        mock_session_manager.current_session = mock_session

        manager = UndoManager(session_manager=mock_session_manager)
        result = manager.load_from_session()

        assert result is False
