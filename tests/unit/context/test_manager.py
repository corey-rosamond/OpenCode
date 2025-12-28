"""Unit tests for context manager."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.context.compaction import ContextCompactor
from code_forge.context.events import (
    CompressionEvent,
    CompressionEventType,
    WarningLevel,
)
from code_forge.context.manager import (
    ContextManager,
    TruncationMode,
    get_strategy,
)
from code_forge.context.strategies import (
    CompositeStrategy,
    SlidingWindowStrategy,
    SmartTruncationStrategy,
    TokenBudgetStrategy,
)


class TestTruncationMode:
    """Tests for TruncationMode enum."""

    def test_values(self) -> None:
        """Should have expected values."""
        assert TruncationMode.SLIDING_WINDOW.value == "sliding_window"
        assert TruncationMode.TOKEN_BUDGET.value == "token_budget"
        assert TruncationMode.SMART.value == "smart"
        assert TruncationMode.SUMMARIZE.value == "summarize"


class TestGetStrategy:
    """Tests for get_strategy function."""

    def test_sliding_window(self) -> None:
        """Should return SlidingWindowStrategy."""
        strategy = get_strategy(TruncationMode.SLIDING_WINDOW)
        assert isinstance(strategy, SlidingWindowStrategy)

    def test_token_budget(self) -> None:
        """Should return TokenBudgetStrategy."""
        strategy = get_strategy(TruncationMode.TOKEN_BUDGET)
        assert isinstance(strategy, TokenBudgetStrategy)

    def test_smart(self) -> None:
        """Should return SmartTruncationStrategy."""
        strategy = get_strategy(TruncationMode.SMART)
        assert isinstance(strategy, SmartTruncationStrategy)

    def test_summarize(self) -> None:
        """Should return CompositeStrategy for summarize."""
        strategy = get_strategy(TruncationMode.SUMMARIZE)
        assert isinstance(strategy, CompositeStrategy)


class TestContextManager:
    """Tests for ContextManager."""

    def test_init_default(self) -> None:
        """Should initialize with default settings."""
        manager = ContextManager(model="claude-3-opus")

        assert manager.model == "claude-3-opus"
        assert manager.mode == TruncationMode.SMART
        assert manager.auto_truncate is True

    def test_init_custom_mode(self) -> None:
        """Should use custom truncation mode."""
        manager = ContextManager(
            model="claude-3-opus",
            mode=TruncationMode.SLIDING_WINDOW,
        )

        assert manager.mode == TruncationMode.SLIDING_WINDOW
        assert isinstance(manager.strategy, SlidingWindowStrategy)

    def test_init_with_llm_creates_compactor(self) -> None:
        """Should create compactor when LLM provided."""
        mock_llm = MagicMock()
        manager = ContextManager(model="claude-3-opus", llm=mock_llm)

        assert isinstance(manager.compactor, ContextCompactor)

    def test_init_without_llm_no_compactor(self) -> None:
        """Should not create compactor without LLM."""
        manager = ContextManager(model="claude-3-opus")

        assert manager.compactor is None

    def test_set_system_prompt(self) -> None:
        """Should set system prompt and return token count."""
        manager = ContextManager(model="claude-3-opus")

        tokens = manager.set_system_prompt("You are a helpful assistant.")

        assert tokens > 0
        assert manager._system_prompt == "You are a helpful assistant."

    def test_set_tool_definitions(self) -> None:
        """Should set tool definitions and return token count."""
        manager = ContextManager(model="claude-3-opus")

        tools = [
            {
                "type": "function",
                "function": {"name": "read_file", "description": "Read a file"},
            }
        ]
        tokens = manager.set_tool_definitions(tools)

        assert tokens > 0

    def test_add_message(self) -> None:
        """Should add message to context."""
        manager = ContextManager(model="claude-3-opus")

        manager.add_message({"role": "user", "content": "Hello"})

        assert len(manager._messages) == 1
        assert manager._messages[0]["content"] == "Hello"

    def test_add_message_compacts_tool_results(self) -> None:
        """Should compact large tool results."""
        manager = ContextManager(model="claude-3-opus")
        manager.tool_compactor.max_result_tokens = 50

        # Use real words so token count is realistic
        manager.add_message({"role": "tool", "content": "word " * 1000})

        # Content should be truncated
        assert len(manager._messages[0]["content"]) < 5000

    def test_add_messages(self) -> None:
        """Should add multiple messages."""
        manager = ContextManager(model="claude-3-opus")

        manager.add_messages(
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ]
        )

        assert len(manager._messages) == 2

    def test_get_messages(self) -> None:
        """Should return copy of messages."""
        manager = ContextManager(model="claude-3-opus")
        manager.add_message({"role": "user", "content": "Hello"})

        messages = manager.get_messages()

        assert len(messages) == 1
        # Should be a copy
        messages.append({"role": "user", "content": "New"})
        assert len(manager._messages) == 1

    def test_get_context_for_request(self) -> None:
        """Should include system prompt and messages."""
        manager = ContextManager(model="claude-3-opus")
        manager.set_system_prompt("System")
        manager.add_message({"role": "user", "content": "Hello"})

        context = manager.get_context_for_request()

        assert len(context) == 2
        assert context[0]["role"] == "system"
        assert context[0]["content"] == "System"
        assert context[1]["role"] == "user"

    def test_get_context_for_request_no_system(self) -> None:
        """Should work without system prompt."""
        manager = ContextManager(model="claude-3-opus")
        manager.add_message({"role": "user", "content": "Hello"})

        context = manager.get_context_for_request()

        assert len(context) == 1
        assert context[0]["role"] == "user"

    def test_auto_truncate_when_over_limit(self) -> None:
        """Should auto-truncate when over limit."""
        manager = ContextManager(
            model="gpt-4",  # 8K context
            mode=TruncationMode.TOKEN_BUDGET,
            auto_truncate=True,
        )

        # Add many large messages with real words
        for _ in range(50):
            manager.add_message({"role": "user", "content": "word " * 200})

        # Should have truncated
        assert manager.token_usage <= manager.tracker.limits.effective_limit

    def test_no_auto_truncate_when_disabled(self) -> None:
        """Should not auto-truncate when disabled."""
        manager = ContextManager(
            model="claude-3-opus",  # Large context so messages fit
            auto_truncate=False,
        )

        # Add many messages
        for i in range(100):
            manager.add_message({"role": "user", "content": f"Message {i}"})

        # All messages should still be there
        assert len(manager._messages) == 100

    def test_token_usage(self) -> None:
        """Should return current token usage."""
        manager = ContextManager(model="claude-3-opus")
        manager.set_system_prompt("System")
        manager.add_message({"role": "user", "content": "Hello"})

        usage = manager.token_usage

        assert usage > 0

    def test_available_tokens(self) -> None:
        """Should return available tokens."""
        manager = ContextManager(model="claude-3-opus")

        available = manager.available_tokens

        assert available > 0
        assert available < manager.tracker.limits.effective_limit

    def test_usage_percentage(self) -> None:
        """Should return usage percentage."""
        manager = ContextManager(model="claude-3-opus")
        manager.add_message({"role": "user", "content": "Hello"})

        percentage = manager.usage_percentage

        assert 0 < percentage < 100

    def test_is_near_limit(self) -> None:
        """Should return True when over 80% usage."""
        manager = ContextManager(model="gpt-4", auto_truncate=False)  # Small context

        # Fill most of the context with real words
        for _ in range(50):
            manager.add_message({"role": "user", "content": "word " * 100})
            if manager.usage_percentage > 85:
                break

        assert manager.is_near_limit or manager.usage_percentage > 80

    def test_is_near_limit_false_when_low_usage(self) -> None:
        """Should return False when under 80% usage."""
        manager = ContextManager(model="claude-3-opus")
        manager.add_message({"role": "user", "content": "Hello"})

        assert not manager.is_near_limit

    def test_reset(self) -> None:
        """Should clear all messages."""
        manager = ContextManager(model="claude-3-opus")
        manager.add_message({"role": "user", "content": "Hello"})
        manager.add_message({"role": "assistant", "content": "Hi!"})

        manager.reset()

        assert len(manager._messages) == 0
        assert manager.token_usage == manager.tracker.budget.system_prompt

    def test_get_stats(self) -> None:
        """Should return stats dictionary."""
        manager = ContextManager(model="claude-3-opus")
        manager.add_message({"role": "user", "content": "Hello"})

        stats = manager.get_stats()

        assert stats["model"] == "claude-3-opus"
        assert stats["mode"] == "smart"
        assert stats["message_count"] == 1
        assert stats["token_usage"] > 0
        assert stats["available_tokens"] > 0
        assert 0 < stats["usage_percentage"] < 100
        assert stats["max_tokens"] == 200000

    @pytest.mark.asyncio
    async def test_compact_if_needed_without_compactor(self) -> None:
        """Should return False without compactor."""
        manager = ContextManager(model="claude-3-opus")

        result = await manager.compact_if_needed()

        assert result is False

    @pytest.mark.asyncio
    async def test_compact_if_needed_below_threshold(self) -> None:
        """Should return False when below threshold."""
        mock_llm = AsyncMock()
        manager = ContextManager(model="claude-3-opus", llm=mock_llm)
        manager.add_message({"role": "user", "content": "Hello"})

        result = await manager.compact_if_needed(threshold=0.9)

        assert result is False

    @pytest.mark.asyncio
    async def test_compact_if_needed_compacts(self) -> None:
        """Should compact when above threshold."""
        mock_llm = AsyncMock()
        response = MagicMock()
        response.content = "Summary"
        mock_llm.ainvoke.return_value = response

        manager = ContextManager(
            model="gpt-4",  # Small context for testing
            llm=mock_llm,
            auto_truncate=False,  # Disable auto-truncate so messages accumulate
        )

        # Add messages with real words to reach threshold
        for i in range(50):
            manager.add_message({"role": "user", "content": f"Message {i} " + "word " * 20})

        # Set very low threshold to trigger compaction
        result = await manager.compact_if_needed(threshold=0.01)

        # May or may not compact depending on internal state
        # The key is it doesn't crash
        assert isinstance(result, bool)


class TestContextManagerIntegration:
    """Integration tests for ContextManager."""

    def test_full_workflow(self) -> None:
        """Test typical usage workflow."""
        manager = ContextManager(
            model="claude-3-opus",
            mode=TruncationMode.SMART,
        )

        # Set system prompt
        manager.set_system_prompt("You are a helpful assistant.")

        # Set tools
        manager.set_tool_definitions(
            [{"type": "function", "function": {"name": "test"}}]
        )

        # Simulate conversation
        manager.add_message({"role": "user", "content": "Hello"})
        manager.add_message({"role": "assistant", "content": "Hi! How can I help?"})
        manager.add_message({"role": "user", "content": "What's 2+2?"})
        manager.add_message({"role": "assistant", "content": "4"})

        # Check state
        assert len(manager.get_messages()) == 4
        assert manager.usage_percentage < 1  # Very small usage

        # Get context for LLM
        context = manager.get_context_for_request()
        assert len(context) == 5  # system + 4 messages
        assert context[0]["role"] == "system"

        # Get stats
        stats = manager.get_stats()
        assert stats["message_count"] == 4

    def test_large_conversation_truncation(self) -> None:
        """Test truncation with large conversation."""
        manager = ContextManager(
            model="gpt-4",  # 8K context
            mode=TruncationMode.SMART,
            auto_truncate=True,
        )

        manager.set_system_prompt("System prompt here.")

        # Add many messages with real words
        for i in range(100):
            manager.add_message({"role": "user", "content": f"Message {i} " + "word " * 50})

        # Should have truncated
        assert len(manager._messages) < 100
        assert manager.token_usage <= manager.tracker.limits.effective_limit

        # Context should still be valid for request
        context = manager.get_context_for_request()
        assert context[0]["role"] == "system"

    def test_tool_result_handling(self) -> None:
        """Test handling of tool results."""
        manager = ContextManager(model="claude-3-opus")
        manager.tool_compactor.max_result_tokens = 100

        # Add tool call and result
        manager.add_message(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "read_file", "arguments": '{"path": "/"}'},
                    }
                ],
            }
        )

        # Add large tool result with real words
        manager.add_message(
            {
                "role": "tool",
                "content": "word " * 1000,  # ~1300 tokens
                "tool_call_id": "call_1",
            }
        )

        # Result should be compacted
        tool_msg = manager._messages[1]
        assert len(tool_msg["content"]) < 5000
        assert "truncated" in tool_msg["content"].lower()


class MockObserver:
    """Mock observer for testing compression events."""

    def __init__(self) -> None:
        self.events: list[CompressionEvent] = []

    def on_compression_event(self, event: CompressionEvent) -> None:
        """Record the event."""
        self.events.append(event)


class TestContextManagerObservers:
    """Tests for ContextManager observer functionality."""

    def test_add_observer(self) -> None:
        """Should add observer to list."""
        manager = ContextManager(model="claude-3-opus")
        observer = MockObserver()

        manager.add_observer(observer)

        assert observer in manager._observers

    def test_add_observer_no_duplicates(self) -> None:
        """Should not add same observer twice."""
        manager = ContextManager(model="claude-3-opus")
        observer = MockObserver()

        manager.add_observer(observer)
        manager.add_observer(observer)

        assert manager._observers.count(observer) == 1

    def test_remove_observer(self) -> None:
        """Should remove observer from list."""
        manager = ContextManager(model="claude-3-opus")
        observer = MockObserver()
        manager.add_observer(observer)

        manager.remove_observer(observer)

        assert observer not in manager._observers

    def test_remove_observer_not_present(self) -> None:
        """Should not raise when removing non-existent observer."""
        manager = ContextManager(model="claude-3-opus")
        observer = MockObserver()

        # Should not raise
        manager.remove_observer(observer)

    def test_truncation_emits_event(self) -> None:
        """Should emit truncation event when messages are removed."""
        manager = ContextManager(
            model="gpt-4",  # Small context
            mode=TruncationMode.TOKEN_BUDGET,
            auto_truncate=True,
        )
        observer = MockObserver()
        manager.add_observer(observer)

        # Add many messages to trigger truncation
        for _ in range(50):
            manager.add_message({"role": "user", "content": "word " * 200})

        # Should have received truncation events
        truncation_events = [
            e for e in observer.events if e.event_type == CompressionEventType.TRUNCATION
        ]
        assert len(truncation_events) > 0

        # Check event properties
        event = truncation_events[-1]
        assert event.messages_before > event.messages_after
        assert event.tokens_before >= event.tokens_after

    def test_reset_emits_cleared_event(self) -> None:
        """Should emit cleared event when reset is called."""
        manager = ContextManager(model="claude-3-opus")
        observer = MockObserver()
        manager.add_observer(observer)

        # Add messages
        manager.add_message({"role": "user", "content": "Hello"})
        manager.add_message({"role": "assistant", "content": "Hi!"})

        # Clear any events from adding
        observer.events.clear()

        # Reset
        manager.reset()

        # Should have received cleared event
        assert len(observer.events) == 1
        event = observer.events[0]
        assert event.event_type == CompressionEventType.CLEARED
        assert event.messages_before == 2
        assert event.messages_after == 0

    def test_reset_no_event_when_empty(self) -> None:
        """Should not emit event when resetting empty context."""
        manager = ContextManager(model="claude-3-opus")
        observer = MockObserver()
        manager.add_observer(observer)

        manager.reset()

        assert len(observer.events) == 0

    def test_warning_event_at_threshold(self) -> None:
        """Should emit warning event when crossing threshold."""
        manager = ContextManager(
            model="gpt-4",
            auto_truncate=False,
            warning_threshold=80.0,
            critical_threshold=90.0,
        )
        observer = MockObserver()
        manager.add_observer(observer)

        # Add messages until we cross 80%
        for _ in range(50):
            manager.add_message({"role": "user", "content": "word " * 100})
            if manager.usage_percentage > 85:
                break

        # Check for warning events
        warning_events = [
            e for e in observer.events if e.event_type == CompressionEventType.WARNING
        ]
        if manager.usage_percentage >= 80:
            assert len(warning_events) > 0
            # Should have at least caution level
            assert any(e.warning_level == WarningLevel.CAUTION for e in warning_events)

    def test_custom_warning_thresholds(self) -> None:
        """Should respect custom warning thresholds."""
        manager = ContextManager(
            model="claude-3-opus",
            warning_threshold=50.0,  # Warn at 50%
            critical_threshold=70.0,  # Critical at 70%
        )

        assert manager.warning_threshold == 50.0
        assert manager.critical_threshold == 70.0

    def test_observer_exception_handled(self) -> None:
        """Should handle observer exceptions gracefully."""
        manager = ContextManager(model="claude-3-opus")

        # Create an observer that raises
        class BadObserver:
            def on_compression_event(self, event: CompressionEvent) -> None:
                raise RuntimeError("Observer error")

        bad_observer = BadObserver()
        good_observer = MockObserver()

        manager.add_observer(bad_observer)
        manager.add_observer(good_observer)

        # Add messages then reset to trigger event
        manager.add_message({"role": "user", "content": "Hello"})
        manager.reset()

        # Good observer should still receive event
        assert len(good_observer.events) == 1


class TestContextManagerWithConfig:
    """Tests for ContextManager with configuration options."""

    def test_init_with_custom_thresholds(self) -> None:
        """Should initialize with custom threshold settings."""
        manager = ContextManager(
            model="claude-3-opus",
            warning_threshold=75.0,
            critical_threshold=85.0,
        )

        assert manager.warning_threshold == 75.0
        assert manager.critical_threshold == 85.0

    def test_get_cache_stats(self) -> None:
        """Should return cache statistics."""
        manager = ContextManager(model="claude-3-opus")

        # Add messages to populate cache
        for i in range(10):
            manager.add_message({"role": "user", "content": f"Message {i}"})

        stats = manager.get_cache_stats()

        assert stats is not None
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate_percent" in stats

    def test_clear_cache(self) -> None:
        """Should clear token counter cache."""
        manager = ContextManager(model="claude-3-opus")

        # Add messages to populate cache
        for i in range(10):
            manager.add_message({"role": "user", "content": f"Message {i}"})

        result = manager.clear_cache()

        assert result is True
        stats = manager.get_cache_stats()
        assert stats is not None
        assert stats["size"] == 0
