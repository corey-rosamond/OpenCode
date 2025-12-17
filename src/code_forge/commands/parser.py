"""Command parsing utilities."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field


@dataclass
class ParsedCommand:
    """Parsed slash command structure.

    Represents a parsed command with its name, positional arguments,
    keyword arguments, and flags.

    Attributes:
        name: Command name (lowercase).
        args: Positional arguments.
        kwargs: Keyword arguments (--key value or --key=value).
        flags: Boolean flags (--flag or -f).
        raw: Original input text.
    """

    name: str
    args: list[str] = field(default_factory=list)
    kwargs: dict[str, str] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)
    raw: str = ""

    @property
    def has_args(self) -> bool:
        """Check if command has positional arguments."""
        return len(self.args) > 0

    def get_arg(self, index: int, default: str | None = None) -> str | None:
        """Get positional argument by index.

        Args:
            index: Argument index (0-based).
            default: Default value if not present.

        Returns:
            Argument value or default.
        """
        if 0 <= index < len(self.args):
            return self.args[index]
        return default

    def get_kwarg(self, name: str, default: str | None = None) -> str | None:
        """Get keyword argument by name.

        Args:
            name: Argument name.
            default: Default value if not present.

        Returns:
            Argument value or default.
        """
        return self.kwargs.get(name, default)

    def has_flag(self, name: str) -> bool:
        """Check if flag is set.

        Args:
            name: Flag name (without dashes).

        Returns:
            True if flag is present.
        """
        return name in self.flags

    @property
    def subcommand(self) -> str | None:
        """Get first argument as subcommand."""
        return self.get_arg(0)

    @property
    def rest_args(self) -> list[str]:
        """Get arguments after the first (subcommand)."""
        return self.args[1:]


class CommandParser:
    """Parses slash command input.

    Handles command detection, name extraction, and argument parsing.
    Supports quoted strings, flags, and keyword arguments.

    Attributes:
        COMMAND_PREFIX: The prefix that identifies commands (/).
    """

    COMMAND_PREFIX = "/"
    KWARG_PATTERN = re.compile(r"^--([a-zA-Z][a-zA-Z0-9_-]*)$")
    FLAG_PATTERN = re.compile(r"^-([a-zA-Z])$")

    def is_command(self, text: str) -> bool:
        """Check if text is a slash command.

        A valid command starts with / followed by a letter.

        Args:
            text: Input text to check.

        Returns:
            True if text starts with command prefix and has valid format.
        """
        stripped = text.strip()
        if not stripped.startswith(self.COMMAND_PREFIX):
            return False

        # Must have content after prefix
        if len(stripped) <= len(self.COMMAND_PREFIX):
            return False

        # First char after prefix must be letter
        first_char = stripped[len(self.COMMAND_PREFIX)]
        return first_char.isalpha()

    def parse(self, text: str) -> ParsedCommand:
        """Parse command text into structured form.

        Parses the command name, positional arguments, keyword arguments,
        and flags from the input text.

        Args:
            text: Command text starting with /.

        Returns:
            ParsedCommand with parsed components.

        Raises:
            ValueError: If text is not a valid command.
        """
        stripped = text.strip()

        if not self.is_command(stripped):
            raise ValueError(f"Not a valid command: {text}")

        # Remove prefix
        content = stripped[len(self.COMMAND_PREFIX) :]

        # Parse using shlex for proper quoting
        try:
            tokens = shlex.split(content)
        except ValueError as e:
            # Provide helpful error for unbalanced quotes
            error_msg = str(e)
            if "quote" in error_msg.lower():
                raise ValueError(
                    f"Unbalanced quotes in command: {text}\n"
                    f"Hint: Ensure all quotes are properly closed, "
                    f'e.g., /session title "My Title"'
                ) from e
            # For other shlex errors, fallback to simple split
            tokens = content.split()

        if not tokens:
            raise ValueError("Empty command")

        # First token is command name
        name = tokens[0].lower()
        tokens = tokens[1:]

        # Parse remaining tokens
        args: list[str] = []
        kwargs: dict[str, str] = {}
        flags: set[str] = set()

        # Track if we've seen "--" separator (end of options)
        end_of_options = False

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Check for "--" separator (POSIX convention: end of options)
            if token == "--" and not end_of_options:
                end_of_options = True
                i += 1
                continue

            # After "--", treat everything as positional arguments
            if end_of_options:
                args.append(token)
                i += 1
                continue

            # Check for --key=value or --key value
            if token.startswith("--"):
                if "=" in token:
                    key, value = token[2:].split("=", 1)
                    kwargs[key] = value
                else:
                    key = token[2:]
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                        kwargs[key] = tokens[i + 1]
                        i += 1
                    else:
                        flags.add(key)

            # Check for -f flags
            elif token.startswith("-") and len(token) == 2 and token[1].isalpha():
                flags.add(token[1])

            # Positional argument
            else:
                args.append(token)

            i += 1

        return ParsedCommand(
            name=name,
            args=args,
            kwargs=kwargs,
            flags=flags,
            raw=text,
        )

    def suggest_command(self, text: str, available: list[str]) -> str | None:
        """Suggest a command if input is close to a known command.

        Uses string similarity to find the closest matching command.

        Args:
            text: Input text.
            available: List of available command names.

        Returns:
            Suggested command name or None if no close match.
        """
        if not self.is_command(text):
            return None

        try:
            parsed = self.parse(text)
            name = parsed.name
        except ValueError:
            return None

        # Exact match - no suggestion needed
        if name in available:
            return None

        # Find closest match
        best_match: str | None = None
        best_score = 0.0

        for cmd in available:
            score = self._similarity(name, cmd)
            if score > best_score and score > 0.6:
                best_score = score
                best_match = cmd

        return best_match

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using Levenshtein-based distance.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Similarity score between 0 and 1.
        """
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Use Levenshtein distance
        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len1, len2)

        return 1.0 - (distance / max_len)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Edit distance between strings.
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]
