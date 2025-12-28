"""Interrupt handler for Code-Forge CLI.

This module provides the InterruptHandler class for detecting ESC key presses
during streaming operations, allowing users to cancel long-running operations.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import termios
import tty
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def raw_mode() -> Iterator[None]:
    """Context manager to put terminal in raw mode for key detection.

    Saves terminal settings and restores them on exit.

    Yields:
        None
    """
    if not sys.stdin.isatty():
        yield
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class InterruptHandler:
    """Handles ESC key interrupts during streaming operations.

    Monitors keyboard input for double-ESC presses to cancel operations.
    Uses a double-press mechanism to avoid accidental interrupts.

    Attributes:
        interrupted: Whether an interrupt has been requested.
        esc_count: Number of consecutive ESC presses.
        last_esc_time: Time of last ESC press.
    """

    # Time window for double-ESC detection (seconds)
    ESC_WINDOW = 1.5

    # ESC key code
    ESC_KEY = b'\x1b'

    def __init__(self) -> None:
        """Initialize interrupt handler."""
        self._interrupted = False
        self._esc_count = 0
        self._last_esc_time = 0.0
        self._monitor_task: asyncio.Task[None] | None = None
        self._running = False
        self._on_first_esc: asyncio.Event | None = None

    @property
    def interrupted(self) -> bool:
        """Check if interrupt was requested.

        Returns:
            True if double-ESC was detected.
        """
        return self._interrupted

    def reset(self) -> None:
        """Reset interrupt state for new operation."""
        self._interrupted = False
        self._esc_count = 0
        self._last_esc_time = 0.0

    async def start_monitoring(self) -> None:
        """Start monitoring for ESC key presses.

        Creates a background task that reads stdin for ESC sequences.
        """
        if self._running:
            return

        self.reset()
        self._running = True
        self._on_first_esc = asyncio.Event()
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop monitoring for ESC key presses.

        Cancels the background monitoring task.
        """
        self._running = False
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None
        self._on_first_esc = None

    async def _monitor_loop(self) -> None:
        """Main monitoring loop for ESC detection.

        Runs in a separate task, reading stdin for ESC key presses.
        Uses non-blocking reads with small timeouts.
        """
        if not sys.stdin.isatty():
            return

        loop = asyncio.get_event_loop()
        fd = sys.stdin.fileno()

        # Save terminal settings
        try:
            old_settings = termios.tcgetattr(fd)
        except termios.error:
            return

        try:
            # Set terminal to raw mode for character-by-character reading
            tty.setcbreak(fd)

            while self._running and not self._interrupted:
                try:
                    # Use asyncio to read with timeout
                    ready = await asyncio.wait_for(
                        loop.run_in_executor(None, self._check_input),
                        timeout=0.1
                    )

                    if ready:
                        char = sys.stdin.read(1)
                        if char == '\x1b':  # ESC
                            await self._handle_esc()

                except TimeoutError:
                    # Check if ESC window expired
                    if self._esc_count > 0:
                        current_time = asyncio.get_event_loop().time()
                        if current_time - self._last_esc_time > self.ESC_WINDOW:
                            self._esc_count = 0
                    continue
                except asyncio.CancelledError:
                    break

        finally:
            # Restore terminal settings
            with contextlib.suppress(termios.error):
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _check_input(self) -> bool:
        """Check if input is available on stdin.

        Returns:
            True if input is available.
        """
        import select
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        return bool(ready)

    async def _handle_esc(self) -> None:
        """Handle an ESC key press.

        Tracks consecutive ESC presses within the time window.
        Sets interrupted flag on double-ESC.
        """
        current_time = asyncio.get_event_loop().time()

        # Check if within time window of previous ESC
        if self._esc_count > 0 and current_time - self._last_esc_time > self.ESC_WINDOW:
            # Window expired, start fresh
            self._esc_count = 0

        self._esc_count += 1
        self._last_esc_time = current_time

        if self._esc_count == 1:
            # First ESC - signal for UI feedback
            if self._on_first_esc:
                self._on_first_esc.set()
        elif self._esc_count >= 2:
            # Double ESC - interrupt!
            self._interrupted = True

    async def wait_for_first_esc(self, timeout: float = 0.1) -> bool:
        """Wait for first ESC press notification.

        Args:
            timeout: Maximum time to wait.

        Returns:
            True if first ESC was pressed.
        """
        if self._on_first_esc is None:
            return False
        try:
            await asyncio.wait_for(self._on_first_esc.wait(), timeout=timeout)
            return True
        except TimeoutError:
            return False


# Global interrupt handler instance
_interrupt_handler: InterruptHandler | None = None


def get_interrupt_handler() -> InterruptHandler:
    """Get or create the global interrupt handler.

    Returns:
        The global InterruptHandler instance.
    """
    global _interrupt_handler  # noqa: PLW0603
    if _interrupt_handler is None:
        _interrupt_handler = InterruptHandler()
    return _interrupt_handler
