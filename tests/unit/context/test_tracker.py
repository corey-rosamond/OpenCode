"""Tests for session context tracker."""

from __future__ import annotations

import pytest

from code_forge.context.tracker import (
    EntityType,
    OperationType,
    SessionContextTracker,
    TrackedEntity,
    TrackedOperation,
)


class TestTrackedEntity:
    """Tests for TrackedEntity dataclass."""

    def test_creation(self) -> None:
        """Test entity creation."""
        entity = TrackedEntity(
            type=EntityType.FILE,
            value="test.py",
        )
        assert entity.type == EntityType.FILE
        assert entity.value == "test.py"
        assert entity.mention_count == 1
        assert entity.last_mentioned == 0

    def test_hash(self) -> None:
        """Test entity hashing."""
        e1 = TrackedEntity(EntityType.FILE, "test.py")
        e2 = TrackedEntity(EntityType.FILE, "test.py")
        e3 = TrackedEntity(EntityType.FILE, "other.py")

        assert hash(e1) == hash(e2)
        assert hash(e1) != hash(e3)

    def test_equality(self) -> None:
        """Test entity equality."""
        e1 = TrackedEntity(EntityType.FILE, "test.py", mention_count=1)
        e2 = TrackedEntity(EntityType.FILE, "test.py", mention_count=5)
        e3 = TrackedEntity(EntityType.FUNCTION, "test.py")

        assert e1 == e2  # Same type and value
        assert e1 != e3  # Different type


class TestTrackedOperation:
    """Tests for TrackedOperation dataclass."""

    def test_creation(self) -> None:
        """Test operation creation."""
        op = TrackedOperation(
            type=OperationType.READ,
            target="test.py",
            tool_name="Read",
        )
        assert op.type == OperationType.READ
        assert op.target == "test.py"
        assert op.tool_name == "Read"
        assert op.success is True
        assert op.turn == 0


class TestSessionContextTracker:
    """Tests for SessionContextTracker."""

    def test_initial_state(self) -> None:
        """Test tracker starts with empty state."""
        tracker = SessionContextTracker()
        assert tracker.active_file is None
        assert tracker.last_operation is None
        assert tracker.turn_count == 0

    def test_increment_turn(self) -> None:
        """Test turn counter increments."""
        tracker = SessionContextTracker()
        assert tracker.turn_count == 0

        tracker.increment_turn()
        assert tracker.turn_count == 1

        tracker.increment_turn()
        assert tracker.turn_count == 2

    def test_set_active_file(self) -> None:
        """Test setting active file."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")

        assert tracker.active_file == "test.py"

    def test_set_active_file_tracks_entity(self) -> None:
        """Test setting active file also tracks as entity."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")

        entity = tracker.get_entity(EntityType.FILE, "test.py")
        assert entity is not None
        assert entity.value == "test.py"

    def test_clear_active_file(self) -> None:
        """Test clearing active file."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")
        tracker.clear_active_file()

        assert tracker.active_file is None

    def test_track_operation(self) -> None:
        """Test tracking an operation."""
        tracker = SessionContextTracker()
        tracker.track_operation(
            op_type=OperationType.READ,
            target="test.py",
            tool_name="Read",
        )

        assert tracker.last_operation is not None
        assert tracker.last_operation.type == OperationType.READ
        assert tracker.last_operation.target == "test.py"

    def test_track_operation_sets_active_file(self) -> None:
        """Test file operations set active file."""
        tracker = SessionContextTracker()
        tracker.track_operation(
            op_type=OperationType.EDIT,
            target="test.py",
            tool_name="Edit",
        )

        assert tracker.active_file == "test.py"

    def test_track_operation_with_turn(self) -> None:
        """Test operation records turn number."""
        tracker = SessionContextTracker()
        tracker.increment_turn()
        tracker.increment_turn()

        tracker.track_operation(
            op_type=OperationType.READ,
            target="test.py",
            tool_name="Read",
        )

        assert tracker.last_operation is not None
        assert tracker.last_operation.turn == 2

    def test_track_entity(self) -> None:
        """Test tracking an entity."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FILE, "test.py")

        entity = tracker.get_entity(EntityType.FILE, "test.py")
        assert entity is not None
        assert entity.value == "test.py"
        assert entity.mention_count == 1

    def test_track_entity_increments_count(self) -> None:
        """Test tracking same entity increments count."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FILE, "test.py")
        tracker.track_entity(EntityType.FILE, "test.py")
        tracker.track_entity(EntityType.FILE, "test.py")

        entity = tracker.get_entity(EntityType.FILE, "test.py")
        assert entity is not None
        assert entity.mention_count == 3

    def test_track_entity_updates_last_mentioned(self) -> None:
        """Test tracking updates last mentioned turn."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FILE, "test.py")

        tracker.increment_turn()
        tracker.increment_turn()
        tracker.track_entity(EntityType.FILE, "test.py")

        entity = tracker.get_entity(EntityType.FILE, "test.py")
        assert entity is not None
        assert entity.last_mentioned == 2

    def test_get_recent_files(self) -> None:
        """Test getting recent files."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FILE, "a.py")
        tracker.increment_turn()
        tracker.track_entity(EntityType.FILE, "b.py")
        tracker.increment_turn()
        tracker.track_entity(EntityType.FILE, "c.py")

        recent = tracker.get_recent_files(2)
        assert len(recent) == 2
        assert recent[0] == "c.py"  # Most recent first
        assert recent[1] == "b.py"

    def test_get_recent_operations(self) -> None:
        """Test getting recent operations."""
        tracker = SessionContextTracker()
        tracker.track_operation(OperationType.READ, "a.py", "Read")
        tracker.track_operation(OperationType.EDIT, "b.py", "Edit")
        tracker.track_operation(OperationType.WRITE, "c.py", "Write")

        ops = tracker.get_recent_operations(2)
        assert len(ops) == 2
        assert ops[0].target == "b.py"
        assert ops[1].target == "c.py"

    def test_get_recent_operations_by_type(self) -> None:
        """Test filtering operations by type."""
        tracker = SessionContextTracker()
        tracker.track_operation(OperationType.READ, "a.py", "Read")
        tracker.track_operation(OperationType.EDIT, "b.py", "Edit")
        tracker.track_operation(OperationType.READ, "c.py", "Read")

        ops = tracker.get_recent_operations(10, op_type=OperationType.READ)
        assert len(ops) == 2
        assert all(op.type == OperationType.READ for op in ops)

    def test_get_last_file_operation(self) -> None:
        """Test getting last file operation."""
        tracker = SessionContextTracker()
        tracker.track_operation(OperationType.READ, "a.py", "Read")
        tracker.track_operation(OperationType.EXECUTE, "npm run", "Bash")
        tracker.track_operation(OperationType.EDIT, "b.py", "Edit")

        last = tracker.get_last_file_operation()
        assert last is not None
        assert last.target == "b.py"
        assert last.type == OperationType.EDIT

    def test_extract_entities_from_text_files(self) -> None:
        """Test extracting file paths from text."""
        tracker = SessionContextTracker()
        text = 'Please edit "src/main.py" and check ./config.json'

        entities = tracker.extract_entities_from_text(text)
        file_entities = [e for e in entities if e.type == EntityType.FILE]

        assert len(file_entities) >= 2

    def test_extract_entities_from_text_functions(self) -> None:
        """Test extracting function names from text."""
        tracker = SessionContextTracker()
        text = "Look at function process_data and def handle_request"

        entities = tracker.extract_entities_from_text(text)
        func_entities = [e for e in entities if e.type == EntityType.FUNCTION]

        assert len(func_entities) >= 1

    def test_extract_entities_from_text_classes(self) -> None:
        """Test extracting class names from text."""
        tracker = SessionContextTracker()
        text = "Update class UserManager and interface DataStore"

        entities = tracker.extract_entities_from_text(text)
        class_entities = [e for e in entities if e.type == EntityType.CLASS]

        assert len(class_entities) >= 1

    def test_extract_entities_from_text_urls(self) -> None:
        """Test extracting URLs from text."""
        tracker = SessionContextTracker()
        text = "Fetch data from https://api.example.com/data"

        entities = tracker.extract_entities_from_text(text)
        url_entities = [e for e in entities if e.type == EntityType.URL]

        assert len(url_entities) == 1
        assert url_entities[0].value == "https://api.example.com/data"

    def test_get_context_summary(self) -> None:
        """Test getting context summary."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")
        tracker.track_operation(OperationType.READ, "test.py", "Read")
        tracker.increment_turn()

        summary = tracker.get_context_summary()

        assert summary["active_file"] == "test.py"
        assert summary["turn_count"] == 1
        assert summary["last_operation"] is not None
        assert summary["last_operation"]["target"] == "test.py"

    def test_reset(self) -> None:
        """Test resetting tracker state."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")
        tracker.track_entity(EntityType.FILE, "other.py")
        tracker.increment_turn()

        tracker.reset()

        assert tracker.active_file is None
        assert tracker.last_operation is None
        assert tracker.turn_count == 0
        assert tracker.get_recent_files() == []

    def test_looks_like_file(self) -> None:
        """Test file path detection."""
        tracker = SessionContextTracker()

        assert tracker._looks_like_file("test.py")
        assert tracker._looks_like_file("src/main.py")
        assert tracker._looks_like_file("./config.json")
        assert tracker._looks_like_file("/etc/config")
        assert not tracker._looks_like_file("http://example.com")
        assert not tracker._looks_like_file("")

    def test_looks_like_url(self) -> None:
        """Test URL detection."""
        tracker = SessionContextTracker()

        assert tracker._looks_like_url("http://example.com")
        assert tracker._looks_like_url("https://api.example.com/data")
        assert tracker._looks_like_url("ftp://files.example.com")
        assert not tracker._looks_like_url("test.py")
        assert not tracker._looks_like_url("/path/to/file")

    def test_operation_history_limit(self) -> None:
        """Test operations are limited to MAX_OPERATIONS."""
        tracker = SessionContextTracker()

        # Add more than MAX_OPERATIONS
        for i in range(60):
            tracker.track_operation(
                OperationType.READ,
                f"file{i}.py",
                "Read",
            )

        ops = tracker.get_recent_operations(100)
        assert len(ops) <= 50  # MAX_OPERATIONS


class TestTrackedEntitySerialization:
    """Tests for TrackedEntity serialization."""

    def test_to_dict(self) -> None:
        """Test entity serialization to dict."""
        entity = TrackedEntity(
            type=EntityType.FILE,
            value="test.py",
            context="main file",
            mention_count=3,
            last_mentioned=5,
        )

        data = entity.to_dict()

        assert data["type"] == "file"
        assert data["value"] == "test.py"
        assert data["context"] == "main file"
        assert data["mention_count"] == 3
        assert data["last_mentioned"] == 5

    def test_from_dict(self) -> None:
        """Test entity deserialization from dict."""
        data = {
            "type": "function",
            "value": "my_func",
            "context": "helper function",
            "mention_count": 2,
            "last_mentioned": 10,
        }

        entity = TrackedEntity.from_dict(data)

        assert entity.type == EntityType.FUNCTION
        assert entity.value == "my_func"
        assert entity.context == "helper function"
        assert entity.mention_count == 2
        assert entity.last_mentioned == 10

    def test_from_dict_defaults(self) -> None:
        """Test entity deserialization with missing optional fields."""
        data = {
            "type": "class",
            "value": "MyClass",
        }

        entity = TrackedEntity.from_dict(data)

        assert entity.type == EntityType.CLASS
        assert entity.value == "MyClass"
        assert entity.context == ""
        assert entity.mention_count == 1
        assert entity.last_mentioned == 0

    def test_roundtrip(self) -> None:
        """Test entity serialization roundtrip."""
        original = TrackedEntity(
            type=EntityType.URL,
            value="https://example.com",
            context="API endpoint",
            mention_count=5,
            last_mentioned=15,
        )

        restored = TrackedEntity.from_dict(original.to_dict())

        assert restored.type == original.type
        assert restored.value == original.value
        assert restored.context == original.context
        assert restored.mention_count == original.mention_count
        assert restored.last_mentioned == original.last_mentioned


class TestTrackedOperationSerialization:
    """Tests for TrackedOperation serialization."""

    def test_to_dict(self) -> None:
        """Test operation serialization to dict."""
        op = TrackedOperation(
            type=OperationType.EDIT,
            target="src/main.py",
            tool_name="Edit",
            success=True,
            result_summary="Updated function",
            turn=3,
        )

        data = op.to_dict()

        assert data["type"] == "edit"
        assert data["target"] == "src/main.py"
        assert data["tool_name"] == "Edit"
        assert data["success"] is True
        assert data["result_summary"] == "Updated function"
        assert data["turn"] == 3

    def test_from_dict(self) -> None:
        """Test operation deserialization from dict."""
        data = {
            "type": "write",
            "target": "new_file.py",
            "tool_name": "Write",
            "success": False,
            "result_summary": "Failed to write",
            "turn": 7,
        }

        op = TrackedOperation.from_dict(data)

        assert op.type == OperationType.WRITE
        assert op.target == "new_file.py"
        assert op.tool_name == "Write"
        assert op.success is False
        assert op.result_summary == "Failed to write"
        assert op.turn == 7

    def test_roundtrip(self) -> None:
        """Test operation serialization roundtrip."""
        original = TrackedOperation(
            type=OperationType.SEARCH,
            target="*.py",
            tool_name="Glob",
            success=True,
            result_summary="Found 10 files",
            turn=12,
        )

        restored = TrackedOperation.from_dict(original.to_dict())

        assert restored.type == original.type
        assert restored.target == original.target
        assert restored.tool_name == original.tool_name
        assert restored.success == original.success
        assert restored.result_summary == original.result_summary
        assert restored.turn == original.turn


class TestSessionContextTrackerPersistence:
    """Tests for SessionContextTracker persistence."""

    def test_to_dict_empty(self) -> None:
        """Test serializing empty tracker."""
        tracker = SessionContextTracker()
        data = tracker.to_dict()

        assert data["active_file"] is None
        assert data["last_operation"] is None
        assert data["entities"] == {}
        assert data["operations"] == []
        assert data["turn_count"] == 0

    def test_to_dict_with_data(self) -> None:
        """Test serializing tracker with data."""
        tracker = SessionContextTracker()
        tracker.set_active_file("main.py")
        tracker.track_operation(OperationType.READ, "main.py", "Read")
        tracker.track_entity(EntityType.FUNCTION, "process_data")
        tracker.increment_turn()

        data = tracker.to_dict()

        assert data["active_file"] == "main.py"
        assert data["last_operation"] is not None
        assert data["last_operation"]["target"] == "main.py"
        assert len(data["entities"]) >= 1
        assert len(data["operations"]) == 1
        assert data["turn_count"] == 1

    def test_load_from_dict(self) -> None:
        """Test loading tracker from dict."""
        data = {
            "active_file": "config.py",
            "last_operation": {
                "type": "edit",
                "target": "config.py",
                "tool_name": "Edit",
                "success": True,
                "result_summary": "Updated config",
                "turn": 5,
            },
            "entities": {
                "file:config.py": {
                    "type": "file",
                    "value": "config.py",
                    "context": "",
                    "mention_count": 2,
                    "last_mentioned": 5,
                }
            },
            "operations": [
                {
                    "type": "edit",
                    "target": "config.py",
                    "tool_name": "Edit",
                    "success": True,
                    "result_summary": "Updated config",
                    "turn": 5,
                }
            ],
            "turn_count": 5,
        }

        tracker = SessionContextTracker()
        tracker.load_from_dict(data)

        assert tracker.active_file == "config.py"
        assert tracker.last_operation is not None
        assert tracker.last_operation.target == "config.py"
        assert tracker.turn_count == 5
        assert len(tracker.get_recent_files()) == 1

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = SessionContextTracker()
        original.set_active_file("app.py")
        original.track_operation(OperationType.WRITE, "app.py", "Write")
        original.track_entity(EntityType.CLASS, "Application")
        original.increment_turn()
        original.increment_turn()

        # Serialize and restore
        data = original.to_dict()
        restored = SessionContextTracker()
        restored.load_from_dict(data)

        assert restored.active_file == original.active_file
        assert restored.turn_count == original.turn_count
        assert restored.last_operation is not None
        assert restored.last_operation.target == "app.py"

    def test_save_to_session(self) -> None:
        """Test saving context to session metadata."""

        # Mock session object
        class MockSession:
            def __init__(self) -> None:
                self.metadata: dict = {}

        session = MockSession()
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")
        tracker.increment_turn()

        tracker.save_to_session(session)

        assert "session_context" in session.metadata
        assert session.metadata["session_context"]["active_file"] == "test.py"
        assert session.metadata["session_context"]["turn_count"] == 1

    def test_load_from_session(self) -> None:
        """Test loading context from session metadata."""

        # Mock session object with existing context
        class MockSession:
            def __init__(self) -> None:
                self.metadata: dict = {
                    "session_context": {
                        "active_file": "restored.py",
                        "last_operation": None,
                        "entities": {},
                        "operations": [],
                        "turn_count": 10,
                    }
                }

        session = MockSession()
        tracker = SessionContextTracker()

        result = tracker.load_from_session(session)

        assert result is True
        assert tracker.active_file == "restored.py"
        assert tracker.turn_count == 10

    def test_load_from_session_no_data(self) -> None:
        """Test loading from session with no context data."""

        class MockSession:
            def __init__(self) -> None:
                self.metadata: dict = {}

        session = MockSession()
        tracker = SessionContextTracker()
        tracker.set_active_file("existing.py")  # Pre-existing state

        result = tracker.load_from_session(session)

        assert result is False
        # Original state should be preserved
        assert tracker.active_file == "existing.py"

    def test_load_from_session_no_metadata(self) -> None:
        """Test loading from session without metadata attribute."""

        class MockSession:
            pass

        session = MockSession()
        tracker = SessionContextTracker()

        result = tracker.load_from_session(session)

        assert result is False
