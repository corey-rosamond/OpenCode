"""Tests for interrupt handler."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from code_forge.cli.interrupt import InterruptHandler, get_interrupt_handler


class TestInterruptHandler:
    """Tests for InterruptHandler class."""

    def test_initial_state(self) -> None:
        """Test handler starts in non-interrupted state."""
        handler = InterruptHandler()
        assert handler.interrupted is False

    def test_reset(self) -> None:
        """Test reset clears state."""
        handler = InterruptHandler()
        handler._interrupted = True
        handler._esc_count = 2
        handler._last_esc_time = 100.0

        handler.reset()

        assert handler.interrupted is False
        assert handler._esc_count == 0
        assert handler._last_esc_time == 0.0

    @pytest.mark.asyncio
    async def test_start_monitoring_sets_running(self) -> None:
        """Test start_monitoring sets running flag."""
        handler = InterruptHandler()

        # Mock stdin.isatty to return False (skip actual monitoring)
        with patch("sys.stdin.isatty", return_value=False):
            await handler.start_monitoring()

        assert handler._running is True

        await handler.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_monitoring_clears_running(self) -> None:
        """Test stop_monitoring clears running flag."""
        handler = InterruptHandler()
        handler._running = True

        await handler.stop_monitoring()

        assert handler._running is False

    @pytest.mark.asyncio
    async def test_stop_monitoring_cancels_task(self) -> None:
        """Test stop_monitoring cancels monitor task."""
        handler = InterruptHandler()

        # Create a real task that will be cancelled
        async def dummy_task() -> None:
            await asyncio.sleep(10)

        task = asyncio.create_task(dummy_task())
        handler._monitor_task = task
        handler._running = True

        await handler.stop_monitoring()

        assert task.cancelled()
        assert handler._monitor_task is None

    @pytest.mark.asyncio
    async def test_handle_esc_first_press(self) -> None:
        """Test first ESC press sets count."""
        handler = InterruptHandler()
        handler._on_first_esc = asyncio.Event()

        await handler._handle_esc()

        assert handler._esc_count == 1
        assert handler.interrupted is False
        assert handler._on_first_esc.is_set()

    @pytest.mark.asyncio
    async def test_handle_esc_double_press_triggers_interrupt(self) -> None:
        """Test double ESC press sets interrupted flag."""
        handler = InterruptHandler()
        handler._on_first_esc = asyncio.Event()

        # First press
        await handler._handle_esc()
        assert handler._esc_count == 1
        assert handler.interrupted is False

        # Second press (within window)
        await handler._handle_esc()
        assert handler._esc_count == 2
        assert handler.interrupted is True

    @pytest.mark.asyncio
    async def test_handle_esc_window_expiry(self) -> None:
        """Test ESC count resets after window expires."""
        handler = InterruptHandler()
        handler._on_first_esc = asyncio.Event()

        # First press
        await handler._handle_esc()
        assert handler._esc_count == 1

        # Simulate window expiry
        handler._last_esc_time = 0  # Old timestamp

        # Second press after window
        await handler._handle_esc()
        # Should reset and count as first press
        assert handler._esc_count == 1
        assert handler.interrupted is False

    @pytest.mark.asyncio
    async def test_wait_for_first_esc_returns_true_when_set(self) -> None:
        """Test wait_for_first_esc returns True when event is set."""
        handler = InterruptHandler()
        handler._on_first_esc = asyncio.Event()
        handler._on_first_esc.set()

        result = await handler.wait_for_first_esc(timeout=0.1)

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_first_esc_returns_false_on_timeout(self) -> None:
        """Test wait_for_first_esc returns False on timeout."""
        handler = InterruptHandler()
        handler._on_first_esc = asyncio.Event()

        result = await handler.wait_for_first_esc(timeout=0.01)

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_first_esc_returns_false_when_no_event(self) -> None:
        """Test wait_for_first_esc returns False when no event."""
        handler = InterruptHandler()
        handler._on_first_esc = None

        result = await handler.wait_for_first_esc(timeout=0.1)

        assert result is False


class TestGetInterruptHandler:
    """Tests for get_interrupt_handler function."""

    def test_returns_handler(self) -> None:
        """Test function returns an InterruptHandler."""
        handler = get_interrupt_handler()
        assert isinstance(handler, InterruptHandler)

    def test_returns_same_instance(self) -> None:
        """Test function returns singleton."""
        handler1 = get_interrupt_handler()
        handler2 = get_interrupt_handler()
        assert handler1 is handler2


class TestInterruptHandlerConstants:
    """Tests for InterruptHandler constants."""

    def test_esc_window(self) -> None:
        """Test ESC window constant is reasonable."""
        assert InterruptHandler.ESC_WINDOW == 1.5

    def test_esc_key(self) -> None:
        """Test ESC key constant is correct."""
        assert InterruptHandler.ESC_KEY == b'\x1b'
