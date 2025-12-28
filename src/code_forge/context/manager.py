"""Central context management."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from .compaction import ContextCompactor, LLMProtocol, ToolResultCompactor
from .events import (
    CompressionEvent,
    CompressionEventType,
    CompressionObserver,
    WarningLevel,
    get_warning_level,
)
from .limits import ContextTracker
from .strategies import (
    CompositeStrategy,
    SlidingWindowStrategy,
    SmartTruncationStrategy,
    TokenBudgetStrategy,
    TruncationStrategy,
)
from .tokens import TokenCounter, get_counter

logger = logging.getLogger(__name__)


class TruncationMode(str, Enum):
    """Truncation mode selection."""

    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUDGET = "token_budget"
    SMART = "smart"
    SUMMARIZE = "summarize"


def get_strategy(mode: TruncationMode) -> TruncationStrategy:
    """Get truncation strategy for mode.

    Args:
        mode: Truncation mode.

    Returns:
        TruncationStrategy instance.
    """
    if mode == TruncationMode.SLIDING_WINDOW:
        return SlidingWindowStrategy()
    elif mode == TruncationMode.TOKEN_BUDGET:
        return TokenBudgetStrategy()
    elif mode == TruncationMode.SMART:
        return SmartTruncationStrategy()
    elif mode == TruncationMode.SUMMARIZE:
        # Summarize falls back to smart truncation
        return CompositeStrategy(
            [
                SmartTruncationStrategy(),
                TokenBudgetStrategy(),
            ]
        )
    else:
        return SmartTruncationStrategy()


class ContextManager:
    """Central context management.

    Coordinates token counting, tracking, and truncation
    to keep context within model limits.
    """

    def __init__(
        self,
        model: str,
        mode: TruncationMode = TruncationMode.SMART,
        llm: LLMProtocol | None = None,
        auto_truncate: bool = True,
        warning_threshold: float = 80.0,
        critical_threshold: float = 90.0,
    ) -> None:
        """Initialize context manager.

        Args:
            model: Model name for limits and counting.
            mode: Truncation mode to use.
            llm: LLM client for summarization (optional).
            auto_truncate: Automatically truncate on overflow.
            warning_threshold: Usage percentage for caution warning (default 80).
            critical_threshold: Usage percentage for critical warning (default 90).
        """
        self.model = model
        self.mode = mode
        self.auto_truncate = auto_truncate
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        # Initialize components
        self.counter: TokenCounter = get_counter(model)
        self.tracker: ContextTracker = ContextTracker.for_model(model)
        self.strategy: TruncationStrategy = get_strategy(mode)

        # Optional compactors
        self.compactor: ContextCompactor | None = (
            ContextCompactor(llm) if llm else None
        )
        self.tool_compactor: ToolResultCompactor = ToolResultCompactor()

        # Internal state
        self._messages: list[dict[str, Any]] = []
        self._system_prompt: str = ""
        self._observers: list[CompressionObserver] = []
        self._last_warning_level: WarningLevel = WarningLevel.NONE

    def set_system_prompt(self, prompt: str) -> int:
        """Set the system prompt.

        Args:
            prompt: System prompt text.

        Returns:
            Token count for prompt.
        """
        self._system_prompt = prompt
        return self.tracker.set_system_prompt(prompt)

    def set_tool_definitions(self, tools: list[dict[str, Any]]) -> int:
        """Set tool definitions.

        Args:
            tools: Tool definition list.

        Returns:
            Token count for tools.
        """
        return self.tracker.set_tool_definitions(tools)

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to context.

        Automatically truncates if needed and auto_truncate is enabled.
        Emits warning events when usage crosses thresholds.

        Args:
            message: Message to add.
        """
        # Compact tool results if needed
        if message.get("role") == "tool":
            message = self.tool_compactor.compact_message(message, self.counter)

        self._messages.append(message)
        self.tracker.add_message(message)

        # Check for overflow
        if self.auto_truncate and self.tracker.exceeds_limit():
            self._truncate()

        # Check warning thresholds after adding message
        self._check_warning_threshold()

    def add_messages(self, messages: list[dict[str, Any]]) -> None:
        """Add multiple messages.

        Args:
            messages: Messages to add.
        """
        for message in messages:
            self.add_message(message)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get current message list.

        Returns:
            Current messages.
        """
        return list(self._messages)

    def get_context_for_request(self) -> list[dict[str, Any]]:
        """Get messages ready for LLM request.

        Includes system prompt as first message.

        Returns:
            Messages for LLM request.
        """
        messages: list[dict[str, Any]] = []

        if self._system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self._system_prompt,
                }
            )

        messages.extend(self._messages)
        return messages

    def add_observer(self, observer: CompressionObserver) -> None:
        """Add a compression event observer.

        Args:
            observer: Observer to add.
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: CompressionObserver) -> None:
        """Remove a compression event observer.

        Args:
            observer: Observer to remove.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_observers(self, event: CompressionEvent) -> None:
        """Notify all observers of a compression event.

        Args:
            event: Event to broadcast.
        """
        for observer in self._observers:
            try:
                observer.on_compression_event(event)
            except Exception as e:
                logger.warning(f"Observer failed to handle event: {e}")

    def _check_warning_threshold(self) -> None:
        """Check if usage has crossed a warning threshold and emit event."""
        usage = self.usage_percentage
        current_level = get_warning_level(
            usage,
            warning_threshold=self.warning_threshold,
            critical_threshold=self.critical_threshold,
        )

        # Only emit if level increased (went from none->caution or caution->critical)
        if current_level != self._last_warning_level:
            if current_level != WarningLevel.NONE:
                event = CompressionEvent(
                    event_type=CompressionEventType.WARNING,
                    tokens_before=self.token_usage,
                    tokens_after=self.token_usage,
                    messages_before=len(self._messages),
                    messages_after=len(self._messages),
                    warning_level=current_level,
                    usage_percentage=usage,
                )
                self._notify_observers(event)
            self._last_warning_level = current_level

    def _truncate(self) -> None:
        """Truncate messages to fit within limit.

        Validates that truncated result fits within budget.
        Logs warning if truncation was insufficient.
        Emits CompressionEvent when messages are removed.
        """
        tokens_before = self.token_usage
        messages_before = len(self._messages)
        target_tokens = self.tracker.budget.conversation_budget

        truncated = self.strategy.truncate(
            self._messages,
            target_tokens,
            self.counter,
        )

        if len(truncated) < len(self._messages):
            logger.info(
                f"Truncated context: {len(self._messages)} -> {len(truncated)} messages"
            )
            self._messages = truncated
            self.tracker.update(truncated)

            # Emit truncation event
            tokens_after = self.token_usage
            event = CompressionEvent(
                event_type=CompressionEventType.TRUNCATION,
                tokens_before=tokens_before,
                tokens_after=tokens_after,
                messages_before=messages_before,
                messages_after=len(truncated),
                usage_percentage=self.usage_percentage,
                strategy=self.mode.value,
            )
            self._notify_observers(event)

            # Validate truncation result
            actual_tokens = sum(
                self.counter.count_message(msg) for msg in truncated
            )
            if actual_tokens > target_tokens:
                logger.warning(
                    f"Truncation insufficient: {actual_tokens} tokens "
                    f"exceeds target {target_tokens} by {actual_tokens - target_tokens}"
                )
        elif self.tracker.exceeds_limit():
            # Truncation didn't reduce messages but we're still over limit
            logger.warning(
                "Truncation failed to reduce message count while over limit"
            )

    async def compact_if_needed(self, threshold: float = 0.9) -> bool:
        """Compact context if usage exceeds threshold.

        Args:
            threshold: Usage percentage to trigger compaction.

        Returns:
            True if compaction occurred.
        """
        if not self.compactor:
            return False

        usage = self.tracker.usage_percentage()

        if usage < threshold * 100:
            return False

        tokens_before = self.token_usage
        messages_before = len(self._messages)
        target_tokens = int(self.tracker.budget.conversation_budget * 0.7)

        compacted = await self.compactor.compact(
            self._messages,
            target_tokens,
            self.counter,
        )

        if len(compacted) < len(self._messages):
            self._messages = compacted
            self.tracker.update(compacted)

            # Emit compaction event
            tokens_after = self.token_usage
            event = CompressionEvent(
                event_type=CompressionEventType.COMPACTION,
                tokens_before=tokens_before,
                tokens_after=tokens_after,
                messages_before=messages_before,
                messages_after=len(compacted),
                usage_percentage=self.usage_percentage,
                strategy="llm_summarization",
            )
            self._notify_observers(event)
            return True

        return False

    @property
    def token_usage(self) -> int:
        """Current token usage.

        Returns:
            Total tokens in use.
        """
        return self.tracker.current_tokens()

    @property
    def available_tokens(self) -> int:
        """Available tokens for new content.

        Returns:
            Available tokens.
        """
        return self.tracker.available_tokens()

    @property
    def usage_percentage(self) -> float:
        """Context usage percentage.

        Returns:
            Usage as percentage.
        """
        return self.tracker.usage_percentage()

    @property
    def is_near_limit(self) -> bool:
        """Check if near context limit.

        Returns:
            True if over 80% usage.
        """
        return self.usage_percentage > 80

    def reset(self) -> None:
        """Clear all messages and emit cleared event."""
        tokens_before = self.token_usage
        messages_before = len(self._messages)

        self._messages = []
        self.tracker.reset()
        self._last_warning_level = WarningLevel.NONE

        # Emit cleared event if there were messages
        if messages_before > 0:
            event = CompressionEvent(
                event_type=CompressionEventType.CLEARED,
                tokens_before=tokens_before,
                tokens_after=0,
                messages_before=messages_before,
                messages_after=0,
                usage_percentage=0.0,
            )
            self._notify_observers(event)

    def get_stats(self) -> dict[str, Any]:
        """Get context statistics.

        Returns:
            Dictionary of stats.
        """
        return {
            "model": self.model,
            "mode": self.mode.value,
            "message_count": len(self._messages),
            "token_usage": self.token_usage,
            "available_tokens": self.available_tokens,
            "usage_percentage": self.usage_percentage,
            "max_tokens": self.tracker.limits.max_tokens,
            "effective_limit": self.tracker.limits.effective_limit,
        }

    def get_cache_stats(self) -> dict[str, int] | None:
        """Get token counter cache statistics.

        Returns:
            Dictionary with hits, misses, size, hit_rate_percent,
            or None if counter doesn't support caching.
        """
        from .tokens import CachingCounter

        if isinstance(self.counter, CachingCounter):
            return self.counter.get_stats()
        return None

    def clear_cache(self) -> bool:
        """Clear the token counter cache.

        Returns:
            True if cache was cleared, False if counter doesn't support caching.
        """
        from .tokens import CachingCounter

        if isinstance(self.counter, CachingCounter):
            self.counter.clear_cache()
            return True
        return False
