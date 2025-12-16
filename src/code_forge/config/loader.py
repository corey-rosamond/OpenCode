"""Configuration loader for Code-Forge.

This module implements the ConfigLoader class that handles hierarchical
configuration loading, merging, validation, and live reload.
"""

from __future__ import annotations

import copy
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

from code_forge.config.models import CodeForgeConfig
from code_forge.config.sources import (
    EnvironmentSource,
    IConfigSource,
    JsonFileSource,
    YamlFileSource,
)
from code_forge.core import ConfigError, IConfigLoader, get_logger

logger = get_logger("config.loader")


class ConfigLoader(IConfigLoader):
    """Configuration loader with hierarchical merging.

    Load order (later overrides earlier):
    1. Defaults (from CodeForgeConfig)
    2. Enterprise settings (/etc/forge/settings.json)
    3. User settings (~/.forge/settings.json or .yaml)
    4. Project settings (.forge/settings.json or .yaml)
    5. Local settings (.forge/settings.local.json)
    6. Environment variables (FORGE_*)

    Thread Safety:
    - Uses threading.Lock to protect config access during reload
    - File watcher runs in separate thread, triggers reload safely
    - Observers are notified outside the lock to prevent deadlocks
    """

    def __init__(
        self,
        user_dir: Path | None = None,
        project_dir: Path | None = None,
        enterprise_dir: Path | None = None,
    ) -> None:
        """Initialize configuration loader.

        Args:
            user_dir: User configuration directory. Defaults to ~/.forge
            project_dir: Project configuration directory. Defaults to ./.forge
            enterprise_dir: Enterprise configuration directory. Defaults to /etc/forge
        """
        self._user_dir = user_dir or Path.home() / ".forge"
        self._project_dir = project_dir or Path.cwd() / ".forge"
        self._enterprise_dir = enterprise_dir or Path("/etc/forge")
        self._config: CodeForgeConfig | None = None
        self._observers: list[Callable[[CodeForgeConfig], None]] = []
        self._file_watcher: BaseObserver | None = None
        self._lock = threading.Lock()

    @property
    def config(self) -> CodeForgeConfig:
        """Get current configuration, loading if necessary.

        Thread-safe: uses lock to prevent races during reload.

        Returns:
            Current CodeForgeConfig instance.
        """
        with self._lock:
            if self._config is None:
                self._config = self.load_all()
            return self._config

    @property
    def user_dir(self) -> Path:
        """Get user configuration directory."""
        return self._user_dir

    @property
    def project_dir(self) -> Path:
        """Get project configuration directory."""
        return self._project_dir

    def load_all(self) -> CodeForgeConfig:
        """Load and merge all configuration sources.

        Returns:
            Validated CodeForgeConfig with all sources merged.

        Raises:
            ConfigError: If configuration cannot be loaded or validated.
        """
        # Start with defaults
        config: dict[str, Any] = CodeForgeConfig().model_dump()

        # 1. Load enterprise settings (if exists)
        enterprise_json = self._enterprise_dir / "settings.json"
        config = self._load_and_merge(config, JsonFileSource(enterprise_json))

        # 2. Load user settings (JSON preferred, fallback to YAML)
        user_json = self._user_dir / "settings.json"
        user_yaml = self._user_dir / "settings.yaml"
        if user_json.exists():
            config = self._load_and_merge(config, JsonFileSource(user_json))
        elif user_yaml.exists():
            config = self._load_and_merge(config, YamlFileSource(user_yaml))

        # 3. Load project settings (JSON preferred, fallback to YAML)
        project_json = self._project_dir / "settings.json"
        project_yaml = self._project_dir / "settings.yaml"
        if project_json.exists():
            config = self._load_and_merge(config, JsonFileSource(project_json))
        elif project_yaml.exists():
            config = self._load_and_merge(config, YamlFileSource(project_yaml))

        # 4. Load local overrides (always JSON, gitignored)
        local_json = self._project_dir / "settings.local.json"
        config = self._load_and_merge(config, JsonFileSource(local_json))

        # 5. Apply environment variables (highest precedence)
        config = self._load_and_merge(config, EnvironmentSource())

        # 6. Validate and return
        try:
            return CodeForgeConfig.model_validate(config)
        except ValidationError as e:
            logger.error("Configuration validation failed: %s", e)
            raise ConfigError(f"Configuration validation failed: {e}") from e

    def _load_and_merge(
        self,
        base: dict[str, Any],
        source: IConfigSource,
    ) -> dict[str, Any]:
        """Load from source and merge into base config.

        Args:
            base: Base configuration dictionary.
            source: Configuration source to load from.

        Returns:
            Merged configuration dictionary.
        """
        try:
            if source.exists():
                override = source.load()
                if override:
                    logger.debug("Loaded config from %s", source)
                    return self.merge(base, override)
                else:
                    logger.debug("Config source %s exists but returned empty", source)
        except ConfigError as e:
            # Log and continue with base config
            logger.debug("Skipped config source %s: %s", source, e)
        except FileNotFoundError:
            # File was deleted between exists() check and load() (TOCTOU race)
            logger.debug("Config source %s disappeared before load", source)
        return base

    def load(self, path: Path) -> dict[str, Any]:
        """Load single configuration file.

        Args:
            path: Path to configuration file.

        Returns:
            Configuration dictionary.

        Raises:
            ConfigError: If file format is not supported or file is invalid.
        """
        suffix = path.suffix.lower()
        if suffix == ".json":
            return JsonFileSource(path).load()
        elif suffix in (".yaml", ".yml"):
            return YamlFileSource(path).load()
        else:
            raise ConfigError(f"Unsupported configuration format: {suffix}")

    def merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary.
            override: Override configuration dictionary.

        Returns:
            New dictionary with override values merged into base.
            Nested dictionaries are merged recursively.
            Other values are replaced by override.

        Note:
            Uses deepcopy to ensure the result is fully independent of inputs.
            Modifying the returned dict will not affect base or override.
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.merge(result[key], value)
            else:
                # Deepcopy the override value to prevent shared references
                result[key] = copy.deepcopy(value)

        return result

    def validate(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        try:
            CodeForgeConfig.model_validate(config)
            return True, []
        except ValidationError as e:
            return False, [str(e)]

    def reload(self) -> None:
        """Reload configuration from all sources.

        Thread-safe: uses lock to prevent races during reload.
        Observers are notified outside the lock to prevent deadlocks.
        If reload fails, the old configuration is preserved.
        """
        try:
            new_config = self.load_all()
            with self._lock:
                self._config = new_config
            # Notify outside lock to prevent deadlocks
            self._notify_observers(new_config)
            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error("Failed to reload configuration: %s", e)
            # Keep old config on error

    def watch(self) -> None:
        """Start watching configuration files for changes.

        Creates a file watcher that monitors user and project
        configuration directories. When a .json or .yaml file
        changes, the configuration is automatically reloaded.
        """
        if self._file_watcher is not None:
            return

        handler = _ConfigChangeHandler(self)
        self._file_watcher = Observer()

        # Watch directories that exist
        for path in [self._user_dir, self._project_dir]:
            if path.exists() and path.is_dir():
                self._file_watcher.schedule(  # type: ignore[no-untyped-call]
                    handler, str(path), recursive=False
                )
                logger.debug("Watching %s for configuration changes", path)

        self._file_watcher.start()  # type: ignore[no-untyped-call]
        logger.info("Configuration file watcher started")

    def stop_watching(self) -> None:
        """Stop watching configuration files.

        Safe to call multiple times. Waits for watcher thread to finish.
        """
        if self._file_watcher is not None:
            self._file_watcher.stop()  # type: ignore[no-untyped-call]
            self._file_watcher.join(timeout=5.0)
            self._file_watcher = None
            logger.info("Configuration file watcher stopped")

    def add_observer(self, callback: Callable[[CodeForgeConfig], None]) -> None:
        """Add observer for configuration changes.

        Args:
            callback: Function to call when configuration changes.
                      Receives the new CodeForgeConfig instance.
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[CodeForgeConfig], None]) -> None:
        """Remove observer.

        Args:
            callback: Previously registered callback to remove.
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, config: CodeForgeConfig) -> None:
        """Notify all observers of configuration change.

        Args:
            config: New configuration to pass to observers.
        """
        for observer in self._observers:
            try:
                observer(config)
            except Exception as e:
                logger.error("Observer error: %s", e)

    def __del__(self) -> None:
        """Cleanup: ensure file watcher is stopped.

        Note: __del__ may be called with partially destroyed state,
        so we wrap everything in try/except to avoid masking errors.
        """
        try:
            self.stop_watching()
        except Exception:
            # Can't safely log in __del__ - interpreter may be shutting down
            pass


class _ConfigChangeHandler(FileSystemEventHandler):
    """File system event handler for configuration changes.

    Includes debouncing to prevent rapid reload calls when files
    are being modified quickly (e.g., editor auto-save).
    """

    # Debounce window in seconds
    DEBOUNCE_SECONDS = 0.5

    def __init__(self, loader: ConfigLoader) -> None:
        """Initialize handler.

        Args:
            loader: ConfigLoader to notify of changes.
        """
        super().__init__()
        self._loader = loader
        self._last_event_time: float = 0
        self._pending_reload: threading.Timer | None = None
        self._lock = threading.Lock()

    def _schedule_reload(self, src_path: str) -> None:
        """Schedule a debounced reload.

        Args:
            src_path: Path that triggered the event (for logging).
        """
        with self._lock:
            # Cancel any pending reload
            if self._pending_reload is not None:
                self._pending_reload.cancel()
                self._pending_reload = None

            # Schedule new reload after debounce period
            def do_reload() -> None:
                with self._lock:
                    self._pending_reload = None
                logger.debug("Debounced config reload triggered by: %s", src_path)
                self._loader.reload()

            self._pending_reload = threading.Timer(self.DEBOUNCE_SECONDS, do_reload)
            self._pending_reload.daemon = True
            self._pending_reload.start()
            logger.debug("Config change detected, reload scheduled: %s", src_path)

    def _is_config_file(self, path: str) -> bool:
        """Check if path is a config file (not a temp file).

        Args:
            path: File path to check.

        Returns:
            True if this is a config file we should watch.
        """
        # Filter out temp files created by editors
        if path.endswith((".swp", ".tmp", "~", ".bak")):
            return False
        if ".__" in path or path.startswith(".#"):
            return False
        return path.endswith((".json", ".yaml", ".yml"))

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event.
        """
        if event.is_directory:
            return

        src_path = str(event.src_path)
        if self._is_config_file(src_path):
            self._schedule_reload(src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: File system event.
        """
        if event.is_directory:
            return

        src_path = str(event.src_path)
        if self._is_config_file(src_path):
            self._schedule_reload(src_path)
