"""Message conversion between LangChain and Code-Forge formats."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

if TYPE_CHECKING:
    from code_forge.llm.models import Message


def langchain_to_forge(message: BaseMessage) -> Message:
    """
    Convert a LangChain message to an Code-Forge message.

    Args:
        message: LangChain message to convert

    Returns:
        Equivalent Code-Forge Message

    Raises:
        ValueError: If message type is not supported
    """
    from code_forge.llm.models import Message, ToolCall

    if isinstance(message, SystemMessage):
        return Message.system(str(message.content))

    elif isinstance(message, HumanMessage):
        return Message.user(str(message.content))

    elif isinstance(message, AIMessage):
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    # Generate UUID if ID is None/empty to ensure tool result matching works
                    id=tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                    type="function",
                    function={
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"])
                        if isinstance(tc["args"], dict)
                        else tc["args"],
                    },
                )
                for tc in message.tool_calls
            ]
        content = str(message.content) if message.content else None
        return Message.assistant(content=content, tool_calls=tool_calls)

    elif isinstance(message, ToolMessage):
        return Message.tool_result(
            tool_call_id=message.tool_call_id,
            content=str(message.content),
        )

    else:
        raise ValueError(f"Unsupported message type: {type(message).__name__}")


def forge_to_langchain(message: Message) -> BaseMessage:
    """
    Convert an Code-Forge message to a LangChain message.

    Args:
        message: Code-Forge message to convert

    Returns:
        Equivalent LangChain message

    Raises:
        ValueError: If message role is not supported
    """
    from code_forge.llm.models import MessageRole

    # Helper to extract string content (LangChain expects str, not list)
    def get_string_content(content: str | list[Any] | None) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        # Handle list[ContentPart] - extract text
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content)

    if message.role == MessageRole.SYSTEM:
        return SystemMessage(content=get_string_content(message.content))

    elif message.role == MessageRole.USER:
        return HumanMessage(content=get_string_content(message.content))

    elif message.role == MessageRole.ASSISTANT:
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                # Handle both ToolCall objects and dict representations
                if hasattr(tc, "function"):
                    # ToolCall object
                    func: dict[str, Any] = tc.function
                    tc_id: str = tc.id
                else:
                    # Dict representation
                    tc_dict: dict[str, Any] = tc  # type: ignore[assignment]
                    func = tc_dict.get("function", {})
                    tc_id = tc_dict.get("id", "")

                args = func.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(
                    {
                        "id": tc_id,
                        "name": func.get("name", ""),
                        "args": args,
                    }
                )
        return AIMessage(
            content=get_string_content(message.content),
            tool_calls=tool_calls if tool_calls else [],
        )

    elif message.role == MessageRole.TOOL:
        return ToolMessage(
            content=get_string_content(message.content),
            tool_call_id=message.tool_call_id or "",
        )

    else:
        raise ValueError(f"Unsupported message role: {message.role}")


def langchain_messages_to_forge(messages: list[BaseMessage]) -> list[Message]:
    """
    Convert a list of LangChain messages to Code-Forge messages.

    Args:
        messages: List of LangChain messages to convert

    Returns:
        List of equivalent Code-Forge Messages
    """
    return [langchain_to_forge(m) for m in messages]


def forge_messages_to_langchain(messages: list[Message]) -> list[BaseMessage]:
    """
    Convert a list of Code-Forge messages to LangChain messages.

    Args:
        messages: List of Code-Forge messages to convert

    Returns:
        List of equivalent LangChain messages
    """
    return [forge_to_langchain(m) for m in messages]
