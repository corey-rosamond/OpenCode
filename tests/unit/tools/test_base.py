"""Tests for code_forge.tools.base module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolExecution,
    ToolParameter,
    ToolResult,
)


# =============================================================================
# Test Fixtures
# =============================================================================


class EchoTool(BaseTool):
    """Simple tool that echoes a message."""

    @property
    def name(self) -> str:
        return "Echo"

    @property
    def description(self) -> str:
        return "Echo a message back"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="message",
                type="string",
                description="Message to echo",
                required=True,
            )
        ]

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(kwargs["message"])


class SlowTool(BaseTool):
    """Tool that takes time to execute (for timeout testing)."""

    @property
    def name(self) -> str:
        return "Slow"

    @property
    def description(self) -> str:
        return "A slow tool for timeout testing"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        await asyncio.sleep(10)
        return ToolResult.ok("done")


class ErrorTool(BaseTool):
    """Tool that raises an exception."""

    @property
    def name(self) -> str:
        return "Error"

    @property
    def description(self) -> str:
        return "A tool that raises an error"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        raise RuntimeError("Intentional error")


class MultiParamTool(BaseTool):
    """Tool with multiple parameters for validation testing."""

    @property
    def name(self) -> str:
        return "MultiParam"

    @property
    def description(self) -> str:
        return "Tool with multiple parameters"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="required_str",
                type="string",
                description="Required string",
                required=True,
                min_length=1,
                max_length=100,
            ),
            ToolParameter(
                name="optional_int",
                type="integer",
                description="Optional integer",
                required=False,
                default=42,
                minimum=0,
                maximum=100,
            ),
            ToolParameter(
                name="format",
                type="string",
                description="Output format",
                required=False,
                default="json",
                enum=["json", "yaml", "toml"],
            ),
            ToolParameter(
                name="value",
                type="number",
                description="A number value",
                required=False,
            ),
            ToolParameter(
                name="enabled",
                type="boolean",
                description="Enable feature",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="items",
                type="array",
                description="List of items",
                required=False,
            ),
            ToolParameter(
                name="config",
                type="object",
                description="Configuration object",
                required=False,
            ),
        ]

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(kwargs)


# =============================================================================
# ToolCategory Tests
# =============================================================================


class TestToolCategory:
    """Tests for ToolCategory enum."""

    def test_category_values(self) -> None:
        """Test that all category values are correct."""
        assert ToolCategory.FILE.value == "file"
        assert ToolCategory.EXECUTION.value == "execution"
        assert ToolCategory.WEB.value == "web"
        assert ToolCategory.TASK.value == "task"
        assert ToolCategory.NOTEBOOK.value == "notebook"
        assert ToolCategory.MCP.value == "mcp"
        assert ToolCategory.OTHER.value == "other"

    def test_category_count(self) -> None:
        """Test that we have the expected number of categories."""
        assert len(ToolCategory) == 7

    def test_category_is_string_enum(self) -> None:
        """Test that categories can be used as strings via .value."""
        assert ToolCategory.FILE.value == "file"
        # Also test that it's an instance of str (since it's str, Enum)
        assert isinstance(ToolCategory.FILE, str)


# =============================================================================
# ToolParameter Tests
# =============================================================================


class TestToolParameter:
    """Tests for ToolParameter model."""

    def test_create_simple_parameter(self) -> None:
        """Test creating a simple required parameter."""
        param = ToolParameter(
            name="file_path",
            type="string",
            description="Path to file",
            required=True,
        )
        assert param.name == "file_path"
        assert param.type == "string"
        assert param.description == "Path to file"
        assert param.required is True
        assert param.default is None
        assert param.enum is None

    def test_create_optional_parameter(self) -> None:
        """Test creating an optional parameter with default."""
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Max items",
            required=False,
            default=100,
        )
        assert param.required is False
        assert param.default == 100

    def test_create_enum_parameter(self) -> None:
        """Test creating a parameter with enum constraint."""
        param = ToolParameter(
            name="format",
            type="string",
            description="Output format",
            enum=["json", "yaml"],
        )
        assert param.enum == ["json", "yaml"]

    def test_create_numeric_parameter_with_constraints(self) -> None:
        """Test creating a numeric parameter with min/max."""
        param = ToolParameter(
            name="timeout",
            type="integer",
            description="Timeout in seconds",
            minimum=1,
            maximum=600,
        )
        assert param.minimum == 1
        assert param.maximum == 600

    def test_create_string_parameter_with_length_constraints(self) -> None:
        """Test creating a string parameter with length constraints."""
        param = ToolParameter(
            name="content",
            type="string",
            description="Content",
            min_length=1,
            max_length=10000,
        )
        assert param.min_length == 1
        assert param.max_length == 10000


class TestToolParameterJsonSchema:
    """Tests for ToolParameter.to_json_schema()."""

    def test_simple_schema(self) -> None:
        """Test basic JSON Schema generation."""
        param = ToolParameter(
            name="path",
            type="string",
            description="File path",
        )
        schema = param.to_json_schema()
        assert schema == {
            "type": "string",
            "description": "File path",
        }

    def test_schema_with_enum(self) -> None:
        """Test JSON Schema with enum constraint."""
        param = ToolParameter(
            name="format",
            type="string",
            description="Format",
            enum=["json", "yaml"],
        )
        schema = param.to_json_schema()
        assert schema["enum"] == ["json", "yaml"]

    def test_schema_with_default(self) -> None:
        """Test JSON Schema with default value."""
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Limit",
            default=100,
        )
        schema = param.to_json_schema()
        assert schema["default"] == 100

    def test_schema_with_numeric_constraints(self) -> None:
        """Test JSON Schema with minimum/maximum."""
        param = ToolParameter(
            name="value",
            type="integer",
            description="Value",
            minimum=0,
            maximum=100,
        )
        schema = param.to_json_schema()
        assert schema["minimum"] == 0
        assert schema["maximum"] == 100

    def test_schema_with_string_length_constraints(self) -> None:
        """Test JSON Schema with minLength/maxLength."""
        param = ToolParameter(
            name="content",
            type="string",
            description="Content",
            min_length=1,
            max_length=1000,
        )
        schema = param.to_json_schema()
        assert schema["minLength"] == 1
        assert schema["maxLength"] == 1000


# =============================================================================
# ToolResult Tests
# =============================================================================


class TestToolResult:
    """Tests for ToolResult model."""

    def test_create_success_result(self) -> None:
        """Test creating a successful result."""
        result = ToolResult(success=True, output="content")
        assert result.success is True
        assert result.output == "content"
        assert result.error is None

    def test_create_failure_result(self) -> None:
        """Test creating a failed result."""
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.output is None
        assert result.error == "Something went wrong"

    def test_default_metadata(self) -> None:
        """Test that metadata defaults to empty dict."""
        result = ToolResult(success=True)
        assert result.metadata == {}


class TestToolResultFactoryMethods:
    """Tests for ToolResult.ok() and .fail()."""

    def test_ok_creates_success(self) -> None:
        """Test ToolResult.ok() creates successful result."""
        result = ToolResult.ok("output data")
        assert result.success is True
        assert result.output == "output data"
        assert result.error is None

    def test_ok_with_metadata(self) -> None:
        """Test ToolResult.ok() with metadata."""
        result = ToolResult.ok("output", lines=100, bytes=5000)
        assert result.metadata == {"lines": 100, "bytes": 5000}

    def test_fail_creates_failure(self) -> None:
        """Test ToolResult.fail() creates failed result."""
        result = ToolResult.fail("Error message")
        assert result.success is False
        assert result.error == "Error message"
        assert result.output is None

    def test_fail_with_metadata(self) -> None:
        """Test ToolResult.fail() with metadata."""
        result = ToolResult.fail("Error", path="/foo", errno=13)
        assert result.metadata == {"path": "/foo", "errno": 13}


class TestToolResultToDisplay:
    """Tests for ToolResult.to_display()."""

    def test_success_display(self) -> None:
        """Test to_display() for successful result."""
        result = ToolResult.ok("Hello World")
        assert result.to_display() == "Hello World"

    def test_failure_display(self) -> None:
        """Test to_display() for failed result."""
        result = ToolResult.fail("Something went wrong")
        assert result.to_display() == "Error: Something went wrong"

    def test_display_with_non_string_output(self) -> None:
        """Test to_display() converts non-string output."""
        result = ToolResult.ok({"key": "value"})
        assert result.to_display() == "{'key': 'value'}"


# =============================================================================
# ExecutionContext Tests
# =============================================================================


class TestExecutionContext:
    """Tests for ExecutionContext model."""

    def test_create_minimal_context(self) -> None:
        """Test creating context with only required fields."""
        ctx = ExecutionContext(working_dir="/home/user")
        assert ctx.working_dir == "/home/user"
        assert ctx.session_id is None
        assert ctx.agent_id is None
        assert ctx.dry_run is False
        assert ctx.timeout == 120.0
        assert ctx.max_output_size == 100000
        assert ctx.metadata == {}

    def test_create_full_context(self) -> None:
        """Test creating context with all fields."""
        ctx = ExecutionContext(
            working_dir="/home/user",
            session_id="sess_123",
            agent_id="agent_456",
            dry_run=True,
            timeout=60.0,
            max_output_size=50000,
            metadata={"user": "test"},
        )
        assert ctx.working_dir == "/home/user"
        assert ctx.session_id == "sess_123"
        assert ctx.agent_id == "agent_456"
        assert ctx.dry_run is True
        assert ctx.timeout == 60.0
        assert ctx.max_output_size == 50000
        assert ctx.metadata == {"user": "test"}


# =============================================================================
# ToolExecution Tests
# =============================================================================


class TestToolExecution:
    """Tests for ToolExecution model."""

    def test_create_execution_record(self) -> None:
        """Test creating an execution record."""
        ctx = ExecutionContext(working_dir="/home")
        result = ToolResult.ok("output")
        start = datetime(2024, 1, 15, 10, 0, 0)
        end = datetime(2024, 1, 15, 10, 0, 1)

        execution = ToolExecution(
            tool_name="Read",
            parameters={"file_path": "/foo"},
            context=ctx,
            result=result,
            started_at=start,
            completed_at=end,
        )

        assert execution.tool_name == "Read"
        assert execution.parameters == {"file_path": "/foo"}
        assert execution.context is ctx
        assert execution.result is result
        assert execution.started_at == start
        assert execution.completed_at == end

    def test_duration_calculation(self) -> None:
        """Test duration_ms property calculation."""
        ctx = ExecutionContext(working_dir="/home")
        result = ToolResult.ok("output")
        start = datetime(2024, 1, 15, 10, 0, 0)
        end = start + timedelta(milliseconds=123)

        execution = ToolExecution(
            tool_name="Read",
            parameters={},
            context=ctx,
            result=result,
            started_at=start,
            completed_at=end,
        )

        assert execution.duration_ms == pytest.approx(123.0)


# =============================================================================
# BaseTool Tests - Parameter Validation
# =============================================================================


class TestBaseToolValidation:
    """Tests for BaseTool.validate_params()."""

    def test_valid_required_parameter(self) -> None:
        """Test validation passes with required parameter."""
        tool = EchoTool()
        valid, error = tool.validate_params(message="Hello")
        assert valid is True
        assert error is None

    def test_missing_required_parameter(self) -> None:
        """Test validation fails for missing required parameter."""
        tool = EchoTool()
        valid, error = tool.validate_params()
        assert valid is False
        assert error == "Missing required parameter: message"

    def test_valid_string_type(self) -> None:
        """Test string type validation."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hello")
        assert valid is True

    def test_invalid_string_type(self) -> None:
        """Test invalid string type fails."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str=123)
        assert valid is False
        assert "expected string" in error

    def test_valid_integer_type(self) -> None:
        """Test integer type validation."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=42)
        assert valid is True

    def test_invalid_integer_type_float(self) -> None:
        """Test float doesn't validate as integer."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=3.14)
        assert valid is False
        assert "expected integer" in error

    def test_invalid_integer_type_string(self) -> None:
        """Test string doesn't validate as integer."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int="42")
        assert valid is False
        assert "expected integer" in error

    def test_boolean_not_integer(self) -> None:
        """Test that booleans don't validate as integers."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=True)
        assert valid is False
        assert "expected integer" in error

    def test_valid_number_type_int(self) -> None:
        """Test int validates as number."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", value=42)
        assert valid is True

    def test_valid_number_type_float(self) -> None:
        """Test float validates as number."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", value=3.14)
        assert valid is True

    def test_invalid_number_type(self) -> None:
        """Test string doesn't validate as number."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", value="3.14")
        assert valid is False
        assert "expected number" in error

    def test_valid_boolean_type(self) -> None:
        """Test boolean type validation."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", enabled=True)
        assert valid is True
        valid, error = tool.validate_params(required_str="hi", enabled=False)
        assert valid is True

    def test_invalid_boolean_type(self) -> None:
        """Test string doesn't validate as boolean."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", enabled="true")
        assert valid is False
        assert "expected boolean" in error

    def test_valid_array_type(self) -> None:
        """Test array type validation."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", items=[1, 2, 3])
        assert valid is True

    def test_invalid_array_type(self) -> None:
        """Test string doesn't validate as array."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", items="[1,2,3]")
        assert valid is False
        assert "expected array" in error

    def test_valid_object_type(self) -> None:
        """Test object type validation."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", config={"key": "value"})
        assert valid is True

    def test_invalid_object_type(self) -> None:
        """Test string doesn't validate as object."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", config="{'key': 'value'}")
        assert valid is False
        assert "expected object" in error

    def test_valid_enum_value(self) -> None:
        """Test enum validation passes for valid value."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", format="json")
        assert valid is True

    def test_invalid_enum_value(self) -> None:
        """Test enum validation fails for invalid value."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", format="xml")
        assert valid is False
        assert "must be one of" in error

    def test_numeric_minimum_valid(self) -> None:
        """Test numeric minimum validation passes."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=0)
        assert valid is True

    def test_numeric_minimum_invalid(self) -> None:
        """Test numeric minimum validation fails."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=-1)
        assert valid is False
        assert "below minimum" in error

    def test_numeric_maximum_valid(self) -> None:
        """Test numeric maximum validation passes."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=100)
        assert valid is True

    def test_numeric_maximum_invalid(self) -> None:
        """Test numeric maximum validation fails."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi", optional_int=101)
        assert valid is False
        assert "above maximum" in error

    def test_string_min_length_valid(self) -> None:
        """Test string min_length validation passes."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="a")
        assert valid is True

    def test_string_min_length_invalid(self) -> None:
        """Test string min_length validation fails."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="")
        assert valid is False
        assert "too short" in error

    def test_string_max_length_valid(self) -> None:
        """Test string max_length validation passes."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="a" * 100)
        assert valid is True

    def test_string_max_length_invalid(self) -> None:
        """Test string max_length validation fails."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="a" * 101)
        assert valid is False
        assert "too long" in error

    def test_optional_parameter_can_be_omitted(self) -> None:
        """Test optional parameters don't cause validation failure when omitted."""
        tool = MultiParamTool()
        valid, error = tool.validate_params(required_str="hi")
        assert valid is True


# =============================================================================
# BaseTool Tests - Execution
# =============================================================================


class TestBaseToolExecution:
    """Tests for BaseTool.execute()."""

    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        """Test successful tool execution."""
        tool = EchoTool()
        ctx = ExecutionContext(working_dir="/tmp")
        result = await tool.execute(ctx, message="Hello World")

        assert result.success is True
        assert result.output == "Hello World"
        assert isinstance(result.duration_ms, (int, float))
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_validation_failure_returns_error(self) -> None:
        """Test validation failure returns error result."""
        tool = EchoTool()
        ctx = ExecutionContext(working_dir="/tmp")
        result = await tool.execute(ctx)  # Missing required param

        assert result.success is False
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Test tool timeout returns error result."""
        tool = SlowTool()
        ctx = ExecutionContext(working_dir="/tmp", timeout=0.1)
        result = await tool.execute(ctx)

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_exception_handling(self) -> None:
        """Test exception is caught and returned as error result."""
        tool = ErrorTool()
        ctx = ExecutionContext(working_dir="/tmp")
        result = await tool.execute(ctx)

        assert result.success is False
        assert "Intentional error" in result.error

    @pytest.mark.asyncio
    async def test_dry_run_mode(self) -> None:
        """Test dry run mode returns dry run result."""
        tool = EchoTool()
        ctx = ExecutionContext(working_dir="/tmp", dry_run=True)
        result = await tool.execute(ctx, message="test")

        assert result.success is True
        assert "[Dry Run]" in result.output
        assert result.metadata.get("dry_run") is True


# =============================================================================
# BaseTool Tests - Schema Generation
# =============================================================================


class TestBaseToolOpenAISchema:
    """Tests for BaseTool.to_openai_schema()."""

    def test_openai_schema_structure(self) -> None:
        """Test OpenAI schema has correct structure."""
        tool = EchoTool()
        schema = tool.to_openai_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "Echo"
        assert schema["function"]["description"] == "Echo a message back"
        assert "parameters" in schema["function"]

    def test_openai_schema_parameters(self) -> None:
        """Test OpenAI schema parameters."""
        tool = EchoTool()
        schema = tool.to_openai_schema()
        params = schema["function"]["parameters"]

        assert params["type"] == "object"
        assert "properties" in params
        assert "message" in params["properties"]
        assert params["required"] == ["message"]

    def test_openai_schema_parameter_details(self) -> None:
        """Test OpenAI schema parameter details."""
        tool = EchoTool()
        schema = tool.to_openai_schema()
        msg_param = schema["function"]["parameters"]["properties"]["message"]

        assert msg_param["type"] == "string"
        assert msg_param["description"] == "Message to echo"


class TestBaseToolAnthropicSchema:
    """Tests for BaseTool.to_anthropic_schema()."""

    def test_anthropic_schema_structure(self) -> None:
        """Test Anthropic schema has correct structure."""
        tool = EchoTool()
        schema = tool.to_anthropic_schema()

        assert schema["name"] == "Echo"
        assert schema["description"] == "Echo a message back"
        assert "input_schema" in schema

    def test_anthropic_schema_parameters(self) -> None:
        """Test Anthropic schema parameters."""
        tool = EchoTool()
        schema = tool.to_anthropic_schema()
        input_schema = schema["input_schema"]

        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "message" in input_schema["properties"]
        assert input_schema["required"] == ["message"]


# =============================================================================
# BaseTool Tests - Properties
# =============================================================================


class TestBaseToolProperties:
    """Tests for BaseTool properties."""

    def test_tool_name(self) -> None:
        """Test tool name property."""
        tool = EchoTool()
        assert tool.name == "Echo"

    def test_tool_description(self) -> None:
        """Test tool description property."""
        tool = EchoTool()
        assert tool.description == "Echo a message back"

    def test_tool_category(self) -> None:
        """Test tool category property."""
        tool = EchoTool()
        assert tool.category == ToolCategory.OTHER

        tool2 = MultiParamTool()
        assert tool2.category == ToolCategory.FILE

    def test_tool_parameters(self) -> None:
        """Test tool parameters property."""
        tool = EchoTool()
        params = tool.parameters
        assert len(params) == 1
        assert params[0].name == "message"
