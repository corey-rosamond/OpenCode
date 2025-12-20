"""Tests for CLI theme definitions."""

from __future__ import annotations

import pytest

from code_forge.cli.themes import (
    DARK_THEME,
    LIGHT_THEME,
    Theme,
    ThemeRegistry,
)


class TestTheme:
    """Tests for Theme dataclass."""

    def test_theme_creation(self) -> None:
        """Test creating a theme with all attributes."""
        theme = Theme(
            name="test",
            background="#000000",
            foreground="#ffffff",
            accent="#0000ff",
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            dim="#888888",
            status_bar_bg="#111111",
            status_bar_fg="#eeeeee",
        )
        assert theme.name == "test"
        assert theme.background == "#000000"
        assert theme.foreground == "#ffffff"
        assert theme.accent == "#0000ff"

    def test_theme_is_frozen(self) -> None:
        """Test that themes are immutable."""
        with pytest.raises(AttributeError):
            DARK_THEME.name = "modified"  # type: ignore[misc]

    def test_theme_to_dict(self) -> None:
        """Test converting theme to dictionary."""
        result = DARK_THEME.to_dict()
        assert isinstance(result, dict)
        assert "background" in result
        assert "foreground" in result
        assert "accent" in result
        assert "success" in result
        assert "warning" in result
        assert "error" in result
        assert "dim" in result
        assert "status_bar_bg" in result
        assert "status_bar_fg" in result
        # Name is not in dict
        assert "name" not in result

    def test_theme_to_dict_values(self) -> None:
        """Test that to_dict returns correct values."""
        result = DARK_THEME.to_dict()
        assert result["background"] == DARK_THEME.background
        assert result["foreground"] == DARK_THEME.foreground
        assert result["accent"] == DARK_THEME.accent

    def test_theme_to_prompt_toolkit_style(self) -> None:
        """Test converting theme to prompt_toolkit style."""
        result = DARK_THEME.to_prompt_toolkit_style()
        assert isinstance(result, dict)
        assert "" in result  # Default style
        assert "prompt" in result
        assert "continuation" in result
        assert "bottom-toolbar" in result

    def test_theme_prompt_style_contains_colors(self) -> None:
        """Test that prompt style uses theme colors."""
        result = DARK_THEME.to_prompt_toolkit_style()
        assert DARK_THEME.accent in result["prompt"]
        assert DARK_THEME.dim in result["continuation"]
        assert DARK_THEME.status_bar_bg in result["bottom-toolbar"]


class TestBuiltInThemes:
    """Tests for built-in theme definitions."""

    def test_dark_theme_exists(self) -> None:
        """Test DARK_THEME is defined."""
        assert isinstance(DARK_THEME, Theme)
        assert DARK_THEME.name == "dark"

    def test_light_theme_exists(self) -> None:
        """Test LIGHT_THEME is defined."""
        assert isinstance(LIGHT_THEME, Theme)
        assert LIGHT_THEME.name == "light"

    def test_dark_theme_has_all_colors(self) -> None:
        """Test DARK_THEME has all required colors."""
        assert DARK_THEME.background.startswith("#")
        assert DARK_THEME.foreground.startswith("#")
        assert DARK_THEME.accent.startswith("#")
        assert DARK_THEME.success.startswith("#")
        assert DARK_THEME.warning.startswith("#")
        assert DARK_THEME.error.startswith("#")
        assert DARK_THEME.dim.startswith("#")
        assert DARK_THEME.status_bar_bg.startswith("#")
        assert DARK_THEME.status_bar_fg.startswith("#")

    def test_light_theme_has_all_colors(self) -> None:
        """Test LIGHT_THEME has all required colors."""
        assert LIGHT_THEME.background.startswith("#")
        assert LIGHT_THEME.foreground.startswith("#")
        assert LIGHT_THEME.accent.startswith("#")
        assert LIGHT_THEME.success.startswith("#")
        assert LIGHT_THEME.warning.startswith("#")
        assert LIGHT_THEME.error.startswith("#")
        assert LIGHT_THEME.dim.startswith("#")
        assert LIGHT_THEME.status_bar_bg.startswith("#")
        assert LIGHT_THEME.status_bar_fg.startswith("#")

    def test_themes_are_distinct(self) -> None:
        """Test that dark and light themes are different."""
        assert DARK_THEME.background != LIGHT_THEME.background
        assert DARK_THEME.foreground != LIGHT_THEME.foreground


class TestThemeRegistry:
    """Tests for ThemeRegistry."""

    def test_get_dark_theme(self) -> None:
        """Test getting dark theme by name."""
        theme = ThemeRegistry.get("dark")
        assert theme == DARK_THEME

    def test_get_light_theme(self) -> None:
        """Test getting light theme by name."""
        theme = ThemeRegistry.get("light")
        assert theme == LIGHT_THEME

    def test_get_case_insensitive(self) -> None:
        """Test that theme lookup is case-insensitive."""
        assert ThemeRegistry.get("DARK") == DARK_THEME
        assert ThemeRegistry.get("Dark") == DARK_THEME
        assert ThemeRegistry.get("LIGHT") == LIGHT_THEME

    def test_get_with_whitespace(self) -> None:
        """Test that theme lookup strips whitespace."""
        assert ThemeRegistry.get("  dark  ") == DARK_THEME
        assert ThemeRegistry.get("\tlight\n") == LIGHT_THEME

    def test_get_unknown_returns_default(self) -> None:
        """Test that unknown theme name returns default."""
        theme = ThemeRegistry.get("unknown")
        assert theme == ThemeRegistry.get_default()

    def test_get_default(self) -> None:
        """Test getting default theme."""
        default = ThemeRegistry.get_default()
        assert isinstance(default, Theme)

    def test_list_themes(self) -> None:
        """Test listing available themes."""
        themes = ThemeRegistry.list_themes()
        assert isinstance(themes, list)
        assert "dark" in themes
        assert "light" in themes

    def test_register_custom_theme(self) -> None:
        """Test registering a custom theme."""
        custom = Theme(
            name="custom",
            background="#121212",
            foreground="#e0e0e0",
            accent="#bb86fc",
            success="#03dac6",
            warning="#ffc107",
            error="#cf6679",
            dim="#666666",
            status_bar_bg="#1f1f1f",
            status_bar_fg="#e0e0e0",
        )
        ThemeRegistry.register(custom)
        assert ThemeRegistry.get("custom") == custom
        assert "custom" in ThemeRegistry.list_themes()

    def test_register_overwrites_existing(self) -> None:
        """Test that registering with same name overwrites."""
        original = ThemeRegistry.get("dark")
        custom = Theme(
            name="dark",
            background="#000001",
            foreground="#ffffff",
            accent="#0000ff",
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            dim="#888888",
            status_bar_bg="#111111",
            status_bar_fg="#eeeeee",
        )
        ThemeRegistry.register(custom)
        assert ThemeRegistry.get("dark").background == "#000001"
        # Restore original
        ThemeRegistry.register(original)

    def test_set_default(self) -> None:
        """Test setting default theme."""
        original_default = ThemeRegistry._default
        try:
            ThemeRegistry.set_default("light")
            assert ThemeRegistry.get_default() == LIGHT_THEME
        finally:
            ThemeRegistry._default = original_default

    def test_set_default_case_insensitive(self) -> None:
        """Test that set_default is case-insensitive."""
        original_default = ThemeRegistry._default
        try:
            ThemeRegistry.set_default("LIGHT")
            assert ThemeRegistry.get_default() == LIGHT_THEME
        finally:
            ThemeRegistry._default = original_default

    def test_set_default_unknown_raises(self) -> None:
        """Test that setting unknown default raises ValueError."""
        with pytest.raises(ValueError, match="Unknown theme"):
            ThemeRegistry.set_default("nonexistent")
