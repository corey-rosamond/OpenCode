"""Context compression events.

This module defines events and observer patterns for context compression visibility.
Events are emitted when context is truncated, compacted, or approaches limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .manager import ContextManager


class CompressionEventType(str, Enum):
    """Types of compression events."""

    TRUNCATION = "truncation"  # Messages removed due to token limit
    COMPACTION = "compaction"  # Messages summarized by LLM
    WARNING = "warning"  # Approaching context limit
    CLEARED = "cleared"  # Context manually cleared


class WarningLevel(str, Enum):
    """Warning levels for context usage."""

    NONE = "none"  # Below 80%
    CAUTION = "caution"  # 80-90%
    CRITICAL = "critical"  # 90%+


@dataclass(frozen=True)
class CompressionEvent:
    """Event emitted when context is compressed or reaches thresholds.

    Attributes:
        event_type: Type of compression event.
        tokens_before: Token count before compression.
        tokens_after: Token count after compression.
        messages_before: Message count before compression.
        messages_after: Message count after compression.
        warning_level: Warning level for threshold events.
        usage_percentage: Current usage percentage (0-100).
        strategy: Name of compression strategy used.
    """

    event_type: CompressionEventType
    tokens_before: int
    tokens_after: int
    messages_before: int
    messages_after: int
    warning_level: WarningLevel = WarningLevel.NONE
    usage_percentage: float = 0.0
    strategy: str = ""

    @property
    def tokens_saved(self) -> int:
        """Number of tokens saved by compression."""
        return max(0, self.tokens_before - self.tokens_after)

    @property
    def messages_removed(self) -> int:
        """Number of messages removed by compression."""
        return max(0, self.messages_before - self.messages_after)

    @property
    def compression_ratio(self) -> float:
        """Compression ratio (0.0-1.0, lower is more compressed)."""
        if self.tokens_before == 0:
            return 1.0
        return self.tokens_after / self.tokens_before


class CompressionObserver(Protocol):
    """Protocol for observing compression events.

    Implement this protocol to receive notifications when
    context compression occurs or thresholds are reached.
    """

    def on_compression_event(self, event: CompressionEvent) -> None:
        """Called when a compression event occurs.

        Args:
            event: The compression event that occurred.
        """
        ...  # pragma: no cover


def get_warning_level(
    usage_percentage: float,
    warning_threshold: float = 80.0,
    critical_threshold: float = 90.0,
) -> WarningLevel:
    """Determine warning level from usage percentage.

    Args:
        usage_percentage: Current usage percentage (0-100).
        warning_threshold: Percentage for caution warning (default 80).
        critical_threshold: Percentage for critical warning (default 90).

    Returns:
        Appropriate warning level.
    """
    if usage_percentage >= critical_threshold:
        return WarningLevel.CRITICAL
    elif usage_percentage >= warning_threshold:
        return WarningLevel.CAUTION
    return WarningLevel.NONE
