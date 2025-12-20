"""Unit tests for session storage."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from code_forge.sessions.models import Session
from code_forge.sessions.storage import (
    SessionCorruptedError,
    SessionNotFoundError,
    SessionStorage,
    SessionStorageError,
)


class TestSessionStorage:
    """Tests for SessionStorage class."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir: Path) -> SessionStorage:
        """Create a SessionStorage with temporary directory."""
        return SessionStorage(temp_dir)

    def test_init_creates_directory(self, temp_dir: Path) -> None:
        """Test that init creates storage directory."""
        storage_dir = temp_dir / "sessions"
        assert not storage_dir.exists()
        SessionStorage(storage_dir)
        assert storage_dir.exists()

    def test_init_with_string_path(self, temp_dir: Path) -> None:
        """Test init with string path."""
        storage = SessionStorage(str(temp_dir))
        assert storage.storage_dir == temp_dir

    def test_init_with_none_uses_default(self) -> None:
        """Test init with None uses default directory."""
        # Don't actually create it, just check the path
        storage = SessionStorage.__new__(SessionStorage)
        storage.storage_dir = SessionStorage.get_default_dir()
        assert "forge" in str(storage.storage_dir)
        assert "sessions" in str(storage.storage_dir)

    def test_get_default_dir(self) -> None:
        """Test default directory location."""
        default_dir = SessionStorage.get_default_dir()
        assert default_dir.name == "sessions"
        assert "forge" in str(default_dir)

    def test_get_default_dir_with_xdg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default dir respects XDG_DATA_HOME."""
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")
        default_dir = SessionStorage.get_default_dir()
        assert str(default_dir).startswith("/custom/data")

    def test_get_project_dir(self) -> None:
        """Test project-local directory."""
        project_dir = SessionStorage.get_project_dir("/home/user/project")
        assert project_dir == Path("/home/user/project/.forge/sessions")

    def test_get_path(self, storage: SessionStorage) -> None:
        """Test getting session file path."""
        path = storage.get_path("session-123")
        assert path == storage.storage_dir / "session-123.json"

    def test_get_backup_path(self, storage: SessionStorage) -> None:
        """Test getting backup file path."""
        path = storage.get_backup_path("session-123")
        assert path == storage.storage_dir / "session-123.backup"

    def test_exists_false(self, storage: SessionStorage) -> None:
        """Test exists returns False for missing session."""
        assert storage.exists("nonexistent") is False

    def test_exists_true(self, storage: SessionStorage) -> None:
        """Test exists returns True for existing session."""
        session = Session(title="Test")
        storage.save(session)
        assert storage.exists(session.id) is True

    def test_save_creates_file(self, storage: SessionStorage) -> None:
        """Test save creates session file."""
        session = Session(title="Test Session")
        storage.save(session)
        assert storage.get_path(session.id).exists()

    def test_save_writes_json(self, storage: SessionStorage) -> None:
        """Test save writes valid JSON."""
        session = Session(title="Test")
        storage.save(session)
        path = storage.get_path(session.id)
        with path.open() as f:
            data = json.load(f)
        assert data["title"] == "Test"

    def test_save_creates_backup(self, storage: SessionStorage) -> None:
        """Test save creates backup of existing file."""
        session = Session(title="Original")
        storage.save(session)

        session.title = "Updated"
        storage.save(session)

        backup_path = storage.get_backup_path(session.id)
        assert backup_path.exists()

        # Backup should have original content
        with backup_path.open() as f:
            data = json.load(f)
        assert data["title"] == "Original"

    def test_save_atomic(self, storage: SessionStorage, temp_dir: Path) -> None:
        """Test save is atomic (temp file then rename)."""
        session = Session(title="Test")
        storage.save(session)

        # Check that no temp files remain
        temp_files = list(temp_dir.glob("*.json"))
        assert len(temp_files) == 1
        assert temp_files[0].name == f"{session.id}.json"

    def test_save_sets_permissions(self, storage: SessionStorage) -> None:
        """Test save sets secure file permissions."""
        session = Session()
        storage.save(session)
        path = storage.get_path(session.id)
        # Check file is readable only by owner
        mode = path.stat().st_mode
        assert mode & 0o077 == 0  # No group/other permissions

    def test_load_success(self, storage: SessionStorage) -> None:
        """Test loading existing session."""
        session = Session(title="Test", model="gpt-4")
        session.add_message_from_dict("user", "Hello!")
        storage.save(session)

        loaded = storage.load(session.id)
        assert loaded.id == session.id
        assert loaded.title == "Test"
        assert loaded.model == "gpt-4"
        assert loaded.message_count == 1

    def test_load_not_found(self, storage: SessionStorage) -> None:
        """Test loading non-existent session raises error."""
        with pytest.raises(SessionNotFoundError):
            storage.load("nonexistent-id")

    def test_load_corrupted(self, storage: SessionStorage) -> None:
        """Test loading corrupted session raises error."""
        session = Session()
        path = storage.get_path(session.id)
        path.write_text("not valid json {{{")

        with pytest.raises(SessionCorruptedError):
            storage.load(session.id)

    def test_load_or_none_success(self, storage: SessionStorage) -> None:
        """Test load_or_none returns session when found."""
        session = Session(title="Test")
        storage.save(session)

        loaded = storage.load_or_none(session.id)
        assert isinstance(loaded, Session)
        assert loaded.id == session.id

    def test_load_or_none_missing(self, storage: SessionStorage) -> None:
        """Test load_or_none returns None when missing."""
        result = storage.load_or_none("nonexistent")
        assert result is None

    def test_load_or_none_corrupted(self, storage: SessionStorage) -> None:
        """Test load_or_none returns None when corrupted."""
        session = Session()
        path = storage.get_path(session.id)
        path.write_text("invalid json")

        result = storage.load_or_none(session.id)
        assert result is None

    def test_delete_existing(self, storage: SessionStorage) -> None:
        """Test deleting existing session."""
        session = Session()
        storage.save(session)
        assert storage.exists(session.id)

        result = storage.delete(session.id)
        assert result is True
        assert not storage.exists(session.id)

    def test_delete_nonexistent(self, storage: SessionStorage) -> None:
        """Test deleting non-existent session."""
        result = storage.delete("nonexistent")
        assert result is False

    def test_delete_removes_backup(self, storage: SessionStorage) -> None:
        """Test delete also removes backup file."""
        session = Session(title="Original")
        storage.save(session)
        session.title = "Updated"
        storage.save(session)  # Creates backup

        backup_path = storage.get_backup_path(session.id)
        assert backup_path.exists()

        storage.delete(session.id)
        assert not backup_path.exists()

    def test_list_session_ids_empty(self, storage: SessionStorage) -> None:
        """Test listing sessions when empty."""
        ids = storage.list_session_ids()
        assert ids == []

    def test_list_session_ids(self, storage: SessionStorage) -> None:
        """Test listing session IDs."""
        s1 = Session()
        s2 = Session()
        s3 = Session()
        storage.save(s1)
        storage.save(s2)
        storage.save(s3)

        ids = storage.list_session_ids()
        assert len(ids) == 3
        assert s1.id in ids
        assert s2.id in ids
        assert s3.id in ids

    def test_recover_from_backup_success(self, storage: SessionStorage) -> None:
        """Test recovering from backup."""
        session = Session(title="Original")
        storage.save(session)
        session.title = "Updated"
        storage.save(session)

        # Corrupt the main file
        path = storage.get_path(session.id)
        path.write_text("corrupted")

        # Recover
        result = storage.recover_from_backup(session.id)
        assert result is True

        # Should have original content
        loaded = storage.load(session.id)
        assert loaded.title == "Original"

    def test_recover_from_backup_no_backup(self, storage: SessionStorage) -> None:
        """Test recovery fails when no backup exists."""
        result = storage.recover_from_backup("no-backup")
        assert result is False

    def test_get_storage_size(self, storage: SessionStorage) -> None:
        """Test getting total storage size."""
        # Initially empty
        assert storage.get_storage_size() == 0

        # Add sessions
        storage.save(Session(title="Session 1"))
        storage.save(Session(title="Session 2"))

        size = storage.get_storage_size()
        assert size > 0

    def test_cleanup_old_sessions(self, storage: SessionStorage) -> None:
        """Test cleaning up old sessions."""
        # Create sessions with varying ages
        from datetime import timedelta

        old_session = Session(title="Old")
        old_session.updated_at = old_session.updated_at - timedelta(days=60)
        storage.save(old_session)

        new_session = Session(title="New")
        storage.save(new_session)

        # Cleanup old sessions
        deleted = storage.cleanup_old_sessions(max_age_days=30, keep_minimum=0)

        # Old session should be deleted
        assert old_session.id in deleted
        assert not storage.exists(old_session.id)

        # New session should remain
        assert storage.exists(new_session.id)

    def test_cleanup_old_sessions_keeps_minimum(self, storage: SessionStorage) -> None:
        """Test cleanup respects keep_minimum."""
        from datetime import timedelta

        # Create 5 old sessions
        sessions = []
        for i in range(5):
            s = Session(title=f"Session {i}")
            s.updated_at = s.updated_at - timedelta(days=60)
            storage.save(s)
            sessions.append(s)

        # Cleanup but keep at least 3
        deleted = storage.cleanup_old_sessions(max_age_days=30, keep_minimum=3)

        # Only 2 should be deleted
        assert len(deleted) == 2

        # 3 should remain
        remaining = storage.list_session_ids()
        assert len(remaining) == 3

    def test_cleanup_old_backups(self, storage: SessionStorage) -> None:
        """Test cleaning up old backups."""
        # Create some backup files
        for i in range(5):
            backup_path = storage.storage_dir / f"session-{i}.backup"
            backup_path.write_text("{}")

        count = storage.cleanup_old_backups()
        # Without modifying mtime, no backups should be deleted
        # as they're all "new"
        assert count == 0


class TestSessionStorageErrors:
    """Tests for storage error handling."""

    def test_session_storage_error_is_exception(self) -> None:
        """Test SessionStorageError is an exception."""
        assert issubclass(SessionStorageError, Exception)

    def test_session_not_found_error(self) -> None:
        """Test SessionNotFoundError."""
        assert issubclass(SessionNotFoundError, SessionStorageError)
        err = SessionNotFoundError("Session xyz not found")
        assert "xyz" in str(err)

    def test_session_corrupted_error(self) -> None:
        """Test SessionCorruptedError."""
        assert issubclass(SessionCorruptedError, SessionStorageError)
        err = SessionCorruptedError("Invalid JSON")
        assert "Invalid" in str(err)


class TestSessionStorageEdgeCases:
    """Tests for storage edge cases to improve coverage."""

    @pytest.fixture
    def storage(self) -> SessionStorage:
        """Create a SessionStorage for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionStorage(Path(tmpdir))

    def test_load_general_exception(self, storage: SessionStorage) -> None:
        """Test load handles general exceptions."""
        # Create a session file with valid JSON but missing required fields
        # This will cause an exception during Session.from_dict
        session_path = storage.get_path("bad-session")
        # Use a valid JSON that will fail deserialization in a way that's not JSONDecodeError
        session_path.write_text('{"messages": "not-a-list"}')

        with pytest.raises(SessionStorageError):
            storage.load("bad-session")

    def test_save_backup_failure_continues(
        self, storage: SessionStorage
    ) -> None:
        """Test save continues if backup fails."""
        import shutil

        session = Session()

        # Save once
        storage.save(session)

        # Make backup path a directory so backup copy will fail
        backup_path = storage.get_backup_path(session.id)

        # Remove backup if exists, create as directory with file inside
        if backup_path.exists():
            backup_path.unlink()
        backup_path.mkdir()
        (backup_path / "blocker.txt").write_text("block")

        # Second save should still work despite backup failure
        session.title = "Updated"
        storage.save(session)

        # Verify save worked
        loaded = storage.load(session.id)
        assert loaded.title == "Updated"

        # Cleanup
        shutil.rmtree(backup_path)

    def test_cleanup_old_backups_by_age(self, storage: SessionStorage) -> None:
        """Test cleanup removes old backups by age."""
        import time

        # Create some backup files with old timestamps
        backup_path = storage.storage_dir / "old-session.backup"
        backup_path.write_text("{}")

        # Set mtime to 10 days ago (beyond default 7 day limit)
        old_time = time.time() - (10 * 24 * 3600)
        os.utime(backup_path, (old_time, old_time))

        count = storage.cleanup_old_backups()
        assert count == 1
        assert not backup_path.exists()

    def test_cleanup_old_backups_by_count(self, storage: SessionStorage) -> None:
        """Test cleanup removes excess backups by count."""
        # Create more backups than MAX_BACKUPS
        original_max = SessionStorage.MAX_BACKUPS
        SessionStorage.MAX_BACKUPS = 3

        try:
            for i in range(5):
                backup_path = storage.storage_dir / f"session-{i}.backup"
                backup_path.write_text("{}")

            count = storage.cleanup_old_backups()
            # 5 - 3 = 2 excess backups should be deleted
            assert count == 2

            # Should have exactly 3 remaining
            remaining = list(storage.storage_dir.glob("*.backup"))
            assert len(remaining) == 3
        finally:
            SessionStorage.MAX_BACKUPS = original_max

    def test_get_project_dir_string(self) -> None:
        """Test get_project_dir accepts string path."""
        project_dir = SessionStorage.get_project_dir("/some/project")
        assert project_dir == Path("/some/project/.forge/sessions")
