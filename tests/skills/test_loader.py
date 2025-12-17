"""Tests for skill loader."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_forge.skills.base import Skill
from code_forge.skills.loader import (
    SkillLoadError,
    SkillLoader,
    get_default_search_paths,
)
from code_forge.skills.parser import SkillParser


class TestSkillLoader:
    """Tests for SkillLoader."""

    @pytest.fixture
    def loader(self) -> SkillLoader:
        """Create loader instance."""
        return SkillLoader()

    @pytest.fixture
    def skills_dir(self, tmp_path: Path) -> Path:
        """Create a temporary skills directory with sample skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create YAML skill
        yaml_skill = skills_dir / "pdf.yaml"
        yaml_skill.write_text("""
name: pdf
description: PDF skill
prompt: Work with PDFs
tools:
  - read
""")

        # Create Markdown skill
        md_skill = skills_dir / "excel.md"
        md_skill.write_text("""---
name: excel
description: Excel skill
---

Work with spreadsheets.
""")

        return skills_dir

    def test_create_loader(self) -> None:
        """Test creating a loader."""
        loader = SkillLoader()
        assert loader.search_paths == []
        assert isinstance(loader.parser, SkillParser)

    def test_create_loader_with_paths(self, tmp_path: Path) -> None:
        """Test creating loader with search paths."""
        loader = SkillLoader(search_paths=[tmp_path])
        assert tmp_path in loader.search_paths

    def test_create_loader_with_parser(self) -> None:
        """Test creating loader with custom parser."""
        parser = SkillParser()
        loader = SkillLoader(parser=parser)
        assert loader.parser is parser

    def test_add_search_path(self, loader: SkillLoader, tmp_path: Path) -> None:
        """Test adding a search path."""
        loader.add_search_path(tmp_path)
        assert tmp_path in loader.search_paths

        # Adding same path again should not duplicate
        loader.add_search_path(tmp_path)
        assert loader.search_paths.count(tmp_path) == 1

    def test_load_from_file_yaml(
        self, loader: SkillLoader, skills_dir: Path
    ) -> None:
        """Test loading a YAML skill file."""
        skill = loader.load_from_file(skills_dir / "pdf.yaml")
        assert isinstance(skill, Skill)
        assert skill.name == "pdf"
        assert skill.description == "PDF skill"

    def test_load_from_file_md(
        self, loader: SkillLoader, skills_dir: Path
    ) -> None:
        """Test loading a Markdown skill file."""
        skill = loader.load_from_file(skills_dir / "excel.md")
        assert isinstance(skill, Skill)
        assert skill.name == "excel"

    def test_load_from_file_nonexistent(self, loader: SkillLoader) -> None:
        """Test loading a nonexistent file."""
        skill = loader.load_from_file(Path("/nonexistent/skill.yaml"))
        assert skill is None

    def test_load_from_file_unsupported_extension(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test loading file with unsupported extension."""
        txt_file = tmp_path / "skill.txt"
        txt_file.write_text("content")
        skill = loader.load_from_file(txt_file)
        assert skill is None

    def test_load_from_file_invalid_content(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test loading file with invalid content."""
        invalid_skill = tmp_path / "invalid.yaml"
        invalid_skill.write_text("not: valid: yaml: syntax:")
        skill = loader.load_from_file(invalid_skill)
        assert skill is None

    def test_load_from_directory(
        self, loader: SkillLoader, skills_dir: Path
    ) -> None:
        """Test loading all skills from a directory."""
        skills = loader.load_from_directory(skills_dir)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert "pdf" in names
        assert "excel" in names

    def test_load_from_directory_nonexistent(self, loader: SkillLoader) -> None:
        """Test loading from nonexistent directory."""
        skills = loader.load_from_directory(Path("/nonexistent"))
        assert skills == []

    def test_load_from_directory_not_a_dir(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test loading from a file instead of directory."""
        file = tmp_path / "file.txt"
        file.write_text("content")
        skills = loader.load_from_directory(file)
        assert skills == []

    def test_load_from_directory_empty(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test loading from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        skills = loader.load_from_directory(empty_dir)
        assert skills == []

    def test_load_from_directory_skips_invalid(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test that invalid skills are skipped."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Valid skill
        valid = skills_dir / "valid.yaml"
        valid.write_text("""
name: valid
description: Valid skill
prompt: Test
""")

        # Invalid skill (missing fields)
        invalid = skills_dir / "invalid.yaml"
        invalid.write_text("""
name: invalid
""")

        skills = loader.load_from_directory(skills_dir)
        assert len(skills) == 1
        assert skills[0].name == "valid"

    def test_discover_skills(
        self, loader: SkillLoader, skills_dir: Path
    ) -> None:
        """Test discovering skills from search paths."""
        loader.add_search_path(skills_dir)
        skills = loader.discover_skills()
        assert len(skills) == 2

    def test_discover_skills_multiple_paths(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test discovering from multiple search paths."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "skill1.yaml").write_text("""
name: skill1
description: Skill 1
prompt: Test
""")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "skill2.yaml").write_text("""
name: skill2
description: Skill 2
prompt: Test
""")

        loader.add_search_path(dir1)
        loader.add_search_path(dir2)
        skills = loader.discover_skills()
        assert len(skills) == 2

    def test_discover_skills_duplicates(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test that duplicate skills are skipped."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "skill.yaml").write_text("""
name: skill
description: First
prompt: Test
""")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "skill.yaml").write_text("""
name: skill
description: Second
prompt: Test
""")

        loader.add_search_path(dir1)
        loader.add_search_path(dir2)
        skills = loader.discover_skills()

        # Only first should be loaded
        assert len(skills) == 1
        assert skills[0].description == "First"

    def test_reload_skill(
        self, loader: SkillLoader, skills_dir: Path
    ) -> None:
        """Test reloading a skill."""
        loader.add_search_path(skills_dir)
        skill = loader.reload_skill("pdf")
        assert isinstance(skill, Skill)
        assert skill.name == "pdf"

    def test_reload_skill_not_found(self, loader: SkillLoader) -> None:
        """Test reloading a skill that doesn't exist."""
        skill = loader.reload_skill("nonexistent")
        assert skill is None

    def test_reload_skill_checks_extensions(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test that reload checks multiple extensions."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create skill with .yml extension
        (skills_dir / "skill.yml").write_text("""
name: skill
description: YAML skill
prompt: Test
""")

        loader.add_search_path(skills_dir)
        skill = loader.reload_skill("skill")
        assert isinstance(skill, Skill)
        assert skill.name == "skill"

    def test_on_error_callback(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test error callback is called."""
        errors_received: list[tuple[str, list[str]]] = []

        def error_handler(path: str, errors: list[str]) -> None:
            errors_received.append((path, errors))

        loader.on_error(error_handler)

        # Try to load nonexistent file
        loader.load_from_file(Path("/nonexistent/skill.yaml"))

        assert len(errors_received) == 1
        assert "nonexistent" in errors_received[0][0]

    def test_on_error_callback_exception(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test that callback exceptions are handled."""
        def bad_handler(path: str, errors: list[str]) -> None:
            raise RuntimeError("Handler error")

        loader.on_error(bad_handler)

        # Should not raise
        loader.load_from_file(Path("/nonexistent/skill.yaml"))

    def test_get_skill_files(
        self, loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test getting skill files from directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "a.yaml").touch()
        (skills_dir / "b.md").touch()
        (skills_dir / "c.yml").touch()
        (skills_dir / "d.txt").touch()  # Should be ignored

        files = loader._get_skill_files(skills_dir)
        assert len(files) == 3
        # Should be sorted
        assert files[0].name == "a.yaml"


class TestGetDefaultSearchPaths:
    """Tests for get_default_search_paths."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        paths = get_default_search_paths()
        assert isinstance(paths, list)

    @patch("code_forge.skills.loader.Path.home")
    def test_includes_user_dir_if_exists(self, mock_home: MagicMock) -> None:
        """Test that user dir is included if it exists."""
        mock_path = MagicMock()
        mock_path.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_home.return_value = mock_path

        paths = get_default_search_paths()
        # The mock should have been called
        mock_home.assert_called()

    @patch("code_forge.skills.loader.Path.home")
    @patch("code_forge.skills.loader.Path.cwd")
    def test_no_paths_if_dirs_dont_exist(
        self, mock_cwd: MagicMock, mock_home: MagicMock
    ) -> None:
        """Test that no paths are returned if dirs don't exist."""
        mock_path = MagicMock()
        mock_path.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False
        mock_home.return_value = mock_path
        mock_cwd.return_value = mock_path

        paths = get_default_search_paths()
        assert paths == []
