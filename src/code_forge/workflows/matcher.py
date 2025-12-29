"""Workflow request matcher for natural language detection.

This module analyzes natural language requests to determine if they
should trigger predefined workflows, providing intelligent workflow
selection and parameter extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from code_forge.workflows.registry import WorkflowTemplateRegistry


@dataclass
class WorkflowMatch:
    """Result of matching a request to a workflow.

    Attributes:
        workflow_name: Name of the matched workflow.
        confidence: Match confidence (0.0 to 1.0).
        parameters: Extracted parameters from the request.
        trigger_patterns: Patterns that triggered the match.
        reason: Human-readable reason for the match.
    """

    workflow_name: str
    confidence: float
    parameters: dict[str, Any] = field(default_factory=dict)
    trigger_patterns: list[str] = field(default_factory=list)
    reason: str = ""

    def __post_init__(self) -> None:
        """Clamp confidence to valid range."""
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class WorkflowTrigger:
    """Definition of a workflow trigger pattern.

    Attributes:
        workflow_name: Name of the workflow to trigger.
        patterns: Regex patterns that trigger this workflow.
        keywords: Keywords that boost match confidence.
        parameter_extractors: Named groups to extract as parameters.
        base_confidence: Base confidence for pattern matches.
    """

    workflow_name: str
    patterns: list[str]
    keywords: list[str] = field(default_factory=list)
    parameter_extractors: list[str] = field(default_factory=list)
    base_confidence: float = 0.8


class WorkflowMatcher:
    """Matches natural language requests to workflow templates.

    Analyzes user requests to determine if they should trigger a workflow,
    and extracts relevant parameters for workflow execution.
    """

    # Built-in trigger patterns for common workflows
    BUILTIN_TRIGGERS: ClassVar[list[WorkflowTrigger]] = [
        WorkflowTrigger(
            workflow_name="bug-fix",
            patterns=[
                r"(?:fix|debug|investigate)\s+(?:the\s+)?(?:bug|error|issue|problem)",
                r"(?:there(?:'s|\s+is)\s+(?:a|an)\s+)?(?:bug|error|issue|crash)\s+in",
                r"(?:why\s+is|figure\s+out\s+why)\s+\S+\s+(?:failing|broken|crashing)",
                r"(?:track\s+down|find)\s+(?:the\s+)?(?:root\s+)?cause",
            ],
            keywords=["bug", "error", "fix", "debug", "crash", "issue", "failing"],
            base_confidence=0.85,
        ),
        WorkflowTrigger(
            workflow_name="feature-impl",
            patterns=[
                r"(?:implement|add|create|build)\s+(?:a\s+)?(?:new\s+)?feature",
                r"(?:add|implement)\s+(?:support\s+for|capability|functionality)",
                r"(?:create|build)\s+(?:a\s+)?new\s+(?:component|module|service)",
            ],
            keywords=["implement", "feature", "add", "create", "build", "new"],
            base_confidence=0.85,
        ),
        WorkflowTrigger(
            workflow_name="pr-review",
            patterns=[
                r"(?:review|check)\s+(?:the\s+)?(?:pr|pull\s+request|merge\s+request)",
                r"(?:look\s+at|examine)\s+(?:the\s+)?(?:pr|pull\s+request|merge\s+request)",
                r"(?:is\s+this|should\s+I\s+merge)\s+(?:pr|pull\s+request)\s+(?:ready|safe)",
            ],
            keywords=["review", "pr", "pull request", "merge"],
            base_confidence=0.9,
        ),
        WorkflowTrigger(
            workflow_name="code-quality",
            patterns=[
                r"(?:improve|check|analyze)\s+(?:code\s+)?quality",
                r"(?:run|perform)\s+(?:a\s+)?(?:code\s+)?(?:review|audit|analysis)",
                r"(?:refactor|clean\s+up|optimize)\s+(?:the\s+)?(?:code|codebase)",
            ],
            keywords=["quality", "refactor", "clean", "improve", "review", "audit"],
            base_confidence=0.8,
        ),
        WorkflowTrigger(
            workflow_name="security-audit",
            patterns=[
                r"(?:run|perform)\s+(?:a\s+)?security\s+(?:audit|scan|check|review)",
                r"(?:check|analyze)\s+(?:for\s+)?(?:security\s+)?vulnerabilities",
                r"(?:is\s+this|make\s+sure\s+this\s+is)\s+secure",
            ],
            keywords=["security", "audit", "vulnerability", "secure", "scan"],
            base_confidence=0.9,
        ),
        WorkflowTrigger(
            workflow_name="migration",
            patterns=[
                r"(?:migrate|upgrade|update)\s+(?:to\s+)?(?:new\s+)?(?:version|framework)",
                r"(?:refactor\s+)?(?:migration|upgrade)\s+(?:to|from)",
                r"(?:update|upgrade)\s+(?:all\s+)?dependencies",
            ],
            keywords=["migrate", "migration", "upgrade", "version", "update"],
            base_confidence=0.85,
        ),
        WorkflowTrigger(
            workflow_name="parallel-analysis",
            patterns=[
                r"(?:analyze|examine)\s+(?:the\s+)?(?:entire\s+)?(?:codebase|project)",
                r"(?:perform|run)\s+(?:a\s+)?(?:full|comprehensive)\s+analysis",
                r"(?:what(?:'s|\s+is)\s+the\s+)?(?:state|health)\s+of\s+(?:the\s+)?(?:code|project)",
            ],
            keywords=["analyze", "analysis", "codebase", "comprehensive", "full"],
            base_confidence=0.8,
        ),
    ]

    def __init__(
        self,
        registry: WorkflowTemplateRegistry | None = None,
        custom_triggers: list[WorkflowTrigger] | None = None,
    ) -> None:
        """Initialize the workflow matcher.

        Args:
            registry: Optional workflow registry for template lookup.
            custom_triggers: Optional custom trigger patterns.
        """
        self._registry = registry
        self._triggers = list(self.BUILTIN_TRIGGERS)
        if custom_triggers:
            self._triggers.extend(custom_triggers)

        # Compile patterns for efficiency
        self._compiled: list[tuple[WorkflowTrigger, list[re.Pattern[str]]]] = []
        for trigger in self._triggers:
            compiled_patterns = []
            for pattern in trigger.patterns:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    pass
            self._compiled.append((trigger, compiled_patterns))

    def match(self, text: str) -> WorkflowMatch | None:
        """Match a request to a workflow.

        Args:
            text: User request text.

        Returns:
            WorkflowMatch if a workflow should be triggered, None otherwise.
        """
        text = text.strip()
        if not text:
            return None

        best_match: WorkflowMatch | None = None
        best_confidence = 0.0

        for trigger, patterns in self._compiled:
            confidence, matched_patterns = self._calculate_match(text, trigger, patterns)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = WorkflowMatch(
                    workflow_name=trigger.workflow_name,
                    confidence=confidence,
                    trigger_patterns=matched_patterns,
                    reason=self._generate_reason(trigger, matched_patterns),
                )

        # Only return if confidence is high enough
        if best_match and best_match.confidence >= 0.7:
            return best_match

        return None

    def match_all(self, text: str, min_confidence: float = 0.5) -> list[WorkflowMatch]:
        """Get all matching workflows ranked by confidence.

        Args:
            text: User request text.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of WorkflowMatch objects sorted by confidence.
        """
        text = text.strip()
        if not text:
            return []

        matches: list[WorkflowMatch] = []

        for trigger, patterns in self._compiled:
            confidence, matched_patterns = self._calculate_match(text, trigger, patterns)
            if confidence >= min_confidence:
                matches.append(WorkflowMatch(
                    workflow_name=trigger.workflow_name,
                    confidence=confidence,
                    trigger_patterns=matched_patterns,
                    reason=self._generate_reason(trigger, matched_patterns),
                ))

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def _calculate_match(
        self,
        text: str,
        trigger: WorkflowTrigger,
        patterns: list[re.Pattern[str]],
    ) -> tuple[float, list[str]]:
        """Calculate match confidence for a trigger.

        Args:
            text: User request text.
            trigger: Workflow trigger definition.
            patterns: Compiled regex patterns.

        Returns:
            Tuple of (confidence, matched_pattern_strings).
        """
        confidence = 0.0
        matched_patterns: list[str] = []

        # Check pattern matches
        for i, pattern in enumerate(patterns):
            if pattern.search(text):
                matched_patterns.append(trigger.patterns[i])
                confidence = max(confidence, trigger.base_confidence)

        if not matched_patterns:
            # Check keyword fallback
            text_lower = text.lower()
            keyword_matches = sum(1 for kw in trigger.keywords if kw in text_lower)
            if keyword_matches >= 2:
                confidence = 0.5 + (keyword_matches * 0.05)
                matched_patterns = [f"keywords: {', '.join(kw for kw in trigger.keywords if kw in text_lower)}"]

        # Boost confidence for multiple pattern matches
        if len(matched_patterns) > 1:
            confidence = min(1.0, confidence + 0.05)

        # Boost for keyword presence
        text_lower = text.lower()
        keyword_count = sum(1 for kw in trigger.keywords if kw in text_lower)
        if keyword_count > 0:
            confidence = min(1.0, confidence + keyword_count * 0.02)

        return confidence, matched_patterns

    def _generate_reason(
        self,
        trigger: WorkflowTrigger,
        matched_patterns: list[str],
    ) -> str:
        """Generate a human-readable reason for the match.

        Args:
            trigger: Matched workflow trigger.
            matched_patterns: List of patterns that matched.

        Returns:
            Reason string.
        """
        if not matched_patterns:
            return ""

        if matched_patterns[0].startswith("keywords:"):
            return f"Request contains keywords associated with '{trigger.workflow_name}'"

        return f"Request matches pattern for '{trigger.workflow_name}' workflow"

    def should_trigger_workflow(self, text: str) -> bool:
        """Quick check if a workflow should be triggered.

        Args:
            text: User request text.

        Returns:
            True if a workflow should be triggered.
        """
        match = self.match(text)
        return match is not None

    def get_suggested_workflow(self, text: str) -> str | None:
        """Get the name of the suggested workflow for a request.

        Args:
            text: User request text.

        Returns:
            Workflow name if one should be triggered, None otherwise.
        """
        match = self.match(text)
        return match.workflow_name if match else None

    def add_trigger(self, trigger: WorkflowTrigger) -> None:
        """Add a custom trigger pattern.

        Args:
            trigger: Workflow trigger to add.
        """
        self._triggers.append(trigger)
        compiled_patterns = []
        for pattern in trigger.patterns:
            try:
                compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                pass
        self._compiled.append((trigger, compiled_patterns))

    def remove_trigger(self, workflow_name: str) -> bool:
        """Remove triggers for a workflow.

        Args:
            workflow_name: Name of workflow to remove triggers for.

        Returns:
            True if triggers were removed.
        """
        original_len = len(self._triggers)
        self._triggers = [t for t in self._triggers if t.workflow_name != workflow_name]
        self._compiled = [(t, p) for t, p in self._compiled if t.workflow_name != workflow_name]
        return len(self._triggers) < original_len
