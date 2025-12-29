"""Status bar for Code-Forge CLI.

This module provides the StatusBar class for displaying runtime information
at the bottom of the terminal, including model, tokens, mode, and status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ContextWarningLevel(str, Enum):
    """Warning levels for context usage."""

    NONE = "none"  # Below 80%
    CAUTION = "caution"  # 80-90%
    CRITICAL = "critical"  # 90%+


@dataclass
class StatusBar:
    """Status bar displayed at bottom of terminal.

    The status bar shows current model, token usage, operating mode,
    and status information in a formatted line.

    Attributes:
        model: Current model name.
        tokens_used: Number of tokens used.
        tokens_max: Maximum tokens available.
        mode: Current operating mode.
        status: Current status text.
        visible: Whether status bar is visible.
        thinking_enabled: Whether extended thinking is enabled.
        warning_level: Current context usage warning level.
        last_compression: Description of last compression event.
    """

    model: str = ""
    tokens_used: int = 0
    tokens_max: int = 128000
    mode: str = "Normal"
    status: str = "Ready"
    visible: bool = True
    thinking_enabled: bool = False
    warning_level: ContextWarningLevel = ContextWarningLevel.NONE
    last_compression: str = ""
    _observers: list[StatusBarObserver] = field(default_factory=list, repr=False)

    def set_model(self, model: str) -> None:
        """Update current model.

        Args:
            model: New model name.
        """
        if model != self.model:
            self.model = model
            self._notify()

    def set_tokens(self, used: int, max_tokens: int | None = None) -> None:
        """Update token counts.

        Args:
            used: Number of tokens used.
            max_tokens: Maximum tokens (optional).
        """
        changed = self.tokens_used != used
        self.tokens_used = used
        if max_tokens is not None and self.tokens_max != max_tokens:
            self.tokens_max = max_tokens
            changed = True
        if changed:
            self._notify()

    def set_mode(self, mode: str) -> None:
        """Update operating mode.

        Args:
            mode: New mode name.
        """
        if mode != self.mode:
            self.mode = mode
            self._notify()

    def set_status(self, status: str) -> None:
        """Update status text.

        Args:
            status: New status text.
        """
        if status != self.status:
            self.status = status
            self._notify()

    def set_visible(self, visible: bool) -> None:
        """Set status bar visibility.

        Args:
            visible: Whether to show status bar.
        """
        if visible != self.visible:
            self.visible = visible
            self._notify()

    def set_thinking(self, enabled: bool) -> None:
        """Set extended thinking mode.

        Args:
            enabled: Whether thinking mode is enabled.
        """
        if enabled != self.thinking_enabled:
            self.thinking_enabled = enabled
            self._notify()

    def toggle_thinking(self) -> bool:
        """Toggle extended thinking mode.

        Returns:
            New thinking mode state.
        """
        self.thinking_enabled = not self.thinking_enabled
        self._notify()
        return self.thinking_enabled

    def set_warning_level(self, level: ContextWarningLevel) -> None:
        """Set context usage warning level.

        Args:
            level: New warning level.
        """
        if level != self.warning_level:
            self.warning_level = level
            self._notify()

    def set_compression_info(self, info: str) -> None:
        """Set last compression event description.

        Args:
            info: Description of compression event.
        """
        if info != self.last_compression:
            self.last_compression = info
            self._notify()

    def clear_compression_info(self) -> None:
        """Clear the compression info after display."""
        if self.last_compression:
            self.last_compression = ""
            self._notify()

    @property
    def usage_percentage(self) -> float:
        """Calculate current usage percentage.

        Returns:
            Usage as percentage (0-100).
        """
        if self.tokens_max == 0:
            return 0.0
        return (self.tokens_used / self.tokens_max) * 100

    def add_observer(self, observer: StatusBarObserver) -> None:
        """Add an observer to be notified of changes.

        Args:
            observer: Observer to add.
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: StatusBarObserver) -> None:
        """Remove an observer.

        Args:
            observer: Observer to remove.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify(self) -> None:
        """Notify all observers of a change."""
        for observer in self._observers:
            observer.on_status_changed(self)

    def _get_warning_indicator(self) -> str:
        """Get warning indicator text based on warning level.

        Returns:
            Warning indicator string or empty string.
        """
        if self.warning_level == ContextWarningLevel.CRITICAL:
            return "[!CRITICAL!]"
        elif self.warning_level == ContextWarningLevel.CAUTION:
            return "[CAUTION]"
        return ""

    def _format_tokens_with_warning(self) -> str:
        """Format token display with optional warning indicator.

        Returns:
            Formatted token string.
        """
        base = f"Tokens: {self.tokens_used:,}/{self.tokens_max:,}"
        warning = self._get_warning_indicator()
        if warning:
            return f"{base} {warning}"
        return base

    def render(self, width: int) -> str:
        """Render status bar to string.

        Creates a formatted status bar string with left, center, and right
        sections that fits within the given width.

        Args:
            width: Terminal width in characters.

        Returns:
            Formatted status bar string, empty if not visible.
        """
        if not self.visible:
            return ""

        if width <= 0:
            return ""

        left = f" {self.model}"
        center = self._format_tokens_with_warning()
        right = f"{self.mode} | {self.status} "

        total_content = len(left) + len(center) + len(right)

        # If content won't fit, use compact format
        if total_content >= width:
            return self._render_compact(width)

        # Calculate padding for centered layout
        left_pad = (width - len(center)) // 2 - len(left)
        left_pad = max(left_pad, 1)

        right_pad = width - len(left) - left_pad - len(center) - len(right)
        right_pad = max(right_pad, 1)

        return f"{left}{' ' * left_pad}{center}{' ' * right_pad}{right}"

    def _render_compact(self, width: int) -> str:
        """Render compact status bar for narrow terminals.

        Args:
            width: Terminal width.

        Returns:
            Compact status bar string.
        """
        if width < 20:
            return f" {self.model[:width - 2]}"

        # Model and status only
        compact = f" {self.model} | {self.status} "
        if len(compact) <= width:
            return compact

        # Just model
        return f" {self.model[:width - 4]}... "

    def format_for_prompt_toolkit(self) -> str:
        """Format status bar for prompt_toolkit bottom_toolbar.

        Returns:
            Status bar text formatted for prompt_toolkit.
        """
        if not self.visible:
            return ""

        thinking_indicator = "Thinking: On" if self.thinking_enabled else "Thinking: Off"
        tokens_display = self._format_tokens_with_warning()

        # Add compression indicator if present
        compression_display = ""
        if self.last_compression:
            compression_display = f"  |  [Compressed] {self.last_compression}"

        return (
            f" {self.model}  |  "
            f"{tokens_display}  |  "
            f"{thinking_indicator}  |  "
            f"{self.mode}  |  {self.status}{compression_display} "
        )

    def format_input_hints(self) -> str:
        """Format input hints bar for display below the prompt.

        Shows keyboard hints like 'Tab accepts' and 'Shift+Tab thinking'.

        Returns:
            Input hints text.
        """
        thinking_state = "on" if self.thinking_enabled else "off"
        return f"Tab autocomplete  |  Shift+Tab thinking ({thinking_state})  |  ? help"


class StatusBarObserver:
    """Interface for status bar change observers.

    Implement this interface to receive notifications when the
    status bar content changes.
    """

    def on_status_changed(self, status_bar: StatusBar) -> None:
        """Called when status bar content changes.

        Args:
            status_bar: The updated status bar.
        """
        pass  # Default implementation does nothing
