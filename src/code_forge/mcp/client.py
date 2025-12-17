"""MCP client implementation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from code_forge.mcp.protocol import (
    MCPCapabilities,
    MCPNotification,
    MCPPrompt,
    MCPPromptMessage,
    MCPRequest,
    MCPResource,
    MCPResourceTemplate,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    parse_message,
)
from code_forge.mcp.transport.base import MCPTransport

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """MCP client error."""

    def __init__(self, message: str, code: int | None = None) -> None:
        """Initialize error.

        Args:
            message: Error message.
            code: Optional JSON-RPC error code.
        """
        super().__init__(message)
        self.code = code


class MCPClient:
    """Client for communicating with MCP servers.

    This class implements the MCP client protocol, handling initialization,
    tool calls, resource reads, and prompt retrieval.
    """

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        transport: MCPTransport,
        client_name: str = "forge",
        client_version: str = "1.0.0",
        request_timeout: float = 30.0,
        on_disconnect: Callable[[Exception | None], None] | None = None,
    ) -> None:
        """Initialize MCP client.

        Args:
            transport: Transport to use for communication.
            client_name: Client name for initialization.
            client_version: Client version.
            request_timeout: Timeout for requests in seconds.
            on_disconnect: Optional callback invoked when connection is lost unexpectedly.
                          Receives the exception that caused the disconnect, or None.
        """
        self.transport = transport
        self.client_name = client_name
        self.client_version = client_version
        self.request_timeout = request_timeout
        self._on_disconnect = on_disconnect
        self._server_info: MCPServerInfo | None = None
        self._pending_requests: dict[str | int, asyncio.Future[dict[str, Any]]] = {}
        self._receive_task: asyncio.Task[None] | None = None
        self._receive_lock = asyncio.Lock()

    async def connect(self) -> MCPServerInfo:
        """Connect to server and initialize.

        Returns:
            Server information including capabilities.

        Raises:
            MCPClientError: If connection or initialization fails.
        """
        try:
            await self.transport.connect()
        except ConnectionError as e:
            raise MCPClientError(f"Connection failed: {e}") from e

        # Start message receiver
        self._receive_task = asyncio.create_task(self._receive_loop())

        try:
            # Send initialize request
            result = await self._request(
                "initialize",
                {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "clientInfo": {
                        "name": self.client_name,
                        "version": self.client_version,
                    },
                    "capabilities": {},
                },
            )

            self._server_info = MCPServerInfo.from_dict(result)

            # Send initialized notification
            await self._notify("notifications/initialized", {})

            logger.info(
                f"Connected to {self._server_info.name} "
                f"v{self._server_info.version}"
            )
            return self._server_info

        except Exception as e:
            # Clean up on failure
            await self.disconnect()
            if isinstance(e, MCPClientError):
                raise
            raise MCPClientError(f"Initialization failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from server."""
        if self._receive_task is not None:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Cancel any pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(MCPClientError("Connection closed"))
        self._pending_requests.clear()

        try:
            await self.transport.disconnect()
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")

        self._server_info = None
        logger.info("Disconnected from MCP server")

    @property
    def capabilities(self) -> MCPCapabilities | None:
        """Get server capabilities.

        Returns:
            Server capabilities if connected, None otherwise.
        """
        if self._server_info is not None:
            return self._server_info.capabilities
        return None

    @property
    def is_connected(self) -> bool:
        """Check if connected.

        Returns:
            True if connected, False otherwise.
        """
        return self.transport.is_connected and self._server_info is not None

    @property
    def server_info(self) -> MCPServerInfo | None:
        """Get server info.

        Returns:
            Server info if connected, None otherwise.
        """
        return self._server_info

    # Tool methods

    async def list_tools(self) -> list[MCPTool]:
        """List available tools.

        Returns:
            List of tools from the server.
        """
        if not self.capabilities or not self.capabilities.tools:
            return []

        result = await self._request("tools/list", {})
        tools = result.get("tools", [])
        return [MCPTool.from_dict(t) for t in tools]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Call a tool.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result content.

        Raises:
            MCPClientError: If tool call fails.
        """
        result = await self._request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )
        content: list[dict[str, Any]] = result.get("content", [])
        return content

    # Resource methods

    async def list_resources(self) -> list[MCPResource]:
        """List available resources.

        Returns:
            List of resources from the server.
        """
        if not self.capabilities or not self.capabilities.resources:
            return []

        result = await self._request("resources/list", {})
        resources = result.get("resources", [])
        return [MCPResource.from_dict(r) for r in resources]

    async def list_resource_templates(self) -> list[MCPResourceTemplate]:
        """List resource templates.

        Returns:
            List of resource templates from the server.
        """
        if not self.capabilities or not self.capabilities.resources:
            return []

        result = await self._request("resources/templates/list", {})
        templates = result.get("resourceTemplates", [])
        return [MCPResourceTemplate.from_dict(t) for t in templates]

    async def read_resource(self, uri: str) -> list[dict[str, Any]]:
        """Read a resource.

        Args:
            uri: Resource URI.

        Returns:
            Resource contents.

        Raises:
            MCPClientError: If resource read fails.
        """
        result = await self._request("resources/read", {"uri": uri})
        contents: list[dict[str, Any]] = result.get("contents", [])
        return contents

    # Prompt methods

    async def list_prompts(self) -> list[MCPPrompt]:
        """List available prompts.

        Returns:
            List of prompts from the server.
        """
        if not self.capabilities or not self.capabilities.prompts:
            return []

        result = await self._request("prompts/list", {})
        prompts = result.get("prompts", [])
        return [MCPPrompt.from_dict(p) for p in prompts]

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, str] | None = None,
    ) -> list[MCPPromptMessage]:
        """Get a prompt.

        Args:
            name: Prompt name.
            arguments: Prompt arguments.

        Returns:
            Prompt messages.

        Raises:
            MCPClientError: If prompt retrieval fails.
        """
        result = await self._request(
            "prompts/get",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )
        messages = result.get("messages", [])
        return [MCPPromptMessage.from_dict(m) for m in messages]

    # Internal methods

    async def _request(
        self,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Send request and wait for response.

        Args:
            method: The JSON-RPC method.
            params: The method parameters.

        Returns:
            The result from the response.

        Raises:
            MCPClientError: If request fails or times out.
        """
        request = MCPRequest(method=method, params=params)
        if request.id is None:
            raise MCPClientError("Request ID is required")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_requests[request.id] = future

        try:
            await self.transport.send(request.to_dict())
            result = await asyncio.wait_for(future, timeout=self.request_timeout)
            return result
        except TimeoutError as e:
            raise MCPClientError(f"Request timeout: {method}") from e
        except ConnectionError as e:
            raise MCPClientError(f"Connection error: {e}") from e
        finally:
            self._pending_requests.pop(request.id, None)

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        """Send notification (no response expected).

        Args:
            method: The notification method.
            params: The notification parameters.

        Raises:
            MCPClientError: If send fails.
        """
        notification = MCPNotification(method=method, params=params)
        try:
            await self.transport.send(notification.to_dict())
        except ConnectionError as e:
            raise MCPClientError(f"Notification failed: {e}") from e

    async def _receive_loop(self) -> None:
        """Receive and dispatch messages."""
        disconnect_error: Exception | None = None
        try:
            while self.transport.is_connected:
                try:
                    message = await self.transport.receive()
                    await self._handle_message(message)
                except ConnectionError as e:
                    logger.error(f"Receive error: {e}")
                    disconnect_error = e
                    break
        except asyncio.CancelledError:
            pass  # Normal shutdown, not an unexpected disconnect
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
            disconnect_error = e
        finally:
            # Cancel all pending requests
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(MCPClientError("Connection closed"))
            # Notify disconnect callback if provided
            if disconnect_error is not None and self._on_disconnect is not None:
                try:
                    self._on_disconnect(disconnect_error)
                except Exception as callback_err:
                    logger.error(f"Disconnect callback error: {callback_err}")

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle incoming message.

        Args:
            data: The raw message data.
        """
        try:
            message = parse_message(data)
        except ValueError as e:
            logger.error(f"Invalid message: {e}")
            return

        if isinstance(message, MCPResponse):
            # Match to pending request
            future = self._pending_requests.get(message.id)
            if future is not None and not future.done():
                if message.error is not None:
                    future.set_exception(
                        MCPClientError(
                            message.error.message,
                            message.error.code,
                        )
                    )
                else:
                    future.set_result(message.result or {})
            else:
                logger.warning(f"Unexpected response ID: {message.id}")
        elif isinstance(message, MCPNotification):
            # Handle server notification
            logger.debug(f"Received notification: {message.method}")
            # Future: implement notification handlers
        elif isinstance(message, MCPRequest):
            # Handle server request (rare)
            logger.debug(f"Received request from server: {message.method}")
            # Future: implement request handlers
