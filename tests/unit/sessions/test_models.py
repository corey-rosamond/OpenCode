"""Unit tests for session models."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from code_forge.sessions.models import (
    Session,
    SessionMessage,
    ToolInvocation,
)


class TestToolInvocation:
    """Tests for ToolInvocation dataclass."""

    def test_create_with_defaults(self) -> None:
        """Test creating invocation with default values."""
        inv = ToolInvocation()
        assert isinstance(inv.id, str) and len(inv.id) > 0
        assert inv.tool_name == ""
        assert inv.arguments == {}
        assert inv.result is None
        assert inv.success is True
        assert inv.error is None
        assert inv.duration == 0.0
        assert isinstance(inv.timestamp, datetime)

    def test_create_with_values(self) -> None:
        """Test creating invocation with specific values."""
        inv = ToolInvocation(
            tool_name="bash",
            arguments={"command": "ls"},
            result={"output": "file.txt"},
            duration=0.5,
            success=True,
        )
        assert inv.tool_name == "bash"
        assert inv.arguments == {"command": "ls"}
        assert inv.result == {"output": "file.txt"}
        assert inv.duration == 0.5
        assert inv.success is True

    def test_create_failed_invocation(self) -> None:
        """Test creating a failed invocation."""
        inv = ToolInvocation(
            tool_name="read",
            arguments={"file": "missing.txt"},
            success=False,
            error="File not found",
        )
        assert inv.success is False
        assert inv.error == "File not found"

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        inv = ToolInvocation(
            id="test-id",
            tool_name="bash",
            arguments={"command": "pwd"},
            result={"output": "/home"},
            duration=0.1,
            success=True,
        )
        data = inv.to_dict()
        assert data["id"] == "test-id"
        assert data["tool_name"] == "bash"
        assert data["arguments"] == {"command": "pwd"}
        assert data["result"] == {"output": "/home"}
        assert data["duration"] == 0.1
        assert data["success"] is True
        assert data["error"] is None
        assert isinstance(data["timestamp"], str)

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "test-id",
            "tool_name": "read",
            "arguments": {"file": "test.py"},
            "result": {"content": "code"},
            "timestamp": "2024-01-15T10:30:00+00:00",
            "duration": 0.05,
            "success": True,
            "error": None,
        }
        inv = ToolInvocation.from_dict(data)
        assert inv.id == "test-id"
        assert inv.tool_name == "read"
        assert inv.arguments == {"file": "test.py"}
        assert inv.result == {"content": "code"}
        assert inv.duration == 0.05
        assert inv.success is True

    def test_from_dict_missing_fields(self) -> None:
        """Test deserialization with missing fields."""
        data: dict[str, Any] = {"tool_name": "bash"}
        inv = ToolInvocation.from_dict(data)
        assert inv.tool_name == "bash"
        assert isinstance(inv.id, str) and len(inv.id) > 0
        assert inv.arguments == {}
        assert inv.success is True

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        inv = ToolInvocation(
            tool_name="write",
            arguments={"file": "out.txt", "content": "data"},
            result={"bytes_written": 4},
            duration=0.02,
        )
        data = inv.to_dict()
        restored = ToolInvocation.from_dict(data)
        assert restored.tool_name == inv.tool_name
        assert restored.arguments == inv.arguments
        assert restored.result == inv.result
        assert restored.duration == inv.duration


class TestSessionMessage:
    """Tests for SessionMessage dataclass."""

    def test_create_with_defaults(self) -> None:
        """Test creating message with defaults."""
        msg = SessionMessage()
        assert isinstance(msg.id, str) and len(msg.id) > 0
        assert msg.role == "user"
        assert msg.content == ""
        assert msg.tool_calls is None
        assert msg.tool_call_id is None
        assert msg.name is None
        assert isinstance(msg.timestamp, datetime)

    def test_create_user_message(self) -> None:
        """Test creating a user message."""
        msg = SessionMessage(role="user", content="Hello!")
        assert msg.role == "user"
        assert msg.content == "Hello!"

    def test_create_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = SessionMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_create_system_message(self) -> None:
        """Test creating a system message."""
        msg = SessionMessage(role="system", content="You are helpful.")
        assert msg.role == "system"

    def test_create_tool_message(self) -> None:
        """Test creating a tool result message."""
        msg = SessionMessage(
            role="tool",
            content='{"output": "result"}',
            tool_call_id="call_123",
            name="bash",
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_123"
        assert msg.name == "bash"

    def test_create_message_with_tool_calls(self) -> None:
        """Test creating an assistant message with tool calls."""
        tool_calls = [
            {"id": "call_1", "name": "bash", "arguments": {"command": "ls"}}
        ]
        msg = SessionMessage(
            role="assistant",
            content="Let me check...",
            tool_calls=tool_calls,
        )
        assert msg.tool_calls == tool_calls

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        msg = SessionMessage(
            id="msg-id",
            role="user",
            content="Hello!",
        )
        data = msg.to_dict()
        assert data["id"] == "msg-id"
        assert data["role"] == "user"
        assert data["content"] == "Hello!"
        assert "timestamp" in data
        assert "tool_calls" not in data  # None values excluded
        assert "tool_call_id" not in data

    def test_to_dict_with_tool_fields(self) -> None:
        """Test serialization includes tool fields when present."""
        msg = SessionMessage(
            role="tool",
            content="result",
            tool_call_id="call_1",
            name="bash",
        )
        data = msg.to_dict()
        assert data["tool_call_id"] == "call_1"
        assert data["name"] == "bash"

    def test_to_llm_message(self) -> None:
        """Test conversion to LLM message format."""
        msg = SessionMessage(
            id="msg-id",
            role="user",
            content="Hello!",
        )
        llm_msg = msg.to_llm_message()
        assert llm_msg == {"role": "user", "content": "Hello!"}
        assert "id" not in llm_msg
        assert "timestamp" not in llm_msg

    def test_to_llm_message_with_tool_calls(self) -> None:
        """Test conversion includes tool fields."""
        tool_calls = [{"id": "call_1", "name": "bash"}]
        msg = SessionMessage(
            role="assistant",
            content="Running...",
            tool_calls=tool_calls,
        )
        llm_msg = msg.to_llm_message()
        assert llm_msg["tool_calls"] == tool_calls

    def test_from_llm_message(self) -> None:
        """Test creation from LLM message dict."""
        llm_msg = {"role": "user", "content": "Hello!"}
        msg = SessionMessage.from_llm_message(llm_msg)
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert isinstance(msg.id, str) and len(msg.id) > 0  # New ID generated

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "msg-id",
            "role": "assistant",
            "content": "Response",
            "timestamp": "2024-01-15T10:30:00+00:00",
        }
        msg = SessionMessage.from_dict(data)
        assert msg.id == "msg-id"
        assert msg.role == "assistant"
        assert msg.content == "Response"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        msg = SessionMessage(
            role="tool",
            content='{"result": "ok"}',
            tool_call_id="call_1",
            name="read",
        )
        data = msg.to_dict()
        restored = SessionMessage.from_dict(data)
        assert restored.role == msg.role
        assert restored.content == msg.content
        assert restored.tool_call_id == msg.tool_call_id
        assert restored.name == msg.name


class TestSession:
    """Tests for Session dataclass."""

    def test_create_with_defaults(self) -> None:
        """Test creating session with defaults."""
        session = Session()
        assert isinstance(session.id, str) and len(session.id) > 0
        assert session.title == ""
        assert session.working_dir == ""
        assert session.model == ""
        assert session.messages == []
        assert session.tool_history == []
        assert session.total_prompt_tokens == 0
        assert session.total_completion_tokens == 0
        assert session.tags == []
        assert session.metadata == {}
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_create_with_values(self) -> None:
        """Test creating session with specific values."""
        session = Session(
            title="Test Session",
            working_dir="/home/user/project",
            model="anthropic/claude-3",
            tags=["python", "refactoring"],
        )
        assert session.title == "Test Session"
        assert session.working_dir == "/home/user/project"
        assert session.model == "anthropic/claude-3"
        assert session.tags == ["python", "refactoring"]

    def test_add_message(self) -> None:
        """Test adding a message to session."""
        session = Session()
        msg = SessionMessage(role="user", content="Hello!")
        session.add_message(msg)
        assert session.message_count == 1
        assert session.messages[0] is msg

    def test_add_message_from_dict(self) -> None:
        """Test creating and adding message from components."""
        session = Session()
        msg = session.add_message_from_dict("user", "Hello!")
        assert session.message_count == 1
        assert msg.role == "user"
        assert msg.content == "Hello!"

    def test_add_message_updates_timestamp(self) -> None:
        """Test that adding message updates updated_at."""
        session = Session()
        original_updated = session.updated_at
        session.add_message_from_dict("user", "Hello!")
        assert session.updated_at >= original_updated

    def test_add_tool_invocation(self) -> None:
        """Test adding tool invocation."""
        session = Session()
        inv = ToolInvocation(tool_name="bash", arguments={"command": "ls"})
        session.add_tool_invocation(inv)
        assert len(session.tool_history) == 1
        assert session.tool_history[0] is inv

    def test_record_tool_call(self) -> None:
        """Test recording tool call from components."""
        session = Session()
        inv = session.record_tool_call(
            tool_name="read",
            arguments={"file": "test.py"},
            result={"content": "code"},
            duration=0.05,
        )
        assert len(session.tool_history) == 1
        assert inv.tool_name == "read"
        assert inv.arguments == {"file": "test.py"}

    def test_update_usage(self) -> None:
        """Test updating token usage."""
        session = Session()
        session.update_usage(100, 50)
        assert session.total_prompt_tokens == 100
        assert session.total_completion_tokens == 50
        session.update_usage(50, 25)
        assert session.total_prompt_tokens == 150
        assert session.total_completion_tokens == 75

    def test_total_tokens_property(self) -> None:
        """Test total_tokens property."""
        session = Session()
        session.update_usage(100, 50)
        assert session.total_tokens == 150

    def test_message_count_property(self) -> None:
        """Test message_count property."""
        session = Session()
        assert session.message_count == 0
        session.add_message_from_dict("user", "Hello!")
        assert session.message_count == 1
        session.add_message_from_dict("assistant", "Hi!")
        assert session.message_count == 2

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        session = Session(
            id="session-id",
            title="Test",
            working_dir="/tmp",
            model="gpt-4",
            tags=["test"],
        )
        session.add_message_from_dict("user", "Hello!")
        session.record_tool_call("bash", {"command": "ls"})
        session.update_usage(100, 50)

        data = session.to_dict()
        assert data["id"] == "session-id"
        assert data["title"] == "Test"
        assert data["working_dir"] == "/tmp"
        assert data["model"] == "gpt-4"
        assert data["tags"] == ["test"]
        assert len(data["messages"]) == 1
        assert len(data["tool_history"]) == 1
        assert data["total_prompt_tokens"] == 100
        assert data["total_completion_tokens"] == 50
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_to_json(self) -> None:
        """Test serialization to JSON string."""
        session = Session(title="Test")
        json_str = session.to_json()
        parsed = json.loads(json_str)
        assert parsed["title"] == "Test"

    def test_to_json_with_indent(self) -> None:
        """Test JSON serialization with custom indent."""
        session = Session(title="Test")
        json_str = session.to_json(indent=4)
        assert "    " in json_str  # 4-space indent

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "session-id",
            "title": "Test Session",
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:00:00+00:00",
            "working_dir": "/home/user",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello!"}],
            "tool_history": [
                {"tool_name": "bash", "arguments": {"command": "ls"}}
            ],
            "total_prompt_tokens": 100,
            "total_completion_tokens": 50,
            "tags": ["test"],
            "metadata": {"key": "value"},
        }
        session = Session.from_dict(data)
        assert session.id == "session-id"
        assert session.title == "Test Session"
        assert session.working_dir == "/home/user"
        assert session.model == "gpt-4"
        assert session.message_count == 1
        assert len(session.tool_history) == 1
        assert session.total_prompt_tokens == 100
        assert session.total_completion_tokens == 50
        assert session.tags == ["test"]
        assert session.metadata == {"key": "value"}

    def test_from_dict_missing_fields(self) -> None:
        """Test deserialization with missing fields."""
        data: dict[str, Any] = {"title": "Minimal"}
        session = Session.from_dict(data)
        assert session.title == "Minimal"
        assert isinstance(session.id, str) and len(session.id) > 0
        assert session.messages == []
        assert session.tags == []

    def test_from_json(self) -> None:
        """Test deserialization from JSON string."""
        json_str = '{"id": "test-id", "title": "Test"}'
        session = Session.from_json(json_str)
        assert session.id == "test-id"
        assert session.title == "Test"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        session = Session(
            title="Test Session",
            working_dir="/home/user/project",
            model="claude-3",
            tags=["python", "api"],
            metadata={"branch": "main"},
        )
        session.add_message_from_dict("user", "Hello!")
        session.add_message_from_dict("assistant", "Hi there!")
        session.record_tool_call("read", {"file": "main.py"})
        session.update_usage(200, 100)

        # Via dict
        data = session.to_dict()
        restored = Session.from_dict(data)
        assert restored.id == session.id
        assert restored.title == session.title
        assert restored.message_count == session.message_count
        assert len(restored.tool_history) == len(session.tool_history)
        assert restored.total_tokens == session.total_tokens
        assert restored.tags == session.tags

        # Via JSON
        json_str = session.to_json()
        restored2 = Session.from_json(json_str)
        assert restored2.id == session.id

    def test_datetime_timezone_aware(self) -> None:
        """Test that datetimes are timezone-aware UTC."""
        session = Session()
        # Check that tzinfo is set (timezone-aware datetime)
        assert session.created_at.tzinfo is not None, "created_at should be timezone-aware"
        assert session.updated_at.tzinfo is not None, "updated_at should be timezone-aware"
        # Verify they can be formatted as ISO strings without error
        assert isinstance(session.created_at.isoformat(), str)
        assert isinstance(session.updated_at.isoformat(), str)

    def test_metadata_isolation(self) -> None:
        """Test that metadata dicts are independent."""
        s1 = Session()
        s2 = Session()
        s1.metadata["key"] = "value1"
        s2.metadata["key"] = "value2"
        assert s1.metadata["key"] == "value1"
        assert s2.metadata["key"] == "value2"

    def test_tags_isolation(self) -> None:
        """Test that tags lists are independent."""
        s1 = Session()
        s2 = Session()
        s1.tags.append("tag1")
        s2.tags.append("tag2")
        assert s1.tags == ["tag1"]
        assert s2.tags == ["tag2"]


class TestSessionMessageEdgeCases:
    """Edge case tests for SessionMessage to improve coverage."""

    def test_to_llm_message_with_tool_calls(self) -> None:
        """Test to_llm_message includes tool_calls."""
        msg = SessionMessage(
            role="assistant",
            content="",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "read"}}],
        )
        llm_msg = msg.to_llm_message()
        assert "tool_calls" in llm_msg
        assert len(llm_msg["tool_calls"]) == 1

    def test_to_llm_message_with_tool_call_id(self) -> None:
        """Test to_llm_message includes tool_call_id."""
        msg = SessionMessage(
            role="tool",
            content="result",
            tool_call_id="call_1",
        )
        llm_msg = msg.to_llm_message()
        assert llm_msg["tool_call_id"] == "call_1"

    def test_to_llm_message_with_name(self) -> None:
        """Test to_llm_message includes name."""
        msg = SessionMessage(
            role="tool",
            content="result",
            name="read_file",
        )
        llm_msg = msg.to_llm_message()
        assert llm_msg["name"] == "read_file"

    def test_from_llm_message(self) -> None:
        """Test creating SessionMessage from LLM message."""
        llm_msg = {
            "role": "assistant",
            "content": "Hello!",
            "tool_calls": [{"id": "call_1"}],
            "name": "assistant",
        }
        msg = SessionMessage.from_llm_message(llm_msg)
        assert msg.role == "assistant"
        assert msg.content == "Hello!"
        assert msg.tool_calls == [{"id": "call_1"}]
        assert msg.name == "assistant"

    def test_from_llm_message_minimal(self) -> None:
        """Test creating SessionMessage from minimal LLM message."""
        llm_msg: dict[str, Any] = {}
        msg = SessionMessage.from_llm_message(llm_msg)
        assert msg.role == "user"
        assert msg.content == ""


class TestToolInvocationEdgeCases:
    """Edge case tests for ToolInvocation to improve coverage."""

    def test_from_dict_with_none_timestamp(self) -> None:
        """Test from_dict with None timestamp uses current time."""
        data: dict[str, Any] = {
            "tool_name": "bash",
            "arguments": {},
            "timestamp": None,
        }
        inv = ToolInvocation.from_dict(data)
        assert isinstance(inv.timestamp, datetime)


class TestSessionEdgeCases:
    """Edge case tests for Session to improve coverage."""

    def test_from_dict_with_none_dates(self) -> None:
        """Test from_dict with None dates uses current time."""
        data: dict[str, Any] = {
            "title": "Test",
            "created_at": None,
            "updated_at": None,
        }
        session = Session.from_dict(data)
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
