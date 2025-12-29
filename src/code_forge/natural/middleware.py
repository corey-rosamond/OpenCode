"""Natural language middleware for request preprocessing.

This module provides middleware that integrates natural language
interpretation into the agent's request processing pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from code_forge.natural.intent import IntentClassifier, IntentType
from code_forge.natural.resolver import ParameterResolver, ResolvedParameters
from code_forge.natural.planner import ToolSequencePlanner, ToolSequence

if TYPE_CHECKING:
    from code_forge.context.tracker import SessionContextTracker

logger = logging.getLogger(__name__)


@dataclass
class ProcessedRequest:
    """Result of processing a user request through natural language layer.

    Attributes:
        original_text: The original user input.
        intent_type: Detected intent type.
        confidence: Classification confidence.
        suggested_tool: Recommended tool to use.
        inferred_parameters: Auto-inferred tool parameters.
        requires_sequence: Whether this needs multi-step execution.
        sequence: Planned tool sequence for complex requests.
        context_hints: Context used for inference.
    """

    original_text: str
    intent_type: IntentType = IntentType.UNKNOWN
    confidence: float = 0.0
    suggested_tool: str = ""
    inferred_parameters: dict[str, Any] = field(default_factory=dict)
    requires_sequence: bool = False
    sequence: ToolSequence | None = None
    context_hints: list[str] = field(default_factory=list)


class NaturalLanguageMiddleware:
    """Middleware for natural language request preprocessing.

    This middleware analyzes user requests to:
    - Detect intent (replace_all, find_files, etc.)
    - Infer tool parameters from natural language
    - Plan multi-step sequences for complex requests
    - Track context for pronoun resolution
    """

    def __init__(
        self,
        context_tracker: SessionContextTracker | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            context_tracker: Optional session context tracker for
                            context-aware parameter inference.
        """
        self._classifier = IntentClassifier()
        self._resolver = ParameterResolver(context_tracker=context_tracker)
        self._planner = ToolSequencePlanner()
        self._context_tracker = context_tracker

    def process(self, text: str) -> ProcessedRequest:
        """Process a user request through the natural language layer.

        Args:
            text: User input text.

        Returns:
            ProcessedRequest with intent, parameters, and sequence info.
        """
        text = text.strip()
        if not text:
            return ProcessedRequest(original_text=text)

        # Step 1: Classify intent
        intent = self._classifier.classify(text)

        # Step 2: Resolve parameters
        resolved = self._resolver.resolve(text)

        # Step 3: Check if this needs a sequence
        requires_sequence = self._planner.requires_sequence(text)
        sequence = None
        if requires_sequence:
            sequence = self._planner.plan_complex(text)

        # Step 4: Build result
        return ProcessedRequest(
            original_text=text,
            intent_type=intent.type,
            confidence=intent.confidence,
            suggested_tool=resolved.tool_name,
            inferred_parameters=resolved.parameters,
            requires_sequence=requires_sequence,
            sequence=sequence,
            context_hints=resolved.context_used,
        )

    def enhance_tool_parameters(
        self,
        tool_name: str,
        user_text: str,
        existing_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Enhance existing tool parameters based on user text.

        This is useful when you already have some parameters but want
        to infer additional ones from the natural language request.

        Args:
            tool_name: Name of the tool being called.
            user_text: Original user request text.
            existing_params: Parameters already specified.

        Returns:
            Enhanced parameters dictionary.
        """
        if tool_name == "Edit":
            return self._resolver.enhance_edit_parameters(
                user_text,
                existing_params,
            )

        # For other tools, just return hints merged with existing
        hints = self._resolver.get_parameter_hints(tool_name, user_text)
        merged = dict(hints)
        merged.update(existing_params)  # Existing params take precedence
        return merged

    def should_use_replace_all(self, text: str) -> bool:
        """Quick check if text indicates replace-all intent.

        Args:
            text: User input text.

        Returns:
            True if replace_all should be used.
        """
        return self._classifier.has_replace_all_intent(text)

    def get_sequence_summary(self, text: str) -> str:
        """Get a human-readable summary of planned steps.

        Args:
            text: User input text.

        Returns:
            Summary string of planned steps.
        """
        if not self._planner.requires_sequence(text):
            return "Single-step operation"

        sequence = self._planner.plan_complex(text)
        return self._planner.get_sequence_summary(sequence)

    def extract_file_reference(self, text: str) -> str | None:
        """Extract file path from text or context.

        Args:
            text: User input text.

        Returns:
            File path if found, None otherwise.
        """
        # First try to extract from text
        resolved = self._resolver.resolve(text)
        if resolved.parameters.get("file_path"):
            return resolved.parameters["file_path"]

        # Fall back to context tracker
        if self._context_tracker:
            return self._context_tracker.active_file

        return None


def create_middleware(
    context_tracker: SessionContextTracker | None = None,
) -> NaturalLanguageMiddleware:
    """Factory function to create middleware instance.

    Args:
        context_tracker: Optional session context tracker.

    Returns:
        Configured NaturalLanguageMiddleware instance.
    """
    return NaturalLanguageMiddleware(context_tracker=context_tracker)
