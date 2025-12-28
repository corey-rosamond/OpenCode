"""
Base classes for the skills system.

Skills provide domain-specific capabilities that modify
assistant behavior through specialized prompts and tools.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SkillConfig:
    """Configuration option for a skill.

    Attributes:
        name: Option name
        type: Value type (string, int, bool, choice)
        default: Default value
        description: Help text
        choices: Valid choices for 'choice' type
        required: Whether option must be provided
    """

    name: str
    type: str = "string"
    default: Any = None
    description: str = ""
    choices: list[str] | None = None
    required: bool = False

    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate a value against this config.

        Returns:
            (is_valid, error_message)
        """
        if value is None:
            if self.required:
                return False, f"Required option '{self.name}' not provided"
            return True, ""

        if self.type == "string":
            if not isinstance(value, str):
                return False, f"'{self.name}' must be a string"

        elif self.type == "int":
            if not isinstance(value, int):
                return False, f"'{self.name}' must be an integer"

        elif self.type == "bool":
            if not isinstance(value, bool):
                return False, f"'{self.name}' must be a boolean"

        elif self.type == "choice" and self.choices and value not in self.choices:
            return False, f"'{self.name}' must be one of: {self.choices}"

        return True, ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.description:
            result["description"] = self.description
        if self.choices:
            result["choices"] = self.choices
        if self.required:
            result["required"] = self.required
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillConfig":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "string"),
            default=data.get("default"),
            description=data.get("description", ""),
            choices=data.get("choices"),
            required=data.get("required", False),
        )


@dataclass
class SkillMetadata:
    """Metadata for a skill.

    Attributes:
        name: Unique skill identifier
        description: Human-readable description
        author: Skill author
        version: Version string
        tags: Categorization tags
        aliases: Alternative names
        examples: Usage examples
    """

    name: str
    description: str
    author: str = ""
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)

    def matches_query(self, query: str) -> bool:
        """Check if skill matches a search query."""
        query_lower = query.lower()
        if query_lower in self.name.lower():
            return True
        if query_lower in self.description.lower():
            return True
        return any(query_lower in tag.lower() for tag in self.tags)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
        }
        if self.author:
            result["author"] = self.author
        if self.version != "1.0.0":
            result["version"] = self.version
        if self.tags:
            result["tags"] = self.tags
        if self.aliases:
            result["aliases"] = self.aliases
        if self.examples:
            result["examples"] = self.examples
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillMetadata":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=str(data.get("version", "1.0.0")),
            tags=data.get("tags", []),
            aliases=data.get("aliases", []),
            examples=data.get("examples", []),
        )


@dataclass
class SkillDefinition:
    """Complete skill definition.

    Attributes:
        metadata: Skill metadata
        prompt: System prompt addition
        tools: Required tool names
        config: Configuration options
        dependencies: Names of other skills this skill depends on
        source_path: Path to source file
        is_builtin: Whether this is a built-in skill
    """

    metadata: SkillMetadata
    prompt: str
    tools: list[str] = field(default_factory=list)
    config: list[SkillConfig] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    source_path: str | None = None
    is_builtin: bool = False

    def get_config_option(self, name: str) -> SkillConfig | None:
        """Get a config option by name."""
        for opt in self.config:
            if opt.name == name:
                return opt
        return None

    def validate_config(self, values: dict[str, Any]) -> list[str]:
        """Validate configuration values.

        Returns:
            List of error messages
        """
        errors = []
        for opt in self.config:
            value = values.get(opt.name, opt.default)
            valid, error = opt.validate(value)
            if not valid:
                errors.append(error)
        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {
            "metadata": self.metadata.to_dict(),
            "prompt": self.prompt,
        }
        if self.tools:
            result["tools"] = self.tools
        if self.config:
            result["config"] = [c.to_dict() for c in self.config]
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.source_path:
            result["source_path"] = self.source_path
        if self.is_builtin:
            result["is_builtin"] = self.is_builtin
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillDefinition":
        """Create from dictionary."""
        metadata_data = data.get("metadata", {})
        if not metadata_data:
            # Handle flat format where metadata fields are at top level
            metadata_data = {
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "author": data.get("author", ""),
                "version": data.get("version", "1.0.0"),
                "tags": data.get("tags", []),
                "aliases": data.get("aliases", []),
                "examples": data.get("examples", []),
            }

        config_list = []
        for cfg in data.get("config", []):
            if isinstance(cfg, dict):
                config_list.append(SkillConfig.from_dict(cfg))

        return cls(
            metadata=SkillMetadata.from_dict(metadata_data),
            prompt=data.get("prompt", ""),
            tools=data.get("tools", []),
            config=config_list,
            dependencies=data.get("dependencies", []),
            source_path=data.get("source_path"),
            is_builtin=data.get("is_builtin", False),
        )


class Skill:
    """A skill that provides domain-specific capabilities.

    Skills modify assistant behavior by:
    - Adding specialized system prompts
    - Enabling specific tools
    - Maintaining skill-specific context
    """

    def __init__(self, definition: SkillDefinition) -> None:
        """Initialize skill.

        Args:
            definition: Skill definition
        """
        self.definition = definition
        self._active = False
        self._context: dict[str, Any] = {}
        self._activated_at: datetime | None = None

    @property
    def name(self) -> str:
        """Get skill name."""
        return self.definition.metadata.name

    @property
    def description(self) -> str:
        """Get skill description."""
        return self.definition.metadata.description

    @property
    def tags(self) -> list[str]:
        """Get skill tags."""
        return self.definition.metadata.tags

    @property
    def is_active(self) -> bool:
        """Check if skill is active."""
        return self._active

    @property
    def is_builtin(self) -> bool:
        """Check if this is a built-in skill."""
        return self.definition.is_builtin

    @property
    def dependencies(self) -> list[str]:
        """Get skill dependencies (names of other skills this depends on)."""
        return self.definition.dependencies

    def activate(self, config: dict[str, Any] | None = None) -> list[str]:
        """Activate the skill.

        This method performs synchronous in-memory operations (defaults,
        validation, state updates) and should complete quickly. If subclasses
        need to perform slow initialization, they should do so asynchronously
        outside of this method or use lazy initialization patterns.

        Args:
            config: Configuration values

        Returns:
            List of validation errors (empty if valid)
        """
        config = config or {}

        # Apply defaults
        for opt in self.definition.config:
            if opt.name not in config and opt.default is not None:
                config[opt.name] = opt.default

        # Validate config
        errors = self.definition.validate_config(config)
        if errors:
            return errors

        self._active = True
        self._context = config.copy()
        self._activated_at = datetime.now()
        return []

    def deactivate(self) -> None:
        """Deactivate the skill."""
        self._active = False
        self._context.clear()
        self._activated_at = None

    # Maximum length for context values to prevent injection via very long strings
    MAX_CONTEXT_VALUE_LENGTH = 1000

    def get_prompt(self) -> str:
        """Get skill prompt with variable substitution.

        Variables in the format {{ name }} are replaced
        with values from the context.

        Security:
        - Only allows alphanumeric values and common punctuation
        - Truncates values to MAX_CONTEXT_VALUE_LENGTH to prevent injection
          via very long strings that could overflow buffers or confuse parsers
        """
        prompt = self.definition.prompt

        # Substitute variables with sanitized values
        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1).strip()
            value = self._context.get(var_name)
            if value is None:
                return match.group(0)  # Keep original if not found

            # Convert to string and enforce length limit
            str_value = str(value)
            if len(str_value) > self.MAX_CONTEXT_VALUE_LENGTH:
                str_value = str_value[: self.MAX_CONTEXT_VALUE_LENGTH] + "..."

            # Sanitize value to prevent injection
            # Only allow safe characters: alphanumeric, spaces, common punctuation
            # Remove any potentially dangerous characters
            sanitized = re.sub(
                r'[^\w\s\-_.,:;!?@#$%&*()+=\[\]{}<>/\\|`~\'"]+', "", str_value
            )
            return sanitized

        prompt = re.sub(r"\{\{\s*(\w+)\s*\}\}", replace_var, prompt)
        return prompt

    def get_tools(self) -> list[str]:
        """Get required tools for this skill."""
        return self.definition.tools.copy()

    def get_context(self) -> dict[str, Any]:
        """Get current skill context.

        Returns a defensive copy to prevent external modification of internal
        state. Cache the result if you need to access context multiple times.

        Returns:
            Copy of the context dictionary.
        """
        return self._context.copy()

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self._context[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize skill state."""
        return {
            "name": self.name,
            "active": self._active,
            "context": self._context,
            "activated_at": (
                self._activated_at.isoformat() if self._activated_at else None
            ),
        }

    def get_help(self) -> str:
        """Get help text for this skill."""
        lines = [
            f"# {self.name}",
            "",
            self.description,
            "",
        ]

        if self.definition.metadata.author:
            lines.append(f"Author: {self.definition.metadata.author}")

        lines.append(f"Version: {self.definition.metadata.version}")

        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")

        if self.definition.tools:
            lines.extend(
                [
                    "",
                    "## Required Tools",
                    ", ".join(self.definition.tools),
                ]
            )

        if self.definition.config:
            lines.extend(
                [
                    "",
                    "## Configuration",
                ]
            )
            for opt in self.definition.config:
                req = " (required)" if opt.required else ""
                default = f" [default: {opt.default}]" if opt.default else ""
                lines.append(f"- **{opt.name}**{req}: {opt.description}{default}")

        if self.definition.metadata.examples:
            lines.extend(
                [
                    "",
                    "## Examples",
                ]
            )
            for example in self.definition.metadata.examples:
                lines.append(f"- {example}")

        return "\n".join(lines)


__all__ = [
    "Skill",
    "SkillConfig",
    "SkillDefinition",
    "SkillMetadata",
]
