"""Pronoun and reference resolver for Code-Forge.

This module provides resolution of conversational references like:
- "it" -> active file or last operation target
- "that file" -> most recently mentioned file
- "the function" -> most recently mentioned function
- "there" -> last mentioned location/directory
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from code_forge.context.tracker import SessionContextTracker

from code_forge.context.tracker import EntityType


@dataclass
class ResolvedReference:
    """A resolved reference.

    Attributes:
        original: The original text that was resolved.
        resolved: The resolved value.
        entity_type: Type of entity it resolved to.
        confidence: Confidence level (0.0-1.0).
    """

    original: str
    resolved: str
    entity_type: EntityType
    confidence: float = 1.0


class PronounResolver:
    """Resolves pronouns and references using session context.

    Handles patterns like:
    - "it" / "this" -> active file or last target
    - "that file" / "the file" -> most recent file
    - "that function" / "the method" -> most recent function/method
    - "there" / "that directory" -> most recent directory
    - "the error" / "that error" -> last failed operation
    """

    # Patterns that refer to files
    FILE_PATTERNS: ClassVar[list[str]] = [
        r"\b(?:it|this)\b",  # Generic pronouns (context-dependent)
        r"\b(?:that|the|this)\s+file\b",
        r"\b(?:that|the|this)\s+document\b",
        r"\b(?:that|the|this)\s+script\b",
        r"\b(?:that|the|this)\s+module\b",
        r"\b(?:that|the|this)\s+source\b",
        r"\bsame\s+file\b",
        r"\bcurrent\s+file\b",
        r"\bactive\s+file\b",
    ]

    # Patterns that refer to functions/methods
    FUNCTION_PATTERNS: ClassVar[list[str]] = [
        r"\b(?:that|the|this)\s+function\b",
        r"\b(?:that|the|this)\s+method\b",
        r"\b(?:that|the|this)\s+def\b",
        r"\b(?:that|the|this)\s+procedure\b",
        r"\b(?:that|the|this)\s+routine\b",
    ]

    # Patterns that refer to classes
    CLASS_PATTERNS: ClassVar[list[str]] = [
        r"\b(?:that|the|this)\s+class\b",
        r"\b(?:that|the|this)\s+interface\b",
        r"\b(?:that|the|this)\s+struct\b",
        r"\b(?:that|the|this)\s+type\b",
    ]

    # Patterns that refer to directories
    DIRECTORY_PATTERNS: ClassVar[list[str]] = [
        r"\b(?:that|the|this)\s+directory\b",
        r"\b(?:that|the|this)\s+folder\b",
        r"\b(?:that|the|this)\s+dir\b",
        r"\bthere\b",
        r"\bsame\s+(?:directory|folder|dir)\b",
    ]

    # Patterns that refer to errors
    ERROR_PATTERNS: ClassVar[list[str]] = [
        r"\b(?:that|the|this)\s+error\b",
        r"\b(?:that|the|this)\s+issue\b",
        r"\b(?:that|the|this)\s+problem\b",
        r"\b(?:that|the|this)\s+bug\b",
        r"\b(?:that|the|this)\s+failure\b",
    ]

    # Patterns that refer to URLs
    URL_PATTERNS: ClassVar[list[str]] = [
        r"\b(?:that|the|this)\s+url\b",
        r"\b(?:that|the|this)\s+link\b",
        r"\b(?:that|the|this)\s+page\b",
        r"\b(?:that|the|this)\s+site\b",
    ]

    def __init__(self, tracker: SessionContextTracker) -> None:
        """Initialize the resolver.

        Args:
            tracker: Session context tracker to use for resolution.
        """
        self._tracker = tracker

    def resolve(self, text: str) -> list[ResolvedReference]:
        """Resolve all references in the text.

        Args:
            text: Input text containing potential references.

        Returns:
            List of resolved references.
        """
        resolutions: list[ResolvedReference] = []
        text_lower = text.lower()

        # Check for file references
        for pattern in self.FILE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                resolution = self._resolve_file_reference(match.group(0))
                if resolution:
                    resolutions.append(resolution)

        # Check for function references
        for pattern in self.FUNCTION_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                resolution = self._resolve_function_reference(match.group(0))
                if resolution:
                    resolutions.append(resolution)

        # Check for class references
        for pattern in self.CLASS_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                resolution = self._resolve_class_reference(match.group(0))
                if resolution:
                    resolutions.append(resolution)

        # Check for directory references
        for pattern in self.DIRECTORY_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                resolution = self._resolve_directory_reference(match.group(0))
                if resolution:
                    resolutions.append(resolution)

        # Check for error references
        for pattern in self.ERROR_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                resolution = self._resolve_error_reference(match.group(0))
                if resolution:
                    resolutions.append(resolution)

        # Check for URL references
        for pattern in self.URL_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                resolution = self._resolve_url_reference(match.group(0))
                if resolution:
                    resolutions.append(resolution)

        return resolutions

    def resolve_single(self, text: str) -> ResolvedReference | None:
        """Resolve a single reference in text.

        Returns the highest-confidence resolution.

        Args:
            text: Input text.

        Returns:
            Best resolution or None.
        """
        resolutions = self.resolve(text)
        if not resolutions:
            return None
        # Return highest confidence
        return max(resolutions, key=lambda r: r.confidence)

    def expand_references(self, text: str) -> str:
        """Expand references in text with resolved values.

        Args:
            text: Input text with references.

        Returns:
            Text with references expanded to actual values.
        """
        resolutions = self.resolve(text)
        if not resolutions:
            return text

        # Sort by position (longest first to avoid partial replacements)
        result = text
        for resolution in sorted(resolutions, key=lambda r: -len(r.original)):
            # Case-insensitive replacement
            pattern = re.compile(re.escape(resolution.original), re.IGNORECASE)
            result = pattern.sub(f"`{resolution.resolved}`", result, count=1)

        return result

    def _resolve_file_reference(self, reference: str) -> ResolvedReference | None:
        """Resolve a file reference.

        Args:
            reference: The reference text.

        Returns:
            Resolved reference or None.
        """
        # Check active file first
        if self._tracker.active_file:
            confidence = 0.9 if reference in ("it", "this") else 0.95
            return ResolvedReference(
                original=reference,
                resolved=self._tracker.active_file,
                entity_type=EntityType.FILE,
                confidence=confidence,
            )

        # Check recent files
        recent_files = self._tracker.get_recent_files(1)
        if recent_files:
            return ResolvedReference(
                original=reference,
                resolved=recent_files[0],
                entity_type=EntityType.FILE,
                confidence=0.8,
            )

        # Check last file operation
        last_op = self._tracker.get_last_file_operation()
        if last_op:
            return ResolvedReference(
                original=reference,
                resolved=last_op.target,
                entity_type=EntityType.FILE,
                confidence=0.7,
            )

        return None

    def _resolve_function_reference(self, reference: str) -> ResolvedReference | None:
        """Resolve a function reference.

        Args:
            reference: The reference text.

        Returns:
            Resolved reference or None.
        """
        # Find most recent function entity
        entities = [
            e for e in self._tracker._context.entities.values()
            if e.type == EntityType.FUNCTION
        ]
        if entities:
            most_recent = max(entities, key=lambda e: e.last_mentioned)
            return ResolvedReference(
                original=reference,
                resolved=most_recent.value,
                entity_type=EntityType.FUNCTION,
                confidence=0.85,
            )
        return None

    def _resolve_class_reference(self, reference: str) -> ResolvedReference | None:
        """Resolve a class reference.

        Args:
            reference: The reference text.

        Returns:
            Resolved reference or None.
        """
        # Find most recent class entity
        entities = [
            e for e in self._tracker._context.entities.values()
            if e.type == EntityType.CLASS
        ]
        if entities:
            most_recent = max(entities, key=lambda e: e.last_mentioned)
            return ResolvedReference(
                original=reference,
                resolved=most_recent.value,
                entity_type=EntityType.CLASS,
                confidence=0.85,
            )
        return None

    def _resolve_directory_reference(self, reference: str) -> ResolvedReference | None:
        """Resolve a directory reference.

        Args:
            reference: The reference text.

        Returns:
            Resolved reference or None.
        """
        # Find most recent directory entity
        entities = [
            e for e in self._tracker._context.entities.values()
            if e.type == EntityType.DIRECTORY
        ]
        if entities:
            most_recent = max(entities, key=lambda e: e.last_mentioned)
            return ResolvedReference(
                original=reference,
                resolved=most_recent.value,
                entity_type=EntityType.DIRECTORY,
                confidence=0.85,
            )

        # Fall back to active file's directory
        if self._tracker.active_file:
            from pathlib import Path
            directory = str(Path(self._tracker.active_file).parent)
            return ResolvedReference(
                original=reference,
                resolved=directory,
                entity_type=EntityType.DIRECTORY,
                confidence=0.6,
            )

        return None

    def _resolve_error_reference(self, reference: str) -> ResolvedReference | None:
        """Resolve an error reference.

        Args:
            reference: The reference text.

        Returns:
            Resolved reference or None.
        """
        # Find last failed operation
        for op in reversed(self._tracker._context.operations):
            if not op.success:
                return ResolvedReference(
                    original=reference,
                    resolved=op.result_summary or f"Error in {op.target}",
                    entity_type=EntityType.FILE,  # Use FILE as fallback type
                    confidence=0.8,
                )
        return None

    def _resolve_url_reference(self, reference: str) -> ResolvedReference | None:
        """Resolve a URL reference.

        Args:
            reference: The reference text.

        Returns:
            Resolved reference or None.
        """
        # Find most recent URL entity
        entities = [
            e for e in self._tracker._context.entities.values()
            if e.type == EntityType.URL
        ]
        if entities:
            most_recent = max(entities, key=lambda e: e.last_mentioned)
            return ResolvedReference(
                original=reference,
                resolved=most_recent.value,
                entity_type=EntityType.URL,
                confidence=0.9,
            )
        return None

    def get_context_hints(self) -> str:
        """Generate context hints for the LLM.

        Returns:
            String with context hints to add to the prompt.
        """
        hints: list[str] = []

        # Active file hint
        if self._tracker.active_file:
            hints.append(f"Active file: {self._tracker.active_file}")

        # Recent files
        recent = self._tracker.get_recent_files(3)
        if recent and recent != [self._tracker.active_file]:
            other_recent = [f for f in recent if f != self._tracker.active_file]
            if other_recent:
                hints.append(f"Recent files: {', '.join(other_recent[:3])}")

        # Last operation
        if self._tracker.last_operation:
            op = self._tracker.last_operation
            status = "succeeded" if op.success else "failed"
            hints.append(f"Last operation: {op.type.value} on {op.target} ({status})")

        if hints:
            return "\n".join(["[Session Context]", *hints])
        return ""
