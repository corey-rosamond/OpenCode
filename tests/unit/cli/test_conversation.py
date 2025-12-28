"""Tests for conversational presentation layer."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

import pytest

from code_forge.cli.conversation import (
    ConversationalPresenter,
    ErrorExplainer,
    ReasoningExtractor,
    ToolDescriptor,
)


class TestToolDescriptor:
    """Tests for ToolDescriptor."""

    def test_get_action_read(self) -> None:
        """Test action message for Read tool."""
        action = ToolDescriptor.get_action("Read", {"file_path": "/app/config.py"})
        assert "Reading" in action
        assert "config.py" in action

    def test_get_action_write(self) -> None:
        """Test action message for Write tool."""
        action = ToolDescriptor.get_action("Write", {"file_path": "/app/main.py"})
        assert "Writing" in action
        assert "main.py" in action

    def test_get_action_edit(self) -> None:
        """Test action message for Edit tool."""
        action = ToolDescriptor.get_action("Edit", {"file_path": "/src/utils.py"})
        assert "Editing" in action
        assert "utils.py" in action

    def test_get_action_bash(self) -> None:
        """Test action message for Bash tool."""
        action = ToolDescriptor.get_action("Bash", {"command": "npm install"})
        assert "Running" in action
        assert "npm install" in action

    def test_get_action_grep(self) -> None:
        """Test action message for Grep tool."""
        action = ToolDescriptor.get_action("Grep", {"pattern": "TODO"})
        assert "Searching" in action
        assert "TODO" in action

    def test_get_action_glob(self) -> None:
        """Test action message for Glob tool."""
        action = ToolDescriptor.get_action("Glob", {"pattern": "**/*.py"})
        assert "Finding" in action
        assert "*.py" in action

    def test_get_action_unknown_tool(self) -> None:
        """Test action message for unknown tool."""
        action = ToolDescriptor.get_action("UnknownTool", {})
        assert "Running UnknownTool" in action

    def test_get_action_long_bash_command(self) -> None:
        """Test truncation of long bash commands."""
        long_cmd = "npm install --save-dev typescript eslint prettier webpack"
        action = ToolDescriptor.get_action("Bash", {"command": long_cmd})
        assert "..." in action

    def test_get_completion_success(self) -> None:
        """Test completion message on success."""
        completion = ToolDescriptor.get_completion("Read", True, 0.5)
        assert "File contents loaded" in completion
        assert "0.5s" in completion

    def test_get_completion_failure(self) -> None:
        """Test completion message on failure."""
        completion = ToolDescriptor.get_completion("Read", False, 1.2)
        assert "Could not read file" in completion
        assert "1.2s" in completion

    def test_get_completion_unknown_tool(self) -> None:
        """Test completion message for unknown tool."""
        completion = ToolDescriptor.get_completion("UnknownTool", True, 0.3)
        assert "Complete" in completion
        assert "0.3s" in completion

    def test_extract_context_web_fetch(self) -> None:
        """Test context extraction for WebFetch."""
        action = ToolDescriptor.get_action(
            "WebFetch", {"url": "https://example.com/api/data"}
        )
        assert "example.com" in action


class TestReasoningExtractor:
    """Tests for ReasoningExtractor."""

    def test_looks_like_reasoning_ill(self) -> None:
        """Test detection of 'I'll' reasoning."""
        assert ReasoningExtractor.looks_like_reasoning("I'll start by reading the file")

    def test_looks_like_reasoning_let_me(self) -> None:
        """Test detection of 'Let me' reasoning."""
        assert ReasoningExtractor.looks_like_reasoning("Let me check the configuration")

    def test_looks_like_reasoning_first(self) -> None:
        """Test detection of 'First' reasoning."""
        assert ReasoningExtractor.looks_like_reasoning("First, I need to understand the code")

    def test_looks_like_reasoning_looking_at(self) -> None:
        """Test detection of 'Looking at' reasoning."""
        assert ReasoningExtractor.looks_like_reasoning("Looking at the error message...")

    def test_not_reasoning(self) -> None:
        """Test non-reasoning text."""
        assert not ReasoningExtractor.looks_like_reasoning("Here's the modified code:")
        assert not ReasoningExtractor.looks_like_reasoning("The function returns True")

    def test_extract_reasoning(self) -> None:
        """Test reasoning extraction."""
        text = "I'll start by reading the config file.\n\nThe configuration looks correct."
        reasoning, remaining = ReasoningExtractor.extract_reasoning(text)

        assert reasoning == "I'll start by reading the config file."
        assert "configuration looks correct" in remaining

    def test_extract_reasoning_no_match(self) -> None:
        """Test when no reasoning is found."""
        text = "Here is the output:\n\nsome data"
        reasoning, remaining = ReasoningExtractor.extract_reasoning(text)

        assert reasoning is None
        assert remaining == text


class TestErrorExplainer:
    """Tests for ErrorExplainer."""

    def test_explain_file_not_found(self) -> None:
        """Test explanation for file not found."""
        explanation = ErrorExplainer.explain("File not found: /missing.txt")
        assert "doesn't exist" in explanation
        assert "path" in explanation.lower() or "Glob" in explanation

    def test_explain_permission_denied(self) -> None:
        """Test explanation for permission denied."""
        explanation = ErrorExplainer.explain("Permission denied: /etc/passwd")
        assert "permission" in explanation.lower()

    def test_explain_timeout(self) -> None:
        """Test explanation for timeout."""
        explanation = ErrorExplainer.explain("Operation timed out after 30s")
        assert "long" in explanation.lower()
        assert "steps" in explanation.lower() or "scope" in explanation.lower()

    def test_explain_connection_refused(self) -> None:
        """Test explanation for connection refused."""
        explanation = ErrorExplainer.explain("Connection refused")
        assert "connect" in explanation.lower() or "server" in explanation.lower()

    def test_explain_unknown_error(self) -> None:
        """Test that unknown errors are returned as-is."""
        original = "Some random error message"
        explanation = ErrorExplainer.explain(original)
        assert explanation == original


class TestConversationalPresenter:
    """Tests for ConversationalPresenter."""

    @pytest.fixture
    def mock_console(self) -> MagicMock:
        """Create a mock console."""
        return MagicMock()

    @pytest.fixture
    def presenter(self, mock_console: MagicMock) -> ConversationalPresenter:
        """Create a presenter with mock console."""
        return ConversationalPresenter(mock_console)

    def test_present_tool_start(
        self, presenter: ConversationalPresenter, mock_console: MagicMock
    ) -> None:
        """Test presenting tool start."""
        presenter.present_tool_start("Read", {"file_path": "/app/config.py"})

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Reading" in call_args
        assert "config.py" in call_args

    def test_present_tool_end_success(
        self, presenter: ConversationalPresenter, mock_console: MagicMock
    ) -> None:
        """Test presenting successful tool end."""
        presenter.present_tool_end("Read", True, 0.5)

        call_args = mock_console.print.call_args[0][0]
        assert "loaded" in call_args.lower() or "0.5s" in call_args

    def test_present_tool_end_failure(
        self, presenter: ConversationalPresenter, mock_console: MagicMock
    ) -> None:
        """Test presenting failed tool end."""
        presenter.present_tool_end("Read", False, 1.0)

        call_args = mock_console.print.call_args[0][0]
        assert "red" in call_args.lower() or "error" in call_args.lower() or "could not" in call_args.lower()

    def test_present_error(
        self, presenter: ConversationalPresenter, mock_console: MagicMock
    ) -> None:
        """Test presenting error."""
        presenter.present_error("File not found: /missing.txt")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Error" in call_args

    def test_accumulate_text(self, presenter: ConversationalPresenter) -> None:
        """Test text accumulation."""
        presenter.accumulate_text("Hello ")
        presenter.accumulate_text("world")

        assert presenter.get_accumulated_text() == "Hello world"
        assert presenter.get_accumulated_text() == ""  # Cleared after get

    def test_present_reasoning(
        self, presenter: ConversationalPresenter, mock_console: MagicMock
    ) -> None:
        """Test reasoning presentation."""
        reasoning = presenter.present_reasoning("I'll start by reading the file")

        assert reasoning is not None
        mock_console.print.assert_called_once()

    def test_present_reasoning_none(
        self, presenter: ConversationalPresenter, mock_console: MagicMock
    ) -> None:
        """Test when no reasoning is found."""
        reasoning = presenter.present_reasoning("Here is the code:")

        assert reasoning is None
        mock_console.print.assert_not_called()

    def test_truncate_output(self, presenter: ConversationalPresenter) -> None:
        """Test output truncation."""
        long_text = "\n".join([f"Line {i}" for i in range(20)])
        result = presenter._truncate_output(long_text, max_lines=5)

        assert "Line 0" in result
        assert "Line 4" in result
        assert "Line 5" not in result
        assert "more lines" in result
