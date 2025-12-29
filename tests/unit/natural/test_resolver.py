"""Tests for parameter resolution."""

from __future__ import annotations

import pytest

from code_forge.natural.resolver import (
    ParameterResolver,
    ResolvedParameters,
)
from code_forge.natural.intent import IntentType


class TestResolvedParameters:
    """Tests for ResolvedParameters dataclass."""

    def test_creation(self) -> None:
        """Test creation of resolved parameters."""
        resolved = ResolvedParameters(
            tool_name="Edit",
            parameters={"file_path": "test.py"},
            confidence=0.9,
            inferred_flags={"replace_all": True},
            context_used=["Inferred replace_all from context"],
        )
        assert resolved.tool_name == "Edit"
        assert resolved.parameters["file_path"] == "test.py"
        assert resolved.inferred_flags["replace_all"] is True
        assert len(resolved.context_used) == 1

    def test_default_values(self) -> None:
        """Test default values."""
        resolved = ResolvedParameters(tool_name="Read")
        assert resolved.parameters == {}
        assert resolved.confidence == 0.0
        assert resolved.inferred_flags == {}
        assert resolved.context_used == []


class TestParameterResolver:
    """Tests for ParameterResolver."""

    @pytest.fixture
    def resolver(self) -> ParameterResolver:
        """Create a resolver instance."""
        return ParameterResolver()

    def test_resolve_replace_all(self, resolver: ParameterResolver) -> None:
        """Test resolving replace all intent."""
        result = resolver.resolve("replace all foo with bar")

        assert result.tool_name == "Edit"
        assert result.parameters.get("replace_all") is True
        assert result.inferred_flags.get("replace_all") is True
        assert result.confidence >= 0.8

    def test_resolve_replace_all_extracts_text(self, resolver: ParameterResolver) -> None:
        """Test that replace all extracts old/new text."""
        result = resolver.resolve("replace all oldValue with newValue")

        assert result.parameters.get("old_text") == "oldValue"
        assert result.parameters.get("new_text") == "newValue"

    def test_resolve_simple_replace(self, resolver: ParameterResolver) -> None:
        """Test resolving simple replace (no 'all')."""
        result = resolver.resolve("replace foo with bar")

        assert result.tool_name == "Edit"
        # Should NOT infer replace_all without explicit "all"
        assert result.inferred_flags.get("replace_all") is not True or \
               "replace_all" not in result.inferred_flags

    def test_resolve_rename_infers_replace_all(self, resolver: ParameterResolver) -> None:
        """Test that rename operations infer replace_all."""
        result = resolver.resolve("rename getData to fetchData")

        assert result.tool_name == "Edit"
        assert result.parameters.get("replace_all") is True
        assert result.parameters.get("old_string") == "getData"
        assert result.parameters.get("new_string") == "fetchData"

    def test_resolve_find_files(self, resolver: ParameterResolver) -> None:
        """Test resolving find files intent."""
        result = resolver.resolve("find all files matching *.py")

        assert result.tool_name == "Glob"
        assert "pattern" in result.parameters

    def test_resolve_search_content(self, resolver: ParameterResolver) -> None:
        """Test resolving search content intent."""
        result = resolver.resolve("search for TODO in the codebase")

        assert result.tool_name == "Grep"
        assert result.parameters.get("pattern") == "TODO"

    def test_resolve_run_tests(self, resolver: ParameterResolver) -> None:
        """Test resolving run tests intent."""
        result = resolver.resolve("run the tests")

        assert result.tool_name == "Bash"
        assert "command" in result.parameters

    def test_resolve_run_tests_with_target(self, resolver: ParameterResolver) -> None:
        """Test resolving run tests with specific target."""
        result = resolver.resolve("run tests for utils")

        assert result.tool_name == "Bash"
        assert "utils" in result.parameters.get("command", "")

    def test_resolve_build(self, resolver: ParameterResolver) -> None:
        """Test resolving build intent."""
        result = resolver.resolve("build the project")

        assert result.tool_name == "Bash"
        assert "command" in result.parameters

    def test_resolve_unknown(self, resolver: ParameterResolver) -> None:
        """Test resolving unknown intent."""
        result = resolver.resolve("some random text that doesn't match anything")

        assert result.tool_name == ""
        assert result.confidence == 0.0

    def test_resolve_find_definition(self, resolver: ParameterResolver) -> None:
        """Test resolving find definition intent."""
        result = resolver.resolve("find the definition of handleError")

        assert result.tool_name == "Grep"
        assert "pattern" in result.parameters
        # Should create a definition search pattern
        assert "handleError" in result.parameters.get("pattern", "")

    def test_resolve_fetch_url(self, resolver: ParameterResolver) -> None:
        """Test resolving fetch URL intent."""
        result = resolver.resolve("fetch https://api.example.com/data")

        assert result.tool_name == "WebFetch"
        assert result.parameters.get("url") == "https://api.example.com/data"

    def test_enhance_edit_parameters(self, resolver: ParameterResolver) -> None:
        """Test enhancing existing Edit parameters."""
        existing = {"file_path": "test.py", "old_string": "foo"}

        enhanced = resolver.enhance_edit_parameters(
            "replace all foo with bar",
            existing,
        )

        assert enhanced["file_path"] == "test.py"
        assert enhanced["replace_all"] is True

    def test_enhance_edit_parameters_no_override(self, resolver: ParameterResolver) -> None:
        """Test that existing replace_all is not overridden."""
        existing = {"replace_all": False}

        enhanced = resolver.enhance_edit_parameters(
            "replace all foo with bar",
            existing,
        )

        # Should not override existing value
        assert enhanced["replace_all"] is False

    def test_suggest_tool_for_request(self, resolver: ParameterResolver) -> None:
        """Test tool suggestion."""
        assert resolver.suggest_tool_for_request("read config.py") == "Read"
        assert resolver.suggest_tool_for_request("find all *.py files") == "Glob"
        assert resolver.suggest_tool_for_request("replace foo with bar") == "Edit"

    def test_suggest_tool_unknown(self, resolver: ParameterResolver) -> None:
        """Test tool suggestion for unknown request."""
        result = resolver.suggest_tool_for_request("xyz abc 123")
        assert result is None

    def test_get_parameter_hints_edit(self, resolver: ParameterResolver) -> None:
        """Test getting parameter hints for Edit tool."""
        hints = resolver.get_parameter_hints("Edit", "replace all foo with bar")

        assert hints.get("replace_all") is True
        assert hints.get("old_string") == "foo"
        assert hints.get("new_string") == "bar"

    def test_get_parameter_hints_grep(self, resolver: ParameterResolver) -> None:
        """Test getting parameter hints for Grep tool."""
        hints = resolver.get_parameter_hints("Grep", "search for error in codebase")

        assert "pattern" in hints

    def test_get_parameter_hints_glob(self, resolver: ParameterResolver) -> None:
        """Test getting parameter hints for Glob tool."""
        hints = resolver.get_parameter_hints("Glob", "find files matching test.py")

        assert "pattern" in hints


class TestParameterResolverWithContext:
    """Tests for ParameterResolver with session context."""

    def test_resolve_with_active_file(self) -> None:
        """Test resolving with active file from context."""
        # Create a mock context tracker
        class MockContextTracker:
            active_file = "src/main.py"

        resolver = ParameterResolver(context_tracker=MockContextTracker())
        result = resolver.resolve("edit the file")

        # Should use active file from context
        assert result.parameters.get("file_path") == "src/main.py"
        assert any("active file" in ctx.lower() for ctx in result.context_used)

    def test_resolve_without_context(self) -> None:
        """Test resolving without context tracker."""
        resolver = ParameterResolver(context_tracker=None)
        result = resolver.resolve("edit the file")

        # Should not have file_path without context
        assert "file_path" not in result.parameters or result.parameters.get("file_path") is None
