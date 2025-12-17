"""Tests for plugin manager."""

import sys
from pathlib import Path

import pytest

from code_forge.plugins.base import Plugin, PluginCapabilities, PluginMetadata
from code_forge.plugins.config import PluginConfig, PluginConfigManager
from code_forge.plugins.discovery import PluginDiscovery
from code_forge.plugins.exceptions import PluginNotFoundError
from code_forge.plugins.loader import LoadedPlugin, PluginLoader
from code_forge.plugins.manager import PluginManager
from code_forge.plugins.registry import PluginRegistry


class SamplePlugin(Plugin):
    """Sample plugin for testing."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sample-plugin",
            version="1.0.0",
            description="Sample plugin",
        )

    @property
    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(tools=True)


class TestPluginManager:
    """Tests for PluginManager."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> PluginManager:
        """Create a plugin manager for testing."""
        config = PluginConfig(
            user_dir=tmp_path / "user_plugins",
            project_dir=tmp_path / "project_plugins",
        )
        return PluginManager(config=config)

    def test_init_default(self) -> None:
        """Test default initialization."""
        manager = PluginManager()
        assert isinstance(manager.config, PluginConfig)
        assert isinstance(manager.registry, PluginRegistry)
        assert isinstance(manager.config_manager, PluginConfigManager)
        assert isinstance(manager.discovery, PluginDiscovery)
        assert isinstance(manager.loader, PluginLoader)

    def test_init_with_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = PluginConfig(enabled=False)
        manager = PluginManager(config=config)
        assert manager.config.enabled is False

    def test_init_with_shared_registry(self) -> None:
        """Test initialization with shared registry."""
        registry = PluginRegistry()
        manager = PluginManager(registry=registry)
        assert manager.registry is registry

    def test_plugins_property_empty(self, manager: PluginManager) -> None:
        """Test plugins property when empty."""
        assert manager.plugins == {}

    def test_discover_and_load(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test discovering and loading plugins."""
        # Create a plugin
        plugin_dir = tmp_path / "user_plugins" / "test-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: test-plugin
version: 1.0.0
description: Test plugin
entry_point: test_plugin:TestPlugin
capabilities:
  tools: true
""")

        (plugin_dir / "test_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata, PluginCapabilities

class TestPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
        )

    @property
    def capabilities(self):
        return PluginCapabilities(tools=True)
""")

        manager.discover_and_load()

        assert len(manager.plugins) == 1
        assert "test-plugin" in manager.plugins

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_discover_and_load_disabled(self) -> None:
        """Test discover_and_load when plugin system is disabled."""
        config = PluginConfig(enabled=False)
        manager = PluginManager(config=config)

        manager.discover_and_load()
        assert manager.plugins == {}

    def test_discover_and_load_with_error(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test discover_and_load handles errors gracefully."""
        # Create a plugin with import error
        plugin_dir = tmp_path / "user_plugins" / "bad-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: bad-plugin
version: 1.0.0
description: Bad plugin
entry_point: nonexistent_module:Plugin
""")

        manager.discover_and_load()

        # Should have error recorded but not crash
        errors = manager.get_load_errors()
        assert "bad-plugin" in errors

    def test_get_plugin(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test getting a plugin by ID."""
        # Create and load a plugin
        plugin_dir = tmp_path / "user_plugins" / "my-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: my-plugin
version: 1.0.0
description: My plugin
entry_point: my_plugin:MyPlugin
""")

        (plugin_dir / "my_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class MyPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My plugin",
        )
""")

        manager.discover_and_load()

        plugin = manager.get_plugin("my-plugin")
        assert isinstance(plugin, LoadedPlugin)
        assert plugin.id == "my-plugin"

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_get_plugin_not_found(self, manager: PluginManager) -> None:
        """Test getting non-existent plugin."""
        plugin = manager.get_plugin("nonexistent")
        assert plugin is None

    def test_enable_plugin(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test enabling a disabled plugin."""
        # Create and load a disabled plugin
        manager.config.disabled_plugins = ["disabled-plugin"]

        plugin_dir = tmp_path / "user_plugins" / "disabled-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: disabled-plugin
version: 1.0.0
description: Disabled plugin
entry_point: disabled_plugin:DisabledPlugin
""")

        (plugin_dir / "disabled_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class DisabledPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="disabled-plugin",
            version="1.0.0",
            description="Disabled plugin",
        )
""")

        manager.discover_and_load()

        plugin = manager.get_plugin("disabled-plugin")
        assert isinstance(plugin, LoadedPlugin)
        assert plugin.enabled is False

        manager.enable("disabled-plugin")
        assert plugin.enabled is True

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_enable_not_found(self, manager: PluginManager) -> None:
        """Test enabling non-existent plugin."""
        with pytest.raises(PluginNotFoundError):
            manager.enable("nonexistent")

    def test_enable_already_enabled(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test enabling already enabled plugin is idempotent."""
        plugin_dir = tmp_path / "user_plugins" / "enabled-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: enabled-plugin
version: 1.0.0
description: Enabled plugin
entry_point: enabled_plugin:Plugin
""")

        (plugin_dir / "enabled_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class Plugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="enabled-plugin",
            version="1.0.0",
            description="Enabled plugin",
        )
""")

        manager.discover_and_load()

        # Enable twice should not raise
        manager.enable("enabled-plugin")
        manager.enable("enabled-plugin")

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_disable_plugin(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test disabling an enabled plugin."""
        plugin_dir = tmp_path / "user_plugins" / "to-disable"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: to-disable
version: 1.0.0
description: To disable
entry_point: to_disable:Plugin
""")

        (plugin_dir / "to_disable.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class Plugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="to-disable",
            version="1.0.0",
            description="To disable",
        )
""")

        manager.discover_and_load()

        plugin = manager.get_plugin("to-disable")
        assert isinstance(plugin, LoadedPlugin)
        assert plugin.enabled is True

        manager.disable("to-disable")
        assert plugin.enabled is False

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_disable_not_found(self, manager: PluginManager) -> None:
        """Test disabling non-existent plugin."""
        with pytest.raises(PluginNotFoundError):
            manager.disable("nonexistent")

    def test_list_plugins(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test listing all plugins."""
        # Create two plugins
        for name in ["plugin1", "plugin2"]:
            plugin_dir = tmp_path / "user_plugins" / name
            plugin_dir.mkdir(parents=True)

            (plugin_dir / "plugin.yaml").write_text(f"""
name: {name}
version: 1.0.0
description: {name}
entry_point: {name}:Plugin
""")

            (plugin_dir / f"{name}.py").write_text(f"""
from code_forge.plugins.base import Plugin, PluginMetadata

class Plugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="{name}",
            version="1.0.0",
            description="{name}",
        )
""")

        manager.discover_and_load()

        plugins = manager.list_plugins()
        assert len(plugins) == 2
        plugin_ids = {p.id for p in plugins}
        assert plugin_ids == {"plugin1", "plugin2"}

        # Cleanup
        for name in ["plugin1", "plugin2"]:
            plugin_dir = tmp_path / "user_plugins" / name
            if str(plugin_dir) in sys.path:
                sys.path.remove(str(plugin_dir))

    def test_get_load_errors(self, manager: PluginManager) -> None:
        """Test getting load errors."""
        errors = manager.get_load_errors()
        assert isinstance(errors, dict)
        assert errors == {}

    def test_shutdown(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test shutting down plugin system."""
        plugin_dir = tmp_path / "user_plugins" / "shutdown-test"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: shutdown-test
version: 1.0.0
description: Shutdown test
entry_point: shutdown_test:Plugin
""")

        (plugin_dir / "shutdown_test.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class Plugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="shutdown-test",
            version="1.0.0",
            description="Shutdown test",
        )
""")

        manager.discover_and_load()
        assert len(manager.plugins) == 1

        manager.shutdown()
        assert len(manager._plugins) == 0

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_reload_plugin(self, manager: PluginManager, tmp_path: Path) -> None:
        """Test reloading a plugin."""
        plugin_dir = tmp_path / "user_plugins" / "reload-test"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: reload-test
version: 1.0.0
description: Reload test
entry_point: reload_test:Plugin
""")

        (plugin_dir / "reload_test.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class Plugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="reload-test",
            version="1.0.0",
            description="Reload test",
        )
""")

        manager.discover_and_load()

        # Should not raise
        manager.reload("reload-test")

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_reload_not_found(self, manager: PluginManager) -> None:
        """Test reloading non-existent plugin."""
        with pytest.raises(PluginNotFoundError):
            manager.reload("nonexistent")

    def test_lifecycle_hook_on_load_failure(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test on_load hook failure is handled gracefully."""
        plugin_dir = tmp_path / "user_plugins" / "failing-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: failing-plugin
version: 1.0.0
description: Failing plugin
entry_point: failing_plugin:FailingPlugin
""")

        (plugin_dir / "failing_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class FailingPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="failing-plugin",
            version="1.0.0",
            description="Failing plugin",
        )

    def on_load(self):
        raise RuntimeError("on_load failed")
""")

        manager.discover_and_load()

        # Plugin should still be loaded despite hook failure
        assert "failing-plugin" in manager.plugins

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_lifecycle_hook_on_activate_failure(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test on_activate hook failure is handled gracefully."""
        plugin_dir = tmp_path / "user_plugins" / "activate-fail"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: activate-fail
version: 1.0.0
description: Activate fail
entry_point: activate_fail:ActivateFailPlugin
""")

        (plugin_dir / "activate_fail.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class ActivateFailPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="activate-fail",
            version="1.0.0",
            description="Activate fail",
        )

    def on_activate(self):
        raise RuntimeError("on_activate failed")
""")

        manager.discover_and_load()

        # Plugin should still be loaded despite hook failure
        assert "activate-fail" in manager.plugins

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_lifecycle_hook_on_deactivate_failure(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test on_deactivate hook failure is handled gracefully."""
        plugin_dir = tmp_path / "user_plugins" / "deactivate-fail"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: deactivate-fail
version: 1.0.0
description: Deactivate fail
entry_point: deactivate_fail:DeactivateFailPlugin
""")

        (plugin_dir / "deactivate_fail.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class DeactivateFailPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="deactivate-fail",
            version="1.0.0",
            description="Deactivate fail",
        )

    def on_deactivate(self):
        raise RuntimeError("on_deactivate failed")
""")

        manager.discover_and_load()
        plugin = manager.get_plugin("deactivate-fail")
        assert isinstance(plugin, LoadedPlugin)
        assert plugin.active

        # Disable should handle error gracefully
        manager.disable("deactivate-fail")
        assert not plugin.enabled

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_disable_already_disabled(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test disabling already disabled plugin is idempotent."""
        manager.config.disabled_plugins = ["already-disabled"]

        plugin_dir = tmp_path / "user_plugins" / "already-disabled"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: already-disabled
version: 1.0.0
description: Already disabled
entry_point: already_disabled:AlreadyDisabledPlugin
""")

        (plugin_dir / "already_disabled.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class AlreadyDisabledPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="already-disabled",
            version="1.0.0",
            description="Already disabled",
        )
""")

        manager.discover_and_load()
        plugin = manager.get_plugin("already-disabled")
        assert isinstance(plugin, LoadedPlugin)
        assert not plugin.enabled

        # Disable again should not raise
        manager.disable("already-disabled")

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_shutdown_handles_errors(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test shutdown handles errors gracefully."""
        plugin_dir = tmp_path / "user_plugins" / "shutdown-error"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: shutdown-error
version: 1.0.0
description: Shutdown error
entry_point: shutdown_error:ShutdownErrorPlugin
""")

        (plugin_dir / "shutdown_error.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata

class ShutdownErrorPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="shutdown-error",
            version="1.0.0",
            description="Shutdown error",
        )

    def on_deactivate(self):
        raise RuntimeError("deactivate failed during shutdown")
""")

        manager.discover_and_load()
        assert len(manager.plugins) == 1

        # Should not raise despite error
        manager.shutdown()
        assert len(manager._plugins) == 0

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_plugin_with_tools(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test loading plugin that registers tools."""
        plugin_dir = tmp_path / "user_plugins" / "tools-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: tools-plugin
version: 1.0.0
description: Plugin with tools
entry_point: tools_plugin:ToolsPlugin
capabilities:
  tools: true
""")

        (plugin_dir / "tools_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata, PluginCapabilities

class MockTool:
    name = "mock-tool"

class ToolsPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="tools-plugin",
            version="1.0.0",
            description="Plugin with tools",
        )

    @property
    def capabilities(self):
        return PluginCapabilities(tools=True)

    def register_tools(self):
        return [MockTool()]
""")

        manager.discover_and_load()

        # Check tools were registered
        tools = manager.registry.get_tools()
        assert "tools-plugin__mock-tool" in tools

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_plugin_with_commands(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test loading plugin that registers commands."""
        plugin_dir = tmp_path / "user_plugins" / "commands-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: commands-plugin
version: 1.0.0
description: Plugin with commands
entry_point: commands_plugin:CommandsPlugin
capabilities:
  commands: true
""")

        (plugin_dir / "commands_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata, PluginCapabilities

class MockCommand:
    name = "mock-cmd"

class CommandsPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="commands-plugin",
            version="1.0.0",
            description="Plugin with commands",
        )

    @property
    def capabilities(self):
        return PluginCapabilities(commands=True)

    def register_commands(self):
        return [MockCommand()]
""")

        manager.discover_and_load()

        # Check commands were registered
        commands = manager.registry.get_commands()
        assert "commands-plugin:mock-cmd" in commands

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))

    def test_plugin_with_hooks(
        self, manager: PluginManager, tmp_path: Path
    ) -> None:
        """Test loading plugin that registers hooks."""
        plugin_dir = tmp_path / "user_plugins" / "hooks-plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.yaml").write_text("""
name: hooks-plugin
version: 1.0.0
description: Plugin with hooks
entry_point: hooks_plugin:HooksPlugin
capabilities:
  hooks: true
""")

        (plugin_dir / "hooks_plugin.py").write_text("""
from code_forge.plugins.base import Plugin, PluginMetadata, PluginCapabilities

class HooksPlugin(Plugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="hooks-plugin",
            version="1.0.0",
            description="Plugin with hooks",
        )

    @property
    def capabilities(self):
        return PluginCapabilities(hooks=True)

    def register_hooks(self):
        def before_handler():
            pass
        def after_handler():
            pass
        return {
            "before_execute": [before_handler],
            "after_execute": [after_handler],
        }
""")

        manager.discover_and_load()

        # Check hooks were registered
        hooks = manager.registry.get_hooks("before_execute")
        assert len(hooks) == 1
        hooks = manager.registry.get_hooks("after_execute")
        assert len(hooks) == 1

        # Cleanup
        if str(plugin_dir) in sys.path:
            sys.path.remove(str(plugin_dir))
