"""Tests for skill parser."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from code_forge.skills.base import SkillDefinition
from code_forge.skills.parser import (
    ParseResult,
    SkillParseError,
    SkillParser,
)


class TestSkillParser:
    """Tests for SkillParser."""

    @pytest.fixture
    def parser(self) -> SkillParser:
        """Create parser instance."""
        return SkillParser()

    def test_parse_yaml_valid(self, parser: SkillParser) -> None:
        """Test parsing valid YAML."""
        content = """
name: test-skill
description: A test skill
prompt: You are a test assistant.
tools:
  - read
  - write
tags:
  - testing
"""
        result = parser.parse_yaml(content)
        assert result.errors == []
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.metadata.name == "test-skill"
        assert result.definition.metadata.description == "A test skill"
        assert result.definition.prompt == "You are a test assistant."
        assert result.definition.tools == ["read", "write"]
        assert result.definition.metadata.tags == ["testing"]

    def test_parse_yaml_missing_name(self, parser: SkillParser) -> None:
        """Test parsing YAML with missing name."""
        content = """
description: A test skill
prompt: Test
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "name" in result.errors[0].lower()
        assert result.definition is None

    def test_parse_yaml_missing_description(self, parser: SkillParser) -> None:
        """Test parsing YAML with missing description."""
        content = """
name: test
prompt: Test
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "description" in result.errors[0].lower()

    def test_parse_yaml_invalid_syntax(self, parser: SkillParser) -> None:
        """Test parsing invalid YAML syntax."""
        content = """
name: test
  invalid: indentation
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "yaml" in result.errors[0].lower()

    def test_parse_yaml_not_mapping(self, parser: SkillParser) -> None:
        """Test parsing YAML that is not a mapping."""
        content = """
- item1
- item2
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "mapping" in result.errors[0].lower()

    def test_parse_yaml_with_config(self, parser: SkillParser) -> None:
        """Test parsing YAML with config options."""
        content = """
name: test
description: Test
prompt: Test
config:
  - name: format
    type: choice
    choices:
      - text
      - json
    default: text
    description: Output format
"""
        result = parser.parse_yaml(content)
        assert result.errors == []
        assert isinstance(result.definition, SkillDefinition)
        assert len(result.definition.config) == 1
        assert result.definition.config[0].name == "format"
        assert result.definition.config[0].type == "choice"
        assert result.definition.config[0].choices == ["text", "json"]

    def test_parse_yaml_with_metadata(self, parser: SkillParser) -> None:
        """Test parsing YAML with all metadata fields."""
        content = """
name: test
description: Test skill
author: Test Author
version: 2.0.0
aliases:
  - t
  - tst
examples:
  - Example usage
prompt: Test
"""
        result = parser.parse_yaml(content)
        assert result.errors == []
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.metadata.author == "Test Author"
        assert result.definition.metadata.version == "2.0.0"
        assert result.definition.metadata.aliases == ["t", "tst"]
        assert result.definition.metadata.examples == ["Example usage"]

    def test_parse_yaml_source_path(self, parser: SkillParser) -> None:
        """Test that source path is set."""
        content = """
name: test
description: Test
prompt: Test
"""
        result = parser.parse_yaml(content, "/path/to/skill.yaml")
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.source_path == "/path/to/skill.yaml"

    def test_parse_markdown_valid(self, parser: SkillParser) -> None:
        """Test parsing valid Markdown with frontmatter."""
        content = """---
name: md-skill
description: Markdown skill
tools:
  - read
---

You are specialized in markdown processing.

Handle markdown files carefully.
"""
        result = parser.parse_markdown(content)
        assert result.errors == []
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.metadata.name == "md-skill"
        assert "markdown processing" in result.definition.prompt

    def test_parse_markdown_no_frontmatter(self, parser: SkillParser) -> None:
        """Test parsing Markdown without frontmatter."""
        content = """
# Just Markdown

No frontmatter here.
"""
        result = parser.parse_markdown(content)
        assert len(result.errors) > 0
        assert "frontmatter" in result.errors[0].lower()

    def test_parse_markdown_empty_frontmatter(self, parser: SkillParser) -> None:
        """Test parsing Markdown with empty frontmatter."""
        content = """---
---

Some content.
"""
        result = parser.parse_markdown(content)
        assert len(result.errors) > 0  # Missing required fields

    def test_parse_markdown_prompt_in_frontmatter(self, parser: SkillParser) -> None:
        """Test that frontmatter prompt takes precedence."""
        content = """---
name: test
description: Test
prompt: Frontmatter prompt
---

Body content.
"""
        result = parser.parse_markdown(content)
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.prompt == "Frontmatter prompt"

    def test_parse_markdown_prompt_from_body(self, parser: SkillParser) -> None:
        """Test using markdown body as prompt."""
        content = """---
name: test
description: Test
---

Body is the prompt.
"""
        result = parser.parse_markdown(content)
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.prompt == "Body is the prompt."

    def test_parse_file_yaml(self, parser: SkillParser, tmp_path: Path) -> None:
        """Test parsing a YAML file."""
        skill_file = tmp_path / "test.yaml"
        skill_file.write_text("""
name: file-skill
description: From file
prompt: File prompt
""")
        result = parser.parse_file(skill_file)
        assert result.errors == []
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.metadata.name == "file-skill"

    def test_parse_file_md(self, parser: SkillParser, tmp_path: Path) -> None:
        """Test parsing a Markdown file."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text("""---
name: md-file-skill
description: From MD file
---

Markdown prompt.
""")
        result = parser.parse_file(skill_file)
        assert result.errors == []
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.metadata.name == "md-file-skill"

    def test_parse_file_unknown_extension(
        self, parser: SkillParser, tmp_path: Path
    ) -> None:
        """Test parsing file with unknown extension."""
        skill_file = tmp_path / "test.txt"
        skill_file.write_text("content")
        result = parser.parse_file(skill_file)
        assert len(result.errors) > 0
        assert "unknown" in result.errors[0].lower()

    def test_parse_method(self, parser: SkillParser) -> None:
        """Test the parse method with extension."""
        content = """
name: test
description: Test
prompt: Test
"""
        result = parser.parse(content, ".yaml")
        assert isinstance(result.definition, SkillDefinition)

        result = parser.parse(content, "yml")  # Without dot
        assert isinstance(result.definition, SkillDefinition)

    def test_validate_invalid_name(self, parser: SkillParser) -> None:
        """Test validation of invalid skill name."""
        content = """
name: InvalidName
description: Test
prompt: Test
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "name" in result.errors[0].lower()

    def test_validate_empty_name(self, parser: SkillParser) -> None:
        """Test validation of empty skill name."""
        content = """
name: ""
description: Test
prompt: Test
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0

    def test_validate_empty_prompt(self, parser: SkillParser) -> None:
        """Test validation of empty prompt."""
        content = """
name: test
description: Test
prompt: ""
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "prompt" in result.errors[0].lower()

    def test_validate_duplicate_config(self, parser: SkillParser) -> None:
        """Test validation of duplicate config options."""
        content = """
name: test
description: Test
prompt: Test
config:
  - name: format
    type: string
  - name: format
    type: string
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "duplicate" in result.errors[0].lower()

    def test_validate_invalid_config_type(self, parser: SkillParser) -> None:
        """Test validation of invalid config type generates warning."""
        content = """
name: test
description: Test
prompt: Test
config:
  - name: option
    type: invalid_type
"""
        result = parser.parse_yaml(content)
        # Invalid types are converted to string with a warning
        assert len(result.warnings) > 0
        assert "unknown config type" in result.warnings[0].lower()
        # Definition should still be created with string type
        assert isinstance(result.definition, SkillDefinition)
        assert result.definition.config[0].type == "string"

    def test_validate_choice_without_choices(self, parser: SkillParser) -> None:
        """Test validation of choice type without choices."""
        content = """
name: test
description: Test
prompt: Test
config:
  - name: option
    type: choice
"""
        result = parser.parse_yaml(content)
        assert len(result.errors) > 0
        assert "choices" in result.errors[0].lower()

    def test_extract_config_warnings(self, parser: SkillParser) -> None:
        """Test that invalid config entries generate warnings."""
        content = """
name: test
description: Test
prompt: Test
config:
  - name: valid
    type: string
  - invalid_entry
"""
        result = parser.parse_yaml(content)
        assert len(result.warnings) > 0

    def test_unknown_config_type_warning(self, parser: SkillParser) -> None:
        """Test warning for unknown config type."""
        content = """
name: test
description: Test
prompt: Test
config:
  - name: option
    type: unknown_type
"""
        result = parser.parse_yaml(content)
        # Should have warning about unknown type and error about invalid type
        assert len(result.errors) > 0 or len(result.warnings) > 0

    def test_parse_file_read_error(
        self, parser: SkillParser, tmp_path: Path
    ) -> None:
        """Test handling file read error."""
        nonexistent = tmp_path / "nonexistent.yaml"
        result = parser.parse_file(nonexistent)
        assert len(result.errors) > 0
        assert "read" in result.errors[0].lower() or "no such file" in result.errors[0].lower()
