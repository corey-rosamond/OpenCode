"""Tests for MCP connection manager."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.mcp.client import MCPClient, MCPClientError
from code_forge.mcp.config import MCPConfig, MCPServerConfig, MCPSettings
from code_forge.mcp.manager import MCPConnection, MCPManager
from code_forge.mcp.protocol import (
    MCPCapabilities,
    MCPPrompt,
    MCPResource,
    MCPServerInfo,
    MCPTool,
)


class TestMCPConnection:
    """Tests for MCPConnection."""

    def test_creation(self) -> None:
        """Test connection creation."""
        client = MagicMock(spec=MCPClient)
        client.is_connected = True
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test",
        )
        adapter = MagicMock()

        connection = MCPConnection(
            name="test",
            client=client,
            config=config,
            adapter=adapter,
            tools=[],
            resources=[],
            prompts=[],
        )

        assert connection.name == "test"
        assert connection.is_connected is True

    def test_is_connected_property(self) -> None:
        """Test is_connected property."""
        client = MagicMock(spec=MCPClient)
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test",
        )

        connection = MCPConnection(
            name="test",
            client=client,
            config=config,
            adapter=MagicMock(),
        )

        client.is_connected = True
        assert connection.is_connected is True

        client.is_connected = False
        assert connection.is_connected is False


class TestMCPManager:
    """Tests for MCPManager."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        MCPManager.reset_instance()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        MCPManager.reset_instance()

    def test_initialization(self) -> None:
        """Test manager initialization."""
        config = MCPConfig()
        manager = MCPManager(config)
        assert manager.config is config
        assert isinstance(manager.tool_registry, MCPToolRegistry)
        assert manager.list_connections() == []

    def test_get_instance_singleton(self) -> None:
        """Test singleton pattern."""
        manager1 = MCPManager.get_instance()
        manager2 = MCPManager.get_instance()
        assert manager1 is manager2

    def test_set_instance(self) -> None:
        """Test setting custom instance."""
        config = MCPConfig()
        custom_manager = MCPManager(config)
        MCPManager.set_instance(custom_manager)

        assert MCPManager.get_instance() is custom_manager

    def test_reset_instance(self) -> None:
        """Test resetting singleton."""
        manager1 = MCPManager.get_instance()
        MCPManager.reset_instance()
        manager2 = MCPManager.get_instance()
        assert manager1 is not manager2

    @pytest.mark.asyncio
    async def test_connect_unknown_server(self) -> None:
        """Test connecting to unknown server."""
        config = MCPConfig()
        manager = MCPManager(config)

        with pytest.raises(ValueError, match="Unknown server"):
            await manager.connect("nonexistent")

    @pytest.mark.asyncio
    async def test_connect_disabled_server(self) -> None:
        """Test connecting to disabled server."""
        config = MCPConfig(
            servers={
                "disabled": MCPServerConfig(
                    name="disabled",
                    transport="stdio",
                    command="test",
                    enabled=False,
                )
            }
        )
        manager = MCPManager(config)

        with pytest.raises(ValueError, match="disabled"):
            await manager.connect("disabled")

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful connection."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="echo",  # Use echo for simple test
                )
            }
        )
        manager = MCPManager(config)

        # Mock the transport and client
        mock_transport = MagicMock()
        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test-server",
                version="1.0.0",
                capabilities=MCPCapabilities(tools=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport", return_value=mock_transport):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                connection = await manager.connect("test")

                assert connection.name == "test"
                assert manager.is_connected("test")

                await manager.disconnect("test")

    @pytest.mark.asyncio
    async def test_connect_already_connected(self) -> None:
        """Test connecting when already connected returns existing connection."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="echo",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                conn1 = await manager.connect("test")
                conn2 = await manager.connect("test")

                assert conn1 is conn2

                await manager.disconnect("test")

    @pytest.mark.asyncio
    async def test_connect_all(self) -> None:
        """Test connecting to all auto-connect servers."""
        config = MCPConfig(
            servers={
                "auto1": MCPServerConfig(
                    name="auto1",
                    transport="stdio",
                    command="test",
                    auto_connect=True,
                ),
                "auto2": MCPServerConfig(
                    name="auto2",
                    transport="stdio",
                    command="test",
                    auto_connect=True,
                ),
                "manual": MCPServerConfig(
                    name="manual",
                    transport="stdio",
                    command="test",
                    auto_connect=False,
                ),
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                connections = await manager.connect_all()

                assert len(connections) == 2
                names = [c.name for c in connections]
                assert "auto1" in names
                assert "auto2" in names
                assert "manual" not in names

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnecting from a server."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="echo",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(tools=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(
            return_value=[MCPTool(name="tool1", description="", input_schema={})]
        )
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")
                assert len(manager.tool_registry.list_tools()) == 1

                await manager.disconnect("test")

                assert not manager.is_connected("test")
                assert manager.get_connection("test") is None
                assert len(manager.tool_registry.list_tools()) == 0

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self) -> None:
        """Test disconnecting when not connected."""
        manager = MCPManager(MCPConfig())
        await manager.disconnect("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_disconnect_all(self) -> None:
        """Test disconnecting from all servers."""
        config = MCPConfig(
            servers={
                "server1": MCPServerConfig(
                    name="server1",
                    transport="stdio",
                    command="test",
                ),
                "server2": MCPServerConfig(
                    name="server2",
                    transport="stdio",
                    command="test",
                ),
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("server1")
                await manager.connect("server2")
                assert len(manager.list_connections()) == 2

                await manager.disconnect_all()

                assert len(manager.list_connections()) == 0

    @pytest.mark.asyncio
    async def test_reconnect(self) -> None:
        """Test reconnecting to a server."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="echo",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")
                old_conn = manager.get_connection("test")

                new_conn = await manager.reconnect("test")

                # Should be a new connection
                assert new_conn is not old_conn
                assert manager.is_connected("test")

                await manager.disconnect_all()

    def test_get_connection(self) -> None:
        """Test getting a connection."""
        manager = MCPManager(MCPConfig())
        assert manager.get_connection("test") is None

    def test_list_connections(self) -> None:
        """Test listing connections."""
        manager = MCPManager(MCPConfig())
        assert manager.list_connections() == []

    def test_is_connected(self) -> None:
        """Test checking connection status."""
        manager = MCPManager(MCPConfig())
        assert not manager.is_connected("test")

    @pytest.mark.asyncio
    async def test_get_all_tools(self) -> None:
        """Test getting tools from all connections."""
        config = MCPConfig(
            servers={
                "server1": MCPServerConfig(
                    name="server1",
                    transport="stdio",
                    command="test",
                ),
                "server2": MCPServerConfig(
                    name="server2",
                    transport="stdio",
                    command="test",
                ),
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(tools=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        call_count = [0]

        async def mock_list_tools() -> list[MCPTool]:
            call_count[0] += 1
            return [
                MCPTool(
                    name=f"tool{call_count[0]}",
                    description="",
                    input_schema={},
                )
            ]

        mock_client.list_tools = mock_list_tools

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("server1")
                await manager.connect("server2")

                tools = manager.get_all_tools()
                assert len(tools) == 2

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_get_all_resources(self) -> None:
        """Test getting resources from all connections."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="test",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(resources=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(
            return_value=[MCPResource(uri="file:///test", name="test")]
        )
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")

                resources = manager.get_all_resources()
                assert len(resources) == 1
                assert resources[0].name == "test"

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_get_all_prompts(self) -> None:
        """Test getting prompts from all connections."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="test",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(prompts=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(
            return_value=[MCPPrompt(name="test-prompt")]
        )
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")

                prompts = manager.get_all_prompts()
                assert len(prompts) == 1
                assert prompts[0].name == "test-prompt"

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        """Test getting manager status."""
        config = MCPConfig(
            servers={
                "configured1": MCPServerConfig(
                    name="configured1",
                    transport="stdio",
                    command="test",
                ),
                "configured2": MCPServerConfig(
                    name="configured2",
                    transport="stdio",
                    command="test",
                ),
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(tools=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(
            return_value=[MCPTool(name="tool1", description="", input_schema={})]
        )
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("configured1")

                status = manager.get_status()

                assert status["configured_servers"] == 2
                assert status["connected_servers"] == 1
                assert status["total_tools"] == 1
                assert "configured1" in status["connections"]
                assert status["connections"]["configured1"]["connected"] is True
                assert status["connections"]["configured1"]["tools"] == 1

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_read_resource(self) -> None:
        """Test reading a resource through the manager."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="test",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(resources=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.read_resource = AsyncMock(
            return_value=[{"uri": "file:///test", "text": "content"}]
        )
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")

                result = await manager.read_resource("test", "file:///test")
                assert result == [{"uri": "file:///test", "text": "content"}]

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_read_resource_not_connected(self) -> None:
        """Test reading resource from disconnected server."""
        manager = MCPManager(MCPConfig())

        with pytest.raises(ValueError, match="Server not connected"):
            await manager.read_resource("test", "file:///test")

    @pytest.mark.asyncio
    async def test_get_prompt(self) -> None:
        """Test getting a prompt through the manager."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="test",
                )
            }
        )
        manager = MCPManager(config)

        from code_forge.mcp.protocol import MCPPromptMessage

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(prompts=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.get_prompt = AsyncMock(
            return_value=[MCPPromptMessage(role="user", content="Hello")]
        )
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")

                result = await manager.get_prompt("test", "summarize", {"length": "short"})
                assert len(result) == 1
                assert result[0]["role"] == "user"

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_get_prompt_not_connected(self) -> None:
        """Test getting prompt from disconnected server."""
        manager = MCPManager(MCPConfig())

        with pytest.raises(ValueError, match="Server not connected"):
            await manager.get_prompt("test", "summarize")

    @pytest.mark.asyncio
    async def test_create_transport_stdio(self) -> None:
        """Test creating stdio transport."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="python",
                    args=["-m", "server"],
                    env={"KEY": "value"},
                    cwd="/tmp",
                )
            }
        )
        manager = MCPManager(config)

        with patch("code_forge.mcp.manager.StdioTransport") as mock_stdio:
            manager._create_transport(config.servers["test"])
            mock_stdio.assert_called_once_with(
                command="python",
                args=["-m", "server"],
                env={"KEY": "value"},
                cwd="/tmp",
            )

    @pytest.mark.asyncio
    async def test_create_transport_http(self) -> None:
        """Test creating HTTP transport."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="http",
                    url="https://example.com",
                    headers={"Auth": "token"},
                )
            },
            settings=MCPSettings(timeout=60),
        )
        manager = MCPManager(config)

        with patch("code_forge.mcp.manager.HTTPTransport") as mock_http:
            manager._create_transport(config.servers["test"])
            mock_http.assert_called_once_with(
                url="https://example.com",
                headers={"Auth": "token"},
                timeout=60,
            )

    def test_create_transport_unknown(self) -> None:
        """Test creating transport with unknown type."""
        config = MCPConfig()
        manager = MCPManager(config)

        # Create a config with invalid transport (bypass validation)
        bad_config = MCPServerConfig.__new__(MCPServerConfig)
        bad_config.name = "test"
        bad_config.transport = "unknown"
        bad_config.command = "test"

        with pytest.raises(ValueError, match="Unknown transport"):
            manager._create_transport(bad_config)

    @pytest.mark.asyncio
    async def test_connect_registers_tools(self) -> None:
        """Test that connecting registers tools in the registry."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport="stdio",
                    command="test",
                )
            }
        )
        manager = MCPManager(config)

        mock_client = MagicMock(spec=MCPClient)
        mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(tools=True),
            )
        )
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(
            return_value=[
                MCPTool(name="tool1", description="Tool 1", input_schema={}),
                MCPTool(name="tool2", description="Tool 2", input_schema={}),
            ]
        )
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                await manager.connect("test")

                tools = manager.tool_registry.list_tools()
                assert len(tools) == 2

                # Verify tool names are namespaced
                tool_names = [t["name"] for t in tools]
                assert "mcp__test__tool1" in tool_names
                assert "mcp__test__tool2" in tool_names

                await manager.disconnect_all()
