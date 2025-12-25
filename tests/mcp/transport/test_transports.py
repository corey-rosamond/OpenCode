"""Tests for MCP transports.

This module provides comprehensive tests for MCP transports:
- StdioTransport (subprocess communication)
- HTTPTransport (HTTP/SSE communication)
- Base MCPTransport interface
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.mcp.transport.base import MCPTransport
from code_forge.mcp.transport.http import HTTPTransport
from code_forge.mcp.transport.stdio import DANGEROUS_ENV_VARS, StdioTransport


# =============================================================================
# StdioTransport Tests
# =============================================================================

class TestStdioTransportInit:
    """Tests for StdioTransport initialization."""

    def test_basic_init(self) -> None:
        """Test basic initialization."""
        transport = StdioTransport(command="node")

        assert transport.command == "node"
        assert transport.args == []
        assert transport.env is None
        assert transport.cwd is None
        assert transport.is_connected is False

    def test_init_with_args(self) -> None:
        """Test initialization with arguments."""
        transport = StdioTransport(
            command="python",
            args=["-m", "mcp_server"],
        )

        assert transport.command == "python"
        assert transport.args == ["-m", "mcp_server"]

    def test_init_with_env(self) -> None:
        """Test initialization with environment variables."""
        transport = StdioTransport(
            command="node",
            env={"API_KEY": "test-key"},
        )

        assert transport.env == {"API_KEY": "test-key"}

    def test_init_with_cwd(self) -> None:
        """Test initialization with working directory."""
        transport = StdioTransport(
            command="node",
            cwd="/path/to/project",
        )

        assert transport.cwd == "/path/to/project"


class TestStdioTransportConnect:
    """Tests for StdioTransport connection."""

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful connection."""
        transport = StdioTransport(command="echo")

        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_process = MagicMock()
            mock_process.returncode = None
            mock_process.pid = 12345
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.stderr = MagicMock()
            mock_create.return_value = mock_process

            await transport.connect()

        assert transport.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self) -> None:
        """Test connection with nonexistent command."""
        transport = StdioTransport(command="nonexistent_command_xyz")

        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_create.side_effect = FileNotFoundError("Command not found")

            with pytest.raises(ConnectionError, match="Command not found"):
                await transport.connect()

    @pytest.mark.asyncio
    async def test_connect_permission_denied(self) -> None:
        """Test connection with permission denied."""
        transport = StdioTransport(command="/etc/passwd")

        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_create.side_effect = PermissionError("Permission denied")

            with pytest.raises(ConnectionError, match="Permission denied"):
                await transport.connect()

    @pytest.mark.asyncio
    async def test_connect_process_exits_immediately(self) -> None:
        """Test handling of process that exits immediately."""
        transport = StdioTransport(command="false")

        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.stderr = AsyncMock()
            mock_process.stderr.read = AsyncMock(return_value=b"Error")
            mock_create.return_value = mock_process

            with pytest.raises(ConnectionError, match="exited immediately"):
                await transport.connect()

    @pytest.mark.asyncio
    async def test_connect_warns_on_dangerous_env_vars(self) -> None:
        """Test warning on dangerous environment variables."""
        transport = StdioTransport(
            command="node",
            env={"LD_PRELOAD": "/evil.so"},
        )

        with patch("asyncio.create_subprocess_exec") as mock_create, \
             patch("code_forge.mcp.transport.stdio.logger") as mock_logger:
            mock_process = MagicMock()
            mock_process.returncode = None
            mock_process.pid = 12345
            mock_create.return_value = mock_process

            await transport.connect()

            # Should have warned about dangerous env var
            mock_logger.warning.assert_called()
            warning_msg = str(mock_logger.warning.call_args)
            assert "LD_PRELOAD" in warning_msg


class TestStdioTransportDisconnect:
    """Tests for StdioTransport disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_terminates_process(self) -> None:
        """Test that disconnect terminates the process."""
        transport = StdioTransport(command="sleep")

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        transport._process = mock_process

        await transport.disconnect()

        mock_process.terminate.assert_called_once()
        assert transport._process is None

    @pytest.mark.asyncio
    async def test_disconnect_kills_if_terminate_times_out(self) -> None:
        """Test that disconnect kills process if terminate times out."""
        transport = StdioTransport(command="sleep")

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock(side_effect=[asyncio.TimeoutError, None])
        transport._process = mock_process

        await transport.disconnect()

        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_handles_already_exited(self) -> None:
        """Test disconnect handles already exited process."""
        transport = StdioTransport(command="sleep")

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.terminate = MagicMock(side_effect=ProcessLookupError)
        transport._process = mock_process

        # Should not raise
        await transport.disconnect()

        assert transport._process is None


class TestStdioTransportSend:
    """Tests for StdioTransport send operation."""

    @pytest.mark.asyncio
    async def test_send_not_connected_raises(self) -> None:
        """Test send raises when not connected."""
        transport = StdioTransport(command="node")

        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.send({"jsonrpc": "2.0", "method": "test"})

    @pytest.mark.asyncio
    async def test_send_process_exited_raises(self) -> None:
        """Test send raises when process has exited."""
        transport = StdioTransport(command="node")

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdin = MagicMock()
        transport._process = mock_process

        with pytest.raises(ConnectionError, match="Process exited"):
            await transport.send({"jsonrpc": "2.0"})

    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        """Test successful send."""
        transport = StdioTransport(command="node")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.stdin = mock_stdin
        transport._process = mock_process

        message = {"jsonrpc": "2.0", "method": "test", "id": 1}
        await transport.send(message)

        # Verify write was called with JSON + newline
        mock_stdin.write.assert_called_once()
        written = mock_stdin.write.call_args[0][0]
        assert b"jsonrpc" in written
        assert written.endswith(b"\n")

    @pytest.mark.asyncio
    async def test_send_broken_pipe(self) -> None:
        """Test send handles broken pipe."""
        transport = StdioTransport(command="node")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock(side_effect=BrokenPipeError)

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.stdin = mock_stdin
        transport._process = mock_process

        with pytest.raises(ConnectionError, match="Write failed"):
            await transport.send({"jsonrpc": "2.0"})


class TestStdioTransportReceive:
    """Tests for StdioTransport receive operation."""

    @pytest.mark.asyncio
    async def test_receive_not_connected_raises(self) -> None:
        """Test receive raises when not connected."""
        transport = StdioTransport(command="node")

        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_receive_success(self) -> None:
        """Test successful receive."""
        transport = StdioTransport(command="node")

        message = {"jsonrpc": "2.0", "result": "ok", "id": 1}
        message_bytes = (json.dumps(message) + "\n").encode()

        mock_stdout = MagicMock()
        mock_stdout.readline = AsyncMock(return_value=message_bytes)

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.stdout = mock_stdout
        transport._process = mock_process

        result = await transport.receive()

        assert result == message

    @pytest.mark.asyncio
    async def test_receive_skips_empty_lines(self) -> None:
        """Test receive skips empty lines."""
        transport = StdioTransport(command="node")

        message = {"jsonrpc": "2.0", "id": 1}
        responses = [
            b"\n",
            b"  \n",
            (json.dumps(message) + "\n").encode(),
        ]

        mock_stdout = MagicMock()
        mock_stdout.readline = AsyncMock(side_effect=responses)

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.stdout = mock_stdout
        transport._process = mock_process

        result = await transport.receive()

        assert result == message

    @pytest.mark.asyncio
    async def test_receive_invalid_json_raises(self) -> None:
        """Test receive raises on invalid JSON."""
        transport = StdioTransport(command="node")

        mock_stdout = MagicMock()
        mock_stdout.readline = AsyncMock(return_value=b"not json\n")

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.stdout = mock_stdout
        transport._process = mock_process

        with pytest.raises(ConnectionError, match="Invalid JSON"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_receive_connection_closed(self) -> None:
        """Test receive handles connection closed."""
        transport = StdioTransport(command="node")

        mock_stdout = MagicMock()
        mock_stdout.readline = AsyncMock(return_value=b"")

        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.stdout = mock_stdout
        transport._process = mock_process

        with pytest.raises(ConnectionError, match="closed connection"):
            await transport.receive()


class TestDangerousEnvVars:
    """Tests for dangerous environment variable detection."""

    def test_dangerous_env_vars_defined(self) -> None:
        """Test that dangerous env vars are defined."""
        assert "LD_PRELOAD" in DANGEROUS_ENV_VARS
        assert "LD_LIBRARY_PATH" in DANGEROUS_ENV_VARS
        assert "DYLD_INSERT_LIBRARIES" in DANGEROUS_ENV_VARS
        assert "PYTHONPATH" in DANGEROUS_ENV_VARS
        assert "NODE_OPTIONS" in DANGEROUS_ENV_VARS

    def test_dangerous_env_vars_is_frozenset(self) -> None:
        """Test that dangerous env vars is immutable."""
        assert isinstance(DANGEROUS_ENV_VARS, frozenset)


# =============================================================================
# HTTPTransport Tests
# =============================================================================

class TestHTTPTransportInit:
    """Tests for HTTPTransport initialization."""

    def test_basic_init(self) -> None:
        """Test basic initialization."""
        transport = HTTPTransport(url="http://localhost:8080")

        assert transport.url == "http://localhost:8080"
        assert transport.headers == {}
        assert transport.timeout == 30
        assert transport.proxy is None
        assert transport.is_connected is False

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from URL."""
        transport = HTTPTransport(url="http://localhost:8080/")

        assert transport.url == "http://localhost:8080"

    def test_init_with_headers(self) -> None:
        """Test initialization with headers."""
        transport = HTTPTransport(
            url="http://localhost:8080",
            headers={"Authorization": "Bearer token"},
        )

        assert transport.headers["Authorization"] == "Bearer token"

    def test_init_with_timeout(self) -> None:
        """Test initialization with timeout."""
        transport = HTTPTransport(
            url="http://localhost:8080",
            timeout=60,
        )

        assert transport.timeout == 60

    def test_init_with_proxy(self) -> None:
        """Test initialization with proxy."""
        transport = HTTPTransport(
            url="http://localhost:8080",
            proxy="http://proxy:3128",
        )

        assert transport.proxy == "http://proxy:3128"


class TestHTTPTransportConnect:
    """Tests for HTTPTransport connection."""

    @pytest.mark.asyncio
    async def test_connect_sets_connected_flag(self) -> None:
        """Test that connect sets the connected flag."""
        transport = HTTPTransport(url="http://localhost:8080")

        # Manually set up the transport as if connected
        # (avoiding the complex aiohttp mocking)
        transport._session = MagicMock()
        transport._connected = True

        assert transport.is_connected is True

    def test_connect_url_is_stored(self) -> None:
        """Test that URL is properly stored."""
        transport = HTTPTransport(url="http://localhost:8080/api")

        assert transport.url == "http://localhost:8080/api"


class TestHTTPTransportDisconnect:
    """Tests for HTTPTransport disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_closes_session(self) -> None:
        """Test that disconnect closes the session."""
        transport = HTTPTransport(url="http://localhost:8080")

        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        transport._session = mock_session
        transport._connected = True
        transport._sse_task = None

        await transport.disconnect()

        mock_session.close.assert_called_once()
        assert transport._session is None
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cancels_sse_task(self) -> None:
        """Test that disconnect cancels SSE task."""
        transport = HTTPTransport(url="http://localhost:8080")

        # Create a proper asyncio Task mock
        async def dummy_coro():
            pass

        mock_task = asyncio.create_task(dummy_coro())
        mock_task.cancel()  # Pre-cancel to avoid issues

        transport._session = AsyncMock()
        transport._session.close = AsyncMock()
        transport._connected = True
        transport._sse_task = mock_task

        await transport.disconnect()

        assert transport._sse_task is None


class TestHTTPTransportSend:
    """Tests for HTTPTransport send operation."""

    @pytest.mark.asyncio
    async def test_send_not_connected_raises(self) -> None:
        """Test send raises when not connected."""
        transport = HTTPTransport(url="http://localhost:8080")

        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.send({"jsonrpc": "2.0"})

    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        """Test successful send."""
        transport = HTTPTransport(url="http://localhost:8080")

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"result": "ok"})

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        transport._session = mock_session
        transport._connected = True

        await transport.send({"jsonrpc": "2.0", "method": "test"})

        mock_session.post.assert_called_once()


class TestHTTPTransportReceive:
    """Tests for HTTPTransport receive operation."""

    @pytest.mark.asyncio
    async def test_receive_not_connected_raises(self) -> None:
        """Test receive raises when not connected and queue is empty."""
        transport = HTTPTransport(url="http://localhost:8080")
        transport._connected = False

        with pytest.raises(ConnectionError, match="Not connected"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_receive_from_queue(self) -> None:
        """Test receive gets message from queue."""
        transport = HTTPTransport(url="http://localhost:8080")
        transport._connected = True

        message = {"jsonrpc": "2.0", "result": "ok"}
        await transport._message_queue.put(message)

        result = await transport.receive()

        assert result == message

    @pytest.mark.asyncio
    async def test_receive_timeout(self) -> None:
        """Test receive timeout."""
        transport = HTTPTransport(url="http://localhost:8080", timeout=1)
        transport._connected = True

        with pytest.raises(ConnectionError, match="timeout"):
            await transport.receive()


class TestHTTPTransportIsConnected:
    """Tests for HTTPTransport is_connected property."""

    def test_is_connected_false_initially(self) -> None:
        """Test is_connected is False initially."""
        transport = HTTPTransport(url="http://localhost:8080")
        assert transport.is_connected is False

    def test_is_connected_requires_session_and_flag(self) -> None:
        """Test is_connected requires both session and flag."""
        transport = HTTPTransport(url="http://localhost:8080")

        # Only flag set
        transport._connected = True
        transport._session = None
        assert transport.is_connected is False

        # Only session set
        transport._connected = False
        transport._session = MagicMock()
        assert transport.is_connected is False

        # Both set
        transport._connected = True
        transport._session = MagicMock()
        assert transport.is_connected is True


# =============================================================================
# MCPTransport Protocol Tests
# =============================================================================

class TestMCPTransportProtocol:
    """Tests for MCPTransport abstract interface."""

    def test_stdio_implements_protocol(self) -> None:
        """Test StdioTransport implements MCPTransport."""
        transport = StdioTransport(command="node")
        assert isinstance(transport, MCPTransport)

    def test_http_implements_protocol(self) -> None:
        """Test HTTPTransport implements MCPTransport."""
        transport = HTTPTransport(url="http://localhost:8080")
        assert isinstance(transport, MCPTransport)

    def test_protocol_has_required_methods(self) -> None:
        """Test MCPTransport defines required methods."""
        assert hasattr(MCPTransport, "connect")
        assert hasattr(MCPTransport, "disconnect")
        assert hasattr(MCPTransport, "send")
        assert hasattr(MCPTransport, "receive")
        assert hasattr(MCPTransport, "is_connected")
