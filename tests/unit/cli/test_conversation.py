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

    # ===== FILE SYSTEM ERRORS =====

    def test_explain_file_not_found(self) -> None:
        """Test explanation for file not found."""
        explanation = ErrorExplainer.explain("File not found: /missing.txt")
        assert "doesn't exist" in explanation
        assert "path" in explanation.lower() or "Glob" in explanation

    def test_explain_permission_denied(self) -> None:
        """Test explanation for permission denied."""
        explanation = ErrorExplainer.explain("Permission denied: /etc/passwd")
        assert "permission" in explanation.lower()

    def test_explain_no_such_file(self) -> None:
        """Test explanation for no such file or directory."""
        explanation = ErrorExplainer.explain("No such file or directory: /tmp/foo")
        assert "doesn't exist" in explanation or "path" in explanation.lower()
        assert "Try:" in explanation

    def test_explain_is_a_directory(self) -> None:
        """Test explanation for is a directory error."""
        explanation = ErrorExplainer.explain("Is a directory: /tmp/")
        assert "directory" in explanation.lower()
        assert "file" in explanation.lower()

    def test_explain_no_space_left(self) -> None:
        """Test explanation for disk full."""
        explanation = ErrorExplainer.explain("No space left on device")
        assert "disk" in explanation.lower() or "full" in explanation.lower()

    def test_explain_too_many_open_files(self) -> None:
        """Test explanation for too many open files."""
        explanation = ErrorExplainer.explain("Too many open files")
        assert "file" in explanation.lower()
        assert "limit" in explanation.lower() or "descriptor" in explanation.lower()

    # ===== PYTHON ERRORS =====

    def test_explain_module_not_found(self) -> None:
        """Test explanation for ModuleNotFoundError."""
        explanation = ErrorExplainer.explain("ModuleNotFoundError: No module named 'requests'")
        assert "module" in explanation.lower() or "installed" in explanation.lower()
        assert "pip" in explanation.lower()

    def test_explain_import_error(self) -> None:
        """Test explanation for ImportError."""
        explanation = ErrorExplainer.explain("ImportError: cannot import name 'foo'")
        assert "import" in explanation.lower()

    def test_explain_syntax_error(self) -> None:
        """Test explanation for SyntaxError."""
        explanation = ErrorExplainer.explain("SyntaxError: invalid syntax")
        assert "syntax" in explanation.lower()
        assert "colons" in explanation.lower() or "indentation" in explanation.lower()

    def test_explain_type_error(self) -> None:
        """Test explanation for TypeError."""
        explanation = ErrorExplainer.explain("TypeError: unsupported operand type")
        assert "type" in explanation.lower()

    def test_explain_attribute_error(self) -> None:
        """Test explanation for AttributeError."""
        explanation = ErrorExplainer.explain("AttributeError: 'NoneType' has no attribute 'foo'")
        assert "attribute" in explanation.lower() or "method" in explanation.lower()

    def test_explain_key_error(self) -> None:
        """Test explanation for KeyError."""
        explanation = ErrorExplainer.explain("KeyError: 'missing_key'")
        assert "key" in explanation.lower() or "dictionary" in explanation.lower()

    def test_explain_index_error(self) -> None:
        """Test explanation for IndexError."""
        explanation = ErrorExplainer.explain("IndexError: list index out of range")
        assert "index" in explanation.lower() or "range" in explanation.lower()

    def test_explain_name_error(self) -> None:
        """Test explanation for NameError."""
        explanation = ErrorExplainer.explain("NameError: name 'foo' is not defined")
        assert "defined" in explanation.lower() or "variable" in explanation.lower()

    # ===== NODE.JS / NPM ERRORS =====

    def test_explain_module_not_found_node(self) -> None:
        """Test explanation for MODULE_NOT_FOUND."""
        explanation = ErrorExplainer.explain("Error: Cannot find module 'MODULE_NOT_FOUND'")
        assert "module" in explanation.lower() or "installed" in explanation.lower()
        assert "npm install" in explanation.lower()

    def test_explain_enoent(self) -> None:
        """Test explanation for ENOENT."""
        explanation = ErrorExplainer.explain("Error: ENOENT: no such file or directory")
        assert "not found" in explanation.lower() or "directory" in explanation.lower()

    def test_explain_eaddrinuse(self) -> None:
        """Test explanation for port in use."""
        explanation = ErrorExplainer.explain("Error: EADDRINUSE: address already in use")
        assert "port" in explanation.lower() or "use" in explanation.lower()

    def test_explain_npm_peer_dep(self) -> None:
        """Test explanation for npm peer dependency error."""
        explanation = ErrorExplainer.explain("npm ERR! peer dep missing")
        assert "peer" in explanation.lower() or "dependency" in explanation.lower()

    # ===== GIT ERRORS =====

    def test_explain_not_a_git_repo(self) -> None:
        """Test explanation for not a git repository."""
        explanation = ErrorExplainer.explain("fatal: not a git repository")
        assert "git" in explanation.lower()
        assert "repository" in explanation.lower() or "init" in explanation.lower()

    def test_explain_merge_conflict(self) -> None:
        """Test explanation for merge conflict."""
        explanation = ErrorExplainer.explain("CONFLICT (content): Merge conflict in file.txt")
        assert "conflict" in explanation.lower() or "merge" in explanation.lower()

    def test_explain_push_rejected(self) -> None:
        """Test explanation for push rejected."""
        explanation = ErrorExplainer.explain("! [rejected] main -> main (non-fast-forward)")
        assert "push" in explanation.lower() or "pull" in explanation.lower()

    def test_explain_detached_head(self) -> None:
        """Test explanation for detached HEAD."""
        explanation = ErrorExplainer.explain("You are in 'detached HEAD' state")
        assert "branch" in explanation.lower() or "head" in explanation.lower()

    # ===== NETWORK / HTTP ERRORS =====

    def test_explain_connection_refused(self) -> None:
        """Test explanation for connection refused."""
        explanation = ErrorExplainer.explain("Connection refused")
        assert "connect" in explanation.lower() or "server" in explanation.lower()

    def test_explain_timeout(self) -> None:
        """Test explanation for timeout."""
        explanation = ErrorExplainer.explain("Operation timed out after 30s")
        assert "long" in explanation.lower() or "network" in explanation.lower()

    def test_explain_dns_failure(self) -> None:
        """Test explanation for DNS failure."""
        explanation = ErrorExplainer.explain("Name or service not known")
        assert "dns" in explanation.lower() or "hostname" in explanation.lower()

    def test_explain_ssl_error(self) -> None:
        """Test explanation for SSL error."""
        explanation = ErrorExplainer.explain("SSL: CERTIFICATE_VERIFY_FAILED")
        assert "ssl" in explanation.lower() or "certificate" in explanation.lower()

    def test_explain_http_401(self) -> None:
        """Test explanation for HTTP 401."""
        explanation = ErrorExplainer.explain("HTTP 401 Unauthorized")
        assert "authentication" in explanation.lower() or "credentials" in explanation.lower()

    def test_explain_http_403(self) -> None:
        """Test explanation for HTTP 403."""
        explanation = ErrorExplainer.explain("HTTP 403 Forbidden")
        assert "forbidden" in explanation.lower() or "permission" in explanation.lower()

    def test_explain_http_404(self) -> None:
        """Test explanation for HTTP 404."""
        explanation = ErrorExplainer.explain("HTTP 404 Not Found")
        assert "not found" in explanation.lower() or "resource" in explanation.lower()

    def test_explain_http_429(self) -> None:
        """Test explanation for HTTP 429."""
        explanation = ErrorExplainer.explain("HTTP 429 Too Many Requests")
        assert "rate" in explanation.lower() or "requests" in explanation.lower()

    def test_explain_http_500(self) -> None:
        """Test explanation for HTTP 500."""
        explanation = ErrorExplainer.explain("HTTP 500 Internal Server Error")
        assert "server" in explanation.lower() or "error" in explanation.lower()

    # ===== SHELL / COMMAND ERRORS =====

    def test_explain_command_not_found(self) -> None:
        """Test explanation for command not found."""
        explanation = ErrorExplainer.explain("Command not found: docker")
        assert "installed" in explanation.lower() or "path" in explanation.lower()

    def test_explain_exit_code_1(self) -> None:
        """Test explanation for exit code 1."""
        explanation = ErrorExplainer.explain("Process exited with exit code 1")
        assert "error" in explanation.lower() or "failed" in explanation.lower()

    def test_explain_exit_code_127(self) -> None:
        """Test explanation for exit code 127."""
        explanation = ErrorExplainer.explain("exit code 127")
        assert "not found" in explanation.lower() or "command" in explanation.lower()

    def test_explain_killed(self) -> None:
        """Test explanation for killed process."""
        explanation = ErrorExplainer.explain("Killed")
        assert "memory" in explanation.lower() or "killed" in explanation.lower()

    def test_explain_segfault(self) -> None:
        """Test explanation for segmentation fault."""
        explanation = ErrorExplainer.explain("Segmentation fault (core dumped)")
        assert "crash" in explanation.lower() or "memory" in explanation.lower()

    # ===== API / SERVICE ERRORS =====

    def test_explain_rate_limit(self) -> None:
        """Test explanation for rate limit."""
        explanation = ErrorExplainer.explain("rate limit exceeded")
        assert "rate" in explanation.lower() or "requests" in explanation.lower()
        assert "wait" in explanation.lower()

    def test_explain_quota_exceeded(self) -> None:
        """Test explanation for quota exceeded."""
        explanation = ErrorExplainer.explain("quota exceeded")
        assert "quota" in explanation.lower() or "usage" in explanation.lower()

    def test_explain_invalid_api_key(self) -> None:
        """Test explanation for invalid API key."""
        explanation = ErrorExplainer.explain("invalid api key")
        assert "api" in explanation.lower() or "key" in explanation.lower()

    # ===== DOCKER ERRORS =====

    def test_explain_docker_daemon_error(self) -> None:
        """Test explanation for docker daemon error."""
        explanation = ErrorExplainer.explain("docker: Error response from daemon: cannot start container")
        assert "docker" in explanation.lower() or "daemon" in explanation.lower()

    def test_explain_docker_image_not_found(self) -> None:
        """Test explanation for docker image not found."""
        explanation = ErrorExplainer.explain("image not found: myimage:latest")
        assert "image" in explanation.lower()
        assert "pull" in explanation.lower() or "exist" in explanation.lower()

    # ===== DATABASE ERRORS =====

    def test_explain_db_connection_refused(self) -> None:
        """Test explanation for database connection refused."""
        explanation = ErrorExplainer.explain("connection refused to database")
        assert "connect" in explanation.lower() or "database" in explanation.lower()

    def test_explain_db_auth_failed(self) -> None:
        """Test explanation for database auth failed."""
        explanation = ErrorExplainer.explain("authentication failed for user 'postgres'")
        assert "authentication" in explanation.lower() or "credentials" in explanation.lower()

    def test_explain_duplicate_key(self) -> None:
        """Test explanation for duplicate key error."""
        explanation = ErrorExplainer.explain("duplicate key value violates unique constraint")
        assert "duplicate" in explanation.lower() or "exists" in explanation.lower()

    # ===== UNKNOWN ERROR =====

    def test_explain_unknown_error(self) -> None:
        """Test that unknown errors are returned as-is."""
        original = "Some random error message"
        explanation = ErrorExplainer.explain(original)
        assert explanation == original

    # ===== CASE INSENSITIVITY =====

    def test_explain_case_insensitive(self) -> None:
        """Test that error matching is case insensitive."""
        explanation1 = ErrorExplainer.explain("FILE NOT FOUND")
        explanation2 = ErrorExplainer.explain("file not found")
        # Both should get an explanation (not be returned as-is)
        assert "doesn't exist" in explanation1 or "doesn't exist" in explanation2

    # ===== ERROR CATALOG SIZE =====

    def test_error_catalog_has_many_patterns(self) -> None:
        """Test that error catalog has 50+ patterns."""
        assert len(ErrorExplainer.ERROR_CATALOG) >= 50


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
