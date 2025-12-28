"""Tests for CLI status bar."""

from __future__ import annotations

import pytest

from code_forge.cli.status import ContextWarningLevel, StatusBar, StatusBarObserver


class MockObserver(StatusBarObserver):
    """Mock observer for testing."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_status_bar: StatusBar | None = None

    def on_status_changed(self, status_bar: StatusBar) -> None:
        self.call_count += 1
        self.last_status_bar = status_bar


class TestStatusBar:
    """Tests for StatusBar class."""

    def test_default_values(self) -> None:
        """Test default status bar values."""
        status = StatusBar()
        assert status.model == ""
        assert status.tokens_used == 0
        assert status.tokens_max == 128000
        assert status.mode == "Normal"
        assert status.status == "Ready"
        assert status.visible is True

    def test_custom_values(self) -> None:
        """Test creating status bar with custom values."""
        status = StatusBar(
            model="claude-3",
            tokens_used=1000,
            tokens_max=200000,
            mode="Plan",
            status="Processing",
            visible=False,
        )
        assert status.model == "claude-3"
        assert status.tokens_used == 1000
        assert status.tokens_max == 200000
        assert status.mode == "Plan"
        assert status.status == "Processing"
        assert status.visible is False

    def test_set_model(self) -> None:
        """Test setting model name."""
        status = StatusBar()
        status.set_model("gpt-4")
        assert status.model == "gpt-4"

    def test_set_model_notifies(self) -> None:
        """Test that set_model notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_model("gpt-4")
        assert observer.call_count == 1

    def test_set_model_no_notify_if_same(self) -> None:
        """Test that set_model doesn't notify if value unchanged."""
        status = StatusBar(model="gpt-4")
        observer = MockObserver()
        status.add_observer(observer)
        status.set_model("gpt-4")
        assert observer.call_count == 0

    def test_set_tokens(self) -> None:
        """Test setting token counts."""
        status = StatusBar()
        status.set_tokens(5000)
        assert status.tokens_used == 5000
        assert status.tokens_max == 128000  # Unchanged

    def test_set_tokens_with_max(self) -> None:
        """Test setting token counts with max."""
        status = StatusBar()
        status.set_tokens(5000, 200000)
        assert status.tokens_used == 5000
        assert status.tokens_max == 200000

    def test_set_tokens_notifies(self) -> None:
        """Test that set_tokens notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_tokens(5000)
        assert observer.call_count == 1

    def test_set_tokens_no_notify_if_same(self) -> None:
        """Test that set_tokens doesn't notify if unchanged."""
        status = StatusBar(tokens_used=5000)
        observer = MockObserver()
        status.add_observer(observer)
        status.set_tokens(5000)
        assert observer.call_count == 0

    def test_set_mode(self) -> None:
        """Test setting mode."""
        status = StatusBar()
        status.set_mode("Plan")
        assert status.mode == "Plan"

    def test_set_mode_notifies(self) -> None:
        """Test that set_mode notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_mode("Plan")
        assert observer.call_count == 1

    def test_set_status(self) -> None:
        """Test setting status text."""
        status = StatusBar()
        status.set_status("Processing")
        assert status.status == "Processing"

    def test_set_status_notifies(self) -> None:
        """Test that set_status notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_status("Processing")
        assert observer.call_count == 1

    def test_set_visible(self) -> None:
        """Test setting visibility."""
        status = StatusBar()
        status.set_visible(False)
        assert status.visible is False

    def test_set_visible_notifies(self) -> None:
        """Test that set_visible notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_visible(False)
        assert observer.call_count == 1


class TestStatusBarObserver:
    """Tests for observer functionality."""

    def test_add_observer(self) -> None:
        """Test adding an observer."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_status("test")
        assert observer.call_count == 1

    def test_add_same_observer_twice(self) -> None:
        """Test that adding same observer twice only registers once."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.add_observer(observer)
        status.set_status("test")
        assert observer.call_count == 1

    def test_remove_observer(self) -> None:
        """Test removing an observer."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.remove_observer(observer)
        status.set_status("test")
        assert observer.call_count == 0

    def test_remove_nonexistent_observer(self) -> None:
        """Test removing observer that wasn't added."""
        status = StatusBar()
        observer = MockObserver()
        # Should not raise
        status.remove_observer(observer)

    def test_multiple_observers(self) -> None:
        """Test multiple observers are all notified."""
        status = StatusBar()
        observer1 = MockObserver()
        observer2 = MockObserver()
        status.add_observer(observer1)
        status.add_observer(observer2)
        status.set_status("test")
        assert observer1.call_count == 1
        assert observer2.call_count == 1

    def test_observer_receives_status_bar(self) -> None:
        """Test that observer receives status bar reference."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_status("test")
        assert observer.last_status_bar is status


class TestStatusBarRender:
    """Tests for status bar rendering."""

    def test_render_basic(self) -> None:
        """Test basic rendering."""
        status = StatusBar(
            model="gpt-4",
            tokens_used=1000,
            tokens_max=10000,
            mode="Normal",
            status="Ready",
        )
        result = status.render(80)
        assert "gpt-4" in result
        assert "1,000" in result
        assert "10,000" in result
        assert "Normal" in result
        assert "Ready" in result

    def test_render_invisible(self) -> None:
        """Test rendering when invisible."""
        status = StatusBar(visible=False)
        result = status.render(80)
        assert result == ""

    def test_render_zero_width(self) -> None:
        """Test rendering with zero width."""
        status = StatusBar()
        result = status.render(0)
        assert result == ""

    def test_render_negative_width(self) -> None:
        """Test rendering with negative width."""
        status = StatusBar()
        result = status.render(-10)
        assert result == ""

    def test_render_narrow_terminal(self) -> None:
        """Test rendering in narrow terminal uses compact format."""
        status = StatusBar(model="gpt-4", status="Ready")
        result = status.render(30)
        assert len(result) <= 30 or "..." in result

    def test_render_very_narrow(self) -> None:
        """Test rendering in very narrow terminal."""
        status = StatusBar(model="claude-3-opus", status="Ready")
        result = status.render(15)
        # Should truncate to fit
        assert len(result) <= 15 or "..." in result

    def test_render_wide_terminal(self) -> None:
        """Test rendering fills width appropriately."""
        status = StatusBar()
        result = status.render(120)
        # Should have padding
        assert len(result) > 0

    def test_format_for_prompt_toolkit(self) -> None:
        """Test formatting for prompt_toolkit toolbar."""
        status = StatusBar(
            model="gpt-4",
            tokens_used=5000,
            tokens_max=128000,
            mode="Normal",
            status="Ready",
        )
        result = status.format_for_prompt_toolkit()
        assert "gpt-4" in result
        assert "5,000" in result
        assert "128,000" in result
        assert "Normal" in result
        assert "Ready" in result

    def test_format_invisible_prompt_toolkit(self) -> None:
        """Test formatting for prompt_toolkit when invisible."""
        status = StatusBar(visible=False)
        result = status.format_for_prompt_toolkit()
        assert result == ""


class TestStatusBarTokenFormatting:
    """Tests for token number formatting."""

    def test_format_thousands_separator(self) -> None:
        """Test that large numbers have thousand separators."""
        status = StatusBar(tokens_used=1234567, tokens_max=10000000)
        result = status.render(100)
        assert "1,234,567" in result
        assert "10,000,000" in result

    def test_format_small_numbers(self) -> None:
        """Test that small numbers are formatted correctly."""
        status = StatusBar(tokens_used=100, tokens_max=1000)
        result = status.render(80)
        assert "100" in result
        assert "1,000" in result


class TestStatusBarObserverInterface:
    """Tests for StatusBarObserver interface."""

    def test_default_implementation(self) -> None:
        """Test that default implementation does nothing."""
        observer = StatusBarObserver()
        status = StatusBar()
        # Should not raise
        observer.on_status_changed(status)


class TestStatusBarThinking:
    """Tests for thinking mode functionality."""

    def test_default_thinking_disabled(self) -> None:
        """Test that thinking is disabled by default."""
        status = StatusBar()
        assert status.thinking_enabled is False

    def test_set_thinking_enabled(self) -> None:
        """Test setting thinking mode."""
        status = StatusBar()
        status.set_thinking(True)
        assert status.thinking_enabled is True

    def test_set_thinking_disabled(self) -> None:
        """Test disabling thinking mode."""
        status = StatusBar(thinking_enabled=True)
        status.set_thinking(False)
        assert status.thinking_enabled is False

    def test_set_thinking_notifies(self) -> None:
        """Test that set_thinking notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_thinking(True)
        assert observer.call_count == 1

    def test_set_thinking_no_notify_if_same(self) -> None:
        """Test that set_thinking doesn't notify if unchanged."""
        status = StatusBar(thinking_enabled=True)
        observer = MockObserver()
        status.add_observer(observer)
        status.set_thinking(True)
        assert observer.call_count == 0

    def test_toggle_thinking_from_off(self) -> None:
        """Test toggling thinking from off to on."""
        status = StatusBar()
        result = status.toggle_thinking()
        assert result is True
        assert status.thinking_enabled is True

    def test_toggle_thinking_from_on(self) -> None:
        """Test toggling thinking from on to off."""
        status = StatusBar(thinking_enabled=True)
        result = status.toggle_thinking()
        assert result is False
        assert status.thinking_enabled is False

    def test_toggle_thinking_notifies(self) -> None:
        """Test that toggle_thinking notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.toggle_thinking()
        assert observer.call_count == 1

    def test_format_prompt_toolkit_with_thinking_off(self) -> None:
        """Test format includes thinking state when off."""
        status = StatusBar(model="gpt-4", thinking_enabled=False)
        result = status.format_for_prompt_toolkit()
        assert "Thinking: Off" in result

    def test_format_prompt_toolkit_with_thinking_on(self) -> None:
        """Test format includes thinking state when on."""
        status = StatusBar(model="gpt-4", thinking_enabled=True)
        result = status.format_for_prompt_toolkit()
        assert "Thinking: On" in result

    def test_format_input_hints(self) -> None:
        """Test input hints format."""
        status = StatusBar()
        result = status.format_input_hints()
        assert "Tab autocomplete" in result
        assert "Shift+Tab thinking" in result
        assert "? help" in result

    def test_format_input_hints_thinking_off(self) -> None:
        """Test input hints show thinking state off."""
        status = StatusBar(thinking_enabled=False)
        result = status.format_input_hints()
        assert "(off)" in result

    def test_format_input_hints_thinking_on(self) -> None:
        """Test input hints show thinking state on."""
        status = StatusBar(thinking_enabled=True)
        result = status.format_input_hints()
        assert "(on)" in result


class TestContextWarningLevel:
    """Tests for ContextWarningLevel enum."""

    def test_values(self) -> None:
        """Test warning level values."""
        assert ContextWarningLevel.NONE.value == "none"
        assert ContextWarningLevel.CAUTION.value == "caution"
        assert ContextWarningLevel.CRITICAL.value == "critical"


class TestStatusBarWarningLevel:
    """Tests for StatusBar warning level functionality."""

    def test_default_warning_level(self) -> None:
        """Test default warning level is NONE."""
        status = StatusBar()
        assert status.warning_level == ContextWarningLevel.NONE

    def test_set_warning_level(self) -> None:
        """Test setting warning level."""
        status = StatusBar()
        status.set_warning_level(ContextWarningLevel.CAUTION)
        assert status.warning_level == ContextWarningLevel.CAUTION

    def test_set_warning_level_critical(self) -> None:
        """Test setting critical warning level."""
        status = StatusBar()
        status.set_warning_level(ContextWarningLevel.CRITICAL)
        assert status.warning_level == ContextWarningLevel.CRITICAL

    def test_set_warning_level_notifies(self) -> None:
        """Test that set_warning_level notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_warning_level(ContextWarningLevel.CAUTION)
        assert observer.call_count == 1

    def test_set_warning_level_no_notify_if_same(self) -> None:
        """Test that set_warning_level doesn't notify if unchanged."""
        status = StatusBar(warning_level=ContextWarningLevel.CAUTION)
        observer = MockObserver()
        status.add_observer(observer)
        status.set_warning_level(ContextWarningLevel.CAUTION)
        assert observer.call_count == 0

    def test_render_with_warning(self) -> None:
        """Test rendering includes warning indicator."""
        status = StatusBar(
            model="gpt-4",
            tokens_used=8000,
            tokens_max=10000,
            warning_level=ContextWarningLevel.CAUTION,
        )
        result = status.render(100)
        assert "[CAUTION]" in result

    def test_render_with_critical_warning(self) -> None:
        """Test rendering includes critical warning indicator."""
        status = StatusBar(
            model="gpt-4",
            tokens_used=9500,
            tokens_max=10000,
            warning_level=ContextWarningLevel.CRITICAL,
        )
        result = status.render(100)
        assert "[!CRITICAL!]" in result

    def test_render_no_warning_indicator_when_none(self) -> None:
        """Test no warning indicator when level is NONE."""
        status = StatusBar(
            model="gpt-4",
            tokens_used=1000,
            tokens_max=10000,
            warning_level=ContextWarningLevel.NONE,
        )
        result = status.render(100)
        assert "[CAUTION]" not in result
        assert "[!CRITICAL!]" not in result

    def test_format_prompt_toolkit_with_warning(self) -> None:
        """Test prompt_toolkit format includes warning."""
        status = StatusBar(
            model="gpt-4",
            warning_level=ContextWarningLevel.CAUTION,
        )
        result = status.format_for_prompt_toolkit()
        assert "[CAUTION]" in result

    def test_format_prompt_toolkit_with_critical(self) -> None:
        """Test prompt_toolkit format includes critical warning."""
        status = StatusBar(
            model="gpt-4",
            warning_level=ContextWarningLevel.CRITICAL,
        )
        result = status.format_for_prompt_toolkit()
        assert "[!CRITICAL!]" in result


class TestStatusBarCompressionInfo:
    """Tests for StatusBar compression info functionality."""

    def test_default_compression_info(self) -> None:
        """Test default compression info is empty."""
        status = StatusBar()
        assert status.last_compression == ""

    def test_set_compression_info(self) -> None:
        """Test setting compression info."""
        status = StatusBar()
        status.set_compression_info("Context truncated: 5 messages removed")
        assert status.last_compression == "Context truncated: 5 messages removed"

    def test_set_compression_info_notifies(self) -> None:
        """Test that set_compression_info notifies observers."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.set_compression_info("Context truncated")
        assert observer.call_count == 1

    def test_set_compression_info_no_notify_if_same(self) -> None:
        """Test that set_compression_info doesn't notify if unchanged."""
        status = StatusBar(last_compression="Context truncated")
        observer = MockObserver()
        status.add_observer(observer)
        status.set_compression_info("Context truncated")
        assert observer.call_count == 0

    def test_clear_compression_info(self) -> None:
        """Test clearing compression info."""
        status = StatusBar(last_compression="Context truncated")
        status.clear_compression_info()
        assert status.last_compression == ""

    def test_clear_compression_info_notifies(self) -> None:
        """Test that clear_compression_info notifies observers."""
        status = StatusBar(last_compression="Context truncated")
        observer = MockObserver()
        status.add_observer(observer)
        status.clear_compression_info()
        assert observer.call_count == 1

    def test_clear_compression_info_no_notify_if_empty(self) -> None:
        """Test that clear doesn't notify if already empty."""
        status = StatusBar()
        observer = MockObserver()
        status.add_observer(observer)
        status.clear_compression_info()
        assert observer.call_count == 0


class TestStatusBarUsagePercentage:
    """Tests for StatusBar usage percentage property."""

    def test_usage_percentage_zero(self) -> None:
        """Test usage percentage when zero tokens used."""
        status = StatusBar(tokens_used=0, tokens_max=10000)
        assert status.usage_percentage == 0.0

    def test_usage_percentage_half(self) -> None:
        """Test usage percentage at 50%."""
        status = StatusBar(tokens_used=5000, tokens_max=10000)
        assert status.usage_percentage == 50.0

    def test_usage_percentage_full(self) -> None:
        """Test usage percentage at 100%."""
        status = StatusBar(tokens_used=10000, tokens_max=10000)
        assert status.usage_percentage == 100.0

    def test_usage_percentage_zero_max(self) -> None:
        """Test usage percentage when max is zero."""
        status = StatusBar(tokens_used=1000, tokens_max=0)
        assert status.usage_percentage == 0.0
