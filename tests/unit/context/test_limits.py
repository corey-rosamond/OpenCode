"""Unit tests for context limits and tracking."""

import json
from typing import Any

import pytest

from code_forge.context.limits import (
    ContextBudget,
    ContextLimits,
    ContextTracker,
    MODEL_LIMITS,
)
from code_forge.context.tokens import TokenCounter


class TestContextBudget:
    """Tests for ContextBudget dataclass."""

    def test_init_valid_budget(self) -> None:
        """Should create budget with valid parameters."""
        budget = ContextBudget(total=100000, response_reserve=4096)
        assert budget.total == 100000
        assert budget.response_reserve == 4096

    def test_init_requires_positive_total(self) -> None:
        """Should raise ValueError for non-positive total."""
        with pytest.raises(ValueError, match="total must be positive"):
            ContextBudget(total=0)

        with pytest.raises(ValueError, match="total must be positive"):
            ContextBudget(total=-100)

    def test_init_requires_non_negative_reserve(self) -> None:
        """Should raise ValueError for negative reserve."""
        with pytest.raises(ValueError, match="cannot be negative"):
            ContextBudget(total=100000, response_reserve=-1)

    def test_init_reserve_must_be_less_than_total(self) -> None:
        """Should raise ValueError if reserve >= total."""
        with pytest.raises(ValueError, match="must be less than total"):
            ContextBudget(total=100, response_reserve=100)

        with pytest.raises(ValueError, match="must be less than total"):
            ContextBudget(total=100, response_reserve=200)

    def test_negative_allocations_clamped_to_zero(self) -> None:
        """Negative allocations should be clamped to zero."""
        budget = ContextBudget(
            total=100000,
            system_prompt=-100,
            conversation=-50,
            tools=-25,
        )
        assert budget.system_prompt == 0
        assert budget.conversation == 0
        assert budget.tools == 0

    def test_available_property(self) -> None:
        """available should return tokens remaining after allocations."""
        budget = ContextBudget(
            total=100000,
            system_prompt=2000,
            conversation=50000,
            tools=5000,
            response_reserve=4096,
        )
        # 100000 - 2000 - 50000 - 5000 - 4096 = 38904
        assert budget.available == 38904

    def test_available_never_negative(self) -> None:
        """available should never be negative."""
        budget = ContextBudget(total=10000, response_reserve=4000)
        budget.system_prompt = 5000
        budget.conversation = 5000
        budget.tools = 5000
        # Over budget, but available should be 0, not negative
        assert budget.available == 0

    def test_conversation_budget_property(self) -> None:
        """conversation_budget should return max tokens for conversation."""
        budget = ContextBudget(
            total=100000,
            system_prompt=2000,
            tools=5000,
            response_reserve=4096,
        )
        # 100000 - 2000 - 5000 - 4096 = 88904
        assert budget.conversation_budget == 88904

    def test_conversation_budget_never_negative(self) -> None:
        """conversation_budget should never be negative."""
        budget = ContextBudget(
            total=10000,
            system_prompt=8000,
            tools=3000,
            response_reserve=4000,
        )
        assert budget.conversation_budget == 0

    def test_is_over_budget_false(self) -> None:
        """is_over_budget should return False when under budget."""
        budget = ContextBudget(total=100000, response_reserve=4096)
        budget.system_prompt = 2000
        budget.conversation = 50000
        assert not budget.is_over_budget

    def test_is_over_budget_true(self) -> None:
        """is_over_budget should return True when over budget."""
        budget = ContextBudget(total=10000, response_reserve=4000)
        budget.system_prompt = 5000
        budget.conversation = 5000
        budget.tools = 1000
        # Total: 5000 + 5000 + 1000 + 4000 = 15000 > 10000
        assert budget.is_over_budget

    def test_update_system_prompt(self) -> None:
        """update_system_prompt should set system_prompt."""
        budget = ContextBudget(total=100000)
        budget.update_system_prompt(5000)
        assert budget.system_prompt == 5000

    def test_update_system_prompt_clamps_negative(self) -> None:
        """update_system_prompt should clamp negative values."""
        budget = ContextBudget(total=100000)
        budget.update_system_prompt(-100)
        assert budget.system_prompt == 0

    def test_update_tools(self) -> None:
        """update_tools should set tools."""
        budget = ContextBudget(total=100000)
        budget.update_tools(3000)
        assert budget.tools == 3000

    def test_update_conversation(self) -> None:
        """update_conversation should set conversation."""
        budget = ContextBudget(total=100000)
        budget.update_conversation(50000)
        assert budget.conversation == 50000


class TestContextLimits:
    """Tests for ContextLimits dataclass."""

    def test_for_model_known_model(self) -> None:
        """Should return correct limits for known model."""
        limits = ContextLimits.for_model("claude-3-opus")
        assert limits.max_tokens == 200000
        assert limits.max_output_tokens == 4096

    def test_for_model_gpt4(self) -> None:
        """Should return correct limits for GPT-4."""
        limits = ContextLimits.for_model("gpt-4")
        assert limits.max_tokens == 8192
        assert limits.max_output_tokens == 4096

    def test_for_model_unknown_uses_default(self) -> None:
        """Should use default limits for unknown model."""
        limits = ContextLimits.for_model("unknown-model-xyz")
        default_ctx, default_out = MODEL_LIMITS["default"]
        assert limits.max_tokens == default_ctx
        assert limits.max_output_tokens == default_out

    def test_for_model_case_insensitive(self) -> None:
        """Model matching should be case insensitive."""
        limits1 = ContextLimits.for_model("CLAUDE-3-OPUS")
        limits2 = ContextLimits.for_model("claude-3-opus")
        assert limits1.max_tokens == limits2.max_tokens

    def test_for_model_prefix_match(self) -> None:
        """Should match model prefixes."""
        # "gpt-4-turbo-preview" should match "gpt-4-turbo"
        limits = ContextLimits.for_model("gpt-4-turbo-preview")
        assert limits.max_tokens == 128000

    def test_effective_limit(self) -> None:
        """effective_limit should subtract output tokens and reserved."""
        limits = ContextLimits(
            model="test",
            max_tokens=100000,
            max_output_tokens=4096,
            reserved_tokens=1000,
        )
        # 100000 - 4096 - 1000 = 94904
        assert limits.effective_limit == 94904

    def test_effective_limit_default_reserved(self) -> None:
        """Should use default reserved tokens."""
        limits = ContextLimits(
            model="test",
            max_tokens=100000,
            max_output_tokens=4096,
        )
        # Default reserved is 1000
        assert limits.effective_limit == 94904


class TestContextTracker:
    """Tests for ContextTracker."""

    def test_for_model_creates_tracker(self) -> None:
        """Should create tracker with correct limits and counter."""
        tracker = ContextTracker.for_model("claude-3-opus")
        assert tracker.limits.max_tokens == 200000
        assert isinstance(tracker.counter, TokenCounter)

    def test_set_system_prompt(self) -> None:
        """Should set system prompt and update budget."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tokens = tracker.set_system_prompt("You are a helpful assistant.")
        assert tokens > 0
        assert tracker.budget.system_prompt == tokens
        assert tracker.system_prompt == "You are a helpful assistant."

    def test_set_tool_definitions(self) -> None:
        """Should set tool definitions and update budget."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {"type": "object"},
                },
            }
        ]
        tokens = tracker.set_tool_definitions(tools)
        assert tokens > 0
        assert tracker.budget.tools == tokens
        assert tracker.tool_definitions == tools

    def test_update_messages(self) -> None:
        """Should update with message list."""
        tracker = ContextTracker.for_model("claude-3-opus")
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        tokens = tracker.update(messages)
        assert tokens > 0
        assert tracker.budget.conversation == tokens
        assert len(tracker.messages) == 2

    def test_add_message(self) -> None:
        """Should add single message and update budget."""
        tracker = ContextTracker.for_model("claude-3-opus")
        message = {"role": "user", "content": "Hello"}
        tokens = tracker.add_message(message)
        assert tokens > 0
        assert len(tracker.messages) == 1

    def test_add_message_accumulates(self) -> None:
        """Adding messages should accumulate tokens."""
        tracker = ContextTracker.for_model("claude-3-opus")

        tracker.add_message({"role": "user", "content": "Hello"})
        tokens1 = tracker.budget.conversation

        tracker.add_message({"role": "assistant", "content": "Hi!"})
        tokens2 = tracker.budget.conversation

        assert tokens2 > tokens1

    def test_current_tokens(self) -> None:
        """Should return total current tokens."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tracker.set_system_prompt("System")
        tracker.set_tool_definitions([{"name": "tool"}])
        tracker.add_message({"role": "user", "content": "Hello"})

        total = tracker.current_tokens()
        expected = (
            tracker.budget.system_prompt
            + tracker.budget.conversation
            + tracker.budget.tools
        )
        assert total == expected

    def test_exceeds_limit_false(self) -> None:
        """Should return False when under limit."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tracker.add_message({"role": "user", "content": "Hello"})
        assert not tracker.exceeds_limit()

    def test_exceeds_limit_true(self) -> None:
        """Should return True when over limit."""
        # Use a model with small context
        tracker = ContextTracker.for_model("gpt-4")  # 8K context

        # Add many messages to exceed the limit
        for _ in range(100):
            tracker.add_message({"role": "user", "content": "word " * 100})

        assert tracker.exceeds_limit()

    def test_overflow_amount_zero_when_under(self) -> None:
        """Should return 0 when under limit."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tracker.add_message({"role": "user", "content": "Hello"})
        assert tracker.overflow_amount() == 0

    def test_overflow_amount_positive_when_over(self) -> None:
        """Should return positive value when over limit."""
        tracker = ContextTracker.for_model("gpt-4")  # 8K context

        # Add many messages to exceed the limit
        for _ in range(100):
            tracker.add_message({"role": "user", "content": "word " * 100})

        assert tracker.overflow_amount() > 0

    def test_available_tokens(self) -> None:
        """Should return available tokens."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tracker.set_system_prompt("System")
        available = tracker.available_tokens()
        assert available > 0
        assert available < tracker.limits.effective_limit

    def test_usage_percentage(self) -> None:
        """Should return usage as percentage."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tracker.add_message({"role": "user", "content": "Hello"})

        usage = tracker.usage_percentage()
        assert 0 < usage < 100

    def test_usage_percentage_zero_when_empty(self) -> None:
        """Should return 0 when no usage."""
        tracker = ContextTracker.for_model("claude-3-opus")
        assert tracker.usage_percentage() == 0

    def test_reset(self) -> None:
        """Should reset messages and conversation budget."""
        tracker = ContextTracker.for_model("claude-3-opus")
        tracker.add_message({"role": "user", "content": "Hello"})
        tracker.add_message({"role": "assistant", "content": "Hi!"})

        tracker.reset()

        assert len(tracker.messages) == 0
        assert tracker.budget.conversation == 0


class TestModelLimits:
    """Tests for MODEL_LIMITS configuration."""

    def test_claude_models_have_200k_context(self) -> None:
        """Claude 3 models should have 200K context."""
        for key in ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]:
            ctx, _ = MODEL_LIMITS[key]
            assert ctx == 200000

    def test_gpt4_turbo_has_128k_context(self) -> None:
        """GPT-4 Turbo should have 128K context."""
        ctx, _ = MODEL_LIMITS["gpt-4-turbo"]
        assert ctx == 128000

    def test_default_exists(self) -> None:
        """Default limits should exist."""
        assert "default" in MODEL_LIMITS
