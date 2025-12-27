"""Context truncation strategies."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from .tokens import TokenCounter

logger = logging.getLogger(__name__)


class TruncationStrategy(ABC):
    """Abstract base for truncation strategies.

    Truncation strategies reduce message history to fit
    within token limits while preserving important context.
    """

    @abstractmethod
    def truncate(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        counter: TokenCounter,
    ) -> list[dict[str, Any]]:
        """Truncate messages to fit target tokens.

        Args:
            messages: Messages to truncate.
            target_tokens: Target token count.
            counter: Token counter to use.

        Returns:
            Truncated message list.
        """
        ...

    def _count_messages(
        self,
        messages: list[dict[str, Any]],
        counter: TokenCounter,
    ) -> int:
        """Count tokens in messages."""
        return counter.count_messages(messages)


class SlidingWindowStrategy(TruncationStrategy):
    """Keep most recent messages within window.

    Simple strategy that keeps the N most recent messages.
    System prompt is always preserved.
    """

    def __init__(
        self,
        window_size: int = 20,
        preserve_system: bool = True,
    ) -> None:
        """Initialize sliding window strategy.

        Args:
            window_size: Maximum messages to keep.
            preserve_system: Whether to preserve system messages.
        """
        self.window_size = window_size
        self.preserve_system = preserve_system

    def truncate(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,  # noqa: ARG002
        counter: TokenCounter,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Truncate using sliding window.

        Args:
            messages: Messages to truncate.
            target_tokens: Target token count (ignored for window).
            counter: Token counter.

        Returns:
            Truncated messages.
        """
        if not messages:
            return []

        # Separate system messages
        system_messages: list[dict[str, Any]] = []
        other_messages: list[dict[str, Any]] = []

        for msg in messages:
            if self.preserve_system and msg.get("role") == "system":
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # Keep window of recent messages
        if len(other_messages) > self.window_size:
            other_messages = other_messages[-self.window_size :]

        # Combine
        result = system_messages + other_messages

        logger.debug(f"Sliding window: {len(messages)} -> {len(result)} messages")

        return result


class TokenBudgetStrategy(TruncationStrategy):
    """Truncate to fit within token budget.

    Removes oldest messages (except system) until within budget.
    """

    def __init__(self, preserve_system: bool = True) -> None:
        """Initialize token budget strategy.

        Args:
            preserve_system: Whether to preserve system messages.
        """
        self.preserve_system = preserve_system

    def truncate(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        counter: TokenCounter,
    ) -> list[dict[str, Any]]:
        """Truncate to fit token budget.

        Args:
            messages: Messages to truncate.
            target_tokens: Maximum tokens allowed.
            counter: Token counter.

        Returns:
            Truncated messages.
        """
        if not messages:
            return []

        current_tokens = self._count_messages(messages, counter)

        if current_tokens <= target_tokens:
            return messages

        # Separate system messages
        system_messages: list[dict[str, Any]] = []
        other_messages: list[dict[str, Any]] = []

        for msg in messages:
            if self.preserve_system and msg.get("role") == "system":
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # Calculate tokens needed for system messages
        system_tokens = self._count_messages(system_messages, counter)
        available_tokens = target_tokens - system_tokens

        if available_tokens <= 0:
            logger.warning("System messages exceed budget")
            return system_messages

        # Remove oldest messages until within budget
        # Track token count incrementally (O(n) total) instead of recounting (O(n^2))
        result = list(other_messages)
        result_tokens = self._count_messages(result, counter)

        while result and result_tokens > available_tokens:
            # Remove oldest (first) message and subtract its tokens
            removed = result.pop(0)
            removed_tokens = counter.count_messages([removed])
            result_tokens -= removed_tokens
            logger.debug(f"Removed message: {removed.get('role')}")

        final = system_messages + result

        logger.debug(
            f"Token budget: {len(messages)} -> {len(final)} messages, "
            f"{current_tokens} -> {self._count_messages(final, counter)} tokens"
        )

        return final


class SmartTruncationStrategy(TruncationStrategy):
    """Preserve first and last messages, remove middle.

    Keeps important context at conversation start and
    recent context at the end.
    """

    def __init__(
        self,
        preserve_first: int = 2,
        preserve_last: int = 10,
        preserve_system: bool = True,
    ) -> None:
        """Initialize smart truncation strategy.

        Args:
            preserve_first: First N messages to keep.
            preserve_last: Last N messages to keep.
            preserve_system: Whether to preserve system messages.
        """
        self.preserve_first = preserve_first
        self.preserve_last = preserve_last
        self.preserve_system = preserve_system

    def truncate(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        counter: TokenCounter,
    ) -> list[dict[str, Any]]:
        """Truncate keeping ends, removing middle.

        Args:
            messages: Messages to truncate.
            target_tokens: Maximum tokens allowed.
            counter: Token counter.

        Returns:
            Truncated messages.
        """
        if not messages:
            return []

        # Separate system messages
        system_messages: list[dict[str, Any]] = []
        other_messages: list[dict[str, Any]] = []

        for msg in messages:
            if self.preserve_system and msg.get("role") == "system":
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # If small enough, keep all
        total_preserve = self.preserve_first + self.preserve_last
        if len(other_messages) <= total_preserve:
            return system_messages + other_messages

        # Keep first and last
        first_msgs = other_messages[: self.preserve_first]
        last_msgs = other_messages[-self.preserve_last :]

        # Calculate omitted count
        omitted_count = len(other_messages) - total_preserve

        # Add truncation marker
        truncation_marker: dict[str, Any] = {
            "role": "system",
            "content": f"[{omitted_count} messages omitted]",
        }

        result = system_messages + first_msgs + [truncation_marker] + last_msgs

        # Check if within budget, if not, reduce last messages
        while (
            self._count_messages(result, counter) > target_tokens and len(last_msgs) > 1
        ):
            last_msgs.pop(0)
            result = system_messages + first_msgs + [truncation_marker] + last_msgs

        logger.debug(f"Smart truncation: {len(messages)} -> {len(result)} messages")

        return result


class SelectiveTruncationStrategy(TruncationStrategy):
    """Selectively preserve messages by criteria.

    Allows preserving messages marked as important or
    filtering by role.
    """

    def __init__(
        self,
        preserve_roles: set[str] | None = None,
        preserve_marked: bool = True,
        mark_key: str = "_preserve",
    ) -> None:
        """Initialize selective strategy.

        Args:
            preserve_roles: Roles to always preserve.
            preserve_marked: Preserve messages with mark_key.
            mark_key: Key in message metadata for preservation.
        """
        self.preserve_roles = preserve_roles or {"system"}
        self.preserve_marked = preserve_marked
        self.mark_key = mark_key

    def truncate(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        counter: TokenCounter,
    ) -> list[dict[str, Any]]:
        """Truncate selectively.

        Args:
            messages: Messages to truncate.
            target_tokens: Maximum tokens.
            counter: Token counter.

        Returns:
            Truncated messages.
        """
        if not messages:
            return []

        # Separate preserved and removable, tracking original indices
        # Using indices instead of id() to avoid GC/copy issues
        preserved: list[tuple[int, dict[str, Any]]] = []
        removable: list[tuple[int, dict[str, Any]]] = []

        for idx, msg in enumerate(messages):
            role = msg.get("role", "")
            marked = msg.get(self.mark_key, False)

            if role in self.preserve_roles or (self.preserve_marked and marked):
                preserved.append((idx, msg))
            else:
                removable.append((idx, msg))

        # Check if preserved alone fits
        preserved_msgs = [msg for _, msg in preserved]
        preserved_tokens = self._count_messages(preserved_msgs, counter)
        if preserved_tokens >= target_tokens:
            logger.warning("Preserved messages exceed budget")
            return preserved_msgs

        # Add removable from end until budget
        available = target_tokens - preserved_tokens
        added: list[tuple[int, dict[str, Any]]] = []

        for idx, msg in reversed(removable):
            test_list = [msg] + [m for _, m in added]
            if self._count_messages(test_list, counter) <= available:
                added.insert(0, (idx, msg))
            else:
                break

        # Merge and sort by original index (stable ordering)
        result = preserved + added
        result.sort(key=lambda item: item[0])

        # Return just the messages
        return [msg for _, msg in result]


class CompositeStrategy(TruncationStrategy):
    """Chain multiple strategies.

    Applies strategies in order until within budget.
    """

    def __init__(self, strategies: list[TruncationStrategy]) -> None:
        """Initialize composite strategy.

        Args:
            strategies: Strategies to apply in order.
        """
        self.strategies = strategies

    def truncate(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        counter: TokenCounter,
    ) -> list[dict[str, Any]]:
        """Truncate using chained strategies.

        Args:
            messages: Messages to truncate.
            target_tokens: Maximum tokens.
            counter: Token counter.

        Returns:
            Truncated messages.
        """
        result = messages

        for strategy in self.strategies:
            result = strategy.truncate(result, target_tokens, counter)

            if self._count_messages(result, counter) <= target_tokens:
                break

        return result
