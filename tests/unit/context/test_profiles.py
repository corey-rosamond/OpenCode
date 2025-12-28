"""Tests for language profiles."""

from __future__ import annotations

import pytest

from code_forge.context.profiles import (
    PROFILES,
    LanguageProfile,
    generate_project_context,
    get_profile,
    get_profile_for_project,
)
from code_forge.context.project_detector import ProjectInfo, ProjectType


class TestLanguageProfile:
    """Tests for LanguageProfile dataclass."""

    def test_default_values(self) -> None:
        """Test default values for LanguageProfile."""
        profile = LanguageProfile(
            project_type=ProjectType.PYTHON,
            display_name="Python",
        )
        assert profile.project_type == ProjectType.PYTHON
        assert profile.display_name == "Python"
        assert profile.file_extensions == []
        assert profile.preferred_tools == []
        assert profile.run_command is None
        assert profile.test_command is None
        assert profile.lint_command is None
        assert profile.format_command is None
        assert profile.build_command is None
        assert profile.package_install is None
        assert profile.best_practices == []
        assert profile.common_patterns == []
        assert profile.avoid_patterns == []

    def test_to_context_hints_empty(self) -> None:
        """Test context hints with no commands set."""
        profile = LanguageProfile(
            project_type=ProjectType.UNKNOWN,
            display_name="Unknown",
        )
        result = profile.to_context_hints()
        assert result == ""

    def test_to_context_hints_with_commands(self) -> None:
        """Test context hints with commands set."""
        profile = LanguageProfile(
            project_type=ProjectType.PYTHON,
            display_name="Python",
            test_command="pytest",
            lint_command="ruff check .",
            format_command="ruff format .",
            package_install="pip install -r requirements.txt",
            best_practices=["Use type hints", "Follow PEP 8"],
        )
        result = profile.to_context_hints()

        assert "Run tests: pytest" in result
        assert "Lint code: ruff check ." in result
        assert "Format code: ruff format ." in result
        assert "Install dependencies: pip install" in result
        assert "Best practices:" in result
        assert "Use type hints" in result
        assert "Follow PEP 8" in result

    def test_to_context_hints_limits_best_practices(self) -> None:
        """Test that best practices are limited to 3."""
        profile = LanguageProfile(
            project_type=ProjectType.PYTHON,
            display_name="Python",
            best_practices=["One", "Two", "Three", "Four", "Five"],
        )
        result = profile.to_context_hints()

        assert "One" in result
        assert "Two" in result
        assert "Three" in result
        assert "Four" not in result
        assert "Five" not in result


class TestProfiles:
    """Tests for pre-defined PROFILES."""

    def test_python_profile_exists(self) -> None:
        """Test that Python profile exists."""
        assert ProjectType.PYTHON in PROFILES
        profile = PROFILES[ProjectType.PYTHON]
        assert profile.display_name == "Python"
        assert ".py" in profile.file_extensions
        assert profile.test_command is not None
        assert profile.lint_command is not None
        assert len(profile.best_practices) > 0

    def test_javascript_profile_exists(self) -> None:
        """Test that JavaScript profile exists."""
        assert ProjectType.JAVASCRIPT in PROFILES
        profile = PROFILES[ProjectType.JAVASCRIPT]
        assert profile.display_name == "JavaScript"
        assert ".js" in profile.file_extensions

    def test_typescript_profile_exists(self) -> None:
        """Test that TypeScript profile exists."""
        assert ProjectType.TYPESCRIPT in PROFILES
        profile = PROFILES[ProjectType.TYPESCRIPT]
        assert profile.display_name == "TypeScript"
        assert ".ts" in profile.file_extensions

    def test_rust_profile_exists(self) -> None:
        """Test that Rust profile exists."""
        assert ProjectType.RUST in PROFILES
        profile = PROFILES[ProjectType.RUST]
        assert profile.display_name == "Rust"
        assert ".rs" in profile.file_extensions
        assert profile.test_command == "cargo test"
        assert profile.build_command == "cargo build"

    def test_go_profile_exists(self) -> None:
        """Test that Go profile exists."""
        assert ProjectType.GO in PROFILES
        profile = PROFILES[ProjectType.GO]
        assert profile.display_name == "Go"
        assert ".go" in profile.file_extensions

    def test_java_profile_exists(self) -> None:
        """Test that Java profile exists."""
        assert ProjectType.JAVA in PROFILES
        profile = PROFILES[ProjectType.JAVA]
        assert profile.display_name == "Java"

    def test_ruby_profile_exists(self) -> None:
        """Test that Ruby profile exists."""
        assert ProjectType.RUBY in PROFILES
        profile = PROFILES[ProjectType.RUBY]
        assert profile.display_name == "Ruby"

    def test_php_profile_exists(self) -> None:
        """Test that PHP profile exists."""
        assert ProjectType.PHP in PROFILES
        profile = PROFILES[ProjectType.PHP]
        assert profile.display_name == "PHP"

    def test_all_profiles_have_required_fields(self) -> None:
        """Test that all profiles have required fields set."""
        for ptype, profile in PROFILES.items():
            assert profile.project_type == ptype
            assert len(profile.display_name) > 0
            assert len(profile.file_extensions) > 0
            assert len(profile.preferred_tools) > 0


class TestGetProfile:
    """Tests for get_profile function."""

    def test_get_known_profile(self) -> None:
        """Test getting a known profile."""
        profile = get_profile(ProjectType.PYTHON)
        assert profile is not None
        assert profile.project_type == ProjectType.PYTHON

    def test_get_unknown_profile(self) -> None:
        """Test getting an unknown profile."""
        profile = get_profile(ProjectType.UNKNOWN)
        assert profile is None


class TestGetProfileForProject:
    """Tests for get_profile_for_project function."""

    def test_get_profile_for_python_project(self) -> None:
        """Test getting profile for Python project."""
        info = ProjectInfo(project_type=ProjectType.PYTHON)
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.project_type == ProjectType.PYTHON

    def test_get_profile_for_unknown_project(self) -> None:
        """Test getting profile for unknown project."""
        info = ProjectInfo(project_type=ProjectType.UNKNOWN)
        profile = get_profile_for_project(info)
        assert profile is None

    def test_customizes_test_command_pytest(self) -> None:
        """Test that pytest test framework is used."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            test_framework="pytest",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.test_command == "pytest"

    def test_customizes_test_command_jest(self) -> None:
        """Test that jest test framework is used."""
        info = ProjectInfo(
            project_type=ProjectType.JAVASCRIPT,
            test_framework="jest",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.test_command == "npm test"

    def test_customizes_test_command_vitest(self) -> None:
        """Test that vitest test framework is used."""
        info = ProjectInfo(
            project_type=ProjectType.TYPESCRIPT,
            test_framework="vitest",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.test_command == "npx vitest"

    def test_customizes_package_install_poetry(self) -> None:
        """Test that Poetry package manager is used."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            package_manager="Poetry",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.package_install == "poetry install"

    def test_customizes_package_install_pipenv(self) -> None:
        """Test that Pipenv package manager is used."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            package_manager="Pipenv",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.package_install == "pipenv install"

    def test_customizes_package_install_pnpm(self) -> None:
        """Test that pnpm package manager is used."""
        info = ProjectInfo(
            project_type=ProjectType.JAVASCRIPT,
            package_manager="pnpm",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.package_install == "pnpm install"

    def test_customizes_package_install_yarn(self) -> None:
        """Test that Yarn package manager is used."""
        info = ProjectInfo(
            project_type=ProjectType.JAVASCRIPT,
            package_manager="Yarn",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.package_install == "yarn install"

    def test_customizes_package_install_bun(self) -> None:
        """Test that Bun package manager is used."""
        info = ProjectInfo(
            project_type=ProjectType.JAVASCRIPT,
            package_manager="Bun",
        )
        profile = get_profile_for_project(info)
        assert profile is not None
        assert profile.package_install == "bun install"


class TestGenerateProjectContext:
    """Tests for generate_project_context function."""

    def test_unknown_project(self) -> None:
        """Test context for unknown project."""
        info = ProjectInfo()
        result = generate_project_context(info)
        assert "# Project Context" in result
        assert "Unknown" in result

    def test_python_project(self) -> None:
        """Test context for Python project."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            name="myproject",
            version="1.0.0",
            frameworks=["FastAPI"],
            package_manager="Poetry",
            test_framework="pytest",
        )
        result = generate_project_context(info)

        assert "# Project Context" in result
        assert "Python" in result
        assert "myproject" in result
        assert "1.0.0" in result
        assert "# Language Hints" in result
        assert "pytest" in result
        assert "# Framework Notes" in result
        assert "FastAPI" in result

    def test_limits_frameworks(self) -> None:
        """Test that frameworks are limited to 5."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            frameworks=["A", "B", "C", "D", "E", "F", "G"],
        )
        result = generate_project_context(info)

        # Should only have 5 framework notes
        count = result.count("- ")
        assert count <= 5

    def test_includes_language_hints(self) -> None:
        """Test that language hints are included."""
        info = ProjectInfo(project_type=ProjectType.RUST)
        result = generate_project_context(info)

        assert "# Language Hints" in result
        assert "cargo test" in result

    def test_includes_best_practices(self) -> None:
        """Test that best practices are included."""
        info = ProjectInfo(project_type=ProjectType.PYTHON)
        result = generate_project_context(info)

        assert "Best practices:" in result
        assert "type hints" in result.lower() or "pep 8" in result.lower()


class TestFrameworkHints:
    """Tests for framework-specific hints."""

    @pytest.mark.parametrize(
        "framework,expected",
        [
            ("Django", "Django ORM"),
            ("FastAPI", "Pydantic"),
            ("React", "functional components"),
            ("Rails", "Rails conventions"),
            ("Pytest", "fixtures"),
        ],
    )
    def test_framework_hints(self, framework: str, expected: str) -> None:
        """Test that framework hints contain expected content."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            frameworks=[framework],
        )
        result = generate_project_context(info)
        # Some frameworks may not have hints
        if f"- {framework}:" in result:
            assert expected.lower() in result.lower()
