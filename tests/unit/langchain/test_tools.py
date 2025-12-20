"""Unit tests for tool adapters."""

import pytest
from pydantic import BaseModel

from code_forge.langchain.tools import (
    LangChainToolAdapter,
    CodeForgeToolAdapter,
    adapt_tools_for_langchain,
    adapt_tools_for_forge,
)
from code_forge.tools.base import BaseTool, ToolParameter, ToolResult, ToolCategory, ExecutionContext


class TestLangChainToolAdapter:
    """Tests for LangChainToolAdapter."""

    def test_adapter_name(self) -> None:
        """Test that adapter name matches wrapped tool."""

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            category = ToolCategory.FILE
            parameters: list[ToolParameter] = []

        tool = MockTool()
        adapter = LangChainToolAdapter(forge_tool=tool)

        assert adapter.name == "mock_tool"

    def test_adapter_description(self) -> None:
        """Test that adapter description matches wrapped tool."""

        class MockTool:
            name = "mock_tool"
            description = "A detailed description"
            category = ToolCategory.FILE
            parameters: list[ToolParameter] = []

        tool = MockTool()
        adapter = LangChainToolAdapter(forge_tool=tool)

        assert adapter.description == "A detailed description"

    def test_args_schema_generation(self) -> None:
        """Test that args_schema is generated from parameters."""

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            category = ToolCategory.FILE
            parameters = [
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file",
                    required=True,
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding",
                    required=False,
                    default="utf-8",
                ),
            ]

        tool = MockTool()
        adapter = LangChainToolAdapter(forge_tool=tool)

        # Access the args_schema - it's a dynamically created Pydantic model
        schema_class = adapter.args_schema

        assert isinstance(schema_class, type)
        assert issubclass(schema_class, BaseModel)

        # Check schema has the right fields
        fields = schema_class.model_fields
        assert "file_path" in fields
        assert "encoding" in fields

    def test_args_schema_type_mapping(self) -> None:
        """Test that parameter types are correctly mapped."""

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            category = ToolCategory.FILE
            parameters = [
                ToolParameter(name="count", type="integer", description="A count", required=True),
                ToolParameter(name="ratio", type="number", description="A ratio", required=True),
                ToolParameter(name="enabled", type="boolean", description="Flag", required=True),
                ToolParameter(name="items", type="array", description="Items", required=True),
                ToolParameter(name="config", type="object", description="Config", required=True),
            ]

        tool = MockTool()
        adapter = LangChainToolAdapter(forge_tool=tool)

        # Access the args_schema - it's a dynamically created Pydantic model
        schema_class = adapter.args_schema
        assert isinstance(schema_class, type)
        json_schema = schema_class.model_json_schema()

        props = json_schema.get("properties", {})
        assert "count" in props
        assert "ratio" in props
        assert "enabled" in props
        assert "items" in props
        assert "config" in props

    @pytest.mark.asyncio
    async def test_arun_success(self) -> None:
        """Test async execution returns formatted result."""
        from unittest.mock import AsyncMock, MagicMock

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            category = ToolCategory.FILE
            parameters = [
                ToolParameter(name="input", type="string", description="Input", required=True),
            ]

            async def execute(self, context, **kwargs):
                return ToolResult(success=True, output="Received: test")

        tool = MockTool()
        mock_context = ExecutionContext(working_dir="/tmp")

        adapter = LangChainToolAdapter(
            forge_tool=tool,
            context=mock_context,
        )

        result = await adapter._arun(input="test")

        assert result == "Received: test"

    @pytest.mark.asyncio
    async def test_arun_error(self) -> None:
        """Test async execution returns error message."""

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            category = ToolCategory.FILE
            parameters: list[ToolParameter] = []

            async def execute(self, context, **kwargs):
                return ToolResult(success=False, error="Something went wrong")

        tool = MockTool()
        mock_context = ExecutionContext(working_dir="/tmp")

        adapter = LangChainToolAdapter(
            forge_tool=tool,
            context=mock_context,
        )

        result = await adapter._arun()

        assert "Error:" in result
        assert "Something went wrong" in result


class TestCodeForgeToolAdapter:
    """Tests for CodeForgeToolAdapter."""

    def test_adapter_name(self) -> None:
        """Test that adapter name matches wrapped tool."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A LangChain tool"

            def _run(self, **kwargs):
                return "ok"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        assert adapter.name == "lc_mock_tool"

    def test_adapter_description(self) -> None:
        """Test that adapter description matches wrapped tool."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A detailed description for LC tool"

            def _run(self, **kwargs):
                return "ok"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        assert adapter.description == "A detailed description for LC tool"

    def test_extract_parameters_from_schema(self) -> None:
        """Test parameter extraction from args_schema."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class InputSchema(BaseModel):
            query: str
            max_results: int = 10

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A tool with schema"
            args_schema: type[BaseModel] = InputSchema

            def _run(self, query: str, max_results: int = 10):
                return f"Query: {query}, Max: {max_results}"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        params = adapter.parameters

        # Should have extracted parameters
        param_names = [p.name for p in params]
        assert "query" in param_names
        assert "max_results" in param_names

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful execution."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A LangChain tool"

            def _run(self, **kwargs):
                return "success result"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        result = await adapter.execute({}, None)

        assert result.success is True
        assert result.output == "success result"

    @pytest.mark.asyncio
    async def test_execute_error(self) -> None:
        """Test error handling in execution."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A LangChain tool"

            def _run(self, **kwargs):
                raise ValueError("Tool failed")

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        result = await adapter.execute({}, None)

        assert result.success is False
        assert "Tool failed" in result.error

    def test_to_openai_schema(self) -> None:
        """Test OpenAI schema generation."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class InputSchema(BaseModel):
            query: str

        class MockLCTool(LCBaseTool):
            name: str = "search_tool"
            description: str = "Search for information"
            args_schema: type[BaseModel] = InputSchema

            def _run(self, query: str):
                return "results"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        schema = adapter.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search_tool"
        assert schema["function"]["description"] == "Search for information"


class TestBatchAdaptation:
    """Tests for batch tool adaptation."""

    def test_adapt_tools_for_langchain(self) -> None:
        """Test adapting multiple Code-Forge tools for LangChain."""

        class MockTool1:
            name = "tool1"
            description = "Tool 1"
            category = ToolCategory.FILE
            parameters: list[ToolParameter] = []

        class MockTool2:
            name = "tool2"
            description = "Tool 2"
            category = ToolCategory.FILE
            parameters: list[ToolParameter] = []

        tools = [MockTool1(), MockTool2()]
        adapted = adapt_tools_for_langchain(tools)

        assert len(adapted) == 2
        assert all(isinstance(t, LangChainToolAdapter) for t in adapted)
        assert adapted[0].name == "tool1"
        assert adapted[1].name == "tool2"

    def test_adapt_tools_for_forge(self) -> None:
        """Test adapting multiple LangChain tools for Code-Forge."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool1(LCBaseTool):
            name: str = "lc_tool1"
            description: str = "LC Tool 1"

            def _run(self, **kwargs):
                return "ok"

        class MockLCTool2(LCBaseTool):
            name: str = "lc_tool2"
            description: str = "LC Tool 2"

            def _run(self, **kwargs):
                return "ok"

        tools = [MockLCTool1(), MockLCTool2()]
        adapted = adapt_tools_for_forge(tools)

        assert len(adapted) == 2
        assert all(isinstance(t, CodeForgeToolAdapter) for t in adapted)
        assert adapted[0].name == "lc_tool1"
        assert adapted[1].name == "lc_tool2"

    def test_empty_list_adaptation(self) -> None:
        """Test that empty lists return empty lists."""
        assert adapt_tools_for_langchain([]) == []
        assert adapt_tools_for_forge([]) == []


class TestLangChainToolAdapterSync:
    """Tests for synchronous LangChainToolAdapter methods."""

    def test_run_sync(self) -> None:
        """Test synchronous _run method."""

        class MockTool:
            name = "mock_tool"
            description = "A mock tool"
            category = ToolCategory.FILE
            parameters = [
                ToolParameter(name="input", type="string", description="Input", required=True),
            ]

            async def execute(self, context, **kwargs):
                return ToolResult(success=True, output="Sync result")

        tool = MockTool()
        mock_context = ExecutionContext(working_dir="/tmp")

        adapter = LangChainToolAdapter(
            forge_tool=tool,
            context=mock_context,
        )

        # Test sync execution
        result = adapter._run(input="test")

        assert result == "Sync result"


class TestCodeForgeToolAdapterEdgeCases:
    """Edge case tests for CodeForgeToolAdapter."""

    def test_category_property(self) -> None:
        """Test category property returns OTHER."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A LangChain tool"

            def _run(self, **kwargs):
                return "ok"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        from code_forge.tools.base import ToolCategory
        assert adapter.category == ToolCategory.OTHER

    def test_requires_confirmation_property(self) -> None:
        """Test requires_confirmation returns False."""
        from langchain_core.tools import BaseTool as LCBaseTool

        class MockLCTool(LCBaseTool):
            name: str = "lc_mock_tool"
            description: str = "A LangChain tool"

            def _run(self, **kwargs):
                return "ok"

        tool = MockLCTool()
        adapter = CodeForgeToolAdapter(langchain_tool=tool)

        assert adapter.requires_confirmation is False
