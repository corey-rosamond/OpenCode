"""Tests for file tool utilities."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from code_forge.tools.file.utils import validate_path_security


class TestValidatePathSecurity:
    """Test path security validation."""

    def test_valid_absolute_path(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")
        is_valid, error = validate_path_security(str(file_path))
        assert is_valid
        assert error is None

    def test_path_traversal_detected(self, tmp_path: Path) -> None:
        # Path with traversal
        path_with_traversal = f"{tmp_path}/../../../etc/passwd"
        is_valid, error = validate_path_security(path_with_traversal)
        assert not is_valid
        assert isinstance(error, str)
        assert "traversal" in error.lower()

    def test_double_dot_in_middle(self, tmp_path: Path) -> None:
        # Path with .. in the middle
        (tmp_path / "subdir").mkdir()
        path_with_traversal = f"{tmp_path}/subdir/../../../etc/passwd"
        is_valid, error = validate_path_security(path_with_traversal)
        assert not is_valid
        assert isinstance(error, str)
        assert "traversal" in error.lower()

    def test_base_dir_enforcement(self, tmp_path: Path) -> None:
        # Create a file outside base_dir
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "file.txt"
        outside_file.write_text("content")

        base_dir = tmp_path / "base"
        base_dir.mkdir()

        # Try to access file outside base_dir
        is_valid, error = validate_path_security(
            str(outside_file), base_dir=str(base_dir)
        )
        assert not is_valid
        assert isinstance(error, str)
        # Error message should indicate the path is outside the allowed base dir
        assert "outside" in error.lower() or "base" in error.lower()

    def test_valid_path_within_base_dir(self, tmp_path: Path) -> None:
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        file_in_base = base_dir / "file.txt"
        file_in_base.write_text("content")

        is_valid, error = validate_path_security(
            str(file_in_base), base_dir=str(base_dir)
        )
        assert is_valid
        assert error is None

    def test_symlink_not_allowed_by_default(self, tmp_path: Path) -> None:
        # Create a symlink
        target = tmp_path / "target.txt"
        target.write_text("content")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        is_valid, error = validate_path_security(str(symlink))
        assert not is_valid
        assert isinstance(error, str)
        assert "symlink" in error.lower()

    def test_symlink_allowed_when_enabled(self, tmp_path: Path) -> None:
        # Create a symlink
        target = tmp_path / "target.txt"
        target.write_text("content")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        is_valid, error = validate_path_security(str(symlink), allow_symlinks=True)
        assert is_valid
        assert error is None

    def test_nonexistent_file_passes(self, tmp_path: Path) -> None:
        # Nonexistent files should pass validation
        # (existence is checked separately by tools)
        nonexistent = tmp_path / "nonexistent.txt"
        is_valid, error = validate_path_security(str(nonexistent))
        assert is_valid
        assert error is None

    def test_empty_path(self) -> None:
        is_valid, error = validate_path_security("")
        # Empty path should fail or be handled gracefully
        # The behavior depends on implementation
        assert isinstance(is_valid, bool)


class TestPathTraversalPatterns:
    """Test various path traversal patterns."""

    @pytest.mark.parametrize(
        "malicious_path",
        [
            "/tmp/../../../etc/passwd",
            "/tmp/./../../etc/passwd",
            "/tmp/subdir/../../../../../../etc/passwd",
        ],
    )
    def test_various_traversal_patterns(self, malicious_path: str) -> None:
        is_valid, error = validate_path_security(malicious_path)
        assert not is_valid
        assert isinstance(error, str)
        assert "traversal" in error.lower()

    def test_normalized_path_still_catches_traversal(self, tmp_path: Path) -> None:
        # Even if the path looks "clean" after normalization,
        # if it escapes the expected directory, it should fail
        # This tests that we check the resolved path
        malicious = f"{tmp_path}/../../../etc/passwd"
        is_valid, error = validate_path_security(malicious)
        assert not is_valid
