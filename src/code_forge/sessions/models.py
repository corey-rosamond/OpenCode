"""Session data models."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ToolInvocation:
    """Record of a tool invocation within a session.

    Tracks tool execution history including arguments, results,
    timing, and success/failure status.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration: float = 0.0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolInvocation:
        """Deserialize from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(UTC)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            tool_name=data.get("tool_name", ""),
            arguments=data.get("arguments", {}),
            result=data.get("result"),
            timestamp=timestamp,
            duration=data.get("duration", 0.0),
            success=data.get("success", True),
            error=data.get("error"),
        )


@dataclass
class SessionMessage:
    """A message within a session.

    Wraps the core Message type with session-specific metadata.
    Provides conversion to/from LangChain and OpenAI message formats.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # "system", "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        data: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.tool_calls is not None:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            data["name"] = self.name
        return data

    def to_llm_message(self) -> dict[str, Any]:
        """Convert to LLM-compatible message format (OpenAI/Anthropic style).

        Returns:
            Dictionary suitable for LLM API calls and ContextManager.
            Does NOT include session-specific fields like id/timestamp.
        """
        msg: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_calls is not None:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            msg["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            msg["name"] = self.name
        return msg

    @classmethod
    def from_llm_message(cls, msg: dict[str, Any]) -> SessionMessage:
        """Create SessionMessage from an LLM message dict.

        Args:
            msg: Message dict with role, content, and optional tool fields.

        Returns:
            SessionMessage instance with new id and timestamp.
        """
        return cls(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            tool_calls=msg.get("tool_calls"),
            tool_call_id=msg.get("tool_call_id"),
            name=msg.get("name"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionMessage:
        """Deserialize from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(UTC)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            timestamp=timestamp,
        )


@dataclass
class Session:
    """A conversation session.

    Contains all messages, tool invocations, and metadata for a
    single conversation session. Sessions can be persisted to disk
    and resumed later.

    Attributes:
        id: Unique session identifier (UUID).
        title: Human-readable session title.
        created_at: When the session was created.
        updated_at: When the session was last modified.
        working_dir: Working directory for the session.
        model: LLM model used for this session.
        messages: List of conversation messages.
        tool_history: List of tool invocations.
        total_prompt_tokens: Cumulative prompt tokens used.
        total_completion_tokens: Cumulative completion tokens used.
        tags: Tags for organization.
        metadata: Additional custom key-value data.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    working_dir: str = ""
    model: str = ""

    messages: list[SessionMessage] = field(default_factory=list)
    tool_history: list[ToolInvocation] = field(default_factory=list)

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: SessionMessage) -> None:
        """Add a message to the session.

        Args:
            message: The message to add.
        """
        self.messages.append(message)
        self._mark_updated()

    # Valid message roles
    VALID_ROLES = frozenset({"system", "user", "assistant", "tool"})

    def add_message_from_dict(
        self,
        role: str,
        content: str,
        **kwargs: Any,
    ) -> SessionMessage:
        """Create and add a message from components.

        Args:
            role: Message role (must be: system, user, assistant, or tool).
            content: Message content.
            **kwargs: Additional message fields.

        Returns:
            The created SessionMessage.

        Raises:
            ValueError: If role is not a valid message role.
        """
        # Validate role
        if role not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid message role: {role!r}. "
                f"Must be one of: {', '.join(sorted(self.VALID_ROLES))}"
            )

        message = SessionMessage(
            role=role,
            content=content,
            **kwargs,
        )
        self.add_message(message)
        return message

    def add_tool_invocation(self, invocation: ToolInvocation) -> None:
        """Add a tool invocation to history.

        Args:
            invocation: The tool invocation record.
        """
        self.tool_history.append(invocation)
        self._mark_updated()

    def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None = None,
        duration: float = 0.0,
        success: bool = True,
        error: str | None = None,
    ) -> ToolInvocation:
        """Record a tool invocation from components.

        Args:
            tool_name: Name of the tool.
            arguments: Arguments passed to the tool.
            result: Tool execution result.
            duration: Execution duration in seconds.
            success: Whether execution succeeded.
            error: Error message if failed.

        Returns:
            The created ToolInvocation.
        """
        invocation = ToolInvocation(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            duration=duration,
            success=success,
            error=error,
        )
        self.add_tool_invocation(invocation)
        return invocation

    def update_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Update token usage statistics.

        Args:
            prompt_tokens: Number of prompt tokens used.
            completion_tokens: Number of completion tokens used.
        """
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self._mark_updated()

    @property
    def total_tokens(self) -> int:
        """Total tokens used in this session."""
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def message_count(self) -> int:
        """Number of messages in the session."""
        return len(self.messages)

    def _mark_updated(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to dictionary for JSON storage.

        Returns:
            Dictionary representation of the session.
        """
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "working_dir": self.working_dir,
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "tool_history": [t.to_dict() for t in self.tool_history],
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize session to JSON string.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserialize session from dictionary.

        Args:
            data: Dictionary containing session data.

        Returns:
            Session instance.
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(UTC)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now(UTC)

        messages = [
            SessionMessage.from_dict(m)
            for m in data.get("messages", [])
        ]

        tool_history = [
            ToolInvocation.from_dict(t)
            for t in data.get("tool_history", [])
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            created_at=created_at,
            updated_at=updated_at,
            working_dir=data.get("working_dir", ""),
            model=data.get("model", ""),
            messages=messages,
            tool_history=tool_history,
            total_prompt_tokens=data.get("total_prompt_tokens", 0),
            total_completion_tokens=data.get("total_completion_tokens", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> Session:
        """Deserialize session from JSON string.

        Args:
            json_str: JSON string containing session data.

        Returns:
            Session instance.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
