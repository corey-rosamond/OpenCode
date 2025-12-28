"""Additional tests to boost coverage for MCP module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.mcp.client import MCPClient, MCPClientError
from code_forge.mcp.config import MCPConfig, MCPConfigLoader, MCPServerConfig, MCPSettings
from code_forge.mcp.manager import MCPConnection, MCPManager
from code_forge.mcp.protocol import (
    MCPCapabilities,
    MCPError,
    MCPNotification,
    MCPPrompt,
    MCPPromptArgument,
    MCPPromptMessage,
    MCPRequest,
    MCPResource,
    MCPResourceTemplate,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    parse_json_message,
    parse_message,
)
from code_forge.mcp.tools import MCPToolAdapter, MCPToolRegistry
from code_forge.mcp.transport.stdio import StdioTransport


class TestMCPManagerAdditional:
    """Additional tests for MCPManager."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        MCPManager.reset_instance()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        MCPManager.reset_instance()

    @pytest.mark.asyncio
    async def test_connect_with_missing_command(self) -> None:
        """Test connect fails for stdio with missing command."""
        from unittest.mock import MagicMock

        # Create config with mock server config (bypass Pydantic validation)
        config = MCPConfig()
        mock_server = MagicMock(spec=MCPServerConfig)
        mock_server.name = "test"
        mock_server.transport = "stdio"
        mock_server.command = None
        mock_server.enabled = True
        mock_server.args = None
        mock_server.env = None
        mock_server.cwd = None
        mock_server.url = None
        mock_server.headers = None
        mock_server.auto_connect = True
        config.servers["test"] = mock_server

        manager = MCPManager(config)

        with pytest.raises(ValueError, match="command is required"):
            await manager.connect("test")

    @pytest.mark.asyncio
    async def test_connect_with_missing_url(self) -> None:
        """Test connect fails for streamable-http with missing url."""
        from unittest.mock import MagicMock
        from code_forge.config.models import TransportType

        # Create config with mock server config (bypass Pydantic validation)
        config = MCPConfig()
        mock_server = MagicMock(spec=MCPServerConfig)
        mock_server.name = "test"
        mock_server.transport = TransportType.STREAMABLE_HTTP
        mock_server.url = None
        mock_server.enabled = True
        mock_server.command = None
        mock_server.args = None
        mock_server.env = None
        mock_server.cwd = None
        mock_server.headers = None
        mock_server.auto_connect = True
        config.servers["test"] = mock_server

        manager = MCPManager(config)

        with pytest.raises(ValueError, match="url is required"):
            await manager.connect("test")

    @pytest.mark.asyncio
    async def test_connect_with_dead_connection_reconnects(self) -> None:
        """Test that connecting to a dead connection causes reconnect."""
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

        # Create a fake dead connection
        mock_client = MagicMock(spec=MCPClient)
        mock_client.is_connected = False  # Marked as dead
        mock_client.disconnect = AsyncMock()

        mock_adapter = MagicMock()
        mock_conn = MCPConnection(
            name="test",
            client=mock_client,
            config=config.servers["test"],
            adapter=mock_adapter,
        )
        manager._connections["test"] = mock_conn

        # New connect should clean up old and create new
        new_mock_client = MagicMock(spec=MCPClient)
        new_mock_client.connect = AsyncMock(
            return_value=MCPServerInfo(
                name="test",
                version="1.0",
                capabilities=MCPCapabilities(),
            )
        )
        new_mock_client.is_connected = True
        new_mock_client.list_tools = AsyncMock(return_value=[])
        new_mock_client.list_resources = AsyncMock(return_value=[])
        new_mock_client.list_prompts = AsyncMock(return_value=[])
        new_mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch(
                "code_forge.mcp.manager.MCPClient", return_value=new_mock_client
            ):
                conn = await manager.connect("test")
                assert conn.client is new_mock_client

                await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_connect_failure_cleans_up(self) -> None:
        """Test that connection failure cleans up properly."""
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
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.disconnect = AsyncMock()

        with patch("code_forge.mcp.manager.StdioTransport"):
            with patch("code_forge.mcp.manager.MCPClient", return_value=mock_client):
                with pytest.raises(MCPClientError, match="Connection failed"):
                    await manager.connect("test")

                # Should have tried to disconnect
                mock_client.disconnect.assert_called()

    @pytest.mark.asyncio
    async def test_reload_config_disconnects_removed_servers(self) -> None:
        """Test that reload_config disconnects servers removed from config."""
        config = MCPConfig(
            servers={
                "to-remove": MCPServerConfig(
                    name="to-remove",
                    transport="stdio",
                    command="echo",
                )
            }
        )
        manager = MCPManager(config)

        # Setup a fake connection
        mock_client = MagicMock(spec=MCPClient)
        mock_client.is_connected = True
        mock_client.disconnect = AsyncMock()

        mock_conn = MCPConnection(
            name="to-remove",
            client=mock_client,
            config=config.servers["to-remove"],
            adapter=MagicMock(),
        )
        manager._connections["to-remove"] = mock_conn

        # Create empty config loader
        with patch.object(MCPConfigLoader, "load", return_value=MCPConfig()):
            await manager.reload_config()

        assert "to-remove" not in manager._connections


class TestMCPConfigLoaderAdditional:
    """Additional tests for MCPConfigLoader."""

    def test_expand_env_vars_with_none(self) -> None:
        """Test that None values are preserved."""
        loader = MCPConfigLoader()
        result = loader._expand_env_vars(None)
        assert result is None

    def test_expand_env_vars_with_number(self) -> None:
        """Test that numbers are preserved."""
        loader = MCPConfigLoader()
        result = loader._expand_env_vars(42)
        assert result == 42

    def test_expand_env_vars_with_bool(self) -> None:
        """Test that booleans are preserved."""
        loader = MCPConfigLoader()
        result = loader._expand_env_vars(True)
        assert result is True


class TestMCPToolsAdditional:
    """Additional tests for MCP tools."""

    def test_format_result_with_plain_string(self) -> None:
        """Test formatting result with plain string items."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test")

        result = adapter._format_result(["plain", "text"])
        assert result == "plain\ntext"

    def test_format_result_with_text_in_dict(self) -> None:
        """Test formatting result with text key in unknown type."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test")

        result = adapter._format_result([{"type": "custom", "text": "content"}])
        assert result == "content"

    @pytest.mark.asyncio
    async def test_execute_with_wrong_prefix(self) -> None:
        """Test execute with incorrect prefix."""
        client = MagicMock(spec=MCPClient)
        adapter = MCPToolAdapter(client, "test")

        with pytest.raises(ValueError, match="Invalid MCP tool name"):
            await adapter.execute("wrong__prefix__tool", {})


class TestMCPProtocolEdgeCases:
    """Test edge cases in protocol module."""

    def test_mcp_error_class_constants(self) -> None:
        """Test that MCPError class constants are correct."""
        assert MCPError.PARSE_ERROR == -32700
        assert MCPError.INVALID_REQUEST == -32600
        assert MCPError.METHOD_NOT_FOUND == -32601
        assert MCPError.INVALID_PARAMS == -32602
        assert MCPError.INTERNAL_ERROR == -32603

    def test_mcp_request_to_dict_without_params(self) -> None:
        """Test request to_dict without params and without id."""
        request = MCPRequest(method="test", id=None)
        d = request.to_dict()
        assert "id" not in d
        assert "params" not in d

    def test_mcp_capabilities_to_dict_empty(self) -> None:
        """Test capabilities to_dict with all False."""
        caps = MCPCapabilities()
        d = caps.to_dict()
        assert d == {"capabilities": {}}


class TestMCPConfigEdgeCases:
    """Test edge cases in config module."""

    def test_mcp_settings_from_dict_empty(self) -> None:
        """Test settings from empty dict uses defaults."""
        settings = MCPSettings.model_validate({})
        assert settings.auto_connect is True
        assert settings.reconnect_attempts == 3
        assert settings.reconnect_delay == 5
        assert settings.timeout == 30

    def test_mcp_config_from_dict_empty(self) -> None:
        """Test config from empty dict."""
        config = MCPConfig.model_validate({})
        assert config.servers == {}
        assert config.settings.auto_connect is True


class TestProtocolParseMessage:
    """Test parse_message function."""

    def test_parse_message_request(self) -> None:
        """Test parsing a request message."""
        msg = {"jsonrpc": "2.0", "method": "test", "id": 1}
        result = parse_message(msg)
        assert isinstance(result, MCPRequest)
        assert result.method == "test"
        assert result.id == 1

    def test_parse_message_notification(self) -> None:
        """Test parsing a notification (no id)."""
        msg = {"jsonrpc": "2.0", "method": "notify"}
        result = parse_message(msg)
        assert isinstance(result, MCPNotification)
        assert result.method == "notify"

    def test_parse_message_response(self) -> None:
        """Test parsing a response."""
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"data": "value"}}
        result = parse_message(msg)
        assert isinstance(result, MCPResponse)
        assert result.id == 1
        assert result.result == {"data": "value"}

    def test_parse_message_error_response(self) -> None:
        """Test parsing an error response."""
        msg = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid"}}
        result = parse_message(msg)
        assert isinstance(result, MCPResponse)
        assert isinstance(result.error, MCPError)
        assert result.error.code == -32600

    def test_parse_json_message(self) -> None:
        """Test parsing JSON string message."""
        json_str = '{"jsonrpc": "2.0", "method": "test", "id": 1}'
        result = parse_json_message(json_str)
        assert isinstance(result, MCPRequest)

    def test_parse_json_message_invalid(self) -> None:
        """Test parsing invalid JSON."""
        with pytest.raises(ValueError):
            parse_json_message("not json")


class TestProtocolDataclasses:
    """Test protocol dataclass methods."""

    def test_mcp_response_is_error(self) -> None:
        """Test MCPResponse.is_error property."""
        error_response = MCPResponse(id=1, error={"code": -1, "message": "err"})
        assert error_response.is_error is True

        success_response = MCPResponse(id=1, result={"data": "ok"})
        assert success_response.is_error is False

    def test_mcp_notification_to_dict(self) -> None:
        """Test MCPNotification.to_dict."""
        notif = MCPNotification(method="test", params={"key": "val"})
        d = notif.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["method"] == "test"
        assert d["params"] == {"key": "val"}

    def test_mcp_notification_to_dict_no_params(self) -> None:
        """Test MCPNotification.to_dict without params."""
        notif = MCPNotification(method="test")
        d = notif.to_dict()
        assert "params" not in d

    def test_mcp_tool_from_dict(self) -> None:
        """Test MCPTool.from_dict."""
        data = {"name": "tool", "description": "desc", "inputSchema": {"type": "object"}}
        tool = MCPTool.from_dict(data)
        assert tool.name == "tool"
        assert tool.description == "desc"
        assert tool.input_schema == {"type": "object"}

    def test_mcp_resource_from_dict(self) -> None:
        """Test MCPResource.from_dict."""
        data = {"uri": "file:///test", "name": "test", "mimeType": "text/plain"}
        resource = MCPResource.from_dict(data)
        assert resource.uri == "file:///test"
        assert resource.name == "test"
        assert resource.mime_type == "text/plain"

    def test_mcp_resource_template_from_dict(self) -> None:
        """Test MCPResourceTemplate.from_dict."""
        data = {"uriTemplate": "file:///{path}", "name": "files", "description": "Files"}
        template = MCPResourceTemplate.from_dict(data)
        assert template.uri_template == "file:///{path}"
        assert template.name == "files"
        assert template.description == "Files"

    def test_mcp_prompt_from_dict_with_args(self) -> None:
        """Test MCPPrompt.from_dict with arguments."""
        data = {
            "name": "prompt",
            "description": "A prompt",
            "arguments": [{"name": "arg1", "description": "Arg 1", "required": True}],
        }
        prompt = MCPPrompt.from_dict(data)
        assert prompt.name == "prompt"
        assert len(prompt.arguments) == 1
        assert prompt.arguments[0].name == "arg1"
        assert prompt.arguments[0].required is True

    def test_mcp_prompt_message_from_dict(self) -> None:
        """Test MCPPromptMessage.from_dict."""
        data = {"role": "user", "content": "Hello"}
        msg = MCPPromptMessage.from_dict(data)
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_mcp_capabilities_from_dict_full(self) -> None:
        """Test MCPCapabilities.from_dict with all capabilities."""
        # The from_dict expects a dict with "capabilities" key
        data = {
            "capabilities": {
                "tools": {},
                "resources": {"subscribe": True},
                "prompts": {},
                "logging": {},
            }
        }
        caps = MCPCapabilities.from_dict(data)
        assert caps.tools is True
        assert caps.resources is True
        assert caps.prompts is True
        assert caps.logging is True

    def test_mcp_capabilities_to_dict_full(self) -> None:
        """Test MCPCapabilities.to_dict with all True."""
        caps = MCPCapabilities(tools=True, resources=True, prompts=True, logging=True)
        d = caps.to_dict()
        assert "tools" in d["capabilities"]
        assert "resources" in d["capabilities"]
        assert "prompts" in d["capabilities"]
        assert "logging" in d["capabilities"]

    def test_mcp_server_info_from_dict(self) -> None:
        """Test MCPServerInfo.from_dict."""
        data = {
            "serverInfo": {"name": "test", "version": "1.0"},
            "capabilities": {"tools": {}},
        }
        info = MCPServerInfo.from_dict(data)
        assert info.name == "test"
        assert info.version == "1.0"
        assert info.capabilities.tools is True


class TestMCPToolRegistryAdditional:
    """Additional registry tests."""

    def test_get_original_name_not_found(self) -> None:
        """Test get_original_name for unknown tool."""
        registry = MCPToolRegistry()
        result = registry.get_original_name("nonexistent")
        assert result is None

    def test_get_tools_for_server_empty(self) -> None:
        """Test get_tools_for_server with no tools."""
        registry = MCPToolRegistry()
        result = registry.get_tools_for_server("nonexistent")
        assert result == []


class TestMCPClientAdditional:
    """Additional MCPClient tests."""

    @pytest.mark.asyncio
    async def test_list_tools_with_capability(self) -> None:
        """Test list_tools when capability is supported but we mock request."""
        from code_forge.mcp.transport.base import MCPTransport

        transport = MagicMock(spec=MCPTransport)
        transport.is_connected = True
        client = MCPClient(transport, request_timeout=0.5)

        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(tools=True),
        )

        # Mock the _request method directly
        tool_data = [{"name": "tool1", "description": "Test", "inputSchema": {}}]
        client._request = AsyncMock(return_value={"tools": tool_data})

        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "tool1"

    @pytest.mark.asyncio
    async def test_list_resources_with_capability(self) -> None:
        """Test list_resources when capability is supported."""
        from code_forge.mcp.transport.base import MCPTransport

        transport = MagicMock(spec=MCPTransport)
        transport.is_connected = True
        client = MCPClient(transport, request_timeout=0.5)

        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(resources=True),
        )

        resource_data = [{"uri": "file:///test", "name": "test"}]
        client._request = AsyncMock(return_value={"resources": resource_data})

        resources = await client.list_resources()
        assert len(resources) == 1
        assert resources[0].uri == "file:///test"

    @pytest.mark.asyncio
    async def test_list_prompts_with_capability(self) -> None:
        """Test list_prompts when capability is supported."""
        from code_forge.mcp.transport.base import MCPTransport

        transport = MagicMock(spec=MCPTransport)
        transport.is_connected = True
        client = MCPClient(transport, request_timeout=0.5)

        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(prompts=True),
        )

        prompt_data = [{"name": "prompt1", "description": "A prompt"}]
        client._request = AsyncMock(return_value={"prompts": prompt_data})

        prompts = await client.list_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "prompt1"

    @pytest.mark.asyncio
    async def test_list_resource_templates_with_capability(self) -> None:
        """Test list_resource_templates when capability is supported."""
        from code_forge.mcp.transport.base import MCPTransport

        transport = MagicMock(spec=MCPTransport)
        transport.is_connected = True
        client = MCPClient(transport, request_timeout=0.5)

        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(resources=True),
        )

        template_data = [{"uriTemplate": "file:///{path}", "name": "files"}]
        client._request = AsyncMock(return_value={"resourceTemplates": template_data})

        templates = await client.list_resource_templates()
        assert len(templates) == 1
        assert templates[0].name == "files"
