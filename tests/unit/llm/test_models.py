"""Unit tests for LLM models."""

import pytest

from code_forge.llm.models import (
    CompletionChoice,
    CompletionRequest,
    CompletionResponse,
    ContentPart,
    Message,
    MessageRole,
    StreamChunk,
    StreamDelta,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


class TestMessageRole:
    """Tests for MessageRole enum."""

    @pytest.mark.parametrize(
        "role,expected_value",
        [
            (MessageRole.SYSTEM, "system"),
            (MessageRole.USER, "user"),
            (MessageRole.ASSISTANT, "assistant"),
            (MessageRole.TOOL, "tool"),
        ]
    )
    def test_role_values(self, role: MessageRole, expected_value: str) -> None:
        assert role.value == expected_value


class TestContentPart:
    """Tests for ContentPart dataclass."""

    def test_text_content_to_dict(self) -> None:
        part = ContentPart(type="text", text="Hello world")
        result = part.to_dict()
        assert result == {"type": "text", "text": "Hello world"}

    def test_image_content_to_dict(self) -> None:
        part = ContentPart(
            type="image_url", image_url={"url": "https://example.com/image.png"}
        )
        result = part.to_dict()
        assert result == {
            "type": "image_url",
            "image_url": {"url": "https://example.com/image.png"},
        }


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_to_dict(self) -> None:
        tc = ToolCall(
            id="call_123",
            type="function",
            function={"name": "read_file", "arguments": '{"path": "/tmp/test"}'},
        )
        result = tc.to_dict()
        assert result == {
            "id": "call_123",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "/tmp/test"}'},
        }

    def test_from_dict(self) -> None:
        data = {
            "id": "call_456",
            "type": "function",
            "function": {"name": "write_file", "arguments": '{}'},
        }
        tc = ToolCall.from_dict(data)
        assert tc.id == "call_456"
        assert tc.type == "function"
        assert tc.function["name"] == "write_file"


class TestMessage:
    """Tests for Message dataclass."""

    @pytest.mark.parametrize(
        "factory_method,content,expected_role",
        [
            (Message.system, "You are a helpful assistant.", MessageRole.SYSTEM),
            (Message.user, "Hello!", MessageRole.USER),
            (Message.assistant, "Hello! How can I help?", MessageRole.ASSISTANT),
        ]
    )
    def test_message_factories(self, factory_method, content: str, expected_role: MessageRole) -> None:
        msg = factory_method(content)
        assert msg.role == expected_role
        assert msg.content == content

    def test_assistant_factory_with_tool_calls(self) -> None:
        tool_call = ToolCall(id="call_1", type="function", function={"name": "test"})
        msg = Message.assistant(content=None, tool_calls=[tool_call])
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content is None
        assert isinstance(msg.tool_calls, list)
        assert len(msg.tool_calls) == 1

    def test_tool_result_factory(self) -> None:
        msg = Message.tool_result("call_abc123", "File contents here")
        assert msg.role == MessageRole.TOOL
        assert msg.tool_call_id == "call_abc123"
        assert msg.content == "File contents here"

    def test_to_dict_simple(self) -> None:
        msg = Message.user("Hello!")
        result = msg.to_dict()
        assert result == {"role": "user", "content": "Hello!"}

    def test_to_dict_with_tool_calls(self) -> None:
        tool_call = ToolCall(
            id="call_1", type="function", function={"name": "test", "arguments": "{}"}
        )
        msg = Message.assistant(content=None, tool_calls=[tool_call])
        result = msg.to_dict()
        assert result["role"] == "assistant"
        assert result["content"] is None
        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1

    def test_to_dict_multimodal(self) -> None:
        parts = [
            ContentPart(type="text", text="What's in this image?"),
            ContentPart(type="image_url", image_url={"url": "https://example.com/img.png"}),
        ]
        msg = Message.user(parts)
        result = msg.to_dict()
        assert result["role"] == "user"
        assert isinstance(result["content"], list)
        assert len(result["content"]) == 2

    def test_to_dict_tool_result(self) -> None:
        msg = Message.tool_result("call_123", "Result data")
        result = msg.to_dict()
        assert result["role"] == "tool"
        assert result["content"] == "Result data"
        assert result["tool_call_id"] == "call_123"

    def test_from_dict_simple(self) -> None:
        data = {"role": "user", "content": "Hello!"}
        msg = Message.from_dict(data)
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello!"

    def test_from_dict_with_tool_calls(self) -> None:
        data = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "test"}}
            ],
        }
        msg = Message.from_dict(data)
        assert msg.role == MessageRole.ASSISTANT
        assert isinstance(msg.tool_calls, list)
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call_1"


class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""

    def test_to_dict(self) -> None:
        tool = ToolDefinition(
            name="read_file",
            description="Read a file from disk",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )
        result = tool.to_dict()
        assert result == {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from disk",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        }


class TestCompletionRequest:
    """Tests for CompletionRequest dataclass."""

    def test_basic_request_to_dict(self) -> None:
        request = CompletionRequest(
            model="anthropic/claude-3-opus",
            messages=[Message.user("Hello!")],
        )
        result = request.to_dict()
        assert result["model"] == "anthropic/claude-3-opus"
        assert len(result["messages"]) == 1
        assert result["temperature"] == 1.0
        assert result["stream"] is False

    def test_request_with_tools(self) -> None:
        tool = ToolDefinition(
            name="test", description="test tool", parameters={"type": "object"}
        )
        request = CompletionRequest(
            model="test/model",
            messages=[Message.user("Hello!")],
            tools=[tool],
            tool_choice="auto",
        )
        result = request.to_dict()
        assert "tools" in result
        assert result["tool_choice"] == "auto"

    def test_request_with_optional_params(self) -> None:
        request = CompletionRequest(
            model="test/model",
            messages=[Message.user("Hello!")],
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop=["\n\n"],
        )
        result = request.to_dict()
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 1000
        assert result["top_p"] == 0.9
        assert result["frequency_penalty"] == 0.5
        assert result["presence_penalty"] == 0.3
        assert result["stop"] == ["\n\n"]

    def test_request_with_openrouter_params(self) -> None:
        request = CompletionRequest(
            model="test/model",
            messages=[Message.user("Hello!")],
            transforms=["middle-out"],
            route="fallback",
        )
        result = request.to_dict()
        assert result["transforms"] == ["middle-out"]
        assert result["route"] == "fallback"


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_from_dict(self) -> None:
        data = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        usage = TokenUsage.from_dict(data)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 5
        assert usage.total_tokens == 15

    def test_from_dict_missing_fields(self) -> None:
        usage = TokenUsage.from_dict({})
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestCompletionChoice:
    """Tests for CompletionChoice dataclass."""

    def test_from_dict(self) -> None:
        data = {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello!"},
            "finish_reason": "stop",
        }
        choice = CompletionChoice.from_dict(data)
        assert choice.index == 0
        assert choice.message.content == "Hello!"
        assert choice.finish_reason == "stop"


class TestCompletionResponse:
    """Tests for CompletionResponse dataclass."""

    def test_from_dict(self) -> None:
        data = {
            "id": "gen-abc123",
            "model": "anthropic/claude-3-opus",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "created": 1705312345,
        }
        response = CompletionResponse.from_dict(data)
        assert response.id == "gen-abc123"
        assert response.model == "anthropic/claude-3-opus"
        assert len(response.choices) == 1
        assert response.choices[0].message.content == "Hello!"
        assert response.usage.total_tokens == 15
        assert response.created == 1705312345

    def test_from_dict_with_provider(self) -> None:
        data = {
            "id": "gen-123",
            "model": "test/model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hi"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
            "created": 1705312345,
            "provider": "anthropic",
        }
        response = CompletionResponse.from_dict(data)
        assert response.provider == "anthropic"


class TestStreamDelta:
    """Tests for StreamDelta dataclass."""

    def test_from_dict_with_role(self) -> None:
        delta = StreamDelta.from_dict({"role": "assistant"})
        assert delta.role == "assistant"
        assert delta.content is None

    def test_from_dict_with_content(self) -> None:
        delta = StreamDelta.from_dict({"content": "Hello"})
        assert delta.content == "Hello"

    def test_from_dict_with_tool_calls(self) -> None:
        data = {"tool_calls": [{"index": 0, "id": "call_1"}]}
        delta = StreamDelta.from_dict(data)
        assert isinstance(delta.tool_calls, list)
        assert len(delta.tool_calls) == 1


class TestStreamChunk:
    """Tests for StreamChunk dataclass."""

    def test_from_dict(self) -> None:
        data = {
            "id": "gen-123",
            "model": "test/model",
            "choices": [
                {"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}
            ],
        }
        chunk = StreamChunk.from_dict(data)
        assert chunk.id == "gen-123"
        assert chunk.model == "test/model"
        assert chunk.delta.content == "Hello"
        assert chunk.finish_reason is None

    @pytest.mark.parametrize(
        "finish_reason",
        [
            "stop",
            "length",
            "tool_calls",
            "content_filter",
        ]
    )
    def test_from_dict_with_finish_reason(self, finish_reason: str) -> None:
        data = {
            "id": "gen-123",
            "model": "test/model",
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
        }
        chunk = StreamChunk.from_dict(data)
        assert chunk.finish_reason == finish_reason

    def test_from_dict_with_usage(self) -> None:
        data = {
            "id": "gen-123",
            "model": "test/model",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        chunk = StreamChunk.from_dict(data)
        assert isinstance(chunk.usage, TokenUsage)
        assert chunk.usage.total_tokens == 15

    def test_from_dict_empty_choices(self) -> None:
        data = {"id": "gen-123", "model": "test/model", "choices": []}
        chunk = StreamChunk.from_dict(data)
        assert chunk.index == 0
        assert chunk.delta.content is None


class TestCompletionRequestParameters:
    """Test completion request with various parameters."""

    @pytest.mark.parametrize(
        "temperature,max_tokens,top_p",
        [
            (0.0, 100, 1.0),
            (0.5, 500, 0.9),
            (0.7, 1000, 0.95),
            (1.0, 2000, 1.0),
            (1.5, 4000, 0.8),
        ]
    )
    def test_request_with_sampling_params(self, temperature: float, max_tokens: int, top_p: float) -> None:
        request = CompletionRequest(
            model="test/model",
            messages=[Message.user("Test")],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )
        result = request.to_dict()
        assert result["temperature"] == temperature
        assert result["max_tokens"] == max_tokens
        assert result["top_p"] == top_p
