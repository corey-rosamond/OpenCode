"""MCP server configuration.

This module provides the MCPConfigLoader for loading MCP configuration
from YAML files. The configuration models (MCPServerConfig, MCPSettings,
MCPConfig) are defined in code_forge.config.models for consistency with
other configuration models.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Import Pydantic models from canonical location
from code_forge.config.models import (
    MCPConfig,
    MCPServerConfig,
    MCPSettings,
    TransportType,
)

# Re-export for backward compatibility
__all__ = [
    "MCPConfig",
    "MCPConfigLoader",
    "MCPServerConfig",
    "MCPSettings",
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

        return self._parse_config(data)

    def _parse_config(self, data: dict[str, Any]) -> MCPConfig:
        """Parse configuration data into Pydantic models.

        Args:
            data: Raw configuration dictionary.

        Returns:
            Parsed MCPConfig.
        """
        servers: dict[str, MCPServerConfig] = {}
        for name, server_data in data.get("servers", {}).items():
            # Convert transport string to enum if needed
            transport = server_data.get("transport", "stdio")
            if transport == "http":
                transport = "streamable-http"
            server_data["transport"] = transport
            server_data["name"] = name

            # Handle None values for list/dict fields
            if server_data.get("args") is None:
                server_data["args"] = []
            if server_data.get("headers") is None:
                server_data["headers"] = {}
            if server_data.get("env") is None:
                server_data["env"] = {}

            servers[name] = MCPServerConfig.model_validate(server_data)

        settings_data = data.get("settings", {})
        settings = MCPSettings.model_validate(settings_data)

        return MCPConfig(servers=servers, settings=settings)

    def merge_configs(self, *configs: MCPConfig) -> MCPConfig:
        """Merge multiple configurations.

        Later configs override earlier ones. Settings are merged field by field.

        Args:
            *configs: Configurations to merge (in order of precedence).

        Returns:
            Merged configuration.
        """
        merged_servers: dict[str, MCPServerConfig] = {}
        merged_settings_dict: dict[str, Any] = {}

        # Create default instance for comparison
        default_settings = MCPSettings()

        for config in configs:
            # Merge servers (later overrides)
            merged_servers.update(config.servers)

            # Merge settings field by field
            settings = config.settings
            for field_name in MCPSettings.model_fields:
                current_value = getattr(settings, field_name)
                default_value = getattr(default_settings, field_name)
                if current_value != default_value:
                    merged_settings_dict[field_name] = current_value

        merged_settings = MCPSettings.model_validate(merged_settings_dict)
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

        # Convert Pydantic models to dict for YAML serialization
        config_dict = self._config_to_dict(config)
        with open(path, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False)

    def _config_to_dict(self, config: MCPConfig) -> dict[str, Any]:
        """Convert MCPConfig to dictionary for serialization.

        Args:
            config: Configuration to convert.

        Returns:
            Dictionary representation.
        """
        servers_dict: dict[str, Any] = {}
        for name, server in config.servers.items():
            server_dict = server.model_dump(exclude={"name"}, exclude_none=True)
            # Convert transport enum to string
            if "transport" in server_dict:
                server_dict["transport"] = server_dict["transport"].value
            servers_dict[name] = server_dict

        return {
            "servers": servers_dict,
            "settings": config.settings.model_dump(),
        }
