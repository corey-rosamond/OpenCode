"""Context compression adapter for StatusBar.

This module provides an adapter that bridges ContextManager compression
events to StatusBar updates, providing real-time visibility into
context compression operations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from code_forge.context.events import (
    CompressionEvent,
    CompressionEventType,
    WarningLevel,
)

from .status import ContextWarningLevel, StatusBar

if TYPE_CHECKING:
    from code_forge.context import ContextManager

logger = logging.getLogger(__name__)


def _map_warning_level(level: WarningLevel) -> ContextWarningLevel:
    """Map context WarningLevel to StatusBar ContextWarningLevel.

    Args:
        level: Context warning level.

    Returns:
        Corresponding StatusBar warning level.
    """
    if level == WarningLevel.CRITICAL:
        return ContextWarningLevel.CRITICAL
    elif level == WarningLevel.CAUTION:
        return ContextWarningLevel.CAUTION
    return ContextWarningLevel.NONE


class ContextStatusAdapter:
    """Adapter that connects ContextManager events to StatusBar.

    This adapter implements the CompressionObserver protocol and
    updates the StatusBar with compression events and warnings.

    Attributes:
        status_bar: The StatusBar to update.
        context_manager: The ContextManager to observe.
    """

    def __init__(
        self,
        status_bar: StatusBar,
        context_manager: ContextManager | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            status_bar: StatusBar to update with events.
            context_manager: Optional ContextManager to observe.
        """
        self.status_bar = status_bar
        self._context_manager: ContextManager | None = None

        if context_manager:
            self.attach(context_manager)

    def attach(self, context_manager: ContextManager) -> None:
        """Attach to a ContextManager to observe its events.

        Args:
            context_manager: ContextManager to observe.
        """
        if self._context_manager:
            self._context_manager.remove_observer(self)

        self._context_manager = context_manager
        context_manager.add_observer(self)

        # Initial sync
        self._sync_tokens()

    def detach(self) -> None:
        """Detach from the current ContextManager."""
        if self._context_manager:
            self._context_manager.remove_observer(self)
            self._context_manager = None

    def _sync_tokens(self) -> None:
        """Sync current token count from ContextManager to StatusBar."""
        if self._context_manager:
            self.status_bar.set_tokens(
                used=self._context_manager.token_usage,
                max_tokens=self._context_manager.tracker.limits.effective_limit,
            )

    def on_compression_event(self, event: CompressionEvent) -> None:
        """Handle compression events from ContextManager.

        Args:
            event: The compression event that occurred.
        """
        # Update token count
        self.status_bar.set_tokens(
            used=event.tokens_after,
            max_tokens=self.status_bar.tokens_max,
        )

        # Update warning level
        self.status_bar.set_warning_level(_map_warning_level(event.warning_level))

        # Generate compression notification
        if event.event_type == CompressionEventType.TRUNCATION:
            self._handle_truncation(event)
        elif event.event_type == CompressionEventType.COMPACTION:
            self._handle_compaction(event)
        elif event.event_type == CompressionEventType.WARNING:
            self._handle_warning(event)
        elif event.event_type == CompressionEventType.CLEARED:
            self._handle_cleared(event)

    def _handle_truncation(self, event: CompressionEvent) -> None:
        """Handle truncation event.

        Args:
            event: Truncation event.
        """
        msgs_removed = event.messages_removed
        tokens_saved = event.tokens_saved

        info = f"Context truncated: {msgs_removed} messages removed, {tokens_saved:,} tokens freed"
        self.status_bar.set_compression_info(info)
        logger.info(info)

    def _handle_compaction(self, event: CompressionEvent) -> None:
        """Handle compaction event.

        Args:
            event: Compaction event.
        """
        msgs_removed = event.messages_removed
        tokens_saved = event.tokens_saved
        ratio = event.compression_ratio

        info = (
            f"Context compacted: {msgs_removed} messages summarized, "
            f"{tokens_saved:,} tokens freed ({ratio:.0%} of original)"
        )
        self.status_bar.set_compression_info(info)
        logger.info(info)

    def _handle_warning(self, event: CompressionEvent) -> None:
        """Handle warning event.

        Args:
            event: Warning event.
        """
        level = event.warning_level
        usage = event.usage_percentage

        if level == WarningLevel.CRITICAL:
            info = f"Context usage critical: {usage:.1f}% - responses may lose context"
        else:
            info = f"Context usage high: {usage:.1f}% - approaching limit"

        self.status_bar.set_compression_info(info)
        logger.warning(info)

    def _handle_cleared(self, event: CompressionEvent) -> None:
        """Handle cleared event.

        Args:
            event: Cleared event.
        """
        msgs_cleared = event.messages_before
        tokens_cleared = event.tokens_before

        info = f"Context cleared: {msgs_cleared} messages, {tokens_cleared:,} tokens"
        self.status_bar.set_compression_info(info)
        self.status_bar.set_warning_level(ContextWarningLevel.NONE)
        logger.info(info)
