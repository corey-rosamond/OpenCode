"""Core value objects and type definitions for Code-Forge."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, NewType
from uuid import uuid4

from pydantic import BaseModel, Field

# Type aliases for clarity
ToolName = NewType("ToolName", str)
ModelId = NewType("ModelId", str)


class AgentId(BaseModel):
    """Unique identifier for an agent instance."""

    value: str = Field(default_factory=lambda: str(uuid4()))

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __hash__(self) -> int:
        """Return hash for use in sets/dicts."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Check equality with another AgentId."""
        if not isinstance(other, AgentId):
            return NotImplemented
        return self.value == other.value


class SessionId(BaseModel):
    """Value object for session identification."""

    value: str

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __hash__(self) -> int:
        """Return hash for use in sets/dicts."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Check equality with another SessionId."""
        if not isinstance(other, SessionId):
            return NotImplemented
        return self.value == other.value


class ProjectId(BaseModel):
    """Identifier for a project (directory path hash)."""

    value: str
    path: str

    @classmethod
    def from_path(cls, path: str) -> ProjectId:
        """Create a ProjectId from a filesystem path.

        Args:
            path: The filesystem path to the project.

        Returns:
            A ProjectId with a hashed value and the original path.
        """
        hash_val = hashlib.sha256(path.encode()).hexdigest()[:12]
        return cls(value=hash_val, path=path)

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __hash__(self) -> int:
        """Return hash for use in sets/dicts."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Check equality with another ProjectId."""
        if not isinstance(other, ProjectId):
            return NotImplemented
        return self.value == other.value


# ToolParameter and ToolResult are defined in tools/base.py with full functionality
# Re-exported here for backwards compatibility with imports from code_forge.core
from code_forge.tools.base import ToolParameter, ToolResult  # noqa: E402


class Message(BaseModel):
    """A conversation message."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class CompletionRequest(BaseModel):
    """Request for model completion."""

    messages: list[Message]
    model: str
    max_tokens: int | None = None
    temperature: float = 1.0
    stream: bool = False
    tools: list[dict[str, Any]] | None = None


class CompletionResponse(BaseModel):
    """Response from model completion."""

    content: str
    model: str
    finish_reason: str
    usage: dict[str, int]
    tool_calls: list[dict[str, Any]] | None = None


class SessionSummary(BaseModel):
    """Summary of a session for listing."""

    id: SessionId
    project_path: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    preview: str


class Session(BaseModel):
    """Full session data."""

    id: SessionId
    project_path: str
    created_at: datetime
    last_activity: datetime
    messages: list[dict[str, Any]]
    context: dict[str, Any]
    metadata: dict[str, Any]
