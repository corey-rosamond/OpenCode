"""Language profiles for context-aware assistance.

This module provides language-specific hints, tool preferences, and
best practices for each supported project type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .project_detector import ProjectInfo, ProjectType


@dataclass
class LanguageProfile:
    """Language-specific context and hints.

    Attributes:
        project_type: The project type this profile is for.
        display_name: Human-readable language name.
        file_extensions: Common file extensions for this language.
        preferred_tools: Tools to prefer for this language.
        run_command: Command to run the main file/program.
        test_command: Command to run tests.
        lint_command: Command to run linter.
        format_command: Command to run formatter.
        build_command: Command to build the project.
        package_install: Command to install dependencies.
        best_practices: Language-specific best practices.
        common_patterns: Common code patterns and idioms.
        avoid_patterns: Anti-patterns to avoid.
    """

    project_type: ProjectType
    display_name: str
    file_extensions: list[str] = field(default_factory=list)
    preferred_tools: list[str] = field(default_factory=list)
    run_command: str | None = None
    test_command: str | None = None
    lint_command: str | None = None
    format_command: str | None = None
    build_command: str | None = None
    package_install: str | None = None
    best_practices: list[str] = field(default_factory=list)
    common_patterns: list[str] = field(default_factory=list)
    avoid_patterns: list[str] = field(default_factory=list)

    def to_context_hints(self) -> str:
        """Generate context hints for the system prompt.

        Returns:
            Formatted hints string.
        """
        hints = []

        if self.test_command:
            hints.append(f"Run tests: {self.test_command}")

        if self.lint_command:
            hints.append(f"Lint code: {self.lint_command}")

        if self.format_command:
            hints.append(f"Format code: {self.format_command}")

        if self.package_install:
            hints.append(f"Install dependencies: {self.package_install}")

        if self.best_practices:
            hints.append("Best practices:")
            for practice in self.best_practices[:3]:  # Limit to 3
                hints.append(f"  - {practice}")

        return "\n".join(hints)


# Pre-defined language profiles
PROFILES: dict[ProjectType, LanguageProfile] = {
    ProjectType.PYTHON: LanguageProfile(
        project_type=ProjectType.PYTHON,
        display_name="Python",
        file_extensions=[".py", ".pyi", ".pyx"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="python {file}",
        test_command="pytest",
        lint_command="ruff check .",
        format_command="ruff format .",
        package_install="pip install -r requirements.txt",
        best_practices=[
            "Use type hints for function signatures",
            "Follow PEP 8 style guidelines",
            "Write docstrings for public functions",
            "Use pathlib.Path instead of os.path",
            "Prefer f-strings over .format() or %",
        ],
        common_patterns=[
            "Context managers (with statement)",
            "List/dict/set comprehensions",
            "Dataclasses or Pydantic models",
            "async/await for I/O operations",
        ],
        avoid_patterns=[
            "Bare except clauses",
            "Mutable default arguments",
            "Global variables",
            "Deep inheritance hierarchies",
        ],
    ),
    ProjectType.JAVASCRIPT: LanguageProfile(
        project_type=ProjectType.JAVASCRIPT,
        display_name="JavaScript",
        file_extensions=[".js", ".mjs", ".cjs", ".jsx"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="node {file}",
        test_command="npm test",
        lint_command="npm run lint",
        format_command="npm run format",
        package_install="npm install",
        best_practices=[
            "Use const/let instead of var",
            "Use arrow functions for callbacks",
            "Handle promises with async/await",
            "Use destructuring for cleaner code",
        ],
        common_patterns=[
            "ES6+ modules (import/export)",
            "Spread operator for objects/arrays",
            "Optional chaining (?.) and nullish coalescing (??)",
            "Array methods (map, filter, reduce)",
        ],
        avoid_patterns=[
            "Using == instead of ===",
            "Callback hell (use async/await)",
            "Modifying prototypes",
            "Using eval()",
        ],
    ),
    ProjectType.TYPESCRIPT: LanguageProfile(
        project_type=ProjectType.TYPESCRIPT,
        display_name="TypeScript",
        file_extensions=[".ts", ".tsx", ".mts", ".cts"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="npx ts-node {file}",
        test_command="npm test",
        lint_command="npm run lint",
        format_command="npm run format",
        package_install="npm install",
        best_practices=[
            "Define explicit types for function parameters and returns",
            "Use interfaces for object shapes",
            "Leverage union types and type guards",
            "Use strict mode in tsconfig.json",
        ],
        common_patterns=[
            "Generic types for reusable code",
            "Type inference where obvious",
            "Discriminated unions for state",
            "Utility types (Partial, Pick, Omit)",
        ],
        avoid_patterns=[
            "Using 'any' type",
            "Type assertions without validation",
            "Ignoring null/undefined",
            "Over-complicated generics",
        ],
    ),
    ProjectType.RUST: LanguageProfile(
        project_type=ProjectType.RUST,
        display_name="Rust",
        file_extensions=[".rs"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="cargo run",
        test_command="cargo test",
        lint_command="cargo clippy",
        format_command="cargo fmt",
        build_command="cargo build",
        package_install="cargo build",
        best_practices=[
            "Use Result and Option instead of panicking",
            "Leverage the borrow checker, don't fight it",
            "Use iterators over manual loops",
            "Derive common traits (Debug, Clone, etc.)",
        ],
        common_patterns=[
            "Pattern matching with match",
            "Error propagation with ?",
            "Builder pattern for complex objects",
            "Trait objects for polymorphism",
        ],
        avoid_patterns=[
            "Unnecessary use of unsafe",
            "Excessive cloning",
            "Ignoring clippy warnings",
            "String instead of &str when borrowing",
        ],
    ),
    ProjectType.GO: LanguageProfile(
        project_type=ProjectType.GO,
        display_name="Go",
        file_extensions=[".go"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="go run {file}",
        test_command="go test ./...",
        lint_command="golangci-lint run",
        format_command="go fmt ./...",
        build_command="go build",
        package_install="go mod download",
        best_practices=[
            "Handle errors explicitly, don't ignore them",
            "Use short variable names in small scopes",
            "Accept interfaces, return structs",
            "Use goroutines with proper synchronization",
        ],
        common_patterns=[
            "Error handling with if err != nil",
            "Defer for cleanup",
            "Channels for concurrency",
            "Table-driven tests",
        ],
        avoid_patterns=[
            "Ignoring errors with _",
            "Naked returns in complex functions",
            "Goroutine leaks",
            "Package-level variables",
        ],
    ),
    ProjectType.JAVA: LanguageProfile(
        project_type=ProjectType.JAVA,
        display_name="Java",
        file_extensions=[".java"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="java {file}",
        test_command="./gradlew test",
        lint_command="./gradlew spotlessCheck",
        format_command="./gradlew spotlessApply",
        build_command="./gradlew build",
        package_install="./gradlew dependencies",
        best_practices=[
            "Use records for data classes (Java 16+)",
            "Prefer composition over inheritance",
            "Use Optional for nullable returns",
            "Write unit tests with JUnit",
        ],
        common_patterns=[
            "Stream API for collections",
            "Lambda expressions",
            "Try-with-resources",
            "Builder pattern",
        ],
        avoid_patterns=[
            "Null returns without documentation",
            "Catching generic Exception",
            "Mutable public fields",
            "God classes",
        ],
    ),
    ProjectType.RUBY: LanguageProfile(
        project_type=ProjectType.RUBY,
        display_name="Ruby",
        file_extensions=[".rb", ".rake"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="ruby {file}",
        test_command="bundle exec rspec",
        lint_command="bundle exec rubocop",
        format_command="bundle exec rubocop -a",
        package_install="bundle install",
        best_practices=[
            "Follow the Ruby Style Guide",
            "Use blocks and iterators",
            "Write expressive method names",
            "Use symbols for identifiers",
        ],
        common_patterns=[
            "Blocks and procs",
            "Method chaining",
            "Duck typing",
            "Convention over configuration",
        ],
        avoid_patterns=[
            "Monkey patching core classes",
            "Global variables",
            "Long methods",
            "Ignoring nil",
        ],
    ),
    ProjectType.PHP: LanguageProfile(
        project_type=ProjectType.PHP,
        display_name="PHP",
        file_extensions=[".php"],
        preferred_tools=["Read", "Edit", "Write", "Bash", "Grep"],
        run_command="php {file}",
        test_command="./vendor/bin/phpunit",
        lint_command="./vendor/bin/phpstan analyse",
        format_command="./vendor/bin/php-cs-fixer fix",
        package_install="composer install",
        best_practices=[
            "Use strict types (declare(strict_types=1))",
            "Follow PSR standards",
            "Use type declarations",
            "Leverage Composer autoloading",
        ],
        common_patterns=[
            "Dependency injection",
            "Named arguments (PHP 8+)",
            "Attributes for metadata",
            "Match expressions",
        ],
        avoid_patterns=[
            "Mixing HTML and PHP logic",
            "Using mysql_* functions",
            "Suppressing errors with @",
            "Global state",
        ],
    ),
}


def get_profile(project_type: ProjectType) -> LanguageProfile | None:
    """Get the language profile for a project type.

    Args:
        project_type: The project type.

    Returns:
        LanguageProfile if found, None otherwise.
    """
    return PROFILES.get(project_type)


def get_profile_for_project(info: ProjectInfo) -> LanguageProfile | None:
    """Get the language profile for a detected project.

    Args:
        info: Detected project information.

    Returns:
        LanguageProfile if found, None otherwise.
    """
    profile = get_profile(info.project_type)

    if profile is None:
        return None

    # Create a customized profile based on detected info
    customized = LanguageProfile(
        project_type=profile.project_type,
        display_name=profile.display_name,
        file_extensions=profile.file_extensions.copy(),
        preferred_tools=profile.preferred_tools.copy(),
        run_command=profile.run_command,
        test_command=profile.test_command,
        lint_command=profile.lint_command,
        format_command=profile.format_command,
        build_command=profile.build_command,
        package_install=profile.package_install,
        best_practices=profile.best_practices.copy(),
        common_patterns=profile.common_patterns.copy(),
        avoid_patterns=profile.avoid_patterns.copy(),
    )

    # Customize based on detected frameworks/tools
    if info.test_framework:
        if info.test_framework == "pytest":
            customized.test_command = "pytest"
        elif info.test_framework == "jest":
            customized.test_command = "npm test"
        elif info.test_framework == "vitest":
            customized.test_command = "npx vitest"

    # Customize package install based on detected manager
    if info.package_manager:
        if info.package_manager == "Poetry":
            customized.package_install = "poetry install"
        elif info.package_manager == "Pipenv":
            customized.package_install = "pipenv install"
        elif info.package_manager == "uv":
            customized.package_install = "uv pip install -r requirements.txt"
        elif info.package_manager == "pnpm":
            customized.package_install = "pnpm install"
        elif info.package_manager == "Yarn":
            customized.package_install = "yarn install"
        elif info.package_manager == "Bun":
            customized.package_install = "bun install"

    return customized


def generate_project_context(info: ProjectInfo) -> str:
    """Generate comprehensive project context for system prompt.

    Args:
        info: Detected project information.

    Returns:
        Formatted context string.
    """
    lines = []

    # Basic project info
    lines.append("# Project Context")
    lines.append(info.to_context_string())

    # Get language profile
    profile = get_profile_for_project(info)
    if profile:
        lines.append("")
        lines.append("# Language Hints")
        lines.append(profile.to_context_hints())

        # Add framework-specific hints
        if info.frameworks:
            lines.append("")
            lines.append("# Framework Notes")
            for fw in info.frameworks[:5]:  # Limit to 5
                hint = _get_framework_hint(fw)
                if hint:
                    lines.append(f"- {fw}: {hint}")

    return "\n".join(lines)


def _get_framework_hint(framework: str) -> str | None:
    """Get a brief hint for a framework.

    Args:
        framework: Framework name.

    Returns:
        Hint string or None.
    """
    hints: dict[str, str] = {
        # Python
        "Django": "Use Django ORM, prefer class-based views for complex logic",
        "FastAPI": "Use Pydantic models for validation, async endpoints",
        "Flask": "Use blueprints for organization, Flask-SQLAlchemy for DB",
        "Pytest": "Use fixtures, parametrize for test variants",
        "SQLAlchemy": "Use the 2.0 style with select(), session.execute()",
        "Pydantic": "Use Field() for validation, model_validator for complex checks",
        # JavaScript/TypeScript
        "React": "Use functional components with hooks, avoid class components",
        "Vue": "Use Composition API, script setup syntax",
        "Angular": "Use standalone components, signals for reactivity",
        "Next.js": "Use App Router, Server Components by default",
        "Express": "Use middleware for cross-cutting concerns",
        "Nest.js": "Use decorators, dependency injection",
        "Jest": "Use describe/it blocks, mock modules with jest.mock()",
        "Vitest": "Similar to Jest, use vi.mock() for mocking",
        # Rust
        "Tokio": "Use async runtime, prefer spawn for concurrent tasks",
        "Actix": "Use extractors for request data, middleware for auth",
        "Axum": "Use extractors, Router for routing",
        # Ruby
        "Rails": "Follow Rails conventions, use migrations for DB changes",
        "RSpec": "Use describe/context/it, let for lazy evaluation",
        # PHP
        "Laravel": "Use Eloquent ORM, Blade templates, artisan commands",
        "Symfony": "Use Doctrine ORM, Twig templates, services",
    }
    return hints.get(framework)
