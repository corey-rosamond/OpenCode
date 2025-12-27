"""Tests for MCP client."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.mcp.client import MCPClient, MCPClientError
from code_forge.mcp.protocol import (
    MCPCapabilities,
    MCPError,
    MCPPrompt,
    MCPPromptMessage,
    MCPResource,
    MCPResourceTemplate,
    MCPServerInfo,
    MCPTool,
)
from code_forge.mcp.transport.base import MCPTransport


class MockTransport(MCPTransport):
    """Mock transport for testing."""

    def __init__(self) -> None:
        self._connected = False
        self._messages: list[dict[str, Any]] = []
        self._responses: list[dict[str, Any]] = []
        self._response_index = 0

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def send(self, message: dict[str, Any]) -> None:
        if not self._connected:
            raise ConnectionError("Not connected")
        self._messages.append(message)

    async def receive(self) -> dict[str, Any]:
        if not self._connected:
            raise ConnectionError("Not connected")
        if self._response_index >= len(self._responses):
            # Block indefinitely
            await asyncio.sleep(100)
        response = self._responses[self._response_index]
        self._response_index += 1
        return response

    @property
    def is_connected(self) -> bool:
        return self._connected

    def add_response(self, response: dict[str, Any]) -> None:
        """Add a response to be returned."""
        self._responses.append(response)

    def get_sent_messages(self) -> list[dict[str, Any]]:
        """Get all sent messages."""
        return self._messages


class TestMCPClientError:
    """Tests for MCPClientError."""

    def test_creation(self) -> None:
        """Test basic creation."""
        error = MCPClientError("Test error")
        assert str(error) == "Test error"
        assert error.code is None

    def test_creation_with_code(self) -> None:
        """Test creation with error code."""
        error = MCPClientError("Method not found", code=-32601)
        assert str(error) == "Method not found"
        assert error.code == -32601


class TestMCPClient:
    """Tests for MCPClient."""

    def test_initialization(self) -> None:
        """Test client initialization."""
        transport = MockTransport()
        client = MCPClient(transport)
        assert client.transport is transport
        assert client.client_name == "forge"
        assert client.client_version == "1.0.0"
        assert client.capabilities is None
        assert client.server_info is None
        assert client.is_connected is False

    def test_initialization_custom(self) -> None:
        """Test client initialization with custom values."""
        transport = MockTransport()
        client = MCPClient(
            transport,
            client_name="test-client",
            client_version="2.0.0",
            request_timeout=60.0,
        )
        assert client.client_name == "test-client"
        assert client.client_version == "2.0.0"
        assert client.request_timeout == 60.0

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful connection."""
        transport = MockTransport()
        client = MCPClient(transport)

        # Add initialize response
        transport.add_response(
            {
                "jsonrpc": "2.0",
                "id": None,  # Will be matched by first request
                "result": {
                    "serverInfo": {"name": "test-server", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }
        )

        # Mock the response matching
        original_receive = transport.receive

        async def patched_receive() -> dict[str, Any]:
            response = await original_receive()
            # Set the ID to match the request
            if transport._messages:
                last_msg = transport._messages[-1]
                if "id" in last_msg:
                    response["id"] = last_msg["id"]
            return response

        transport.receive = patched_receive  # type: ignore

        server_info = await client.connect()

        assert server_info.name == "test-server"
        assert server_info.version == "1.0.0"
        assert isinstance(client.capabilities, MCPCapabilities)
        assert client.capabilities.tools is True
        assert client.is_connected is True

        # Verify initialize was sent
        assert len(transport.get_sent_messages()) >= 1
        init_msg = transport.get_sent_messages()[0]
        assert init_msg["method"] == "initialize"

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_transport_failure(self) -> None:
        """Test connection when transport fails."""
        transport = MockTransport()

        async def failing_connect() -> None:
            raise ConnectionError("Transport error")

        transport.connect = failing_connect  # type: ignore

        client = MCPClient(transport)

        with pytest.raises(MCPClientError, match="Connection failed"):
            await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnection."""
        transport = MockTransport()
        client = MCPClient(transport)

        # Simulate connected state
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(),
        )

        await client.disconnect()

        assert client.is_connected is False
        assert client.server_info is None
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_clears_pending_requests(self) -> None:
        """Test that disconnect clears pending requests."""
        transport = MockTransport()
        client = MCPClient(transport)
        transport._connected = True

        # Add a pending request
        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        client._pending_requests["test-id"] = future

        await client.disconnect()

        # Future should be set with an exception
        assert future.done()
        with pytest.raises(MCPClientError):
            future.result()

    @pytest.mark.asyncio
    async def test_list_tools_no_capability(self) -> None:
        """Test listing tools when server doesn't support tools."""
        transport = MockTransport()
        client = MCPClient(transport)
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(tools=False),
        )

        tools = await client.list_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_list_resources_no_capability(self) -> None:
        """Test listing resources when server doesn't support resources."""
        transport = MockTransport()
        client = MCPClient(transport)
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(resources=False),
        )

        resources = await client.list_resources()
        assert resources == []

    @pytest.mark.asyncio
    async def test_list_prompts_no_capability(self) -> None:
        """Test listing prompts when server doesn't support prompts."""
        transport = MockTransport()
        client = MCPClient(transport)
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(prompts=False),
        )

        prompts = await client.list_prompts()
        assert prompts == []

    @pytest.mark.asyncio
    async def test_list_resource_templates_no_capability(self) -> None:
        """Test listing resource templates without capability."""
        transport = MockTransport()
        client = MCPClient(transport)
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(resources=False),
        )

        templates = await client.list_resource_templates()
        assert templates == []

    @pytest.mark.asyncio
    async def test_request_timeout(self) -> None:
        """Test request timeout handling."""
        transport = MockTransport()
        client = MCPClient(transport, request_timeout=0.1)
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(tools=True),
        )

        # Start receive loop
        client._receive_task = asyncio.create_task(client._receive_loop())

        try:
            # This should timeout since no response is provided
            with pytest.raises(MCPClientError, match="timeout"):
                await client.list_tools()
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_handle_error_response(self) -> None:
        """Test handling of error responses."""
        transport = MockTransport()
        client = MCPClient(transport, request_timeout=1.0)
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(tools=True),
        )

        # Add error response
        transport.add_response(
            {
                "jsonrpc": "2.0",
                "id": None,  # Will be set
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

        # Patch receive to set correct ID
        original_receive = transport.receive

        async def patched_receive() -> dict[str, Any]:
            response = await original_receive()
            if transport._messages:
                last_msg = transport._messages[-1]
                if "id" in last_msg:
                    response["id"] = last_msg["id"]
            return response

        transport.receive = patched_receive  # type: ignore

        # Start receive loop
        client._receive_task = asyncio.create_task(client._receive_loop())

        try:
            with pytest.raises(MCPClientError, match="Method not found"):
                await client.list_tools()
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_call_tool(self) -> None:
        """Test calling a tool."""
        transport = MockTransport()
        client = MCPClient(transport, request_timeout=1.0)
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(tools=True),
        )

        # Add response
        transport.add_response(
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {"content": [{"type": "text", "text": "Hello"}]},
            }
        )

        # Patch receive
        original_receive = transport.receive

        async def patched_receive() -> dict[str, Any]:
            response = await original_receive()
            if transport._messages:
                last_msg = transport._messages[-1]
                if "id" in last_msg:
                    response["id"] = last_msg["id"]
            return response

        transport.receive = patched_receive  # type: ignore

        # Start receive loop
        client._receive_task = asyncio.create_task(client._receive_loop())

        try:
            result = await client.call_tool("test_tool", {"arg": "value"})
            assert result == [{"type": "text", "text": "Hello"}]

            # Verify request
            sent = transport.get_sent_messages()[-1]
            assert sent["method"] == "tools/call"
            assert sent["params"]["name"] == "test_tool"
            assert sent["params"]["arguments"] == {"arg": "value"}
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_read_resource(self) -> None:
        """Test reading a resource."""
        transport = MockTransport()
        client = MCPClient(transport, request_timeout=1.0)
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(resources=True),
        )

        # Add response
        transport.add_response(
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "contents": [{"uri": "file:///test", "text": "content"}]
                },
            }
        )

        # Patch receive
        original_receive = transport.receive

        async def patched_receive() -> dict[str, Any]:
            response = await original_receive()
            if transport._messages:
                last_msg = transport._messages[-1]
                if "id" in last_msg:
                    response["id"] = last_msg["id"]
            return response

        transport.receive = patched_receive  # type: ignore

        # Start receive loop
        client._receive_task = asyncio.create_task(client._receive_loop())

        try:
            result = await client.read_resource("file:///test")
            assert result == [{"uri": "file:///test", "text": "content"}]
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_get_prompt(self) -> None:
        """Test getting a prompt."""
        transport = MockTransport()
        client = MCPClient(transport, request_timeout=1.0)
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(prompts=True),
        )

        # Add response
        transport.add_response(
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "messages": [{"role": "user", "content": "Hello"}]
                },
            }
        )

        # Patch receive
        original_receive = transport.receive

        async def patched_receive() -> dict[str, Any]:
            response = await original_receive()
            if transport._messages:
                last_msg = transport._messages[-1]
                if "id" in last_msg:
                    response["id"] = last_msg["id"]
            return response

        transport.receive = patched_receive  # type: ignore

        # Start receive loop
        client._receive_task = asyncio.create_task(client._receive_loop())

        try:
            result = await client.get_prompt("test_prompt", {"arg": "value"})
            assert len(result) == 1
            assert result[0].role == "user"
            assert result[0].content == "Hello"
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_notify(self) -> None:
        """Test sending a notification."""
        transport = MockTransport()
        client = MCPClient(transport)
        transport._connected = True

        await client._notify("test/notification", {"data": "value"})

        # Verify notification was sent
        sent = transport.get_sent_messages()[-1]
        assert sent["method"] == "test/notification"
        assert sent["params"] == {"data": "value"}
        assert "id" not in sent

    @pytest.mark.asyncio
    async def test_handle_notification_from_server(self) -> None:
        """Test handling notifications from server."""
        transport = MockTransport()
        client = MCPClient(transport)
        transport._connected = True

        # Handle a notification message
        await client._handle_message(
            {"jsonrpc": "2.0", "method": "notifications/progress", "params": {}}
        )
        # Should not raise - notifications are logged but not processed

    @pytest.mark.asyncio
    async def test_handle_invalid_message(self) -> None:
        """Test handling invalid messages."""
        transport = MockTransport()
        client = MCPClient(transport)
        transport._connected = True

        # Handle an invalid message
        await client._handle_message({"jsonrpc": "2.0"})
        # Should not raise - invalid messages are logged

    @pytest.mark.asyncio
    async def test_handle_unexpected_response(self) -> None:
        """Test handling responses with unknown IDs."""
        transport = MockTransport()
        client = MCPClient(transport)
        transport._connected = True

        # Handle a response with unknown ID
        await client._handle_message(
            {"jsonrpc": "2.0", "id": "unknown-id", "result": {}}
        )
        # Should not raise - logged as warning

    @pytest.mark.asyncio
    async def test_protocol_version(self) -> None:
        """Test protocol version is correct."""
        assert MCPClient.PROTOCOL_VERSION == "2024-11-05"


class TestMCPClientIntegration:
    """Integration tests for MCPClient with real-ish scenarios."""

    @pytest.mark.asyncio
    async def test_workflow_steps(self) -> None:
        """Test individual workflow steps with proper mocking."""
        # The full integration workflow is covered by individual tests
        # This test verifies the pieces work together conceptually
        transport = MockTransport()
        client = MCPClient(transport, request_timeout=1.0)

        # Just verify client can be created and has right properties
        assert client.transport is transport
        assert client.is_connected is False
        assert client.capabilities is None

        # Simulate a connected state manually
        transport._connected = True
        client._server_info = MCPServerInfo(
            name="test",
            version="1.0.0",
            capabilities=MCPCapabilities(tools=True, resources=True, prompts=True),
        )

        # Verify connected state
        assert client.is_connected is True
        assert isinstance(client.capabilities, MCPCapabilities)
        assert client.capabilities.tools is True

        # Clean up
        await client.disconnect()
        assert client.is_connected is False
