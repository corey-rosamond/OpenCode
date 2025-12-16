"""Shell process management for background command execution."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from code_forge.core.logging import get_logger

if TYPE_CHECKING:
    from asyncio.subprocess import Process

logger = get_logger("shell")


class ShellStatus(str, Enum):
    """Status of a shell process."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMEOUT = "timeout"


@dataclass
class ShellProcess:
    """Represents a background shell process.

    Tracks process state, output buffers, and provides
    methods for reading output and controlling the process.

    Uses deque-based chunk storage for O(1) append operations instead
    of O(n) string concatenation. The stdout_buffer and stderr_buffer
    properties compute the full string lazily when accessed.
    """

    # Maximum buffer size (10MB) to prevent memory exhaustion
    MAX_BUFFER_SIZE: ClassVar[int] = 10 * 1024 * 1024

    id: str
    command: str
    working_dir: str
    process: Process | None = None
    status: ShellStatus = ShellStatus.PENDING
    exit_code: int | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    last_read_stdout: int = 0
    last_read_stderr: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    # Private chunk storage for O(1) appends (not exposed in init/repr)
    _stdout_chunks: deque[str] = field(default_factory=deque, init=False, repr=False)
    _stderr_chunks: deque[str] = field(default_factory=deque, init=False, repr=False)
    _stdout_size: int = field(default=0, init=False, repr=False)
    _stderr_size: int = field(default=0, init=False, repr=False)

    @property
    def stdout_buffer(self) -> str:
        """Get stdout buffer as string (computed from chunks)."""
        return "".join(self._stdout_chunks)

    @property
    def stderr_buffer(self) -> str:
        """Get stderr buffer as string (computed from chunks)."""
        return "".join(self._stderr_chunks)

    def _append_to_buffer(self, buffer_name: str, data: str) -> None:
        """Append data to buffer with size limit.

        Uses deque-based storage for O(1) appends. When max size is reached,
        removes oldest chunks to make room for new data.

        Args:
            buffer_name: 'stdout' or 'stderr'
            data: Data to append
        """
        if buffer_name == "stdout":
            self._stdout_chunks.append(data)
            self._stdout_size += len(data)
            # Trim oldest chunks if over limit
            while self._stdout_size > self.MAX_BUFFER_SIZE and self._stdout_chunks:
                removed = self._stdout_chunks.popleft()
                self._stdout_size -= len(removed)
                self.stdout_truncated = True
        else:
            self._stderr_chunks.append(data)
            self._stderr_size += len(data)
            # Trim oldest chunks if over limit
            while self._stderr_size > self.MAX_BUFFER_SIZE and self._stderr_chunks:
                removed = self._stderr_chunks.popleft()
                self._stderr_size -= len(removed)
                self.stderr_truncated = True

    def get_new_output(self, include_stderr: bool = True) -> str:
        """Get output since last read.

        Args:
            include_stderr: Whether to include stderr in output.

        Returns:
            New output since last read.
        """
        stdout = self.stdout_buffer[self.last_read_stdout :]
        self.last_read_stdout = len(self.stdout_buffer)

        if include_stderr:
            stderr = self.stderr_buffer[self.last_read_stderr :]
            self.last_read_stderr = len(self.stderr_buffer)
            if stderr:
                stdout += f"\n[stderr]\n{stderr}"

        return stdout

    def get_all_output(self) -> str:
        """Get all output from the process."""
        output = self.stdout_buffer
        if self.stderr_buffer:
            output += f"\n[stderr]\n{self.stderr_buffer}"
        return output

    async def read_output(self) -> bool:
        """Read available output from process streams.

        Reads all currently available data from stdout and stderr.

        Returns:
            True if any data was read.
        """
        if self.process is None:
            return False

        read_any = False

        # Read all available stdout
        if self.process.stdout:
            while True:
                try:
                    data = await asyncio.wait_for(
                        self.process.stdout.read(4096), timeout=0.05
                    )
                    if data:
                        self._append_to_buffer("stdout", data.decode("utf-8", errors="replace"))
                        read_any = True
                    else:
                        # Empty data means EOF
                        break
                except TimeoutError:
                    # No more data available right now
                    break
                except OSError as e:
                    # Pipe broken, process terminated, etc.
                    logger.debug(f"stdout read OSError (shell {self.id}): {e}")
                    break
                except Exception as e:
                    # Unexpected error - log for debugging
                    logger.warning(
                        f"Unexpected error reading stdout (shell {self.id}): "
                        f"{type(e).__name__}: {e}"
                    )
                    break

        # Read all available stderr
        if self.process.stderr:
            while True:
                try:
                    data = await asyncio.wait_for(
                        self.process.stderr.read(4096), timeout=0.05
                    )
                    if data:
                        self._append_to_buffer("stderr", data.decode("utf-8", errors="replace"))
                        read_any = True
                    else:
                        # Empty data means EOF
                        break
                except TimeoutError:
                    # No more data available right now
                    break
                except OSError as e:
                    # Pipe broken, process terminated, etc.
                    logger.debug(f"stderr read OSError (shell {self.id}): {e}")
                    break
                except Exception as e:
                    # Unexpected error - log for debugging
                    logger.warning(
                        f"Unexpected error reading stderr (shell {self.id}): "
                        f"{type(e).__name__}: {e}"
                    )
                    break

        return read_any

    async def wait(self, timeout: float | None = None) -> int:
        """Wait for process to complete.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            Exit code.

        Raises:
            TimeoutError: If timeout exceeded.
            RuntimeError: If process not started.
        """
        if self.process is None:
            raise RuntimeError("Process not started")

        try:
            exit_code = await asyncio.wait_for(self.process.wait(), timeout=timeout)
            self.exit_code = exit_code
            self.completed_at = time.time()
            self.status = ShellStatus.COMPLETED if exit_code == 0 else ShellStatus.FAILED
            return exit_code
        except TimeoutError:
            self.status = ShellStatus.TIMEOUT
            raise

    def kill(self) -> None:
        """Kill the process."""
        if self.process and self.process.returncode is None:
            self.process.kill()
        self.status = ShellStatus.KILLED
        self.completed_at = time.time()

    def terminate(self) -> None:
        """Send SIGTERM to the process."""
        if self.process and self.process.returncode is None:
            self.process.terminate()

    @property
    def is_running(self) -> bool:
        """Check if process is still running."""
        if self.process is None:
            return False
        return self.process.returncode is None

    @property
    def duration_ms(self) -> float | None:
        """Get duration in milliseconds."""
        if self.started_at is None:
            return None
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000


class ShellManager:
    """Manages background shell processes.

    Singleton pattern ensures global access to shell state.
    Provides methods for creating, tracking, and cleaning up shells.
    """

    _instance: ClassVar[ShellManager | None] = None
    _shells: dict[str, ShellProcess]
    _lock: asyncio.Lock | None  # Created lazily in async context

    def __new__(cls) -> ShellManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._shells = {}
            cls._instance._lock = None  # Lazy init - asyncio.Lock() requires running loop
        return cls._instance

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the async lock (lazy initialization).

        The lock is created on first use within an async context.
        This ensures the lock is associated with the current event loop.

        Returns:
            asyncio.Lock instance.

        Raises:
            RuntimeError: If called outside of an async context.
        """
        # Ensure we're in an async context before creating/using the lock
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                "ShellManager._get_lock() must be called from within an async context. "
                "All ShellManager async methods must be awaited within a running event loop."
            ) from None

        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        if cls._instance:
            # Kill all running shells
            for shell in cls._instance._shells.values():
                if shell.is_running:
                    shell.kill()
            cls._instance._shells.clear()
            cls._instance._lock = None
        cls._instance = None

    @classmethod
    async def create_shell(
        cls,
        command: str,
        working_dir: str,
        env: dict[str, str] | None = None,
    ) -> ShellProcess:
        """Create and start a new background shell.

        Args:
            command: Command to execute.
            working_dir: Working directory for command.
            env: Optional environment variables.

        Returns:
            ShellProcess instance.
        """
        manager = cls()
        shell_id = f"shell_{uuid.uuid4().hex[:8]}"

        shell = ShellProcess(
            id=shell_id,
            command=command,
            working_dir=working_dir,
        )

        # Prepare environment
        shell_env = os.environ.copy()
        if env:
            shell_env.update(env)

        # Start process
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=shell_env,
        )

        shell.process = process
        shell.status = ShellStatus.RUNNING
        shell.started_at = time.time()

        async with manager._get_lock():
            manager._shells[shell_id] = shell

        return shell

    @classmethod
    def get_shell(cls, shell_id: str) -> ShellProcess | None:
        """Get shell by ID."""
        manager = cls()
        return manager._shells.get(shell_id)

    @classmethod
    def list_shells(cls) -> list[ShellProcess]:
        """List all shells."""
        manager = cls()
        return list(manager._shells.values())

    @classmethod
    def list_running(cls) -> list[ShellProcess]:
        """List running shells."""
        manager = cls()
        return [s for s in manager._shells.values() if s.is_running]

    @classmethod
    async def cleanup_completed(cls, max_age_seconds: float = 3600) -> int:
        """Remove completed shells older than max_age.

        Args:
            max_age_seconds: Maximum age for completed shells.

        Returns:
            Number of shells removed.
        """
        manager = cls()
        now = time.time()
        to_remove = []

        async with manager._get_lock():
            for shell_id, shell in manager._shells.items():
                is_old = shell.completed_at and (now - shell.completed_at) > max_age_seconds
                if not shell.is_running and is_old:
                    to_remove.append(shell_id)

            for shell_id in to_remove:
                del manager._shells[shell_id]

        return len(to_remove)

    @classmethod
    async def kill_all(cls) -> int:
        """Kill all running shells. Returns count killed."""
        manager = cls()
        count = 0

        async with manager._get_lock():
            for shell in manager._shells.values():
                if shell.is_running:
                    shell.kill()
                    count += 1

        return count
