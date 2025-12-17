"""Tests for built-in skills."""

import pytest

from code_forge.skills.base import Skill
from code_forge.skills.builtin import (
    API_SKILL,
    BUILTIN_SKILLS,
    DATABASE_SKILL,
    EXCEL_SKILL,
    PDF_SKILL,
    TESTING_SKILL,
    create_builtin_skill,
    get_builtin_skills,
    register_builtin_skills,
)
from code_forge.skills.registry import SkillRegistry


class TestBuiltinSkills:
    """Tests for built-in skills."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    def test_pdf_skill(self) -> None:
        """Test PDF skill definition."""
        assert PDF_SKILL.name == "pdf"
        assert "PDF" in PDF_SKILL.description
        assert PDF_SKILL.is_builtin is True
        assert "read" in PDF_SKILL.get_tools()
        assert "documents" in PDF_SKILL.tags

    def test_excel_skill(self) -> None:
        """Test Excel skill definition."""
        assert EXCEL_SKILL.name == "excel"
        assert "Excel" in EXCEL_SKILL.description or "spreadsheet" in EXCEL_SKILL.description.lower()
        assert EXCEL_SKILL.is_builtin is True
        assert "xlsx" in EXCEL_SKILL.definition.metadata.aliases
        assert "csv" in EXCEL_SKILL.definition.metadata.aliases
        assert "data" in EXCEL_SKILL.tags

    def test_database_skill(self) -> None:
        """Test Database skill definition."""
        assert DATABASE_SKILL.name == "database"
        assert "database" in DATABASE_SKILL.description.lower()
        assert DATABASE_SKILL.is_builtin is True
        assert "db" in DATABASE_SKILL.definition.metadata.aliases
        assert "sql" in DATABASE_SKILL.tags

    def test_api_skill(self) -> None:
        """Test API skill definition."""
        assert API_SKILL.name == "api"
        assert "API" in API_SKILL.description
        assert API_SKILL.is_builtin is True
        assert "api" in API_SKILL.tags

    def test_testing_skill(self) -> None:
        """Test Testing skill definition."""
        assert TESTING_SKILL.name == "testing"
        assert "test" in TESTING_SKILL.description.lower()
        assert TESTING_SKILL.is_builtin is True
        assert "test" in TESTING_SKILL.definition.metadata.aliases
        assert "testing" in TESTING_SKILL.tags

    def test_all_builtin_skills_list(self) -> None:
        """Test BUILTIN_SKILLS list."""
        assert len(BUILTIN_SKILLS) == 5
        names = {s.name for s in BUILTIN_SKILLS}
        assert names == {"pdf", "excel", "database", "api", "testing"}

    def test_all_skills_are_builtin(self) -> None:
        """Test that all built-in skills have is_builtin=True."""
        for skill in BUILTIN_SKILLS:
            assert skill.is_builtin is True

    def test_all_skills_have_prompts(self) -> None:
        """Test that all built-in skills have prompts."""
        for skill in BUILTIN_SKILLS:
            assert skill.definition.prompt != ""
            assert len(skill.definition.prompt) > 50  # Should have meaningful content

    def test_all_skills_have_tools(self) -> None:
        """Test that all built-in skills have tools."""
        for skill in BUILTIN_SKILLS:
            assert len(skill.get_tools()) > 0

    def test_all_skills_have_tags(self) -> None:
        """Test that all built-in skills have tags."""
        for skill in BUILTIN_SKILLS:
            assert len(skill.tags) > 0

    def test_all_skills_can_activate(self) -> None:
        """Test that all built-in skills can be activated."""
        for skill in BUILTIN_SKILLS:
            errors = skill.activate()
            assert errors == []
            assert skill.is_active
            skill.deactivate()


class TestCreateBuiltinSkill:
    """Tests for create_builtin_skill function."""

    def test_create_minimal(self) -> None:
        """Test creating skill with minimal args."""
        skill = create_builtin_skill(
            name="test",
            description="Test skill",
            prompt="Test prompt",
        )
        assert skill.name == "test"
        assert skill.description == "Test skill"
        assert skill.definition.prompt == "Test prompt"
        assert skill.is_builtin is True
        assert skill.definition.metadata.author == "Code-Forge"

    def test_create_with_tools(self) -> None:
        """Test creating skill with tools."""
        skill = create_builtin_skill(
            name="test",
            description="Test",
            prompt="Test",
            tools=["read", "write"],
        )
        assert skill.get_tools() == ["read", "write"]

    def test_create_with_tags(self) -> None:
        """Test creating skill with tags."""
        skill = create_builtin_skill(
            name="test",
            description="Test",
            prompt="Test",
            tags=["tag1", "tag2"],
        )
        assert skill.tags == ["tag1", "tag2"]

    def test_create_with_aliases(self) -> None:
        """Test creating skill with aliases."""
        skill = create_builtin_skill(
            name="test",
            description="Test",
            prompt="Test",
            aliases=["t", "tst"],
        )
        assert skill.definition.metadata.aliases == ["t", "tst"]

    def test_create_with_examples(self) -> None:
        """Test creating skill with examples."""
        skill = create_builtin_skill(
            name="test",
            description="Test",
            prompt="Test",
            examples=["Example 1", "Example 2"],
        )
        assert skill.definition.metadata.examples == ["Example 1", "Example 2"]


class TestGetBuiltinSkills:
    """Tests for get_builtin_skills function."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        skills = get_builtin_skills()
        assert isinstance(skills, list)

    def test_returns_all_skills(self) -> None:
        """Test that function returns all built-in skills."""
        skills = get_builtin_skills()
        assert len(skills) == 5

    def test_returns_copies(self) -> None:
        """Test that modifications don't affect original."""
        skills = get_builtin_skills()
        original_len = len(BUILTIN_SKILLS)
        skills.append(create_builtin_skill("new", "New", "New"))
        assert len(BUILTIN_SKILLS) == original_len


class TestRegisterBuiltinSkills:
    """Tests for register_builtin_skills function."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    def test_registers_all_skills(self) -> None:
        """Test that all built-in skills are registered."""
        registry = SkillRegistry()
        count = register_builtin_skills(registry)
        assert count == 5

        assert isinstance(registry.get("pdf"), Skill)
        assert isinstance(registry.get("excel"), Skill)
        assert isinstance(registry.get("database"), Skill)
        assert isinstance(registry.get("api"), Skill)
        assert isinstance(registry.get("testing"), Skill)

    def test_uses_singleton_if_none(self) -> None:
        """Test that singleton is used if no registry provided."""
        count = register_builtin_skills()
        assert count == 5

        registry = SkillRegistry.get_instance()
        assert isinstance(registry.get("pdf"), Skill)

    def test_skips_already_registered(self) -> None:
        """Test that already registered skills are skipped."""
        registry = SkillRegistry()

        # Register first time
        count1 = register_builtin_skills(registry)
        assert count1 == 5

        # Register again
        count2 = register_builtin_skills(registry)
        assert count2 == 0

    def test_registers_aliases(self) -> None:
        """Test that aliases are registered."""
        registry = SkillRegistry()
        register_builtin_skills(registry)

        # Excel aliases
        assert isinstance(registry.get("xlsx"), Skill)
        assert isinstance(registry.get("csv"), Skill)

        # Database alias
        assert isinstance(registry.get("db"), Skill)

        # Testing alias
        assert isinstance(registry.get("test"), Skill)
