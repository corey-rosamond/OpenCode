"""Plugin loading."""

from __future__ import annotations

import importlib
import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Plugin, PluginContext
from .config import PluginConfigManager  # noqa: TC001 - used at runtime
from .exceptions import PluginLoadError
from .manifest import PluginManifest  # noqa: TC001 - used at runtime

if TYPE_CHECKING:
    from .discovery import DiscoveredPlugin


@dataclass
class LoadedPlugin:
    """Loaded plugin instance.

    Contains the loaded plugin instance along with its manifest,
    context, and state information.

    Attributes:
        id: Plugin identifier.
        manifest: Plugin manifest.
        instance: Plugin instance.
        context: Plugin context.
        source: Discovery source.
        enabled: Whether plugin is enabled.
        active: Whether plugin is currently active.
        added_sys_path: Path added to sys.path for cleanup.
    """

    id: str
    manifest: PluginManifest
    instance: Plugin
    context: PluginContext
    source: str
    enabled: bool = True
    active: bool = False
    # Track if we added a path to sys.path so we can clean it up on unload
    added_sys_path: str | None = None


class PluginLoader:
    """Load plugin instances.

    Handles importing plugin modules, instantiating plugin classes,
    and creating plugin contexts.
    """

    def __init__(self, config_manager: PluginConfigManager) -> None:
        """Initialize plugin loader.

        Args:
            config_manager: Plugin configuration manager.
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

    def load(self, discovered: DiscoveredPlugin) -> LoadedPlugin:
        """Load a discovered plugin.

        Imports the plugin module, instantiates the plugin class,
        and creates the plugin context.

        Args:
            discovered: Discovered plugin information.

        Returns:
            Loaded plugin instance.

        Raises:
            PluginLoadError: If plugin fails to load.
        """
        manifest = discovered.manifest
        plugin_id = manifest.name
        added_path: str | None = None

        try:
            # Add plugin path to sys.path if needed
            # Track what we add so we can clean up on unload
            if discovered.path:
                plugin_path = str(discovered.path)
                if plugin_path not in sys.path:
                    sys.path.insert(0, plugin_path)
                    added_path = plugin_path  # Remember for cleanup

            # Import plugin module
            # Entry point format: "module.path:ClassName"
            if ":" not in manifest.entry_point:
                raise PluginLoadError(
                    f"Invalid entry point format: '{manifest.entry_point}'. "
                    f"Expected 'module.path:ClassName' (e.g., 'my_plugin.main:MyPlugin')",
                    plugin_id=plugin_id,
                )
            module_name, class_name = manifest.entry_point.split(":", 1)
            if not module_name:
                raise PluginLoadError(
                    f"Invalid entry point: empty module name in '{manifest.entry_point}'",
                    plugin_id=plugin_id,
                )
            if not class_name:
                raise PluginLoadError(
                    f"Invalid entry point: empty class name in '{manifest.entry_point}'",
                    plugin_id=plugin_id,
                )
            module = importlib.import_module(module_name)

            # Get plugin class
            if not hasattr(module, class_name):
                raise PluginLoadError(
                    f"Plugin class {class_name} not found in {module_name}",
                    plugin_id=plugin_id,
                )

            plugin_class = getattr(module, class_name)

            # Validate it's a Plugin subclass
            if not issubclass(plugin_class, Plugin):
                raise PluginLoadError(
                    f"{class_name} is not a Plugin subclass",
                    plugin_id=plugin_id,
                )

            # Create instance
            instance = plugin_class()

            # Create context
            context = self.create_context(plugin_id, manifest)

            # Set context on instance
            instance.set_context(context)

            # Check if disabled
            enabled = not self.config_manager.is_plugin_disabled(plugin_id)

            return LoadedPlugin(
                id=plugin_id,
                manifest=manifest,
                instance=instance,
                context=context,
                source=discovered.source,
                enabled=enabled,
                added_sys_path=added_path,  # Track for cleanup
            )

        except ImportError as e:
            raise PluginLoadError(
                f"Failed to import plugin: {e}",
                plugin_id=plugin_id,
            ) from e
        except ValueError as e:
            # Raised by other validation errors
            raise PluginLoadError(
                f"Plugin validation error: {e}",
                plugin_id=plugin_id,
            ) from e
        except Exception as e:
            raise PluginLoadError(
                f"Failed to load plugin: {e}",
                plugin_id=plugin_id,
            ) from e

    def create_context(
        self,
        plugin_id: str,
        manifest: PluginManifest,
    ) -> PluginContext:
        """Create context for a plugin.

        Args:
            plugin_id: Plugin identifier.
            manifest: Plugin manifest.

        Returns:
            Plugin context.
        """
        # Get plugin config
        config = self.config_manager.get_plugin_config(
            plugin_id,
            schema=manifest.config_schema,
        )

        # Get plugin data directory
        data_dir = self.config_manager.get_plugin_data_dir(plugin_id)

        # Create logger for plugin
        logger = logging.getLogger(f"code_forge.plugins.{plugin_id}")

        return PluginContext(
            plugin_id=plugin_id,
            data_dir=data_dir,
            config=config,
            logger=logger,
        )

    def unload(self, plugin: LoadedPlugin) -> None:
        """Unload a plugin and clean up sys.path modifications.

        Calls lifecycle hooks and removes any sys.path entries
        that were added during load.

        Args:
            plugin: Plugin to unload.
        """
        try:
            if plugin.active:
                plugin.instance.on_deactivate()
                plugin.active = False

            plugin.instance.on_unload()

        except Exception as e:
            self.logger.warning(f"Error unloading plugin {plugin.id}: {e}")

        # Clean up sys.path entry we added during load
        # This prevents sys.path from growing indefinitely as plugins are
        # loaded/unloaded/reloaded, and avoids potential import conflicts
        if plugin.added_sys_path and plugin.added_sys_path in sys.path:
            try:
                sys.path.remove(plugin.added_sys_path)
                self.logger.debug(f"Removed {plugin.added_sys_path} from sys.path")
            except ValueError:
                pass  # Already removed (shouldn't happen, but be defensive)
