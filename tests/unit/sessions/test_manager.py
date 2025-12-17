"""Unit tests for session manager."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from code_forge.sessions.index import SessionIndex
from code_forge.sessions.manager import SessionManager
from code_forge.sessions.models import Session
from code_forge.sessions.storage import SessionNotFoundError, SessionStorage


class TestSessionManagerSingleton:
    """Tests for SessionManager singleton pattern."""

    def test_get_instance_returns_same_instance(self) -> None:
        """Test get_instance returns the same instance."""
        SessionManager.reset_instance()
        try:
            manager1 = SessionManager.get_instance()
            manager2 = SessionManager.get_instance()
            assert manager1 is manager2
        finally:
            SessionManager.reset_instance()

    def test_reset_instance_clears_instance(self) -> None:
        """Test reset_instance clears the singleton."""
        SessionManager.reset_instance()
        manager1 = SessionManager.get_instance()
        SessionManager.reset_instance()
        manager2 = SessionManager.get_instance()
        assert manager1 is not manager2
        SessionManager.reset_instance()


class TestSessionManager:
    """Tests for SessionManager class."""

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
    def manager(self, storage: SessionStorage) -> SessionManager:
        """Create a SessionManager for testing."""
        SessionManager.reset_instance()
        return SessionManager(storage=storage, auto_save_interval=0)

    def test_init(self, manager: SessionManager) -> None:
        """Test manager initialization."""
        assert isinstance(manager.storage, SessionStorage)
        assert isinstance(manager.index, SessionIndex)
        assert manager.current_session is None
        assert manager.has_current is False

    def test_create_session(self, manager: SessionManager) -> None:
        """Test creating a new session."""
        session = manager.create(title="Test Session", model="gpt-4")

        assert isinstance(session, Session)
        assert session.title == "Test Session"
        assert session.model == "gpt-4"
        assert manager.current_session is session
        assert manager.has_current is True

    def test_create_session_uses_cwd(self, manager: SessionManager) -> None:
        """Test create uses current directory if not specified."""
        session = manager.create()
        assert session.working_dir == str(Path.cwd())

    def test_create_session_with_working_dir(self, manager: SessionManager) -> None:
        """Test create with custom working directory."""
        session = manager.create(working_dir="/custom/path")
        assert session.working_dir == "/custom/path"

    def test_create_session_with_tags(self, manager: SessionManager) -> None:
        """Test create with tags."""
        session = manager.create(tags=["python", "api"])
        assert session.tags == ["python", "api"]

    def test_create_session_with_metadata(self, manager: SessionManager) -> None:
        """Test create with metadata."""
        session = manager.create(metadata={"branch": "main"})
        assert session.metadata == {"branch": "main"}

    def test_create_saves_immediately(self, manager: SessionManager) -> None:
        """Test that create saves session to storage."""
        session = manager.create()
        assert manager.storage.exists(session.id)

    def test_create_adds_to_index(self, manager: SessionManager) -> None:
        """Test that create adds session to index."""
        session = manager.create()
        assert session.id in manager.index

    def test_create_fires_hook(self, manager: SessionManager) -> None:
        """Test that create fires session:start hook."""
        events: list[tuple[str, Session]] = []

        def on_start(session: Session) -> None:
            events.append(("start", session))

        manager.register_hook("session:start", on_start)
        session = manager.create()

        assert len(events) == 1
        assert events[0][0] == "start"
        assert events[0][1] is session

    def test_resume_session(self, manager: SessionManager) -> None:
        """Test resuming an existing session."""
        # Create and close a session
        session = manager.create(title="Test")
        session_id = session.id
        manager.close()
        assert manager.current_session is None

        # Resume
        resumed = manager.resume(session_id)
        assert resumed.id == session_id
        assert resumed.title == "Test"
        assert manager.current_session is resumed

    def test_resume_not_found(self, manager: SessionManager) -> None:
        """Test resuming non-existent session raises error."""
        with pytest.raises(SessionNotFoundError):
            manager.resume("nonexistent-id")

    def test_resume_fires_hook(self, manager: SessionManager) -> None:
        """Test that resume fires session:start hook."""
        events: list[str] = []

        def on_start(_session: Session) -> None:
            events.append("start")

        manager.register_hook("session:start", on_start)

        session = manager.create()
        events.clear()  # Clear create event

        session_id = session.id
        manager.close()
        manager.resume(session_id)

        assert events == ["start"]

    def test_resume_latest(self, manager: SessionManager) -> None:
        """Test resuming the most recent session."""
        _s1 = manager.create(title="First")
        manager.close()

        s2 = manager.create(title="Second")
        manager.close()

        resumed = manager.resume_latest()
        assert isinstance(resumed, Session)
        assert resumed.id == s2.id

    def test_resume_latest_no_sessions(self, manager: SessionManager) -> None:
        """Test resume_latest with no sessions."""
        result = manager.resume_latest()
        assert result is None

    def test_resume_or_create_resumes(self, manager: SessionManager) -> None:
        """Test resume_or_create resumes existing session."""
        s1 = manager.create(title="Existing")
        manager.close()

        result = manager.resume_or_create()
        assert result.id == s1.id

    def test_resume_or_create_creates(self, manager: SessionManager) -> None:
        """Test resume_or_create creates new when none exist."""
        result = manager.resume_or_create(model="gpt-4")
        assert isinstance(result, Session)
        assert result.model == "gpt-4"

    def test_save_session(self, manager: SessionManager) -> None:
        """Test saving a session."""
        session = manager.create()
        session.title = "Updated Title"
        manager.save()

        # Reload and verify
        loaded = manager.storage.load(session.id)
        assert loaded.title == "Updated Title"

    def test_save_no_session(self, manager: SessionManager) -> None:
        """Test save with no current session logs warning."""
        # Should not raise
        manager.save()

    def test_save_fires_hook(self, manager: SessionManager) -> None:
        """Test that save fires session:save hook."""
        events: list[str] = []

        def on_save(_session: Session) -> None:
            events.append("save")

        manager.register_hook("session:save", on_save)
        manager.create()
        events.clear()  # Clear create event (which also saves)

        manager.save()
        assert events == ["save"]

    def test_close_session(self, manager: SessionManager) -> None:
        """Test closing a session."""
        _session = manager.create()
        assert manager.has_current

        manager.close()
        assert manager.current_session is None
        assert not manager.has_current

    def test_close_saves_session(self, manager: SessionManager) -> None:
        """Test that close saves the session."""
        session = manager.create()
        session.title = "Before Close"
        manager.close()

        loaded = manager.storage.load(session.id)
        assert loaded.title == "Before Close"

    def test_close_fires_hook(self, manager: SessionManager) -> None:
        """Test that close fires session:end hook."""
        events: list[str] = []

        def on_end(_session: Session) -> None:
            events.append("end")

        manager.register_hook("session:end", on_end)
        manager.create()
        manager.close()

        assert "end" in events

    def test_delete_session(self, manager: SessionManager) -> None:
        """Test deleting a session."""
        session = manager.create()
        session_id = session.id
        manager.close()

        result = manager.delete(session_id)
        assert result is True
        assert not manager.storage.exists(session_id)
        assert session_id not in manager.index

    def test_delete_current_session(self, manager: SessionManager) -> None:
        """Test deleting the current session."""
        session = manager.create()
        session_id = session.id

        result = manager.delete(session_id)
        assert result is True
        assert manager.current_session is None

    def test_list_sessions(self, manager: SessionManager) -> None:
        """Test listing sessions."""
        for i in range(5):
            manager.create(title=f"Session {i}")
            manager.close()

        sessions = manager.list_sessions()
        assert len(sessions) == 5

    def test_list_sessions_with_filters(self, manager: SessionManager) -> None:
        """Test listing with filters."""
        manager.create(title="Python API", tags=["python"])
        manager.close()
        manager.create(title="JavaScript", tags=["javascript"])
        manager.close()

        results = manager.list_sessions(tags=["python"])
        assert len(results) == 1
        assert results[0].title == "Python API"

    def test_get_session(self, manager: SessionManager) -> None:
        """Test getting a full session by ID."""
        session = manager.create(title="Test")
        session_id = session.id
        manager.close()

        loaded = manager.get_session(session_id)
        assert isinstance(loaded, Session)
        assert loaded.id == session_id
        assert loaded.title == "Test"

    def test_get_session_not_found(self, manager: SessionManager) -> None:
        """Test get_session returns None for missing session."""
        result = manager.get_session("nonexistent")
        assert result is None

    def test_add_message(self, manager: SessionManager) -> None:
        """Test adding a message to current session."""
        session = manager.create()
        msg = manager.add_message("user", "Hello!")

        assert session.message_count == 1
        assert msg.role == "user"
        assert msg.content == "Hello!"

    def test_add_message_with_kwargs(self, manager: SessionManager) -> None:
        """Test adding message with extra fields."""
        manager.create()
        msg = manager.add_message(
            "tool",
            '{"result": "ok"}',
            tool_call_id="call_123",
            name="bash",
        )
        assert msg.tool_call_id == "call_123"
        assert msg.name == "bash"

    def test_add_message_no_session(self, manager: SessionManager) -> None:
        """Test add_message raises when no session."""
        with pytest.raises(ValueError):
            manager.add_message("user", "Hello!")

    def test_add_message_fires_hook(self, manager: SessionManager) -> None:
        """Test that add_message fires session:message hook."""
        events: list[tuple[Session, SessionMessage]] = []

        def on_message(session: Session, message: SessionMessage) -> None:
            events.append((session, message))

        manager.register_hook("session:message", on_message)
        session = manager.create()
        msg = manager.add_message("user", "Hello!")

        assert len(events) == 1
        assert events[0][0] is session
        assert events[0][1] is msg

    def test_record_tool_call(self, manager: SessionManager) -> None:
        """Test recording a tool call."""
        session = manager.create()
        inv = manager.record_tool_call(
            tool_name="bash",
            arguments={"command": "ls"},
            result={"output": "files..."},
            duration=0.5,
        )

        assert len(session.tool_history) == 1
        assert inv.tool_name == "bash"
        assert inv.arguments == {"command": "ls"}
        assert inv.duration == 0.5

    def test_record_tool_call_no_session(self, manager: SessionManager) -> None:
        """Test record_tool_call raises when no session."""
        with pytest.raises(ValueError):
            manager.record_tool_call("bash", {"command": "ls"})

    def test_update_usage(self, manager: SessionManager) -> None:
        """Test updating token usage."""
        session = manager.create()
        manager.update_usage(100, 50)

        assert session.total_prompt_tokens == 100
        assert session.total_completion_tokens == 50
        assert session.total_tokens == 150

    def test_update_usage_no_session(self, manager: SessionManager) -> None:
        """Test update_usage with no session does nothing."""
        # Should not raise
        manager.update_usage(100, 50)

    def test_generate_title_from_message(self, manager: SessionManager) -> None:
        """Test generating title from first user message."""
        session = manager.create()
        manager.add_message("user", "Help me refactor the API client")

        title = manager.generate_title(session)
        assert title == "Help me refactor the API client"

    def test_generate_title_truncates_long_message(self, manager: SessionManager) -> None:
        """Test generate_title truncates long messages."""
        session = manager.create()
        long_msg = "x" * 100
        manager.add_message("user", long_msg)

        title = manager.generate_title(session)
        assert len(title) == 50
        assert title.endswith("...")

    def test_generate_title_uses_first_line(self, manager: SessionManager) -> None:
        """Test generate_title uses only first line."""
        session = manager.create()
        manager.add_message("user", "First line\nSecond line\nThird line")

        title = manager.generate_title(session)
        assert title == "First line"

    def test_generate_title_fallback(self, manager: SessionManager) -> None:
        """Test generate_title fallback to timestamp."""
        session = manager.create()  # No messages

        title = manager.generate_title(session)
        assert "Session" in title
        assert session.created_at.strftime("%Y-%m-%d") in title

    def test_set_title(self, manager: SessionManager) -> None:
        """Test setting session title."""
        session = manager.create()
        manager.set_title("New Title")

        assert session.title == "New Title"

    def test_add_tag(self, manager: SessionManager) -> None:
        """Test adding a tag."""
        session = manager.create()
        manager.add_tag("python")

        assert "python" in session.tags

    def test_add_tag_no_duplicates(self, manager: SessionManager) -> None:
        """Test add_tag prevents duplicates."""
        session = manager.create(tags=["python"])
        manager.add_tag("python")

        assert session.tags.count("python") == 1

    def test_remove_tag(self, manager: SessionManager) -> None:
        """Test removing a tag."""
        session = manager.create(tags=["python", "api"])
        result = manager.remove_tag("python")

        assert result is True
        assert "python" not in session.tags
        assert "api" in session.tags

    def test_remove_tag_not_present(self, manager: SessionManager) -> None:
        """Test removing non-existent tag."""
        manager.create()
        result = manager.remove_tag("nonexistent")

        assert result is False


class TestSessionManagerHooks:
    """Tests for SessionManager hook system."""

    @pytest.fixture
    def manager(self) -> SessionManager:
        """Create a SessionManager for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(Path(tmpdir))
            yield SessionManager(storage=storage, auto_save_interval=0)

    def test_register_hook(self, manager: SessionManager) -> None:
        """Test registering a hook."""
        called = []

        def callback(session: Session) -> None:
            called.append(session.id)

        manager.register_hook("session:start", callback)
        session = manager.create()

        assert len(called) == 1
        assert called[0] == session.id

    def test_unregister_hook(self, manager: SessionManager) -> None:
        """Test unregistering a hook."""
        called = []

        def callback(session: Session) -> None:
            called.append(session.id)

        manager.register_hook("session:start", callback)
        result = manager.unregister_hook("session:start", callback)
        assert result is True

        manager.create()
        assert len(called) == 0

    def test_unregister_nonexistent_hook(self, manager: SessionManager) -> None:
        """Test unregistering non-existent hook."""

        def callback(_session: Session) -> None:
            pass

        result = manager.unregister_hook("session:start", callback)
        assert result is False

    def test_hook_error_logged(self, manager: SessionManager) -> None:
        """Test that hook errors are logged but don't break flow."""

        def bad_callback(_session: Session) -> None:
            raise ValueError("Hook error!")

        manager.register_hook("session:start", bad_callback)

        # Should not raise
        session = manager.create()
        assert isinstance(session, Session)

    def test_multiple_hooks(self, manager: SessionManager) -> None:
        """Test multiple hooks for same event."""
        events: list[str] = []

        def callback1(_session: Session) -> None:
            events.append("callback1")

        def callback2(_session: Session) -> None:
            events.append("callback2")

        manager.register_hook("session:start", callback1)
        manager.register_hook("session:start", callback2)
        manager.create()

        assert events == ["callback1", "callback2"]

    def test_all_hook_events(self, manager: SessionManager) -> None:
        """Test that all hook events are fired correctly."""
        events: list[str] = []

        manager.register_hook("session:start", lambda _s: events.append("start"))
        manager.register_hook("session:message", lambda _s, _m: events.append("message"))
        manager.register_hook("session:save", lambda _s: events.append("save"))
        manager.register_hook("session:end", lambda _s: events.append("end"))

        _session = manager.create()  # Fires start (and save)
        events.clear()

        manager.add_message("user", "Hello!")  # Fires message
        manager.save()  # Fires save
        manager.close()  # Fires save and end

        assert "message" in events
        assert "save" in events
        assert "end" in events


class TestSessionManagerAutoSave:
    """Tests for SessionManager auto-save feature."""

    def test_auto_save_disabled_when_zero(self) -> None:
        """Test auto-save is disabled when interval is 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(Path(tmpdir))
            manager = SessionManager(storage=storage, auto_save_interval=0)
            manager.create()

            # Auto-save task should not be started
            assert manager._auto_save_task is None

    def test_auto_save_disabled_when_negative(self) -> None:
        """Test auto-save is disabled when interval is negative."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(Path(tmpdir))
            manager = SessionManager(storage=storage, auto_save_interval=-1)
            manager.create()

            assert manager._auto_save_task is None

    @pytest.mark.asyncio
    async def test_auto_save_task_created_in_async_context(self) -> None:
        """Test auto-save task is created when running in async context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(Path(tmpdir))
            manager = SessionManager(storage=storage, auto_save_interval=10)

            manager.create()

            # Task should be created since we're in async context
            assert isinstance(manager._auto_save_task, asyncio.Task)

            # Stop it cleanly
            manager._stop_auto_save()
            assert manager._auto_save_task is None

    @pytest.mark.asyncio
    async def test_auto_save_stops_on_close(self) -> None:
        """Test auto-save stops when session is closed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(Path(tmpdir))
            manager = SessionManager(storage=storage, auto_save_interval=10)

            manager.create()
            task = manager._auto_save_task
            assert isinstance(task, asyncio.Task)

            manager.close()
            assert manager._auto_save_task is None


class TestSessionManagerEdgeCases:
    """Tests for SessionManager edge cases."""

    @pytest.fixture
    def manager(self) -> SessionManager:
        """Create a SessionManager for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(Path(tmpdir))
            yield SessionManager(storage=storage, auto_save_interval=0)

    def test_set_title_no_session(self, manager: SessionManager) -> None:
        """Test set_title with no current session does nothing."""
        manager.set_title("Test Title")
        # Should not raise

    def test_add_tag_no_session(self, manager: SessionManager) -> None:
        """Test add_tag with no current session does nothing."""
        manager.add_tag("test-tag")
        # Should not raise

    def test_remove_tag_no_session(self, manager: SessionManager) -> None:
        """Test remove_tag with no current session returns False."""
        result = manager.remove_tag("test-tag")
        assert result is False

    def test_close_no_session(self, manager: SessionManager) -> None:
        """Test closing when no session is active does nothing."""
        manager.close()  # Should not raise

    def test_register_invalid_hook_event(self, manager: SessionManager) -> None:
        """Test registering hook for invalid event is ignored."""
        manager.register_hook("invalid:event", lambda: None)
        # Should not raise, just does nothing

    def test_resume_latest_rebuilds_stale_index(self, manager: SessionManager) -> None:
        """Test resume_latest rebuilds index when entry is stale."""
        # Create a session but then delete its file to make index stale
        session = manager.create()
        session_id = session.id
        manager.close()

        # Delete the file directly, making index stale
        manager.storage.get_path(session_id).unlink()

        # resume_latest should rebuild and return None
        result = manager.resume_latest()
        assert result is None

    def test_has_current_property(self, manager: SessionManager) -> None:
        """Test has_current property."""
        assert manager.has_current is False
        manager.create()
        assert manager.has_current is True
        manager.close()
        assert manager.has_current is False
