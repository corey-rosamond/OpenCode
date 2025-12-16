"""Plugin lifecycle management."""

from __future__ import annotations

import importlib.metadata
import logging
import re
import threading

from .config import PluginConfig, PluginConfigManager
from .discovery import DiscoveredPlugin, PluginDiscovery
from .exceptions import PluginLoadError, PluginNotFoundError
from .loader import LoadedPlugin, PluginLoader
from .registry import PluginRegistry


class PluginManager:
    """Manage plugin lifecycle.

    Coordinates plugin discovery, loading, activation, and shutdown.
    Provides runtime enable/disable and reload capabilities.

    Thread-safe: Uses RLock for plugin operations.
    """

    def __init__(
        self,
        config: PluginConfig | None = None,
        registry: PluginRegistry | None = None,
    ) -> None:
        """Initialize plugin manager.

        Args:
            config: Plugin configuration.
            registry: Plugin registry (shared or new).
        """
        self.config = config or PluginConfig()
        self.registry = registry or PluginRegistry()
        self.config_manager = PluginConfigManager(self.config)
        self.discovery = PluginDiscovery(
            user_dir=self.config.user_dir,
            project_dir=self.config.project_dir,
        )
        self.loader = PluginLoader(self.config_manager)
        self.logger = logging.getLogger(__name__)

        self._plugins: dict[str, LoadedPlugin] = {}
        self._load_errors: dict[str, str] = {}
        self._lock = threading.RLock()  # Thread-safe plugin operations
        self._loading: set[str] = set()  # Track plugins being loaded (circular detection)

    @property
    def plugins(self) -> dict[str, LoadedPlugin]:
        """Get all loaded plugins.

        Returns:
            Dictionary mapping plugin IDs to LoadedPlugin instances.
        """
        return dict(self._plugins)

    def _check_dependencies(self, dependencies: list[str]) -> list[str]:
        """Check if plugin dependencies are installed.

        Args:
            dependencies: List of package requirements (e.g., ["requests>=2.0", "pyyaml"]).

        Returns:
            List of missing or unsatisfied dependencies.
        """
        missing: list[str] = []

        for dep in dependencies:
            # Parse package name (handle version specifiers)
            # e.g., "requests>=2.0" -> "requests"
            match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
            if not match:
                self.logger.warning(f"Invalid dependency format: {dep}")
                missing.append(dep)
                continue

            package_name = match.group(1)
            try:
                importlib.metadata.version(package_name)
            except importlib.metadata.PackageNotFoundError:
                missing.append(dep)
                self.logger.debug(f"Dependency not found: {dep}")

        return missing

    def discover_and_load(self) -> None:
        """Discover and load all plugins.

        Discovers plugins from all sources and attempts to load each one.
        Failed plugins are recorded in load_errors but don't prevent
        other plugins from loading.
        """
        if not self.config.enabled:
            self.logger.info("Plugin system is disabled")
            return

        discovered = self.discovery.discover()
        self.logger.info(f"Discovered {len(discovered)} plugins")

        for plugin_info in discovered:
            try:
                self._load_plugin(plugin_info)
            except PluginLoadError as e:
                self._load_errors[plugin_info.id] = str(e)
                self.logger.warning(f"Failed to load plugin {plugin_info.id}: {e}")

    def _load_plugin(self, discovered: DiscoveredPlugin) -> LoadedPlugin:
        """Load a single plugin.

        Args:
            discovered: Discovered plugin information.

        Returns:
            Loaded plugin instance.

        Raises:
            PluginLoadError: If dependencies are missing or plugin fails to load.
        """
        # Check dependencies before loading
        if discovered.manifest and discovered.manifest.dependencies:
            missing = self._check_dependencies(discovered.manifest.dependencies)
            if missing:
                raise PluginLoadError(
                    f"Plugin {discovered.id} has missing dependencies: {', '.join(missing)}",
                    plugin_id=discovered.id,
                )

        plugin = self.loader.load(discovered)
        self._plugins[plugin.id] = plugin

        # Call on_load lifecycle hook
        try:
            plugin.instance.on_load()
        except Exception as e:
            self.logger.warning(f"Plugin {plugin.id} on_load failed: {e}")

        # If enabled, activate and register contributions
        if plugin.enabled:
            self._activate_plugin(plugin)

        return plugin

    def _activate_plugin(self, plugin: LoadedPlugin) -> None:
        """Activate a plugin and register its contributions.

        Args:
            plugin: Plugin to activate.
        """
        # Register tools
        if plugin.manifest.capabilities.tools:
            for tool in plugin.instance.register_tools():
                name = self.registry.register_tool(plugin.id, tool)
                self.logger.debug(f"Registered tool: {name}")

        # Register commands
        if plugin.manifest.capabilities.commands:
            for command in plugin.instance.register_commands():
                name = self.registry.register_command(plugin.id, command)
                self.logger.debug(f"Registered command: {name}")

        # Register hooks
        if plugin.manifest.capabilities.hooks:
            for event, handlers in plugin.instance.register_hooks().items():
                for handler in handlers:
                    self.registry.register_hook(plugin.id, event, handler)
                    self.logger.debug(f"Registered hook for {event}")

        # Call on_activate lifecycle hook
        try:
            plugin.instance.on_activate()
            plugin.active = True
        except Exception as e:
            self.logger.warning(f"Plugin {plugin.id} on_activate failed: {e}")

    def _deactivate_plugin(self, plugin: LoadedPlugin) -> None:
        """Deactivate a plugin and unregister its contributions.

        Args:
            plugin: Plugin to deactivate.
        """
        # Unregister all contributions
        self.registry.unregister_plugin(plugin.id)

        # Call on_deactivate lifecycle hook
        try:
            plugin.instance.on_deactivate()
            plugin.active = False
        except Exception as e:
            self.logger.warning(f"Plugin {plugin.id} on_deactivate failed: {e}")

    def get_plugin(self, plugin_id: str) -> LoadedPlugin | None:
        """Get a plugin by ID.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            LoadedPlugin instance or None if not found.
        """
        return self._plugins.get(plugin_id)

    def enable(self, plugin_id: str) -> None:
        """Enable a plugin.

        Activates the plugin and registers its contributions.

        Args:
            plugin_id: Plugin identifier.

        Raises:
            PluginNotFoundError: If plugin not found.
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise PluginNotFoundError(
                f"Plugin not found: {plugin_id}",
                plugin_id=plugin_id,
            )

        if plugin.enabled:
            return

        # Enable in config
        self.config_manager.enable_plugin(plugin_id)

        # Activate plugin
        plugin.enabled = True
        self._activate_plugin(plugin)

        self.logger.info(f"Enabled plugin: {plugin_id}")

    def disable(self, plugin_id: str) -> None:
        """Disable a plugin.

        Deactivates the plugin and unregisters its contributions.

        Args:
            plugin_id: Plugin identifier.

        Raises:
            PluginNotFoundError: If plugin not found.
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise PluginNotFoundError(
                f"Plugin not found: {plugin_id}",
                plugin_id=plugin_id,
            )

        if not plugin.enabled:
            return

        # Deactivate plugin
        self._deactivate_plugin(plugin)

        # Disable in config
        self.config_manager.disable_plugin(plugin_id)
        plugin.enabled = False

        self.logger.info(f"Disabled plugin: {plugin_id}")

    def reload(self, plugin_id: str) -> None:
        """Reload a plugin.

        Unloads and reloads the plugin, re-registering its contributions.

        Thread-safe: Entire reload operation is atomic.
        Prevents access to plugin during reload.

        Args:
            plugin_id: Plugin ID to reload.

        Raises:
            PluginNotFoundError: If plugin not found.
            PluginLoadError: If reload fails.
        """
        with self._lock:
            # Check for circular reload
            if plugin_id in self._loading:
                raise PluginLoadError(
                    f"Circular reload detected: {plugin_id}",
                    plugin_id=plugin_id,
                )

            plugin = self._plugins.get(plugin_id)
            if plugin is None:
                raise PluginNotFoundError(
                    f"Plugin not found: {plugin_id}",
                    plugin_id=plugin_id,
                )

            # Mark as loading to prevent concurrent access
            self._loading.add(plugin_id)

            try:
                # Unload
                if plugin.active:
                    self._deactivate_plugin(plugin)
                self.loader.unload(plugin)

                # Find the discovered info again
                discovered_list = self.discovery.discover()
                discovered = next(
                    (d for d in discovered_list if d.id == plugin_id),
                    None,
                )

                if discovered is None:
                    del self._plugins[plugin_id]
                    raise PluginNotFoundError(
                        f"Plugin no longer found: {plugin_id}",
                        plugin_id=plugin_id,
                    )

                # Reload
                new_plugin = self.loader.load(discovered)
                self._plugins[plugin_id] = new_plugin

            finally:
                # Always remove from loading set
                self._loading.discard(plugin_id)

        new_plugin.instance.on_load()

        if new_plugin.enabled:
            self._activate_plugin(new_plugin)

        self.logger.info(f"Reloaded plugin: {plugin_id}")

    def list_plugins(self) -> list[LoadedPlugin]:
        """List all loaded plugins.

        Returns:
            List of all LoadedPlugin instances.
        """
        return list(self._plugins.values())

    def get_load_errors(self) -> dict[str, str]:
        """Get plugins that failed to load.

        Returns:
            Dictionary mapping plugin IDs to error messages.
        """
        return dict(self._load_errors)

    def shutdown(self) -> None:
        """Shutdown plugin system.

        Deactivates and unloads all plugins.
        """
        for plugin in list(self._plugins.values()):
            try:
                if plugin.active:
                    self._deactivate_plugin(plugin)
                self.loader.unload(plugin)
            except Exception as e:
                self.logger.warning(f"Error shutting down plugin {plugin.id}: {e}")

        self._plugins.clear()
