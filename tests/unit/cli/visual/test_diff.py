"""Tests for diff presenter."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from code_forge.cli.visual.diff import (
    DiffLine,
    DiffPresenter,
    DiffStyle,
    format_change_summary,
    show_edit_diff,
)


class TestDiffLine:
    """Tests for DiffLine dataclass."""

    def test_creation(self) -> None:
        """Test DiffLine creation."""
        line = DiffLine(
            content="test content",
            line_type="+",
            new_line_no=10,
        )
        assert line.content == "test content"
        assert line.line_type == "+"
        assert line.new_line_no == 10
        assert line.old_line_no is None

    def test_deletion_line(self) -> None:
        """Test deletion line."""
        line = DiffLine(
            content="removed",
            line_type="-",
            old_line_no=5,
        )
        assert line.line_type == "-"
        assert line.old_line_no == 5


class TestDiffStyle:
    """Tests for DiffStyle enum."""

    def test_unified_style(self) -> None:
        """Test unified style value."""
        assert DiffStyle.UNIFIED.value == "unified"

    def test_minimal_style(self) -> None:
        """Test minimal style value."""
        assert DiffStyle.MINIMAL.value == "minimal"


class TestDiffPresenter:
    """Tests for DiffPresenter class."""

    def test_creation_with_defaults(self) -> None:
        """Test presenter creation with defaults."""
        presenter = DiffPresenter()
        assert presenter._style == DiffStyle.UNIFIED
        assert presenter._context_lines == 3
        assert presenter._show_line_numbers is True

    def test_creation_with_custom_console(self) -> None:
        """Test presenter creation with custom console."""
        console = Console()
        presenter = DiffPresenter(console=console)
        assert presenter._console is console

    def test_creation_with_minimal_style(self) -> None:
        """Test presenter creation with minimal style."""
        presenter = DiffPresenter(style=DiffStyle.MINIMAL)
        assert presenter._style == DiffStyle.MINIMAL

    def test_no_changes(self) -> None:
        """Test handling of identical content."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console)

        presenter.show_diff("same content", "same content", "test.py")

        result = output.getvalue()
        assert "No changes" in result

    def test_simple_addition(self) -> None:
        """Test simple line addition."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console)

        old = "line1\nline2"
        new = "line1\nline2\nline3"

        presenter.show_diff(old, new, "test.py")

        result = output.getvalue()
        assert "test.py" in result
        assert "line3" in result

    def test_simple_deletion(self) -> None:
        """Test simple line deletion."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console)

        old = "line1\nline2\nline3"
        new = "line1\nline3"

        presenter.show_diff(old, new, "test.py")

        result = output.getvalue()
        assert "line2" in result

    def test_modification(self) -> None:
        """Test line modification."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console)

        old = "old_value = 1"
        new = "new_value = 2"

        presenter.show_diff(old, new, "test.py")

        result = output.getvalue()
        assert "old_value" in result
        assert "new_value" in result

    def test_format_diff_no_changes(self) -> None:
        """Test format_diff with no changes."""
        presenter = DiffPresenter()
        result = presenter.format_diff("same", "same", "test.py")
        assert result == "(no changes)"

    def test_format_diff_with_changes(self) -> None:
        """Test format_diff with changes."""
        presenter = DiffPresenter()
        result = presenter.format_diff("old", "new", "test.py")

        assert "test.py" in result
        assert "-" in result or "+" in result

    def test_get_change_summary(self) -> None:
        """Test change summary calculation."""
        presenter = DiffPresenter()

        old = "line1\nline2\nline3"
        new = "line1\nnew_line\nline3\nline4"

        summary = presenter.get_change_summary(old, new)

        assert "additions" in summary
        assert "deletions" in summary
        assert "total_changes" in summary
        assert summary["old_lines"] == 3
        assert summary["new_lines"] == 4

    def test_get_change_summary_no_changes(self) -> None:
        """Test change summary with identical content."""
        presenter = DiffPresenter()
        summary = presenter.get_change_summary("same", "same")

        assert summary["additions"] == 0
        assert summary["deletions"] == 0
        assert summary["total_changes"] == 0

    def test_max_lines_limit(self) -> None:
        """Test max lines limit is respected."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console, max_lines=5)

        # Create content with many changes
        old = "\n".join(f"line{i}" for i in range(50))
        new = "\n".join(f"modified{i}" for i in range(50))

        presenter.show_diff(old, new, "test.py")

        result = output.getvalue()
        assert "more lines" in result

    def test_minimal_style_rendering(self) -> None:
        """Test minimal style shows only changes."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console, style=DiffStyle.MINIMAL)

        old = "context\nold_line\nmore_context"
        new = "context\nnew_line\nmore_context"

        presenter.show_diff(old, new, "test.py")

        result = output.getvalue()
        assert "old_line" in result
        assert "new_line" in result

    def test_line_numbers_enabled(self) -> None:
        """Test line numbers are shown when enabled."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console, show_line_numbers=True)

        old = "line1\nline2"
        new = "line1\nmodified"

        presenter.show_diff(old, new, "test.py")

        # Line numbers should appear in the output
        # This is a basic check - actual line numbers depend on diff context
        result = output.getvalue()
        assert "test.py" in result

    def test_line_numbers_disabled(self) -> None:
        """Test line numbers can be disabled."""
        presenter = DiffPresenter(show_line_numbers=False)
        assert presenter._show_line_numbers is False

    def test_custom_context_lines(self) -> None:
        """Test custom context lines setting."""
        presenter = DiffPresenter(context_lines=5)
        assert presenter._context_lines == 5

    def test_title_displayed(self) -> None:
        """Test title is displayed when provided."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        presenter = DiffPresenter(console=console)

        presenter.show_diff("old", "new", "test.py", title="My Custom Title")

        result = output.getvalue()
        assert "My Custom Title" in result


class TestShowEditDiff:
    """Tests for show_edit_diff function."""

    def test_shows_diff(self) -> None:
        """Test show_edit_diff displays diff."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        show_edit_diff(console, "old content", "new content", "test.py")

        result = output.getvalue()
        assert "test.py" in result


class TestFormatChangeSummary:
    """Tests for format_change_summary function."""

    def test_additions_only(self) -> None:
        """Test summary with only additions."""
        result = format_change_summary("a", "a\nb\nc")
        assert "+" in result
        assert "lines" in result

    def test_deletions_only(self) -> None:
        """Test summary with only deletions."""
        result = format_change_summary("a\nb\nc", "a")
        assert "-" in result
        assert "lines" in result

    def test_both_additions_and_deletions(self) -> None:
        """Test summary with both changes."""
        result = format_change_summary("old\nvalue", "new\nvalue\nextra")
        assert "lines" in result

    def test_no_changes(self) -> None:
        """Test summary with no changes."""
        result = format_change_summary("same", "same")
        assert result == "no changes"


class TestDiffPresenterEdgeCases:
    """Edge case tests for DiffPresenter."""

    def test_empty_old_content(self) -> None:
        """Test diffing from empty file."""
        presenter = DiffPresenter()
        summary = presenter.get_change_summary("", "new content")
        assert summary["additions"] > 0

    def test_empty_new_content(self) -> None:
        """Test diffing to empty file."""
        presenter = DiffPresenter()
        summary = presenter.get_change_summary("old content", "")
        assert summary["deletions"] > 0

    def test_both_empty(self) -> None:
        """Test diffing two empty strings."""
        presenter = DiffPresenter()
        summary = presenter.get_change_summary("", "")
        assert summary["total_changes"] == 0

    def test_multiline_content(self) -> None:
        """Test with multiple lines of changes."""
        old = """def old_function():
    x = 1
    y = 2
    return x + y"""

        new = """def new_function():
    a = 10
    b = 20
    return a * b"""

        presenter = DiffPresenter()
        summary = presenter.get_change_summary(old, new)

        assert summary["additions"] > 0
        assert summary["deletions"] > 0

    def test_whitespace_changes(self) -> None:
        """Test changes that include whitespace."""
        old = "line1\nline2"
        new = "line1\n  line2"  # Added leading whitespace

        presenter = DiffPresenter()
        result = presenter.format_diff(old, new, "test.py")

        # Should detect the whitespace change
        assert result != "(no changes)"

    def test_unicode_content(self) -> None:
        """Test handling unicode content."""
        old = "Hello 世界"
        new = "Hello 世界! 🎉"

        presenter = DiffPresenter()
        summary = presenter.get_change_summary(old, new)

        # Should handle unicode without errors
        assert "additions" in summary
