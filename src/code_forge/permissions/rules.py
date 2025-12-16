"""Permission rule definition and pattern matching."""

from __future__ import annotations

import fnmatch
import functools
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from code_forge.permissions.models import (
    PermissionLevel,
    PermissionResult,
    PermissionRule,
    get_tool_category,
)


class PatternMatcher:
    """
    Matches tool/argument patterns against values.

    Pattern formats:
    - tool:name - Match tool by name
    - tool:name* - Match tool with glob
    - arg:name:pattern - Match argument value
    - category:name - Match tool category
    - Combined with comma: tool:bash,arg:command:*rm*

    Thread Safety:
    - Uses functools.lru_cache for compiled regex patterns
    - LRU eviction prevents unbounded memory growth
    """

    # Maximum pattern length to prevent ReDoS via long patterns
    MAX_PATTERN_LENGTH = 500

    # Patterns that can cause catastrophic backtracking (ReDoS)
    # These detect nested quantifiers which are the main ReDoS vector
    REDOS_PATTERNS = [
        r"\([^)]*[+*][^)]*\)[+*]",  # (a+)+ or (a*)*
        r"\[[^\]]*\][+*]{2,}",  # [a-z]++ (possessive not supported, but ++ can be typo)
        r"(\.\*){3,}",  # Multiple .* in sequence
    ]

    @staticmethod
    @functools.lru_cache(maxsize=256)
    def _compile_regex(pattern: str) -> re.Pattern[str] | None:
        """Compile and cache a regex pattern with ReDoS protection.

        Returns None if pattern is invalid or potentially dangerous.

        Security: Rejects patterns that could cause catastrophic backtracking.
        """
        # Length limit
        if len(pattern) > PatternMatcher.MAX_PATTERN_LENGTH:
            return None

        # Check for known ReDoS patterns
        for redos_pattern in PatternMatcher.REDOS_PATTERNS:
            if re.search(redos_pattern, pattern):
                return None

        try:
            return re.compile(pattern)
        except re.error:
            return None

    @classmethod
    def match(cls, pattern: str, tool_name: str, arguments: dict[str, Any]) -> bool:
        """
        Check if a pattern matches the given tool and arguments.

        Args:
            pattern: The pattern to match
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            True if pattern matches
        """
        # Parse pattern into components
        components = cls.parse_pattern(pattern)

        # All components must match
        for comp_type, comp_name, comp_pattern in components:
            if comp_type == "tool":
                if not cls._match_value(comp_pattern, tool_name):
                    return False

            elif comp_type == "arg":
                arg_value = arguments.get(comp_name)
                if arg_value is None:
                    return False
                if not cls._match_value(comp_pattern, str(arg_value)):
                    return False

            elif comp_type == "category":
                tool_category = get_tool_category(tool_name)
                if (
                    tool_category.value != comp_pattern
                    and tool_category.name.lower() != comp_pattern
                ):
                    return False

        return True

    @classmethod
    def parse_pattern(cls, pattern: str) -> list[tuple[str, str, str]]:
        """
        Parse a pattern into components.

        Returns list of (type, name, pattern) tuples.
        - type: "tool", "arg", or "category"
        - name: argument name (for arg type) or empty
        - pattern: the pattern to match

        Examples:
        - "tool:bash" -> [("tool", "", "bash")]
        - "arg:command:*rm*" -> [("arg", "command", "*rm*")]
        - "tool:bash,arg:command:*" -> [("tool", "", "bash"), ("arg", "command", "*")]
        """
        components: list[tuple[str, str, str]] = []

        # Split on comma for combined patterns
        parts = pattern.split(",")

        for part in parts:
            part_stripped = part.strip()

            if part_stripped.startswith("tool:"):
                components.append(("tool", "", part_stripped[5:]))

            elif part_stripped.startswith("arg:"):
                rest = part_stripped[4:]
                if ":" in rest:
                    name, pat = rest.split(":", 1)
                    components.append(("arg", name, pat))
                else:
                    components.append(("arg", rest, "*"))

            elif part_stripped.startswith("category:"):
                components.append(("category", "", part_stripped[9:]))

            else:
                components.append(("tool", "", part_stripped))

        return components

    @classmethod
    def _match_value(cls, pattern: str, value: str) -> bool:
        """
        Match a single pattern against a value.

        Supports:
        - Exact match: "bash" == "bash"
        - Glob pattern: "*.py" matches "test.py"
        - Regex pattern: "^/tmp/.*" matches "/tmp/foo"
        """
        # Empty pattern matches nothing
        if not pattern:
            return False

        # Exact match
        if pattern == value:
            return True

        # Check if it's a regex pattern (starts with ^, ends with $, or contains
        # regex-specific chars that aren't glob chars)
        if cls._is_regex(pattern):
            return cls._match_regex(pattern, value)

        # Glob pattern
        return cls._match_glob(pattern, value)

    @classmethod
    def _is_regex(cls, pattern: str) -> bool:
        """Check if pattern is a regex (vs glob)."""
        regex_chars = {"^", "$", "+", "\\", "(", ")", "{", "}", "|"}
        return any(char in pattern for char in regex_chars)

    @classmethod
    def _match_glob(cls, pattern: str, value: str) -> bool:
        """Match using glob/fnmatch pattern.

        Security: Values are normalized to prevent path traversal attacks.
        For example, '/etc/../etc/passwd' is normalized to '/etc/passwd'.
        """
        # Normalize path-like values to prevent traversal evasion
        normalized_value = cls._normalize_path_value(value)
        return fnmatch.fnmatch(normalized_value, pattern)

    @classmethod
    def _normalize_path_value(cls, value: str) -> str:
        """Normalize path-like values to prevent traversal attacks.

        Handles paths like '/etc/../etc/passwd' -> '/etc/passwd'.
        Non-path values are returned unchanged.
        """
        # Only normalize if it looks like a path
        if "/" in value or "\\" in value or value.startswith("."):
            # Use os.path.normpath to resolve .. and .
            return os.path.normpath(value)
        return value

    @classmethod
    def _match_regex(cls, pattern: str, value: str) -> bool:
        """Match using regex pattern.

        Security: Values are normalized to prevent path traversal attacks.
        """
        compiled = cls._compile_regex(pattern)
        if compiled is None:
            return False  # Invalid regex
        # Normalize path-like values to prevent traversal evasion
        normalized_value = cls._normalize_path_value(value)
        return bool(compiled.search(normalized_value))

    @classmethod
    def specificity(cls, pattern: str) -> int:
        """
        Calculate pattern specificity score.

        Higher score = more specific pattern.
        Used to determine rule precedence.
        """
        components = cls.parse_pattern(pattern)
        score = 0

        for comp_type, _comp_name, comp_pattern in components:
            # Base score for having a component
            score += 10

            # Tool patterns
            if comp_type == "tool":
                if "*" not in comp_pattern and "?" not in comp_pattern:
                    score += 20  # Exact tool match
                else:
                    score += 5  # Glob pattern

            # Argument patterns are more specific
            elif comp_type == "arg":
                score += 30  # Having argument constraint
                if "*" not in comp_pattern and "?" not in comp_pattern:
                    score += 20  # Exact argument match
                else:
                    score += 5

            # Category is less specific than tool
            elif comp_type == "category":
                score += 5

        return score


@dataclass
class RuleSet:
    """
    Collection of permission rules with evaluation logic.

    Rules are evaluated in order of:
    1. Priority (higher first)
    2. Specificity (more specific first)
    3. Permission level (more restrictive wins ties)
    """

    rules: list[PermissionRule] = field(default_factory=list)
    default: PermissionLevel = PermissionLevel.ASK

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)

    def remove_rule(self, pattern: str) -> bool:
        """
        Remove a rule by pattern.

        Returns True if a rule was removed.
        """
        for i, rule in enumerate(self.rules):
            if rule.pattern == pattern:
                self.rules.pop(i)
                return True
        return False

    def get_rule(self, pattern: str) -> PermissionRule | None:
        """Get a rule by pattern."""
        for rule in self.rules:
            if rule.pattern == pattern:
                return rule
        return None

    def evaluate(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> PermissionResult:
        """
        Evaluate rules to determine permission for a tool execution.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            PermissionResult with the determined level and matching rule
        """
        # Find all matching rules
        matches: list[tuple[PermissionRule, int]] = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if PatternMatcher.match(rule.pattern, tool_name, arguments):
                specificity = PatternMatcher.specificity(rule.pattern)
                matches.append((rule, specificity))

        if not matches:
            # No matching rules, use default
            return PermissionResult(
                level=self.default,
                rule=None,
                reason=f"No matching rules, using default: {self.default.value}",
            )

        # Sort by priority (desc), specificity (desc), then restrictiveness (desc)
        def sort_key(item: tuple[PermissionRule, int]) -> tuple[int, int, int]:
            rule, spec = item
            # Negate for descending order
            perm_order = [
                PermissionLevel.ALLOW,
                PermissionLevel.ASK,
                PermissionLevel.DENY,
            ]
            return (-rule.priority, -spec, -perm_order.index(rule.permission))

        matches.sort(key=sort_key)

        # Most important match wins
        best_rule, _ = matches[0]

        return PermissionResult(
            level=best_rule.permission,
            rule=best_rule,
            reason=best_rule.description or f"Matched rule: {best_rule.pattern}",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize rule set to dictionary."""
        return {
            "default": self.default.value,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleSet:
        """Deserialize rule set from dictionary."""
        return cls(
            rules=[PermissionRule.from_dict(r) for r in data.get("rules", [])],
            default=PermissionLevel(data.get("default", "ask")),
        )

    def __len__(self) -> int:
        """Return number of rules."""
        return len(self.rules)

    def __iter__(self) -> Iterator[PermissionRule]:
        """Iterate over rules."""
        return iter(self.rules)
