"""Tool sequence planning for complex requests.

This module plans multi-step tool sequences for complex natural
language requests that require multiple tool invocations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from .intent import Intent, IntentClassifier, IntentType


class StepType(str, Enum):
    """Types of steps in a tool sequence."""

    TOOL_CALL = "tool_call"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    PARALLEL = "parallel"


@dataclass
class PlannedStep:
    """A single step in a tool sequence.

    Attributes:
        step_type: Type of step.
        tool_name: Tool to invoke (for TOOL_CALL).
        parameters: Parameters for the tool.
        description: Human-readable description.
        depends_on: Indices of steps this depends on.
        condition: Condition for conditional steps.
    """

    step_type: StepType
    tool_name: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    depends_on: list[int] = field(default_factory=list)
    condition: str = ""


@dataclass
class ToolSequence:
    """A planned sequence of tool calls.

    Attributes:
        steps: Ordered list of steps.
        description: Overall sequence description.
        estimated_complexity: Complexity estimate (low/medium/high).
        original_request: Original user request.
    """

    steps: list[PlannedStep]
    description: str = ""
    estimated_complexity: str = "low"
    original_request: str = ""

    @property
    def tool_count(self) -> int:
        """Count of tool call steps."""
        return sum(1 for s in self.steps if s.step_type == StepType.TOOL_CALL)


@dataclass
class SequenceTemplate:
    """Template for common multi-step operations.

    Attributes:
        name: Template name.
        description: What this template does.
        trigger_patterns: Patterns that trigger this template.
        steps: Template steps with placeholders.
    """

    name: str
    description: str
    trigger_patterns: list[str]
    steps: list[dict[str, Any]]


class ToolSequencePlanner:
    """Plans tool sequences for complex requests.

    Analyzes user requests to determine if multiple tools are needed
    and plans the optimal sequence of operations.
    """

    # Templates for common multi-step operations
    TEMPLATES: ClassVar[list[SequenceTemplate]] = [
        SequenceTemplate(
            name="rename_across_project",
            description="Rename a symbol across all project files",
            trigger_patterns=[
                r"rename\s+\w+\s+to\s+\w+\s+(?:across|in|throughout)\s+(?:the\s+)?(?:project|codebase|all\s+files)",
                r"(?:globally|everywhere)\s+rename",
                r"refactor\s+\w+\s+to\s+\w+",
            ],
            steps=[
                {
                    "tool": "Grep",
                    "params": {"pattern": "{old_name}", "output_mode": "files_with_matches"},
                    "description": "Find all files containing the symbol",
                },
                {
                    "tool": "Edit",
                    "params": {"old_string": "{old_name}", "new_string": "{new_name}", "replace_all": True},
                    "description": "Replace symbol in each file",
                    "for_each": "files_found",
                },
            ],
        ),
        SequenceTemplate(
            name="find_and_edit",
            description="Find files and edit them",
            trigger_patterns=[
                r"find\s+(?:all\s+)?(?P<pattern>\S+)\s+files?\s+and\s+(?:edit|modify|update)",
                r"(?:in|across)\s+all\s+(?P<pattern>\S+)\s+files?\s+(?:replace|change)",
            ],
            steps=[
                {
                    "tool": "Glob",
                    "params": {"pattern": "{pattern}"},
                    "description": "Find matching files",
                },
                {
                    "tool": "Edit",
                    "params": {},
                    "description": "Edit each file",
                    "for_each": "files_found",
                },
            ],
        ),
        SequenceTemplate(
            name="read_then_edit",
            description="Read a file to understand it, then edit",
            trigger_patterns=[
                r"(?:look\s+at|check|review)\s+(?P<file>\S+)\s+(?:and|then)\s+(?:edit|modify|fix|update)",
                r"understand\s+(?P<file>\S+)\s+(?:and|then|before)\s+(?:chang|modif|edit)",
            ],
            steps=[
                {
                    "tool": "Read",
                    "params": {"file_path": "{file}"},
                    "description": "Read the file first",
                },
                {
                    "tool": "Edit",
                    "params": {"file_path": "{file}"},
                    "description": "Edit the file",
                },
            ],
        ),
        SequenceTemplate(
            name="test_after_edit",
            description="Edit and then run tests",
            trigger_patterns=[
                r"(?:edit|modify|fix|update)\s+.+\s+(?:and|then)\s+(?:run|execute)\s+tests?",
                r"(?:fix|update)\s+.+\s+(?:and\s+)?(?:make\s+sure|verify|ensure)\s+tests?\s+pass",
            ],
            steps=[
                {
                    "tool": "Edit",
                    "params": {},
                    "description": "Make the edit",
                },
                {
                    "tool": "Bash",
                    "params": {"command": "pytest"},
                    "description": "Run tests to verify",
                },
            ],
        ),
        SequenceTemplate(
            name="search_and_explain",
            description="Search for code and explain it",
            trigger_patterns=[
                r"find\s+(?:where|how)\s+.+\s+(?:is\s+)?(?:used|called|defined)\s+and\s+explain",
                r"search\s+for\s+.+\s+and\s+(?:explain|describe)",
            ],
            steps=[
                {
                    "tool": "Grep",
                    "params": {},
                    "description": "Search for the code",
                },
                {
                    "tool": "Read",
                    "params": {},
                    "description": "Read relevant files",
                    "for_each": "files_found",
                },
            ],
        ),
        SequenceTemplate(
            name="create_with_content",
            description="Create a new file with specific content",
            trigger_patterns=[
                r"create\s+(?:a\s+)?(?:new\s+)?(?P<file>\S+)\s+(?:file\s+)?(?:with|containing)",
                r"(?:make|add)\s+(?:a\s+)?(?:new\s+)?(?P<file>\S+)\s+(?:that|which)\s+(?:has|contains)",
            ],
            steps=[
                {
                    "tool": "Write",
                    "params": {"file_path": "{file}"},
                    "description": "Create the file with content",
                },
            ],
        ),
        SequenceTemplate(
            name="backup_and_edit",
            description="Backup a file before editing",
            trigger_patterns=[
                r"(?:backup|save\s+a\s+copy)\s+(?:of\s+)?(?P<file>\S+)\s+(?:before|then)\s+(?:edit|modify)",
                r"safely\s+(?:edit|modify)\s+(?P<file>\S+)",
            ],
            steps=[
                {
                    "tool": "Bash",
                    "params": {"command": "cp {file} {file}.bak"},
                    "description": "Create backup",
                },
                {
                    "tool": "Edit",
                    "params": {"file_path": "{file}"},
                    "description": "Edit the file",
                },
            ],
        ),
    ]

    def __init__(self) -> None:
        """Initialize the planner."""
        self._classifier = IntentClassifier()
        self._compiled_templates: list[tuple[SequenceTemplate, list[re.Pattern[str]]]] = []
        self._compile_templates()

    def _compile_templates(self) -> None:
        """Compile template trigger patterns."""
        for template in self.TEMPLATES:
            patterns = []
            for pattern in template.trigger_patterns:
                try:
                    patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    pass
            self._compiled_templates.append((template, patterns))

    def plan(self, text: str) -> ToolSequence:
        """Plan a tool sequence for a request.

        Args:
            text: User request text.

        Returns:
            ToolSequence with planned steps.
        """
        text = text.strip()

        # First, try to match a template
        template_sequence = self._match_template(text)
        if template_sequence:
            return template_sequence

        # Otherwise, create a simple single-step sequence
        intent = self._classifier.classify(text)
        if intent.type == IntentType.UNKNOWN:
            return ToolSequence(
                steps=[],
                description="Could not determine intent",
                original_request=text,
            )

        # Create single-step sequence
        step = self._intent_to_step(intent)
        return ToolSequence(
            steps=[step] if step else [],
            description=f"Single step: {intent.type.value}",
            estimated_complexity="low",
            original_request=text,
        )

    def plan_complex(self, text: str) -> ToolSequence:
        """Plan a complex multi-step sequence.

        Analyzes the request for compound operations and
        creates an appropriate sequence.

        Args:
            text: User request text.

        Returns:
            ToolSequence with potentially multiple steps.
        """
        # Check for compound requests (multiple intents)
        steps: list[PlannedStep] = []
        text_lower = text.lower()

        # Check for "and then" patterns indicating sequence
        if " and then " in text_lower or " then " in text_lower:
            parts = re.split(r'\s+(?:and\s+)?then\s+', text, flags=re.IGNORECASE)
            for i, part in enumerate(parts):
                intent = self._classifier.classify(part.strip())
                if intent.type != IntentType.UNKNOWN:
                    step = self._intent_to_step(intent)
                    if step:
                        if i > 0:
                            step.depends_on = [i - 1]
                        steps.append(step)

        # Check for "and" patterns indicating parallel
        elif " and " in text_lower:
            # Only split on "and" if it looks like a compound request
            if re.search(r'(?:find|search|edit|read)\s+.+\s+and\s+(?:find|search|edit|read)', text_lower):
                parts = re.split(r'\s+and\s+', text, flags=re.IGNORECASE)
                for part in parts:
                    intent = self._classifier.classify(part.strip())
                    if intent.type != IntentType.UNKNOWN:
                        step = self._intent_to_step(intent)
                        if step:
                            steps.append(step)

        if not steps:
            # Fall back to simple planning
            return self.plan(text)

        complexity = "low" if len(steps) <= 2 else ("medium" if len(steps) <= 4 else "high")

        return ToolSequence(
            steps=steps,
            description=f"Multi-step sequence with {len(steps)} operations",
            estimated_complexity=complexity,
            original_request=text,
        )

    def requires_sequence(self, text: str) -> bool:
        """Check if a request requires multiple steps.

        Args:
            text: User request text.

        Returns:
            True if multiple tools are likely needed.
        """
        # Check for template match
        for template, patterns in self._compiled_templates:
            for pattern in patterns:
                if pattern.search(text):
                    return len(template.steps) > 1

        # Check for compound patterns
        text_lower = text.lower()
        compound_indicators = [
            " and then ",
            " then ",
            " after ",
            " before ",
            " first ",
            " finally ",
            " across all ",
            " in all ",
            " throughout ",
        ]

        return any(indicator in text_lower for indicator in compound_indicators)

    def _match_template(self, text: str) -> ToolSequence | None:
        """Try to match a template to the request.

        Args:
            text: User request text.

        Returns:
            ToolSequence if template matched, None otherwise.
        """
        for template, patterns in self._compiled_templates:
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    # Extract parameters from match
                    params = match.groupdict()

                    # Build steps from template
                    steps = []
                    for i, step_def in enumerate(template.steps):
                        step_params = {}
                        for key, value in step_def.get("params", {}).items():
                            if isinstance(value, str) and "{" in value:
                                # Substitute parameters
                                for pname, pvalue in params.items():
                                    value = value.replace(f"{{{pname}}}", pvalue or "")
                            step_params[key] = value

                        step = PlannedStep(
                            step_type=StepType.TOOL_CALL,
                            tool_name=step_def["tool"],
                            parameters=step_params,
                            description=step_def.get("description", ""),
                            depends_on=[i - 1] if i > 0 else [],
                        )
                        steps.append(step)

                    complexity = "low" if len(steps) <= 2 else "medium"

                    return ToolSequence(
                        steps=steps,
                        description=template.description,
                        estimated_complexity=complexity,
                        original_request=text,
                    )

        return None

    def _intent_to_step(self, intent: Intent) -> PlannedStep | None:
        """Convert an intent to a planned step.

        Args:
            intent: Classified intent.

        Returns:
            PlannedStep or None if cannot convert.
        """
        from .resolver import ParameterResolver

        resolver = ParameterResolver()
        resolved = resolver.resolve(intent.original_text)

        if not resolved.tool_name:
            return None

        return PlannedStep(
            step_type=StepType.TOOL_CALL,
            tool_name=resolved.tool_name,
            parameters=resolved.parameters,
            description=f"{intent.type.value}: {intent.original_text[:50]}",
        )

    def get_sequence_summary(self, sequence: ToolSequence) -> str:
        """Get a human-readable summary of a sequence.

        Args:
            sequence: Tool sequence to summarize.

        Returns:
            Summary string.
        """
        if not sequence.steps:
            return "No steps planned."

        lines = [f"Plan: {sequence.description}"]
        lines.append(f"Complexity: {sequence.estimated_complexity}")
        lines.append("")

        for i, step in enumerate(sequence.steps, 1):
            deps = ""
            if step.depends_on:
                deps = f" (after step {', '.join(str(d+1) for d in step.depends_on)})"
            lines.append(f"  {i}. {step.tool_name}: {step.description}{deps}")

        return "\n".join(lines)
