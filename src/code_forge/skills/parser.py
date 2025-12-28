"""
Skill file parser.

Parses skill definitions from YAML and Markdown files.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import yaml

from .base import SkillConfig, SkillDefinition, SkillMetadata


class SkillParseError(Exception):
    """Error parsing skill file."""

    pass


@dataclass
class ParseResult:
    """Result of parsing a skill file."""

    definition: SkillDefinition | None
    errors: list[str]
    warnings: list[str]


class SkillParser:
    """Parses skill definition files."""

    # Required fields in skill definition
    REQUIRED_FIELDS: ClassVar[list[str]] = ["name", "description"]

    # Valid config types
    VALID_CONFIG_TYPES: ClassVar[set[str]] = {"string", "int", "bool", "choice"}

    def parse_file(self, path: Path) -> ParseResult:
        """Parse a skill file.

        Args:
            path: Path to skill file

        Returns:
            ParseResult with definition or errors
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            return ParseResult(
                definition=None,
                errors=[f"Failed to read file: {e}"],
                warnings=[],
            )

        if path.suffix in (".yaml", ".yml"):
            return self.parse_yaml(content, str(path))
        elif path.suffix == ".md":
            return self.parse_markdown(content, str(path))
        else:
            return ParseResult(
                definition=None,
                errors=[f"Unknown file type: {path.suffix}"],
                warnings=[],
            )

    def parse_yaml(self, content: str, source_path: str = "") -> ParseResult:
        """Parse YAML skill file.

        Args:
            content: YAML content
            source_path: Source file path

        Returns:
            ParseResult
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return ParseResult(
                definition=None,
                errors=[f"YAML parse error: {e}"],
                warnings=[],
            )

        if not isinstance(data, dict):
            return ParseResult(
                definition=None,
                errors=["Skill file must be a YAML mapping"],
                warnings=[],
            )

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")

        if errors:
            return ParseResult(None, errors, warnings)

        # Parse metadata
        metadata = SkillMetadata(
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=str(data.get("version", "1.0.0")),
            tags=data.get("tags", []),
            aliases=data.get("aliases", []),
            examples=data.get("examples", []),
        )

        # Parse config options
        config = self._extract_config(data.get("config", []), warnings)

        # Build definition
        definition = SkillDefinition(
            metadata=metadata,
            prompt=data.get("prompt", ""),
            tools=data.get("tools", []),
            config=config,
            dependencies=data.get("dependencies", []),
            source_path=source_path if source_path else None,
        )

        # Validate
        validation_errors = self.validate(definition)
        errors.extend(validation_errors)

        if errors:
            return ParseResult(None, errors, warnings)

        return ParseResult(definition, [], warnings)

    def parse_markdown(self, content: str, source_path: str = "") -> ParseResult:
        """Parse Markdown skill file with YAML frontmatter.

        Args:
            content: Markdown content
            source_path: Source file path

        Returns:
            ParseResult
        """
        # Extract YAML frontmatter
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )

        if not frontmatter_match:
            return ParseResult(
                definition=None,
                errors=["Markdown skill must have YAML frontmatter"],
                warnings=[],
            )

        yaml_content = frontmatter_match.group(1)
        markdown_body = frontmatter_match.group(2).strip()

        # Parse YAML part without validation first
        errors: list[str] = []
        warnings: list[str] = []

        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return ParseResult(
                definition=None,
                errors=[f"YAML parse error: {e}"],
                warnings=[],
            )

        if not isinstance(data, dict):
            return ParseResult(
                definition=None,
                errors=["Skill file must be a YAML mapping"],
                warnings=[],
            )

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")

        if errors:
            return ParseResult(None, errors, warnings)

        # Parse metadata
        metadata = SkillMetadata(
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=str(data.get("version", "1.0.0")),
            tags=data.get("tags", []),
            aliases=data.get("aliases", []),
            examples=data.get("examples", []),
        )

        # Parse config options
        config = self._extract_config(data.get("config", []), warnings)

        # Get prompt - use markdown body if not in frontmatter
        prompt = data.get("prompt", "")
        if not prompt and markdown_body:
            prompt = markdown_body

        # Build definition
        definition = SkillDefinition(
            metadata=metadata,
            prompt=prompt,
            tools=data.get("tools", []),
            config=config,
            dependencies=data.get("dependencies", []),
            source_path=source_path if source_path else None,
        )

        # Validate
        validation_errors = self.validate(definition)
        errors.extend(validation_errors)

        if errors:
            return ParseResult(None, errors, warnings)

        return ParseResult(definition, [], warnings)

    def parse(self, content: str, extension: str, source_path: str = "") -> ParseResult:
        """Parse skill content based on file extension.

        Args:
            content: File content
            extension: File extension (with or without dot)
            source_path: Source file path

        Returns:
            ParseResult
        """
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        if ext in (".yaml", ".yml"):
            return self.parse_yaml(content, source_path)
        elif ext == ".md":
            return self.parse_markdown(content, source_path)
        else:
            return ParseResult(
                definition=None,
                errors=[f"Unknown file type: {extension}"],
                warnings=[],
            )

    def validate(self, definition: SkillDefinition) -> list[str]:
        """Validate skill definition.

        Args:
            definition: Definition to validate

        Returns:
            List of error messages
        """
        errors = []

        # Name validation
        if not definition.metadata.name:
            errors.append("Skill name cannot be empty")
        elif not re.match(r"^[a-z][a-z0-9-]*$", definition.metadata.name):
            errors.append(
                "Skill name must start with letter and contain "
                "only lowercase letters, numbers, and hyphens"
            )

        # Description validation
        if not definition.metadata.description:
            errors.append("Skill description cannot be empty")

        # Prompt validation
        if not definition.prompt:
            errors.append("Skill must have a prompt")

        # Config validation
        config_names: set[str] = set()
        for opt in definition.config:
            if not opt.name:
                errors.append("Config option name cannot be empty")
            elif opt.name in config_names:
                errors.append(f"Duplicate config option: {opt.name}")
            else:
                config_names.add(opt.name)

            if opt.type not in self.VALID_CONFIG_TYPES:
                errors.append(f"Invalid config type: {opt.type}")

            if opt.type == "choice" and not opt.choices:
                errors.append(
                    f"Config '{opt.name}' is type 'choice' but has no choices"
                )

        return errors

    def _extract_config(
        self, config_data: list[Any], warnings: list[str]
    ) -> list[SkillConfig]:
        """Extract config options from parsed data.

        Args:
            config_data: Raw config data from YAML
            warnings: List to append warnings to

        Returns:
            List of SkillConfig objects
        """
        config = []
        for opt_data in config_data:
            if isinstance(opt_data, dict):
                opt_type = opt_data.get("type", "string")
                if opt_type not in self.VALID_CONFIG_TYPES:
                    warnings.append(f"Unknown config type '{opt_type}', using 'string'")
                    opt_type = "string"

                config.append(
                    SkillConfig(
                        name=opt_data.get("name", ""),
                        type=opt_type,
                        default=opt_data.get("default"),
                        description=opt_data.get("description", ""),
                        choices=opt_data.get("choices"),
                        required=opt_data.get("required", False),
                    )
                )
            else:
                warnings.append(f"Ignoring invalid config entry: {opt_data}")

        return config


__all__ = [
    "ParseResult",
    "SkillParseError",
    "SkillParser",
]
