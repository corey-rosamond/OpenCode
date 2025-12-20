"""Tests for core value objects and types."""

from __future__ import annotations

from datetime import datetime

import pytest

from code_forge.core.types import (
    AgentId,
    CompletionRequest,
    CompletionResponse,
    Message,
    ProjectId,
    Session,
    SessionId,
    SessionSummary,
    ToolParameter,
    ToolResult,
)


class TestAgentId:
    """Tests for AgentId value object."""

    def test_create_agent_id_generates_uuid(self) -> None:
        """AgentId should generate a UUID when created without arguments."""
        agent_id = AgentId()
        assert isinstance(agent_id.value, str)
        assert len(agent_id.value) == 36  # UUID format

    def test_agent_id_string_representation(self) -> None:
        """AgentId should convert to string correctly."""
        agent_id = AgentId(value="test-uuid")
        assert str(agent_id) == "test-uuid"

    def test_agent_id_is_hashable(self) -> None:
        """AgentId should be hashable for use in sets/dicts."""
        agent_id = AgentId(value="test-uuid")
        hash_value = hash(agent_id)
        assert isinstance(hash_value, int)

    def test_agent_id_equality(self) -> None:
        """AgentIds with same value should be equal."""
        id1 = AgentId(value="same-value")
        id2 = AgentId(value="same-value")
        id3 = AgentId(value="different-value")
        assert id1 == id2
        assert id1 != id3

    def test_agent_id_can_be_used_in_set(self) -> None:
        """AgentId should work correctly in sets."""
        id1 = AgentId(value="test-1")
        id2 = AgentId(value="test-1")
        id3 = AgentId(value="test-2")
        agent_set = {id1, id2, id3}
        assert len(agent_set) == 2


class TestSessionId:
    """Tests for SessionId value object."""

    def test_create_session_id(self) -> None:
        """SessionId should store the provided value."""
        session_id = SessionId(value="session-123")
        assert session_id.value == "session-123"

    def test_session_id_string_representation(self) -> None:
        """SessionId should convert to string correctly."""
        session_id = SessionId(value="session-abc")
        assert str(session_id) == "session-abc"

    def test_session_id_is_hashable(self) -> None:
        """SessionId should be hashable."""
        session_id = SessionId(value="session-123")
        hash_value = hash(session_id)
        assert isinstance(hash_value, int)

    def test_session_id_equality(self) -> None:
        """SessionIds with same value should be equal."""
        id1 = SessionId(value="session-1")
        id2 = SessionId(value="session-1")
        id3 = SessionId(value="session-2")
        assert id1 == id2
        assert id1 != id3


class TestProjectId:
    """Tests for ProjectId value object."""

    def test_create_project_id_from_path(self) -> None:
        """ProjectId should create a hashed value from path."""
        project_id = ProjectId.from_path("/home/user/project")
        assert isinstance(project_id.value, str)
        assert len(project_id.value) == 12  # Truncated hash
        assert project_id.path == "/home/user/project"

    def test_project_id_stores_original_path(self) -> None:
        """ProjectId should store the original path."""
        path = "/test/project/path"
        project_id = ProjectId.from_path(path)
        assert project_id.path == path

    def test_project_id_same_path_same_hash(self) -> None:
        """Same path should produce same hash."""
        id1 = ProjectId.from_path("/same/path")
        id2 = ProjectId.from_path("/same/path")
        assert id1.value == id2.value

    def test_project_id_different_path_different_hash(self) -> None:
        """Different paths should produce different hashes."""
        id1 = ProjectId.from_path("/path/one")
        id2 = ProjectId.from_path("/path/two")
        assert id1.value != id2.value

    def test_project_id_string_representation(self) -> None:
        """ProjectId string should be the hash value."""
        project_id = ProjectId.from_path("/test")
        assert str(project_id) == project_id.value

    def test_project_id_is_hashable(self) -> None:
        """ProjectId should be hashable."""
        project_id = ProjectId.from_path("/test")
        hash_value = hash(project_id)
        assert isinstance(hash_value, int)


class TestToolParameter:
    """Tests for ToolParameter model."""

    def test_create_tool_parameter(self) -> None:
        """ToolParameter should store all fields correctly."""
        param = ToolParameter(
            name="file_path",
            type="string",
            description="Path to the file",
            required=True,
            default=None,
        )
        assert param.name == "file_path"
        assert param.type == "string"
        assert param.description == "Path to the file"
        assert param.required is True
        assert param.default is None

    def test_tool_parameter_defaults(self) -> None:
        """ToolParameter should have correct defaults."""
        param = ToolParameter(
            name="test",
            type="string",
            description="test param",
        )
        assert param.required is True
        assert param.default is None


class TestToolResult:
    """Tests for ToolResult model."""

    def test_create_successful_tool_result(self) -> None:
        """ToolResult should store success correctly."""
        result = ToolResult(
            success=True,
            output="file contents",
        )
        assert result.success is True
        assert result.output == "file contents"
        assert result.error is None

    def test_create_failed_tool_result(self) -> None:
        """ToolResult should store failure correctly."""
        result = ToolResult(
            success=False,
            output=None,
            error="File not found",
        )
        assert result.success is False
        assert result.error == "File not found"

    def test_tool_result_metadata_default(self) -> None:
        """ToolResult should default to empty metadata dict."""
        result = ToolResult(success=True, output="test")
        assert result.metadata == {}


class TestMessage:
    """Tests for Message model."""

    def test_create_user_message(self) -> None:
        """Message should store user role and content."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_calls is None

    def test_create_assistant_message(self) -> None:
        """Message should store assistant messages."""
        msg = Message(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_create_message_with_tool_calls(self) -> None:
        """Message should store tool calls."""
        tool_calls = [{"id": "call_1", "function": {"name": "read_file"}}]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        assert msg.tool_calls == tool_calls


class TestCompletionRequest:
    """Tests for CompletionRequest model."""

    def test_create_completion_request(self) -> None:
        """CompletionRequest should store all fields."""
        messages = [Message(role="user", content="Hello")]
        request = CompletionRequest(
            messages=messages,
            model="gpt-4",
        )
        assert request.messages == messages
        assert request.model == "gpt-4"
        assert request.temperature == 1.0
        assert request.stream is False

    def test_completion_request_defaults(self) -> None:
        """CompletionRequest should have correct defaults."""
        request = CompletionRequest(
            messages=[],
            model="test-model",
        )
        assert request.max_tokens is None
        assert request.temperature == 1.0
        assert request.stream is False
        assert request.tools is None


class TestCompletionResponse:
    """Tests for CompletionResponse model."""

    def test_create_completion_response(self) -> None:
        """CompletionResponse should store all fields."""
        response = CompletionResponse(
            content="Hello!",
            model="gpt-4",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert response.content == "Hello!"
        assert response.model == "gpt-4"
        assert response.finish_reason == "stop"
        assert response.usage["prompt_tokens"] == 10
        assert response.tool_calls is None


class TestSessionSummary:
    """Tests for SessionSummary model."""

    def test_create_session_summary(self) -> None:
        """SessionSummary should store all fields."""
        now = datetime.now()
        summary = SessionSummary(
            id=SessionId(value="sess-1"),
            project_path="/test/project",
            created_at=now,
            last_activity=now,
            message_count=10,
            preview="Hello, how can I help?",
        )
        assert summary.id.value == "sess-1"
        assert summary.project_path == "/test/project"
        assert summary.message_count == 10


class TestSession:
    """Tests for Session model."""

    def test_create_session(self) -> None:
        """Session should store all fields."""
        now = datetime.now()
        session = Session(
            id=SessionId(value="sess-1"),
            project_path="/test/project",
            created_at=now,
            last_activity=now,
            messages=[{"role": "user", "content": "Hello"}],
            context={"key": "value"},
            metadata={"version": "1.0"},
        )
        assert session.id.value == "sess-1"
        assert len(session.messages) == 1
        assert session.context["key"] == "value"
