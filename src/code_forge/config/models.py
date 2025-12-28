"""Configuration models for Code-Forge.

This module defines Pydantic models for all configuration sections,
including validation, defaults, and security considerations.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class TransportType(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


class RoutingVariant(str, Enum):
    """OpenRouter routing variants."""

    NITRO = "nitro"
    FLOOR = "floor"
    EXACTO = "exacto"
    THINKING = "thinking"
    ONLINE = "online"


class HookType(str, Enum):
    """Hook execution type."""

    COMMAND = "command"
    PROMPT = "prompt"


class ModelConfig(BaseModel):
    """Model-related configuration.

    Attributes:
        default: Default model to use.
        fallback: List of fallback models if primary fails.
        max_tokens: Maximum tokens for completion (1-200000).
        temperature: Sampling temperature (0.0-2.0).
        routing_variant: OpenRouter routing variant.
    """

    model_config = ConfigDict(validate_assignment=True)

    default: str = "anthropic/claude-3.5-sonnet"
    fallback: list[str] = Field(default_factory=lambda: ["openai/gpt-4o", "google/gemini-pro"])
    max_tokens: int = Field(default=8192, ge=1, le=200000)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    routing_variant: RoutingVariant | None = None

    @field_validator("default")
    @classmethod
    def validate_default_model(cls, v: str) -> str:
        """Validate that default model name is non-empty."""
        if not v or not v.strip():
            raise ValueError("Model name must be a non-empty string")
        return v.strip()


class PermissionConfig(BaseModel):
    """Permission system configuration.

    Attributes:
        allow: Patterns for auto-allow (e.g., "Read(*)").
        ask: Patterns requiring user confirmation.
        deny: Patterns to block entirely.
    """

    model_config = ConfigDict(validate_assignment=True)

    allow: list[str] = Field(default_factory=list)
    ask: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class HookConfig(BaseModel):
    """Single hook configuration.

    Attributes:
        type: Type of hook (command or prompt).
        matcher: Tool pattern to match (e.g., "Bash(*)").
        command: Shell command to execute (for command hooks).
        prompt: Prompt to inject (for prompt hooks).
        timeout: Execution timeout in seconds (1-300).
    """

    model_config = ConfigDict(validate_assignment=True)

    type: HookType
    matcher: str | None = None
    command: str | None = None
    prompt: str | None = None
    timeout: int = Field(default=60, ge=1, le=300)

    @field_validator("command", "prompt")
    @classmethod
    def validate_hook_content(cls, v: str | None) -> str | None:
        """Strip whitespace from hook content."""
        if v is not None:
            return v.strip() if v.strip() else None
        return v


class HooksConfig(BaseModel):
    """All hooks configuration.

    Attributes:
        pre_tool_use: Hooks executed before tool use.
        post_tool_use: Hooks executed after tool use.
        user_prompt_submit: Hooks executed on user prompt submit.
        stop: Hooks executed on agent stop.
        subagent_stop: Hooks executed on subagent stop.
        notification: Hooks for notifications.
    """

    model_config = ConfigDict(validate_assignment=True)

    pre_tool_use: list[HookConfig] = Field(default_factory=list)
    post_tool_use: list[HookConfig] = Field(default_factory=list)
    user_prompt_submit: list[HookConfig] = Field(default_factory=list)
    stop: list[HookConfig] = Field(default_factory=list)
    subagent_stop: list[HookConfig] = Field(default_factory=list)
    notification: list[HookConfig] = Field(default_factory=list)


class MCPServerConfig(BaseModel):
    """MCP server configuration.

    Attributes:
        name: Server identifier (set when loading from config).
        transport: Transport type (stdio or streamable-http).
        command: Command to execute (for stdio transport).
        args: Command arguments.
        url: Server URL (for HTTP transport).
        headers: HTTP headers (for HTTP transport).
        env: Environment variables for the server.
        cwd: Working directory for the server process.
        enabled: Whether the server is enabled.
        auto_connect: Whether to auto-connect on startup.
        oauth_client_id: OAuth 2.1 client ID.
    """

    model_config = ConfigDict(validate_assignment=True)

    name: str = ""
    transport: TransportType = TransportType.STDIO
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    enabled: bool = True
    auto_connect: bool = True
    oauth_client_id: str | None = None

    @field_validator("command")
    @classmethod
    def validate_stdio_command(cls, v: str | None) -> str | None:
        """Validate and normalize command."""
        if v is not None:
            return v.strip() if v.strip() else None
        return v


class MCPSettings(BaseModel):
    """Global MCP settings.

    Attributes:
        auto_connect: Whether to auto-connect enabled servers.
        reconnect_attempts: Number of reconnection attempts.
        reconnect_delay: Delay between reconnection attempts in seconds.
        timeout: Default operation timeout in seconds.
    """

    model_config = ConfigDict(validate_assignment=True)

    auto_connect: bool = True
    reconnect_attempts: int = Field(default=3, ge=0, le=10)
    reconnect_delay: int = Field(default=5, ge=1, le=60)
    timeout: int = Field(default=30, ge=1, le=300)


class MCPConfig(BaseModel):
    """Complete MCP configuration.

    Attributes:
        servers: Dictionary of server configurations by name.
        settings: Global MCP settings.
    """

    model_config = ConfigDict(validate_assignment=True)

    servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    settings: MCPSettings = Field(default_factory=MCPSettings)

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        """Get list of enabled servers.

        Returns:
            List of enabled server configs.
        """
        return [s for s in self.servers.values() if s.enabled]

    def get_auto_connect_servers(self) -> list[MCPServerConfig]:
        """Get list of servers to auto-connect.

        Returns:
            List of server configs with auto_connect=True.
        """
        return [
            s
            for s in self.servers.values()
            if s.enabled and s.auto_connect and self.settings.auto_connect
        ]


class DisplayConfig(BaseModel):
    """Display/UI configuration.

    Attributes:
        theme: Color theme ("dark" or "light").
        show_tokens: Show token usage.
        show_cost: Show API cost.
        streaming: Enable streaming responses.
        vim_mode: Enable vim keybindings.
        status_line: Show status line.
        color: Enable colored output (can be overridden by --no-color).
        quiet: Reduce output verbosity (can be overridden by -q/--quiet).
        json_output: Output responses in JSON format (can be overridden by --json).
    """

    model_config = ConfigDict(validate_assignment=True)

    theme: str = "dark"
    show_tokens: bool = True
    show_cost: bool = True
    streaming: bool = True
    vim_mode: bool = False
    status_line: bool = True
    color: bool = True
    quiet: bool = False
    json_output: bool = False

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme is a known value."""
        v = v.strip().lower()
        if v not in ("dark", "light"):
            # Allow custom themes, just normalize
            pass
        return v


class SessionConfig(BaseModel):
    """Session management configuration.

    Attributes:
        auto_save: Automatically save sessions.
        save_interval: Interval between saves in seconds (10-3600).
        max_history: Maximum messages in history (1-10000).
        session_dir: Custom session directory.
        compress_after: Messages before compression (10+).
        token_cache_size: Maximum entries in token counter cache (100-10000).
    """

    model_config = ConfigDict(validate_assignment=True)

    auto_save: bool = True
    save_interval: int = Field(default=60, ge=10, le=3600)
    max_history: int = Field(default=100, ge=1, le=10000)
    session_dir: Path | None = None
    compress_after: int = Field(default=50, ge=10)
    token_cache_size: int = Field(default=1000, ge=100, le=10000)


class CodeForgeConfig(BaseModel):
    """Root configuration model.

    This is the main configuration class that contains all configuration
    sections. It uses Pydantic for validation and SecretStr for API keys
    to prevent accidental logging.

    Attributes:
        model: Model-related configuration.
        permissions: Permission system configuration.
        hooks: Hook configurations.
        mcp_servers: MCP server definitions.
        display: Display/UI preferences.
        session: Session management settings.
        api_key: OpenRouter API key (sensitive).
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",  # Ignore unknown fields
    )

    model: ModelConfig = Field(default_factory=ModelConfig)
    permissions: PermissionConfig = Field(default_factory=PermissionConfig)
    hooks: HooksConfig = Field(default_factory=HooksConfig)
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)

    # Sensitive - use SecretStr to prevent logging
    api_key: SecretStr | None = None

    def get_api_key(self) -> str | None:
        """Get the API key value safely.

        Returns:
            The API key string or None if not set.
        """
        if self.api_key is not None:
            return self.api_key.get_secret_value()
        return None
