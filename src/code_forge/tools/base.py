"""Base tool classes and models for the tool system.

This module provides the foundational classes for implementing tools:
- ToolCategory: Enum for categorizing tools
- ToolParameter: Model for defining tool parameters with JSON Schema generation
- ToolResult: Model for tool execution results
- ExecutionContext: Model for execution context
- ToolExecution: Record of a tool execution
- BaseTool: Abstract base class for all tools (Command pattern)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from code_forge.core.errors import CodeForgeError
from code_forge.core.logging import get_logger

logger = get_logger("tools")


class ToolCategory(str, Enum):
    """Categories for grouping tools."""

    FILE = "file"  # Read, Write, Edit, Glob, Grep
    EXECUTION = "execution"  # Bash, BashOutput, KillShell
    WEB = "web"  # WebSearch, WebFetch
    TASK = "task"  # TodoRead, TodoWrite, Memory
    NOTEBOOK = "notebook"  # NotebookRead, NotebookEdit
    MCP = "mcp"  # Dynamic MCP tools
    UTILITY = "utility"  # General utility tools
    OTHER = "other"  # Miscellaneous


class ToolParameter(BaseModel):
    """Definition of a tool parameter.

    Attributes:
        name: Parameter name (used as the key in kwargs).
        type: JSON Schema type (string, integer, number, boolean, array, object).
        description: Human-readable description for LLM.
        required: Whether the parameter is required.
        default: Default value if not provided.
        enum: List of allowed values.
        min_length: Minimum string length.
        max_length: Maximum string length.
        minimum: Minimum numeric value.
        maximum: Maximum numeric value.
    """

    name: str
    type: str  # JSON Schema types
    description: str
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None
    min_length: int | None = None
    max_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format.

        Returns:
            A dictionary conforming to JSON Schema specification.
        """
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum is not None:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        return schema


class ToolResult(BaseModel):
    """Result from tool execution.

    Attributes:
        success: Whether the tool executed successfully.
        output: The tool's output on success.
        error: Error message on failure.
        duration_ms: Execution duration in milliseconds.
        metadata: Additional metadata about the execution.
    """

    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any, **metadata: Any) -> ToolResult:
        """Create a successful result.

        Args:
            output: The tool's output.
            **metadata: Additional metadata to include.

        Returns:
            A ToolResult with success=True.
        """
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> ToolResult:
        """Create a failed result.

        Args:
            error: Error message describing the failure.
            **metadata: Additional metadata to include.

        Returns:
            A ToolResult with success=False.
        """
        return cls(success=False, error=error, metadata=metadata)

    def to_display(self) -> str:
        """Convert result to a display string.

        Returns:
            Human-readable string representation of the result.
        """
        if self.success:
            return str(self.output)
        else:
            return f"Error: {self.error}"


class ExecutionContext(BaseModel):
    """Context passed to tool execution.

    Note on timeout units:
    - ExecutionContext.timeout is in SECONDS (default 120s = 2 min)
    - This allows asyncio.wait_for() to work directly with context.timeout

    Attributes:
        working_dir: Current working directory for the execution.
        session_id: Optional session identifier.
        agent_id: Optional agent identifier.
        dry_run: If True, don't perform actual changes.
        timeout: Execution timeout in seconds.
        max_output_size: Maximum output size in characters.
        metadata: Additional context metadata.
    """

    working_dir: str
    session_id: str | None = None
    agent_id: str | None = None
    dry_run: bool = False
    timeout: float = 120.0  # seconds (float to match asyncio.wait_for)
    max_output_size: int = 100000  # characters
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class ToolExecution(BaseModel):
    """Record of a tool execution.

    Attributes:
        tool_name: Name of the executed tool.
        parameters: Parameters passed to the tool.
        context: Execution context used.
        result: Result of the execution.
        started_at: When the execution started.
        completed_at: When the execution completed.
    """

    tool_name: str
    parameters: dict[str, Any]
    context: ExecutionContext
    result: ToolResult
    started_at: datetime
    completed_at: datetime

    @property
    def duration_ms(self) -> float:
        """Execution duration in milliseconds."""
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000


class BaseTool(ABC):
    """Abstract base class for all tools.

    Implements the Template Method pattern where execute() defines
    the algorithm skeleton and _execute() is the customization point.

    Subclasses must implement:
    - name: Unique tool identifier
    - description: Human-readable description for LLM
    - category: Tool category for grouping
    - parameters: List of accepted parameters
    - _execute(): The actual tool implementation

    McCabe Complexity Target: <= 6 for all methods
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for LLM."""
        ...

    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Tool category for grouping."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """List of accepted parameters."""
        ...

    @abstractmethod
    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        """Internal execution method - override in subclasses.

        This method should:
        1. Perform the actual tool operation
        2. Return ToolResult.ok() on success
        3. Return ToolResult.fail() on expected errors
        4. Let unexpected exceptions propagate (caught by execute())

        Args:
            context: Execution context with working directory, timeout, etc.
            **kwargs: Tool-specific parameters.

        Returns:
            ToolResult with execution outcome.
        """
        ...

    async def execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        """Execute the tool with validation, timeout, and error handling.

        This is the Template Method that defines the execution algorithm.
        Subclasses should override _execute(), not this method.

        Args:
            context: Execution context with working directory, timeout, etc.
            **kwargs: Tool-specific parameters.

        Returns:
            ToolResult with execution outcome. Never raises exceptions.
        """
        start_time = datetime.now()

        # Step 1: Validate parameters
        valid, error = self.validate_params(**kwargs)
        if not valid:
            return ToolResult.fail(error or "Validation failed")

        # Step 2: Check for dry run
        if context.dry_run:
            return ToolResult.ok(
                f"[Dry Run] Would execute {self.name} with {kwargs}", dry_run=True
            )

        # Step 3: Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._execute(context, **kwargs), timeout=context.timeout
            )
        except TimeoutError:
            result = ToolResult.fail(f"Tool timed out after {context.timeout}s")
        except asyncio.CancelledError:
            result = ToolResult.fail("Tool execution cancelled")
        except CodeForgeError as e:
            result = ToolResult.fail(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in {self.name}")
            result = ToolResult.fail(f"Unexpected error: {e!s}")

        # Step 4: Add timing metadata
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000
        result.duration_ms = duration

        return result

    def validate_params(self, **kwargs: Any) -> tuple[bool, str | None]:
        """Validate parameters against schema.

        Args:
            **kwargs: Parameters to validate.

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        for param in self.parameters:
            # Check required parameters
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"

            # Skip validation if parameter not provided
            if param.name not in kwargs:
                continue

            value = kwargs[param.name]

            # Type checking
            if not self._check_type(value, param.type):
                return False, f"Invalid type for '{param.name}': expected {param.type}"

            # Enum checking
            if param.enum is not None and value not in param.enum:
                return False, f"Invalid value for '{param.name}': must be one of {param.enum}"

            # String length checking
            if param.type == "string" and isinstance(value, str):
                if param.min_length is not None and len(value) < param.min_length:
                    return (
                        False,
                        f"'{param.name}' too short: minimum {param.min_length} chars",
                    )
                if param.max_length is not None and len(value) > param.max_length:
                    return (
                        False,
                        f"'{param.name}' too long: maximum {param.max_length} chars",
                    )

            # Numeric range checking
            if param.type in ("integer", "number") and isinstance(value, (int, float)):
                if param.minimum is not None and value < param.minimum:
                    return False, f"'{param.name}' below minimum: {param.minimum}"
                if param.maximum is not None and value > param.maximum:
                    return False, f"'{param.name}' above maximum: {param.maximum}"

        return True, None

    def _check_type(self, value: Any, expected: str) -> bool:
        """Check if value matches expected JSON Schema type.

        Args:
            value: The value to check.
            expected: Expected JSON Schema type string.

        Returns:
            True if the value matches the expected type.
        """
        type_map: dict[str, type | tuple[type, ...]] = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        expected_type = type_map.get(expected)
        if expected_type is None:
            return True  # Unknown type, allow
        # Special case: booleans should not match as integers
        if expected == "integer" and isinstance(value, bool):
            return False
        return isinstance(value, expected_type)

    def to_openai_schema(self) -> dict[str, Any]:
        """Generate OpenAI-compatible function/tool schema.

        Returns:
            Dictionary conforming to OpenAI's function calling format.
        """
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Generate Anthropic-compatible tool schema.

        Returns:
            Dictionary conforming to Anthropic's tool format.
        """
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_langchain_tool(self) -> Any:
        """Create a LangChain Tool wrapper.

        Returns:
            A LangChain StructuredTool instance.

        Note:
            This requires langchain-core to be installed.
        """
        # Defer imports - langchain-core is an optional dependency
        from langchain_core.tools import StructuredTool
        from pydantic import create_model

        # Create Pydantic model for parameters
        fields: dict[str, Any] = {}
        for param in self.parameters:
            python_type: type = {
                "string": str,
                "integer": int,
                "number": float,
                "boolean": bool,
                "array": list,
                "object": dict,
            }.get(param.type, Any)

            if param.required:
                fields[param.name] = (python_type, ...)
            else:
                fields[param.name] = (python_type, param.default)

        args_model = create_model(f"{self.name}Args", **fields)

        # Capture self for the closure
        tool_instance = self

        # Create async wrapper
        async def run_tool(**kwargs: Any) -> str:
            ctx = ExecutionContext(working_dir=".")
            result = await tool_instance.execute(ctx, **kwargs)
            return result.to_display()

        return StructuredTool.from_function(
            func=lambda **kw: asyncio.run(run_tool(**kw)),
            coroutine=run_tool,
            name=self.name,
            description=self.description,
            args_schema=args_model,
        )
