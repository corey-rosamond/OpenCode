"""Tests for natural language middleware."""

from __future__ import annotations

import pytest

from code_forge.natural.intent import IntentType
from code_forge.natural.middleware import (
    NaturalLanguageMiddleware,
    ProcessedRequest,
    create_middleware,
)


class TestProcessedRequest:
    """Tests for ProcessedRequest dataclass."""

    def test_creation(self) -> None:
        """Test request creation."""
        request = ProcessedRequest(
            original_text="replace all foo with bar",
            intent_type=IntentType.REPLACE_ALL,
            confidence=0.9,
            suggested_tool="Edit",
        )
        assert request.original_text == "replace all foo with bar"
        assert request.intent_type == IntentType.REPLACE_ALL
        assert request.confidence == 0.9
        assert request.suggested_tool == "Edit"

    def test_default_values(self) -> None:
        """Test default values."""
        request = ProcessedRequest(original_text="test")
        assert request.intent_type == IntentType.UNKNOWN
        assert request.confidence == 0.0
        assert request.suggested_tool == ""
        assert request.inferred_parameters == {}
        assert request.requires_sequence is False
        assert request.sequence is None
        assert request.context_hints == []


class TestNaturalLanguageMiddleware:
    """Tests for NaturalLanguageMiddleware."""

    @pytest.fixture
    def middleware(self) -> NaturalLanguageMiddleware:
        """Create a middleware instance."""
        return NaturalLanguageMiddleware()

    def test_process_empty(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test processing empty input."""
        result = middleware.process("")
        assert result.original_text == ""
        assert result.intent_type == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_process_replace_all(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test processing replace all request."""
        result = middleware.process("replace all foo with bar")
        assert result.intent_type == IntentType.REPLACE_ALL
        assert result.confidence >= 0.8
        assert result.suggested_tool == "Edit"
        assert result.inferred_parameters.get("replace_all") is True

    def test_process_rename(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test processing rename request."""
        result = middleware.process("rename getData to fetchData")
        assert result.intent_type == IntentType.RENAME_SYMBOL
        assert result.suggested_tool == "Edit"
        assert result.inferred_parameters.get("old_string") == "getData"
        assert result.inferred_parameters.get("new_string") == "fetchData"

    def test_process_find_files(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test processing find files request."""
        result = middleware.process("find all files matching *.py")
        assert result.intent_type == IntentType.FIND_FILES
        assert result.suggested_tool == "Glob"
        assert "pattern" in result.inferred_parameters

    def test_process_search(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test processing search request."""
        result = middleware.process("search for TODO in the codebase")
        assert result.intent_type == IntentType.SEARCH_CONTENT
        assert result.suggested_tool == "Grep"

    def test_process_complex_request(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test processing complex multi-step request."""
        result = middleware.process("find the error and then fix it")
        assert result.requires_sequence is True
        assert result.sequence is not None
        assert result.sequence.tool_count >= 1

    def test_should_use_replace_all(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test replace_all detection helper."""
        assert middleware.should_use_replace_all("replace all foo with bar")
        assert middleware.should_use_replace_all("change every instance of x to y")
        assert middleware.should_use_replace_all("update foo everywhere")
        assert not middleware.should_use_replace_all("replace foo with bar")
        assert not middleware.should_use_replace_all("edit the file")

    def test_enhance_tool_parameters_edit(self, middleware: NaturalLanguageMiddleware) -> None:
        """Test enhancing Edit tool parameters."""
        existing = {"file_path": "test.py"}
        enhanced = middleware.enhance_tool_parameters(
            "Edit",
            "replace all foo with bar",
            existing,
        )
        assert enhanced["file_path"] == "test.py"
        assert enhanced["replace_all"] is True

    def test_enhance_tool_parameters_preserves_existing(
        self, middleware: NaturalLanguageMiddleware
    ) -> None:
        """Test that existing parameters are preserved."""
        existing = {"file_path": "test.py", "replace_all": False}
        enhanced = middleware.enhance_tool_parameters(
            "Edit",
            "replace all foo with bar",
            existing,
        )
        assert enhanced["replace_all"] is False

    def test_enhance_tool_parameters_other_tool(
        self, middleware: NaturalLanguageMiddleware
    ) -> None:
        """Test enhancing parameters for non-Edit tools."""
        existing = {"pattern": "*.py"}
        enhanced = middleware.enhance_tool_parameters(
            "Glob",
            "find all python files",
            existing,
        )
        assert enhanced["pattern"] == "*.py"

    def test_get_sequence_summary_simple(
        self, middleware: NaturalLanguageMiddleware
    ) -> None:
        """Test summary for simple request."""
        summary = middleware.get_sequence_summary("read config.py")
        assert summary == "Single-step operation"

    def test_get_sequence_summary_complex(
        self, middleware: NaturalLanguageMiddleware
    ) -> None:
        """Test summary for complex request."""
        summary = middleware.get_sequence_summary("find the bug and then fix it")
        assert "Plan:" in summary or "step" in summary.lower() or "Step" in summary

    def test_extract_file_reference(
        self, middleware: NaturalLanguageMiddleware
    ) -> None:
        """Test file reference extraction."""
        file_path = middleware.extract_file_reference("read config.py")
        assert file_path == "config.py"

    def test_extract_file_reference_none(
        self, middleware: NaturalLanguageMiddleware
    ) -> None:
        """Test file reference extraction when no file is mentioned."""
        file_path = middleware.extract_file_reference("search for errors")
        assert file_path is None


class TestNaturalLanguageMiddlewareWithContext:
    """Tests for middleware with context tracker."""

    def test_process_with_context(self) -> None:
        """Test processing with context tracker."""
        class MockContextTracker:
            active_file = "src/main.py"

        middleware = NaturalLanguageMiddleware(context_tracker=MockContextTracker())
        result = middleware.process("edit the file")

        assert result.inferred_parameters.get("file_path") == "src/main.py"

    def test_extract_file_from_context(self) -> None:
        """Test file extraction from context."""
        class MockContextTracker:
            active_file = "config.json"

        middleware = NaturalLanguageMiddleware(context_tracker=MockContextTracker())
        file_path = middleware.extract_file_reference("update it")

        assert file_path == "config.json"


class TestCreateMiddleware:
    """Tests for create_middleware factory."""

    def test_create_without_context(self) -> None:
        """Test factory without context tracker."""
        middleware = create_middleware()
        assert isinstance(middleware, NaturalLanguageMiddleware)

    def test_create_with_context(self) -> None:
        """Test factory with context tracker."""
        class MockContextTracker:
            active_file = "test.py"

        middleware = create_middleware(context_tracker=MockContextTracker())
        assert isinstance(middleware, NaturalLanguageMiddleware)

        # Verify context is used
        result = middleware.process("edit the file")
        assert result.inferred_parameters.get("file_path") == "test.py"
