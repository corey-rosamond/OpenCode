"""
Skills system package.

Provides domain-specific capabilities through reusable skills.
"""

from .base import (
    Skill,
    SkillConfig,
    SkillDefinition,
    SkillMetadata,
)
from .builtin import (
    API_SKILL,
    BUILTIN_SKILLS,
    DATABASE_SKILL,
    EXCEL_SKILL,
    PDF_SKILL,
    TESTING_SKILL,
    get_builtin_skills,
    register_builtin_skills,
)
from .commands import (
    SkillCommand,
    get_skill_command,
)
from .loader import (
    SkillLoader,
    SkillLoadError,
    get_default_search_paths,
)
from .parser import (
    ParseResult,
    SkillParseError,
    SkillParser,
)
from .registry import (
    CircularDependencyError,
    SkillRegistry,
)


def setup_skills() -> SkillRegistry:
    """Set up the skills system.

    Returns:
        Configured skill registry
    """
    registry = SkillRegistry.get_instance()

    # Register built-in skills
    register_builtin_skills(registry)

    # Load user/project skills
    registry.load_skills()

    return registry


__all__ = [
    "API_SKILL",
    "BUILTIN_SKILLS",
    "CircularDependencyError",
    "DATABASE_SKILL",
    "EXCEL_SKILL",
    "PDF_SKILL",
    "TESTING_SKILL",
    "ParseResult",
    "Skill",
    "SkillCommand",
    "SkillConfig",
    "SkillDefinition",
    "SkillLoadError",
    "SkillLoader",
    "SkillMetadata",
    "SkillParseError",
    "SkillParser",
    "SkillRegistry",
    "get_builtin_skills",
    "get_default_search_paths",
    "get_skill_command",
    "register_builtin_skills",
    "setup_skills",
]
