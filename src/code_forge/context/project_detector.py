"""Project type detection for context-aware assistance.

This module provides automatic detection of project types based on
marker files, enabling language-specific suggestions and tool hints.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Supported project types."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    KOTLIN = "kotlin"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    SCALA = "scala"
    ELIXIR = "elixir"
    HASKELL = "haskell"
    SHELL = "shell"
    DOCKER = "docker"
    TERRAFORM = "terraform"
    UNKNOWN = "unknown"


@dataclass
class ProjectInfo:
    """Detected project information.

    Attributes:
        project_type: Primary project type.
        secondary_types: Additional project types detected.
        name: Project name if detected.
        version: Project version if detected.
        frameworks: Detected frameworks (e.g., Django, React, FastAPI).
        package_manager: Detected package manager (npm, pip, cargo, etc.).
        test_framework: Detected test framework (pytest, jest, etc.).
        build_tool: Detected build tool (webpack, make, gradle, etc.).
        markers: Files that indicated the project type.
        metadata: Additional project metadata.
    """

    project_type: ProjectType = ProjectType.UNKNOWN
    secondary_types: list[ProjectType] = field(default_factory=list)
    name: str | None = None
    version: str | None = None
    frameworks: list[str] = field(default_factory=list)
    package_manager: str | None = None
    test_framework: str | None = None
    build_tool: str | None = None
    markers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_context_string(self) -> str:
        """Generate a context string for injection into prompts.

        Returns:
            Formatted string describing the project.
        """
        lines = []

        # Primary type
        type_name = self.project_type.value.title()
        if self.project_type != ProjectType.UNKNOWN:
            lines.append(f"Project Type: {type_name}")

        # Name and version
        if self.name:
            version_str = f" v{self.version}" if self.version else ""
            lines.append(f"Project: {self.name}{version_str}")

        # Frameworks
        if self.frameworks:
            lines.append(f"Frameworks: {', '.join(self.frameworks)}")

        # Package manager
        if self.package_manager:
            lines.append(f"Package Manager: {self.package_manager}")

        # Test framework
        if self.test_framework:
            lines.append(f"Test Framework: {self.test_framework}")

        # Build tool
        if self.build_tool:
            lines.append(f"Build Tool: {self.build_tool}")

        # Secondary types
        if self.secondary_types:
            secondary = [t.value.title() for t in self.secondary_types]
            lines.append(f"Also Uses: {', '.join(secondary)}")

        return "\n".join(lines) if lines else "Project Type: Unknown"


# Marker file patterns for each project type
PROJECT_MARKERS: dict[ProjectType, list[str]] = {
    ProjectType.PYTHON: [
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "tox.ini",
        "pytest.ini",
        ".python-version",
    ],
    ProjectType.JAVASCRIPT: [
        "package.json",
        ".npmrc",
        "yarn.lock",
        "pnpm-lock.yaml",
        ".nvmrc",
    ],
    ProjectType.TYPESCRIPT: [
        "tsconfig.json",
        "tsconfig.base.json",
    ],
    ProjectType.RUST: [
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        ".rustfmt.toml",
    ],
    ProjectType.GO: [
        "go.mod",
        "go.sum",
        "go.work",
    ],
    ProjectType.JAVA: [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        ".mvn",
    ],
    ProjectType.KOTLIN: [
        "build.gradle.kts",
        "settings.gradle.kts",
    ],
    ProjectType.CSHARP: [
        "*.csproj",
        "*.sln",
        "nuget.config",
        "global.json",
    ],
    ProjectType.CPP: [
        "CMakeLists.txt",
        "Makefile",
        "*.vcxproj",
        "conanfile.txt",
        "conanfile.py",
        "meson.build",
    ],
    ProjectType.C: [
        "Makefile",
        "CMakeLists.txt",
    ],
    ProjectType.RUBY: [
        "Gemfile",
        "Gemfile.lock",
        ".ruby-version",
        "Rakefile",
        "*.gemspec",
    ],
    ProjectType.PHP: [
        "composer.json",
        "composer.lock",
        "artisan",
        "phpunit.xml",
    ],
    ProjectType.SWIFT: [
        "Package.swift",
        "*.xcodeproj",
        "*.xcworkspace",
        "Podfile",
    ],
    ProjectType.SCALA: [
        "build.sbt",
        "project/build.properties",
    ],
    ProjectType.ELIXIR: [
        "mix.exs",
        "mix.lock",
    ],
    ProjectType.HASKELL: [
        "stack.yaml",
        "cabal.project",
        "*.cabal",
    ],
    ProjectType.SHELL: [
        "*.sh",
        ".bashrc",
        ".zshrc",
    ],
    ProjectType.DOCKER: [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".dockerignore",
    ],
    ProjectType.TERRAFORM: [
        "*.tf",
        "terraform.tfstate",
        ".terraform.lock.hcl",
    ],
}


# Framework detection patterns
FRAMEWORK_PATTERNS: dict[str, dict[str, Any]] = {
    # Python frameworks
    "Django": {"files": ["manage.py"], "deps": ["django"]},
    "FastAPI": {"deps": ["fastapi"]},
    "Flask": {"deps": ["flask"]},
    "Pytest": {"files": ["pytest.ini", "conftest.py"], "deps": ["pytest"]},
    "SQLAlchemy": {"deps": ["sqlalchemy"]},
    "Pydantic": {"deps": ["pydantic"]},
    # JavaScript/TypeScript frameworks
    "React": {"deps": ["react"]},
    "Vue": {"deps": ["vue"]},
    "Angular": {"files": ["angular.json"], "deps": ["@angular/core"]},
    "Next.js": {"files": ["next.config.js", "next.config.mjs"], "deps": ["next"]},
    "Express": {"deps": ["express"]},
    "Nest.js": {"deps": ["@nestjs/core"]},
    "Jest": {"files": ["jest.config.js", "jest.config.ts"], "deps": ["jest"]},
    "Vitest": {"files": ["vitest.config.ts"], "deps": ["vitest"]},
    # Rust frameworks
    "Tokio": {"deps": ["tokio"]},
    "Actix": {"deps": ["actix-web"]},
    "Axum": {"deps": ["axum"]},
    # Go frameworks
    "Gin": {"deps": ["github.com/gin-gonic/gin"]},
    "Echo": {"deps": ["github.com/labstack/echo"]},
    "Fiber": {"deps": ["github.com/gofiber/fiber"]},
    # Ruby frameworks
    "Rails": {"files": ["config/application.rb"], "deps": ["rails"]},
    "Sinatra": {"deps": ["sinatra"]},
    "RSpec": {"files": [".rspec"], "deps": ["rspec"]},
    # PHP frameworks
    "Laravel": {"files": ["artisan"], "deps": ["laravel/framework"]},
    "Symfony": {"deps": ["symfony/framework-bundle"]},
    "PHPUnit": {"files": ["phpunit.xml"], "deps": ["phpunit/phpunit"]},
}


class ProjectTypeDetector:
    """Detects project type from directory contents.

    This class analyzes a directory to determine the project type(s),
    frameworks, and other metadata to enable context-aware assistance.

    Example:
        ```python
        detector = ProjectTypeDetector()
        info = detector.detect("/path/to/project")
        print(info.project_type)  # ProjectType.PYTHON
        print(info.frameworks)    # ["FastAPI", "Pytest"]
        ```
    """

    def __init__(self, max_depth: int = 2) -> None:
        """Initialize the detector.

        Args:
            max_depth: Maximum directory depth to search for markers.
        """
        self.max_depth = max_depth

    def detect(self, directory: str | Path) -> ProjectInfo:
        """Detect project type from directory.

        Args:
            directory: Path to the project directory.

        Returns:
            ProjectInfo with detected information.
        """
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            logger.warning(f"Directory not found: {directory}")
            return ProjectInfo()

        info = ProjectInfo()

        # Detect project types from marker files
        detected_types = self._detect_types(path)

        if detected_types:
            # Primary type is the first one detected (by priority)
            info.project_type = detected_types[0]
            info.secondary_types = detected_types[1:]

        # Extract metadata from package files
        self._extract_metadata(path, info)

        # Detect frameworks
        self._detect_frameworks(path, info)

        # Detect package manager
        self._detect_package_manager(path, info)

        # Detect test framework
        self._detect_test_framework(path, info)

        # Detect build tool
        self._detect_build_tool(path, info)

        logger.info(
            f"Detected project: {info.project_type.value}, "
            f"frameworks: {info.frameworks}"
        )

        return info

    def _detect_types(self, path: Path) -> list[ProjectType]:
        """Detect project types from marker files.

        Args:
            path: Project directory path.

        Returns:
            List of detected project types, ordered by priority.
        """
        detected: list[tuple[ProjectType, int]] = []

        # Priority order for types (higher = more specific)
        priority = {
            ProjectType.TYPESCRIPT: 10,  # TypeScript over JavaScript
            ProjectType.KOTLIN: 9,  # Kotlin over Java
            ProjectType.PYTHON: 8,
            ProjectType.RUST: 8,
            ProjectType.GO: 8,
            ProjectType.JAVASCRIPT: 7,
            ProjectType.JAVA: 7,
            ProjectType.CSHARP: 7,
            ProjectType.CPP: 6,
            ProjectType.C: 5,
            ProjectType.RUBY: 7,
            ProjectType.PHP: 7,
            ProjectType.SWIFT: 7,
            ProjectType.SCALA: 7,
            ProjectType.ELIXIR: 7,
            ProjectType.HASKELL: 7,
            ProjectType.SHELL: 3,
            ProjectType.DOCKER: 4,
            ProjectType.TERRAFORM: 5,
        }

        for project_type, markers in PROJECT_MARKERS.items():
            for marker in markers:
                if self._marker_exists(path, marker):
                    detected.append((project_type, priority.get(project_type, 0)))
                    break

        # Sort by priority (descending) and return unique types
        detected.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        result = []
        for ptype, _ in detected:
            if ptype not in seen:
                seen.add(ptype)
                result.append(ptype)

        return result

    def _marker_exists(self, path: Path, marker: str) -> bool:
        """Check if a marker file exists.

        Args:
            path: Directory to search.
            marker: File pattern to look for.

        Returns:
            True if marker exists.
        """
        # Direct file check
        if (path / marker).exists():
            return True

        # Glob pattern check (for *.ext patterns)
        if "*" in marker:
            matches = list(path.glob(marker))
            return len(matches) > 0

        # Check subdirectories up to max_depth
        for depth in range(1, self.max_depth + 1):
            pattern = "/".join(["*"] * depth) + "/" + marker
            matches = list(path.glob(pattern))
            if matches:
                return True

        return False

    def _extract_metadata(self, path: Path, info: ProjectInfo) -> None:
        """Extract project metadata from package files.

        Args:
            path: Project directory.
            info: ProjectInfo to update.
        """
        # Python: pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            self._parse_pyproject(pyproject, info)

        # JavaScript/TypeScript: package.json
        package_json = path / "package.json"
        if package_json.exists():
            self._parse_package_json(package_json, info)

        # Rust: Cargo.toml
        cargo_toml = path / "Cargo.toml"
        if cargo_toml.exists():
            self._parse_cargo_toml(cargo_toml, info)

        # Go: go.mod
        go_mod = path / "go.mod"
        if go_mod.exists():
            self._parse_go_mod(go_mod, info)

    def _parse_pyproject(self, file_path: Path, info: ProjectInfo) -> None:
        """Parse pyproject.toml for metadata."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                return

        try:
            with open(file_path, "rb") as f:
                data = tomllib.load(f)

            # Get project info
            project = data.get("project", {})
            info.name = project.get("name")
            info.version = project.get("version")
            info.markers.append("pyproject.toml")

            # Store dependencies for framework detection
            deps = project.get("dependencies", [])
            info.metadata["python_deps"] = deps

            # Check tool sections for test frameworks
            tools = data.get("tool", {})
            if "pytest" in tools:
                info.metadata["has_pytest"] = True

        except Exception as e:
            logger.debug(f"Error parsing pyproject.toml: {e}")

    def _parse_package_json(self, file_path: Path, info: ProjectInfo) -> None:
        """Parse package.json for metadata."""
        try:
            with open(file_path) as f:
                data = json.load(f)

            info.name = data.get("name")
            info.version = data.get("version")
            info.markers.append("package.json")

            # Collect all dependencies
            deps = set()
            deps.update(data.get("dependencies", {}).keys())
            deps.update(data.get("devDependencies", {}).keys())
            deps.update(data.get("peerDependencies", {}).keys())
            info.metadata["npm_deps"] = list(deps)

            # Check for TypeScript
            if "typescript" in deps:
                if ProjectType.TYPESCRIPT not in info.secondary_types:
                    if info.project_type != ProjectType.TYPESCRIPT:
                        info.secondary_types.insert(0, ProjectType.TYPESCRIPT)

        except Exception as e:
            logger.debug(f"Error parsing package.json: {e}")

    def _parse_cargo_toml(self, file_path: Path, info: ProjectInfo) -> None:
        """Parse Cargo.toml for metadata."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                return

        try:
            with open(file_path, "rb") as f:
                data = tomllib.load(f)

            package = data.get("package", {})
            info.name = package.get("name")
            info.version = package.get("version")
            info.markers.append("Cargo.toml")

            # Collect dependencies
            deps = set()
            deps.update(data.get("dependencies", {}).keys())
            deps.update(data.get("dev-dependencies", {}).keys())
            info.metadata["cargo_deps"] = list(deps)

        except Exception as e:
            logger.debug(f"Error parsing Cargo.toml: {e}")

    def _parse_go_mod(self, file_path: Path, info: ProjectInfo) -> None:
        """Parse go.mod for metadata."""
        try:
            content = file_path.read_text()
            lines = content.splitlines()

            for line in lines:
                if line.startswith("module "):
                    info.name = line.split()[1]
                    break

            info.markers.append("go.mod")

            # Extract require statements for deps
            deps = []
            in_require = False
            for line in lines:
                if line.startswith("require ("):
                    in_require = True
                elif in_require and line.strip() == ")":
                    in_require = False
                elif in_require:
                    parts = line.strip().split()
                    if parts:
                        deps.append(parts[0])
                elif line.startswith("require "):
                    parts = line.split()
                    if len(parts) >= 2:
                        deps.append(parts[1])

            info.metadata["go_deps"] = deps

        except Exception as e:
            logger.debug(f"Error parsing go.mod: {e}")

    def _detect_frameworks(self, path: Path, info: ProjectInfo) -> None:
        """Detect frameworks used in the project.

        Args:
            path: Project directory.
            info: ProjectInfo to update.
        """
        # Get all dependencies
        all_deps: set[str] = set()
        for key in ["python_deps", "npm_deps", "cargo_deps", "go_deps"]:
            deps = info.metadata.get(key, [])
            # Handle both list and dict formats
            if isinstance(deps, list):
                for dep in deps:
                    if isinstance(dep, str):
                        # Extract package name from version specifier
                        name = dep.split("[")[0].split(">=")[0].split("==")[0]
                        all_deps.add(name.lower().strip())
            elif isinstance(deps, dict):
                all_deps.update(k.lower() for k in deps.keys())

        for framework, patterns in FRAMEWORK_PATTERNS.items():
            detected = False

            # Check file patterns
            if "files" in patterns:
                for file_pattern in patterns["files"]:
                    if self._marker_exists(path, file_pattern):
                        detected = True
                        break

            # Check dependency patterns
            if not detected and "deps" in patterns:
                for dep in patterns["deps"]:
                    if dep.lower() in all_deps:
                        detected = True
                        break

            if detected:
                info.frameworks.append(framework)

    def _detect_package_manager(self, path: Path, info: ProjectInfo) -> None:
        """Detect package manager.

        Args:
            path: Project directory.
            info: ProjectInfo to update.
        """
        # Python
        if info.project_type == ProjectType.PYTHON:
            if (path / "poetry.lock").exists():
                info.package_manager = "Poetry"
            elif (path / "Pipfile.lock").exists():
                info.package_manager = "Pipenv"
            elif (path / "uv.lock").exists():
                info.package_manager = "uv"
            elif (path / "requirements.txt").exists():
                info.package_manager = "pip"

        # JavaScript/TypeScript
        elif info.project_type in (ProjectType.JAVASCRIPT, ProjectType.TYPESCRIPT):
            if (path / "pnpm-lock.yaml").exists():
                info.package_manager = "pnpm"
            elif (path / "yarn.lock").exists():
                info.package_manager = "Yarn"
            elif (path / "bun.lockb").exists():
                info.package_manager = "Bun"
            elif (path / "package-lock.json").exists():
                info.package_manager = "npm"

        # Rust
        elif info.project_type == ProjectType.RUST:
            info.package_manager = "Cargo"

        # Go
        elif info.project_type == ProjectType.GO:
            info.package_manager = "Go Modules"

        # Ruby
        elif info.project_type == ProjectType.RUBY:
            info.package_manager = "Bundler"

        # PHP
        elif info.project_type == ProjectType.PHP:
            info.package_manager = "Composer"

    def _detect_test_framework(self, path: Path, info: ProjectInfo) -> None:
        """Detect test framework.

        Args:
            path: Project directory.
            info: ProjectInfo to update.
        """
        # Check frameworks list first
        test_frameworks = ["Pytest", "Jest", "Vitest", "RSpec", "PHPUnit"]
        for fw in test_frameworks:
            if fw in info.frameworks:
                info.test_framework = fw.lower()
                return

        # Python
        if info.project_type == ProjectType.PYTHON:
            if (path / "pytest.ini").exists() or (path / "conftest.py").exists():
                info.test_framework = "pytest"
            elif info.metadata.get("has_pytest"):
                info.test_framework = "pytest"

        # JavaScript/TypeScript
        elif info.project_type in (ProjectType.JAVASCRIPT, ProjectType.TYPESCRIPT):
            if (path / "jest.config.js").exists() or (path / "jest.config.ts").exists():
                info.test_framework = "jest"
            elif (path / "vitest.config.ts").exists():
                info.test_framework = "vitest"

        # Rust
        elif info.project_type == ProjectType.RUST:
            info.test_framework = "cargo test"

        # Go
        elif info.project_type == ProjectType.GO:
            info.test_framework = "go test"

    def _detect_build_tool(self, path: Path, info: ProjectInfo) -> None:
        """Detect build tool.

        Args:
            path: Project directory.
            info: ProjectInfo to update.
        """
        # JavaScript/TypeScript
        if info.project_type in (ProjectType.JAVASCRIPT, ProjectType.TYPESCRIPT):
            if (path / "vite.config.ts").exists() or (path / "vite.config.js").exists():
                info.build_tool = "Vite"
            elif (path / "webpack.config.js").exists():
                info.build_tool = "Webpack"
            elif (path / "rollup.config.js").exists():
                info.build_tool = "Rollup"
            elif (path / "esbuild.config.js").exists():
                info.build_tool = "esbuild"

        # Java
        elif info.project_type == ProjectType.JAVA:
            if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
                info.build_tool = "Gradle"
            elif (path / "pom.xml").exists():
                info.build_tool = "Maven"

        # C/C++
        elif info.project_type in (ProjectType.C, ProjectType.CPP):
            if (path / "CMakeLists.txt").exists():
                info.build_tool = "CMake"
            elif (path / "meson.build").exists():
                info.build_tool = "Meson"
            elif (path / "Makefile").exists():
                info.build_tool = "Make"

        # Rust
        elif info.project_type == ProjectType.RUST:
            info.build_tool = "Cargo"


# Singleton instance for convenience
_detector: ProjectTypeDetector | None = None


def get_detector() -> ProjectTypeDetector:
    """Get the singleton ProjectTypeDetector instance.

    Returns:
        ProjectTypeDetector instance.
    """
    global _detector
    if _detector is None:
        _detector = ProjectTypeDetector()
    return _detector


def detect_project(directory: str | Path | None = None) -> ProjectInfo:
    """Convenience function to detect project type.

    Args:
        directory: Project directory. Defaults to current directory.

    Returns:
        ProjectInfo with detected information.
    """
    if directory is None:
        directory = Path.cwd()
    return get_detector().detect(directory)
