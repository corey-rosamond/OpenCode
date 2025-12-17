"""Tests for Thinking mode."""

import time
from datetime import datetime

import pytest

from code_forge.modes.base import ModeContext, ModeName
from code_forge.modes.thinking import (
    THINKING_PATTERN,
    ThinkingConfig,
    ThinkingMode,
    ThinkingResult,
    should_suggest_thinking,
)


class TestThinkingConfig:
    """Tests for ThinkingConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ThinkingConfig()
        assert config.max_thinking_tokens == 10000
        assert config.show_thinking is True
        assert config.thinking_style == "analytical"
        assert config.deep_mode is False

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ThinkingConfig(
            max_thinking_tokens=5000,
            show_thinking=False,
            thinking_style="creative",
            deep_mode=True,
        )
        assert config.max_thinking_tokens == 5000
        assert config.show_thinking is False
        assert config.thinking_style == "creative"
        assert config.deep_mode is True


class TestThinkingResult:
    """Tests for ThinkingResult dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic result creation."""
        result = ThinkingResult(
            thinking="My analysis...",
            response="The answer is...",
        )
        assert result.thinking == "My analysis..."
        assert result.response == "The answer is..."
        assert result.thinking_tokens == 0
        assert result.response_tokens == 0
        assert result.time_seconds == 0.0
        assert isinstance(result.timestamp, datetime)

    def test_with_metrics(self) -> None:
        """Test result with metrics."""
        result = ThinkingResult(
            thinking="Analysis",
            response="Answer",
            thinking_tokens=100,
            response_tokens=50,
            time_seconds=2.5,
        )
        assert result.thinking_tokens == 100
        assert result.response_tokens == 50
        assert result.time_seconds == 2.5

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        result = ThinkingResult(
            thinking="Analysis",
            response="Answer",
            thinking_tokens=100,
            time_seconds=1.5,
        )
        data = result.to_dict()

        assert data["thinking"] == "Analysis"
        assert data["response"] == "Answer"
        assert data["thinking_tokens"] == 100
        assert data["time_seconds"] == 1.5
        assert "timestamp" in data

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "thinking": "Analysis",
            "response": "Answer",
            "thinking_tokens": 100,
            "response_tokens": 50,
            "time_seconds": 2.0,
            "timestamp": "2025-01-01T12:00:00",
        }
        result = ThinkingResult.from_dict(data)

        assert result.thinking == "Analysis"
        assert result.response == "Answer"
        assert result.thinking_tokens == 100
        assert result.time_seconds == 2.0

    def test_from_dict_minimal(self) -> None:
        """Test deserialization with minimal data."""
        data = {
            "thinking": "Analysis",
            "response": "Answer",
        }
        result = ThinkingResult.from_dict(data)

        assert result.thinking == "Analysis"
        assert result.response == "Answer"
        assert result.thinking_tokens == 0

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = ThinkingResult(
            thinking="Deep analysis",
            response="Final answer",
            thinking_tokens=500,
            response_tokens=100,
            time_seconds=3.5,
        )
        restored = ThinkingResult.from_dict(original.to_dict())

        assert restored.thinking == original.thinking
        assert restored.response == original.response
        assert restored.thinking_tokens == original.thinking_tokens


class TestThinkingPattern:
    """Tests for thinking extraction pattern."""

    def test_match_basic(self) -> None:
        """Test basic pattern matching."""
        text = "<thinking>Analysis</thinking><response>Answer</response>"
        match = THINKING_PATTERN.search(text)

        assert match and match.group(0)
        assert match.group(1).strip() == "Analysis"
        assert match.group(2).strip() == "Answer"

    def test_match_with_whitespace(self) -> None:
        """Test matching with whitespace."""
        text = """
        <thinking>
        Multi-line
        analysis
        </thinking>
        <response>
        Multi-line
        answer
        </response>
        """
        match = THINKING_PATTERN.search(text)

        assert match and match.group(0)
        assert "Multi-line" in match.group(1)
        assert "Multi-line" in match.group(2)

    def test_match_case_insensitive(self) -> None:
        """Test case insensitive matching."""
        text = "<THINKING>Analysis</THINKING><RESPONSE>Answer</RESPONSE>"
        match = THINKING_PATTERN.search(text)

        assert match and match.group(0)
        assert match.group(1).strip() == "Analysis"

    def test_no_match(self) -> None:
        """Test no match for plain text."""
        text = "Just a regular response."
        match = THINKING_PATTERN.search(text)
        assert match is None

    def test_partial_tags(self) -> None:
        """Test partial tags don't match."""
        text = "<thinking>Analysis</thinking> but no response tag"
        match = THINKING_PATTERN.search(text)
        assert match is None


class TestThinkingMode:
    """Tests for ThinkingMode class."""

    @pytest.fixture
    def mode(self) -> ThinkingMode:
        """Create thinking mode for tests."""
        return ThinkingMode()

    @pytest.fixture
    def context(self) -> ModeContext:
        """Create test context."""
        messages: list[str] = []
        return ModeContext(output=lambda m: messages.append(m))

    def test_name(self, mode: ThinkingMode) -> None:
        """Test mode name."""
        assert mode.name == ModeName.THINKING

    def test_default_config(self, mode: ThinkingMode) -> None:
        """Test default configuration."""
        assert mode.config.name == ModeName.THINKING
        assert mode.config.description == "Extended thinking mode"
        assert "THINKING MODE" in mode.config.system_prompt_addition

    def test_default_thinking_config(self, mode: ThinkingMode) -> None:
        """Test default thinking config."""
        assert mode.thinking_config.max_thinking_tokens == 10000
        assert mode.thinking_config.show_thinking is True

    def test_custom_thinking_config(self) -> None:
        """Test custom thinking config."""
        config = ThinkingConfig(max_thinking_tokens=5000, deep_mode=True)
        mode = ThinkingMode(thinking_config=config)
        assert mode.thinking_config.max_thinking_tokens == 5000
        assert mode.thinking_config.deep_mode is True

    def test_initial_state(self, mode: ThinkingMode) -> None:
        """Test initial state."""
        assert mode.is_active is False
        assert mode._start_time is None

    def test_activate(self, mode: ThinkingMode, context: ModeContext) -> None:
        """Test mode activation."""
        mode.activate(context)

        assert mode.is_active is True
        assert isinstance(mode._start_time, float)

    def test_activate_deep_mode(self, context: ModeContext) -> None:
        """Test activation in deep mode."""
        config = ThinkingConfig(deep_mode=True)
        mode = ThinkingMode(thinking_config=config)

        mode.activate(context)

        assert "DEEP THINKING" in mode.config.system_prompt_addition

    def test_deactivate(self, mode: ThinkingMode, context: ModeContext) -> None:
        """Test mode deactivation."""
        mode.activate(context)
        mode.deactivate(context)

        assert mode.is_active is False
        assert mode._start_time is None

    def test_set_deep_mode_enable(self, mode: ThinkingMode) -> None:
        """Test enabling deep mode."""
        mode.set_deep_mode(True)

        assert mode.thinking_config.deep_mode is True
        assert "DEEP THINKING" in mode.config.system_prompt_addition

    def test_set_deep_mode_disable(self, mode: ThinkingMode) -> None:
        """Test disabling deep mode."""
        mode.set_deep_mode(True)
        mode.set_deep_mode(False)

        assert mode.thinking_config.deep_mode is False
        assert "DEEP THINKING" not in mode.config.system_prompt_addition

    def test_set_thinking_budget(self, mode: ThinkingMode) -> None:
        """Test setting thinking budget."""
        mode.set_thinking_budget(5000)
        assert mode.thinking_config.max_thinking_tokens == 5000

    def test_set_thinking_budget_minimum(self, mode: ThinkingMode) -> None:
        """Test budget enforces minimum."""
        mode.set_thinking_budget(100)
        assert mode.thinking_config.max_thinking_tokens == 1000

    def test_modify_response_with_tags(
        self, mode: ThinkingMode, context: ModeContext
    ) -> None:
        """Test response modification with thinking tags."""
        mode.activate(context)
        # Wait a tiny bit so we have measurable time
        time.sleep(0.01)

        response = "<thinking>Analysis</thinking><response>Answer</response>"
        result = mode.modify_response(response)

        assert "Analysis" in result
        assert "Answer" in result

    def test_modify_response_without_tags(
        self, mode: ThinkingMode, context: ModeContext
    ) -> None:
        """Test response without tags passes through."""
        mode.activate(context)

        response = "Plain response without tags."
        result = mode.modify_response(response)

        assert result == response

    def test_modify_response_stores_result(
        self, mode: ThinkingMode, context: ModeContext
    ) -> None:
        """Test thinking result is stored in state."""
        mode.activate(context)

        response = "<thinking>Analysis</thinking><response>Answer</response>"
        mode.modify_response(response)

        assert "last_thinking" in mode._state.data

    def test_format_thinking_output_show(self, mode: ThinkingMode) -> None:
        """Test formatting with show_thinking enabled."""
        result = ThinkingResult(
            thinking="Analysis",
            response="Answer",
            time_seconds=1.5,
        )
        output = mode.format_thinking_output(result)

        assert "Thinking Process" in output
        assert "Analysis" in output
        assert "Answer" in output
        assert "1.5s" in output

    def test_format_thinking_output_hide(self) -> None:
        """Test formatting with show_thinking disabled."""
        config = ThinkingConfig(show_thinking=False)
        mode = ThinkingMode(thinking_config=config)

        result = ThinkingResult(
            thinking="Analysis",
            response="Answer",
            time_seconds=1.0,
        )
        output = mode.format_thinking_output(result)

        assert "Thinking Process" not in output
        assert "Analysis" not in output
        assert "Answer" in output

    def test_get_last_thinking_none(self, mode: ThinkingMode) -> None:
        """Test getting last thinking when none exists."""
        result = mode.get_last_thinking()
        assert result is None

    def test_get_last_thinking_exists(
        self, mode: ThinkingMode, context: ModeContext
    ) -> None:
        """Test getting last thinking after processing."""
        mode.activate(context)

        response = "<thinking>Analysis</thinking><response>Answer</response>"
        mode.modify_response(response)

        result = mode.get_last_thinking()

        assert isinstance(result, ThinkingResult)
        assert result.thinking == "Analysis"
        assert result.response == "Answer"


class TestShouldSuggestThinking:
    """Tests for should_suggest_thinking function."""

    def test_complex_keyword(self) -> None:
        """Test detection of 'complex' keyword."""
        assert should_suggest_thinking("This is a complex problem") is True

    def test_difficult_keyword(self) -> None:
        """Test detection of 'difficult' keyword."""
        assert should_suggest_thinking("This is difficult to solve") is True

    def test_tricky_keyword(self) -> None:
        """Test detection of 'tricky' keyword."""
        assert should_suggest_thinking("This is tricky") is True

    def test_tradeoffs(self) -> None:
        """Test detection of trade-offs."""
        assert should_suggest_thinking("What are the trade-offs?") is True
        assert should_suggest_thinking("Consider the tradeoffs") is True

    def test_analyze(self) -> None:
        """Test detection of analyze."""
        assert should_suggest_thinking("Can you analyze this?") is True

    def test_compare_approaches(self) -> None:
        """Test detection of comparing approaches."""
        assert should_suggest_thinking("Compare the approaches") is True

    def test_pros_and_cons(self) -> None:
        """Test detection of pros and cons."""
        assert should_suggest_thinking("What are the pros and cons?") is True

    def test_think_carefully(self) -> None:
        """Test detection of 'think carefully'."""
        assert should_suggest_thinking("Think through this carefully") is True
        assert should_suggest_thinking("Think about it") is True

    def test_normal_message(self) -> None:
        """Test normal messages don't trigger."""
        assert should_suggest_thinking("Hello world") is False
        assert should_suggest_thinking("Fix the bug") is False
        assert should_suggest_thinking("Write a function") is False

    def test_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert should_suggest_thinking("COMPLEX problem") is True
        assert should_suggest_thinking("Analyze THIS") is True
