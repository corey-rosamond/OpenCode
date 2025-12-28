"""Hook registration and pattern matching."""

from __future__ import annotations

import fnmatch
import threading
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from code_forge.hooks.events import HookEvent


class Hook(BaseModel):
    """
    A registered hook.

    Hooks are shell commands that execute in response to events.
    They can observe events, modify behavior, or block operations.

    Attributes:
        event_pattern: Pattern to match events (glob or exact)
        command: Shell command to execute
        timeout: Maximum execution time in seconds (min 0.1, max 300)
        working_dir: Working directory for command
        env: Additional environment variables
        enabled: Whether hook is active
        description: Human-readable description
    """

    model_config = ConfigDict(validate_assignment=True)

    # Timeout bounds to prevent runaway or effectively-disabled hooks
    MIN_TIMEOUT: ClassVar[float] = 0.1  # 100ms minimum
    MAX_TIMEOUT: ClassVar[float] = 300.0  # 5 minutes maximum

    event_pattern: str
    command: str
    timeout: float = 10.0
    working_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    description: str = ""

    @field_validator("timeout")
    @classmethod
    def clamp_timeout(cls, v: float) -> float:
        """Validate and clamp timeout to safe bounds."""
        if v <= 0 or v < cls.MIN_TIMEOUT:
            return cls.MIN_TIMEOUT
        elif v > cls.MAX_TIMEOUT:
            return cls.MAX_TIMEOUT
        return v

    @field_validator("env", mode="before")
    @classmethod
    def ensure_env_dict(cls, v: dict[str, str] | None) -> dict[str, str]:
        """Ensure env is never None."""
        return v if v is not None else {}

    def matches(self, event: HookEvent) -> bool:
        """
        Check if this hook should fire for the given event.

        Supports patterns:
        - Exact match: "tool:pre_execute"
        - Glob: "tool:*"
        - Tool-specific: "tool:pre_execute:bash"
        - Multiple (comma): "session:start,session:end"

        Args:
            event: The event to check

        Returns:
            True if hook should fire
        """
        event_str = event.type.value
        tool_suffix = f":{event.tool_name}" if event.tool_name else ""
        full_event = f"{event_str}{tool_suffix}"

        # Handle comma-separated patterns
        patterns = [p.strip() for p in self.event_pattern.split(",")]

        for pattern in patterns:
            # Exact match
            if pattern in (event_str, full_event):
                return True

            # Match all events
            if pattern == "*":
                return True

            # Glob match against event type
            if fnmatch.fnmatch(event_str, pattern):
                return True

            # Glob match against full event (with tool name)
            if fnmatch.fnmatch(full_event, pattern):
                return True

            # Tool-specific pattern (e.g., "tool:pre_execute:bash")
            if ":" in pattern:
                parts = pattern.split(":")
                if len(parts) == 3:
                    # Format: category:event:tool
                    cat, evt, tool = parts
                    event_parts = event_str.split(":")
                    if (
                        len(event_parts) >= 2
                        and fnmatch.fnmatch(event_parts[0], cat)
                        and fnmatch.fnmatch(event_parts[1], evt)
                        and event.tool_name
                        and fnmatch.fnmatch(event.tool_name, tool)
                    ):
                        return True

        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize hook to dictionary.

        Uses 'event' key for backward compatibility with config files.
        Only includes non-default values.
        """
        data: dict[str, Any] = {
            "event": self.event_pattern,
            "command": self.command,
        }
        if self.timeout != 10.0:
            data["timeout"] = self.timeout
        if self.working_dir:
            data["working_dir"] = self.working_dir
        if self.env:
            data["env"] = self.env
        if not self.enabled:
            data["enabled"] = False
        if self.description:
            data["description"] = self.description
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Hook:
        """Deserialize hook from dictionary.

        Accepts 'event' key for backward compatibility with config files.
        """
        return cls.model_validate({
            "event_pattern": data["event"],
            "command": data["command"],
            "timeout": data.get("timeout", 10.0),
            "working_dir": data.get("working_dir"),
            "env": data.get("env") or {},
            "enabled": data.get("enabled", True),
            "description": data.get("description", ""),
        })


class HookRegistry:
    """
    Registry of hooks.

    Maintains a list of hooks and provides lookup by event.
    Singleton pattern ensures consistent state.
    Thread-safe: uses RLock for all mutations.

    Example:
        ```python
        registry = HookRegistry.get_instance()
        registry.register(Hook(
            event_pattern="tool:pre_execute",
            command="echo 'Tool starting'",
        ))

        event = HookEvent.tool_pre_execute("bash", {})
        matching_hooks = registry.get_hooks(event)
        ```
    """

    _instance: ClassVar[HookRegistry | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._hooks: list[Hook] = []
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> HookRegistry:
        """Get singleton instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._instance_lock:
            cls._instance = None

    def register(self, hook: Hook) -> None:
        """
        Register a hook.

        Thread-safe: uses lock.

        Args:
            hook: Hook to register
        """
        with self._lock:
            self._hooks.append(hook)

    def unregister(self, event_pattern: str) -> bool:
        """
        Unregister hooks matching a pattern.

        Thread-safe: uses lock.

        Args:
            event_pattern: Pattern to match

        Returns:
            True if any hooks were removed
        """
        with self._lock:
            original_count = len(self._hooks)
            self._hooks = [h for h in self._hooks if h.event_pattern != event_pattern]
            return len(self._hooks) < original_count

    def get_hooks(self, event: HookEvent) -> list[Hook]:
        """
        Get all hooks that match an event.

        Thread-safe: returns a copy of matching hooks.

        Args:
            event: Event to match

        Returns:
            List of matching, enabled hooks
        """
        with self._lock:
            return [hook for hook in self._hooks if hook.enabled and hook.matches(event)]

    def clear(self) -> None:
        """Clear all registered hooks."""
        with self._lock:
            self._hooks = []

    def load_hooks(self, hooks: list[Hook]) -> None:
        """
        Load multiple hooks.

        Thread-safe: uses lock.

        Args:
            hooks: Hooks to add
        """
        with self._lock:
            self._hooks.extend(hooks)

    @property
    def hooks(self) -> list[Hook]:
        """Get a copy of all hooks."""
        with self._lock:
            return list(self._hooks)

    def __len__(self) -> int:
        with self._lock:
            return len(self._hooks)

    def __iter__(self) -> Iterator[Hook]:
        # Return copy to avoid issues during iteration
        with self._lock:
            return iter(list(self._hooks))
