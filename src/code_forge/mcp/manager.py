"""MCP connection manager."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from code_forge.mcp.client import MCPClient, MCPClientError
from code_forge.mcp.config import MCPConfig, MCPConfigLoader, MCPServerConfig
from code_forge.mcp.protocol import MCPPrompt, MCPResource, MCPTool
from code_forge.mcp.tools import MCPToolAdapter, MCPToolRegistry
from code_forge.mcp.transport.base import MCPTransport
from code_forge.mcp.transport.http import HTTPTransport
from code_forge.mcp.transport.stdio import StdioTransport

logger = logging.getLogger(__name__)


@dataclass
class MCPConnection:
    """Represents a connection to an MCP server."""

    name: str
    client: MCPClient
    config: MCPServerConfig
    adapter: MCPToolAdapter
    tools: list[MCPTool] = field(default_factory=list)
    resources: list[MCPResource] = field(default_factory=list)
    prompts: list[MCPPrompt] = field(default_factory=list)
    connected_at: datetime = field(default_factory=datetime.now)

    @property
    def is_connected(self) -> bool:
        """Check if connection is active.

        Returns:
            True if connected, False otherwise.
        """
        return self.client.is_connected


class MCPManager:
    """Manages MCP server connections.

    This class is responsible for:
    - Managing connections to MCP servers
    - Loading and applying configuration
    - Registering MCP tools
    - Providing access to resources and prompts
    """

    _instance: MCPManager | None = None
    _lock: asyncio.Lock | None = None

    def __init__(self, config: MCPConfig | None = None) -> None:
        """Initialize manager.

        Args:
            config: MCP configuration (loads default if None).
        """
        self._config = config or MCPConfigLoader().load()
        self._connections: dict[str, MCPConnection] = {}
        self._tool_registry = MCPToolRegistry()
        self._connection_lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> MCPManager:
        """Get singleton instance.

        Returns:
            The singleton MCPManager instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance."""
        if cls._instance is not None:
            # Schedule disconnect_all in the event loop if running
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(cls._instance.disconnect_all())
            except RuntimeError:
                # No running loop, try to run synchronously
                pass
        cls._instance = None

    @classmethod
    def set_instance(cls, instance: MCPManager) -> None:
        """Set the singleton instance.

        Args:
            instance: The instance to use.
        """
        cls._instance = instance

    @property
    def config(self) -> MCPConfig:
        """Get current configuration.

        Returns:
            The MCP configuration.
        """
        return self._config

    @property
    def tool_registry(self) -> MCPToolRegistry:
        """Get MCP tool registry.

        Returns:
            The tool registry.
        """
        return self._tool_registry

    def _create_transport(self, config: MCPServerConfig) -> MCPTransport:
        """Create transport for server config.

        Args:
            config: Server configuration.

        Returns:
            Transport instance.

        Raises:
            ValueError: If transport type is unknown.
        """
        if config.transport == "stdio":
            if config.command is None:
                raise ValueError(f"Server {config.name}: command is required")
            return StdioTransport(
                command=config.command,
                args=config.args,
                env=config.env,
                cwd=config.cwd,
            )
        elif config.transport == "http":
            if config.url is None:
                raise ValueError(f"Server {config.name}: url is required")
            return HTTPTransport(
                url=config.url,
                headers=config.headers,
                timeout=self._config.settings.timeout,
            )
        else:
            raise ValueError(f"Unknown transport: {config.transport}")

    async def connect(self, server_name: str) -> MCPConnection:
        """Connect to a specific server with retry logic.

        Uses exponential backoff with jitter for reconnection attempts.
        Respects settings.reconnect_attempts and settings.reconnect_delay.

        Args:
            server_name: Name of server to connect.

        Returns:
            Connection object.

        Raises:
            ValueError: If server is unknown or disabled.
            MCPClientError: If connection fails after all retries.
        """
        async with self._connection_lock:
            # Check if already connected
            if server_name in self._connections:
                conn = self._connections[server_name]
                if conn.is_connected:
                    return conn
                # Connection exists but is dead, clean up
                await self._disconnect_internal(server_name)

            # Get config
            config = self._config.servers.get(server_name)
            if config is None:
                raise ValueError(f"Unknown server: {server_name}")

            if not config.enabled:
                raise ValueError(f"Server {server_name} is disabled")

            # Get retry settings
            max_attempts = self._config.settings.reconnect_attempts
            base_delay = self._config.settings.reconnect_delay

            last_error: Exception | None = None

            for attempt in range(max_attempts + 1):
                # Create transport and client for each attempt
                transport = self._create_transport(config)
                client = MCPClient(
                    transport,
                    request_timeout=float(self._config.settings.timeout),
                )

                try:
                    # Connect
                    await client.connect()
                    logger.info(f"Connected to MCP server: {server_name}")

                    # Create adapter
                    adapter = MCPToolAdapter(client, server_name)

                    # Discover capabilities
                    tools = await client.list_tools()
                    resources = await client.list_resources()
                    prompts = await client.list_prompts()

                    # Register tools
                    self._tool_registry.register_server_tools(adapter, tools)

                    # Create connection
                    connection = MCPConnection(
                        name=server_name,
                        client=client,
                        config=config,
                        adapter=adapter,
                        tools=tools,
                        resources=resources,
                        prompts=prompts,
                        connected_at=datetime.now(),
                    )

                    self._connections[server_name] = connection
                    return connection

                except Exception as e:
                    await client.disconnect()
                    last_error = e

                    # Log attempt failure
                    if attempt < max_attempts:
                        # Calculate delay with exponential backoff and jitter
                        delay = base_delay * (2**attempt) * random.uniform(0.5, 1.5)
                        logger.warning(
                            f"Connection attempt {attempt + 1}/{max_attempts + 1} "
                            f"to {server_name} failed: {e}. Retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts + 1} connection attempts to "
                            f"{server_name} failed"
                        )

            # All attempts failed
            if isinstance(last_error, MCPClientError):
                raise last_error
            raise MCPClientError(
                f"Failed to connect to {server_name} after {max_attempts + 1} attempts: "
                f"{last_error}"
            ) from last_error

    async def connect_all(self) -> list[MCPConnection]:
        """Connect to all enabled servers with auto_connect=True.

        Returns:
            List of successful connections.
        """
        connections: list[MCPConnection] = []
        servers = self._config.get_auto_connect_servers()

        for config in servers:
            try:
                conn = await self.connect(config.name)
                connections.append(conn)
            except Exception as e:
                logger.error(f"Failed to connect to {config.name}: {e}")

        return connections

    async def _disconnect_internal(self, server_name: str) -> None:
        """Internal disconnect without lock.

        Args:
            server_name: Server to disconnect.
        """
        connection = self._connections.pop(server_name, None)
        if connection is not None:
            # Unregister tools
            self._tool_registry.unregister_server_tools(server_name)
            # Disconnect client
            try:
                await connection.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting {server_name}: {e}")
            logger.info(f"Disconnected from {server_name}")

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from a server.

        Args:
            server_name: Server to disconnect.
        """
        async with self._connection_lock:
            await self._disconnect_internal(server_name)

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        async with self._connection_lock:
            for name in list(self._connections.keys()):
                await self._disconnect_internal(name)

    async def reconnect(self, server_name: str) -> MCPConnection:
        """Reconnect to a server.

        Args:
            server_name: Server to reconnect.

        Returns:
            New connection.
        """
        await self.disconnect(server_name)
        return await self.connect(server_name)

    def get_connection(self, name: str) -> MCPConnection | None:
        """Get connection by name.

        Args:
            name: Server name.

        Returns:
            Connection or None if not connected.
        """
        return self._connections.get(name)

    def list_connections(self) -> list[MCPConnection]:
        """List all connections.

        Returns:
            List of all connections.
        """
        return list(self._connections.values())

    def is_connected(self, server_name: str) -> bool:
        """Check if connected to a server.

        Args:
            server_name: Server name.

        Returns:
            True if connected, False otherwise.
        """
        conn = self._connections.get(server_name)
        return conn is not None and conn.is_connected

    async def reload_config(self) -> None:
        """Reload configuration and reconnect changed servers."""
        new_config = MCPConfigLoader().load()

        async with self._connection_lock:
            # Find servers to disconnect (removed or changed)
            for name in list(self._connections.keys()):
                removed = name not in new_config.servers
                changed = new_config.servers.get(name) != self._config.servers.get(name)
                if removed or changed:
                    await self._disconnect_internal(name)

            # Update config
            self._config = new_config

        # Connect new/changed servers
        await self.connect_all()

    def get_all_tools(self) -> list[MCPTool]:
        """Get tools from all connections.

        Returns:
            List of all tools.
        """
        tools: list[MCPTool] = []
        for conn in self._connections.values():
            tools.extend(conn.tools)
        return tools

    def get_all_resources(self) -> list[MCPResource]:
        """Get resources from all connections.

        Returns:
            List of all resources.
        """
        resources: list[MCPResource] = []
        for conn in self._connections.values():
            resources.extend(conn.resources)
        return resources

    def get_all_prompts(self) -> list[MCPPrompt]:
        """Get prompts from all connections.

        Returns:
            List of all prompts.
        """
        prompts: list[MCPPrompt] = []
        for conn in self._connections.values():
            prompts.extend(conn.prompts)
        return prompts

    def get_status(self) -> dict[str, Any]:
        """Get manager status.

        Returns:
            Status dictionary.
        """
        return {
            "configured_servers": len(self._config.servers),
            "connected_servers": len(self._connections),
            "total_tools": len(self._tool_registry.list_tools()),
            "total_resources": len(self.get_all_resources()),
            "total_prompts": len(self.get_all_prompts()),
            "connections": {
                name: {
                    "connected": conn.is_connected,
                    "tools": len(conn.tools),
                    "resources": len(conn.resources),
                    "prompts": len(conn.prompts),
                    "connected_at": conn.connected_at.isoformat(),
                }
                for name, conn in self._connections.items()
            },
        }

    async def read_resource(self, server_name: str, uri: str) -> list[dict[str, Any]]:
        """Read a resource from a server.

        Args:
            server_name: Server name.
            uri: Resource URI.

        Returns:
            Resource contents.

        Raises:
            ValueError: If server not connected.
        """
        conn = self._connections.get(server_name)
        if conn is None:
            raise ValueError(f"Server not connected: {server_name}")
        return await conn.client.read_resource(uri)

    async def get_prompt(
        self,
        server_name: str,
        name: str,
        arguments: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get a prompt from a server.

        Args:
            server_name: Server name.
            name: Prompt name.
            arguments: Prompt arguments.

        Returns:
            Prompt messages.

        Raises:
            ValueError: If server not connected.
        """
        conn = self._connections.get(server_name)
        if conn is None:
            raise ValueError(f"Server not connected: {server_name}")
        messages = await conn.client.get_prompt(name, arguments)
        return [m.to_dict() for m in messages]
