"""HTTP/SSE transport for remote MCP servers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from code_forge.mcp.transport.base import MCPTransport

logger = logging.getLogger(__name__)


class HTTPTransport(MCPTransport):
    """Transport using HTTP for remote MCP servers.

    This transport connects to an MCP server via HTTP, using POST
    for requests and Server-Sent Events (SSE) for notifications.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> None:
        """Initialize HTTP transport.

        Args:
            url: Base URL of MCP server.
            headers: HTTP headers to include.
            timeout: Request timeout in seconds.
        """
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._session: Any | None = None  # aiohttp.ClientSession
        self._sse_task: asyncio.Task[None] | None = None
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connected = False
        self._closing = False

    async def connect(self) -> None:
        """Establish HTTP connection and start SSE listener.

        Raises:
            ConnectionError: If connection fails.
        """
        try:
            import aiohttp
        except ImportError as e:
            raise ConnectionError(
                "aiohttp is required for HTTP transport. "
                "Install it with: pip install aiohttp"
            ) from e

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
            )

            # Try to connect to verify the server is reachable
            # Most MCP HTTP servers expose an endpoint we can check
            try:
                async with self._session.get(f"{self.url}/health"):
                    # We don't require a specific response, just that we can connect
                    pass
            except aiohttp.ClientError:
                # Health endpoint may not exist, that's okay
                pass

            # Start SSE listener for notifications
            self._sse_task = asyncio.create_task(self._listen_sse())
            self._connected = True
            logger.info(f"Connected to MCP server: {self.url}")

        except Exception as e:
            if self._session is not None:
                await self._session.close()
                self._session = None
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Close HTTP connection."""
        self._closing = True
        self._connected = False

        if self._sse_task is not None:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
            self._sse_task = None

        if self._session is not None:
            await self._session.close()
            self._session = None

        self._closing = False
        logger.info("Disconnected from MCP server")

    async def send(self, message: dict[str, Any]) -> None:
        """Send JSON-RPC message via HTTP POST.

        Args:
            message: The message to send.

        Raises:
            ConnectionError: If not connected or send fails.
        """
        if self._session is None or not self._connected:
            raise ConnectionError("Not connected")

        try:
            import aiohttp

            async with self._session.post(
                f"{self.url}/message",
                json=message,
            ) as response:
                response.raise_for_status()
                result = await response.json()
                # Queue the response for receive()
                await self._message_queue.put(result)
                logger.debug(f"Sent: {json.dumps(message)}")

        except aiohttp.ClientError as e:
            raise ConnectionError(f"HTTP request failed: {e}") from e
        except Exception as e:
            raise ConnectionError(f"Send failed: {e}") from e

    async def receive(self) -> dict[str, Any]:
        """Receive message from queue.

        Returns:
            The received message as a dictionary.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected and self._message_queue.empty():
            raise ConnectionError("Not connected")

        try:
            message = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=self.timeout,
            )
            logger.debug(f"Received: {json.dumps(message)}")
            return message
        except TimeoutError as e:
            raise ConnectionError("Receive timeout") from e

    async def _listen_sse(self) -> None:
        """Listen for Server-Sent Events."""
        if self._session is None:
            return

        try:

            async with self._session.get(
                f"{self.url}/sse",
                headers={"Accept": "text/event-stream"},
            ) as response:
                async for line in response.content:
                    if self._closing:
                        break
                    if line.startswith(b"data: "):
                        try:
                            data = line[6:].decode("utf-8").strip()
                        except UnicodeDecodeError:
                            logger.warning("Invalid UTF-8 in SSE data, skipping")
                            continue
                        if data:
                            try:
                                message = json.loads(data)
                                await self._message_queue.put(message)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in SSE: {data}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._closing:
                logger.error(f"SSE error: {e}")
                self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._connected and self._session is not None
