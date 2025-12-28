"""Token counting implementations."""

import logging
import re
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class TokenCounter(ABC):
    """Abstract base class for token counting.

    Provides interface for counting tokens in text and messages.
    Different implementations support different tokenizer backends.
    """

    @abstractmethod
    def count(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: The text to count tokens in.

        Returns:
            Number of tokens.
        """
        ...

    @abstractmethod
    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dictionaries with role/content.

        Returns:
            Total tokens across all messages.
        """
        ...

    def count_message(self, message: dict[str, Any]) -> int:
        """Count tokens in a single message.

        Args:
            message: Message dictionary.

        Returns:
            Number of tokens.
        """
        return self.count_messages([message])


class TiktokenCounter(TokenCounter):
    """Token counter using OpenAI's tiktoken library.

    Provides accurate token counting for OpenAI and Claude models.
    Falls back to approximate counting if tiktoken not available.
    """

    # Message overhead tokens (varies by model)
    MESSAGE_OVERHEAD = 4  # <im_start>, role, \n, <im_end>
    REPLY_OVERHEAD = 3  # <im_start>assistant<im_sep>

    def __init__(self, model: str | None = None) -> None:
        """Initialize tiktoken counter.

        Args:
            model: Model name for encoding selection.
        """
        self.model = model
        self._encoding: Any = None
        self._fallback = ApproximateCounter()
        self._tiktoken: Any = None

        # Try to load tiktoken
        try:
            import tiktoken

            self._tiktoken = tiktoken

            # Get encoding for model
            if model:
                try:
                    self._encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Unknown model, use default
                    self._encoding = tiktoken.get_encoding("cl100k_base")
            else:
                self._encoding = tiktoken.get_encoding("cl100k_base")

        except ImportError:
            logger.warning("tiktoken not available, using approximate counting")
            self._tiktoken = None

    def count(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count.

        Returns:
            Token count.
        """
        if not text:
            return 0

        if self._encoding:
            return len(self._encoding.encode(text))

        return self._fallback.count(text)

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in messages including overhead.

        Args:
            messages: List of message dictionaries.

        Returns:
            Total token count.
        """
        if not messages:
            return 0

        total = 0

        for message in messages:
            # Base overhead per message
            total += self.MESSAGE_OVERHEAD

            # Role token
            role = message.get("role", "")
            total += self.count(role)

            # Content tokens
            content = message.get("content", "")
            if content:
                total += self.count(content)

            # Name tokens (if present)
            name = message.get("name")
            if name:
                total += self.count(name) + 1  # +1 for separator

            # Tool calls (if present)
            tool_calls = message.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    # Tool call structure overhead
                    total += 10

                    # Function name
                    func = tc.get("function", {})
                    total += self.count(func.get("name", ""))

                    # Arguments
                    args = func.get("arguments", "")
                    total += self.count(args)

            # Tool call ID (for tool results)
            tool_call_id = message.get("tool_call_id")
            if tool_call_id:
                total += self.count(tool_call_id)

        # Reply priming overhead
        total += self.REPLY_OVERHEAD

        return total


class ApproximateCounter(TokenCounter):
    """Approximate token counter for models without tiktoken.

    Uses a simple word-based approximation with configurable
    tokens-per-word ratio.
    """

    def __init__(
        self,
        tokens_per_word: float = 1.3,
        tokens_per_char: float = 0.25,
    ) -> None:
        """Initialize approximate counter.

        Args:
            tokens_per_word: Average tokens per word.
            tokens_per_char: Tokens per character for non-word text.
        """
        self.tokens_per_word = tokens_per_word
        self.tokens_per_char = tokens_per_char

        # Pattern for splitting into words
        self._word_pattern = re.compile(r"\w+")

    def count(self, text: str) -> int:
        """Count tokens approximately.

        Args:
            text: Text to count.

        Returns:
            Approximate token count.
        """
        if not text:
            return 0

        # Count words
        words = self._word_pattern.findall(text)
        word_tokens = int(len(words) * self.tokens_per_word)

        # Count non-word characters (punctuation, whitespace, etc.)
        non_word_chars = len(text) - sum(len(w) for w in words)
        char_tokens = int(non_word_chars * self.tokens_per_char)

        return word_tokens + char_tokens

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in messages approximately.

        Args:
            messages: List of message dictionaries.

        Returns:
            Approximate token count.
        """
        if not messages:
            return 0

        total = 0
        message_overhead = 4  # Per-message overhead

        for message in messages:
            total += message_overhead

            # Content
            content = message.get("content", "")
            if content:
                total += self.count(content)

            # Role
            total += self.count(message.get("role", ""))

            # Tool calls
            tool_calls = message.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    total += 10  # Structure overhead
                    func = tc.get("function", {})
                    total += self.count(func.get("name", ""))
                    total += self.count(func.get("arguments", ""))

        return total


class CachingCounter(TokenCounter):
    """Token counter with LRU caching for repeated text.

    Wraps another counter and caches results for efficiency.
    Uses OrderedDict for true LRU eviction.
    Thread-safe: uses RLock for all cache operations.
    """

    def __init__(
        self,
        counter: TokenCounter,
        max_cache_size: int = 1000,
    ) -> None:
        """Initialize caching counter.

        Args:
            counter: Underlying token counter.
            max_cache_size: Maximum cache entries (must be > 0).

        Raises:
            ValueError: If max_cache_size is not positive.
        """
        if max_cache_size <= 0:
            raise ValueError("max_cache_size must be positive")

        self._counter = counter
        self._cache: OrderedDict[str, int] = OrderedDict()
        self._max_size = max_cache_size
        self._lock = threading.RLock()  # Thread-safe cache access
        self._hits = 0
        self._misses = 0

    def count(self, text: str) -> int:
        """Count with LRU caching.

        Thread-safe: uses lock for cache access.

        Args:
            text: Text to count.

        Returns:
            Token count.
        """
        with self._lock:
            if text in self._cache:
                # Move to end (most recently used) for true LRU behavior
                self._cache.move_to_end(text)
                self._hits += 1
                return self._cache[text]

            self._misses += 1

        # Do the expensive count outside the lock
        count = self._counter.count(text)

        with self._lock:
            # Add to cache, evicting LRU (first) entry if needed
            if len(self._cache) >= self._max_size:
                # Remove least recently used (first) entry
                self._cache.popitem(last=False)

            self._cache[text] = count
        return count

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """Count messages using underlying counter.

        Args:
            messages: Messages to count.

        Returns:
            Token count.
        """
        return self._counter.count_messages(messages)

    def clear_cache(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, size, and hit_rate.
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "hit_rate_percent": int(hit_rate),
            }


# Model-to-encoding mapping
MODEL_ENCODINGS: dict[str, str] = {
    # Claude models use cl100k_base approximation
    "claude": "cl100k_base",
    "anthropic": "cl100k_base",
    # GPT models
    "gpt-4": "cl100k_base",
    "gpt-3.5": "cl100k_base",
    # Others default to approximate
}


def get_counter(model: str, cache_size: int = 1000) -> TokenCounter:
    """Get appropriate token counter for a model.

    Args:
        model: Model name or identifier.
        cache_size: Maximum cache entries for the caching counter.

    Returns:
        TokenCounter instance.
    """
    model_lower = model.lower()

    # Check for tiktoken-compatible models
    for prefix in MODEL_ENCODINGS:
        if prefix in model_lower:
            counter = TiktokenCounter(model)
            return CachingCounter(counter, max_cache_size=cache_size)

    # Fall back to approximate counter
    logger.debug(f"Using approximate counter for model: {model}")
    return CachingCounter(ApproximateCounter(), max_cache_size=cache_size)
