"""Workflow parsing from YAML and Python API.

This module provides parsers for creating WorkflowDefinition objects from
YAML files/strings and a fluent Python API for programmatic workflow creation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from code_forge.core.logging import get_logger
from code_forge.workflows.models import WorkflowDefinition, WorkflowStep

logger = get_logger(__name__)


class WorkflowStepSchema(BaseModel):
    """Pydantic schema for validating workflow step YAML."""

    id: str = Field(..., min_length=1, description="Unique step identifier")
    agent: str = Field(..., min_length=1, description="Agent type to execute")
    description: str = Field(..., min_length=1, description="Step description")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Agent inputs")
    depends_on: list[str] = Field(default_factory=list, description="Dependency step IDs")
    parallel_with: list[str] = Field(default_factory=list, description="Parallel execution hints")
    condition: str | None = Field(None, description="Conditional execution expression")
    timeout: int | None = Field(None, gt=0, description="Step timeout in seconds")
    max_retries: int = Field(0, ge=0, description="Maximum retry attempts")


class WorkflowDefinitionSchema(BaseModel):
    """Pydantic schema for validating workflow definition YAML."""

    name: str = Field(..., min_length=1, description="Workflow name")
    description: str = Field(..., min_length=1, description="Workflow description")
    version: str = Field(..., min_length=1, description="Workflow version")
    author: str | None = Field(None, description="Workflow author")
    steps: list[WorkflowStepSchema] = Field(..., min_items=1, description="Workflow steps")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class YAMLWorkflowParser:
    """Parser for YAML workflow definitions.

    Parses workflow definitions from YAML strings or files, validates the
    schema, and creates WorkflowDefinition objects.

    Example YAML:
        name: my-workflow
        description: A simple workflow
        version: 1.0.0
        steps:
          - id: step1
            agent: plan
            description: Planning step
          - id: step2
            agent: review
            description: Review step
            depends_on: [step1]
    """

    def parse_file(self, path: Path) -> WorkflowDefinition:
        """Parse a workflow from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            Parsed WorkflowDefinition

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or validation fails
        """
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            raise ValueError(f"Cannot read workflow file: {e}") from e

        return self.parse(content, source=str(path))

    def parse(self, yaml_content: str, source: str = "<string>") -> WorkflowDefinition:
        """Parse a workflow from a YAML string.

        Args:
            yaml_content: YAML string to parse
            source: Source identifier for error messages

        Returns:
            Parsed WorkflowDefinition

        Raises:
            ValueError: If YAML is invalid or validation fails
        """
        # Parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {source}: {e}") from e

        if data is None:
            raise ValueError(f"Empty YAML content in {source}")

        if not isinstance(data, dict):
            raise ValueError(f"YAML must be a dictionary in {source}")

        # Validate schema
        try:
            schema = WorkflowDefinitionSchema(**data)
        except ValidationError as e:
            errors = self._format_validation_errors(e)
            raise ValueError(f"Workflow validation failed in {source}:\n{errors}") from e

        # Convert to WorkflowDefinition
        return self._schema_to_definition(schema)

    def _schema_to_definition(self, schema: WorkflowDefinitionSchema) -> WorkflowDefinition:
        """Convert validated schema to WorkflowDefinition.

        Args:
            schema: Validated Pydantic schema

        Returns:
            WorkflowDefinition object
        """
        steps = [
            WorkflowStep(
                id=step.id,
                agent=step.agent,
                description=step.description,
                inputs=step.inputs,
                depends_on=step.depends_on,
                parallel_with=step.parallel_with,
                condition=step.condition,
                timeout=step.timeout,
                max_retries=step.max_retries,
            )
            for step in schema.steps
        ]

        return WorkflowDefinition(
            name=schema.name,
            description=schema.description,
            version=schema.version,
            author=schema.author,
            steps=steps,
            metadata=schema.metadata,
        )

    def _format_validation_errors(self, error: ValidationError) -> str:
        """Format Pydantic validation errors into readable message.

        Args:
            error: Pydantic ValidationError

        Returns:
            Formatted error message
        """
        messages = []
        for err in error.errors():
            location = " -> ".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            messages.append(f"  {location}: {msg}")
        return "\n".join(messages)


class PythonWorkflowBuilder:
    """Fluent API for building workflows programmatically.

    Provides a chainable API for creating workflow definitions in Python code.

    Example:
        >>> builder = PythonWorkflowBuilder("my-workflow", "1.0.0")
        >>> builder.description("A simple workflow")
        >>> builder.add_step("step1", "plan", "Planning step")
        >>> builder.add_step("step2", "review", "Review step", depends_on=["step1"])
        >>> workflow = builder.build()
    """

    def __init__(self, name: str, version: str) -> None:
        """Initialize workflow builder.

        Args:
            name: Workflow name
            version: Workflow version

        Raises:
            ValueError: If name or version is empty
        """
        if not name:
            raise ValueError("Workflow name cannot be empty")
        if not version:
            raise ValueError("Workflow version cannot be empty")

        self._name = name
        self._version = version
        self._description: str | None = None
        self._author: str | None = None
        self._steps: list[WorkflowStep] = []
        self._metadata: dict[str, Any] = {}

    def description(self, desc: str) -> PythonWorkflowBuilder:
        """Set workflow description.

        Args:
            desc: Workflow description

        Returns:
            Self for chaining
        """
        self._description = desc
        return self

    def author(self, author: str) -> PythonWorkflowBuilder:
        """Set workflow author.

        Args:
            author: Workflow author

        Returns:
            Self for chaining
        """
        self._author = author
        return self

    def metadata(self, key: str, value: Any) -> PythonWorkflowBuilder:
        """Add metadata to workflow.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for chaining
        """
        self._metadata[key] = value
        return self

    def add_step(
        self,
        step_id: str,
        agent: str,
        description: str,
        inputs: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        parallel_with: list[str] | None = None,
        condition: str | None = None,
        timeout: int | None = None,
        max_retries: int = 0,
    ) -> PythonWorkflowBuilder:
        """Add a step to the workflow.

        Args:
            step_id: Unique step identifier
            agent: Agent type to execute
            description: Step description
            inputs: Input parameters for the agent
            depends_on: List of step IDs this step depends on
            parallel_with: List of step IDs that can run in parallel
            condition: Optional condition expression
            timeout: Optional step timeout in seconds
            max_retries: Maximum retry attempts

        Returns:
            Self for chaining

        Raises:
            ValueError: If step_id already exists
        """
        # Check for duplicate step IDs
        if any(step.id == step_id for step in self._steps):
            raise ValueError(f"Step with ID '{step_id}' already exists")

        step = WorkflowStep(
            id=step_id,
            agent=agent,
            description=description,
            inputs=inputs or {},
            depends_on=depends_on or [],
            parallel_with=parallel_with or [],
            condition=condition,
            timeout=timeout,
            max_retries=max_retries,
        )

        self._steps.append(step)
        return self

    def build(self) -> WorkflowDefinition:
        """Build the final WorkflowDefinition.

        Returns:
            Complete WorkflowDefinition

        Raises:
            ValueError: If workflow is incomplete (no description or no steps)
        """
        if not self._description:
            raise ValueError("Workflow description is required")

        if not self._steps:
            raise ValueError("Workflow must have at least one step")

        return WorkflowDefinition(
            name=self._name,
            description=self._description,
            version=self._version,
            author=self._author,
            steps=self._steps,
            metadata=self._metadata,
        )
