"""Configuration sources for Code-Forge.

This module implements the Strategy pattern for loading configuration
from different sources (JSON files, YAML files, environment variables).
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

import yaml

from code_forge.core import ConfigError, get_logger

logger = get_logger("config.sources")


class IConfigSource(ABC):
    """Interface for configuration sources.

    Each source knows how to load configuration data from
    a specific location or format.
    """

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Load configuration from source.

        Returns:
            Dictionary containing configuration data.
            Returns empty dict if source doesn't exist.

        Raises:
            ConfigError: If source exists but cannot be parsed.
        """
        ...

    @abstractmethod
    def exists(self) -> bool:
        """Check if source exists.

        Returns:
            True if source exists and can be read.
        """
        ...


class JsonFileSource(IConfigSource):
    """Load configuration from JSON file."""

    def __init__(self, path: Path) -> None:
        """Initialize JSON file source.

        Args:
            path: Path to JSON configuration file.
        """
        self._path = path

    def load(self) -> dict[str, Any]:
        """Load configuration from JSON file.

        Returns:
            Configuration dictionary or empty dict if file doesn't exist.

        Raises:
            ConfigError: If file exists but contains invalid JSON.
        """
        if not self.exists():
            return {}

        try:
            with self._path.open(encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    return {}
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ConfigError(f"JSON root must be object, got {type(data).__name__}")
                return data
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in %s: %s", self._path, e)
            raise ConfigError(f"Invalid JSON in {self._path}: {e}") from e
        except OSError as e:
            logger.warning("Cannot read %s: %s", self._path, e)
            raise ConfigError(f"Cannot read {self._path}: {e}") from e

    def exists(self) -> bool:
        """Check if JSON file exists."""
        return self._path.exists() and self._path.is_file()

    @property
    def path(self) -> Path:
        """Get the file path."""
        return self._path


class YamlFileSource(IConfigSource):
    """Load configuration from YAML file."""

    def __init__(self, path: Path) -> None:
        """Initialize YAML file source.

        Args:
            path: Path to YAML configuration file.
        """
        self._path = path

    def load(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary or empty dict if file doesn't exist.

        Raises:
            ConfigError: If file exists but contains invalid YAML.
        """
        if not self.exists():
            return {}

        try:
            with self._path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None:
                    return {}
                if not isinstance(data, dict):
                    raise ConfigError(f"YAML root must be mapping, got {type(data).__name__}")
                return data
        except yaml.YAMLError as e:
            logger.warning("Invalid YAML in %s: %s", self._path, e)
            raise ConfigError(f"Invalid YAML in {self._path}: {e}") from e
        except OSError as e:
            logger.warning("Cannot read %s: %s", self._path, e)
            raise ConfigError(f"Cannot read {self._path}: {e}") from e

    def exists(self) -> bool:
        """Check if YAML file exists."""
        return self._path.exists() and self._path.is_file()

    @property
    def path(self) -> Path:
        """Get the file path."""
        return self._path


class EnvironmentSource(IConfigSource):
    """Load configuration from environment variables.

    Environment variables are mapped to configuration paths:
    - FORGE_API_KEY -> api_key
    - FORGE_MODEL -> model.default
    - FORGE_MAX_TOKENS -> model.max_tokens
    - FORGE_THEME -> display.theme
    """

    PREFIX: ClassVar[str] = "FORGE_"

    # Mapping of environment variable name to config path
    # (section, key) or just key for top-level
    MAPPINGS: ClassVar[dict[str, str | tuple[str, str]]] = {
        "FORGE_API_KEY": "api_key",
        "FORGE_MODEL": ("model", "default"),
        "FORGE_MAX_TOKENS": ("model", "max_tokens"),
        "FORGE_TEMPERATURE": ("model", "temperature"),
        "FORGE_THEME": ("display", "theme"),
        "FORGE_VIM_MODE": ("display", "vim_mode"),
        "FORGE_STREAMING": ("display", "streaming"),
    }

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        """Initialize environment source.

        Args:
            environ: Environment dictionary. Defaults to os.environ.
        """
        self._environ = environ if environ is not None else dict(os.environ)

    def load(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Returns:
            Configuration dictionary with values from environment.
        """
        config: dict[str, Any] = {}

        for env_var, path in self.MAPPINGS.items():
            value = self._environ.get(env_var)
            if value is not None:
                self._set_nested(config, path, self._convert_value(value, path))

        return config

    def exists(self) -> bool:
        """Environment always exists."""
        return True

    def _set_nested(
        self,
        d: dict[str, Any],
        path: str | tuple[str, str],
        value: Any,
    ) -> None:
        """Set nested dictionary value.

        Args:
            d: Dictionary to modify.
            path: Either a top-level key or (section, key) tuple.
            value: Value to set.
        """
        if isinstance(path, str):
            d[path] = value
        else:
            section, key = path
            if section not in d:
                d[section] = {}
            d[section][key] = value

    # Known keys and their expected types for validation
    BOOLEAN_KEYS: ClassVar[frozenset[str]] = frozenset({
        "vim_mode", "streaming", "show_tokens", "show_cost", "auto_save"
    })
    INTEGER_KEYS: ClassVar[frozenset[str]] = frozenset({
        "max_tokens", "save_interval", "max_history", "compress_after"
    })
    FLOAT_KEYS: ClassVar[frozenset[str]] = frozenset({"temperature"})
    STRING_KEYS: ClassVar[frozenset[str]] = frozenset({
        "api_key", "default", "theme"  # Known string keys
    })

    def _convert_value(self, value: str, path: str | tuple[str, str]) -> Any:
        """Convert string value to appropriate type.

        Args:
            value: String value from environment.
            path: Config path for type inference.

        Returns:
            Converted value (int, float, bool, or str).
        """
        # Determine expected type from path
        key = path[1] if isinstance(path, tuple) else path

        # Boolean conversion
        if key in self.BOOLEAN_KEYS:
            return value.lower() in ("true", "1", "yes", "on")

        # Integer conversion
        if key in self.INTEGER_KEYS:
            try:
                return int(value)
            except ValueError:
                logger.warning("Invalid integer value for %s: %s", key, value)
                return value

        # Float conversion
        if key in self.FLOAT_KEYS:
            try:
                return float(value)
            except ValueError:
                logger.warning("Invalid float value for %s: %s", key, value)
                return value

        # String keys pass through
        if key in self.STRING_KEYS:
            return value

        # Unknown key - log debug and pass through as string
        logger.debug(
            "Unknown config key '%s' from environment, treating as string", key
        )
        return value
