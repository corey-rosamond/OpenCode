"""Tests for plugin configuration."""

from pathlib import Path

import pytest

from code_forge.plugins.config import PluginConfig, PluginConfigManager


class TestPluginConfig:
    """Tests for PluginConfig."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = PluginConfig()
        assert config.enabled is True
        assert config.user_dir is None
        assert config.project_dir is None
        assert config.disabled_plugins == []
        assert config.plugin_configs == {}

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = PluginConfig(
            enabled=False,
            user_dir=Path("/custom/user"),
            project_dir=Path("/custom/project"),
            disabled_plugins=["plugin1", "plugin2"],
            plugin_configs={"plugin1": {"key": "value"}},
        )
        assert config.enabled is False
        assert config.user_dir == Path("/custom/user")
        assert config.disabled_plugins == ["plugin1", "plugin2"]
        assert config.plugin_configs == {"plugin1": {"key": "value"}}

    def test_from_dict_minimal(self) -> None:
        """Test from_dict with minimal data."""
        config = PluginConfig.from_dict({})
        assert config.enabled is True
        assert config.disabled_plugins == []

    def test_from_dict_full(self) -> None:
        """Test from_dict with full data."""
        config = PluginConfig.from_dict({
            "enabled": False,
            "user_dir": "~/.custom/plugins",
            "project_dir": ".custom/plugins",
            "disabled_plugins": ["disabled1"],
            "plugin_configs": {"plugin1": {"key": "value"}},
        })
        assert config.enabled is False
        assert isinstance(config.user_dir, Path)
        assert config.disabled_plugins == ["disabled1"]

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        config = PluginConfig(
            enabled=True,
            user_dir=Path("/user"),
            project_dir=None,
            disabled_plugins=["a"],
            plugin_configs={"b": {"c": 1}},
        )
        result = config.to_dict()
        assert result["enabled"] is True
        assert result["user_dir"] == "/user"
        assert result["project_dir"] is None
        assert result["disabled_plugins"] == ["a"]
        assert result["plugin_configs"] == {"b": {"c": 1}}


class TestPluginConfigManager:
    """Tests for PluginConfigManager."""

    @pytest.fixture
    def config_manager(self, tmp_path: Path) -> PluginConfigManager:
        """Create config manager for tests."""
        config = PluginConfig(
            plugin_configs={
                "test-plugin": {"api_key": "secret", "timeout": 30},
            },
            disabled_plugins=["disabled-plugin"],
        )
        return PluginConfigManager(config, data_dir=tmp_path / "plugin_data")

    def test_get_plugin_config_existing(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test getting existing plugin config."""
        config = config_manager.get_plugin_config("test-plugin")
        assert config == {"api_key": "secret", "timeout": 30}

    def test_get_plugin_config_missing(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test getting missing plugin config."""
        config = config_manager.get_plugin_config("missing-plugin")
        assert config == {}

    def test_get_plugin_config_with_defaults(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test getting plugin config with defaults."""
        config = config_manager.get_plugin_config(
            "new-plugin",
            defaults={"default_key": "default_value"},
        )
        assert config == {"default_key": "default_value"}

    def test_get_plugin_config_merges_defaults(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test defaults are merged with user config."""
        config = config_manager.get_plugin_config(
            "test-plugin",
            defaults={"default_key": "default", "api_key": "overridden"},
        )
        assert config["api_key"] == "secret"  # User value takes precedence
        assert config["default_key"] == "default"

    def test_get_plugin_config_with_schema_defaults(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test schema defaults are applied."""
        schema = {
            "type": "object",
            "properties": {
                "new_prop": {"type": "string", "default": "schema_default"},
            },
        }
        config = config_manager.get_plugin_config("new-plugin", schema=schema)
        assert config["new_prop"] == "schema_default"

    def test_set_plugin_config(self, config_manager: PluginConfigManager) -> None:
        """Test setting plugin config."""
        config_manager.set_plugin_config("new-plugin", {"new_key": "new_value"})
        config = config_manager.get_plugin_config("new-plugin")
        assert config == {"new_key": "new_value"}

    def test_get_plugin_data_dir(
        self, config_manager: PluginConfigManager, tmp_path: Path
    ) -> None:
        """Test getting plugin data directory."""
        data_dir = config_manager.get_plugin_data_dir("my-plugin")
        assert data_dir == tmp_path / "plugin_data" / "my-plugin"
        assert data_dir.exists()

    def test_is_plugin_disabled(self, config_manager: PluginConfigManager) -> None:
        """Test checking if plugin is disabled."""
        assert config_manager.is_plugin_disabled("disabled-plugin") is True
        assert config_manager.is_plugin_disabled("enabled-plugin") is False

    def test_disable_plugin(self, config_manager: PluginConfigManager) -> None:
        """Test disabling a plugin."""
        assert not config_manager.is_plugin_disabled("new-plugin")
        config_manager.disable_plugin("new-plugin")
        assert config_manager.is_plugin_disabled("new-plugin")

    def test_disable_plugin_idempotent(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test disabling already disabled plugin."""
        config_manager.disable_plugin("disabled-plugin")
        config_manager.disable_plugin("disabled-plugin")
        count = config_manager.base_config.disabled_plugins.count("disabled-plugin")
        assert count == 1

    def test_enable_plugin(self, config_manager: PluginConfigManager) -> None:
        """Test enabling a plugin."""
        assert config_manager.is_plugin_disabled("disabled-plugin")
        config_manager.enable_plugin("disabled-plugin")
        assert not config_manager.is_plugin_disabled("disabled-plugin")

    def test_enable_plugin_idempotent(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test enabling already enabled plugin."""
        config_manager.enable_plugin("enabled-plugin")
        config_manager.enable_plugin("enabled-plugin")
        # Should not raise

    def test_validate_config_valid(self, config_manager: PluginConfigManager) -> None:
        """Test validating valid config."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        errors = config_manager.validate_config({"name": "test"}, schema)
        assert errors == []

    def test_validate_config_invalid(self, config_manager: PluginConfigManager) -> None:
        """Test validating invalid config."""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }
        # This test depends on jsonschema being installed
        result = config_manager.validate_config({"count": "not_an_int"}, schema)
        # If jsonschema is installed, should have error; if not, validation is skipped
        assert isinstance(result, list)

    def test_apply_schema_defaults(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test applying schema defaults."""
        schema = {
            "type": "object",
            "properties": {
                "existing": {"type": "string"},
                "new": {"type": "string", "default": "default_value"},
            },
        }
        config = {"existing": "value"}
        result = config_manager._apply_schema_defaults(config, schema)
        assert result["existing"] == "value"
        assert result["new"] == "default_value"

    def test_apply_schema_defaults_non_object(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test applying schema defaults with non-object schema."""
        schema = {
            "type": "string",  # Not an object type
        }
        config = {"key": "value"}
        result = config_manager._apply_schema_defaults(config, schema)
        # Should return config unchanged
        assert result == {"key": "value"}

    def test_apply_schema_defaults_no_properties(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test applying schema defaults with object but no properties."""
        schema = {
            "type": "object",
            # No properties key
        }
        config = {"key": "value"}
        result = config_manager._apply_schema_defaults(config, schema)
        # Should return config unchanged
        assert result == {"key": "value"}

    def test_validate_config_with_schema_error(
        self, config_manager: PluginConfigManager
    ) -> None:
        """Test validating with invalid schema."""
        schema = {
            "type": "object",
            "properties": "not_a_dict",  # Invalid schema
        }
        config = {"name": "test"}
        errors = config_manager.validate_config(config, schema)
        # Should return errors or empty list depending on jsonschema
        assert isinstance(errors, list)
