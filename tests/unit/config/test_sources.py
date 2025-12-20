"""Tests for configuration sources."""

import json
from pathlib import Path

import pytest
import yaml

from code_forge.config.sources import (
    EnvironmentSource,
    JsonFileSource,
    YamlFileSource,
)
from code_forge.core import ConfigError


class TestJsonFileSource:
    """Tests for JsonFileSource."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid JSON file."""
        config_file = tmp_path / "settings.json"
        config_file.write_text('{"model": {"default": "test-model"}}')

        source = JsonFileSource(config_file)
        data = source.load()

        assert data["model"]["default"] == "test-model"

    def test_load_empty_json(self, tmp_path: Path) -> None:
        """Test loading empty JSON file returns empty dict."""
        config_file = tmp_path / "settings.json"
        config_file.write_text("{}")

        source = JsonFileSource(config_file)
        data = source.load()

        assert data == {}

    def test_load_whitespace_only(self, tmp_path: Path) -> None:
        """Test loading whitespace-only file returns empty dict."""
        config_file = tmp_path / "settings.json"
        config_file.write_text("   \n\t  ")

        source = JsonFileSource(config_file)
        data = source.load()

        assert data == {}

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading missing file returns empty dict."""
        config_file = tmp_path / "nonexistent.json"

        source = JsonFileSource(config_file)
        data = source.load()

        assert data == {}

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON raises ConfigError."""
        config_file = tmp_path / "settings.json"
        config_file.write_text('{"broken": }')

        source = JsonFileSource(config_file)
        with pytest.raises(ConfigError) as exc_info:
            source.load()

        assert "Invalid JSON" in str(exc_info.value)

    def test_load_non_object_json(self, tmp_path: Path) -> None:
        """Test loading non-object JSON raises ConfigError."""
        config_file = tmp_path / "settings.json"
        config_file.write_text('["array", "not", "object"]')

        source = JsonFileSource(config_file)
        with pytest.raises(ConfigError) as exc_info:
            source.load()

        assert "root must be object" in str(exc_info.value)

    def test_exists_true(self, tmp_path: Path) -> None:
        """Test exists returns True for existing file."""
        config_file = tmp_path / "settings.json"
        config_file.write_text("{}")

        source = JsonFileSource(config_file)
        assert source.exists() is True

    def test_exists_false_missing(self, tmp_path: Path) -> None:
        """Test exists returns False for missing file."""
        config_file = tmp_path / "nonexistent.json"

        source = JsonFileSource(config_file)
        assert source.exists() is False

    def test_exists_false_directory(self, tmp_path: Path) -> None:
        """Test exists returns False for directory."""
        source = JsonFileSource(tmp_path)
        assert source.exists() is False

    def test_path_property(self, tmp_path: Path) -> None:
        """Test path property returns the file path."""
        config_file = tmp_path / "settings.json"
        source = JsonFileSource(config_file)
        assert source.path == config_file

    def test_load_nested_config(self, tmp_path: Path) -> None:
        """Test loading nested configuration."""
        config_file = tmp_path / "settings.json"
        config_data = {
            "model": {
                "default": "gpt-5",
                "fallback": ["claude-4", "gemini"],
            },
            "display": {
                "theme": "dark",
                "show_tokens": True,
            },
        }
        config_file.write_text(json.dumps(config_data))

        source = JsonFileSource(config_file)
        data = source.load()

        assert data == config_data


class TestYamlFileSource:
    """Tests for YamlFileSource."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Test loading valid YAML file."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("model:\n  default: test-model")

        source = YamlFileSource(config_file)
        data = source.load()

        assert data["model"]["default"] == "test-model"

    def test_load_empty_yaml(self, tmp_path: Path) -> None:
        """Test loading empty YAML file returns empty dict."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("")

        source = YamlFileSource(config_file)
        data = source.load()

        assert data == {}

    def test_load_null_yaml(self, tmp_path: Path) -> None:
        """Test loading YAML with null/None returns empty dict."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("~")  # YAML null

        source = YamlFileSource(config_file)
        data = source.load()

        assert data == {}

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading missing file returns empty dict."""
        config_file = tmp_path / "nonexistent.yaml"

        source = YamlFileSource(config_file)
        data = source.load()

        assert data == {}

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading invalid YAML raises ConfigError."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("invalid: yaml: content:")

        source = YamlFileSource(config_file)
        with pytest.raises(ConfigError) as exc_info:
            source.load()

        assert "Invalid YAML" in str(exc_info.value)

    def test_load_non_mapping_yaml(self, tmp_path: Path) -> None:
        """Test loading non-mapping YAML raises ConfigError."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("- list\n- not\n- mapping")

        source = YamlFileSource(config_file)
        with pytest.raises(ConfigError) as exc_info:
            source.load()

        assert "root must be mapping" in str(exc_info.value)

    def test_exists_true(self, tmp_path: Path) -> None:
        """Test exists returns True for existing file."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("")

        source = YamlFileSource(config_file)
        assert source.exists() is True

    def test_exists_false(self, tmp_path: Path) -> None:
        """Test exists returns False for missing file."""
        config_file = tmp_path / "nonexistent.yaml"

        source = YamlFileSource(config_file)
        assert source.exists() is False

    def test_path_property(self, tmp_path: Path) -> None:
        """Test path property returns the file path."""
        config_file = tmp_path / "settings.yaml"
        source = YamlFileSource(config_file)
        assert source.path == config_file

    def test_load_yml_extension(self, tmp_path: Path) -> None:
        """Test loading .yml file works."""
        config_file = tmp_path / "settings.yml"
        config_file.write_text("model:\n  default: yml-model")

        source = YamlFileSource(config_file)
        data = source.load()

        assert data["model"]["default"] == "yml-model"

    def test_load_nested_config(self, tmp_path: Path) -> None:
        """Test loading nested YAML configuration."""
        config_file = tmp_path / "settings.yaml"
        config_data = {
            "model": {
                "default": "gpt-5",
                "fallback": ["claude-4", "gemini"],
            },
            "display": {
                "theme": "dark",
                "show_tokens": True,
            },
        }
        config_file.write_text(yaml.dump(config_data))

        source = YamlFileSource(config_file)
        data = source.load()

        assert data == config_data


class TestEnvironmentSource:
    """Tests for EnvironmentSource."""

    def test_load_api_key(self) -> None:
        """Test loading API key from environment."""
        environ = {"FORGE_API_KEY": "sk-test-123"}

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["api_key"] == "sk-test-123"

    def test_load_model(self) -> None:
        """Test loading model from environment."""
        environ = {"FORGE_MODEL": "custom-model"}

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["model"]["default"] == "custom-model"

    def test_load_max_tokens(self) -> None:
        """Test loading max_tokens as integer."""
        environ = {"FORGE_MAX_TOKENS": "4096"}

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["model"]["max_tokens"] == 4096

    def test_load_temperature(self) -> None:
        """Test loading temperature as float."""
        environ = {"FORGE_TEMPERATURE": "0.7"}

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["model"]["temperature"] == 0.7

    def test_load_theme(self) -> None:
        """Test loading theme from environment."""
        environ = {"FORGE_THEME": "light"}

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["display"]["theme"] == "light"

    def test_load_vim_mode_true(self) -> None:
        """Test loading vim_mode boolean true."""
        for value in ("true", "1", "yes", "on"):
            environ = {"FORGE_VIM_MODE": value}
            source = EnvironmentSource(environ)
            data = source.load()
            assert data["display"]["vim_mode"] is True

    def test_load_vim_mode_false(self) -> None:
        """Test loading vim_mode boolean false."""
        for value in ("false", "0", "no", "off"):
            environ = {"FORGE_VIM_MODE": value}
            source = EnvironmentSource(environ)
            data = source.load()
            assert data["display"]["vim_mode"] is False

    def test_load_streaming_boolean(self) -> None:
        """Test loading streaming boolean."""
        environ = {"FORGE_STREAMING": "false"}

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["display"]["streaming"] is False

    def test_load_multiple_vars(self) -> None:
        """Test loading multiple environment variables."""
        environ = {
            "FORGE_API_KEY": "sk-123",
            "FORGE_MODEL": "gpt-5",
            "FORGE_THEME": "dark",
        }

        source = EnvironmentSource(environ)
        data = source.load()

        assert data["api_key"] == "sk-123"
        assert data["model"]["default"] == "gpt-5"
        assert data["display"]["theme"] == "dark"

    def test_load_empty_environ(self) -> None:
        """Test loading from empty environment."""
        source = EnvironmentSource({})
        data = source.load()

        assert data == {}

    def test_load_ignores_non_forge_vars(self) -> None:
        """Test non-FORGE_ vars are ignored."""
        environ = {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "OTHER_API_KEY": "ignored",
        }

        source = EnvironmentSource(environ)
        data = source.load()

        assert data == {}

    def test_exists_always_true(self) -> None:
        """Test environment source always exists."""
        source = EnvironmentSource({})
        assert source.exists() is True

    def test_invalid_integer_keeps_string(self) -> None:
        """Test invalid integer value keeps string."""
        environ = {"FORGE_MAX_TOKENS": "not-a-number"}

        source = EnvironmentSource(environ)
        data = source.load()

        # Should keep the string value, validation happens later
        assert data["model"]["max_tokens"] == "not-a-number"

    def test_invalid_float_keeps_string(self) -> None:
        """Test invalid float value keeps string."""
        environ = {"FORGE_TEMPERATURE": "not-a-float"}

        source = EnvironmentSource(environ)
        data = source.load()

        # Should keep the string value, validation happens later
        assert data["model"]["temperature"] == "not-a-float"

    def test_uses_os_environ_by_default(self) -> None:
        """Test default uses os.environ."""
        import os

        # Just verify it doesn't crash with real environ
        source = EnvironmentSource()
        # Access internal environ to verify it's set
        assert isinstance(source._environ, dict)
