"""RAG integration with Code-Forge components.

This module provides integration between RAG and other Code-Forge
components, particularly the ContextManager.

Example:
    from code_forge.rag.integration import RAGContextAugmenter

    augmenter = RAGContextAugmenter(
        rag_manager=rag_manager,
        context_manager=context_manager,
    )

    # Augment context for a user query
    tokens_added = await augmenter.augment_for_query("how does auth work?")
    print(f"Added {tokens_added} tokens of context")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from code_forge.context.manager import ContextManager

    from .manager import RAGManager

logger = logging.getLogger(__name__)


class RAGContextAugmenter:
    """Augments LLM context with RAG results.

    Integrates RAG search results into the conversation context,
    providing relevant project information to the LLM.

    Attributes:
        rag_manager: RAG manager for searching.
        context_manager: Context manager for adding messages.
        auto_augment: Whether to automatically augment on queries.
    """

    def __init__(
        self,
        rag_manager: RAGManager,
        context_manager: ContextManager | None = None,
        auto_augment: bool = True,
    ) -> None:
        """Initialize the augmenter.

        Args:
            rag_manager: RAG manager for searching.
            context_manager: Context manager for adding messages.
            auto_augment: Whether to automatically augment on queries.
        """
        self.rag_manager = rag_manager
        self.context_manager = context_manager
        self.auto_augment = auto_augment
        self._last_query: str | None = None
        self._last_tokens_added: int = 0

    @property
    def is_enabled(self) -> bool:
        """Check if augmentation is enabled.

        Returns:
            True if RAG is enabled and auto_augment is True.
        """
        return self.rag_manager.is_enabled and self.auto_augment

    async def augment_for_query(
        self,
        query: str,
        add_to_context: bool = True,
    ) -> int:
        """Augment context for a user query.

        Searches for relevant content and optionally adds it
        to the context manager.

        Args:
            query: User query or message.
            add_to_context: Whether to add results to context manager.

        Returns:
            Number of tokens added to context.
        """
        if not self.rag_manager.is_enabled:
            return 0

        try:
            # Get augmented context
            augmented_text = await self.rag_manager.augment_context(query)

            if not augmented_text:
                logger.debug(f"No RAG results for query: {query[:50]}...")
                return 0

            # Count tokens
            token_count = self._count_tokens(augmented_text)

            # Add to context if requested
            if add_to_context and self.context_manager is not None:
                self._add_to_context(augmented_text)

            self._last_query = query
            self._last_tokens_added = token_count

            logger.debug(
                f"Augmented context with {token_count} tokens for: {query[:50]}..."
            )
            return token_count

        except Exception as e:
            logger.warning(f"Failed to augment context: {e}")
            return 0

    async def get_context_for_query(self, query: str) -> str:
        """Get relevant context for a query without adding to context.

        Args:
            query: User query or message.

        Returns:
            Formatted context string.
        """
        if not self.rag_manager.is_enabled:
            return ""

        try:
            return await self.rag_manager.augment_context(query)
        except Exception as e:
            logger.warning(f"Failed to get context: {e}")
            return ""

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Uses context manager's counter if available, otherwise estimates.

        Args:
            text: Text to count tokens for.

        Returns:
            Token count.
        """
        if self.context_manager is not None:
            try:
                return self.context_manager.counter.count(text)
            except Exception:
                pass

        # Rough estimate: ~4 characters per token
        return len(text) // 4

    def _add_to_context(self, augmented_text: str) -> None:
        """Add augmented text to context manager.

        Args:
            augmented_text: Formatted RAG results.
        """
        if self.context_manager is None:
            return

        try:
            # Add as a system message with RAG marker
            self.context_manager.add_message({
                "role": "system",
                "content": f"[RAG Context]\n{augmented_text}",
            })
        except Exception as e:
            logger.warning(f"Failed to add RAG context to manager: {e}")

    def get_last_augmentation_stats(self) -> dict[str, Any]:
        """Get statistics about the last augmentation.

        Returns:
            Dictionary with last_query and tokens_added.
        """
        return {
            "last_query": self._last_query,
            "tokens_added": self._last_tokens_added,
        }

    def set_context_manager(self, context_manager: ContextManager) -> None:
        """Set the context manager.

        Args:
            context_manager: Context manager to use.
        """
        self.context_manager = context_manager


class RAGMessageProcessor:
    """Processes messages to determine if RAG augmentation is needed.

    Analyzes user messages to determine if they would benefit
    from RAG context augmentation.

    Attributes:
        rag_manager: RAG manager for checking status.
        min_query_length: Minimum query length to trigger RAG.
        skip_patterns: Patterns that indicate RAG should be skipped.
    """

    def __init__(
        self,
        rag_manager: RAGManager,
        min_query_length: int = 10,
    ) -> None:
        """Initialize the processor.

        Args:
            rag_manager: RAG manager.
            min_query_length: Minimum query length to trigger RAG.
        """
        self.rag_manager = rag_manager
        self.min_query_length = min_query_length

        # Patterns that indicate RAG should be skipped
        self.skip_patterns = [
            # Greetings
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            # Simple acknowledgments
            "yes",
            "no",
            "ok",
            "okay",
            "thanks",
            "thank you",
            # Commands (start with /)
        ]

    def should_augment(self, message: str) -> bool:
        """Check if a message should trigger RAG augmentation.

        Args:
            message: User message.

        Returns:
            True if RAG augmentation should be performed.
        """
        if not self.rag_manager.is_enabled:
            return False

        # Check if message is too short
        if len(message.strip()) < self.min_query_length:
            return False

        # Check if message is a command
        if message.strip().startswith("/"):
            return False

        # Check against skip patterns
        message_lower = message.lower().strip()
        for pattern in self.skip_patterns:
            if message_lower == pattern or message_lower.startswith(f"{pattern} "):
                return False

        return True

    def extract_query(self, message: str) -> str:
        """Extract the search query from a message.

        Args:
            message: User message.

        Returns:
            Extracted query for RAG search.
        """
        # For now, use the full message as the query
        # Future: Could extract key phrases or questions
        return message.strip()


def create_augmenter(
    rag_manager: RAGManager,
    context_manager: ContextManager | None = None,
) -> RAGContextAugmenter:
    """Create a RAG context augmenter.

    Factory function for creating augmenters with proper configuration.

    Args:
        rag_manager: RAG manager.
        context_manager: Optional context manager.

    Returns:
        Configured RAGContextAugmenter.
    """
    return RAGContextAugmenter(
        rag_manager=rag_manager,
        context_manager=context_manager,
        auto_augment=rag_manager.config.auto_index,
    )
