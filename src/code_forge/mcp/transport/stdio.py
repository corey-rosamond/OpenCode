"""Stdio transport for subprocess-based MCP servers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from code_forge.mcp.transport.base import MCPTransport

logger = logging.getLogger(__name__)

# Environment variables that could be used for code injection or privilege escalation
# These are logged as warnings when set in MCP server configuration
DANGEROUS_ENV_VARS = frozenset({
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "PYTHONPATH",
    "NODE_OPTIONS",
    "PERL5LIB",
    "RUBYLIB",
})


class StdioTransport(MCPTransport):
    """Transport using stdio for subprocess communication.

    This transport launches an MCP server as a subprocess and communicates
    with it via stdin/stdout using newline-delimited JSON.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> None:
        """Initialize stdio transport.

        Args:
            command: Command to run.
            args: Command arguments.
            env: Environment variables (merged with current env).
            cwd: Working directory.
        """
        self.command = command
        self.args = args or []
        self.env = env
        self.cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Start subprocess and establish connection.

        Raises:
            ConnectionError: If subprocess fails to start.
        """
        # Build environment
        process_env = os.environ.copy()
        if self.env:
            # Check for potentially dangerous environment variables
            dangerous_vars = [k for k in self.env.keys() if k in DANGEROUS_ENV_VARS]
            if dangerous_vars:
                logger.warning(
                    f"MCP server config sets potentially dangerous environment variables: "
                    f"{', '.join(dangerous_vars)}. These could be used for code injection. "
                    f"Ensure your MCP config is from a trusted source."
                )
            # Expand environment variables in values
            for key, value in self.env.items():
                expanded = os.path.expandvars(value)
                process_env[key] = expanded

        # Start process with proper cleanup on failure
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=self.cwd,
            )

            # Verify process started successfully
            if process.returncode is not None:
                # Process exited immediately
                stderr_data = b""
                if process.stderr is not None:
                    stderr_data = await process.stderr.read()
                stderr_text = stderr_data.decode() if stderr_data else ""
                raise ConnectionError(
                    f"MCP server exited immediately with code {process.returncode}"
                    + (f": {stderr_text}" if stderr_text else "")
                )

            self._process = process
            logger.info(
                f"Started MCP server: {self.command} {' '.join(self.args)} "
                f"(PID: {self._process.pid})"
            )

        except FileNotFoundError as e:
            raise ConnectionError(f"Command not found: {self.command}") from e
        except PermissionError as e:
            raise ConnectionError(f"Permission denied: {self.command}") from e
        except Exception as e:
            # Clean up process if startup failed
            if process is not None and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass  # Best effort cleanup
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(f"Failed to start MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Terminate subprocess."""
        if self._process is not None:
            pid = self._process.pid
            try:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except TimeoutError:
                    logger.warning(f"Process {pid} did not terminate, killing")
                    self._process.kill()
                    await self._process.wait()
            except ProcessLookupError:
                # Process already exited
                pass
            except Exception as e:
                logger.warning(f"Error terminating process: {e}")
            finally:
                self._process = None

            logger.info(f"MCP server disconnected (was PID: {pid})")

    async def send(self, message: dict[str, Any]) -> None:
        """Send JSON-RPC message to subprocess stdin.

        Args:
            message: The message to send.

        Raises:
            ConnectionError: If not connected or write fails.
        """
        if self._process is None or self._process.stdin is None:
            raise ConnectionError("Not connected")

        if self._process.returncode is not None:
            raise ConnectionError(
                f"Process exited with code {self._process.returncode}"
            )

        async with self._write_lock:
            try:
                data = json.dumps(message)
                line = data + "\n"
                self._process.stdin.write(line.encode())
                await self._process.stdin.drain()
                logger.debug(f"Sent: {data}")
            except (BrokenPipeError, ConnectionResetError) as e:
                raise ConnectionError(f"Write failed: {e}") from e

    async def receive(self) -> dict[str, Any]:
        """Receive JSON-RPC message from subprocess stdout.

        Returns:
            The received message as a dictionary.

        Raises:
            ConnectionError: If not connected or read fails.
        """
        if self._process is None or self._process.stdout is None:
            raise ConnectionError("Not connected")

        async with self._read_lock:
            try:
                # Loop to skip empty lines (prevents stack overflow from recursion)
                max_empty_lines = 1000  # Safety limit
                empty_count = 0

                while True:
                    line = await self._process.stdout.readline()
                    if not line:
                        # Check if process exited
                        if self._process.returncode is not None:
                            raise ConnectionError(
                                f"Process exited with code {self._process.returncode}"
                            )
                        raise ConnectionError("Server closed connection")

                    data = line.decode().strip()
                    if data:
                        # Got non-empty data, process it
                        break

                    # Empty line - continue loop but track count for safety
                    empty_count += 1
                    if empty_count >= max_empty_lines:
                        raise ConnectionError(
                            f"Received {max_empty_lines} consecutive empty lines"
                        )

                logger.debug(f"Received: {data}")
                try:
                    result: dict[str, Any] = json.loads(data)
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from server: {data}")
                    raise ConnectionError(f"Invalid JSON from server: {e}") from e

            except (BrokenPipeError, ConnectionResetError) as e:
                raise ConnectionError(f"Read failed: {e}") from e

    @property
    def is_connected(self) -> bool:
        """Check if subprocess is running.

        Returns:
            True if process is running, False otherwise.
        """
        return self._process is not None and self._process.returncode is None
