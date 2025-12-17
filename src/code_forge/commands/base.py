"""Base command classes and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from .executor import CommandContext
    from .parser import ParsedCommand


class ArgumentType(str, Enum):
    """Argument type for validation."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    PATH = "path"


@dataclass
class CommandArgument:
    """Command argument specification.

    Defines an expected argument with validation rules.

    Attributes:
        name: Argument name.
        description: Help text for the argument.
        required: Whether argument is required.
        default: Default value if not provided.
        type: Argument type for validation.
        choices: Valid choices for CHOICE type.
    """

    name: str
    description: str = ""
    required: bool = True
    default: Any = None
    type: ArgumentType = ArgumentType.STRING
    choices: list[str] = field(default_factory=list)

    def validate(self, value: str | None) -> tuple[bool, str | None]:
        """Validate an argument value.

        Args:
            value: Value to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if value is None:
            if self.required:
                return False, f"Missing required argument: {self.name}"
            return True, None

        if self.type == ArgumentType.INTEGER:
            try:
                int(value)
            except ValueError:
                return False, f"Argument {self.name} must be an integer"

        if self.type == ArgumentType.BOOLEAN:
            if value.lower() not in ("true", "false", "yes", "no", "1", "0"):
                return False, f"Argument {self.name} must be a boolean"

        if self.type == ArgumentType.CHOICE and value not in self.choices:
            choices_str = ", ".join(self.choices)
            return False, f"Argument {self.name} must be one of: {choices_str}"

        return True, None

    def convert(self, value: str | None) -> Any:
        """Convert a validated argument value to its proper type.

        Should only be called after validate() returns success.

        Args:
            value: Value to convert.

        Returns:
            Converted value (int, bool, or str depending on type).
        """
        if value is None:
            return self.default

        if self.type == ArgumentType.INTEGER:
            return int(value)

        if self.type == ArgumentType.BOOLEAN:
            return value.lower() in ("true", "yes", "1")

        # STRING, CHOICE, and PATH types stay as strings
        return value


@dataclass
class CommandResult:
    """Result of command execution.

    Contains success status, output text, and optional data.

    Attributes:
        success: Whether command succeeded.
        output: Output text to display.
        error: Error message if failed.
        data: Optional structured data.
    """

    success: bool
    output: str = ""
    error: str | None = None
    data: Any = None

    @classmethod
    def ok(cls, output: str = "", data: Any = None) -> CommandResult:
        """Create a success result.

        Args:
            output: Output text.
            data: Optional structured data.

        Returns:
            Success CommandResult.
        """
        return cls(success=True, output=output, data=data)

    @classmethod
    def fail(cls, error: str, output: str = "") -> CommandResult:
        """Create a failure result.

        Args:
            error: Error message.
            output: Optional output text.

        Returns:
            Failure CommandResult.
        """
        return cls(success=False, output=output, error=error)


class CommandCategory(str, Enum):
    """Command category for organization."""

    GENERAL = "general"
    SESSION = "session"
    CONTEXT = "context"
    CONTROL = "control"
    CONFIG = "config"
    DEBUG = "debug"


class Command(ABC):
    """Base class for all commands.

    Subclasses implement specific command behavior.

    Class Attributes:
        name: Primary command name.
        aliases: Alternative names for the command.
        description: Short description.
        usage: Usage pattern.
        category: Command category.
        arguments: Expected arguments.
    """

    name: ClassVar[str] = ""
    aliases: ClassVar[list[str]] = []
    description: ClassVar[str] = ""
    usage: ClassVar[str] = ""
    category: ClassVar[CommandCategory] = CommandCategory.GENERAL
    arguments: ClassVar[list[CommandArgument]] = []

    @abstractmethod
    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Execute the command.

        Args:
            parsed: Parsed command with arguments.
            context: Execution context.

        Returns:
            CommandResult with output or error.
        """
        ...

    def validate(self, parsed: ParsedCommand) -> list[str]:
        """Validate command arguments.

        Args:
            parsed: Parsed command to validate.

        Returns:
            List of validation error messages.
        """
        errors = []

        for i, arg_spec in enumerate(self.arguments):
            if arg_spec.required:
                value = parsed.get_arg(i)
                if value is None:
                    errors.append(f"Missing required argument: <{arg_spec.name}>")

        return errors

    def get_help(self) -> str:
        """Get detailed help text for the command.

        Returns:
            Formatted help string.
        """
        lines = [
            f"/{self.name} - {self.description}",
            "",
        ]

        if self.usage:
            lines.append("Usage:")
            lines.append(f"  {self.usage}")
            lines.append("")

        if self.aliases:
            lines.append(f"Aliases: {', '.join(self.aliases)}")
            lines.append("")

        if self.arguments:
            lines.append("Arguments:")
            for arg in self.arguments:
                req = "" if arg.required else " (optional)"
                lines.append(f"  <{arg.name}>{req} - {arg.description}")
            lines.append("")

        return "\n".join(lines)


class SubcommandHandler(Command):
    """Base class for commands with subcommands.

    Provides structure for commands like /session that have
    multiple subcommands (/session list, /session new, etc.).

    Class Attributes:
        subcommands: Dictionary mapping subcommand names to Command instances.
    """

    subcommands: ClassVar[dict[str, Command]] = {}

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Execute the appropriate subcommand.

        Args:
            parsed: Parsed command.
            context: Execution context.

        Returns:
            CommandResult from subcommand or default.
        """
        subcommand = parsed.subcommand

        if subcommand is None:
            # Default behavior when no subcommand
            return await self.execute_default(parsed, context)

        if subcommand in self.subcommands:
            # Create new parsed with shifted args
            from .parser import ParsedCommand as ParsedCommandCls

            sub_parsed = ParsedCommandCls(
                name=subcommand,
                args=parsed.rest_args,
                kwargs=parsed.kwargs,
                flags=parsed.flags,
                raw=parsed.raw,
            )
            return await self.subcommands[subcommand].execute(sub_parsed, context)

        return CommandResult.fail(
            f"Unknown subcommand: {subcommand}. "
            f"Available: {', '.join(self.subcommands.keys())}"
        )

    async def execute_default(
        self,
        _parsed: ParsedCommand,
        _context: CommandContext,
    ) -> CommandResult:
        """Execute default behavior when no subcommand given.

        Args:
            _parsed: Parsed command (unused in default implementation).
            _context: Execution context (unused in default implementation).

        Returns:
            CommandResult.
        """
        # Default: show help
        return CommandResult.ok(self.get_help())

    def get_help(self) -> str:
        """Get help including subcommands.

        Returns:
            Formatted help string.
        """
        lines = [
            f"/{self.name} - {self.description}",
            "",
            "Subcommands:",
        ]

        for name, cmd in sorted(self.subcommands.items()):
            lines.append(f"  /{self.name} {name} - {cmd.description}")

        lines.append("")
        lines.append(f"Type /help {self.name} <subcommand> for more details.")

        return "\n".join(lines)
