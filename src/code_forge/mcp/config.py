"""MCP server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    transport: str  # "stdio" or "http"
    command: str | None = None  # for stdio
    args: list[str] | None = None
    url: str | None = None  # for http
    headers: dict[str, str] | None = None
    env: dict[str, str] | None = None
    cwd: str | None = None
    enabled: bool = True
    auto_connect: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.transport not in ("stdio", "http"):
            raise ValueError(
                f"Server {self.name}: transport must be 'stdio' or 'http', "
                f"got '{self.transport}'"
            )
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"Server {self.name}: stdio transport requires command")
        if self.transport == "http" and not self.url:
            raise ValueError(f"Server {self.name}: http transport requires url")

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> MCPServerConfig:
        """Create from dictionary.

        Args:
            name: Server name.
            data: Configuration data.

        Returns:
            Server configuration.
        """
        return cls(
            name=name,
            transport=data.get("transport", "stdio"),
            command=data.get("command"),
            args=data.get("args"),
            url=data.get("url"),
            headers=data.get("headers"),
            env=data.get("env"),
            cwd=data.get("cwd"),
            enabled=data.get("enabled", True),
            auto_connect=data.get("auto_connect", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Configuration as dictionary.
        """
        result: dict[str, Any] = {
            "transport": self.transport,
            "enabled": self.enabled,
            "auto_connect": self.auto_connect,
        }
        if self.command is not None:
            result["command"] = self.command
        if self.args is not None:
            result["args"] = self.args
        if self.url is not None:
            result["url"] = self.url
        if self.headers is not None:
            result["headers"] = self.headers
        if self.env is not None:
            result["env"] = self.env
        if self.cwd is not None:
            result["cwd"] = self.cwd
        return result


@dataclass
class MCPSettings:
    """Global MCP settings."""

    auto_connect: bool = True
    reconnect_attempts: int = 3
    reconnect_delay: int = 5
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPSettings:
        """Create from dictionary.

        Args:
            data: Settings data.

        Returns:
            Settings object.
        """
        return cls(
            auto_connect=data.get("auto_connect", True),
            reconnect_attempts=data.get("reconnect_attempts", 3),
            reconnect_delay=data.get("reconnect_delay", 5),
            timeout=data.get("timeout", 30),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Settings as dictionary.
        """
        return {
            "auto_connect": self.auto_connect,
            "reconnect_attempts": self.reconnect_attempts,
            "reconnect_delay": self.reconnect_delay,
            "timeout": self.timeout,
        }


@dataclass
class MCPConfig:
    """Complete MCP configuration."""

    servers: dict[str, MCPServerConfig] = field(default_factory=dict)
    settings: MCPSettings = field(default_factory=MCPSettings)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPConfig:
        """Create from dictionary.

        Args:
            data: Configuration data.

        Returns:
            Configuration object.
        """
        servers: dict[str, MCPServerConfig] = {}
        for name, server_data in data.get("servers", {}).items():
            servers[name] = MCPServerConfig.from_dict(name, server_data)

        settings_data = data.get("settings", {})
        settings = MCPSettings.from_dict(settings_data)

        return cls(servers=servers, settings=settings)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Configuration as dictionary.
        """
        return {
            "servers": {name: cfg.to_dict() for name, cfg in self.servers.items()},
            "settings": self.settings.to_dict(),
        }

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


class MCPConfigLoader:
    """Loads MCP configuration from files."""

    DEFAULT_USER_PATH = Path.home() / ".forge" / "mcp.yaml"
    DEFAULT_PROJECT_PATH = Path(".forge") / "mcp.yaml"

    def __init__(
        self,
        user_path: Path | None = None,
        project_path: Path | None = None,
    ) -> None:
        """Initialize loader.

        Args:
            user_path: Path to user config (default: ~/.forge/mcp.yaml).
            project_path: Path to project config (default: .forge/mcp.yaml).
        """
        self.user_path = user_path or self.DEFAULT_USER_PATH
        self.project_path = project_path or self.DEFAULT_PROJECT_PATH

    def load(self) -> MCPConfig:
        """Load and merge all configurations.

        Returns:
            Merged configuration.
        """
        configs: list[MCPConfig] = []

        # Load user config
        if self.user_path.exists():
            try:
                configs.append(self.load_from_file(self.user_path))
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to load user MCP config: {e}"
                )

        # Load project config (overrides user)
        if self.project_path.exists():
            try:
                configs.append(self.load_from_file(self.project_path))
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to load project MCP config: {e}"
                )

        if not configs:
            return MCPConfig()

        return self.merge_configs(*configs)

    def load_from_file(self, path: Path) -> MCPConfig:
        """Load configuration from a file.

        Args:
            path: Path to config file.

        Returns:
            Loaded configuration.

        Raises:
            FileNotFoundError: If file doesn't exist.
            yaml.YAMLError: If YAML is invalid.
            ValueError: If configuration is invalid.
        """
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Expand environment variables in values
        data = self._expand_env_vars(data)

        return MCPConfig.from_dict(data)

    def merge_configs(self, *configs: MCPConfig) -> MCPConfig:
        """Merge multiple configurations.

        Later configs override earlier ones. Settings are merged field by field.

        Args:
            *configs: Configurations to merge (in order of precedence).

        Returns:
            Merged configuration.
        """
        merged_servers: dict[str, MCPServerConfig] = {}
        merged_settings = MCPSettings()

        for config in configs:
            # Merge servers (later overrides)
            merged_servers.update(config.servers)

            # Merge settings field by field
            settings = config.settings
            if settings.auto_connect != MCPSettings().auto_connect:
                merged_settings.auto_connect = settings.auto_connect
            if settings.reconnect_attempts != MCPSettings().reconnect_attempts:
                merged_settings.reconnect_attempts = settings.reconnect_attempts
            if settings.reconnect_delay != MCPSettings().reconnect_delay:
                merged_settings.reconnect_delay = settings.reconnect_delay
            if settings.timeout != MCPSettings().timeout:
                merged_settings.timeout = settings.timeout

        return MCPConfig(servers=merged_servers, settings=merged_settings)

    def _expand_env_vars(self, data: Any) -> Any:
        """Recursively expand environment variables.

        Supports ${VAR} and $VAR syntax.

        Args:
            data: Data to expand.

        Returns:
            Data with environment variables expanded.
        """
        if isinstance(data, str):
            return os.path.expandvars(data)
        elif isinstance(data, dict):
            return {k: self._expand_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._expand_env_vars(item) for item in data]
        return data

    # Allowed directories for saving config
    ALLOWED_SAVE_DIRS = [
        Path.home() / ".forge",
        Path(".forge"),
    ]

    def save_to_file(self, config: MCPConfig, path: Path) -> None:
        """Save configuration to a file.

        Security: Only allows saving to expected config directories
        (~/.forge or .forge) to prevent path traversal attacks.

        Args:
            config: Configuration to save.
            path: Path to save to.

        Raises:
            ValueError: If path is outside allowed directories.
        """
        # Resolve the path to handle .. and symlinks
        resolved = path.resolve()

        # Check if path is within allowed directories
        allowed = False
        for allowed_dir in self.ALLOWED_SAVE_DIRS:
            try:
                allowed_resolved = allowed_dir.resolve()
                # Check if resolved path starts with allowed directory
                resolved.relative_to(allowed_resolved)
                allowed = True
                break
            except ValueError:
                # relative_to raises ValueError if path is not relative
                continue

        if not allowed:
            allowed_dirs_str = ", ".join(str(d) for d in self.ALLOWED_SAVE_DIRS)
            raise ValueError(
                f"Cannot save to {path}: path must be within {allowed_dirs_str}"
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.safe_dump(config.to_dict(), f, default_flow_style=False)
