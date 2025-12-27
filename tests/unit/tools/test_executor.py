"""Tests for code_forge.tools.executor module."""

from __future__ import annotations

from typing import Any

import pytest

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.executor import ToolExecutor
from code_forge.tools.registry import ToolRegistry


# =============================================================================
# Test Fixtures
# =============================================================================


class EchoTool(BaseTool):
    """Tool that echoes a message."""

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


class FailingTool(BaseTool):
    """Tool that always fails."""

    @property
    def name(self) -> str:
        return "Failing"

    @property
    def description(self) -> str:
        return "A tool that always fails"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        return ToolResult.fail("Intentional failure")


class FileTool(BaseTool):
    """Tool in FILE category for filtering tests."""

    @property
    def name(self) -> str:
        return "FileOp"

    @property
    def description(self) -> str:
        return "File operation tool"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path",
                required=True,
            )
        ]

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(f"Operated on {kwargs['path']}")


@pytest.fixture
def registry():
    """Create a fresh registry for testing."""
    ToolRegistry.reset()
    reg = ToolRegistry()
    yield reg
    ToolRegistry.reset()


@pytest.fixture
def populated_registry(registry: ToolRegistry) -> ToolRegistry:
    """Create a registry with tools."""
    registry.register(EchoTool())
    registry.register(FailingTool())
    registry.register(FileTool())
    return registry


@pytest.fixture
def executor(populated_registry: ToolRegistry) -> ToolExecutor:
    """Create an executor with populated registry."""
    return ToolExecutor(populated_registry)


@pytest.fixture
def context() -> ExecutionContext:
    """Create an execution context."""
    return ExecutionContext(working_dir="/tmp")


# =============================================================================
# Executor Initialization Tests
# =============================================================================


class TestToolExecutorInit:
    """Tests for ToolExecutor initialization."""

    def test_init_with_registry(self, registry: ToolRegistry) -> None:
        """Test initializing with a registry."""
        executor = ToolExecutor(registry)
        assert executor._registry is registry

    def test_init_without_registry(self) -> None:
        """Test initializing without registry uses singleton."""
        ToolRegistry.reset()
        executor = ToolExecutor()
        assert executor._registry is ToolRegistry()

    def test_empty_executions_on_init(self, executor: ToolExecutor) -> None:
        """Test that executor starts with empty execution history."""
        assert executor.get_executions() == []


# =============================================================================
# Execution Tests
# =============================================================================


class TestToolExecutorExecution:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test successful tool execution."""
        result = await executor.execute("Echo", context, message="Hello")

        assert result.success is True
        assert result.output == "Hello"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test executing unknown tool returns error."""
        result = await executor.execute("NonExistent", context)

        assert result.success is False
        assert "Unknown tool: NonExistent" in result.error

    @pytest.mark.asyncio
    async def test_execute_failing_tool(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test executing a tool that fails."""
        result = await executor.execute("Failing", context)

        assert result.success is False
        assert "Intentional failure" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_validation_error(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test executing without required params fails validation."""
        result = await executor.execute("Echo", context)  # Missing 'message'

        assert result.success is False
        assert "Missing required parameter" in result.error


# =============================================================================
# Execution Tracking Tests
# =============================================================================


class TestToolExecutorTracking:
    """Tests for execution tracking."""

    @pytest.mark.asyncio
    async def test_execution_tracked(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test that execution is tracked."""
        await executor.execute("Echo", context, message="Test")

        executions = executor.get_executions()
        assert len(executions) == 1
        assert executions[0].tool_name == "Echo"
        assert executions[0].parameters == {"message": "Test"}

    @pytest.mark.asyncio
    async def test_multiple_executions_tracked(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test multiple executions are tracked in order."""
        await executor.execute("Echo", context, message="First")
        await executor.execute("Failing", context)
        await executor.execute("Echo", context, message="Third")

        executions = executor.get_executions()
        assert len(executions) == 3
        assert executions[0].tool_name == "Echo"
        assert executions[1].tool_name == "Failing"
        assert executions[2].tool_name == "Echo"

    @pytest.mark.asyncio
    async def test_execution_contains_result(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test that execution record contains result."""
        await executor.execute("Echo", context, message="Test")

        execution = executor.get_executions()[0]
        assert execution.result.success is True
        assert execution.result.output == "Test"

    @pytest.mark.asyncio
    async def test_execution_contains_context(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test that execution record contains context."""
        await executor.execute("Echo", context, message="Test")

        execution = executor.get_executions()[0]
        assert execution.context.working_dir == "/tmp"

    @pytest.mark.asyncio
    async def test_execution_contains_timing(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test that execution record contains timing info."""
        from datetime import datetime
        await executor.execute("Echo", context, message="Test")

        execution = executor.get_executions()[0]
        assert isinstance(execution.started_at, datetime)
        assert execution.started_at is not None
        assert isinstance(execution.completed_at, datetime)
        assert execution.completed_at is not None
        assert execution.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_clear_executions(
        self, executor: ToolExecutor, context: ExecutionContext
    ) -> None:
        """Test clearing execution history."""
        await executor.execute("Echo", context, message="Test1")
        await executor.execute("Echo", context, message="Test2")
        assert len(executor.get_executions()) == 2

        executor.clear_executions()
        assert executor.get_executions() == []

    def test_get_executions_returns_copy(
        self, executor: ToolExecutor
    ) -> None:
        """Test that get_executions returns a copy."""
        executions = executor.get_executions()
        executions.append(None)  # type: ignore

        # Internal list should be unaffected
        assert executor.get_executions() == []


# =============================================================================
# Schema Generation Tests
# =============================================================================


class TestToolExecutorSchemas:
    """Tests for schema generation."""

    def test_get_all_schemas_openai(self, executor: ToolExecutor) -> None:
        """Test getting all schemas in OpenAI format."""
        schemas = executor.get_all_schemas("openai")

        assert len(schemas) == 3
        names = [s["function"]["name"] for s in schemas]
        assert "Echo" in names
        assert "Failing" in names
        assert "FileOp" in names

        # Verify structure
        for schema in schemas:
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_get_all_schemas_anthropic(self, executor: ToolExecutor) -> None:
        """Test getting all schemas in Anthropic format."""
        schemas = executor.get_all_schemas("anthropic")

        assert len(schemas) == 3
        names = [s["name"] for s in schemas]
        assert "Echo" in names
        assert "Failing" in names
        assert "FileOp" in names

        # Verify structure
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema

    def test_get_all_schemas_unknown_format(self, executor: ToolExecutor) -> None:
        """Test that unknown format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            executor.get_all_schemas("unknown")

        assert "Unknown schema format" in str(exc_info.value)

    def test_get_schemas_by_category_openai(self, executor: ToolExecutor) -> None:
        """Test getting schemas by category in OpenAI format."""
        schemas = executor.get_schemas_by_category(ToolCategory.FILE, "openai")

        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "FileOp"

    def test_get_schemas_by_category_anthropic(self, executor: ToolExecutor) -> None:
        """Test getting schemas by category in Anthropic format."""
        schemas = executor.get_schemas_by_category(ToolCategory.FILE, "anthropic")

        assert len(schemas) == 1
        assert schemas[0]["name"] == "FileOp"

    def test_get_schemas_by_category_empty(self, executor: ToolExecutor) -> None:
        """Test getting schemas for empty category."""
        schemas = executor.get_schemas_by_category(ToolCategory.WEB, "openai")
        assert schemas == []

    def test_get_schemas_by_category_unknown_format(
        self, executor: ToolExecutor
    ) -> None:
        """Test that unknown format raises ValueError for category."""
        with pytest.raises(ValueError) as exc_info:
            executor.get_schemas_by_category(ToolCategory.FILE, "unknown")

        assert "Unknown schema format" in str(exc_info.value)


# =============================================================================
# Edge Cases
# =============================================================================


class TestToolExecutorEdgeCases:
    """Tests for edge cases."""

    def test_empty_registry(self, registry: ToolRegistry) -> None:
        """Test executor with empty registry."""
        executor = ToolExecutor(registry)
        schemas = executor.get_all_schemas("openai")
        assert schemas == []

    @pytest.mark.asyncio
    async def test_execute_on_empty_registry(
        self, registry: ToolRegistry, context: ExecutionContext
    ) -> None:
        """Test executing on empty registry."""
        executor = ToolExecutor(registry)
        result = await executor.execute("AnyTool", context)

        assert result.success is False
        assert "Unknown tool" in result.error


# =============================================================================
# Integration Tests
# =============================================================================


class TestToolExecutorIntegration:
    """Integration tests for ToolExecutor."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, context: ExecutionContext) -> None:
        """Test full executor lifecycle."""
        # Setup
        ToolRegistry.reset()
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(FileTool())
        executor = ToolExecutor(registry)

        # Get schemas
        openai_schemas = executor.get_all_schemas("openai")
        assert len(openai_schemas) == 2

        anthropic_schemas = executor.get_all_schemas("anthropic")
        assert len(anthropic_schemas) == 2

        # Execute tools
        result1 = await executor.execute("Echo", context, message="Hello")
        assert result1.success is True

        result2 = await executor.execute("FileOp", context, path="/foo/bar")
        assert result2.success is True

        result3 = await executor.execute("Unknown", context)
        assert result3.success is False

        # Check execution history
        # Note: Unknown tool doesn't get tracked since it fails before tool lookup
        executions = executor.get_executions()
        assert len(executions) == 2

        # Clear and verify
        executor.clear_executions()
        assert executor.get_executions() == []

        # Cleanup
        ToolRegistry.reset()
