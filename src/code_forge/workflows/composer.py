"""Workflow composer for auto-sequencing.

This module provides intelligent workflow composition by analyzing
natural language requests and generating appropriate workflow steps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from code_forge.natural.intent import IntentClassifier, IntentType
from code_forge.workflows.models import WorkflowDefinition, WorkflowStep


@dataclass
class ComposedWorkflow:
    """A dynamically composed workflow.

    Attributes:
        name: Generated workflow name.
        description: Description of what the workflow does.
        steps: List of workflow steps.
        source_request: Original request that generated this workflow.
        confidence: Confidence in the composition.
    """

    name: str
    description: str
    steps: list[WorkflowStep]
    source_request: str = ""
    confidence: float = 0.0

    def to_definition(self) -> WorkflowDefinition:
        """Convert to a WorkflowDefinition.

        Returns:
            WorkflowDefinition for execution.
        """
        return WorkflowDefinition(
            name=self.name,
            description=self.description,
            version="1.0.0",
            steps=self.steps,
            metadata={
                "auto_composed": True,
                "source_request": self.source_request,
                "composition_confidence": self.confidence,
            },
        )


@dataclass
class StepTemplate:
    """Template for generating workflow steps.

    Attributes:
        id_prefix: Prefix for step ID generation.
        agent: Agent type to use.
        description_template: Template for step description.
        input_template: Template for step inputs.
        timeout: Default timeout in seconds.
    """

    id_prefix: str
    agent: str
    description_template: str
    input_template: str
    timeout: int = 300


class WorkflowComposer:
    """Composes workflows dynamically from natural language requests.

    Analyzes the intent and structure of user requests to generate
    appropriate multi-step workflows on-the-fly.
    """

    # Step templates for different intent types
    STEP_TEMPLATES: ClassVar[dict[IntentType, list[StepTemplate]]] = {
        IntentType.FIND_FILES: [
            StepTemplate(
                id_prefix="search",
                agent="code-explorer",
                description_template="Search for files matching {pattern}",
                input_template="Find files matching: {pattern}",
            ),
        ],
        IntentType.SEARCH_CONTENT: [
            StepTemplate(
                id_prefix="search",
                agent="code-explorer",
                description_template="Search for '{query}' in codebase",
                input_template="Search for: {query}",
            ),
            StepTemplate(
                id_prefix="analyze",
                agent="general",
                description_template="Analyze search results",
                input_template="Analyze the search results and summarize findings",
            ),
        ],
        IntentType.REPLACE_ALL: [
            StepTemplate(
                id_prefix="find",
                agent="code-explorer",
                description_template="Find all occurrences of '{old_text}'",
                input_template="Find all files containing: {old_text}",
            ),
            StepTemplate(
                id_prefix="plan",
                agent="plan",
                description_template="Plan replacement strategy",
                input_template="Plan how to safely replace '{old_text}' with '{new_text}'",
            ),
            StepTemplate(
                id_prefix="replace",
                agent="general",
                description_template="Perform replacements",
                input_template="Replace '{old_text}' with '{new_text}' in identified files",
            ),
            StepTemplate(
                id_prefix="verify",
                agent="code-review",
                description_template="Verify replacements",
                input_template="Verify that replacements were made correctly",
            ),
        ],
        IntentType.REFACTOR: [
            StepTemplate(
                id_prefix="analyze",
                agent="code-explorer",
                description_template="Analyze code for refactoring",
                input_template="Analyze {target} for refactoring opportunities",
            ),
            StepTemplate(
                id_prefix="plan",
                agent="plan",
                description_template="Plan refactoring approach",
                input_template="Create a plan for refactoring {target}",
            ),
            StepTemplate(
                id_prefix="refactor",
                agent="refactoring",
                description_template="Perform refactoring",
                input_template="Execute the refactoring plan",
            ),
            StepTemplate(
                id_prefix="test",
                agent="test-runner",
                description_template="Run tests after refactoring",
                input_template="Run tests to verify refactoring didn't break anything",
            ),
        ],
        IntentType.RUN_TESTS: [
            StepTemplate(
                id_prefix="test",
                agent="test-runner",
                description_template="Run tests",
                input_template="Run tests for {target}",
            ),
            StepTemplate(
                id_prefix="analyze",
                agent="general",
                description_template="Analyze test results",
                input_template="Analyze test results and summarize failures",
            ),
        ],
        IntentType.FIND_DEFINITION: [
            StepTemplate(
                id_prefix="find",
                agent="code-explorer",
                description_template="Find definition of {symbol}",
                input_template="Find where {symbol} is defined",
            ),
            StepTemplate(
                id_prefix="explain",
                agent="general",
                description_template="Explain the definition",
                input_template="Explain how {symbol} works",
            ),
        ],
    }

    # Patterns for detecting multi-step requests
    SEQUENCE_PATTERNS: ClassVar[list[tuple[str, list[str]]]] = [
        (r"then\s+", ["sequence"]),
        (r"and\s+then\s+", ["sequence"]),
        (r"after\s+that\s*,?\s+", ["sequence"]),
        (r"first\s+.+?\s+then\s+", ["first_then"]),
        (r"\s+and\s+", ["parallel"]),
    ]

    def __init__(self) -> None:
        """Initialize the workflow composer."""
        self._classifier = IntentClassifier()

    def compose(self, request: str) -> ComposedWorkflow | None:
        """Compose a workflow from a natural language request.

        Args:
            request: User request text.

        Returns:
            ComposedWorkflow if composition succeeds, None if request
            doesn't warrant a workflow.
        """
        request = request.strip()
        if not request:
            return None

        # Check if this warrants a multi-step workflow
        if not self._requires_workflow(request):
            return None

        # Analyze the request
        steps, confidence = self._generate_steps(request)

        if not steps:
            return None

        # Generate workflow name and description
        name = self._generate_name(request)
        description = self._generate_description(request, steps)

        return ComposedWorkflow(
            name=name,
            description=description,
            steps=steps,
            source_request=request,
            confidence=confidence,
        )

    def compose_from_intents(
        self,
        intents: list[IntentType],
        parameters: dict[str, Any],
    ) -> ComposedWorkflow:
        """Compose a workflow from a list of intents.

        Args:
            intents: List of intent types to include.
            parameters: Parameters for template substitution.

        Returns:
            ComposedWorkflow with steps for each intent.
        """
        steps: list[WorkflowStep] = []
        step_index = 0

        for intent in intents:
            templates = self.STEP_TEMPLATES.get(intent, [])
            for template in templates:
                step = self._create_step_from_template(template, parameters, step_index)
                if step_index > 0:
                    step.depends_on = [steps[-1].id]
                steps.append(step)
                step_index += 1

        name = self._generate_name_from_intents(intents)
        description = f"Workflow for: {', '.join(i.value for i in intents)}"

        return ComposedWorkflow(
            name=name,
            description=description,
            steps=steps,
            confidence=0.8 if steps else 0.0,
        )

    def _requires_workflow(self, request: str) -> bool:
        """Check if request warrants a multi-step workflow.

        Args:
            request: User request text.

        Returns:
            True if workflow is warranted.
        """
        request_lower = request.lower()

        # Check for sequence patterns
        for pattern, _ in self.SEQUENCE_PATTERNS:
            if re.search(pattern, request_lower):
                return True

        # Check for complex intent
        intent = self._classifier.classify(request)
        if intent.type in (IntentType.REPLACE_ALL, IntentType.REFACTOR):
            return True

        return False

    def _generate_steps(
        self,
        request: str,
    ) -> tuple[list[WorkflowStep], float]:
        """Generate workflow steps from request.

        Args:
            request: User request text.

        Returns:
            Tuple of (steps, confidence).
        """
        steps: list[WorkflowStep] = []
        confidence = 0.0

        # Classify the intent
        intent = self._classifier.classify(request)
        parameters = intent.parameters

        # Get templates for this intent
        templates = self.STEP_TEMPLATES.get(intent.type)
        if templates:
            for i, template in enumerate(templates):
                step = self._create_step_from_template(template, parameters, i)
                if i > 0:
                    step.depends_on = [steps[-1].id]
                steps.append(step)
            confidence = intent.confidence

        # Check for sequence patterns (e.g., "X then Y")
        if not steps:
            steps, confidence = self._parse_sequence(request)

        return steps, confidence

    def _parse_sequence(
        self,
        request: str,
    ) -> tuple[list[WorkflowStep], float]:
        """Parse a sequence request like "do X then Y".

        Args:
            request: User request text.

        Returns:
            Tuple of (steps, confidence).
        """
        steps: list[WorkflowStep] = []

        # Try to split on "then" or "and then"
        parts = re.split(r"\s+(?:and\s+)?then\s+", request, flags=re.IGNORECASE)
        if len(parts) < 2:
            return [], 0.0

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # Classify this part
            intent = self._classifier.classify(part)

            step = WorkflowStep(
                id=f"step_{i}",
                agent="general",
                description=part[:100],
                inputs={"task": part},
                timeout=300,
            )

            if i > 0:
                step.depends_on = [f"step_{i-1}"]

            steps.append(step)

        return steps, 0.7 if len(steps) >= 2 else 0.0

    def _create_step_from_template(
        self,
        template: StepTemplate,
        parameters: dict[str, Any],
        index: int,
    ) -> WorkflowStep:
        """Create a workflow step from a template.

        Args:
            template: Step template.
            parameters: Parameters for substitution.
            index: Step index for ID generation.

        Returns:
            WorkflowStep instance.
        """
        # Substitute parameters in templates
        description = self._substitute(template.description_template, parameters)
        task = self._substitute(template.input_template, parameters)

        return WorkflowStep(
            id=f"{template.id_prefix}_{index}",
            agent=template.agent,
            description=description,
            inputs={"task": task},
            timeout=template.timeout,
        )

    def _substitute(self, template: str, parameters: dict[str, Any]) -> str:
        """Substitute parameters in a template string.

        Args:
            template: Template string with {param} placeholders.
            parameters: Parameter values.

        Returns:
            Substituted string.
        """
        result = template
        for key, value in parameters.items():
            result = result.replace(f"{{{key}}}", str(value))
        # Remove any remaining placeholders
        result = re.sub(r"\{[^}]+\}", "...", result)
        return result

    def _generate_name(self, request: str) -> str:
        """Generate a workflow name from request.

        Args:
            request: User request text.

        Returns:
            Generated workflow name.
        """
        # Extract key words from request
        words = re.findall(r"\b\w+\b", request.lower())
        # Filter out common words
        stopwords = {"the", "a", "an", "to", "for", "in", "on", "and", "then", "all", "it"}
        keywords = [w for w in words if w not in stopwords][:3]
        if keywords:
            return "-".join(keywords)
        return "auto-workflow"

    def _generate_name_from_intents(self, intents: list[IntentType]) -> str:
        """Generate a name from intent types.

        Args:
            intents: List of intent types.

        Returns:
            Generated name.
        """
        if not intents:
            return "auto-workflow"
        names = [i.value.replace("_", "-") for i in intents[:2]]
        return "-".join(names)

    def _generate_description(
        self,
        request: str,
        steps: list[WorkflowStep],
    ) -> str:
        """Generate a workflow description.

        Args:
            request: Original request.
            steps: Generated steps.

        Returns:
            Description string.
        """
        step_count = len(steps)
        truncated_request = request[:100] + "..." if len(request) > 100 else request
        return f"Auto-generated {step_count}-step workflow for: {truncated_request}"

    def get_suggested_agents(self, request: str) -> list[str]:
        """Get suggested agents for a request.

        Args:
            request: User request text.

        Returns:
            List of suggested agent names.
        """
        intent = self._classifier.classify(request)
        templates = self.STEP_TEMPLATES.get(intent.type, [])
        return list({t.agent for t in templates})
