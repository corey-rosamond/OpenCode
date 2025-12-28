"""Tests for project type detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from code_forge.context.project_detector import (
    PROJECT_MARKERS,
    ProjectInfo,
    ProjectType,
    ProjectTypeDetector,
    detect_project,
    get_detector,
)


class TestProjectType:
    """Tests for ProjectType enum."""

    def test_all_types_have_values(self) -> None:
        """Test that all project types have string values."""
        for ptype in ProjectType:
            assert isinstance(ptype.value, str)
            assert len(ptype.value) > 0

    def test_unknown_type_exists(self) -> None:
        """Test that UNKNOWN type exists for fallback."""
        assert ProjectType.UNKNOWN.value == "unknown"

    def test_common_languages_covered(self) -> None:
        """Test that common programming languages are covered."""
        common = ["python", "javascript", "typescript", "rust", "go", "java"]
        type_values = [t.value for t in ProjectType]
        for lang in common:
            assert lang in type_values


class TestProjectInfo:
    """Tests for ProjectInfo dataclass."""

    def test_default_values(self) -> None:
        """Test default values for ProjectInfo."""
        info = ProjectInfo()
        assert info.project_type == ProjectType.UNKNOWN
        assert info.secondary_types == []
        assert info.name is None
        assert info.version is None
        assert info.frameworks == []
        assert info.package_manager is None
        assert info.test_framework is None
        assert info.build_tool is None
        assert info.markers == []
        assert info.metadata == {}

    def test_to_context_string_unknown(self) -> None:
        """Test context string for unknown project."""
        info = ProjectInfo()
        result = info.to_context_string()
        assert "Unknown" in result

    def test_to_context_string_python(self) -> None:
        """Test context string for Python project."""
        info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            name="myproject",
            version="1.0.0",
            frameworks=["FastAPI", "Pytest"],
            package_manager="Poetry",
            test_framework="pytest",
        )
        result = info.to_context_string()
        assert "Project Type: Python" in result
        assert "Project: myproject v1.0.0" in result
        assert "Frameworks: FastAPI, Pytest" in result
        assert "Package Manager: Poetry" in result
        assert "Test Framework: pytest" in result

    def test_to_context_string_with_secondary_types(self) -> None:
        """Test context string with secondary types."""
        info = ProjectInfo(
            project_type=ProjectType.TYPESCRIPT,
            secondary_types=[ProjectType.DOCKER, ProjectType.SHELL],
        )
        result = info.to_context_string()
        assert "Also Uses: Docker, Shell" in result


class TestProjectMarkers:
    """Tests for PROJECT_MARKERS configuration."""

    def test_markers_defined_for_common_types(self) -> None:
        """Test that markers are defined for common project types."""
        common_types = [
            ProjectType.PYTHON,
            ProjectType.JAVASCRIPT,
            ProjectType.TYPESCRIPT,
            ProjectType.RUST,
            ProjectType.GO,
        ]
        for ptype in common_types:
            assert ptype in PROJECT_MARKERS
            assert len(PROJECT_MARKERS[ptype]) > 0

    def test_python_markers(self) -> None:
        """Test Python project markers."""
        markers = PROJECT_MARKERS[ProjectType.PYTHON]
        assert "pyproject.toml" in markers
        assert "requirements.txt" in markers
        assert "setup.py" in markers

    def test_javascript_markers(self) -> None:
        """Test JavaScript project markers."""
        markers = PROJECT_MARKERS[ProjectType.JAVASCRIPT]
        assert "package.json" in markers

    def test_rust_markers(self) -> None:
        """Test Rust project markers."""
        markers = PROJECT_MARKERS[ProjectType.RUST]
        assert "Cargo.toml" in markers


class TestProjectTypeDetector:
    """Tests for ProjectTypeDetector class."""

    @pytest.fixture
    def detector(self) -> ProjectTypeDetector:
        """Create a detector instance."""
        return ProjectTypeDetector()

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> Path:
        """Create a temporary project directory."""
        return tmp_path

    def test_init_default_depth(self) -> None:
        """Test default max_depth."""
        detector = ProjectTypeDetector()
        assert detector.max_depth == 2

    def test_init_custom_depth(self) -> None:
        """Test custom max_depth."""
        detector = ProjectTypeDetector(max_depth=3)
        assert detector.max_depth == 3

    def test_detect_nonexistent_directory(self, detector: ProjectTypeDetector) -> None:
        """Test detection on nonexistent directory."""
        info = detector.detect("/nonexistent/path")
        assert info.project_type == ProjectType.UNKNOWN

    def test_detect_empty_directory(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test detection on empty directory."""
        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.UNKNOWN

    def test_detect_python_pyproject(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Python detection via pyproject.toml."""
        pyproject = temp_project / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "testproject"
version = "1.0.0"
dependencies = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
        )

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.PYTHON
        assert info.name == "testproject"
        assert info.version == "1.0.0"
        assert "pyproject.toml" in info.markers

    def test_detect_python_requirements(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Python detection via requirements.txt."""
        (temp_project / "requirements.txt").write_text("flask==2.0.0\npytest")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.PYTHON

    def test_detect_javascript_package_json(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test JavaScript detection via package.json."""
        (temp_project / "package.json").write_text(
            json.dumps(
                {
                    "name": "myapp",
                    "version": "2.0.0",
                    "dependencies": {"react": "^18.0.0"},
                    "devDependencies": {"jest": "^29.0.0"},
                }
            )
        )

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.JAVASCRIPT
        assert info.name == "myapp"
        assert info.version == "2.0.0"
        assert "React" in info.frameworks
        assert "Jest" in info.frameworks

    def test_detect_typescript_tsconfig(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test TypeScript detection via tsconfig.json."""
        (temp_project / "package.json").write_text(
            json.dumps(
                {
                    "name": "tsapp",
                    "dependencies": {"typescript": "^5.0.0"},
                }
            )
        )
        (temp_project / "tsconfig.json").write_text("{}")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.TYPESCRIPT

    def test_detect_rust_cargo(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Rust detection via Cargo.toml."""
        (temp_project / "Cargo.toml").write_text(
            """
[package]
name = "myrust"
version = "0.1.0"

[dependencies]
tokio = "1.0"
"""
        )

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.RUST
        assert info.name == "myrust"
        assert info.version == "0.1.0"
        assert info.package_manager == "Cargo"
        assert info.build_tool == "Cargo"

    def test_detect_go_gomod(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Go detection via go.mod."""
        (temp_project / "go.mod").write_text(
            """module github.com/user/mygo

go 1.21

require github.com/gin-gonic/gin v1.9.0
"""
        )

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.GO
        assert info.name == "github.com/user/mygo"
        assert info.package_manager == "Go Modules"
        assert "Gin" in info.frameworks

    def test_detect_ruby_gemfile(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Ruby detection via Gemfile."""
        (temp_project / "Gemfile").write_text("source 'https://rubygems.org'\ngem 'rails'")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.RUBY
        assert info.package_manager == "Bundler"

    def test_detect_php_composer(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test PHP detection via composer.json."""
        (temp_project / "composer.json").write_text("{}")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.PHP
        assert info.package_manager == "Composer"

    def test_detect_java_pom(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Java detection via pom.xml."""
        (temp_project / "pom.xml").write_text("<project></project>")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.JAVA

    def test_detect_java_gradle(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Java detection via build.gradle."""
        (temp_project / "build.gradle").write_text("apply plugin: 'java'")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.JAVA
        assert info.build_tool == "Gradle"

    def test_detect_docker(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Docker detection via Dockerfile."""
        (temp_project / "Dockerfile").write_text("FROM python:3.11")

        info = detector.detect(temp_project)
        # Docker is usually secondary
        assert (
            info.project_type == ProjectType.DOCKER
            or ProjectType.DOCKER in info.secondary_types
        )

    def test_detect_multiple_types(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test detection of multiple project types."""
        # Python + Docker
        (temp_project / "pyproject.toml").write_text("[project]\nname = 'test'")
        (temp_project / "Dockerfile").write_text("FROM python:3.11")
        (temp_project / "docker-compose.yml").write_text("version: '3'")

        info = detector.detect(temp_project)
        assert info.project_type == ProjectType.PYTHON
        assert ProjectType.DOCKER in info.secondary_types

    def test_detect_package_manager_poetry(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Poetry package manager detection."""
        (temp_project / "pyproject.toml").write_text("[project]\nname = 'test'")
        (temp_project / "poetry.lock").write_text("")

        info = detector.detect(temp_project)
        assert info.package_manager == "Poetry"

    def test_detect_package_manager_pipenv(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Pipenv package manager detection."""
        (temp_project / "Pipfile").write_text("")
        (temp_project / "Pipfile.lock").write_text("{}")

        info = detector.detect(temp_project)
        assert info.package_manager == "Pipenv"

    def test_detect_package_manager_npm(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test npm package manager detection."""
        (temp_project / "package.json").write_text("{}")
        (temp_project / "package-lock.json").write_text("{}")

        info = detector.detect(temp_project)
        assert info.package_manager == "npm"

    def test_detect_package_manager_yarn(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Yarn package manager detection."""
        (temp_project / "package.json").write_text("{}")
        (temp_project / "yarn.lock").write_text("")

        info = detector.detect(temp_project)
        assert info.package_manager == "Yarn"

    def test_detect_package_manager_pnpm(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test pnpm package manager detection."""
        (temp_project / "package.json").write_text("{}")
        (temp_project / "pnpm-lock.yaml").write_text("")

        info = detector.detect(temp_project)
        assert info.package_manager == "pnpm"

    def test_detect_test_framework_pytest(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test pytest test framework detection."""
        (temp_project / "pyproject.toml").write_text("[project]\nname = 'test'")
        (temp_project / "pytest.ini").write_text("")

        info = detector.detect(temp_project)
        assert info.test_framework == "pytest"

    def test_detect_test_framework_jest(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Jest test framework detection."""
        (temp_project / "package.json").write_text("{}")
        (temp_project / "jest.config.js").write_text("")

        info = detector.detect(temp_project)
        assert info.test_framework == "jest"

    def test_detect_build_tool_webpack(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Webpack build tool detection."""
        (temp_project / "package.json").write_text("{}")
        (temp_project / "webpack.config.js").write_text("")

        info = detector.detect(temp_project)
        assert info.build_tool == "Webpack"

    def test_detect_build_tool_vite(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Vite build tool detection."""
        (temp_project / "package.json").write_text("{}")
        (temp_project / "vite.config.ts").write_text("")

        info = detector.detect(temp_project)
        assert info.build_tool == "Vite"

    def test_detect_build_tool_cmake(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test CMake build tool detection."""
        (temp_project / "CMakeLists.txt").write_text("")

        info = detector.detect(temp_project)
        assert info.build_tool == "CMake"

    def test_detect_framework_django(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Django framework detection."""
        (temp_project / "pyproject.toml").write_text(
            "[project]\nname = 'test'\ndependencies = ['django']"
        )
        (temp_project / "manage.py").write_text("")

        info = detector.detect(temp_project)
        assert "Django" in info.frameworks

    def test_detect_framework_fastapi(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test FastAPI framework detection."""
        (temp_project / "pyproject.toml").write_text(
            "[project]\nname = 'test'\ndependencies = ['fastapi']"
        )

        info = detector.detect(temp_project)
        assert "FastAPI" in info.frameworks

    def test_detect_framework_react(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test React framework detection."""
        (temp_project / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18.0.0"}})
        )

        info = detector.detect(temp_project)
        assert "React" in info.frameworks

    def test_detect_framework_nextjs(
        self, detector: ProjectTypeDetector, temp_project: Path
    ) -> None:
        """Test Next.js framework detection."""
        (temp_project / "package.json").write_text(
            json.dumps({"dependencies": {"next": "^13.0.0"}})
        )
        (temp_project / "next.config.js").write_text("")

        info = detector.detect(temp_project)
        assert "Next.js" in info.frameworks


class TestGetDetector:
    """Tests for get_detector singleton function."""

    def test_returns_detector(self) -> None:
        """Test that get_detector returns a ProjectTypeDetector."""
        detector = get_detector()
        assert isinstance(detector, ProjectTypeDetector)

    def test_returns_same_instance(self) -> None:
        """Test that get_detector returns the same instance."""
        d1 = get_detector()
        d2 = get_detector()
        assert d1 is d2


class TestDetectProject:
    """Tests for detect_project convenience function."""

    def test_detects_current_directory(self, tmp_path: Path) -> None:
        """Test detection of current directory."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        info = detect_project(tmp_path)
        assert info.project_type == ProjectType.PYTHON

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Test that string paths are accepted."""
        (tmp_path / "package.json").write_text("{}")
        info = detect_project(str(tmp_path))
        assert info.project_type == ProjectType.JAVASCRIPT

    def test_default_to_cwd(self) -> None:
        """Test that None defaults to current working directory."""
        with patch("code_forge.context.project_detector.Path.cwd") as mock_cwd:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_dir.return_value = True
            mock_path.glob.return_value = []
            mock_path.__truediv__ = lambda self, x: MagicMock(exists=lambda: False)
            mock_cwd.return_value = mock_path

            info = detect_project()
            # Should not raise, returns unknown for empty dir
            assert info.project_type == ProjectType.UNKNOWN
