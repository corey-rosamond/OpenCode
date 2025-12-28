"""
Skill registry for managing available skills.

Provides discovery, activation, and lifecycle management.
"""

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .base import Skill
from .loader import SkillLoader, get_default_search_paths

logger = logging.getLogger(__name__)


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected between skills."""

    def __init__(self, cycle: list[str]) -> None:
        """Initialize with the dependency cycle.

        Args:
            cycle: List of skill names forming the cycle
        """
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class SkillRegistry:
    """Registry of available skills.

    Singleton that manages skill registration, discovery,
    and activation.
    """

    _instance: "SkillRegistry | None" = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize registry."""
        self._skills: dict[str, Skill] = {}
        self._aliases: dict[str, str] = {}
        self._active_skill: Skill | None = None
        self._loader: SkillLoader | None = None
        self._on_activate: list[Callable[[Skill], None]] = []
        self._on_deactivate: list[Callable[[Skill], None]] = []

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._lock:
            cls._instance = None

    def set_loader(self, loader: SkillLoader) -> None:
        """Set the skill loader."""
        self._loader = loader

    def register(self, skill: Skill, check_dependencies: bool = True) -> None:
        """Register a skill.

        Args:
            skill: Skill to register
            check_dependencies: Whether to validate dependencies exist and
                check for circular dependencies. Set to False during bulk
                loading when dependencies will be validated after all
                skills are loaded.

        Raises:
            ValueError: If skill name already registered or dependency not found
            CircularDependencyError: If circular dependency detected
        """
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")

        # Temporarily add skill to check dependencies
        self._skills[skill.name] = skill

        if check_dependencies:
            # Validate that all dependencies exist
            for dep_name in skill.dependencies:
                if dep_name not in self._skills:
                    # Remove skill since registration failed
                    del self._skills[skill.name]
                    raise ValueError(
                        f"Skill '{skill.name}' depends on unknown skill: {dep_name}"
                    )

            # Check for circular dependencies
            cycle = self._detect_circular_dependency(skill.name)
            if cycle:
                # Remove skill since registration failed
                del self._skills[skill.name]
                raise CircularDependencyError(cycle)

        # Register aliases
        for alias in skill.definition.metadata.aliases:
            if alias not in self._aliases and alias not in self._skills:
                self._aliases[alias] = skill.name

        logger.debug("Registered skill: %s", skill.name)

    def _detect_circular_dependency(self, start_name: str) -> list[str] | None:
        """Detect circular dependencies starting from a skill.

        Uses depth-first search to find cycles in the dependency graph.

        Args:
            start_name: Name of the skill to start from

        Returns:
            List of skill names forming the cycle, or None if no cycle
        """
        visited: set[str] = set()
        path: list[str] = []

        def dfs(name: str) -> list[str] | None:
            if name in path:
                # Found a cycle - return the cycle portion
                cycle_start = path.index(name)
                return path[cycle_start:] + [name]

            if name in visited:
                return None

            skill = self._skills.get(name)
            if skill is None:
                return None

            visited.add(name)
            path.append(name)

            for dep_name in skill.dependencies:
                cycle = dfs(dep_name)
                if cycle:
                    return cycle

            path.pop()
            return None

        return dfs(start_name)

    def validate_all_dependencies(self) -> list[str]:
        """Validate dependencies for all registered skills.

        Call this after bulk loading skills with check_dependencies=False.

        Returns:
            List of error messages for missing or circular dependencies
        """
        errors: list[str] = []

        # Check for missing dependencies
        for skill_name, skill in self._skills.items():
            for dep_name in skill.dependencies:
                if dep_name not in self._skills:
                    errors.append(
                        f"Skill '{skill_name}' depends on unknown skill: {dep_name}"
                    )

        # Check for circular dependencies in each skill
        for skill_name in self._skills:
            cycle = self._detect_circular_dependency(skill_name)
            if cycle:
                cycle_str = " -> ".join(cycle)
                error = f"Circular dependency detected: {cycle_str}"
                if error not in errors:  # Avoid duplicates
                    errors.append(error)

        return errors

    def unregister(self, name: str) -> bool:
        """Unregister a skill.

        Args:
            name: Skill name

        Returns:
            True if unregistered, False if not found
        """
        skill = self._skills.get(name)
        if skill is None:
            return False

        # Deactivate if active
        if self._active_skill and self._active_skill.name == name:
            self.deactivate()

        # Remove aliases
        aliases_to_remove = [
            alias for alias, target in self._aliases.items() if target == name
        ]
        for alias in aliases_to_remove:
            del self._aliases[alias]

        del self._skills[name]
        logger.debug("Unregistered skill: %s", name)
        return True

    def get(self, name: str) -> Skill | None:
        """Get skill by name or alias.

        Args:
            name: Skill name or alias

        Returns:
            Skill or None if not found
        """
        # Direct lookup
        if name in self._skills:
            return self._skills[name]

        # Alias lookup
        if name in self._aliases:
            return self._skills.get(self._aliases[name])

        return None

    def exists(self, name: str) -> bool:
        """Check if skill exists.

        Args:
            name: Skill name or alias

        Returns:
            True if skill exists
        """
        return self.get(name) is not None

    def list_skills(self, tag: str | None = None) -> list[Skill]:
        """List skills, optionally filtered by tag.

        Args:
            tag: Filter by tag (None = all)

        Returns:
            List of matching skills
        """
        skills = list(self._skills.values())

        if tag:
            skills = [s for s in skills if tag in s.tags]

        return sorted(skills, key=lambda s: s.name)

    def list_builtin(self) -> list[Skill]:
        """List built-in skills."""
        return [s for s in self._skills.values() if s.is_builtin]

    def list_custom(self) -> list[Skill]:
        """List custom (non-builtin) skills."""
        return [s for s in self._skills.values() if not s.is_builtin]

    def search(self, query: str) -> list[Skill]:
        """Search skills by name or description.

        Args:
            query: Search query

        Returns:
            List of matching skills
        """
        matches: list[Skill] = []
        for skill in self._skills.values():
            if skill.definition.metadata.matches_query(query):
                matches.append(skill)
        return sorted(matches, key=lambda s: s.name)

    def get_tags(self) -> list[str]:
        """Get all unique tags across skills."""
        tags: set[str] = set()
        for skill in self._skills.values():
            tags.update(skill.tags)
        return sorted(tags)

    def activate(
        self, name: str, config: dict[str, Any] | None = None
    ) -> tuple[Skill | None, list[str]]:
        """Activate a skill.

        Args:
            name: Skill name or alias
            config: Configuration values

        Returns:
            (Skill, errors) - Skill is None if errors
        """
        skill = self.get(name)
        if skill is None:
            return None, [f"Skill not found: {name}"]

        # Deactivate current skill
        if self._active_skill:
            self.deactivate()

        # Activate new skill
        errors = skill.activate(config)
        if errors:
            return None, errors

        self._active_skill = skill

        # Notify listeners
        for callback in self._on_activate:
            try:
                callback(skill)
            except Exception as e:
                logger.error("Activate callback error: %s", e)

        logger.info("Activated skill: %s", skill.name)
        return skill, []

    def deactivate(self) -> Skill | None:
        """Deactivate current skill.

        Returns:
            Previously active skill, or None
        """
        if self._active_skill is None:
            return None

        skill = self._active_skill
        skill.deactivate()
        self._active_skill = None

        # Notify listeners
        for callback in self._on_deactivate:
            try:
                callback(skill)
            except Exception as e:
                logger.error("Deactivate callback error: %s", e)

        logger.info("Deactivated skill: %s", skill.name)
        return skill

    @property
    def active_skill(self) -> Skill | None:
        """Get currently active skill."""
        return self._active_skill

    def on_activate(self, callback: Callable[[Skill], None]) -> None:
        """Register activation callback."""
        self._on_activate.append(callback)

    def on_deactivate(self, callback: Callable[[Skill], None]) -> None:
        """Register deactivation callback."""
        self._on_deactivate.append(callback)

    def load_skills(self, search_paths: list[Path] | None = None) -> int:
        """Load skills from search paths.

        Args:
            search_paths: Paths to search (uses defaults if None)

        Returns:
            Number of skills loaded
        """
        if self._loader is None:
            paths = search_paths or get_default_search_paths()
            self._loader = SkillLoader(paths)

        skills = self._loader.discover_skills()

        count = 0
        for skill in skills:
            try:
                self.register(skill)
                count += 1
            except ValueError as e:
                logger.warning("Could not register skill: %s", e)

        return count

    def reload_skill(self, name: str) -> Skill | None:
        """Reload a skill from disk.

        Args:
            name: Skill name

        Returns:
            Reloaded skill or None
        """
        if self._loader is None:
            return None

        skill = self._loader.reload_skill(name)
        if skill is None:
            return None

        # Replace in registry
        if name in self._skills:
            was_active = self._active_skill and self._active_skill.name == name
            self.unregister(name)
            self.register(skill)

            if was_active:
                self.activate(name)

        return skill

    def reload_all(self) -> int:
        """Reload all skills from disk.

        Returns:
            Number of skills reloaded
        """
        if self._loader is None:
            return 0

        # Remember active skill
        active_name = self._active_skill.name if self._active_skill else None

        # Clear registry
        self._skills.clear()
        self._aliases.clear()
        self._active_skill = None

        # Reload
        count = self.load_skills()

        # Restore active skill if still exists
        if active_name and active_name in self._skills:
            self.activate(active_name)

        return count

    def get_stats(self) -> dict[str, Any]:
        """Get skill statistics."""
        return {
            "total": len(self._skills),
            "builtin": len(self.list_builtin()),
            "custom": len(self.list_custom()),
            "active": self._active_skill.name if self._active_skill else None,
            "tags": self.get_tags(),
        }


__all__ = [
    "CircularDependencyError",
    "SkillRegistry",
]
