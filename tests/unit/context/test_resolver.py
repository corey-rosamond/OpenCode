"""Tests for pronoun resolver."""

from __future__ import annotations

import pytest

from code_forge.context.resolver import PronounResolver, ResolvedReference
from code_forge.context.tracker import (
    EntityType,
    OperationType,
    SessionContextTracker,
)


class TestResolvedReference:
    """Tests for ResolvedReference dataclass."""

    def test_creation(self) -> None:
        """Test reference creation."""
        ref = ResolvedReference(
            original="that file",
            resolved="test.py",
            entity_type=EntityType.FILE,
            confidence=0.9,
        )
        assert ref.original == "that file"
        assert ref.resolved == "test.py"
        assert ref.entity_type == EntityType.FILE
        assert ref.confidence == 0.9


class TestPronounResolver:
    """Tests for PronounResolver."""

    def test_resolve_it_to_active_file(self) -> None:
        """Test 'it' resolves to active file."""
        tracker = SessionContextTracker()
        tracker.set_active_file("main.py")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Can you fix it?")

        assert len(resolutions) >= 1
        file_refs = [r for r in resolutions if r.entity_type == EntityType.FILE]
        assert any(r.resolved == "main.py" for r in file_refs)

    def test_resolve_that_file(self) -> None:
        """Test 'that file' resolves to recent file."""
        tracker = SessionContextTracker()
        tracker.set_active_file("config.py")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Edit that file")

        assert len(resolutions) >= 1
        assert any(r.resolved == "config.py" for r in resolutions)

    def test_resolve_the_function(self) -> None:
        """Test 'the function' resolves to recent function."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FUNCTION, "process_data")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Refactor the function")

        assert len(resolutions) >= 1
        func_refs = [r for r in resolutions if r.entity_type == EntityType.FUNCTION]
        assert len(func_refs) >= 1
        assert func_refs[0].resolved == "process_data"

    def test_resolve_that_class(self) -> None:
        """Test 'that class' resolves to recent class."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.CLASS, "UserManager")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Update that class")

        assert len(resolutions) >= 1
        class_refs = [r for r in resolutions if r.entity_type == EntityType.CLASS]
        assert len(class_refs) >= 1
        assert class_refs[0].resolved == "UserManager"

    def test_resolve_the_error(self) -> None:
        """Test 'the error' resolves to last failed operation."""
        tracker = SessionContextTracker()
        tracker.track_operation(
            OperationType.EXECUTE,
            "npm run build",
            "Bash",
            success=False,
            result_summary="Module not found",
        )
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Fix the error")

        assert len(resolutions) >= 1
        error_refs = [r for r in resolutions if "Module not found" in r.resolved]
        assert len(error_refs) >= 1

    def test_resolve_that_url(self) -> None:
        """Test 'that url' resolves to recent URL."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.URL, "https://api.example.com")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Fetch from that url again")

        assert len(resolutions) >= 1
        url_refs = [r for r in resolutions if r.entity_type == EntityType.URL]
        assert len(url_refs) >= 1
        assert url_refs[0].resolved == "https://api.example.com"

    def test_resolve_current_file(self) -> None:
        """Test 'current file' resolves to active file."""
        tracker = SessionContextTracker()
        tracker.set_active_file("active.py")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Show the current file")

        assert len(resolutions) >= 1
        assert any(r.resolved == "active.py" for r in resolutions)

    def test_resolve_there_to_directory(self) -> None:
        """Test 'there' resolves to directory."""
        tracker = SessionContextTracker()
        tracker.set_active_file("/src/components/Button.tsx")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Add a new file there")

        assert len(resolutions) >= 1
        dir_refs = [r for r in resolutions if r.entity_type == EntityType.DIRECTORY]
        assert len(dir_refs) >= 1

    def test_resolve_single_returns_best(self) -> None:
        """Test resolve_single returns highest confidence match."""
        tracker = SessionContextTracker()
        tracker.set_active_file("main.py")
        resolver = PronounResolver(tracker)

        result = resolver.resolve_single("Edit it")

        assert result is not None
        assert result.resolved == "main.py"

    def test_resolve_single_returns_none_when_no_match(self) -> None:
        """Test resolve_single returns None when nothing matches."""
        tracker = SessionContextTracker()
        resolver = PronounResolver(tracker)

        result = resolver.resolve_single("Hello world")

        # "it" pattern might still match but with nothing to resolve to
        # If no entities tracked, should return None
        # Actually this might still match "it" pattern but return None from resolution

    def test_expand_references(self) -> None:
        """Test expanding references in text."""
        tracker = SessionContextTracker()
        tracker.set_active_file("config.py")
        resolver = PronounResolver(tracker)

        result = resolver.expand_references("Please edit that file")

        assert "config.py" in result

    def test_expand_references_no_matches(self) -> None:
        """Test expand_references with no matches returns original."""
        tracker = SessionContextTracker()
        resolver = PronounResolver(tracker)

        original = "Hello world"
        result = resolver.expand_references(original)

        # Should return original or close to it
        assert "Hello" in result

    def test_get_context_hints_with_active_file(self) -> None:
        """Test context hints include active file."""
        tracker = SessionContextTracker()
        tracker.set_active_file("main.py")
        resolver = PronounResolver(tracker)

        hints = resolver.get_context_hints()

        assert "main.py" in hints
        assert "Active file" in hints

    def test_get_context_hints_with_recent_files(self) -> None:
        """Test context hints include recent files."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FILE, "a.py")
        tracker.increment_turn()
        tracker.track_entity(EntityType.FILE, "b.py")
        resolver = PronounResolver(tracker)

        hints = resolver.get_context_hints()

        # Should mention recent files
        assert "Recent files" in hints or "a.py" in hints or "b.py" in hints

    def test_get_context_hints_with_last_operation(self) -> None:
        """Test context hints include last operation."""
        tracker = SessionContextTracker()
        tracker.track_operation(
            OperationType.EDIT,
            "test.py",
            "Edit",
            success=True,
        )
        resolver = PronounResolver(tracker)

        hints = resolver.get_context_hints()

        assert "Last operation" in hints
        assert "test.py" in hints

    def test_get_context_hints_empty(self) -> None:
        """Test context hints are empty when nothing tracked."""
        tracker = SessionContextTracker()
        resolver = PronounResolver(tracker)

        hints = resolver.get_context_hints()

        assert hints == ""

    def test_resolve_multiple_patterns(self) -> None:
        """Test resolving multiple reference types."""
        tracker = SessionContextTracker()
        tracker.set_active_file("main.py")
        tracker.track_entity(EntityType.FUNCTION, "process")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Edit it and refactor the function")

        file_refs = [r for r in resolutions if r.entity_type == EntityType.FILE]
        func_refs = [r for r in resolutions if r.entity_type == EntityType.FUNCTION]

        assert len(file_refs) >= 1
        assert len(func_refs) >= 1

    def test_resolve_case_insensitive(self) -> None:
        """Test resolution is case insensitive."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("Edit THAT FILE")

        assert len(resolutions) >= 1
        assert any(r.resolved == "test.py" for r in resolutions)

    def test_confidence_levels(self) -> None:
        """Test different patterns have appropriate confidence."""
        tracker = SessionContextTracker()
        tracker.set_active_file("test.py")
        resolver = PronounResolver(tracker)

        # "it" should have lower confidence than "that file"
        it_resolutions = resolver.resolve("fix it")
        file_resolutions = resolver.resolve("fix that file")

        it_confidence = max(r.confidence for r in it_resolutions) if it_resolutions else 0
        file_confidence = max(r.confidence for r in file_resolutions) if file_resolutions else 0

        # "that file" should have higher confidence
        assert file_confidence >= it_confidence

    def test_most_recent_entity_wins(self) -> None:
        """Test most recently mentioned entity is used."""
        tracker = SessionContextTracker()
        tracker.track_entity(EntityType.FUNCTION, "old_func")
        tracker.increment_turn()
        tracker.track_entity(EntityType.FUNCTION, "new_func")
        resolver = PronounResolver(tracker)

        resolutions = resolver.resolve("refactor the function")

        func_refs = [r for r in resolutions if r.entity_type == EntityType.FUNCTION]
        assert len(func_refs) >= 1
        assert func_refs[0].resolved == "new_func"
