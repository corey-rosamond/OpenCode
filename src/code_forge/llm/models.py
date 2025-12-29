"""Data models for LLM interactions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Role of a message in conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ContentPart:
    """Part of a multimodal message."""

    type: str  # "text" or "image_url"
    text: str | None = None
    image_url: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API format."""
        if self.type == "text":
            return {"type": "text", "text": self.text}
        else:
            return {"type": "image_url", "image_url": self.image_url}


@dataclass
class ToolCall:
    """A tool call from the assistant."""

    id: str
    type: str  # "function"
    function: dict[str, Any]  # {"name": str, "arguments": str}

    def to_dict(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Create from API response."""
        return cls(
            id=data["id"],
            type=data["type"],
            function=data["function"],
        )


@dataclass
class Message:
    """A message in the conversation."""

    role: MessageRole
    content: str | list[ContentPart] | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API format."""
        msg: dict[str, Any] = {"role": self.role.value}

        if isinstance(self.content, str):
            msg["content"] = self.content
        elif isinstance(self.content, list):
            msg["content"] = [p.to_dict() for p in self.content]
        elif self.content is None and self.tool_calls:
            msg["content"] = None
        elif self.content is None:
            msg["content"] = None
        else:
            # Log warning for unexpected content types to avoid silent bugs
            logger.warning(
                "Unexpected content type %s in Message.to_dict(), "
                "passing through as-is. Expected str, list[ContentPart], or None.",
                type(self.content).__name__,
            )
            msg["content"] = self.content

        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            msg["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]

        return msg

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create from API response."""
        tool_calls = None
        if data.get("tool_calls"):
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]

        return cls(
            role=MessageRole(data["role"]),
            content=data.get("content"),
            name=data.get("name"),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=tool_calls,
        )

    @classmethod
    def system(cls, content: str) -> Message:
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str | list[ContentPart]) -> Message:
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(
        cls,
        content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
    ) -> Message:
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool_result(cls, tool_call_id: str, content: str) -> Message:
        """Create a tool result message."""
        return cls(
            role=MessageRole.TOOL,
            content=content,
            tool_call_id=tool_call_id,
        )


@dataclass
class ToolDefinition:
    """Definition of a tool for function calling."""

    name: str
    description: str
    parameters: dict[str, Any]
    type: str = "function"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "type": self.type,
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class CompletionRequest:
    """Request for chat completion."""

    model: str
    messages: list[Message]
    tools: list[ToolDefinition | dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    temperature: float = 1.0
    max_tokens: int | None = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    stream: bool = False
    # OpenRouter-specific
    transforms: list[str] | None = None
    route: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API payload."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "temperature": self.temperature,
            "stream": self.stream,
        }

        if self.tools:
            payload["tools"] = [
                t.to_dict() if hasattr(t, "to_dict") else t for t in self.tools
            ]
        if self.tool_choice:
            payload["tool_choice"] = self.tool_choice
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if self.top_p != 1.0:
            payload["top_p"] = self.top_p
        if self.frequency_penalty != 0.0:
            payload["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0.0:
            payload["presence_penalty"] = self.presence_penalty
        if self.stop:
            payload["stop"] = self.stop
        if self.transforms:
            payload["transforms"] = self.transforms
        if self.route:
            payload["route"] = self.route

        return payload


@dataclass
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenUsage:
        """Create from API response."""
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class CompletionChoice:
    """A completion choice from the response."""

    index: int
    message: Message
    finish_reason: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompletionChoice:
        """Create from API response."""
        return cls(
            index=data["index"],
            message=Message.from_dict(data["message"]),
            finish_reason=data.get("finish_reason"),
        )


@dataclass
class CompletionResponse:
    """Response from chat completion."""

    id: str
    model: str
    choices: list[CompletionChoice]
    usage: TokenUsage
    created: int
    provider: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompletionResponse:
        """Create from API response."""
        return cls(
            id=data["id"],
            model=data["model"],
            choices=[CompletionChoice.from_dict(c) for c in data["choices"]],
            usage=TokenUsage.from_dict(data.get("usage", {})),
            created=data["created"],
            provider=data.get("provider"),
        )


@dataclass
class StreamDelta:
    """Delta in a streaming chunk."""

    role: str | None = None
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    reasoning_content: str | None = None  # DeepSeek/Kimi/OpenRouter reasoning tokens

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamDelta:
        """Create from API response.

        Handles multiple reasoning token formats:
        - reasoning_content: DeepSeek/Kimi native format
        - reasoning_details: OpenRouter unified format (array of objects)
        - thinking: Alternative format used by some models
        """
        # Extract reasoning content from various formats
        reasoning = data.get("reasoning_content")

        # OpenRouter's reasoning_details format (array of detail objects)
        if not reasoning and data.get("reasoning_details"):
            details = data["reasoning_details"]
            if isinstance(details, list):
                # Extract text from reasoning detail objects
                reasoning = "".join(
                    d.get("content", "") if isinstance(d, dict) else str(d)
                    for d in details
                )

        # Alternative "thinking" format
        if not reasoning:
            reasoning = data.get("thinking")

        return cls(
            role=data.get("role"),
            content=data.get("content"),
            tool_calls=data.get("tool_calls"),
            reasoning_content=reasoning,
        )


@dataclass
class StreamChunk:
    """A chunk from streaming response."""

    id: str
    model: str
    delta: StreamDelta
    index: int
    finish_reason: str | None
    usage: TokenUsage | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamChunk:
        """Create from API response."""
        choice = data["choices"][0] if data.get("choices") else {}
        usage = None
        if data.get("usage"):
            usage = TokenUsage.from_dict(data["usage"])

        return cls(
            id=data["id"],
            model=data["model"],
            delta=StreamDelta.from_dict(choice.get("delta", {})),
            index=choice.get("index", 0),
            finish_reason=choice.get("finish_reason"),
            usage=usage,
        )
