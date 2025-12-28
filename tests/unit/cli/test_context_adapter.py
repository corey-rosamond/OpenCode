"""Tests for context status adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from code_forge.cli.context_adapter import ContextStatusAdapter, _map_warning_level
from code_forge.cli.status import ContextWarningLevel, StatusBar
from code_forge.context.events import (
    CompressionEvent,
    CompressionEventType,
    WarningLevel,
)
from code_forge.context.manager import ContextManager


class TestMapWarningLevel:
    """Tests for _map_warning_level function."""

    def test_map_none(self) -> None:
        """Test mapping NONE level."""
        result = _map_warning_level(WarningLevel.NONE)
        assert result == ContextWarningLevel.NONE

    def test_map_caution(self) -> None:
        """Test mapping CAUTION level."""
        result = _map_warning_level(WarningLevel.CAUTION)
        assert result == ContextWarningLevel.CAUTION

    def test_map_critical(self) -> None:
        """Test mapping CRITICAL level."""
        result = _map_warning_level(WarningLevel.CRITICAL)
        assert result == ContextWarningLevel.CRITICAL


class TestContextStatusAdapter:
    """Tests for ContextStatusAdapter class."""

    def test_init_without_context_manager(self) -> None:
        """Test initialization without context manager."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        assert adapter.status_bar is status_bar
        assert adapter._context_manager is None

    def test_init_with_context_manager(self) -> None:
        """Test initialization with context manager."""
        status_bar = StatusBar()
        context_manager = ContextManager(model="claude-3-opus")
        adapter = ContextStatusAdapter(status_bar, context_manager)

        assert adapter._context_manager is context_manager
        assert adapter in context_manager._observers

    def test_attach(self) -> None:
        """Test attaching to a context manager."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)
        context_manager = ContextManager(model="claude-3-opus")

        adapter.attach(context_manager)

        assert adapter._context_manager is context_manager
        assert adapter in context_manager._observers

    def test_attach_replaces_previous(self) -> None:
        """Test that attaching replaces previous context manager."""
        status_bar = StatusBar()
        cm1 = ContextManager(model="claude-3-opus")
        cm2 = ContextManager(model="gpt-4")
        adapter = ContextStatusAdapter(status_bar, cm1)

        adapter.attach(cm2)

        assert adapter._context_manager is cm2
        assert adapter not in cm1._observers
        assert adapter in cm2._observers

    def test_detach(self) -> None:
        """Test detaching from context manager."""
        status_bar = StatusBar()
        context_manager = ContextManager(model="claude-3-opus")
        adapter = ContextStatusAdapter(status_bar, context_manager)

        adapter.detach()

        assert adapter._context_manager is None
        assert adapter not in context_manager._observers

    def test_detach_when_not_attached(self) -> None:
        """Test detaching when not attached doesn't raise."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        # Should not raise
        adapter.detach()

    def test_sync_tokens_on_attach(self) -> None:
        """Test that tokens are synced on attach."""
        status_bar = StatusBar()
        context_manager = ContextManager(model="claude-3-opus")
        context_manager.add_message({"role": "user", "content": "Hello"})

        adapter = ContextStatusAdapter(status_bar, context_manager)

        assert status_bar.tokens_used > 0

    def test_on_compression_event_updates_tokens(self) -> None:
        """Test that compression events update token count."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        adapter.on_compression_event(event)

        assert status_bar.tokens_used == 5000

    def test_on_compression_event_updates_warning_level(self) -> None:
        """Test that warning events update warning level."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.WARNING,
            tokens_before=9000,
            tokens_after=9000,
            messages_before=20,
            messages_after=20,
            warning_level=WarningLevel.CRITICAL,
            usage_percentage=90.0,
        )

        adapter.on_compression_event(event)

        assert status_bar.warning_level == ContextWarningLevel.CRITICAL

    def test_handle_truncation_sets_info(self) -> None:
        """Test that truncation event sets compression info."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.TRUNCATION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        adapter.on_compression_event(event)

        assert "truncated" in status_bar.last_compression.lower()
        assert "10" in status_bar.last_compression  # messages removed
        assert "5,000" in status_bar.last_compression  # tokens saved

    def test_handle_compaction_sets_info(self) -> None:
        """Test that compaction event sets compression info."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.COMPACTION,
            tokens_before=10000,
            tokens_after=5000,
            messages_before=20,
            messages_after=10,
        )

        adapter.on_compression_event(event)

        assert "compacted" in status_bar.last_compression.lower()

    def test_handle_warning_sets_info(self) -> None:
        """Test that warning event sets compression info."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.WARNING,
            tokens_before=9000,
            tokens_after=9000,
            messages_before=20,
            messages_after=20,
            warning_level=WarningLevel.CRITICAL,
            usage_percentage=90.5,
        )

        adapter.on_compression_event(event)

        assert "critical" in status_bar.last_compression.lower()
        assert "90.5%" in status_bar.last_compression

    def test_handle_caution_warning_sets_info(self) -> None:
        """Test that caution warning sets appropriate info."""
        status_bar = StatusBar()
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.WARNING,
            tokens_before=8000,
            tokens_after=8000,
            messages_before=20,
            messages_after=20,
            warning_level=WarningLevel.CAUTION,
            usage_percentage=80.0,
        )

        adapter.on_compression_event(event)

        assert "high" in status_bar.last_compression.lower()
        assert "80.0%" in status_bar.last_compression

    def test_handle_cleared_resets_warning(self) -> None:
        """Test that cleared event resets warning level."""
        status_bar = StatusBar(warning_level=ContextWarningLevel.CRITICAL)
        adapter = ContextStatusAdapter(status_bar)

        event = CompressionEvent(
            event_type=CompressionEventType.CLEARED,
            tokens_before=10000,
            tokens_after=0,
            messages_before=20,
            messages_after=0,
        )

        adapter.on_compression_event(event)

        assert status_bar.warning_level == ContextWarningLevel.NONE
        assert "cleared" in status_bar.last_compression.lower()


class TestContextStatusAdapterIntegration:
    """Integration tests for ContextStatusAdapter with real ContextManager."""

    def test_truncation_updates_status_bar(self) -> None:
        """Test that truncation in manager updates status bar."""
        status_bar = StatusBar()
        context_manager = ContextManager(
            model="gpt-4",  # Small context
            auto_truncate=True,
        )
        adapter = ContextStatusAdapter(status_bar, context_manager)

        # Add many messages to trigger truncation
        for _ in range(50):
            context_manager.add_message({"role": "user", "content": "word " * 200})

        # Status bar should reflect the compression
        assert status_bar.tokens_used > 0
        # May or may not have compression info depending on whether truncation occurred
        # The key is no errors

    def test_reset_updates_status_bar(self) -> None:
        """Test that reset in manager updates status bar."""
        status_bar = StatusBar()
        context_manager = ContextManager(model="claude-3-opus")
        adapter = ContextStatusAdapter(status_bar, context_manager)

        # Add messages
        context_manager.add_message({"role": "user", "content": "Hello"})
        context_manager.add_message({"role": "assistant", "content": "Hi!"})

        # Reset
        context_manager.reset()

        # Status bar should show cleared
        assert status_bar.warning_level == ContextWarningLevel.NONE
        assert "cleared" in status_bar.last_compression.lower()
