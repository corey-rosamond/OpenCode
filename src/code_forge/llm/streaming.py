"""Streaming response utilities."""

from __future__ import annotations

from dataclasses import dataclass, field

from code_forge.llm.models import (
    Message,
    MessageRole,
    StreamChunk,
    TokenUsage,
    ToolCall,
)


@dataclass
class StreamCollector:
    """
    Collects streaming chunks into a complete response.

    Usage:
        collector = StreamCollector()
        async for chunk in client.stream(request):
            collector.add_chunk(chunk)
            print(collector.content, end="", flush=True)
        message = collector.get_message()
    """

    content: str = ""
    tool_calls: list[dict[str, str | dict[str, str]]] = field(default_factory=list)
    usage: TokenUsage | None = None
    model: str = ""
    finish_reason: str | None = None
    _tool_call_index: int = -1

    def add_chunk(self, chunk: StreamChunk) -> str | None:
        """
        Add a chunk and return new content if any.

        Args:
            chunk: Streaming chunk

        Returns:
            New content text, or None if no new content

        Note:
            Validates chunk structure before processing. Malformed chunks
            are silently skipped to allow stream processing to continue.
        """
        # Validate chunk has required attributes
        if not hasattr(chunk, "model"):
            return None

        self.model = chunk.model or self.model

        if hasattr(chunk, "finish_reason") and chunk.finish_reason:
            self.finish_reason = chunk.finish_reason

        if hasattr(chunk, "usage") and chunk.usage:
            self.usage = chunk.usage

        # Validate delta exists
        if not hasattr(chunk, "delta") or chunk.delta is None:
            return None

        delta = chunk.delta
        new_content = None

        # Handle content (validate delta has content attribute)
        if hasattr(delta, "content") and delta.content:
            self.content += delta.content
            new_content = delta.content

        # Handle tool calls (validate delta has tool_calls attribute)
        if not hasattr(delta, "tool_calls") or not delta.tool_calls:
            return new_content

        if delta.tool_calls:
            for tc in delta.tool_calls:
                index = tc.get("index", 0)

                if index > self._tool_call_index:
                    # New tool call
                    self._tool_call_index = index
                    self.tool_calls.append(
                        {
                            "id": tc.get("id", ""),
                            "type": tc.get("type", "function"),
                            "function": {
                                "name": tc.get("function", {}).get("name", ""),
                                "arguments": tc.get("function", {}).get("arguments", ""),
                            },
                        }
                    )
                elif self.tool_calls:
                    # Continue existing tool call
                    current = self.tool_calls[-1]
                    func = tc.get("function", {})
                    if "arguments" in func:
                        current_func = current.get("function", {})
                        if isinstance(current_func, dict):
                            current_func["arguments"] = (
                                current_func.get("arguments", "") + func["arguments"]
                            )

        return new_content

    def get_message(self) -> Message:
        """
        Get the complete message.

        Returns:
            Complete Message object
        """
        tool_calls = None
        if self.tool_calls:
            tool_calls = [
                ToolCall(
                    id=str(tc.get("id", "")),
                    type=str(tc.get("type", "function")),
                    function=tc.get("function", {}),  # type: ignore[arg-type]
                )
                for tc in self.tool_calls
            ]

        return Message(
            role=MessageRole.ASSISTANT,
            content=self.content if self.content else None,
            tool_calls=tool_calls,
        )

    @property
    def is_complete(self) -> bool:
        """Check if streaming is complete."""
        return self.finish_reason is not None
