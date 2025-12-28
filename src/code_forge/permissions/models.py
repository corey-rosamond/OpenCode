"""Permission data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PermissionLevel(str, Enum):
    """
    Permission levels in order of restrictiveness.

    ALLOW: Execute without user confirmation
    ASK: Require user confirmation before execution
    DENY: Block execution entirely
    """

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"

    def __lt__(self, other: object) -> bool:
        """Compare permission levels. ALLOW < ASK < DENY."""
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        order = [PermissionLevel.ALLOW, PermissionLevel.ASK, PermissionLevel.DENY]
        return order.index(self) < order.index(other)

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        """Greater than comparison."""
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return not (self <= other)

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return self == other or self > other


class PermissionCategory(str, Enum):
    """Categories of operations for permission grouping."""

    READ = "read_operations"
    WRITE = "write_operations"
    EXECUTE = "execute_operations"
    NETWORK = "network_operations"
    DESTRUCTIVE = "destructive_operations"
    OTHER = "other_operations"


class PermissionRule(BaseModel):
    """
    A single permission rule.

    Attributes:
        pattern: Pattern to match (e.g., "tool:bash", "arg:file_path:/etc/*")
        permission: Permission level to apply when matched
        description: Human-readable description
        enabled: Whether the rule is active
        priority: Manual priority override (higher = checked first)
    """

    model_config = ConfigDict(validate_assignment=True)

    pattern: str
    permission: PermissionLevel
    description: str = ""
    enabled: bool = True
    priority: int = Field(default=0, ge=-100, le=100)

    def to_dict(self) -> dict[str, Any]:
        """Serialize rule to dictionary."""
        return {
            "pattern": self.pattern,
            "permission": self.permission.value,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionRule:
        """Deserialize rule from dictionary."""
        return cls.model_validate({
            "pattern": data["pattern"],
            "permission": PermissionLevel(data["permission"]),
            "description": data.get("description", ""),
            "enabled": data.get("enabled", True),
            "priority": data.get("priority", 0),
        })


@dataclass
class PermissionResult:
    """
    Result of a permission check.

    Attributes:
        level: The determined permission level
        rule: The rule that matched (if any)
        reason: Human-readable explanation
    """

    level: PermissionLevel
    rule: PermissionRule | None = None
    reason: str = ""

    @property
    def allowed(self) -> bool:
        """Check if execution is allowed without confirmation."""
        return self.level == PermissionLevel.ALLOW

    @property
    def needs_confirmation(self) -> bool:
        """Check if user confirmation is required."""
        return self.level == PermissionLevel.ASK

    @property
    def denied(self) -> bool:
        """Check if execution is denied."""
        return self.level == PermissionLevel.DENY


# Category mappings for tools
TOOL_CATEGORIES: dict[str, PermissionCategory] = {
    "read": PermissionCategory.READ,
    "glob": PermissionCategory.READ,
    "grep": PermissionCategory.READ,
    "write": PermissionCategory.WRITE,
    "edit": PermissionCategory.WRITE,
    "notebook_edit": PermissionCategory.WRITE,
    "bash": PermissionCategory.EXECUTE,
    "bash_output": PermissionCategory.READ,
    "kill_shell": PermissionCategory.EXECUTE,
    "web_fetch": PermissionCategory.NETWORK,
    "web_search": PermissionCategory.NETWORK,
}


def get_tool_category(tool_name: str) -> PermissionCategory:
    """Get the permission category for a tool."""
    return TOOL_CATEGORIES.get(tool_name, PermissionCategory.OTHER)
