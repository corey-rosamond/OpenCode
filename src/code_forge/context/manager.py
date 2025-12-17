"""Central context management."""

import logging
from enum import Enum
from typing import Any

from .compaction import ContextCompactor, LLMProtocol, ToolResultCompactor
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
    ) -> None:
        """Initialize context manager.

        Args:
            model: Model name for limits and counting.
            mode: Truncation mode to use.
            llm: LLM client for summarization (optional).
            auto_truncate: Automatically truncate on overflow.
        """
        self.model = model
        self.mode = mode
        self.auto_truncate = auto_truncate

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

    def _truncate(self) -> None:
        """Truncate messages to fit within limit.

        Validates that truncated result fits within budget.
        Logs warning if truncation was insufficient.
        """
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

        target_tokens = int(self.tracker.budget.conversation_budget * 0.7)

        compacted = await self.compactor.compact(
            self._messages,
            target_tokens,
            self.counter,
        )

        if len(compacted) < len(self._messages):
            self._messages = compacted
            self.tracker.update(compacted)
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
        """Clear all messages."""
        self._messages = []
        self.tracker.reset()

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
