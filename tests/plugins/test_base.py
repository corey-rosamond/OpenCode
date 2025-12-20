"""Tests for plugin base classes."""

import logging
from pathlib import Path
from typing import Any

import pytest

from code_forge.plugins.base import (
    Plugin,
    PluginCapabilities,
    PluginContext,
    PluginMetadata,
)


class TestPluginMetadata:
    """Tests for PluginMetadata."""

    def test_required_fields(self) -> None:
        """Test metadata with required fields only."""
        meta = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
        )
        assert meta.name == "test-plugin"
        assert meta.version == "1.0.0"
        assert meta.description == "Test plugin"
        assert meta.author is None
        assert meta.email is None
        assert meta.license is None
        assert meta.homepage is None
        assert meta.repository is None
        assert meta.keywords == []
        assert meta.forge_version is None

    def test_all_fields(self) -> None:
        """Test metadata with all fields."""
        meta = PluginMetadata(
            name="full-plugin",
            version="2.0.0",
            description="Full plugin",
            author="John Doe",
            email="john@example.com",
            license="MIT",
            homepage="https://example.com",
            repository="https://github.com/example/plugin",
            keywords=["test", "plugin"],
            forge_version=">=1.0.0",
        )
        assert meta.author == "John Doe"
        assert meta.email == "john@example.com"
        assert meta.license == "MIT"
        assert meta.homepage == "https://example.com"
        assert meta.repository == "https://github.com/example/plugin"
        assert meta.keywords == ["test", "plugin"]
        assert meta.forge_version == ">=1.0.0"

    def test_to_dict(self) -> None:
        """Test metadata to dict conversion."""
        meta = PluginMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            author="Author",
            keywords=["a", "b"],
        )
        result = meta.to_dict()
        assert result["name"] == "test"
        assert result["version"] == "1.0.0"
        assert result["author"] == "Author"
        assert result["keywords"] == ["a", "b"]


class TestPluginCapabilities:
    """Tests for PluginCapabilities."""

    def test_defaults(self) -> None:
        """Test default capabilities."""
        caps = PluginCapabilities()
        assert caps.tools is False
        assert caps.commands is False
        assert caps.hooks is False
        assert caps.subagents is False
        assert caps.skills is False
        assert caps.system_access is False

    def test_custom_capabilities(self) -> None:
        """Test custom capabilities."""
        caps = PluginCapabilities(
            tools=True,
            commands=True,
            hooks=False,
        )
        assert caps.tools is True
        assert caps.commands is True
        assert caps.hooks is False

    def test_to_dict(self) -> None:
        """Test capabilities to dict conversion."""
        caps = PluginCapabilities(tools=True, commands=True)
        result = caps.to_dict()
        assert result["tools"] is True
        assert result["commands"] is True
        assert result["hooks"] is False


class TestPluginContext:
    """Tests for PluginContext."""

    def test_context_creation(self, tmp_path: Path) -> None:
        """Test context creation."""
        logger = logging.getLogger("test")
        ctx = PluginContext(
            plugin_id="test-plugin",
            data_dir=tmp_path / "data",
            config={"key": "value"},
            logger=logger,
        )
        assert ctx.plugin_id == "test-plugin"
        assert ctx.data_dir == tmp_path / "data"
        assert ctx.config == {"key": "value"}
        assert ctx.logger is logger

    def test_get_config(self, tmp_path: Path) -> None:
        """Test get_config method."""
        ctx = PluginContext(
            plugin_id="test",
            data_dir=tmp_path,
            config={"key": "value", "nested": {"a": 1}},
            logger=logging.getLogger("test"),
        )
        assert ctx.get_config("key") == "value"
        assert ctx.get_config("nested") == {"a": 1}
        assert ctx.get_config("missing") is None
        assert ctx.get_config("missing", "default") == "default"

    def test_ensure_data_dir_creates_directory(self, tmp_path: Path) -> None:
        """Test ensure_data_dir creates directory."""
        data_dir = tmp_path / "plugin_data" / "my_plugin"
        ctx = PluginContext(
            plugin_id="test",
            data_dir=data_dir,
            config={},
            logger=logging.getLogger("test"),
        )
        assert not data_dir.exists()
        result = ctx.ensure_data_dir()
        assert data_dir.exists()
        assert result == data_dir


class TestPlugin:
    """Tests for Plugin ABC."""

    def test_concrete_plugin(self) -> None:
        """Test concrete plugin implementation."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-plugin",
                    version="1.0.0",
                    description="My plugin",
                )

        plugin = MyPlugin()
        assert plugin.metadata.name == "my-plugin"
        assert plugin.metadata.version == "1.0.0"

    def test_default_capabilities(self) -> None:
        """Test default capabilities."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

        plugin = MyPlugin()
        caps = plugin.capabilities
        assert caps.tools is False
        assert caps.commands is False

    def test_custom_capabilities(self) -> None:
        """Test custom capabilities."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

            @property
            def capabilities(self) -> PluginCapabilities:
                return PluginCapabilities(tools=True)

        plugin = MyPlugin()
        assert plugin.capabilities.tools is True

    def test_context_not_set_raises(self) -> None:
        """Test accessing context before set raises."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

        plugin = MyPlugin()
        with pytest.raises(RuntimeError, match="Plugin not initialized"):
            _ = plugin.context

    def test_set_context(self, tmp_path: Path) -> None:
        """Test setting context."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

        plugin = MyPlugin()
        ctx = PluginContext(
            plugin_id="test",
            data_dir=tmp_path,
            config={},
            logger=logging.getLogger("test"),
        )
        plugin.set_context(ctx)
        assert plugin.context is ctx

    def test_lifecycle_hooks(self) -> None:
        """Test lifecycle hooks can be called."""
        calls: list[str] = []

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

            def on_load(self) -> None:
                calls.append("load")

            def on_activate(self) -> None:
                calls.append("activate")

            def on_deactivate(self) -> None:
                calls.append("deactivate")

            def on_unload(self) -> None:
                calls.append("unload")

        plugin = MyPlugin()
        plugin.on_load()
        plugin.on_activate()
        plugin.on_deactivate()
        plugin.on_unload()
        assert calls == ["load", "activate", "deactivate", "unload"]

    def test_default_register_methods(self) -> None:
        """Test default register methods return empty lists."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

        plugin = MyPlugin()
        assert plugin.register_tools() == []
        assert plugin.register_commands() == []
        assert plugin.register_hooks() == {}

    def test_get_config_schema_default(self) -> None:
        """Test default config schema is None."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

        plugin = MyPlugin()
        assert plugin.get_config_schema() is None

    def test_custom_config_schema(self) -> None:
        """Test custom config schema."""

        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test",
                )

            def get_config_schema(self) -> dict[str, Any] | None:
                return {"type": "object", "properties": {"key": {"type": "string"}}}

        plugin = MyPlugin()
        schema = plugin.get_config_schema()
        assert isinstance(schema, dict)
        assert schema["type"] == "object"
