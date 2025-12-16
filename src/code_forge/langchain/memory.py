"""Conversation memory management for agents."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.messages import BaseMessage

from code_forge.langchain.messages import (
    langchain_to_forge,
    forge_messages_to_langchain,
)

if TYPE_CHECKING:
    from code_forge.llm.models import Message


@dataclass
class ConversationMemory:
    """
    Manages conversation history for agent interactions.

    Supports message windowing, token-based truncation, and
    conversion between Code-Forge and LangChain message formats.

    Example:
        ```python
        memory = ConversationMemory(max_messages=100)

        memory.set_system_message(Message.system("You are helpful."))
        memory.add_message(Message.user("Hello!"))
        memory.add_message(Message.assistant("Hi there!"))

        messages = memory.get_messages()  # Returns all messages
        lc_messages = memory.to_langchain_messages()  # For LangChain
        ```
    """

    messages: list[Message] = field(default_factory=list)
    system_message: Message | None = None
    max_messages: int | None = None
    max_tokens: int | None = None
    _token_counter: Callable[[Message], int] | None = None

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation history.

        Args:
            message: Message to add

        If max_messages is set and exceeded, oldest messages
        (excluding system) are removed.
        """
        from code_forge.llm.models import MessageRole

        # Don't add system messages to history, use set_system_message
        if message.role == MessageRole.SYSTEM:
            self.system_message = message
            return

        self.messages.append(message)

        # Enforce max messages
        if self.max_messages and len(self.messages) > self.max_messages:
            self._trim_to_count(self.max_messages)

    def add_messages(self, messages: list[Message]) -> None:
        """
        Add multiple messages to the conversation history.

        Args:
            messages: List of messages to add
        """
        for message in messages:
            self.add_message(message)

    def add_langchain_message(self, message: BaseMessage) -> None:
        """
        Add a LangChain message (will be converted).

        Args:
            message: LangChain message to add
        """
        forge_msg = langchain_to_forge(message)
        self.add_message(forge_msg)

    def get_messages(self) -> list[Message]:
        """
        Get all messages including system message.

        Returns:
            List of messages with system message first (if set)
        """
        result: list[Message] = []
        if self.system_message:
            result.append(self.system_message)
        result.extend(self.messages)
        return result

    def get_history(self) -> list[Message]:
        """
        Get only conversation history (no system message).

        Returns:
            List of conversation messages
        """
        return list(self.messages)

    def set_system_message(self, message: Message) -> None:
        """
        Set or update the system message.

        Args:
            message: System message to set
        """
        from code_forge.llm.models import Message as Msg
        from code_forge.llm.models import MessageRole

        if message.role != MessageRole.SYSTEM:
            # Extract string content
            content = message.content
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            message = Msg.system(content or "")

        self.system_message = message

    def clear(self) -> None:
        """Clear all messages (including system message)."""
        self.messages = []
        self.system_message = None

    def clear_history(self) -> None:
        """Clear conversation history but keep system message."""
        self.messages = []

    def _trim_to_count(self, max_count: int) -> None:
        """
        Trim messages to a maximum count.

        Removes oldest messages first, keeping the most recent.

        Args:
            max_count: Maximum number of messages to keep
        """
        if len(self.messages) > max_count:
            self.messages = self.messages[-max_count:]

    def trim(self, max_tokens: int) -> None:
        """
        Trim messages to fit within a token budget.

        Removes oldest messages first until under budget.
        System message is never removed.

        Args:
            max_tokens: Maximum total tokens allowed
        """
        if not self._token_counter:
            # Without token counter, fall back to character estimate
            # Rough estimate: 4 characters per token
            def estimate_tokens(msg: Message) -> int:
                content = msg.content or ""
                return len(content) // 4

            self._token_counter = estimate_tokens

        # Count system message tokens
        system_tokens = 0
        if self.system_message:
            system_tokens = self._token_counter(self.system_message)

        available = max_tokens - system_tokens

        # Calculate total tokens once (O(n)), then update incrementally
        total = sum(self._token_counter(m) for m in self.messages)

        # Trim from front until under budget (O(n) total)
        while self.messages and total > available:
            removed = self.messages.pop(0)
            total -= self._token_counter(removed)

    def to_langchain_messages(self) -> list[BaseMessage]:
        """
        Convert all messages to LangChain format.

        Returns:
            List of LangChain BaseMessage instances
        """
        return forge_messages_to_langchain(self.get_messages())

    def from_langchain_messages(self, messages: list[BaseMessage]) -> None:
        """
        Replace history with LangChain messages.

        Args:
            messages: LangChain messages to set
        """
        from code_forge.llm.models import MessageRole

        self.messages = []
        self.system_message = None

        for msg in messages:
            forge_msg = langchain_to_forge(msg)
            if forge_msg.role == MessageRole.SYSTEM:
                self.system_message = forge_msg
            else:
                self.messages.append(forge_msg)

    def __len__(self) -> int:
        """Return number of messages (excluding system)."""
        return len(self.messages)

    def __iter__(self) -> Any:
        """Iterate over all messages."""
        return iter(self.get_messages())


@dataclass
class SlidingWindowMemory(ConversationMemory):
    """
    Memory with sliding window over recent messages.

    Keeps only the most recent N message pairs (user + assistant).
    Useful for long conversations where only recent context matters.
    """

    window_size: int = 10  # Number of exchange pairs to keep

    def add_message(self, message: Message) -> None:
        """Add message and enforce sliding window."""
        super().add_message(message)
        self._enforce_window()

    def _enforce_window(self) -> None:
        """Ensure only window_size pairs (2 * window_size messages) are kept."""
        max_messages = self.window_size * 2

        # Simply keep the most recent messages
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]


@dataclass
class SummaryMemory(ConversationMemory):
    """
    Memory that summarizes old messages to save tokens.

    When messages exceed a threshold, older messages are
    summarized into a single message, preserving context
    while reducing token usage.

    Attributes:
        summary_threshold: Trigger summarization when messages exceed this count
        recent_messages_to_keep: Number of recent messages to preserve (not summarized)
        summary: Current summary of older messages
        summarizer: LLM to use for generating summaries
    """

    summary_threshold: int = 20  # Messages before summarizing
    recent_messages_to_keep: int = 10  # Keep this many recent messages unsummarized
    summary: str | None = None
    summarizer: Any = None  # LLM to use for summarization

    def get_messages(self) -> list[Message]:
        """Get messages with summary prepended if available."""
        from code_forge.llm.models import Message

        result: list[Message] = []

        # Add system message
        if self.system_message:
            result.append(self.system_message)

        # Add summary as a system note if available
        if self.summary:
            result.append(
                Message.system(f"[Previous conversation summary: {self.summary}]")
            )

        # Add recent messages
        result.extend(self.messages)

        return result

    async def maybe_summarize(self) -> None:
        """
        Summarize if messages exceed threshold.

        Requires a summarizer LLM to be set.
        """
        if not self.summarizer or len(self.messages) <= self.summary_threshold:
            return

        # Keep most recent messages, summarize older ones
        keep_count = self.recent_messages_to_keep
        to_summarize = self.messages[:-keep_count] if keep_count > 0 else self.messages
        to_keep = self.messages[-keep_count:] if keep_count > 0 else []

        if to_summarize:
            # Generate summary
            summary_prompt = (
                "Summarize this conversation in 2-3 sentences, "
                "capturing key points and context:\n\n"
            )
            for msg in to_summarize:
                summary_prompt += f"{msg.role.value}: {msg.content}\n"

            from langchain_core.messages import HumanMessage

            response = await self.summarizer.ainvoke(
                [HumanMessage(content=summary_prompt)]
            )

            # Update state
            if self.summary:
                self.summary = f"{self.summary}\n{response.content}"
            else:
                self.summary = response.content

            self.messages = to_keep
