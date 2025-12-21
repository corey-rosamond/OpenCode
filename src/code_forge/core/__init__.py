"""Core package containing interfaces, types, and errors."""

from code_forge.core.errors import (
    ConfigError,
    CodeForgeError,
    PermissionDeniedError,
    ProviderError,
    SessionError,
    ToolError,
)
from code_forge.core.interfaces import (
    IConfigLoader,
    IModelProvider,
    ISessionRepository,
    ITool,
)
from code_forge.core.logging import get_logger, setup_logging
from code_forge.core.types import (
    AgentId,
    CompletionRequest,
    CompletionResponse,
    Message,
    ModelId,
    ProjectId,
    Session,
    SessionId,
    SessionSummary,
    ToolName,
)

__all__ = [
    "AgentId",
    "CompletionRequest",
    "CompletionResponse",
    "ConfigError",
    "IConfigLoader",
    "IModelProvider",
    "ISessionRepository",
    "ITool",
    "Message",
    "ModelId",
    "CodeForgeError",
    "PermissionDeniedError",
    "ProjectId",
    "ProviderError",
    "Session",
    "SessionError",
    "SessionId",
    "SessionSummary",
    "ToolError",
    "ToolName",
    "get_logger",
    "setup_logging",
]
