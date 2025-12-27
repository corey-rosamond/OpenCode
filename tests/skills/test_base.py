"""Tests for skills base classes."""

from datetime import datetime
from typing import Any

import pytest

from code_forge.skills.base import (
    Skill,
    SkillConfig,
    SkillDefinition,
    SkillMetadata,
)


class TestSkillConfig:
    """Tests for SkillConfig."""

    def test_create_config(self) -> None:
        """Test creating a config option."""
        config = SkillConfig(name="format", type="string", default="text")
        assert config.name == "format"
        assert config.type == "string"
        assert config.default == "text"
        assert not config.required

    def test_validate_string_success(self) -> None:
        """Test validating a string value."""
        config = SkillConfig(name="name", type="string")
        valid, error = config.validate("test")
        assert valid is True
        assert error == ""

    def test_validate_string_failure(self) -> None:
        """Test validating an invalid string value."""
        config = SkillConfig(name="name", type="string")
        valid, error = config.validate(123)
        assert valid is False
        assert "must be a string" in error

    def test_validate_int_success(self) -> None:
        """Test validating an integer value."""
        config = SkillConfig(name="count", type="int")
        valid, error = config.validate(42)
        assert valid is True
        assert error == ""

    def test_validate_int_failure(self) -> None:
        """Test validating an invalid integer value."""
        config = SkillConfig(name="count", type="int")
        valid, error = config.validate("not an int")
        assert valid is False
        assert "must be an integer" in error

    def test_validate_bool_success(self) -> None:
        """Test validating a boolean value."""
        config = SkillConfig(name="enabled", type="bool")
        valid, error = config.validate(True)
        assert valid is True
        assert error == ""

    def test_validate_bool_failure(self) -> None:
        """Test validating an invalid boolean value."""
        config = SkillConfig(name="enabled", type="bool")
        valid, error = config.validate("yes")
        assert valid is False
        assert "must be a boolean" in error

    def test_validate_choice_success(self) -> None:
        """Test validating a choice value."""
        config = SkillConfig(
            name="format", type="choice", choices=["text", "json", "yaml"]
        )
        valid, error = config.validate("json")
        assert valid is True
        assert error == ""

    def test_validate_choice_failure(self) -> None:
        """Test validating an invalid choice value."""
        config = SkillConfig(
            name="format", type="choice", choices=["text", "json", "yaml"]
        )
        valid, error = config.validate("xml")
        assert valid is False
        assert "must be one of" in error

    def test_validate_required_missing(self) -> None:
        """Test validating a required value that is missing."""
        config = SkillConfig(name="required_field", type="string", required=True)
        valid, error = config.validate(None)
        assert valid is False
        assert "not provided" in error

    def test_validate_optional_missing(self) -> None:
        """Test validating an optional value that is missing."""
        config = SkillConfig(name="optional_field", type="string", required=False)
        valid, error = config.validate(None)
        assert valid is True
        assert error == ""

    def test_to_dict(self) -> None:
        """Test serializing config to dictionary."""
        config = SkillConfig(
            name="format",
            type="choice",
            default="text",
            description="Output format",
            choices=["text", "json"],
            required=True,
        )
        result = config.to_dict()
        assert result["name"] == "format"
        assert result["type"] == "choice"
        assert result["default"] == "text"
        assert result["description"] == "Output format"
        assert result["choices"] == ["text", "json"]
        assert result["required"] is True

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "name": "format",
            "type": "choice",
            "default": "text",
            "choices": ["text", "json"],
        }
        config = SkillConfig.from_dict(data)
        assert config.name == "format"
        assert config.type == "choice"
        assert config.default == "text"
        assert config.choices == ["text", "json"]


class TestSkillMetadata:
    """Tests for SkillMetadata."""

    def test_create_metadata(self) -> None:
        """Test creating skill metadata."""
        metadata = SkillMetadata(
            name="pdf",
            description="Work with PDF documents",
            author="Code-Forge",
            version="1.0.0",
            tags=["documents", "analysis"],
        )
        assert metadata.name == "pdf"
        assert metadata.description == "Work with PDF documents"
        assert metadata.author == "Code-Forge"
        assert "documents" in metadata.tags

    def test_matches_query_name(self) -> None:
        """Test matching by name."""
        metadata = SkillMetadata(name="pdf", description="PDF documents")
        assert metadata.matches_query("pdf") is True
        assert metadata.matches_query("PDF") is True
        assert metadata.matches_query("excel") is False

    def test_matches_query_description(self) -> None:
        """Test matching by description."""
        metadata = SkillMetadata(name="pdf", description="Work with PDF documents")
        assert metadata.matches_query("documents") is True
        assert metadata.matches_query("spreadsheet") is False

    def test_matches_query_tags(self) -> None:
        """Test matching by tags."""
        metadata = SkillMetadata(
            name="pdf", description="PDF", tags=["documents", "analysis"]
        )
        assert metadata.matches_query("analysis") is True
        assert metadata.matches_query("database") is False

    def test_to_dict(self) -> None:
        """Test serializing metadata to dictionary."""
        metadata = SkillMetadata(
            name="pdf",
            description="PDF documents",
            author="Test",
            tags=["doc"],
        )
        result = metadata.to_dict()
        assert result["name"] == "pdf"
        assert result["description"] == "PDF documents"
        assert result["author"] == "Test"
        assert result["tags"] == ["doc"]

    def test_from_dict(self) -> None:
        """Test creating metadata from dictionary."""
        data = {
            "name": "pdf",
            "description": "PDF documents",
            "author": "Test",
            "version": "2.0.0",
            "tags": ["doc"],
        }
        metadata = SkillMetadata.from_dict(data)
        assert metadata.name == "pdf"
        assert metadata.version == "2.0.0"
        assert metadata.tags == ["doc"]


class TestSkillDefinition:
    """Tests for SkillDefinition."""

    def test_create_definition(self) -> None:
        """Test creating a skill definition."""
        metadata = SkillMetadata(name="test", description="Test skill")
        definition = SkillDefinition(
            metadata=metadata,
            prompt="You are a test assistant.",
            tools=["read", "write"],
        )
        assert definition.metadata.name == "test"
        assert definition.prompt == "You are a test assistant."
        assert "read" in definition.tools

    def test_get_config_option(self) -> None:
        """Test getting config option by name."""
        metadata = SkillMetadata(name="test", description="Test")
        config = [
            SkillConfig(name="format", type="string"),
            SkillConfig(name="verbose", type="bool"),
        ]
        definition = SkillDefinition(
            metadata=metadata, prompt="Test", config=config
        )

        opt = definition.get_config_option("format")
        assert isinstance(opt, SkillConfig)
        assert opt.name == "format"

        opt = definition.get_config_option("nonexistent")
        assert opt is None

    def test_validate_config_success(self) -> None:
        """Test validating valid config."""
        metadata = SkillMetadata(name="test", description="Test")
        config = [SkillConfig(name="format", type="string")]
        definition = SkillDefinition(
            metadata=metadata, prompt="Test", config=config
        )

        errors = definition.validate_config({"format": "json"})
        assert errors == []

    def test_validate_config_failure(self) -> None:
        """Test validating invalid config."""
        metadata = SkillMetadata(name="test", description="Test")
        config = [SkillConfig(name="count", type="int", required=True)]
        definition = SkillDefinition(
            metadata=metadata, prompt="Test", config=config
        )

        errors = definition.validate_config({})
        assert len(errors) == 1
        assert "not provided" in errors[0]

    def test_to_dict(self) -> None:
        """Test serializing definition to dictionary."""
        metadata = SkillMetadata(name="test", description="Test")
        definition = SkillDefinition(
            metadata=metadata,
            prompt="Test prompt",
            tools=["read"],
            is_builtin=True,
        )
        result = definition.to_dict()
        assert result["metadata"]["name"] == "test"
        assert result["prompt"] == "Test prompt"
        assert result["tools"] == ["read"]
        assert result["is_builtin"] is True

    def test_from_dict_nested(self) -> None:
        """Test creating definition from nested dictionary."""
        data = {
            "metadata": {
                "name": "test",
                "description": "Test skill",
            },
            "prompt": "Test prompt",
            "tools": ["read"],
        }
        definition = SkillDefinition.from_dict(data)
        assert definition.metadata.name == "test"
        assert definition.prompt == "Test prompt"
        assert definition.tools == ["read"]

    def test_from_dict_flat(self) -> None:
        """Test creating definition from flat dictionary."""
        data = {
            "name": "test",
            "description": "Test skill",
            "prompt": "Test prompt",
            "tools": ["read"],
        }
        definition = SkillDefinition.from_dict(data)
        assert definition.metadata.name == "test"
        assert definition.prompt == "Test prompt"


class TestSkill:
    """Tests for Skill class."""

    def _create_skill(
        self,
        name: str = "test",
        prompt: str = "Test prompt",
        tools: list[str] | None = None,
        config: list[SkillConfig] | None = None,
    ) -> Skill:
        """Helper to create a test skill."""
        metadata = SkillMetadata(name=name, description=f"{name} skill")
        definition = SkillDefinition(
            metadata=metadata,
            prompt=prompt,
            tools=tools or [],
            config=config or [],
        )
        return Skill(definition)

    def test_create_skill(self) -> None:
        """Test creating a skill."""
        skill = self._create_skill()
        assert skill.name == "test"
        assert skill.description == "test skill"
        assert skill.is_active is False

    def test_activate_skill(self) -> None:
        """Test activating a skill."""
        from datetime import datetime
        skill = self._create_skill()
        errors = skill.activate()
        assert errors == []
        assert skill.is_active is True
        assert isinstance(skill._activated_at, datetime)
        assert skill._activated_at is not None

    def test_activate_with_config(self) -> None:
        """Test activating with configuration."""
        config = [SkillConfig(name="format", type="string", default="text")]
        skill = self._create_skill(config=config)
        errors = skill.activate({"format": "json"})
        assert errors == []
        assert skill.get_context()["format"] == "json"

    def test_activate_applies_defaults(self) -> None:
        """Test that activation applies default config values."""
        config = [SkillConfig(name="format", type="string", default="text")]
        skill = self._create_skill(config=config)
        errors = skill.activate({})
        assert errors == []
        assert skill.get_context()["format"] == "text"

    def test_activate_with_invalid_config(self) -> None:
        """Test activation with invalid config."""
        config = [SkillConfig(name="count", type="int", required=True)]
        skill = self._create_skill(config=config)
        errors = skill.activate({})
        assert len(errors) > 0
        assert skill.is_active is False

    def test_deactivate_skill(self) -> None:
        """Test deactivating a skill."""
        skill = self._create_skill()
        skill.activate()
        skill.deactivate()
        assert skill.is_active is False
        assert skill._activated_at is None
        assert skill.get_context() == {}

    def test_get_prompt_simple(self) -> None:
        """Test getting skill prompt."""
        skill = self._create_skill(prompt="You are a helpful assistant.")
        skill.activate()
        assert skill.get_prompt() == "You are a helpful assistant."

    def test_get_prompt_with_variables(self) -> None:
        """Test prompt variable substitution."""
        skill = self._create_skill(prompt="Analyze {{ file_path }}")
        skill.activate({"file_path": "test.pdf"})
        assert skill.get_prompt() == "Analyze test.pdf"

    def test_get_prompt_missing_variable(self) -> None:
        """Test prompt with missing variable."""
        skill = self._create_skill(prompt="Analyze {{ file_path }}")
        skill.activate({})
        # Missing variables are kept as-is
        assert "{{ file_path }}" in skill.get_prompt()

    def test_get_prompt_sanitizes_values(self) -> None:
        """Test that prompt substitution sanitizes values."""
        skill = self._create_skill(prompt="File: {{ name }}")
        skill.activate({"name": "test\x00file"})  # Null byte should be removed
        prompt = skill.get_prompt()
        assert "\x00" not in prompt

    def test_get_tools(self) -> None:
        """Test getting skill tools."""
        skill = self._create_skill(tools=["read", "write", "bash"])
        tools = skill.get_tools()
        assert tools == ["read", "write", "bash"]
        # Verify it's a copy
        tools.append("glob")
        assert skill.get_tools() == ["read", "write", "bash"]

    def test_set_context(self) -> None:
        """Test setting context values."""
        skill = self._create_skill()
        skill.activate()
        skill.set_context("custom_key", "custom_value")
        assert skill.get_context()["custom_key"] == "custom_value"

    def test_to_dict(self) -> None:
        """Test serializing skill state."""
        skill = self._create_skill()
        skill.activate({"key": "value"})
        result = skill.to_dict()
        assert result["name"] == "test"
        assert result["active"] is True
        assert result["context"]["key"] == "value"
        # activated_at is serialized as ISO format string
        assert isinstance(result["activated_at"], str)
        assert result["activated_at"] is not None

    def test_get_help(self) -> None:
        """Test getting help text."""
        metadata = SkillMetadata(
            name="test",
            description="Test skill",
            author="Tester",
            version="1.0.0",
            tags=["testing"],
            examples=["Example 1"],
        )
        config = [SkillConfig(name="format", default="text", description="Output format")]
        definition = SkillDefinition(
            metadata=metadata,
            prompt="Test",
            tools=["read", "write"],
            config=config,
        )
        skill = Skill(definition)
        help_text = skill.get_help()

        assert "# test" in help_text
        assert "Test skill" in help_text
        assert "Author: Tester" in help_text
        assert "Version: 1.0.0" in help_text
        assert "Tags: testing" in help_text
        assert "Required Tools" in help_text
        assert "read, write" in help_text
        assert "Configuration" in help_text
        assert "format" in help_text
        assert "Examples" in help_text
        assert "Example 1" in help_text

    def test_is_builtin(self) -> None:
        """Test is_builtin property."""
        metadata = SkillMetadata(name="test", description="Test")
        definition = SkillDefinition(
            metadata=metadata, prompt="Test", is_builtin=True
        )
        skill = Skill(definition)
        assert skill.is_builtin is True

    def test_tags_property(self) -> None:
        """Test tags property."""
        metadata = SkillMetadata(
            name="test", description="Test", tags=["a", "b"]
        )
        definition = SkillDefinition(metadata=metadata, prompt="Test")
        skill = Skill(definition)
        assert skill.tags == ["a", "b"]
