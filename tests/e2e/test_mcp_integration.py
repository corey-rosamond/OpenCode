"""E2E tests for MCP (Model Context Protocol) integration.

Tests the complete MCP server lifecycle including connection,
tool discovery, and execution flows.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.mcp.client import MCPClient, MCPClientError
from code_forge.mcp.config import MCPConfig, MCPServerConfig, MCPSettings
from code_forge.mcp.manager import MCPConnection, MCPManager
from code_forge.mcp.protocol import MCPPrompt, MCPResource, MCPTool
from code_forge.mcp.tools import MCPToolAdapter, MCPToolRegistry

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mcp_config() -> MCPConfig:
    """Create MCP configuration for tests."""
    return MCPConfig(
        servers={
            "test-server": MCPServerConfig(
                name="test-server",
                transport="stdio",
                command="python",
                args=["-m", "test_mcp_server"],
                enabled=True,
                auto_connect=True,
            ),
            "disabled-server": MCPServerConfig(
                name="disabled-server",
                transport="stdio",
                command="python",
                args=["-m", "disabled_server"],
                enabled=False,
                auto_connect=False,
            ),
            "http-server": MCPServerConfig(
                name="http-server",
                transport="streamable-http",
                url="http://localhost:8080/mcp",
                enabled=True,
                auto_connect=False,
            ),
        },
        settings=MCPSettings(
            timeout=30,
            reconnect_attempts=3,
            reconnect_delay=1.0,
        ),
    )


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create mock MCP client."""
    client = MagicMock(spec=MCPClient)
    client.is_connected = True
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.list_tools = AsyncMock(return_value=[
        MCPTool(
            name="read_file",
            description="Read a file from disk",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        ),
        MCPTool(
            name="write_file",
            description="Write content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        ),
    ])
    client.list_resources = AsyncMock(return_value=[
        MCPResource(
            uri="file:///project/README.md",
            name="README",
            description="Project README",
        ),
    ])
    client.list_prompts = AsyncMock(return_value=[
        MCPPrompt(
            name="summarize",
            description="Summarize content",
            arguments=[{"name": "text", "required": True}],
        ),
    ])
    client.call_tool = AsyncMock(return_value={"result": "success"})
    client.read_resource = AsyncMock(return_value=[{"text": "# README\nProject docs"}])
    client.get_prompt = AsyncMock(return_value=[
        MagicMock(to_dict=lambda: {"role": "user", "content": "Summarize: test"})
    ])
    return client


@pytest.fixture
def mock_transport() -> MagicMock:
    """Create mock transport."""
    transport = MagicMock()
    transport.connect = AsyncMock()
    transport.disconnect = AsyncMock()
    transport.send = AsyncMock()
    transport.receive = AsyncMock()
    return transport


# =============================================================================
# Test Server Connection Lifecycle
# =============================================================================


class TestServerConnectionLifecycle:
    """Tests for MCP server connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_to_server(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Successfully connect to MCP server."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connection = await manager.connect("test-server")

        assert connection.name == "test-server"
        assert connection.is_connected
        assert len(connection.tools) == 2
        mock_mcp_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_to_disabled_server_fails(
        self, mcp_config: MCPConfig
    ) -> None:
        """Connecting to disabled server raises error."""
        manager = MCPManager(mcp_config)

        with pytest.raises(ValueError, match="disabled"):
            await manager.connect("disabled-server")

    @pytest.mark.asyncio
    async def test_connect_to_unknown_server_fails(
        self, mcp_config: MCPConfig
    ) -> None:
        """Connecting to unknown server raises error."""
        manager = MCPManager(mcp_config)

        with pytest.raises(ValueError, match="Unknown server"):
            await manager.connect("nonexistent-server")

    @pytest.mark.asyncio
    async def test_disconnect_from_server(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Successfully disconnect from MCP server."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")
                await manager.disconnect("test-server")

        assert manager.get_connection("test-server") is None
        mock_mcp_client.disconnect.assert_called()

    @pytest.mark.asyncio
    async def test_reconnect_to_server(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Successfully reconnect to MCP server."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")
                connection = await manager.reconnect("test-server")

        assert connection.is_connected
        # Connect called twice (initial + reconnect)
        assert mock_mcp_client.connect.call_count == 2


# =============================================================================
# Test Tool Discovery
# =============================================================================


class TestToolDiscovery:
    """Tests for MCP tool discovery."""

    @pytest.mark.asyncio
    async def test_tools_discovered_on_connect(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Tools are discovered when connecting."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connection = await manager.connect("test-server")

        assert len(connection.tools) == 2
        tool_names = [t.name for t in connection.tools]
        assert "read_file" in tool_names
        assert "write_file" in tool_names

    @pytest.mark.asyncio
    async def test_tools_registered_in_registry(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Tools are registered in tool registry."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")

        # Check registry has tools
        all_tools = manager.tool_registry.list_tools()
        assert len(all_tools) >= 2

    @pytest.mark.asyncio
    async def test_get_all_tools_aggregates_connections(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """get_all_tools aggregates tools from all connections."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")

        tools = manager.get_all_tools()
        assert len(tools) == 2


# =============================================================================
# Test Resource Discovery
# =============================================================================


class TestResourceDiscovery:
    """Tests for MCP resource discovery."""

    @pytest.mark.asyncio
    async def test_resources_discovered_on_connect(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Resources are discovered when connecting."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connection = await manager.connect("test-server")

        assert len(connection.resources) == 1
        assert connection.resources[0].name == "README"

    @pytest.mark.asyncio
    async def test_read_resource_from_server(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Successfully read resource from server."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")
                content = await manager.read_resource(
                    "test-server",
                    "file:///project/README.md",
                )

        assert len(content) == 1
        assert "README" in content[0]["text"]


# =============================================================================
# Test Prompt Discovery
# =============================================================================


class TestPromptDiscovery:
    """Tests for MCP prompt discovery."""

    @pytest.mark.asyncio
    async def test_prompts_discovered_on_connect(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Prompts are discovered when connecting."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connection = await manager.connect("test-server")

        assert len(connection.prompts) == 1
        assert connection.prompts[0].name == "summarize"

    @pytest.mark.asyncio
    async def test_get_prompt_from_server(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Successfully get prompt from server."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")
                messages = await manager.get_prompt(
                    "test-server",
                    "summarize",
                    {"text": "test content"},
                )

        assert len(messages) == 1
        assert messages[0]["role"] == "user"


# =============================================================================
# Test Multi-Server Management
# =============================================================================


class TestMultiServerManagement:
    """Tests for managing multiple MCP servers."""

    @pytest.mark.asyncio
    async def test_connect_all_auto_connect_servers(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """connect_all connects to all auto_connect servers."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connections = await manager.connect_all()

        # Only test-server has auto_connect=True
        assert len(connections) == 1
        assert connections[0].name == "test-server"

    @pytest.mark.asyncio
    async def test_disconnect_all_servers(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """disconnect_all disconnects from all servers."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect_all()
                await manager.disconnect_all()

        assert len(manager.list_connections()) == 0

    @pytest.mark.asyncio
    async def test_list_connections(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """list_connections returns all active connections."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")
                connections = manager.list_connections()

        assert len(connections) == 1

    @pytest.mark.asyncio
    async def test_is_connected_check(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """is_connected correctly reports connection status."""
        manager = MCPManager(mcp_config)

        assert not manager.is_connected("test-server")

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")

        assert manager.is_connected("test-server")


# =============================================================================
# Test Connection Retry Logic
# =============================================================================


class TestConnectionRetryLogic:
    """Tests for connection retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_failure(
        self, mcp_config: MCPConfig
    ) -> None:
        """Connection is retried on failure."""
        manager = MCPManager(mcp_config)
        call_count = 0

        async def failing_connect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")

        mock_client = MagicMock(spec=MCPClient)
        mock_client.is_connected = True
        mock_client.connect = AsyncMock(side_effect=failing_connect)
        mock_client.disconnect = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_client,
            ):
                connection = await manager.connect("test-server")

        assert connection.is_connected
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mcp_config: MCPConfig) -> None:
        """MCPClientError raised after max retries exceeded."""
        manager = MCPManager(mcp_config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(side_effect=ConnectionError("Always fails"))
        mock_client.disconnect = AsyncMock()

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_client,
            ):
                with pytest.raises(MCPClientError, match="Failed to connect"):
                    await manager.connect("test-server")


# =============================================================================
# Test Tool Execution Flow
# =============================================================================


class TestToolExecutionFlow:
    """Tests for MCP tool execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_via_adapter(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Successfully execute tool via adapter."""
        manager = MCPManager(mcp_config)

        # Mock the tool result as a list of content items
        mock_mcp_client.call_tool = AsyncMock(
            return_value=[{"type": "text", "text": "success"}]
        )

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connection = await manager.connect("test-server")

        # Execute tool through adapter using namespaced name
        result = await connection.adapter.execute(
            "mcp__test_server__read_file",
            {"path": "/test.txt"},
        )
        assert result == "success"

    @pytest.mark.asyncio
    async def test_tool_not_found_error(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Error when tool not found."""
        manager = MCPManager(mcp_config)

        mock_mcp_client.call_tool = AsyncMock(
            side_effect=MCPClientError("Tool not found: unknown_tool")
        )

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                connection = await manager.connect("test-server")

        with pytest.raises(MCPClientError, match="Tool not found"):
            await connection.adapter.execute(
                "mcp__test_server__unknown_tool",
                {},
            )


# =============================================================================
# Test Manager Status
# =============================================================================


class TestManagerStatus:
    """Tests for MCP manager status reporting."""

    @pytest.mark.asyncio
    async def test_get_status_summary(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """get_status returns summary of manager state."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")

        status = manager.get_status()

        assert status["configured_servers"] == 3
        assert status["connected_servers"] == 1
        assert "test-server" in status["connections"]
        assert status["connections"]["test-server"]["connected"] is True
        assert status["connections"]["test-server"]["tools"] == 2


# =============================================================================
# Test Configuration Reload
# =============================================================================


class TestConfigurationReload:
    """Tests for dynamic configuration reload."""

    @pytest.mark.asyncio
    async def test_reload_config_disconnects_changed_servers(
        self, mcp_config: MCPConfig, mock_mcp_client: MagicMock
    ) -> None:
        """Reloading config disconnects changed servers."""
        manager = MCPManager(mcp_config)

        with patch.object(manager, "_create_transport"):
            with patch(
                "code_forge.mcp.manager.MCPClient",
                return_value=mock_mcp_client,
            ):
                await manager.connect("test-server")

                # Modify config to mark server as changed
                new_config = MCPConfig(
                    servers={
                        "test-server": MCPServerConfig(
                            name="test-server",
                            transport="stdio",
                            command="different-command",  # Changed!
                            args=[],
                            enabled=True,
                            auto_connect=True,
                        ),
                    },
                    settings=MCPSettings(),
                )

                with patch(
                    "code_forge.mcp.config.MCPConfigLoader.load",
                    return_value=new_config,
                ):
                    await manager.reload_config()

        # Server was reconnected due to config change
        mock_mcp_client.disconnect.assert_called()


# =============================================================================
# Test Tool Registry Operations
# =============================================================================


class TestToolRegistryOperations:
    """Tests for MCP tool registry."""

    def test_register_and_list_tools(self) -> None:
        """Register and list tools in registry."""
        registry = MCPToolRegistry()
        mock_client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(mock_client, "test-server")

        tools = [
            MCPTool(name="tool1", description="First tool", input_schema={}),
            MCPTool(name="tool2", description="Second tool", input_schema={}),
        ]

        registry.register_server_tools(adapter, tools)

        all_tools = registry.list_tools()
        assert len(all_tools) == 2

    def test_unregister_server_tools(self) -> None:
        """Unregister all tools from a server."""
        registry = MCPToolRegistry()
        mock_client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(mock_client, "test-server")

        tools = [
            MCPTool(name="tool1", description="First tool", input_schema={}),
        ]

        registry.register_server_tools(adapter, tools)
        registry.unregister_server_tools("test-server")

        assert len(registry.list_tools()) == 0

    def test_get_tool_by_name(self) -> None:
        """Get specific tool by name."""
        registry = MCPToolRegistry()
        mock_client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(mock_client, "test-server")

        tools = [
            MCPTool(name="my_tool", description="My tool", input_schema={}),
        ]

        registry.register_server_tools(adapter, tools)

        # Use the namespaced name
        tool_info = registry.get_tool("mcp__test_server__my_tool")
        assert tool_info is not None
        assert tool_info["name"] == "mcp__test_server__my_tool"
        assert tool_info["mcp_tool"] == "my_tool"


# =============================================================================
# Test Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for MCPManager singleton pattern."""

    def test_get_instance_creates_singleton(self) -> None:
        """get_instance creates singleton."""
        MCPManager.reset_instance()

        instance1 = MCPManager.get_instance()
        instance2 = MCPManager.get_instance()

        assert instance1 is instance2
        MCPManager.reset_instance()

    def test_set_instance_overrides_singleton(self) -> None:
        """set_instance can override singleton."""
        MCPManager.reset_instance()

        custom = MCPManager()
        MCPManager.set_instance(custom)

        assert MCPManager.get_instance() is custom
        MCPManager.reset_instance()

    def test_reset_instance_clears_singleton(self) -> None:
        """reset_instance clears singleton."""
        MCPManager.reset_instance()
        MCPManager.get_instance()
        MCPManager.reset_instance()

        # Next call creates new instance
        new_instance = MCPManager.get_instance()
        assert new_instance is not None
        MCPManager.reset_instance()
