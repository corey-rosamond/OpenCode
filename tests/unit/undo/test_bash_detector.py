"""Tests for BashFileDetector."""

from __future__ import annotations

import pytest

from code_forge.undo.bash_detector import BashFileDetector


class TestBashFileDetector:
    """Tests for BashFileDetector."""

    @pytest.fixture
    def working_dir(self) -> str:
        """Test working directory."""
        return "/project"

    def test_detect_output_redirect(self, working_dir: str) -> None:
        """Test detecting output redirection."""
        files = BashFileDetector.detect_files("echo hello > output.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/output.txt"

    def test_detect_append_redirect(self, working_dir: str) -> None:
        """Test detecting append redirection."""
        files = BashFileDetector.detect_files("echo hello >> log.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/log.txt"

    def test_detect_rm_command(self, working_dir: str) -> None:
        """Test detecting rm command."""
        files = BashFileDetector.detect_files("rm file.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/file.txt"

    def test_detect_rm_with_flags(self, working_dir: str) -> None:
        """Test detecting rm with flags."""
        files = BashFileDetector.detect_files("rm -rf directory", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/directory"

    def test_detect_mv_command(self, working_dir: str) -> None:
        """Test detecting mv command (destination)."""
        files = BashFileDetector.detect_files("mv source.txt dest.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/dest.txt"

    def test_detect_cp_command(self, working_dir: str) -> None:
        """Test detecting cp command (destination)."""
        files = BashFileDetector.detect_files("cp source.txt copy.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/copy.txt"

    def test_detect_touch_command(self, working_dir: str) -> None:
        """Test detecting touch command."""
        files = BashFileDetector.detect_files("touch newfile.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/project/newfile.txt"

    def test_detect_mkdir_command(self, working_dir: str) -> None:
        """Test detecting mkdir command."""
        files = BashFileDetector.detect_files("mkdir -p new/directory", working_dir)

        assert len(files) == 1
        assert "/project/new/directory" in files[0]

    def test_detect_sed_inplace(self, working_dir: str) -> None:
        """Test detecting sed in-place edit."""
        files = BashFileDetector.detect_files(
            "sed -i 's/foo/bar/' config.txt", working_dir
        )

        assert len(files) == 1
        assert files[0] == "/project/config.txt"

    def test_detect_tee_command(self, working_dir: str) -> None:
        """Test detecting tee command."""
        files = BashFileDetector.detect_files(
            "echo hello | tee output.txt", working_dir
        )

        assert len(files) == 1
        assert files[0] == "/project/output.txt"

    def test_detect_multiple_files(self, working_dir: str) -> None:
        """Test detecting multiple file modifications."""
        files = BashFileDetector.detect_files(
            "echo hello > file1.txt && rm file2.txt", working_dir
        )

        assert len(files) == 2
        assert "/project/file1.txt" in files
        assert "/project/file2.txt" in files

    def test_detect_absolute_path(self, working_dir: str) -> None:
        """Test detecting absolute paths."""
        files = BashFileDetector.detect_files("echo hello > /tmp/output.txt", working_dir)

        assert len(files) == 1
        assert files[0] == "/tmp/output.txt"

    def test_skip_dev_null(self, working_dir: str) -> None:
        """Test that /dev/null is skipped."""
        files = BashFileDetector.detect_files("echo hello > /dev/null", working_dir)

        assert len(files) == 0

    def test_skip_quoted_path_with_variable(self, working_dir: str) -> None:
        """Test that paths with variables are skipped."""
        files = BashFileDetector.detect_files("echo hello > $OUTPUT_FILE", working_dir)

        assert len(files) == 0

    def test_no_duplicates(self, working_dir: str) -> None:
        """Test that duplicate paths are not returned."""
        files = BashFileDetector.detect_files(
            "echo a > file.txt && echo b > file.txt", working_dir
        )

        assert len(files) == 1

    def test_empty_command(self, working_dir: str) -> None:
        """Test empty command."""
        files = BashFileDetector.detect_files("", working_dir)

        assert len(files) == 0

    def test_no_file_modification(self, working_dir: str) -> None:
        """Test command that doesn't modify files."""
        files = BashFileDetector.detect_files("ls -la", working_dir)

        assert len(files) == 0


class TestBashFileDetectorHelpers:
    """Tests for BashFileDetector helper methods."""

    def test_is_destructive_rm(self) -> None:
        """Test detecting destructive rm command."""
        assert BashFileDetector.is_destructive("rm file.txt") is True

    def test_is_destructive_redirect(self) -> None:
        """Test detecting destructive redirect."""
        assert BashFileDetector.is_destructive("echo > file.txt") is True

    def test_is_destructive_mv(self) -> None:
        """Test detecting destructive mv command."""
        assert BashFileDetector.is_destructive("mv a b") is True

    def test_is_not_destructive(self) -> None:
        """Test non-destructive command."""
        assert BashFileDetector.is_destructive("ls -la") is False
        assert BashFileDetector.is_destructive("cat file.txt") is False

    def test_get_command_type_delete(self) -> None:
        """Test command type detection: delete."""
        assert BashFileDetector.get_command_type("rm file.txt") == "delete"
        assert BashFileDetector.get_command_type("rmdir dir") == "delete"

    def test_get_command_type_move(self) -> None:
        """Test command type detection: move."""
        assert BashFileDetector.get_command_type("mv a b") == "move"

    def test_get_command_type_copy(self) -> None:
        """Test command type detection: copy."""
        assert BashFileDetector.get_command_type("cp a b") == "copy"

    def test_get_command_type_create(self) -> None:
        """Test command type detection: create."""
        assert BashFileDetector.get_command_type("touch file.txt") == "create"
        assert BashFileDetector.get_command_type("mkdir dir") == "create"

    def test_get_command_type_modify(self) -> None:
        """Test command type detection: modify."""
        assert BashFileDetector.get_command_type("echo > file.txt") == "modify"
        assert BashFileDetector.get_command_type("sed -i 's/a/b/' file") == "modify"

    def test_get_command_type_other(self) -> None:
        """Test command type detection: other."""
        assert BashFileDetector.get_command_type("ls -la") == "other"
        assert BashFileDetector.get_command_type("cat file.txt") == "other"
