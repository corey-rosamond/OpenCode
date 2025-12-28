"""Session context tracker for Code-Forge.

This module provides tracking of conversational context including:
- Active file being worked on
- Recent operations and their results
- Mentioned entities (files, functions, classes)
- Reference resolution for pronouns like "it", "that file"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    """Types of entities that can be tracked."""

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    DIRECTORY = "directory"
    URL = "url"
    COMMAND = "command"


class OperationType(str, Enum):
    """Types of operations that can be tracked."""

    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    CREATE = "create"
    SEARCH = "search"
    EXECUTE = "execute"
    FETCH = "fetch"


@dataclass
class TrackedEntity:
    """An entity mentioned or used in the conversation.

    Attributes:
        type: The type of entity.
        value: The entity value (path, name, etc.).
        context: Additional context about the entity.
        mention_count: Number of times this entity was mentioned.
        last_mentioned: Timestamp of last mention (turn number).
    """

    type: EntityType
    value: str
    context: str = ""
    mention_count: int = 1
    last_mentioned: int = 0

    def __hash__(self) -> int:
        """Hash by type and value for set operations."""
        return hash((self.type, self.value))

    def __eq__(self, other: object) -> bool:
        """Compare by type and value."""
        if not isinstance(other, TrackedEntity):
            return NotImplemented
        return self.type == other.type and self.value == other.value


@dataclass
class TrackedOperation:
    """A tracked operation in the session.

    Attributes:
        type: The type of operation.
        target: The target of the operation (file path, etc.).
        tool_name: The tool that performed the operation.
        success: Whether the operation succeeded.
        result_summary: Brief summary of the result.
        turn: The conversation turn number.
    """

    type: OperationType
    target: str
    tool_name: str
    success: bool = True
    result_summary: str = ""
    turn: int = 0


@dataclass
class SessionContext:
    """Current session context state.

    Attributes:
        active_file: The file currently being worked on.
        last_operation: The most recent operation.
        entities: All tracked entities.
        operations: Recent operations (limited history).
        turn_count: Current conversation turn.
    """

    active_file: str | None = None
    last_operation: TrackedOperation | None = None
    entities: dict[str, TrackedEntity] = field(default_factory=dict)
    operations: list[TrackedOperation] = field(default_factory=list)
    turn_count: int = 0

    # Maximum operations to keep in history
    MAX_OPERATIONS: int = 50


class SessionContextTracker:
    """Tracks conversational context throughout a session.

    Maintains state about:
    - What file is currently being worked on
    - What operations have been performed
    - What entities (files, functions, etc.) have been mentioned

    This enables pronoun resolution and context-aware responses.
    """

    def __init__(self) -> None:
        """Initialize the context tracker."""
        self._context = SessionContext()

    @property
    def active_file(self) -> str | None:
        """Get the currently active file.

        Returns:
            Path to active file or None.
        """
        return self._context.active_file

    @property
    def last_operation(self) -> TrackedOperation | None:
        """Get the last operation performed.

        Returns:
            Last operation or None.
        """
        return self._context.last_operation

    @property
    def turn_count(self) -> int:
        """Get the current turn count.

        Returns:
            Number of conversation turns.
        """
        return self._context.turn_count

    def increment_turn(self) -> None:
        """Increment the conversation turn counter."""
        self._context.turn_count += 1

    def set_active_file(self, file_path: str) -> None:
        """Set the currently active file.

        Args:
            file_path: Path to the active file.
        """
        self._context.active_file = file_path
        self.track_entity(EntityType.FILE, file_path)

    def clear_active_file(self) -> None:
        """Clear the active file."""
        self._context.active_file = None

    def track_operation(
        self,
        op_type: OperationType,
        target: str,
        tool_name: str,
        success: bool = True,
        result_summary: str = "",
    ) -> None:
        """Track an operation.

        Args:
            op_type: Type of operation.
            target: Target of the operation.
            tool_name: Tool that performed it.
            success: Whether it succeeded.
            result_summary: Brief result summary.
        """
        operation = TrackedOperation(
            type=op_type,
            target=target,
            tool_name=tool_name,
            success=success,
            result_summary=result_summary,
            turn=self._context.turn_count,
        )

        self._context.last_operation = operation
        self._context.operations.append(operation)

        # Trim history if needed
        if len(self._context.operations) > SessionContext.MAX_OPERATIONS:
            self._context.operations = self._context.operations[-SessionContext.MAX_OPERATIONS:]

        # Update active file for file operations
        if op_type in (OperationType.READ, OperationType.WRITE, OperationType.EDIT):
            self.set_active_file(target)

        # Track target as entity
        if self._looks_like_file(target):
            self.track_entity(EntityType.FILE, target)
        elif self._looks_like_url(target):
            self.track_entity(EntityType.URL, target)

    def track_entity(
        self,
        entity_type: EntityType,
        value: str,
        context: str = "",
    ) -> None:
        """Track a mentioned entity.

        Args:
            entity_type: Type of entity.
            value: Entity value.
            context: Additional context.
        """
        key = f"{entity_type.value}:{value}"

        if key in self._context.entities:
            # Update existing entity
            entity = self._context.entities[key]
            entity.mention_count += 1
            entity.last_mentioned = self._context.turn_count
            if context:
                entity.context = context
        else:
            # Add new entity
            self._context.entities[key] = TrackedEntity(
                type=entity_type,
                value=value,
                context=context,
                mention_count=1,
                last_mentioned=self._context.turn_count,
            )

    def get_entity(self, entity_type: EntityType, value: str) -> TrackedEntity | None:
        """Get a tracked entity.

        Args:
            entity_type: Type of entity.
            value: Entity value.

        Returns:
            The tracked entity or None.
        """
        key = f"{entity_type.value}:{value}"
        return self._context.entities.get(key)

    def get_recent_files(self, limit: int = 5) -> list[str]:
        """Get recently mentioned/used files.

        Args:
            limit: Maximum number of files to return.

        Returns:
            List of file paths, most recent first.
        """
        file_entities = [
            e for e in self._context.entities.values()
            if e.type == EntityType.FILE
        ]
        # Sort by last mentioned, then by mention count
        file_entities.sort(
            key=lambda e: (e.last_mentioned, e.mention_count),
            reverse=True,
        )
        return [e.value for e in file_entities[:limit]]

    def get_recent_operations(
        self,
        limit: int = 10,
        op_type: OperationType | None = None,
    ) -> list[TrackedOperation]:
        """Get recent operations.

        Args:
            limit: Maximum number of operations.
            op_type: Filter by operation type.

        Returns:
            List of recent operations.
        """
        operations = self._context.operations
        if op_type is not None:
            operations = [op for op in operations if op.type == op_type]
        return operations[-limit:]

    def get_last_file_operation(self) -> TrackedOperation | None:
        """Get the last file-related operation.

        Returns:
            Last file operation or None.
        """
        for op in reversed(self._context.operations):
            if op.type in (
                OperationType.READ,
                OperationType.WRITE,
                OperationType.EDIT,
                OperationType.CREATE,
                OperationType.DELETE,
            ):
                return op
        return None

    def extract_entities_from_text(self, text: str) -> list[TrackedEntity]:
        """Extract and track entities from user text.

        Args:
            text: User input text.

        Returns:
            List of extracted entities.
        """
        entities: list[TrackedEntity] = []

        # Extract file paths
        file_patterns = [
            r'["\']([^"\']+\.[a-zA-Z]{1,10})["\']',  # Quoted paths with extension
            r'(?:^|\s)([./][^\s]+\.[a-zA-Z]{1,10})(?:\s|$)',  # Paths starting with . or /
            r'(?:^|\s)([a-zA-Z_][a-zA-Z0-9_/]*\.[a-zA-Z]{1,10})(?:\s|$)',  # Relative paths
        ]
        for pattern in file_patterns:
            for match in re.finditer(pattern, text):
                path = match.group(1)
                if self._looks_like_file(path):
                    self.track_entity(EntityType.FILE, path)
                    entities.append(TrackedEntity(EntityType.FILE, path))

        # Extract function/class names (snake_case or CamelCase with context)
        func_pattern = r'(?:function|def|method)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(func_pattern, text, re.IGNORECASE):
            name = match.group(1)
            self.track_entity(EntityType.FUNCTION, name)
            entities.append(TrackedEntity(EntityType.FUNCTION, name))

        class_pattern = r'(?:class|interface|struct)\s+([A-Z][a-zA-Z0-9_]*)'
        for match in re.finditer(class_pattern, text, re.IGNORECASE):
            name = match.group(1)
            self.track_entity(EntityType.CLASS, name)
            entities.append(TrackedEntity(EntityType.CLASS, name))

        # Extract URLs
        url_pattern = r'https?://[^\s<>"\')]+(?:\.[^\s<>"\')]+)*'
        for match in re.finditer(url_pattern, text):
            url = match.group(0)
            self.track_entity(EntityType.URL, url)
            entities.append(TrackedEntity(EntityType.URL, url))

        return entities

    def get_context_summary(self) -> dict[str, Any]:
        """Get a summary of the current context.

        Returns:
            Dictionary with context summary.
        """
        return {
            "active_file": self._context.active_file,
            "turn_count": self._context.turn_count,
            "last_operation": {
                "type": self._context.last_operation.type.value,
                "target": self._context.last_operation.target,
                "success": self._context.last_operation.success,
            } if self._context.last_operation else None,
            "recent_files": self.get_recent_files(5),
            "entity_count": len(self._context.entities),
            "operation_count": len(self._context.operations),
        }

    def reset(self) -> None:
        """Reset all context state."""
        self._context = SessionContext()

    def _looks_like_file(self, value: str) -> bool:
        """Check if a value looks like a file path.

        Args:
            value: Value to check.

        Returns:
            True if it looks like a file path.
        """
        if not value:
            return False
        # URLs are not files
        if self._looks_like_url(value):
            return False
        # Has extension
        if "." in value:
            ext = value.rsplit(".", 1)[-1]
            if len(ext) <= 10 and ext.isalnum():
                return True
        # Is a path
        return "/" in value or "\\" in value

    def _looks_like_url(self, value: str) -> bool:
        """Check if a value looks like a URL.

        Args:
            value: Value to check.

        Returns:
            True if it looks like a URL.
        """
        return value.startswith(("http://", "https://", "ftp://"))
