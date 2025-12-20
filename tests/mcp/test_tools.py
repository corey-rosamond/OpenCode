"""Tests for MCP tool adapter and registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from code_forge.mcp.client import MCPClient
from code_forge.mcp.protocol import MCPTool
from code_forge.mcp.tools import MCPToolAdapter, MCPToolRegistry, _sanitize_name


class TestSanitizeName:
    """Tests for _sanitize_name function."""

    def test_simple_name(self) -> None:
        """Test simple name."""
        assert _sanitize_name("test") == "test"

    def test_hyphen_replacement(self) -> None:
        """Test hyphen replacement."""
        assert _sanitize_name("test-name") == "test_name"

    def test_dot_replacement(self) -> None:
        """Test dot replacement."""
        assert _sanitize_name("test.name") == "test_name"

    def test_slash_replacement(self) -> None:
        """Test slash replacement."""
        assert _sanitize_name("test/name") == "test_name"

    def test_special_chars_removal(self) -> None:
        """Test removal of special characters."""
        assert _sanitize_name("test@name!") == "testname"

    def test_leading_number(self) -> None:
        """Test handling of leading numbers."""
        assert _sanitize_name("123test") == "_123test"

    def test_mixed(self) -> None:
        """Test mixed cases."""
        assert _sanitize_name("my-server.v2/tool") == "my_server_v2_tool"


class TestMCPToolAdapter:
    """Tests for MCPToolAdapter."""

    def test_initialization(self) -> None:
        """Test adapter initialization."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")
        assert adapter.client is client
        assert adapter.server_name == "test-server"
        assert adapter._sanitized_server == "test_server"

    def test_get_tool_name(self) -> None:
        """Test tool name generation."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "my-server")

        tool = MCPTool(name="read_file", description="Read", input_schema={})
        name = adapter.get_tool_name(tool)
        assert name == "mcp__my_server__read_file"

    def test_get_tool_name_complex(self) -> None:
        """Test tool name generation with complex names."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "my.server.v2")

        tool = MCPTool(name="read-file", description="Read", input_schema={})
        name = adapter.get_tool_name(tool)
        assert name == "mcp__my_server_v2__read_file"

    def test_get_original_tool_name(self) -> None:
        """Test extracting original tool name."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "my-server")

        result = adapter.get_original_tool_name("mcp__my_server__read_file")
        assert result == "read_file"

    def test_get_original_tool_name_wrong_server(self) -> None:
        """Test extracting tool name from wrong server."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "my-server")

        result = adapter.get_original_tool_name("mcp__other_server__read_file")
        assert result is None

    def test_create_tool_definition(self) -> None:
        """Test creating tool definition."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tool = MCPTool(
            name="write_file",
            description="Write to a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )

        definition = adapter.create_tool_definition(tool)

        assert definition["name"] == "mcp__test_server__write_file"
        assert definition["description"] == "Write to a file"
        assert definition["parameters"] == tool.input_schema
        assert definition["mcp_server"] == "test-server"
        assert definition["mcp_tool"] == "write_file"

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        """Test tool execution."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(
            return_value=[{"type": "text", "text": "Result"}]
        )
        adapter = MCPToolAdapter(client, "test-server")

        result = await adapter.execute(
            "mcp__test_server__read_file",
            {"path": "/tmp/test"},
        )

        assert result == "Result"
        client.call_tool.assert_called_once_with(
            "read_file",
            {"path": "/tmp/test"},
        )

    @pytest.mark.asyncio
    async def test_execute_invalid_name(self) -> None:
        """Test execution with invalid tool name."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        with pytest.raises(ValueError, match="Invalid MCP tool name"):
            await adapter.execute("invalid_name", {})

    @pytest.mark.asyncio
    async def test_execute_empty_result(self) -> None:
        """Test execution with empty result."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(return_value=[])
        adapter = MCPToolAdapter(client, "test-server")

        result = await adapter.execute("mcp__test_server__test", {})
        assert result == ""

    @pytest.mark.asyncio
    async def test_execute_multiple_results(self) -> None:
        """Test execution with multiple result items."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(
            return_value=[
                {"type": "text", "text": "Line 1"},
                {"type": "text", "text": "Line 2"},
            ]
        )
        adapter = MCPToolAdapter(client, "test-server")

        result = await adapter.execute("mcp__test_server__test", {})
        assert result == "Line 1\nLine 2"

    @pytest.mark.asyncio
    async def test_execute_image_result(self) -> None:
        """Test execution with image result."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(
            return_value=[{"type": "image", "mimeType": "image/png"}]
        )
        adapter = MCPToolAdapter(client, "test-server")

        result = await adapter.execute("mcp__test_server__test", {})
        assert result == "[Image: image/png]"

    @pytest.mark.asyncio
    async def test_execute_resource_result(self) -> None:
        """Test execution with resource result."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(
            return_value=[{"type": "resource", "uri": "file:///test"}]
        )
        adapter = MCPToolAdapter(client, "test-server")

        result = await adapter.execute("mcp__test_server__test", {})
        assert result == "[Resource: file:///test]"

    @pytest.mark.asyncio
    async def test_execute_unknown_type(self) -> None:
        """Test execution with unknown result type."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(
            return_value=[{"type": "custom", "data": "value"}]
        )
        adapter = MCPToolAdapter(client, "test-server")

        result = await adapter.execute("mcp__test_server__test", {})
        assert "custom" in result


class TestMCPToolRegistry:
    """Tests for MCPToolRegistry."""

    def test_initialization(self) -> None:
        """Test registry initialization."""
        registry = MCPToolRegistry()
        assert registry.list_tools() == []

    def test_register_server_tools(self) -> None:
        """Test registering tools from a server."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [
            MCPTool(name="tool1", description="Tool 1", input_schema={}),
            MCPTool(name="tool2", description="Tool 2", input_schema={}),
        ]

        registered = registry.register_server_tools(adapter, tools)

        assert len(registered) == 2
        assert "mcp__test_server__tool1" in registered
        assert "mcp__test_server__tool2" in registered
        assert len(registry.list_tools()) == 2

    def test_unregister_server_tools(self) -> None:
        """Test unregistering tools from a server."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="tool1", description="Tool 1", input_schema={})]
        registry.register_server_tools(adapter, tools)

        unregistered = registry.unregister_server_tools("test-server")

        assert len(unregistered) == 1
        assert len(registry.list_tools()) == 0

    def test_unregister_preserves_other_servers(self) -> None:
        """Test that unregistering preserves other servers' tools."""
        registry = MCPToolRegistry()
        client1 = MagicMock(spec=MCPClient)
        client2 = MagicMock(spec=MCPClient)
        adapter1 = MCPToolAdapter(client1, "server1")
        adapter2 = MCPToolAdapter(client2, "server2")

        tools1 = [MCPTool(name="tool1", description="", input_schema={})]
        tools2 = [MCPTool(name="tool2", description="", input_schema={})]

        registry.register_server_tools(adapter1, tools1)
        registry.register_server_tools(adapter2, tools2)

        registry.unregister_server_tools("server1")

        assert len(registry.list_tools()) == 1
        assert registry.has_tool("mcp__server2__tool2")

    def test_get_tool(self) -> None:
        """Test getting a tool definition."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="test", description="Test", input_schema={})]
        registry.register_server_tools(adapter, tools)

        tool = registry.get_tool("mcp__test_server__test")
        assert isinstance(tool, dict)
        assert tool["description"] == "Test"

    def test_get_tool_not_found(self) -> None:
        """Test getting a non-existent tool."""
        registry = MCPToolRegistry()
        assert registry.get_tool("nonexistent") is None

    def test_get_adapter(self) -> None:
        """Test getting an adapter for a tool."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="test", description="Test", input_schema={})]
        registry.register_server_tools(adapter, tools)

        result = registry.get_adapter("mcp__test_server__test")
        assert result is adapter

    def test_get_adapter_not_found(self) -> None:
        """Test getting adapter for non-existent tool."""
        registry = MCPToolRegistry()
        assert registry.get_adapter("nonexistent") is None

    def test_get_original_name(self) -> None:
        """Test getting original tool name."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="read_file", description="", input_schema={})]
        registry.register_server_tools(adapter, tools)

        original = registry.get_original_name("mcp__test_server__read_file")
        assert original == "read_file"

    def test_has_tool(self) -> None:
        """Test checking if tool exists."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="test", description="", input_schema={})]
        registry.register_server_tools(adapter, tools)

        assert registry.has_tool("mcp__test_server__test")
        assert not registry.has_tool("nonexistent")

    def test_is_mcp_tool(self) -> None:
        """Test checking if name is MCP tool format."""
        registry = MCPToolRegistry()
        assert registry.is_mcp_tool("mcp__server__tool")
        assert not registry.is_mcp_tool("regular_tool")

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        """Test executing a tool through the registry."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(
            return_value=[{"type": "text", "text": "Success"}]
        )
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="test", description="", input_schema={})]
        registry.register_server_tools(adapter, tools)

        result = await registry.execute(
            "mcp__test_server__test",
            {"arg": "value"},
        )

        assert result == "Success"
        client.call_tool.assert_called_once_with("test", {"arg": "value"})

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self) -> None:
        """Test executing unknown tool."""
        registry = MCPToolRegistry()

        with pytest.raises(ValueError, match="Unknown MCP tool"):
            await registry.execute("nonexistent", {})

    def test_get_tools_for_server(self) -> None:
        """Test getting tools for a specific server."""
        registry = MCPToolRegistry()
        client1 = MagicMock(spec=MCPClient)
        client2 = MagicMock(spec=MCPClient)
        adapter1 = MCPToolAdapter(client1, "server1")
        adapter2 = MCPToolAdapter(client2, "server2")

        tools1 = [
            MCPTool(name="tool1", description="", input_schema={}),
            MCPTool(name="tool2", description="", input_schema={}),
        ]
        tools2 = [MCPTool(name="tool3", description="", input_schema={})]

        registry.register_server_tools(adapter1, tools1)
        registry.register_server_tools(adapter2, tools2)

        server1_tools = registry.get_tools_for_server("server1")
        assert len(server1_tools) == 2

        server2_tools = registry.get_tools_for_server("server2")
        assert len(server2_tools) == 1

    def test_clear(self) -> None:
        """Test clearing all tools."""
        registry = MCPToolRegistry()
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test-server")

        tools = [MCPTool(name="test", description="", input_schema={})]
        registry.register_server_tools(adapter, tools)

        registry.clear()

        assert len(registry.list_tools()) == 0
        assert not registry.has_tool("mcp__test_server__test")
