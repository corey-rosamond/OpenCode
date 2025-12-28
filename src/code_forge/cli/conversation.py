"""Conversational presentation layer for CLI output.

This module provides a natural language wrapper around tool execution events,
making the CLI feel more like a conversation with Claude Code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from rich.console import Console


@dataclass
class ToolDescription:
    """Description for a tool's action and completion messages."""

    action: str  # Present continuous, e.g., "Reading"
    completion: str  # Past/status, e.g., "File contents loaded"
    error: str = "Operation failed"  # Default error message


class ToolDescriptor:
    """Provides natural language descriptions for tools."""

    DESCRIPTIONS: ClassVar[dict[str, ToolDescription]] = {
        "Read": ToolDescription(
            action="Reading",
            completion="File contents loaded",
            error="Could not read file",
        ),
        "Write": ToolDescription(
            action="Writing to",
            completion="File saved",
            error="Could not write file",
        ),
        "Edit": ToolDescription(
            action="Editing",
            completion="Changes applied",
            error="Edit failed",
        ),
        "Bash": ToolDescription(
            action="Running",
            completion="Command completed",
            error="Command failed",
        ),
        "Glob": ToolDescription(
            action="Finding files matching",
            completion="Files found",
            error="Search failed",
        ),
        "Grep": ToolDescription(
            action="Searching for",
            completion="Search complete",
            error="Search failed",
        ),
        "WebSearch": ToolDescription(
            action="Searching the web for",
            completion="Search results ready",
            error="Web search failed",
        ),
        "WebFetch": ToolDescription(
            action="Fetching",
            completion="Page loaded",
            error="Could not fetch URL",
        ),
        "Task": ToolDescription(
            action="Starting task:",
            completion="Task complete",
            error="Task failed",
        ),
        "TodoWrite": ToolDescription(
            action="Updating task list",
            completion="Tasks updated",
            error="Failed to update tasks",
        ),
    }

    @classmethod
    def get_action(cls, tool_name: str, args: dict[str, Any]) -> str:
        """Get the action message for a tool.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Returns:
            Natural language action description.
        """
        desc = cls.DESCRIPTIONS.get(tool_name)
        if not desc:
            return f"Running {tool_name}..."

        # Extract key argument for context
        context = cls._extract_context(tool_name, args)
        if context:
            return f"{desc.action} {context}..."
        return f"{desc.action}..."

    @classmethod
    def get_completion(cls, tool_name: str, success: bool, duration: float) -> str:
        """Get the completion message for a tool.

        Args:
            tool_name: Name of the tool.
            success: Whether the operation succeeded.
            duration: Duration in seconds.

        Returns:
            Natural language completion description.
        """
        desc = cls.DESCRIPTIONS.get(tool_name)
        if not desc:
            status = "Complete" if success else "Failed"
            return f"{status} ({duration:.1f}s)"

        message = desc.completion if success else desc.error
        return f"{message} ({duration:.1f}s)"

    @classmethod
    def _extract_context(cls, tool_name: str, args: dict[str, Any]) -> str | None:
        """Extract context from arguments for display.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Returns:
            Context string or None.
        """
        # File operations - show filename
        if tool_name in ("Read", "Write", "Edit"):
            file_path = args.get("file_path", "")
            if file_path:
                # Extract just the filename
                parts = file_path.replace("\\", "/").split("/")
                return parts[-1] if parts else file_path

        # Search operations - show pattern/query
        if tool_name == "Grep":
            return args.get("pattern", "")[:50]
        if tool_name == "Glob":
            return args.get("pattern", "")
        if tool_name == "WebSearch":
            return args.get("query", "")[:50]

        # Bash - show truncated command
        if tool_name == "Bash":
            cmd = args.get("command", "")
            if len(cmd) > 40:
                return cmd[:37] + "..."
            return cmd

        # WebFetch - show URL
        if tool_name == "WebFetch":
            url = args.get("url", "")
            # Extract domain
            match = re.search(r"https?://([^/]+)", url)
            if match:
                return match.group(1)
            return url[:50] if url else None

        return None


class ReasoningExtractor:
    """Extracts reasoning/intent from LLM output."""

    REASONING_PATTERNS: ClassVar[list[str]] = [
        r"^(?:I'll|I will|Let me|First,?|Now,?|Next,?)",
        r"^(?:Looking at|Checking|Reading|Searching|Examining)",
        r"^(?:To do this|To accomplish this|In order to)",
        r"^(?:Based on|Given|Since)",
    ]

    @classmethod
    def looks_like_reasoning(cls, text: str) -> bool:
        """Check if text looks like reasoning/intent.

        Args:
            text: Text to check.

        Returns:
            True if text appears to be reasoning.
        """
        text = text.strip()
        for pattern in cls.REASONING_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def extract_reasoning(cls, text: str) -> tuple[str | None, str]:
        """Extract reasoning from the start of text.

        Args:
            text: Full text that may contain reasoning.

        Returns:
            Tuple of (reasoning, remaining_text).
        """
        lines = text.split("\n", 1)
        first_line = lines[0].strip()

        if cls.looks_like_reasoning(first_line):
            remaining = lines[1] if len(lines) > 1 else ""
            return first_line, remaining.strip()

        return None, text


class ErrorExplainer:
    """Provides friendly error explanations."""

    ERROR_CATALOG: ClassVar[dict[str, dict[str, Any]]] = {
        "File not found": {
            "explanation": "The file doesn't exist at that location",
            "suggestions": ["Check the file path spelling", "Use Glob to search for the file"],
        },
        "Permission denied": {
            "explanation": "Cannot access this file due to permissions",
            "suggestions": ["Check file permissions with 'ls -la'", "You may need elevated access"],
        },
        "timed out": {
            "explanation": "The operation took too long to complete",
            "suggestions": ["Try a smaller scope", "Break the task into steps"],
        },
        "Connection refused": {
            "explanation": "Could not connect to the server",
            "suggestions": ["Check if the service is running", "Verify the URL is correct"],
        },
        "No such file or directory": {
            "explanation": "The path doesn't exist",
            "suggestions": ["Create the directory first", "Check the path spelling"],
        },
        "Command not found": {
            "explanation": "The program isn't installed or not in PATH",
            "suggestions": ["Install the required tool", "Check if it's in your PATH"],
        },
    }

    @classmethod
    def explain(cls, error: str) -> str:
        """Get a friendly explanation for an error.

        Args:
            error: Error message to explain.

        Returns:
            Friendly explanation with suggestions.
        """
        error_lower = error.lower()

        for pattern, info in cls.ERROR_CATALOG.items():
            if pattern.lower() in error_lower:
                lines = [info["explanation"]]
                if info.get("suggestions"):
                    lines.append("")
                    lines.append("Try:")
                    for suggestion in info["suggestions"]:
                        lines.append(f"  - {suggestion}")
                return "\n".join(lines)

        # Default: just return the original error
        return error


class ConversationalPresenter:
    """Presents tool execution events in a conversational style.

    This class wraps the raw agent events and presents them in a more
    natural, conversational way - similar to how Claude Code displays
    its actions.

    Example:
        presenter = ConversationalPresenter(console)

        # When tool starts:
        presenter.present_tool_start("Read", {"file_path": "/app/config.py"})
        # Output: "Reading config.py..."

        # When tool ends:
        presenter.present_tool_end("Read", True, 0.2)
        # Output: "File contents loaded (0.2s)"
    """

    def __init__(self, console: Console, *, verbose: bool = False) -> None:
        """Initialize the presenter.

        Args:
            console: Rich console for output.
            verbose: If True, show more details.
        """
        self._console = console
        self._verbose = verbose
        self._accumulated_text = ""
        self._current_tool: str | None = None

    def present_tool_start(self, tool_name: str, args: dict[str, Any]) -> None:
        """Present a tool start event.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.
        """
        self._current_tool = tool_name
        action = ToolDescriptor.get_action(tool_name, args)
        self._console.print(f"[dim]{action}[/dim]")

    def present_tool_end(
        self,
        tool_name: str,
        success: bool,
        duration: float,
        result: str = "",
    ) -> None:
        """Present a tool end event.

        Args:
            tool_name: Name of the tool.
            success: Whether the operation succeeded.
            duration: Duration in seconds.
            result: Tool result (optional, for showing preview).
        """
        completion = ToolDescriptor.get_completion(tool_name, success, duration)

        if success:
            # Show result preview for certain tools
            if result and tool_name in ("Read", "Grep", "Glob"):
                preview = self._truncate_output(result, max_lines=3)
                if preview:
                    self._console.print(f"[dim]{preview}[/dim]")

            self._console.print(f"[green]{completion}[/green]")
        else:
            self._console.print(f"[red]{completion}[/red]")

        self._current_tool = None

    def present_error(self, error: str) -> None:
        """Present an error with friendly explanation.

        Args:
            error: Error message.
        """
        explanation = ErrorExplainer.explain(error)
        self._console.print(f"[red]Error: {explanation}[/red]")

    def accumulate_text(self, chunk: str) -> None:
        """Accumulate text chunks for reasoning extraction.

        Args:
            chunk: Text chunk to accumulate.
        """
        self._accumulated_text += chunk

    def get_accumulated_text(self) -> str:
        """Get and clear accumulated text.

        Returns:
            Accumulated text.
        """
        text = self._accumulated_text
        self._accumulated_text = ""
        return text

    def present_reasoning(self, text: str) -> str | None:
        """Extract and present reasoning from text.

        Args:
            text: Text that may contain reasoning.

        Returns:
            Reasoning if found, None otherwise.
        """
        reasoning, _ = ReasoningExtractor.extract_reasoning(text)
        if reasoning:
            self._console.print(f"[italic dim]{reasoning}[/italic dim]")
        return reasoning

    def _truncate_output(self, text: str, max_lines: int = 5) -> str:
        """Truncate output for preview.

        Args:
            text: Text to truncate.
            max_lines: Maximum lines to show.

        Returns:
            Truncated text.
        """
        if not text:
            return ""

        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text

        shown = lines[:max_lines]
        remaining = len(lines) - max_lines
        return "\n".join(shown) + f"\n... ({remaining} more lines)"
