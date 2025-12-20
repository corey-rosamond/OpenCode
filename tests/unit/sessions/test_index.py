"""Unit tests for session index."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any

import pytest

from code_forge.sessions.index import SessionIndex, SessionSummary
from code_forge.sessions.models import Session
from code_forge.sessions.storage import SessionStorage


class TestSessionSummary:
    """Tests for SessionSummary dataclass."""

    def test_create(self) -> None:
        """Test creating a summary."""
        now = datetime.now(UTC)
        summary = SessionSummary(
            id="session-id",
            title="Test Session",
            created_at=now,
            updated_at=now,
            message_count=5,
            total_tokens=1000,
            tags=["python"],
            working_dir="/home/user",
            model="gpt-4",
        )
        assert summary.id == "session-id"
        assert summary.title == "Test Session"
        assert summary.message_count == 5
        assert summary.total_tokens == 1000
        assert summary.tags == ["python"]
        assert summary.working_dir == "/home/user"
        assert summary.model == "gpt-4"

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(UTC)
        summary = SessionSummary(
            id="test-id",
            title="Test",
            created_at=now,
            updated_at=now,
            message_count=10,
            total_tokens=500,
            tags=["api"],
        )
        data = summary.to_dict()
        assert data["id"] == "test-id"
        assert data["title"] == "Test"
        assert data["message_count"] == 10
        assert data["total_tokens"] == 500
        assert data["tags"] == ["api"]
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "test-id",
            "title": "Test Session",
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:00:00+00:00",
            "message_count": 15,
            "total_tokens": 2000,
            "tags": ["refactoring"],
            "working_dir": "/project",
            "model": "claude-3",
        }
        summary = SessionSummary.from_dict(data)
        assert summary.id == "test-id"
        assert summary.title == "Test Session"
        assert summary.message_count == 15
        assert summary.total_tokens == 2000
        assert summary.tags == ["refactoring"]
        assert summary.working_dir == "/project"
        assert summary.model == "claude-3"

    def test_from_dict_missing_fields(self) -> None:
        """Test deserialization with missing optional fields."""
        data: dict[str, Any] = {
            "id": "test-id",
            "title": "Test",
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T10:30:00+00:00",
            "message_count": 0,
            "total_tokens": 0,
        }
        summary = SessionSummary.from_dict(data)
        assert summary.tags == []
        assert summary.working_dir == ""
        assert summary.model == ""

    def test_from_session(self) -> None:
        """Test creating summary from full Session."""
        session = Session(
            title="Full Session",
            working_dir="/home/user/project",
            model="anthropic/claude-3",
            tags=["python", "api"],
        )
        session.add_message_from_dict("user", "Hello!")
        session.add_message_from_dict("assistant", "Hi!")
        session.update_usage(100, 50)

        summary = SessionSummary.from_session(session)
        assert summary.id == session.id
        assert summary.title == "Full Session"
        assert summary.message_count == 2
        assert summary.total_tokens == 150
        assert summary.tags == ["python", "api"]
        assert summary.working_dir == "/home/user/project"
        assert summary.model == "anthropic/claude-3"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        now = datetime.now(UTC)
        summary = SessionSummary(
            id="test",
            title="Test",
            created_at=now,
            updated_at=now,
            message_count=5,
            total_tokens=1000,
            tags=["tag"],
        )
        data = summary.to_dict()
        restored = SessionSummary.from_dict(data)
        assert restored.id == summary.id
        assert restored.title == summary.title
        assert restored.message_count == summary.message_count


class TestSessionIndex:
    """Tests for SessionIndex class."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir: Path) -> SessionStorage:
        """Create a SessionStorage with temporary directory."""
        return SessionStorage(temp_dir)

    @pytest.fixture
    def index(self, storage: SessionStorage) -> SessionIndex:
        """Create a SessionIndex."""
        return SessionIndex(storage)

    def test_init_empty(self, index: SessionIndex) -> None:
        """Test initializing with empty storage."""
        assert index.count() == 0
        assert len(index) == 0

    def test_init_loads_existing_index(self, storage: SessionStorage) -> None:
        """Test that init loads existing index file."""
        # Create and populate first index
        index1 = SessionIndex(storage)
        session = Session(title="Test")
        storage.save(session)
        index1.add(session)
        index1.save_if_dirty()

        # Create new index from same storage
        index2 = SessionIndex(storage)
        assert index2.count() == 1
        assert session.id in index2

    def test_add_session(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test adding a session to index."""
        session = Session(title="Test")
        storage.save(session)
        index.add(session)

        assert session.id in index
        assert index.count() == 1

    def test_update_session(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test updating a session in index."""
        session = Session(title="Original")
        storage.save(session)
        index.add(session)

        session.title = "Updated"
        index.update(session)

        summary = index.get(session.id)
        assert isinstance(summary, SessionSummary)
        assert summary.title == "Updated"

    def test_remove_session(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test removing a session from index."""
        session = Session()
        storage.save(session)
        index.add(session)
        assert session.id in index

        result = index.remove(session.id)
        assert result is True
        assert session.id not in index

    def test_remove_nonexistent(self, index: SessionIndex) -> None:
        """Test removing non-existent session."""
        result = index.remove("nonexistent")
        assert result is False

    def test_get_existing(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test getting existing session summary."""
        session = Session(title="Test", model="gpt-4")
        storage.save(session)
        index.add(session)

        summary = index.get(session.id)
        assert isinstance(summary, SessionSummary)
        assert summary.id == session.id
        assert summary.title == "Test"
        assert summary.model == "gpt-4"

    def test_get_nonexistent(self, index: SessionIndex) -> None:
        """Test getting non-existent session."""
        summary = index.get("nonexistent")
        assert summary is None

    def test_count(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test counting sessions."""
        assert index.count() == 0

        for i in range(3):
            session = Session(title=f"Session {i}")
            storage.save(session)
            index.add(session)

        assert index.count() == 3

    def test_contains(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test __contains__ method."""
        session = Session()
        storage.save(session)

        assert session.id not in index
        index.add(session)
        assert session.id in index

    def test_len(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test __len__ method."""
        assert len(index) == 0

        session = Session()
        storage.save(session)
        index.add(session)
        assert len(index) == 1

    def test_list_default_sorting(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test listing with default sorting (updated_at desc)."""
        # Create sessions with different update times
        s1 = Session(title="Oldest")
        s1.updated_at = s1.updated_at - timedelta(hours=2)
        storage.save(s1)
        index.add(s1)

        s2 = Session(title="Newest")
        storage.save(s2)
        index.add(s2)

        s3 = Session(title="Middle")
        s3.updated_at = s3.updated_at - timedelta(hours=1)
        storage.save(s3)
        index.add(s3)

        results = index.list()
        assert len(results) == 3
        assert results[0].title == "Newest"
        assert results[1].title == "Middle"
        assert results[2].title == "Oldest"

    def test_list_ascending(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test listing with ascending order."""
        s1 = Session(title="A")
        s2 = Session(title="B")
        storage.save(s1)
        storage.save(s2)
        index.add(s1)
        index.add(s2)

        results = index.list(sort_by="title", descending=False)
        assert results[0].title == "A"
        assert results[1].title == "B"

    def test_list_pagination(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test listing with pagination."""
        for i in range(10):
            session = Session(title=f"Session {i}")
            storage.save(session)
            index.add(session)

        # First page
        page1 = index.list(limit=3, offset=0)
        assert len(page1) == 3

        # Second page
        page2 = index.list(limit=3, offset=3)
        assert len(page2) == 3
        assert page1[0].id != page2[0].id

        # Last page (partial)
        page4 = index.list(limit=3, offset=9)
        assert len(page4) == 1

    def test_list_filter_by_tags(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test filtering by tags."""
        s1 = Session(title="Python Only", tags=["python"])
        s2 = Session(title="Python and API", tags=["python", "api"])
        s3 = Session(title="JavaScript", tags=["javascript"])
        for s in [s1, s2, s3]:
            storage.save(s)
            index.add(s)

        # Filter by single tag
        python_sessions = index.list(tags=["python"])
        assert len(python_sessions) == 2

        # Filter by multiple tags (all must match)
        python_api = index.list(tags=["python", "api"])
        assert len(python_api) == 1
        assert python_api[0].title == "Python and API"

        # Filter by non-existent tag
        rust_sessions = index.list(tags=["rust"])
        assert len(rust_sessions) == 0

    def test_list_search(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test searching by title."""
        s1 = Session(title="Refactoring the API client")
        s2 = Session(title="Implementing new features")
        s3 = Session(title="API documentation")
        for s in [s1, s2, s3]:
            storage.save(s)
            index.add(s)

        # Case-insensitive search
        api_sessions = index.list(search="api")
        assert len(api_sessions) == 2

        # Exact match
        refactor_sessions = index.list(search="refactor")
        assert len(refactor_sessions) == 1

    def test_list_filter_by_working_dir(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test filtering by working directory."""
        s1 = Session(title="Project A", working_dir="/home/user/project-a")
        s2 = Session(title="Project B", working_dir="/home/user/project-b")
        s3 = Session(title="Project A again", working_dir="/home/user/project-a")
        for s in [s1, s2, s3]:
            storage.save(s)
            index.add(s)

        results = index.list(working_dir="/home/user/project-a")
        assert len(results) == 2

    def test_list_combined_filters(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test combining multiple filters."""
        s1 = Session(title="Python API", tags=["python", "api"])
        s2 = Session(title="Python CLI", tags=["python", "cli"])
        s3 = Session(title="Rust API", tags=["rust", "api"])
        for s in [s1, s2, s3]:
            storage.save(s)
            index.add(s)

        # Search + tags filter
        results = index.list(search="api", tags=["python"])
        assert len(results) == 1
        assert results[0].title == "Python API"

    def test_get_recent(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test getting recent sessions."""
        for i in range(5):
            session = Session(title=f"Session {i}")
            session.updated_at = session.updated_at - timedelta(hours=i)
            storage.save(session)
            index.add(session)

        recent = index.get_recent(count=3)
        assert len(recent) == 3
        assert recent[0].title == "Session 0"  # Most recent
        assert recent[1].title == "Session 1"
        assert recent[2].title == "Session 2"

    def test_get_by_working_dir(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test getting sessions by working directory."""
        s1 = Session(working_dir="/project-a")
        s2 = Session(working_dir="/project-b")
        s3 = Session(working_dir="/project-a")
        for s in [s1, s2, s3]:
            storage.save(s)
            index.add(s)

        results = index.get_by_working_dir("/project-a")
        assert len(results) == 2

    def test_rebuild(self, index: SessionIndex, storage: SessionStorage) -> None:
        """Test rebuilding index from session files."""
        # Add sessions directly to storage (bypassing index)
        s1 = Session(title="Session 1")
        s2 = Session(title="Session 2")
        storage.save(s1)
        storage.save(s2)

        # Index is empty
        assert index.count() == 0

        # Rebuild
        index.rebuild()

        # Now index has sessions
        assert index.count() == 2
        assert s1.id in index
        assert s2.id in index

    def test_save_if_dirty_saves_when_dirty(
        self, index: SessionIndex, storage: SessionStorage
    ) -> None:
        """Test save_if_dirty saves when index is modified."""
        session = Session()
        storage.save(session)
        index.add(session)
        assert index._dirty is True

        index.save_if_dirty()
        assert index._dirty is False

        # Index file should exist
        assert index.index_path.exists()

    def test_save_if_dirty_skips_when_clean(self, index: SessionIndex) -> None:
        """Test save_if_dirty does nothing when clean."""
        index._dirty = False
        # Just make sure it doesn't raise
        index.save_if_dirty()

    def test_index_persistence(self, storage: SessionStorage) -> None:
        """Test that index persists across instances."""
        # Create and populate index
        index1 = SessionIndex(storage)
        session = Session(title="Persistent")
        storage.save(session)
        index1.add(session)
        index1.save_if_dirty()

        # Create new index instance
        index2 = SessionIndex(storage)
        assert index2.count() == 1
        summary = index2.get(session.id)
        assert isinstance(summary, SessionSummary)
        assert summary.title == "Persistent"

    def test_index_version_mismatch_rebuilds(self, temp_dir: Path) -> None:
        """Test that version mismatch triggers rebuild."""
        # Use fresh storage to avoid fixture pollution
        storage = SessionStorage(temp_dir / "version_test")

        # Create index with some sessions
        session = Session()
        storage.save(session)
        index1 = SessionIndex(storage)
        index1.add(session)
        index1.save_if_dirty()

        # Modify index file version
        import json

        with index1.index_path.open() as f:
            data = json.load(f)
        data["version"] = 999
        with index1.index_path.open("w") as f:
            json.dump(data, f)

        # Create new index - should rebuild
        index2 = SessionIndex(storage)
        assert index2.count() == 1  # Still has session from rebuild

    def test_corrupted_index_rebuilds(self, storage: SessionStorage) -> None:
        """Test that corrupted index is rebuilt."""
        # Create index with sessions
        session = Session()
        storage.save(session)
        index1 = SessionIndex(storage)
        index1.add(session)
        index1.save_if_dirty()

        # Corrupt index file
        index1.index_path.write_text("not valid json")

        # Create new index - should rebuild
        index2 = SessionIndex(storage)
        assert index2.count() == 1  # Rebuilt from session files


class TestSessionSummaryEdgeCases:
    """Edge case tests for SessionSummary to improve coverage."""

    def test_from_dict_with_none_dates(self) -> None:
        """Test from_dict with None dates uses current time."""
        data: dict[str, Any] = {
            "id": "test-id",
            "created_at": None,
            "updated_at": None,
        }
        summary = SessionSummary.from_dict(data)
        assert isinstance(summary.created_at, datetime)
        assert isinstance(summary.updated_at, datetime)
        assert isinstance(summary.created_at.tzinfo, tzinfo)
        assert isinstance(summary.updated_at.tzinfo, tzinfo)


class TestSessionIndexEdgeCases:
    """Edge case tests for SessionIndex to improve coverage."""

    @pytest.fixture
    def storage(self) -> SessionStorage:
        """Create a SessionStorage for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionStorage(Path(tmpdir))

    @pytest.fixture
    def index(self, storage: SessionStorage) -> SessionIndex:
        """Create a SessionIndex for testing."""
        return SessionIndex(storage)

    def test_save_index_failure_handled(self, storage: SessionStorage) -> None:
        """Test save_index handles failures gracefully."""
        index = SessionIndex(storage)
        session = Session()
        storage.save(session)
        index.add(session)

        # Make index path a directory to cause write failure
        index.index_path.unlink(missing_ok=True)
        index.index_path.mkdir()

        # Should not raise, just log error
        index.save_if_dirty()

        # Cleanup
        index.index_path.rmdir()

    def test_rebuild_skips_corrupt_sessions(self, storage: SessionStorage) -> None:
        """Test rebuild skips sessions that can't be loaded."""
        index = SessionIndex(storage)

        # Create a valid session
        session = Session()
        storage.save(session)

        # Create a corrupt session file
        corrupt_path = storage.get_path("corrupt-session")
        corrupt_path.write_text("not valid json")

        # Rebuild should still work, loading only valid sessions
        index.rebuild()
        assert index.count() == 1  # Only the valid session
