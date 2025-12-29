"""Parameter resolution for natural language tool calls.

This module infers tool parameters from natural language context,
enabling conversational commands like "replace all X with Y" to
automatically set appropriate tool flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .intent import Intent, IntentClassifier, IntentType

if TYPE_CHECKING:
    from code_forge.context.tracker import SessionContextTracker


@dataclass
class ResolvedParameters:
    """Resolved parameters for a tool call.

    Attributes:
        tool_name: The tool to use.
        parameters: Inferred parameters for the tool.
        confidence: Confidence in the resolution.
        inferred_flags: Flags that were inferred (e.g., replace_all).
        context_used: Context information that influenced resolution.
    """

    tool_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    inferred_flags: dict[str, bool] = field(default_factory=dict)
    context_used: list[str] = field(default_factory=list)


class ParameterResolver:
    """Resolves tool parameters from natural language and context.

    Uses intent classification and session context to infer
    appropriate parameters for tool calls.
    """

    # Tool mapping from intent types
    INTENT_TO_TOOL: dict[IntentType, str] = {
        IntentType.READ_FILE: "Read",
        IntentType.WRITE_FILE: "Write",
        IntentType.EDIT_FILE: "Edit",
        IntentType.CREATE_FILE: "Write",
        IntentType.DELETE_FILE: "Bash",
        IntentType.FIND_FILES: "Glob",
        IntentType.SEARCH_CONTENT: "Grep",
        IntentType.FIND_DEFINITION: "Grep",
        IntentType.REPLACE_TEXT: "Edit",
        IntentType.REPLACE_ALL: "Edit",
        IntentType.RENAME_SYMBOL: "Edit",
        IntentType.REFACTOR: "Edit",
        IntentType.RUN_COMMAND: "Bash",
        IntentType.RUN_TESTS: "Bash",
        IntentType.BUILD_PROJECT: "Bash",
        IntentType.FETCH_URL: "WebFetch",
        IntentType.SEARCH_WEB: "WebSearch",
    }

    def __init__(
        self,
        context_tracker: SessionContextTracker | None = None,
    ) -> None:
        """Initialize the parameter resolver.

        Args:
            context_tracker: Optional session context for pronoun resolution.
        """
        self._classifier = IntentClassifier()
        self._context_tracker = context_tracker

    def resolve(self, text: str) -> ResolvedParameters:
        """Resolve parameters from natural language text.

        Args:
            text: User input text.

        Returns:
            ResolvedParameters with tool name and inferred parameters.
        """
        intent = self._classifier.classify(text)

        if intent.type == IntentType.UNKNOWN:
            return ResolvedParameters(
                tool_name="",
                confidence=0.0,
            )

        tool_name = self.INTENT_TO_TOOL.get(intent.type, "")
        parameters: dict[str, Any] = {}
        inferred_flags: dict[str, bool] = {}
        context_used: list[str] = []

        # Copy extracted parameters from intent
        parameters.update(intent.parameters)

        # Apply intent-specific parameter inference
        if intent.type == IntentType.REPLACE_ALL:
            inferred_flags["replace_all"] = True
            parameters["replace_all"] = True
            context_used.append("Inferred replace_all=true from 'all' keyword")

        elif intent.type == IntentType.REPLACE_TEXT:
            # Check if replace_all should be inferred
            if self._classifier.has_replace_all_intent(text):
                inferred_flags["replace_all"] = True
                parameters["replace_all"] = True
                context_used.append("Inferred replace_all=true from context")

        elif intent.type == IntentType.RENAME_SYMBOL:
            # Rename typically means replace all occurrences
            inferred_flags["replace_all"] = True
            parameters["replace_all"] = True
            context_used.append("Inferred replace_all=true for rename operation")

            # Map rename parameters to Edit tool parameters
            if "old_name" in parameters:
                parameters["old_string"] = parameters.pop("old_name")
            if "new_name" in parameters:
                parameters["new_string"] = parameters.pop("new_name")

        elif intent.type == IntentType.RUN_TESTS:
            # Infer test command based on project type
            if "target" not in parameters:
                parameters["command"] = self._infer_test_command()
                context_used.append("Inferred test command from project type")
            else:
                target = parameters.pop("target", "")
                parameters["command"] = f"pytest {target}" if target else "pytest"

        elif intent.type == IntentType.BUILD_PROJECT:
            # Infer build command based on project type
            parameters["command"] = self._infer_build_command()
            context_used.append("Inferred build command from project type")

        elif intent.type == IntentType.FIND_FILES:
            # Ensure glob pattern format
            if "pattern" in parameters:
                pattern = parameters["pattern"]
                if not pattern.startswith("*"):
                    parameters["pattern"] = f"**/{pattern}"
                context_used.append("Normalized glob pattern")

        elif intent.type == IntentType.SEARCH_CONTENT:
            # Map query to pattern for Grep
            if "query" in parameters:
                parameters["pattern"] = parameters.pop("query")

        elif intent.type == IntentType.FIND_DEFINITION:
            # Create definition search pattern
            if "symbol" in parameters:
                symbol = parameters.pop("symbol")
                # Search for function/class/variable definitions
                parameters["pattern"] = f"(def|class|const|let|var|function)\\s+{symbol}"
                context_used.append("Created definition search pattern")

        # Resolve file paths from context
        if self._context_tracker:
            self._resolve_file_from_context(parameters, context_used)

        return ResolvedParameters(
            tool_name=tool_name,
            parameters=parameters,
            confidence=intent.confidence,
            inferred_flags=inferred_flags,
            context_used=context_used,
        )

    def enhance_edit_parameters(
        self,
        text: str,
        existing_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Enhance Edit tool parameters based on natural language.

        This is called to augment existing tool parameters with
        inferred values from natural language context.

        Args:
            text: Original user request.
            existing_params: Parameters already set on the tool.

        Returns:
            Enhanced parameters dictionary.
        """
        enhanced = dict(existing_params)

        # Check if replace_all should be inferred
        if "replace_all" not in enhanced:
            if self._classifier.has_replace_all_intent(text):
                enhanced["replace_all"] = True

        return enhanced

    def suggest_tool_for_request(self, text: str) -> str | None:
        """Suggest the best tool for a user request.

        Args:
            text: User request text.

        Returns:
            Tool name or None if no clear match.
        """
        intent = self._classifier.classify(text)
        if intent.confidence >= 0.6:
            return self.INTENT_TO_TOOL.get(intent.type)
        return None

    def _resolve_file_from_context(
        self,
        parameters: dict[str, Any],
        context_used: list[str],
    ) -> None:
        """Resolve file path from session context if needed.

        Args:
            parameters: Parameters dict to update.
            context_used: List to append context info to.
        """
        if self._context_tracker is None:
            return

        # If no file_path specified, try to get active file
        if "file_path" not in parameters:
            active_file = self._context_tracker.active_file
            if active_file:
                parameters["file_path"] = active_file
                context_used.append(f"Using active file: {active_file}")

    def _infer_test_command(self) -> str:
        """Infer test command based on project type.

        Returns:
            Test command string.
        """
        # TODO: Use project type detection from CONV-004
        # For now, default to pytest
        return "pytest"

    def _infer_build_command(self) -> str:
        """Infer build command based on project type.

        Returns:
            Build command string.
        """
        # TODO: Use project type detection from CONV-004
        # For now, default to make
        return "make"

    def get_parameter_hints(self, tool_name: str, text: str) -> dict[str, Any]:
        """Get parameter hints for a specific tool based on text.

        Args:
            tool_name: Name of the tool.
            text: User request text.

        Returns:
            Suggested parameter values.
        """
        hints: dict[str, Any] = {}

        if tool_name == "Edit":
            # Check for replace_all intent
            if self._classifier.has_replace_all_intent(text):
                hints["replace_all"] = True

            # Try to extract replacement pair
            pair = self._classifier.extract_replacement_pair(text)
            if pair:
                hints["old_string"] = pair[0]
                hints["new_string"] = pair[1]

        elif tool_name == "Grep":
            intent = self._classifier.classify(text)
            if intent.type == IntentType.SEARCH_CONTENT:
                if "query" in intent.parameters:
                    hints["pattern"] = intent.parameters["query"]

        elif tool_name == "Glob":
            intent = self._classifier.classify(text)
            if intent.type == IntentType.FIND_FILES:
                if "pattern" in intent.parameters:
                    pattern = intent.parameters["pattern"]
                    if not pattern.startswith("*"):
                        pattern = f"**/{pattern}"
                    hints["pattern"] = pattern

        return hints
