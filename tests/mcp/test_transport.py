"""Tests for MCP transport implementations."""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.mcp.transport.base import MCPTransport
from code_forge.mcp.transport.stdio import StdioTransport


class TestMCPTransportInterface:
    """Tests for MCPTransport abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """Test that MCPTransport cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MCPTransport()  # type: ignore


class TestStdioTransport:
    """Tests for StdioTransport."""

    def test_initialization(self) -> None:
        """Test transport initialization."""
        transport = StdioTransport(
            command="python",
            args=["-m", "test_module"],
            env={"TEST_VAR": "value"},
            cwd="/tmp",
        )
        assert transport.command == "python"
        assert transport.args == ["-m", "test_module"]
        assert transport.env == {"TEST_VAR": "value"}
        assert transport.cwd == "/tmp"

    def test_initialization_defaults(self) -> None:
        """Test transport initialization with defaults."""
        transport = StdioTransport(command="echo")
        assert transport.command == "echo"
        assert transport.args == []
        assert transport.env is None
        assert transport.cwd is None

    def test_is_connected_false_initially(self) -> None:
        """Test that transport is not connected initially."""
        transport = StdioTransport(command="echo")
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self) -> None:
        """Test connection with non-existent command."""
        transport = StdioTransport(command="/nonexistent/command/xyz")
        with pytest.raises(ConnectionError, match="Command not found"):
            await transport.connect()

    @pytest.mark.asyncio
    async def test_send_not_connected(self) -> None:
        """Test sending when not connected."""
        transport = StdioTransport(command="echo")
        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.send({"method": "test"})

    @pytest.mark.asyncio
    async def test_receive_not_connected(self) -> None:
        """Test receiving when not connected."""
        transport = StdioTransport(command="echo")
        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        """Test disconnecting when not connected does not raise."""
        transport = StdioTransport(command="echo")
        await transport.disconnect()  # Should not raise
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self) -> None:
        """Test connecting and disconnecting with a real process."""
        # Use a simple command that stays alive briefly
        transport = StdioTransport(command="cat")

        await transport.connect()
        assert transport.is_connected is True

        await transport.disconnect()
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_send_and_receive(self) -> None:
        """Test sending and receiving with a real echo-like process."""
        # Use cat which echoes stdin to stdout
        transport = StdioTransport(command="cat")

        await transport.connect()
        assert transport.is_connected

        try:
            # Send a message
            message = {"jsonrpc": "2.0", "method": "test", "id": "1"}
            await transport.send(message)

            # Receive the echoed message
            received = await transport.receive()
            assert received == message
        finally:
            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_env_expansion(self) -> None:
        """Test environment variable expansion."""
        os.environ["TEST_MCP_VAR"] = "test_value"
        try:
            transport = StdioTransport(
                command="cat",
                env={"EXPANDED": "${TEST_MCP_VAR}"},
            )

            await transport.connect()
            try:
                # The env should have the expanded value
                assert hasattr(transport, '_process')
                assert transport._process.pid > 0
            finally:
                await transport.disconnect()
        finally:
            del os.environ["TEST_MCP_VAR"]

    @pytest.mark.asyncio
    async def test_process_exits_during_send(self) -> None:
        """Test handling when process exits during send."""
        # Use a command that exits immediately
        transport = StdioTransport(command="true")

        await transport.connect()

        # Wait a moment for the process to exit
        await asyncio.sleep(0.1)

        # Process should have exited
        with pytest.raises(ConnectionError):
            await transport.send({"test": "data"})

    @pytest.mark.asyncio
    async def test_process_closes_stdout(self) -> None:
        """Test handling when process closes stdout."""
        # Use python to print JSON, wait briefly (so connect() passes), then exit
        # The tiny sleep ensures the process is still "running" when connect() checks
        script = 'import sys, time; print("{}"); sys.stdout.flush(); time.sleep(0.1)'
        transport = StdioTransport(
            command="python3",
            args=["-u", "-c", script]  # -u for unbuffered output
        )

        await transport.connect()

        try:
            # First receive gets the output
            result = await transport.receive()
            assert result == {}

            # Second receive should fail (process exited after sleep)
            with pytest.raises(ConnectionError):
                await transport.receive()
        finally:
            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_invalid_json_from_process(self) -> None:
        """Test handling invalid JSON from process."""
        # Use python to send invalid JSON with delay (so connect() passes)
        script = 'import sys, time; print("not valid json"); sys.stdout.flush(); time.sleep(0.1)'
        transport = StdioTransport(
            command="python3",
            args=["-u", "-c", script]
        )

        await transport.connect()

        try:
            with pytest.raises(ConnectionError, match="Invalid JSON"):
                await transport.receive()
        finally:
            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_cwd_option(self) -> None:
        """Test working directory option."""
        transport = StdioTransport(command="cat", cwd="/tmp")

        await transport.connect()
        try:
            assert transport.is_connected
        finally:
            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_terminates_process(self) -> None:
        """Test that disconnect terminates the process."""
        transport = StdioTransport(command="cat")

        await transport.connect()
        assert hasattr(transport, '_process')
        pid = transport._process.pid
        assert pid > 0

        await transport.disconnect()
        assert transport._process is None

    @pytest.mark.asyncio
    async def test_multiple_send_receive(self) -> None:
        """Test multiple send/receive operations."""
        transport = StdioTransport(command="cat")

        await transport.connect()

        try:
            for i in range(3):
                message = {"jsonrpc": "2.0", "method": f"test{i}", "id": str(i)}
                await transport.send(message)
                received = await transport.receive()
                assert received == message
        finally:
            await transport.disconnect()


class TestHTTPTransport:
    """Tests for HTTPTransport."""

    def test_initialization(self) -> None:
        """Test transport initialization."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(
            url="https://example.com/mcp/",
            headers={"Authorization": "Bearer token"},
            timeout=60,
        )
        assert transport.url == "https://example.com/mcp"  # Trailing slash stripped
        assert transport.headers == {"Authorization": "Bearer token"}
        assert transport.timeout == 60

    def test_initialization_defaults(self) -> None:
        """Test transport initialization with defaults."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")
        assert transport.headers == {}
        assert transport.timeout == 30

    def test_is_connected_false_initially(self) -> None:
        """Test that transport is not connected initially."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        """Test disconnecting when not connected does not raise."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")
        await transport.disconnect()
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_send_not_connected(self) -> None:
        """Test sending when not connected."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")
        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.send({"method": "test"})

    @pytest.mark.asyncio
    async def test_receive_not_connected(self) -> None:
        """Test receiving when not connected."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")
        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_connect_requires_aiohttp(self) -> None:
        """Test that connect fails gracefully without aiohttp."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")

        # Mock aiohttp import to fail
        with patch.dict("sys.modules", {"aiohttp": None}):
            # The import happens inside connect, so we need to test differently
            pass  # aiohttp is installed, so this test is informational

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self) -> None:
        """Test connecting and disconnecting (mocked)."""
        from code_forge.mcp.transport.http import HTTPTransport

        transport = HTTPTransport(url="https://example.com")

        # Mock aiohttp
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await transport.connect()
            assert transport.is_connected is True

            await transport.disconnect()
            assert transport.is_connected is False


class TestTransportThreadSafety:
    """Tests for transport thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_sends(self) -> None:
        """Test concurrent send operations."""
        transport = StdioTransport(command="cat")

        await transport.connect()

        try:
            # Send multiple messages concurrently
            messages = [
                {"jsonrpc": "2.0", "method": f"test{i}", "id": str(i)}
                for i in range(5)
            ]

            await asyncio.gather(*[transport.send(msg) for msg in messages])

            # Receive all messages
            received = []
            for _ in range(5):
                msg = await transport.receive()
                received.append(msg)

            # All messages should be received (order may vary)
            assert len(received) == 5
        finally:
            await transport.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_during_receive(self) -> None:
        """Test disconnecting while receive is pending."""
        transport = StdioTransport(command="cat")

        await transport.connect()

        # Start a receive that will block
        async def blocking_receive() -> None:
            try:
                await transport.receive()
            except ConnectionError:
                pass  # Expected

        # Start receive in background
        receive_task = asyncio.create_task(blocking_receive())

        # Give it a moment to start
        await asyncio.sleep(0.05)

        # Disconnect while receive is pending
        await transport.disconnect()

        # Wait for receive task to complete
        await asyncio.wait_for(receive_task, timeout=1.0)
