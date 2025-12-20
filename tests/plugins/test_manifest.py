"""Tests for plugin manifest parsing."""

from pathlib import Path

import pytest

from code_forge.plugins.exceptions import PluginManifestError
from code_forge.plugins.manifest import ManifestParser, PluginManifest


class TestPluginManifest:
    """Tests for PluginManifest."""

    def test_from_yaml(self, tmp_path: Path) -> None:
        """Test loading manifest from YAML."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test-plugin
version: 1.0.0
description: A test plugin
entry_point: test_plugin:TestPlugin
author: Test Author
capabilities:
  tools: true
  commands: true
""")
        manifest = PluginManifest.from_yaml(manifest_path)
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "A test plugin"
        assert manifest.entry_point == "test_plugin:TestPlugin"
        assert manifest.metadata.author == "Test Author"
        assert manifest.capabilities.tools is True
        assert manifest.capabilities.commands is True
        assert manifest.capabilities.hooks is False

    def test_from_yaml_minimal(self, tmp_path: Path) -> None:
        """Test loading minimal manifest from YAML."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: minimal
version: 0.1.0
description: Minimal plugin
entry_point: minimal:Plugin
""")
        manifest = PluginManifest.from_yaml(manifest_path)
        assert manifest.name == "minimal"
        assert manifest.version == "0.1.0"
        assert manifest.capabilities.tools is False

    def test_from_yaml_not_found(self, tmp_path: Path) -> None:
        """Test loading from non-existent file."""
        manifest_path = tmp_path / "missing.yaml"
        with pytest.raises(PluginManifestError, match="Manifest not found"):
            PluginManifest.from_yaml(manifest_path)

    def test_from_yaml_invalid(self, tmp_path: Path) -> None:
        """Test loading invalid YAML."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("invalid: yaml: :")
        with pytest.raises(PluginManifestError, match="Invalid YAML"):
            PluginManifest.from_yaml(manifest_path)

    def test_from_yaml_empty(self, tmp_path: Path) -> None:
        """Test loading empty YAML file."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("")
        with pytest.raises(PluginManifestError, match="Empty manifest"):
            PluginManifest.from_yaml(manifest_path)

    def test_from_yaml_missing_required(self, tmp_path: Path) -> None:
        """Test loading YAML missing required field."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test
version: 1.0.0
# Missing description and entry_point
""")
        with pytest.raises(PluginManifestError, match="Missing required field"):
            PluginManifest.from_yaml(manifest_path)

    def test_from_pyproject(self, tmp_path: Path) -> None:
        """Test loading manifest from pyproject.toml."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text("""
[tool.forge.plugin]
name = "pyproject-plugin"
version = "2.0.0"
description = "A pyproject plugin"
entry_point = "pyproject_plugin:Plugin"
author = "Pyproject Author"

[tool.forge.plugin.capabilities]
tools = true
""")
        manifest = PluginManifest.from_pyproject(pyproject_path)
        assert manifest.name == "pyproject-plugin"
        assert manifest.version == "2.0.0"
        assert manifest.metadata.author == "Pyproject Author"
        assert manifest.capabilities.tools is True

    def test_from_pyproject_not_found(self, tmp_path: Path) -> None:
        """Test loading from non-existent pyproject.toml."""
        pyproject_path = tmp_path / "pyproject.toml"
        with pytest.raises(PluginManifestError, match="not found"):
            PluginManifest.from_pyproject(pyproject_path)

    def test_from_pyproject_no_plugin_section(self, tmp_path: Path) -> None:
        """Test loading pyproject.toml without plugin section."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text("""
[tool.other]
key = "value"
""")
        with pytest.raises(PluginManifestError, match=r"No \[tool.forge.plugin\]"):
            PluginManifest.from_pyproject(pyproject_path)

    def test_from_dict_with_dependencies(self, tmp_path: Path) -> None:
        """Test manifest with dependencies."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: deps-plugin
version: 1.0.0
description: Plugin with deps
entry_point: deps:Plugin
dependencies:
  - requests>=2.0
  - numpy
""")
        manifest = PluginManifest.from_yaml(manifest_path)
        assert manifest.dependencies == ["requests>=2.0", "numpy"]

    def test_from_dict_with_config_schema(self, tmp_path: Path) -> None:
        """Test manifest with config schema."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: config-plugin
version: 1.0.0
description: Plugin with config
entry_point: config:Plugin
config:
  schema:
    type: object
    properties:
      api_key:
        type: string
""")
        manifest = PluginManifest.from_yaml(manifest_path)
        assert isinstance(manifest.config_schema, dict)
        assert manifest.config_schema["type"] == "object"

    def test_path_is_set(self, tmp_path: Path) -> None:
        """Test path is set correctly."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test
version: 1.0.0
description: Test
entry_point: test:Plugin
""")
        manifest = PluginManifest.from_yaml(manifest_path)
        assert manifest.path == tmp_path


class TestManifestParser:
    """Tests for ManifestParser."""

    def test_manifest_files_constant(self) -> None:
        """Test MANIFEST_FILES constant."""
        parser = ManifestParser()
        assert "plugin.yaml" in parser.MANIFEST_FILES
        assert "plugin.yml" in parser.MANIFEST_FILES
        assert "pyproject.toml" in parser.MANIFEST_FILES

    def test_find_manifest_yaml(self, tmp_path: Path) -> None:
        """Test finding plugin.yaml."""
        (tmp_path / "plugin.yaml").write_text("name: test")
        parser = ManifestParser()
        result = parser.find_manifest(tmp_path)
        assert result == tmp_path / "plugin.yaml"

    def test_find_manifest_yml(self, tmp_path: Path) -> None:
        """Test finding plugin.yml."""
        (tmp_path / "plugin.yml").write_text("name: test")
        parser = ManifestParser()
        result = parser.find_manifest(tmp_path)
        assert result == tmp_path / "plugin.yml"

    def test_find_manifest_pyproject(self, tmp_path: Path) -> None:
        """Test finding pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[tool.forge.plugin]")
        parser = ManifestParser()
        result = parser.find_manifest(tmp_path)
        assert result == tmp_path / "pyproject.toml"

    def test_find_manifest_priority(self, tmp_path: Path) -> None:
        """Test manifest priority (yaml > yml > toml)."""
        (tmp_path / "plugin.yaml").write_text("name: yaml")
        (tmp_path / "plugin.yml").write_text("name: yml")
        (tmp_path / "pyproject.toml").write_text("[tool.forge.plugin]")
        parser = ManifestParser()
        result = parser.find_manifest(tmp_path)
        assert result == tmp_path / "plugin.yaml"

    def test_find_manifest_not_found(self, tmp_path: Path) -> None:
        """Test finding manifest when none exists."""
        parser = ManifestParser()
        result = parser.find_manifest(tmp_path)
        assert result is None

    def test_parse_yaml(self, tmp_path: Path) -> None:
        """Test parsing YAML manifest."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test
version: 1.0.0
description: Test
entry_point: test:Plugin
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        assert manifest.name == "test"

    def test_parse_yml(self, tmp_path: Path) -> None:
        """Test parsing YML manifest."""
        manifest_path = tmp_path / "plugin.yml"
        manifest_path.write_text("""
name: test
version: 1.0.0
description: Test
entry_point: test:Plugin
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        assert manifest.name == "test"

    def test_parse_unknown_type(self, tmp_path: Path) -> None:
        """Test parsing unknown manifest type."""
        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text("{}")
        parser = ManifestParser()
        with pytest.raises(PluginManifestError, match="Unknown manifest type"):
            parser.parse(manifest_path)

    def test_validate_valid_manifest(self, tmp_path: Path) -> None:
        """Test validating valid manifest."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: valid-plugin
version: 1.0.0
description: Valid
entry_point: valid:Plugin
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        errors = parser.validate(manifest)
        assert errors == []

    def test_validate_invalid_name(self, tmp_path: Path) -> None:
        """Test validating manifest with invalid name."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: 123invalid
version: 1.0.0
description: Test
entry_point: test:Plugin
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        errors = parser.validate(manifest)
        assert len(errors) == 1
        assert "alphanumeric" in errors[0]

    def test_validate_invalid_version(self, tmp_path: Path) -> None:
        """Test validating manifest with invalid version."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test
version: invalid
description: Test
entry_point: test:Plugin
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        errors = parser.validate(manifest)
        assert len(errors) == 1
        assert "version" in errors[0].lower()

    def test_validate_invalid_entry_point(self, tmp_path: Path) -> None:
        """Test validating manifest with invalid entry point."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test
version: 1.0.0
description: Test
entry_point: invalid_format
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        errors = parser.validate(manifest)
        assert len(errors) == 1
        assert "module:class" in errors[0]

    def test_validate_semver_with_prerelease(self, tmp_path: Path) -> None:
        """Test version with pre-release suffix is valid."""
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text("""
name: test
version: 1.0.0-beta.1
description: Test
entry_point: test:Plugin
""")
        parser = ManifestParser()
        manifest = parser.parse(manifest_path)
        errors = parser.validate(manifest)
        assert errors == []

    def test_valid_plugin_names(self) -> None:
        """Test valid plugin names."""
        parser = ManifestParser()
        assert parser._is_valid_name("my-plugin")
        assert parser._is_valid_name("my_plugin")
        assert parser._is_valid_name("MyPlugin")
        assert parser._is_valid_name("plugin123")

    def test_invalid_plugin_names(self) -> None:
        """Test invalid plugin names."""
        parser = ManifestParser()
        assert not parser._is_valid_name("123plugin")  # starts with number
        assert not parser._is_valid_name("my plugin")  # contains space
        assert not parser._is_valid_name("my.plugin")  # contains dot
