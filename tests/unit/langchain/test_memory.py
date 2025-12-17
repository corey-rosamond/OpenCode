"""Unit tests for conversation memory classes."""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from code_forge.langchain.memory import (
    ConversationMemory,
    SlidingWindowMemory,
    SummaryMemory,
)
from code_forge.llm.models import Message, MessageRole


class TestConversationMemory:
    """Tests for ConversationMemory class."""

    def test_add_message(self) -> None:
        """Test adding messages to memory."""
        memory = ConversationMemory()
        memory.add_message(Message.user("Hello"))
        memory.add_message(Message.assistant("Hi!"))

        history = memory.get_history()
        assert len(history) == 2
        assert history[0].role == MessageRole.USER
        assert history[1].role == MessageRole.ASSISTANT

    def test_add_messages_batch(self) -> None:
        """Test adding multiple messages at once."""
        memory = ConversationMemory()
        memory.add_messages([
            Message.user("Hello"),
            Message.assistant("Hi!"),
            Message.user("How are you?"),
        ])

        assert len(memory.get_history()) == 3

    def test_add_langchain_message(self) -> None:
        """Test adding a LangChain message."""
        memory = ConversationMemory()
        memory.add_langchain_message(HumanMessage(content="Hello from LangChain"))

        history = memory.get_history()
        assert len(history) == 1
        assert history[0].role == MessageRole.USER
        assert history[0].content == "Hello from LangChain"

    def test_system_message_handling(self) -> None:
        """Test that system messages go to system_message field."""
        memory = ConversationMemory()
        memory.add_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))

        # System message should not be in history
        history = memory.get_history()
        assert len(history) == 1

        # But should be in get_messages()
        all_msgs = memory.get_messages()
        assert len(all_msgs) == 2
        assert all_msgs[0].role == MessageRole.SYSTEM

    def test_set_system_message(self) -> None:
        """Test explicitly setting system message."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("You are helpful"))

        assert isinstance(memory.system_message, Message)
        assert memory.system_message.content == "You are helpful"

    def test_set_system_message_converts_role(self) -> None:
        """Test that non-system message is converted when set as system."""
        memory = ConversationMemory()
        # Pass a message with content but wrong role
        memory.set_system_message(Message.user("Be helpful"))

        assert isinstance(memory.system_message, Message)
        assert memory.system_message.role == MessageRole.SYSTEM

    def test_get_messages_order(self) -> None:
        """Test that get_messages returns system message first."""
        memory = ConversationMemory()
        memory.add_message(Message.user("Hello"))
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.assistant("Hi!"))

        msgs = memory.get_messages()
        assert len(msgs) == 3
        assert msgs[0].role == MessageRole.SYSTEM
        assert msgs[1].role == MessageRole.USER
        assert msgs[2].role == MessageRole.ASSISTANT

    def test_max_messages_limit(self) -> None:
        """Test that max_messages limit is enforced."""
        memory = ConversationMemory(max_messages=3)

        for i in range(10):
            memory.add_message(Message.user(f"Message {i}"))

        history = memory.get_history()
        assert len(history) == 3
        # Should keep most recent
        assert history[0].content == "Message 7"
        assert history[2].content == "Message 9"

    def test_clear(self) -> None:
        """Test clearing all messages including system."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))

        memory.clear()

        assert len(memory.get_messages()) == 0
        assert memory.system_message is None

    def test_clear_history(self) -> None:
        """Test clearing only conversation history."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))

        memory.clear_history()

        assert len(memory.get_history()) == 0
        assert isinstance(memory.system_message, Message)

    def test_trim_by_tokens(self) -> None:
        """Test trimming messages by token count."""
        memory = ConversationMemory()
        # Add messages with varying lengths
        memory.add_message(Message.user("A" * 100))  # ~25 tokens
        memory.add_message(Message.assistant("B" * 200))  # ~50 tokens
        memory.add_message(Message.user("C" * 100))  # ~25 tokens

        # Trim to 50 tokens (should remove oldest)
        memory.trim(max_tokens=50)

        history = memory.get_history()
        # Should have trimmed at least one message
        assert len(history) <= 2

    def test_to_langchain_messages(self) -> None:
        """Test conversion to LangChain messages."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))
        memory.add_message(Message.assistant("Hi!"))

        lc_msgs = memory.to_langchain_messages()

        assert len(lc_msgs) == 3
        assert isinstance(lc_msgs[0], SystemMessage)
        assert isinstance(lc_msgs[1], HumanMessage)
        assert isinstance(lc_msgs[2], AIMessage)

    def test_from_langchain_messages(self) -> None:
        """Test importing from LangChain messages."""
        memory = ConversationMemory()

        lc_msgs = [
            SystemMessage(content="Be helpful"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!"),
        ]
        memory.from_langchain_messages(lc_msgs)

        assert isinstance(memory.system_message, Message)
        assert memory.system_message.content == "Be helpful"
        assert len(memory.get_history()) == 2

    def test_len(self) -> None:
        """Test __len__ returns message count (excluding system)."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))
        memory.add_message(Message.assistant("Hi!"))

        assert len(memory) == 2

    def test_iter(self) -> None:
        """Test __iter__ iterates over all messages."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))

        msgs = list(memory)
        assert len(msgs) == 2


class TestSlidingWindowMemory:
    """Tests for SlidingWindowMemory class."""

    def test_window_enforced(self) -> None:
        """Test that sliding window is enforced."""
        memory = SlidingWindowMemory(window_size=2)

        # Add 5 exchanges
        for i in range(5):
            memory.add_message(Message.user(f"Q{i}"))
            memory.add_message(Message.assistant(f"A{i}"))

        history = memory.get_history()
        # Should have at most 4 messages (2 pairs)
        assert len(history) <= 4

    def test_system_message_preserved(self) -> None:
        """Test that system message is preserved with window."""
        memory = SlidingWindowMemory(window_size=1)
        memory.set_system_message(Message.system("Be helpful"))

        # Add many exchanges
        for i in range(5):
            memory.add_message(Message.user(f"Q{i}"))
            memory.add_message(Message.assistant(f"A{i}"))

        msgs = memory.get_messages()
        assert msgs[0].role == MessageRole.SYSTEM

    def test_small_window(self) -> None:
        """Test with very small window size."""
        memory = SlidingWindowMemory(window_size=1)

        memory.add_message(Message.user("First"))
        memory.add_message(Message.assistant("Response 1"))
        memory.add_message(Message.user("Second"))
        memory.add_message(Message.assistant("Response 2"))

        # Should only have last pair
        history = memory.get_history()
        assert len(history) <= 2


class TestSummaryMemory:
    """Tests for SummaryMemory class."""

    def test_get_messages_with_summary(self) -> None:
        """Test that summary is included in messages."""
        memory = SummaryMemory()
        memory.summary = "Previous discussion about Python."
        memory.add_message(Message.user("Hello"))

        msgs = memory.get_messages()

        # Should have summary as a system note
        has_summary = any("[Previous conversation summary:" in (m.content or "") for m in msgs)
        assert has_summary

    def test_get_messages_without_summary(self) -> None:
        """Test messages without summary."""
        memory = SummaryMemory()
        memory.add_message(Message.user("Hello"))

        msgs = memory.get_messages()

        # Should not have summary note
        has_summary = any("[Previous conversation summary:" in (m.content or "") for m in msgs)
        assert not has_summary

    def test_summary_with_system_message(self) -> None:
        """Test that both system message and summary are included."""
        memory = SummaryMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.summary = "Previous discussion."
        memory.add_message(Message.user("Hello"))

        msgs = memory.get_messages()

        assert len(msgs) >= 3  # system + summary + user
        assert msgs[0].role == MessageRole.SYSTEM
        assert msgs[0].content == "Be helpful"

    @pytest.mark.asyncio
    async def test_maybe_summarize_no_op_without_summarizer(self) -> None:
        """Test that maybe_summarize is a no-op without summarizer."""
        memory = SummaryMemory(summary_threshold=5)

        # Add many messages
        for i in range(10):
            memory.add_message(Message.user(f"Msg {i}"))

        await memory.maybe_summarize()

        # Should not have summarized (no summarizer)
        assert memory.summary is None
        assert len(memory.get_history()) == 10

    @pytest.mark.asyncio
    async def test_maybe_summarize_under_threshold(self) -> None:
        """Test that maybe_summarize is a no-op under threshold."""
        memory = SummaryMemory(summary_threshold=10)

        # Add fewer messages than threshold
        for i in range(5):
            memory.add_message(Message.user(f"Msg {i}"))

        await memory.maybe_summarize()

        # Should not have attempted summarization
        assert memory.summary is None

    @pytest.mark.asyncio
    async def test_maybe_summarize_with_summarizer(self) -> None:
        """Test that maybe_summarize works with a summarizer LLM."""
        from unittest.mock import AsyncMock, MagicMock
        from langchain_core.messages import AIMessage

        memory = SummaryMemory(summary_threshold=5)

        # Add more than threshold messages
        for i in range(15):
            memory.add_message(Message.user(f"User message {i}"))
            memory.add_message(Message.assistant(f"Assistant response {i}"))

        # Create mock summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.ainvoke = AsyncMock(
            return_value=AIMessage(content="Summary: User discussed topics 0-14.")
        )
        memory.summarizer = mock_summarizer

        await memory.maybe_summarize()

        # Should have created summary
        assert isinstance(memory.summary, str)
        assert "Summary" in memory.summary
        # Should have trimmed messages
        assert len(memory.messages) == 10  # Keeps last 10

    @pytest.mark.asyncio
    async def test_maybe_summarize_appends_to_existing(self) -> None:
        """Test that subsequent summaries are appended."""
        from unittest.mock import AsyncMock, MagicMock
        from langchain_core.messages import AIMessage

        memory = SummaryMemory(summary_threshold=5)
        memory.summary = "Previous conversation about Python."

        # Add many messages
        for i in range(15):
            memory.add_message(Message.user(f"Msg {i}"))

        mock_summarizer = MagicMock()
        mock_summarizer.ainvoke = AsyncMock(
            return_value=AIMessage(content="New topics discussed.")
        )
        memory.summarizer = mock_summarizer

        await memory.maybe_summarize()

        # Should have combined summaries
        assert "Previous conversation" in memory.summary
        assert "New topics" in memory.summary


class TestConversationMemoryEdgeCases:
    """Edge case tests for ConversationMemory."""

    def test_trim_with_system_message(self) -> None:
        """Test that trim accounts for system message tokens."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("A" * 400))  # ~100 tokens

        # Add some messages
        memory.add_message(Message.user("B" * 400))  # ~100 tokens
        memory.add_message(Message.assistant("C" * 400))  # ~100 tokens
        memory.add_message(Message.user("D" * 400))  # ~100 tokens

        # Trim to 200 tokens (system 100 + 100 for one message)
        memory.trim(max_tokens=200)

        # Should have trimmed some messages while accounting for system
        history = memory.get_history()
        assert len(history) < 3

    def test_trim_with_custom_token_counter(self) -> None:
        """Test trim with custom token counter function."""
        memory = ConversationMemory()

        # Custom counter: 10 tokens per message regardless of content
        def custom_counter(msg):
            return 10

        memory._token_counter = custom_counter

        # Add 5 messages = 50 tokens
        for i in range(5):
            memory.add_message(Message.user(f"Msg {i}"))

        # Trim to 30 tokens (should keep 3 messages)
        memory.trim(max_tokens=30)

        history = memory.get_history()
        assert len(history) == 3

    def test_set_system_message_with_list_content(self) -> None:
        """Test setting system message from message with list content."""
        memory = ConversationMemory()

        # Create message with list content
        msg = Message(
            role=MessageRole.USER,
            content=[{"type": "text", "text": "Hello "}, {"type": "text", "text": "World"}],
        )

        memory.set_system_message(msg)

        assert isinstance(memory.system_message, Message)
        assert memory.system_message.role == MessageRole.SYSTEM
        assert memory.system_message.content == "Hello World"

    def test_from_langchain_clears_existing(self) -> None:
        """Test that from_langchain_messages clears existing data."""
        memory = ConversationMemory()
        memory.set_system_message(Message.system("Old system"))
        memory.add_message(Message.user("Old message"))

        # Import new messages
        lc_msgs = [
            HumanMessage(content="New message"),
        ]
        memory.from_langchain_messages(lc_msgs)

        # Old system message should be cleared
        assert memory.system_message is None
        # Only new message should exist
        assert len(memory.get_history()) == 1
        assert memory.get_history()[0].content == "New message"


class TestSlidingWindowMemoryEdgeCases:
    """Edge case tests for SlidingWindowMemory."""

    def test_window_with_odd_messages(self) -> None:
        """Test sliding window handles odd number of messages."""
        memory = SlidingWindowMemory(window_size=2)

        # Add odd number of messages (not pairs)
        memory.add_message(Message.user("Q1"))
        memory.add_message(Message.assistant("A1"))
        memory.add_message(Message.user("Q2"))

        history = memory.get_history()
        # Should still enforce window (max 4 messages)
        assert len(history) <= 4

    def test_window_size_one(self) -> None:
        """Test behavior with window size of one."""
        memory = SlidingWindowMemory(window_size=1)

        memory.add_message(Message.user("First"))
        memory.add_message(Message.assistant("Response 1"))
        memory.add_message(Message.user("Second"))
        memory.add_message(Message.assistant("Response 2"))

        # With window_size=1, max is 2 messages (one pair)
        history = memory.get_history()
        assert len(history) == 2
        assert history[0].content == "Second"
        assert history[1].content == "Response 2"
