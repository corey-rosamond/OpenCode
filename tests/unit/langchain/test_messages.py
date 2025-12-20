"""Unit tests for message conversion utilities."""

import json

import pytest
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from code_forge.langchain.messages import (
    langchain_messages_to_forge,
    langchain_to_forge,
    forge_messages_to_langchain,
    forge_to_langchain,
)
from code_forge.llm.models import Message, MessageRole, ToolCall


class TestLangchainToForge:
    """Tests for langchain_to_forge conversion."""

    def test_convert_system_message(self) -> None:
        """Test SystemMessage conversion."""
        lc_msg = SystemMessage(content="You are helpful.")
        oc_msg = langchain_to_forge(lc_msg)

        assert oc_msg.role == MessageRole.SYSTEM
        assert oc_msg.content == "You are helpful."

    def test_convert_human_message(self) -> None:
        """Test HumanMessage conversion."""
        lc_msg = HumanMessage(content="Hello!")
        oc_msg = langchain_to_forge(lc_msg)

        assert oc_msg.role == MessageRole.USER
        assert oc_msg.content == "Hello!"

    def test_convert_ai_message(self) -> None:
        """Test AIMessage conversion."""
        lc_msg = AIMessage(content="Hi there!")
        oc_msg = langchain_to_forge(lc_msg)

        assert oc_msg.role == MessageRole.ASSISTANT
        assert oc_msg.content == "Hi there!"

    def test_convert_ai_message_with_tool_calls(self) -> None:
        """Test AIMessage with tool_calls conversion."""
        lc_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_123",
                    "name": "read_file",
                    "args": {"path": "/tmp/test"},
                }
            ],
        )
        oc_msg = langchain_to_forge(lc_msg)

        assert oc_msg.role == MessageRole.ASSISTANT
        assert isinstance(oc_msg.tool_calls, list)
        assert len(oc_msg.tool_calls) == 1
        assert oc_msg.tool_calls[0].id == "call_123"
        assert oc_msg.tool_calls[0].function["name"] == "read_file"
        # Arguments should be JSON string
        args = json.loads(oc_msg.tool_calls[0].function["arguments"])
        assert args["path"] == "/tmp/test"

    def test_convert_tool_message(self) -> None:
        """Test ToolMessage conversion."""
        lc_msg = ToolMessage(content="file contents here", tool_call_id="call_123")
        oc_msg = langchain_to_forge(lc_msg)

        assert oc_msg.role == MessageRole.TOOL
        assert oc_msg.content == "file contents here"
        assert oc_msg.tool_call_id == "call_123"

    def test_convert_ai_message_empty_content(self) -> None:
        """Test AIMessage with empty content."""
        lc_msg = AIMessage(content="")
        oc_msg = langchain_to_forge(lc_msg)

        assert oc_msg.role == MessageRole.ASSISTANT
        assert oc_msg.content is None

    def test_convert_unsupported_message_type(self) -> None:
        """Test that unsupported message types raise ValueError."""

        class CustomMessage(BaseMessage):
            type: str = "custom"

        msg = CustomMessage(content="test")
        with pytest.raises(ValueError, match="Unsupported message type"):
            langchain_to_forge(msg)


class TestForgeToLangchain:
    """Tests for forge_to_langchain conversion."""

    def test_convert_system_message(self) -> None:
        """Test SYSTEM role conversion."""
        oc_msg = Message.system("Be helpful")
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, SystemMessage)
        assert lc_msg.content == "Be helpful"

    def test_convert_user_message(self) -> None:
        """Test USER role conversion."""
        oc_msg = Message.user("Hello")
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, HumanMessage)
        assert lc_msg.content == "Hello"

    def test_convert_assistant_message(self) -> None:
        """Test ASSISTANT role conversion."""
        oc_msg = Message.assistant("Hi!")
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, AIMessage)
        assert lc_msg.content == "Hi!"

    def test_convert_assistant_message_with_tool_calls(self) -> None:
        """Test ASSISTANT role with tool_calls conversion."""
        oc_msg = Message.assistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="call_456",
                    type="function",
                    function={
                        "name": "write_file",
                        "arguments": json.dumps({"path": "/tmp/out", "content": "hi"}),
                    },
                )
            ],
        )
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, AIMessage)
        assert len(lc_msg.tool_calls) == 1
        assert lc_msg.tool_calls[0]["id"] == "call_456"
        assert lc_msg.tool_calls[0]["name"] == "write_file"
        assert lc_msg.tool_calls[0]["args"]["path"] == "/tmp/out"

    def test_convert_tool_message(self) -> None:
        """Test TOOL role conversion."""
        oc_msg = Message.tool_result("call_789", "result data")
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, ToolMessage)
        assert lc_msg.content == "result data"
        assert lc_msg.tool_call_id == "call_789"

    def test_convert_assistant_with_invalid_json_args(self) -> None:
        """Test that invalid JSON arguments are handled gracefully."""
        oc_msg = Message.assistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="call_bad",
                    type="function",
                    function={
                        "name": "some_tool",
                        "arguments": "not valid json",
                    },
                )
            ],
        )
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, AIMessage)
        assert len(lc_msg.tool_calls) == 1
        # Should default to empty dict for invalid JSON
        assert lc_msg.tool_calls[0]["args"] == {}

    def test_convert_empty_content(self) -> None:
        """Test that None content becomes empty string."""
        oc_msg = Message(role=MessageRole.ASSISTANT, content=None)
        lc_msg = forge_to_langchain(oc_msg)

        assert isinstance(lc_msg, AIMessage)
        assert lc_msg.content == ""


class TestForgeToLangchainEdgeCases:
    """Edge case tests for forge_to_langchain."""

    def test_convert_list_content_to_string(self) -> None:
        """Test that list content is converted to string."""
        # Create a message with list content (simulating multimodal content)
        msg = Message(
            role=MessageRole.USER,
            content=[{"type": "text", "text": "Hello "}, {"type": "text", "text": "World"}],
        )
        result = forge_to_langchain(msg)

        assert isinstance(result, HumanMessage)
        assert result.content == "Hello World"

    def test_convert_assistant_with_dict_tool_calls(self) -> None:
        """Test converting assistant with tool calls as dicts."""
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Calling tool",
            tool_calls=[
                {"id": "call_1", "function": {"name": "test", "arguments": '{"x": 1}'}}
            ],
        )
        result = forge_to_langchain(msg)

        assert isinstance(result, AIMessage)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "test"


class TestBatchConversion:
    """Tests for batch message conversion."""

    def test_langchain_messages_to_forge(self) -> None:
        """Test batch conversion from LangChain to Code-Forge."""
        lc_messages = [
            SystemMessage(content="Be helpful"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there"),
        ]
        oc_messages = langchain_messages_to_forge(lc_messages)

        assert len(oc_messages) == 3
        assert oc_messages[0].role == MessageRole.SYSTEM
        assert oc_messages[1].role == MessageRole.USER
        assert oc_messages[2].role == MessageRole.ASSISTANT

    def test_forge_messages_to_langchain(self) -> None:
        """Test batch conversion from Code-Forge to LangChain."""
        oc_messages = [
            Message.system("Be helpful"),
            Message.user("Hello"),
            Message.assistant("Hi there"),
        ]
        lc_messages = forge_messages_to_langchain(oc_messages)

        assert len(lc_messages) == 3
        assert isinstance(lc_messages[0], SystemMessage)
        assert isinstance(lc_messages[1], HumanMessage)
        assert isinstance(lc_messages[2], AIMessage)

    def test_empty_list_conversion(self) -> None:
        """Test that empty lists convert to empty lists."""
        assert langchain_messages_to_forge([]) == []
        assert forge_messages_to_langchain([]) == []

    def test_roundtrip_conversion(self) -> None:
        """Test that roundtrip conversion preserves data."""
        original = [
            Message.system("Be helpful"),
            Message.user("Hello"),
            Message.assistant("Hi!"),
        ]

        # Code-Forge -> LangChain -> Code-Forge
        lc_msgs = forge_messages_to_langchain(original)
        roundtrip = langchain_messages_to_forge(lc_msgs)

        assert len(roundtrip) == len(original)
        for orig, rt in zip(original, roundtrip):
            assert orig.role == rt.role
            assert orig.content == rt.content
