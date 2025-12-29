"""Diff presenter for Code-Forge CLI.

This module provides visual diff display for file edit operations,
showing what changed in a colored, easy-to-read format.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


class DiffStyle(str, Enum):
    """Style options for diff display."""

    UNIFIED = "unified"  # Standard unified diff format
    SIDE_BY_SIDE = "side_by_side"  # Side-by-side comparison
    INLINE = "inline"  # Inline with highlights
    MINIMAL = "minimal"  # Just show changed lines


@dataclass
class DiffLine:
    """A single line in a diff.

    Attributes:
        content: The line content.
        line_type: Type of change (+, -, or space for context).
        old_line_no: Line number in old file (None for additions).
        new_line_no: Line number in new file (None for deletions).
    """

    content: str
    line_type: str  # '+', '-', ' ', or '@' for hunk header
    old_line_no: int | None = None
    new_line_no: int | None = None


class DiffPresenter:
    """Presents file diffs in a visually appealing format.

    Uses Rich library for colored output showing:
    - Removed lines in red with - prefix
    - Added lines in green with + prefix
    - Context lines in dim
    - Line numbers for navigation
    """

    # Default number of context lines around changes
    DEFAULT_CONTEXT = 3

    # Maximum lines to show in a diff (to avoid overwhelming output)
    MAX_DIFF_LINES = 100

    def __init__(
        self,
        console: Console | None = None,
        style: DiffStyle = DiffStyle.UNIFIED,
        context_lines: int = DEFAULT_CONTEXT,
        show_line_numbers: bool = True,
        max_lines: int = MAX_DIFF_LINES,
    ) -> None:
        """Initialize the diff presenter.

        Args:
            console: Rich console for output (creates one if not provided).
            style: Diff display style.
            context_lines: Number of context lines around changes.
            show_line_numbers: Whether to show line numbers.
            max_lines: Maximum lines to display.
        """
        if console is None:
            from rich.console import Console
            console = Console()
        self._console = console
        self._style = style
        self._context_lines = context_lines
        self._show_line_numbers = show_line_numbers
        self._max_lines = max_lines

    def show_diff(
        self,
        old_content: str,
        new_content: str,
        filename: str = "file",
        title: str | None = None,
    ) -> None:
        """Display a diff between old and new content.

        Args:
            old_content: Original file content.
            new_content: New file content after edit.
            filename: Name of the file being edited.
            title: Optional title for the diff display.
        """
        if old_content == new_content:
            self._console.print("[dim]No changes[/dim]")
            return

        diff_lines = self._generate_diff(old_content, new_content)

        if not diff_lines:
            self._console.print("[dim]No changes[/dim]")
            return

        # Show header
        if title:
            self._console.print(f"[bold]{title}[/bold]")
        self._console.print(f"[dim]─── Changes to [cyan]{filename}[/cyan] ───[/dim]")

        # Render based on style
        if self._style == DiffStyle.UNIFIED:
            self._render_unified(diff_lines)
        elif self._style == DiffStyle.MINIMAL:
            self._render_minimal(diff_lines)
        else:
            # Default to unified for unsupported styles
            self._render_unified(diff_lines)

        self._console.print("[dim]───────────────────────────────[/dim]")

    def format_diff(
        self,
        old_content: str,
        new_content: str,
        filename: str = "file",
    ) -> str:
        """Format a diff as a string without printing.

        Args:
            old_content: Original file content.
            new_content: New file content after edit.
            filename: Name of the file being edited.

        Returns:
            Formatted diff string.
        """
        if old_content == new_content:
            return "(no changes)"

        diff_lines = self._generate_diff(old_content, new_content)

        if not diff_lines:
            return "(no changes)"

        lines: list[str] = []
        lines.append(f"─── Changes to {filename} ───")

        for diff_line in diff_lines[:self._max_lines]:
            if diff_line.line_type == "+":
                lines.append(f"+ {diff_line.content}")
            elif diff_line.line_type == "-":
                lines.append(f"- {diff_line.content}")
            elif diff_line.line_type == "@":
                lines.append(f"@@ {diff_line.content} @@")
            else:
                lines.append(f"  {diff_line.content}")

        if len(diff_lines) > self._max_lines:
            lines.append(f"... ({len(diff_lines) - self._max_lines} more lines)")

        lines.append("───────────────────────────────")
        return "\n".join(lines)

    def get_change_summary(
        self,
        old_content: str,
        new_content: str,
    ) -> dict[str, int]:
        """Get a summary of changes.

        Args:
            old_content: Original content.
            new_content: New content.

        Returns:
            Dictionary with additions, deletions, and modifications counts.
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

        additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

        return {
            "additions": additions,
            "deletions": deletions,
            "total_changes": additions + deletions,
            "old_lines": len(old_lines),
            "new_lines": len(new_lines),
        }

    def _generate_diff(
        self,
        old_content: str,
        new_content: str,
    ) -> list[DiffLine]:
        """Generate diff lines from content.

        Args:
            old_content: Original content.
            new_content: New content.

        Returns:
            List of DiffLine objects.
        """
        old_lines = old_content.splitlines(keepends=False)
        new_lines = new_content.splitlines(keepends=False)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm="",
            n=self._context_lines,
        )

        result: list[DiffLine] = []
        old_line_no = 0
        new_line_no = 0

        for line in diff:
            if line.startswith("---") or line.startswith("+++"):
                # Skip file headers
                continue
            elif line.startswith("@@"):
                # Parse hunk header for line numbers
                # Format: @@ -start,count +start,count @@
                result.append(DiffLine(
                    content=line,
                    line_type="@",
                ))
                # Extract starting line numbers
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        old_part = parts[1]  # -start,count
                        new_part = parts[2]  # +start,count
                        old_line_no = int(old_part.split(",")[0].lstrip("-")) - 1
                        new_line_no = int(new_part.split(",")[0].lstrip("+")) - 1
                    except (ValueError, IndexError):
                        pass
            elif line.startswith("-"):
                old_line_no += 1
                result.append(DiffLine(
                    content=line[1:],  # Remove the - prefix
                    line_type="-",
                    old_line_no=old_line_no,
                ))
            elif line.startswith("+"):
                new_line_no += 1
                result.append(DiffLine(
                    content=line[1:],  # Remove the + prefix
                    line_type="+",
                    new_line_no=new_line_no,
                ))
            else:
                # Context line
                old_line_no += 1
                new_line_no += 1
                content = line[1:] if line.startswith(" ") else line
                result.append(DiffLine(
                    content=content,
                    line_type=" ",
                    old_line_no=old_line_no,
                    new_line_no=new_line_no,
                ))

        return result

    def _render_unified(self, diff_lines: list[DiffLine]) -> None:
        """Render diff in unified format.

        Args:
            diff_lines: List of diff lines to render.
        """
        for idx, diff_line in enumerate(diff_lines):
            if idx >= self._max_lines:
                remaining = len(diff_lines) - idx
                self._console.print(f"[dim]... ({remaining} more lines)[/dim]")
                break

            if diff_line.line_type == "@":
                # Hunk header
                self._console.print(f"[cyan]{diff_line.content}[/cyan]")
            elif diff_line.line_type == "-":
                # Deleted line
                line_no = ""
                if self._show_line_numbers and diff_line.old_line_no:
                    line_no = f"[dim]{diff_line.old_line_no:4d}[/dim] "
                self._console.print(f"{line_no}[red]- {diff_line.content}[/red]")
            elif diff_line.line_type == "+":
                # Added line
                line_no = ""
                if self._show_line_numbers and diff_line.new_line_no:
                    line_no = f"[dim]{diff_line.new_line_no:4d}[/dim] "
                self._console.print(f"{line_no}[green]+ {diff_line.content}[/green]")
            else:
                # Context line
                line_no = ""
                if self._show_line_numbers and diff_line.new_line_no:
                    line_no = f"[dim]{diff_line.new_line_no:4d}[/dim] "
                self._console.print(f"{line_no}[dim]  {diff_line.content}[/dim]")

    def _render_minimal(self, diff_lines: list[DiffLine]) -> None:
        """Render diff showing only changed lines.

        Args:
            diff_lines: List of diff lines to render.
        """
        # Filter to only changed lines
        changed_lines = [d for d in diff_lines if d.line_type in ("+", "-")]

        for idx, diff_line in enumerate(changed_lines):
            if idx >= self._max_lines:
                remaining = len(changed_lines) - idx
                self._console.print(f"[dim]... ({remaining} more lines)[/dim]")
                break

            if diff_line.line_type == "-":
                self._console.print(f"[red]- {diff_line.content}[/red]")
            else:
                self._console.print(f"[green]+ {diff_line.content}[/green]")


def show_edit_diff(
    console: Console,
    old_content: str,
    new_content: str,
    filename: str,
) -> None:
    """Convenience function to show a diff for an edit operation.

    Args:
        console: Rich console for output.
        old_content: Original file content.
        new_content: New file content.
        filename: Name of the edited file.
    """
    presenter = DiffPresenter(console=console, style=DiffStyle.UNIFIED)
    presenter.show_diff(old_content, new_content, filename)


def format_change_summary(
    old_content: str,
    new_content: str,
) -> str:
    """Format a brief change summary.

    Args:
        old_content: Original content.
        new_content: New content.

    Returns:
        Brief summary string like "+5 -3 lines".
    """
    presenter = DiffPresenter()
    summary = presenter.get_change_summary(old_content, new_content)

    parts = []
    if summary["additions"] > 0:
        parts.append(f"+{summary['additions']}")
    if summary["deletions"] > 0:
        parts.append(f"-{summary['deletions']}")

    if not parts:
        return "no changes"

    return " ".join(parts) + " lines"
