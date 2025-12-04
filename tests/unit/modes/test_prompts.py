"""Tests for mode prompts."""

import pytest

from opencode.modes.prompts import (
    HEADLESS_MODE_PROMPT,
    MODE_PROMPTS,
    PLAN_MODE_PROMPT,
    THINKING_MODE_DEEP_PROMPT,
    THINKING_MODE_PROMPT,
    get_mode_prompt,
)


class TestModePrompts:
    """Tests for mode prompt constants."""

    def test_plan_mode_prompt_exists(self) -> None:
        """Test PLAN_MODE_PROMPT is defined."""
        assert PLAN_MODE_PROMPT
        assert len(PLAN_MODE_PROMPT) > 100

    def test_plan_mode_prompt_content(self) -> None:
        """Test PLAN_MODE_PROMPT contains key instructions."""
        assert "PLAN MODE" in PLAN_MODE_PROMPT
        assert "Steps" in PLAN_MODE_PROMPT
        assert "/plan" in PLAN_MODE_PROMPT

    def test_thinking_mode_prompt_exists(self) -> None:
        """Test THINKING_MODE_PROMPT is defined."""
        assert THINKING_MODE_PROMPT
        assert len(THINKING_MODE_PROMPT) > 100

    def test_thinking_mode_prompt_content(self) -> None:
        """Test THINKING_MODE_PROMPT contains key instructions."""
        assert "THINKING MODE" in THINKING_MODE_PROMPT
        assert "<thinking>" in THINKING_MODE_PROMPT
        assert "<response>" in THINKING_MODE_PROMPT

    def test_thinking_deep_prompt_exists(self) -> None:
        """Test THINKING_MODE_DEEP_PROMPT is defined."""
        assert THINKING_MODE_DEEP_PROMPT
        assert len(THINKING_MODE_DEEP_PROMPT) > 100

    def test_thinking_deep_prompt_content(self) -> None:
        """Test THINKING_MODE_DEEP_PROMPT contains key instructions."""
        assert "DEEP THINKING" in THINKING_MODE_DEEP_PROMPT
        assert "Trade-off" in THINKING_MODE_DEEP_PROMPT

    def test_headless_mode_prompt_exists(self) -> None:
        """Test HEADLESS_MODE_PROMPT is defined."""
        assert HEADLESS_MODE_PROMPT
        assert len(HEADLESS_MODE_PROMPT) > 100

    def test_headless_mode_prompt_content(self) -> None:
        """Test HEADLESS_MODE_PROMPT contains key instructions."""
        assert "HEADLESS MODE" in HEADLESS_MODE_PROMPT
        assert "safe" in HEADLESS_MODE_PROMPT
        assert "unsafe" in HEADLESS_MODE_PROMPT


class TestModePromptsDict:
    """Tests for MODE_PROMPTS dictionary."""

    def test_plan_in_dict(self) -> None:
        """Test plan prompt is in dictionary."""
        assert "plan" in MODE_PROMPTS
        assert MODE_PROMPTS["plan"] == PLAN_MODE_PROMPT

    def test_thinking_in_dict(self) -> None:
        """Test thinking prompt is in dictionary."""
        assert "thinking" in MODE_PROMPTS
        assert MODE_PROMPTS["thinking"] == THINKING_MODE_PROMPT

    def test_thinking_deep_in_dict(self) -> None:
        """Test thinking_deep prompt is in dictionary."""
        assert "thinking_deep" in MODE_PROMPTS
        assert MODE_PROMPTS["thinking_deep"] == THINKING_MODE_DEEP_PROMPT

    def test_headless_in_dict(self) -> None:
        """Test headless prompt is in dictionary."""
        assert "headless" in MODE_PROMPTS
        assert MODE_PROMPTS["headless"] == HEADLESS_MODE_PROMPT


class TestGetModePrompt:
    """Tests for get_mode_prompt function."""

    def test_get_plan_prompt(self) -> None:
        """Test getting plan mode prompt."""
        prompt = get_mode_prompt("plan")
        assert prompt == PLAN_MODE_PROMPT

    def test_get_thinking_prompt(self) -> None:
        """Test getting thinking mode prompt."""
        prompt = get_mode_prompt("thinking")
        assert prompt == THINKING_MODE_PROMPT

    def test_get_thinking_deep_prompt(self) -> None:
        """Test getting thinking deep prompt with variant."""
        prompt = get_mode_prompt("thinking", "deep")
        assert prompt == THINKING_MODE_DEEP_PROMPT

    def test_get_headless_prompt(self) -> None:
        """Test getting headless mode prompt."""
        prompt = get_mode_prompt("headless")
        assert prompt == HEADLESS_MODE_PROMPT

    def test_get_unknown_mode(self) -> None:
        """Test getting unknown mode returns empty."""
        prompt = get_mode_prompt("unknown")
        assert prompt == ""

    def test_get_unknown_variant(self) -> None:
        """Test getting unknown variant falls back to base."""
        prompt = get_mode_prompt("plan", "unknown_variant")
        # Should fall back to base plan prompt
        assert prompt == PLAN_MODE_PROMPT

    def test_case_sensitive(self) -> None:
        """Test mode names are case sensitive."""
        # Lowercase should work
        assert get_mode_prompt("plan") == PLAN_MODE_PROMPT
        # Uppercase should not match
        assert get_mode_prompt("PLAN") == ""
