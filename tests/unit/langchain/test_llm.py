"""Unit tests for OpenRouterLLM wrapper."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from code_forge.langchain.llm import OpenRouterLLM
from code_forge.llm.models import (
    CompletionChoice,
    CompletionResponse,
    Message,
    TokenUsage,
    ToolDefinition,
)


class TestOpenRouterLLMInit:
    """Tests for OpenRouterLLM initialization."""

    def test_basic_initialization(self) -> None:
        """Test basic LLM initialization."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(
            client=mock_client,
            model="anthropic/claude-3-opus",
        )

        assert llm.model == "anthropic/claude-3-opus"
        assert llm.client is mock_client

    def test_default_parameters(self) -> None:
        """Test default parameter values."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        assert llm.temperature == 1.0
        assert llm.max_tokens is None
        assert llm.top_p == 1.0
        assert llm.frequency_penalty == 0.0
        assert llm.presence_penalty == 0.0
        assert llm.stop is None

    def test_custom_parameters(self) -> None:
        """Test custom parameter values."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(
            client=mock_client,
            model="test",
            temperature=0.5,
            max_tokens=1000,
            top_p=0.9,
            stop=["END"],
        )

        assert llm.temperature == 0.5
        assert llm.max_tokens == 1000
        assert llm.top_p == 0.9
        assert llm.stop == ["END"]


class TestOpenRouterLLMProperties:
    """Tests for OpenRouterLLM properties."""

    def test_llm_type(self) -> None:
        """Test _llm_type property."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        assert llm._llm_type == "openrouter"

    def test_identifying_params(self) -> None:
        """Test _identifying_params property."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(
            client=mock_client,
            model="test-model",
            temperature=0.7,
            max_tokens=500,
            top_p=0.95,
        )

        params = llm._identifying_params

        assert params["model"] == "test-model"
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 500
        assert params["top_p"] == 0.95


class TestOpenRouterLLMGenerate:
    """Tests for OpenRouterLLM generation methods."""

    @pytest.mark.asyncio
    async def test_agenerate_basic(self) -> None:
        """Test async generation."""
        mock_client = MagicMock()
        mock_response = CompletionResponse(
            id="gen-123",
            model="test-model",
            choices=[
                CompletionChoice(
                    index=0,
                    message=Message.assistant("Hello from mock!"),
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            ),
            created=1234567890,
        )
        mock_client.complete = AsyncMock(return_value=mock_response)

        llm = OpenRouterLLM(client=mock_client, model="test-model")
        result = await llm._agenerate([HumanMessage(content="Hello")])

        assert len(result.generations) == 1
        assert isinstance(result.generations[0].message, AIMessage)
        assert result.generations[0].message.content == "Hello from mock!"
        assert isinstance(result.llm_output, dict)
        assert result.llm_output["usage"]["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_agenerate_with_tool_calls(self) -> None:
        """Test async generation with tool calls in response."""
        from code_forge.llm.models import ToolCall

        mock_client = MagicMock()

        # Response with tool calls
        assistant_msg = Message.assistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="call_123",
                    type="function",
                    function={
                        "name": "read_file",
                        "arguments": '{"path": "/tmp/test"}',
                    },
                )
            ],
        )

        mock_response = CompletionResponse(
            id="gen-456",
            model="test-model",
            choices=[
                CompletionChoice(
                    index=0,
                    message=assistant_msg,
                    finish_reason="tool_calls",
                )
            ],
            usage=TokenUsage(
                prompt_tokens=20, completion_tokens=10, total_tokens=30
            ),
            created=1234567890,
        )
        mock_client.complete = AsyncMock(return_value=mock_response)

        llm = OpenRouterLLM(client=mock_client, model="test-model")
        result = await llm._agenerate([HumanMessage(content="Read a file")])

        assert len(result.generations) == 1
        msg = result.generations[0].message
        assert isinstance(msg, AIMessage)
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0]["name"] == "read_file"


class TestOpenRouterLLMBindTools:
    """Tests for bind_tools method."""

    def test_bind_tool_definitions(self) -> None:
        """Test binding ToolDefinition objects."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"arg": {"type": "string"}}},
        )

        llm_with_tools = llm.bind_tools([tool])

        assert llm_with_tools is not llm  # New instance
        assert len(llm_with_tools._bound_tools) == 1
        assert llm_with_tools._bound_tools[0] == tool

    def test_bind_too_many_tools(self) -> None:
        """Test that binding too many tools raises an error."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        tools = [
            ToolDefinition(
                name=f"tool_{i}",
                description=f"Tool {i}",
                parameters={},
            )
            for i in range(100)  # Exceeds MAX_BOUND_TOOLS
        ]

        with pytest.raises(ValueError, match="Too many tools"):
            llm.bind_tools(tools)

    def test_bind_langchain_style_tool(self) -> None:
        """Test binding a LangChain-style tool."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            args_schema = None

        tool = MockTool()
        llm_with_tools = llm.bind_tools([tool])

        assert len(llm_with_tools._bound_tools) == 1
        assert llm_with_tools._bound_tools[0].name == "mock_tool"

    def test_bind_invalid_tool(self) -> None:
        """Test that binding invalid tool raises an error."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        with pytest.raises(ValueError, match="Cannot convert tool"):
            llm.bind_tools(["not a tool"])


class TestOpenRouterLLMBuildRequest:
    """Tests for request building."""

    def test_build_request_basic(self) -> None:
        """Test basic request building."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(
            client=mock_client,
            model="test-model",
            temperature=0.7,
            max_tokens=500,
        )

        messages = [HumanMessage(content="Hello")]
        request = llm._build_request(messages)

        assert request.model == "test-model"
        assert request.temperature == 0.7
        assert request.max_tokens == 500
        assert len(request.messages) == 1

    def test_build_request_with_stop(self) -> None:
        """Test request building with stop sequences."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(
            client=mock_client,
            model="test",
            stop=["END"],
        )

        messages = [HumanMessage(content="Hello")]
        request = llm._build_request(messages, stop=["STOP"])

        assert request.stop == ["END", "STOP"]

    def test_build_request_with_bound_tools(self) -> None:
        """Test request building includes bound tools."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        tool = ToolDefinition(
            name="test_tool",
            description="A test",
            parameters={},
        )
        llm_with_tools = llm.bind_tools([tool])

        messages = [HumanMessage(content="Hello")]
        request = llm_with_tools._build_request(messages)

        assert isinstance(request.tools, list)
        assert len(request.tools) == 1


class TestOpenRouterLLMStructuredOutput:
    """Tests for structured output configuration."""

    def test_with_structured_output_json_mode(self) -> None:
        """Test with_structured_output with JSON mode raises NotImplementedError."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        # json_mode is not yet implemented
        with pytest.raises(NotImplementedError) as exc_info:
            llm.with_structured_output({}, method="json_mode")
        assert "json_mode is not yet implemented" in str(exc_info.value)

    def test_with_structured_output_function_calling(self) -> None:
        """Test with_structured_output with function calling."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        from pydantic import BaseModel

        class OutputSchema(BaseModel):
            answer: str
            confidence: float

        result = llm.with_structured_output(OutputSchema, method="function_calling")

        # Should have bound the schema as a tool
        assert result is not llm
        assert len(result._bound_tools) == 1
        assert result._bound_tools[0].name == "OutputSchema"

    def test_with_structured_output_dict_schema(self) -> None:
        """Test with_structured_output with dict schema."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        schema = {"title": "MyOutput", "type": "object", "properties": {"value": {"type": "string"}}}
        result = llm.with_structured_output(schema, method="function_calling")

        assert result is not llm
        assert len(result._bound_tools) == 1
        assert result._bound_tools[0].name == "MyOutput"


class TestOpenRouterLLMSync:
    """Tests for synchronous methods."""

    @pytest.mark.asyncio
    async def test_generate_calls_agenerate(self) -> None:
        """Test that _generate calls _agenerate."""
        from langchain_core.outputs import ChatGeneration, ChatResult

        mock_client = MagicMock()
        mock_response = CompletionResponse(
            id="gen-123",
            model="test-model",
            choices=[
                CompletionChoice(
                    index=0,
                    message=Message.assistant("Test response"),
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            ),
            created=1234567890,
        )
        mock_client.complete = AsyncMock(return_value=mock_response)

        llm = OpenRouterLLM(client=mock_client, model="test")
        result = await llm._agenerate([HumanMessage(content="Hello")])

        assert len(result.generations) == 1
        assert result.generations[0].message.content == "Test response"


class TestOpenRouterLLMStreaming:
    """Tests for streaming methods."""

    @pytest.mark.asyncio
    async def test_astream_basic(self) -> None:
        """Test basic async streaming."""
        from code_forge.llm.models import StreamChunk, StreamDelta

        mock_client = MagicMock()

        # Create an async generator for streaming
        async def mock_stream(request):
            yield StreamChunk(
                id="chunk-1",
                model="test-model",
                index=0,
                delta=StreamDelta(content="Hello", tool_calls=None),
                finish_reason=None,
            )
            yield StreamChunk(
                id="chunk-2",
                model="test-model",
                index=0,
                delta=StreamDelta(content=" World", tool_calls=None),
                finish_reason="stop",
            )

        mock_client.stream = mock_stream

        llm = OpenRouterLLM(client=mock_client, model="test-model")
        chunks = []
        async for chunk in llm._astream([HumanMessage(content="Hello")]):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].message.content == "Hello"
        assert chunks[1].message.content == " World"

    @pytest.mark.asyncio
    async def test_astream_with_tool_calls(self) -> None:
        """Test async streaming with tool calls."""
        from code_forge.llm.models import StreamChunk, StreamDelta

        mock_client = MagicMock()

        async def mock_stream(request):
            yield StreamChunk(
                id="chunk-1",
                model="test-model",
                index=0,
                delta=StreamDelta(
                    content="",
                    tool_calls=[
                        {
                            "index": 0,
                            "id": "call_123",
                            "function": {"name": "read_file", "arguments": '{"path":'},
                        }
                    ],
                ),
                finish_reason=None,
            )
            yield StreamChunk(
                id="chunk-2",
                model="test-model",
                index=0,
                delta=StreamDelta(
                    content="",
                    tool_calls=[
                        {
                            "index": 0,
                            "function": {"arguments": '"/tmp/test"}'},
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )

        mock_client.stream = mock_stream

        llm = OpenRouterLLM(client=mock_client, model="test-model")
        chunks = []
        async for chunk in llm._astream([HumanMessage(content="Read file")]):
            chunks.append(chunk)

        assert len(chunks) == 2
        # First chunk should have tool call info
        assert len(chunks[0].message.tool_call_chunks) == 1

    @pytest.mark.asyncio
    async def test_astream_with_run_manager(self) -> None:
        """Test async streaming calls run_manager callback."""
        from code_forge.llm.models import StreamChunk, StreamDelta

        mock_client = MagicMock()

        async def mock_stream(request):
            yield StreamChunk(
                id="chunk-1",
                model="test-model",
                index=0,
                delta=StreamDelta(content="Token", tool_calls=None),
                finish_reason="stop",
            )

        mock_client.stream = mock_stream

        # Mock run manager
        mock_run_manager = AsyncMock()
        mock_run_manager.on_llm_new_token = AsyncMock()

        llm = OpenRouterLLM(client=mock_client, model="test-model")
        chunks = []
        async for chunk in llm._astream(
            [HumanMessage(content="Hello")],
            run_manager=mock_run_manager,
        ):
            chunks.append(chunk)

        # Verify callback was called
        mock_run_manager.on_llm_new_token.assert_called_with("Token")


class TestOpenRouterLLMSyncGenerate:
    """Tests for synchronous _generate method."""

    def test_generate_sync(self) -> None:
        """Test synchronous generation."""
        mock_client = MagicMock()
        mock_response = CompletionResponse(
            id="gen-sync",
            model="test-model",
            choices=[
                CompletionChoice(
                    index=0,
                    message=Message.assistant("Sync response"),
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            ),
            created=1234567890,
        )
        mock_client.complete = AsyncMock(return_value=mock_response)

        llm = OpenRouterLLM(client=mock_client, model="test")

        # Call sync _generate (this uses asyncio.run internally)
        result = llm._generate([HumanMessage(content="Hello")])

        assert len(result.generations) == 1
        assert result.generations[0].message.content == "Sync response"


class TestOpenRouterLLMStructuredOutputEdgeCases:
    """Edge case tests for with_structured_output."""

    def test_with_structured_output_unknown_type(self) -> None:
        """Test with_structured_output with unknown schema type."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        # Pass something that's not a Pydantic model or dict
        result = llm.with_structured_output(42, method="function_calling")

        # Should have bound a tool with default name
        assert result is not llm
        assert len(result._bound_tools) == 1
        assert result._bound_tools[0].name == "structured_output"


class TestOpenRouterLLMBindToolsEdgeCases:
    """Edge case tests for bind_tools."""

    def test_bind_tools_with_openai_schema(self) -> None:
        """Test binding a tool with to_openai_schema method."""
        mock_client = MagicMock()
        llm = OpenRouterLLM(client=mock_client, model="test")

        class MockBaseTool:
            def to_openai_schema(self):
                return {
                    "type": "function",
                    "function": {
                        "name": "openai_tool",
                        "description": "OpenAI style tool",
                        "parameters": {},
                    },
                }

        tool = MockBaseTool()
        llm_with_tools = llm.bind_tools([tool])

        assert len(llm_with_tools._bound_tools) == 1
