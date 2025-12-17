"""Tests for skill registry."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from code_forge.skills.base import Skill, SkillConfig, SkillDefinition, SkillMetadata
from code_forge.skills.loader import SkillLoader
from code_forge.skills.registry import SkillRegistry


def create_test_skill(
    name: str,
    description: str = "Test skill",
    tags: list[str] | None = None,
    aliases: list[str] | None = None,
    is_builtin: bool = False,
    tools: list[str] | None = None,
    config: list[SkillConfig] | None = None,
) -> Skill:
    """Create a test skill."""
    metadata = SkillMetadata(
        name=name,
        description=description,
        tags=tags or [],
        aliases=aliases or [],
    )
    definition = SkillDefinition(
        metadata=metadata,
        prompt=f"You are the {name} assistant.",
        tools=tools or [],
        config=config or [],
        is_builtin=is_builtin,
    )
    return Skill(definition)


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        SkillRegistry.reset_instance()

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Create a fresh registry."""
        return SkillRegistry()

    def test_singleton_instance(self) -> None:
        """Test singleton pattern."""
        instance1 = SkillRegistry.get_instance()
        instance2 = SkillRegistry.get_instance()
        assert instance1 is instance2

    def test_reset_instance(self) -> None:
        """Test resetting singleton."""
        instance1 = SkillRegistry.get_instance()
        SkillRegistry.reset_instance()
        instance2 = SkillRegistry.get_instance()
        assert instance1 is not instance2

    def test_register_skill(self, registry: SkillRegistry) -> None:
        """Test registering a skill."""
        skill = create_test_skill("pdf")
        registry.register(skill)
        assert registry.get("pdf") is skill

    def test_register_duplicate_raises(self, registry: SkillRegistry) -> None:
        """Test that registering duplicate raises error."""
        skill1 = create_test_skill("pdf")
        skill2 = create_test_skill("pdf")
        registry.register(skill1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(skill2)

    def test_register_aliases(self, registry: SkillRegistry) -> None:
        """Test that aliases are registered."""
        skill = create_test_skill("excel", aliases=["xlsx", "csv"])
        registry.register(skill)
        assert registry.get("xlsx") is skill
        assert registry.get("csv") is skill

    def test_unregister_skill(self, registry: SkillRegistry) -> None:
        """Test unregistering a skill."""
        skill = create_test_skill("pdf")
        registry.register(skill)
        result = registry.unregister("pdf")
        assert result is True
        assert registry.get("pdf") is None

    def test_unregister_nonexistent(self, registry: SkillRegistry) -> None:
        """Test unregistering nonexistent skill."""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_unregister_removes_aliases(self, registry: SkillRegistry) -> None:
        """Test that unregister removes aliases."""
        skill = create_test_skill("excel", aliases=["xlsx"])
        registry.register(skill)
        registry.unregister("excel")
        assert registry.get("xlsx") is None

    def test_unregister_deactivates_active(self, registry: SkillRegistry) -> None:
        """Test that unregister deactivates if skill is active."""
        skill = create_test_skill("pdf")
        registry.register(skill)
        registry.activate("pdf")
        assert registry.active_skill is skill

        registry.unregister("pdf")
        assert registry.active_skill is None

    def test_get_by_name(self, registry: SkillRegistry) -> None:
        """Test getting skill by name."""
        skill = create_test_skill("pdf")
        registry.register(skill)
        assert registry.get("pdf") is skill

    def test_get_by_alias(self, registry: SkillRegistry) -> None:
        """Test getting skill by alias."""
        skill = create_test_skill("excel", aliases=["xlsx"])
        registry.register(skill)
        assert registry.get("xlsx") is skill

    def test_get_nonexistent(self, registry: SkillRegistry) -> None:
        """Test getting nonexistent skill."""
        assert registry.get("nonexistent") is None

    def test_exists(self, registry: SkillRegistry) -> None:
        """Test checking if skill exists."""
        skill = create_test_skill("pdf")
        registry.register(skill)
        assert registry.exists("pdf") is True
        assert registry.exists("nonexistent") is False

    def test_list_skills(self, registry: SkillRegistry) -> None:
        """Test listing all skills."""
        registry.register(create_test_skill("pdf"))
        registry.register(create_test_skill("excel"))
        registry.register(create_test_skill("api"))

        skills = registry.list_skills()
        assert len(skills) == 3
        # Should be sorted by name
        names = [s.name for s in skills]
        assert names == ["api", "excel", "pdf"]

    def test_list_skills_by_tag(self, registry: SkillRegistry) -> None:
        """Test listing skills by tag."""
        registry.register(create_test_skill("pdf", tags=["documents"]))
        registry.register(create_test_skill("excel", tags=["data"]))
        registry.register(create_test_skill("csv", tags=["data"]))

        data_skills = registry.list_skills(tag="data")
        assert len(data_skills) == 2
        names = {s.name for s in data_skills}
        assert names == {"excel", "csv"}

    def test_list_builtin(self, registry: SkillRegistry) -> None:
        """Test listing builtin skills."""
        registry.register(create_test_skill("builtin1", is_builtin=True))
        registry.register(create_test_skill("builtin2", is_builtin=True))
        registry.register(create_test_skill("custom"))

        builtin = registry.list_builtin()
        assert len(builtin) == 2
        assert all(s.is_builtin for s in builtin)

    def test_list_custom(self, registry: SkillRegistry) -> None:
        """Test listing custom skills."""
        registry.register(create_test_skill("builtin", is_builtin=True))
        registry.register(create_test_skill("custom1"))
        registry.register(create_test_skill("custom2"))

        custom = registry.list_custom()
        assert len(custom) == 2
        assert all(not s.is_builtin for s in custom)

    def test_search_by_name(self, registry: SkillRegistry) -> None:
        """Test searching by name."""
        registry.register(create_test_skill("pdf"))
        registry.register(create_test_skill("excel"))

        results = registry.search("pdf")
        assert len(results) == 1
        assert results[0].name == "pdf"

    def test_search_by_description(self, registry: SkillRegistry) -> None:
        """Test searching by description."""
        registry.register(create_test_skill("pdf", description="Work with PDF documents"))
        registry.register(create_test_skill("excel", description="Work with spreadsheets"))

        results = registry.search("documents")
        assert len(results) == 1
        assert results[0].name == "pdf"

    def test_search_by_tag(self, registry: SkillRegistry) -> None:
        """Test searching by tag."""
        registry.register(create_test_skill("pdf", tags=["documents"]))
        registry.register(create_test_skill("excel", tags=["data"]))

        results = registry.search("data")
        assert len(results) == 1
        assert results[0].name == "excel"

    def test_search_case_insensitive(self, registry: SkillRegistry) -> None:
        """Test case-insensitive search."""
        registry.register(create_test_skill("pdf", description="PDF Documents"))

        results = registry.search("PDF")
        assert len(results) == 1

        results = registry.search("pdf")
        assert len(results) == 1

    def test_get_tags(self, registry: SkillRegistry) -> None:
        """Test getting all tags."""
        registry.register(create_test_skill("pdf", tags=["documents", "analysis"]))
        registry.register(create_test_skill("excel", tags=["data", "analysis"]))

        tags = registry.get_tags()
        assert set(tags) == {"documents", "analysis", "data"}
        # Should be sorted
        assert tags == sorted(tags)

    def test_activate_skill(self, registry: SkillRegistry) -> None:
        """Test activating a skill."""
        skill = create_test_skill("pdf")
        registry.register(skill)

        result_skill, errors = registry.activate("pdf")
        assert errors == []
        assert result_skill is skill
        assert skill.is_active
        assert registry.active_skill is skill

    def test_activate_with_config(self, registry: SkillRegistry) -> None:
        """Test activating with configuration."""
        config = [SkillConfig(name="format", type="string", default="text")]
        skill = create_test_skill("pdf", config=config)
        registry.register(skill)

        registry.activate("pdf", {"format": "json"})
        assert skill.get_context()["format"] == "json"

    def test_activate_nonexistent(self, registry: SkillRegistry) -> None:
        """Test activating nonexistent skill."""
        result_skill, errors = registry.activate("nonexistent")
        assert result_skill is None
        assert len(errors) > 0
        assert "not found" in errors[0].lower()

    def test_activate_deactivates_previous(self, registry: SkillRegistry) -> None:
        """Test that activation deactivates previous skill."""
        pdf = create_test_skill("pdf")
        excel = create_test_skill("excel")
        registry.register(pdf)
        registry.register(excel)

        registry.activate("pdf")
        assert pdf.is_active

        registry.activate("excel")
        assert not pdf.is_active
        assert excel.is_active
        assert registry.active_skill is excel

    def test_activate_with_invalid_config(self, registry: SkillRegistry) -> None:
        """Test activation with invalid config."""
        config = [SkillConfig(name="count", type="int", required=True)]
        skill = create_test_skill("pdf", config=config)
        registry.register(skill)

        result_skill, errors = registry.activate("pdf", {})
        assert result_skill is None
        assert len(errors) > 0

    def test_deactivate(self, registry: SkillRegistry) -> None:
        """Test deactivating skill."""
        skill = create_test_skill("pdf")
        registry.register(skill)
        registry.activate("pdf")

        result = registry.deactivate()
        assert result is skill
        assert not skill.is_active
        assert registry.active_skill is None

    def test_deactivate_when_none_active(self, registry: SkillRegistry) -> None:
        """Test deactivating when no skill is active."""
        result = registry.deactivate()
        assert result is None

    def test_active_skill_property(self, registry: SkillRegistry) -> None:
        """Test active_skill property."""
        assert registry.active_skill is None

        skill = create_test_skill("pdf")
        registry.register(skill)
        registry.activate("pdf")
        assert registry.active_skill is skill

    def test_on_activate_callback(self, registry: SkillRegistry) -> None:
        """Test activation callback."""
        activated: list[Skill] = []

        def callback(skill: Skill) -> None:
            activated.append(skill)

        registry.on_activate(callback)

        skill = create_test_skill("pdf")
        registry.register(skill)
        registry.activate("pdf")

        assert len(activated) == 1
        assert activated[0] is skill

    def test_on_deactivate_callback(self, registry: SkillRegistry) -> None:
        """Test deactivation callback."""
        deactivated: list[Skill] = []

        def callback(skill: Skill) -> None:
            deactivated.append(skill)

        registry.on_deactivate(callback)

        skill = create_test_skill("pdf")
        registry.register(skill)
        registry.activate("pdf")
        registry.deactivate()

        assert len(deactivated) == 1
        assert deactivated[0] is skill

    def test_callback_exception_handled(self, registry: SkillRegistry) -> None:
        """Test that callback exceptions are handled."""
        def bad_callback(skill: Skill) -> None:
            raise RuntimeError("Callback error")

        registry.on_activate(bad_callback)

        skill = create_test_skill("pdf")
        registry.register(skill)

        # Should not raise
        registry.activate("pdf")
        assert registry.active_skill is skill

    def test_set_loader(self, registry: SkillRegistry) -> None:
        """Test setting the loader."""
        loader = SkillLoader()
        registry.set_loader(loader)
        assert registry._loader is loader

    def test_load_skills(
        self, registry: SkillRegistry, tmp_path: Path
    ) -> None:
        """Test loading skills from paths."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "test.yaml").write_text("""
name: test
description: Test skill
prompt: Test
""")

        count = registry.load_skills([skills_dir])
        assert count == 1
        assert isinstance(registry.get("test"), Skill)

    def test_load_skills_uses_defaults(self, registry: SkillRegistry) -> None:
        """Test that load_skills uses default paths if none provided."""
        with patch("code_forge.skills.registry.get_default_search_paths") as mock:
            mock.return_value = []
            registry.load_skills()
            mock.assert_called_once()

    def test_reload_skill(
        self, registry: SkillRegistry, tmp_path: Path
    ) -> None:
        """Test reloading a skill."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "test.yaml"
        skill_file.write_text("""
name: test
description: Original
prompt: Test
""")

        registry.load_skills([skills_dir])
        original = registry.get("test")
        assert isinstance(original, Skill)
        assert original.description == "Original"

        # Modify file
        skill_file.write_text("""
name: test
description: Updated
prompt: Test
""")

        reloaded = registry.reload_skill("test")
        assert isinstance(reloaded, Skill)
        assert reloaded.description == "Updated"
        assert registry.get("test").description == "Updated"

    def test_reload_skill_no_loader(self, registry: SkillRegistry) -> None:
        """Test reloading when no loader is set."""
        result = registry.reload_skill("test")
        assert result is None

    def test_reload_skill_preserves_active(
        self, registry: SkillRegistry, tmp_path: Path
    ) -> None:
        """Test that reload preserves active state."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "test.yaml"
        skill_file.write_text("""
name: test
description: Test
prompt: Test
""")

        registry.load_skills([skills_dir])
        registry.activate("test")
        assert isinstance(registry.active_skill, Skill)

        registry.reload_skill("test")
        assert isinstance(registry.active_skill, Skill)
        assert registry.active_skill.name == "test"

    def test_reload_all(
        self, registry: SkillRegistry, tmp_path: Path
    ) -> None:
        """Test reloading all skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "test.yaml").write_text("""
name: test
description: Test
prompt: Test
""")

        registry.load_skills([skills_dir])
        assert len(registry.list_skills()) == 1

        # Add another skill
        (skills_dir / "test2.yaml").write_text("""
name: test2
description: Test 2
prompt: Test
""")

        count = registry.reload_all()
        assert count == 2
        assert len(registry.list_skills()) == 2

    def test_reload_all_preserves_active(
        self, registry: SkillRegistry, tmp_path: Path
    ) -> None:
        """Test that reload_all preserves active skill."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "test.yaml").write_text("""
name: test
description: Test
prompt: Test
""")

        registry.load_skills([skills_dir])
        registry.activate("test")

        registry.reload_all()
        assert isinstance(registry.active_skill, Skill)
        assert registry.active_skill.name == "test"

    def test_reload_all_no_loader(self, registry: SkillRegistry) -> None:
        """Test reload_all when no loader is set."""
        result = registry.reload_all()
        assert result == 0

    def test_get_stats(self, registry: SkillRegistry) -> None:
        """Test getting statistics."""
        registry.register(create_test_skill("builtin", is_builtin=True, tags=["a"]))
        registry.register(create_test_skill("custom", tags=["b"]))
        registry.activate("custom")

        stats = registry.get_stats()
        assert stats["total"] == 2
        assert stats["builtin"] == 1
        assert stats["custom"] == 1
        assert stats["active"] == "custom"
        assert set(stats["tags"]) == {"a", "b"}

    def test_get_stats_no_active(self, registry: SkillRegistry) -> None:
        """Test stats when no skill is active."""
        stats = registry.get_stats()
        assert stats["active"] is None

    def test_thread_safety(self, registry: SkillRegistry) -> None:
        """Test that singleton is thread-safe."""
        import threading

        results: list[SkillRegistry] = []

        def get_instance() -> None:
            results.append(SkillRegistry.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert all(r is results[0] for r in results)
