"""Tests for agent type definitions and registry."""

import pytest

from code_forge.agents.types import (
    EXPLORE_AGENT,
    PLAN_AGENT,
    CODE_REVIEW_AGENT,
    GENERAL_AGENT,
    AgentTypeDefinition,
    AgentTypeRegistry,
)


class TestAgentTypeDefinition:
    """Tests for AgentTypeDefinition dataclass."""

    def test_minimal_definition(self) -> None:
        """Test definition with required fields only."""
        type_def = AgentTypeDefinition(
            name="test",
            description="A test agent",
            prompt_template="You are a test agent.",
        )
        assert type_def.name == "test"
        assert type_def.description == "A test agent"
        assert type_def.prompt_template == "You are a test agent."

    def test_default_values(self) -> None:
        """Test default values."""
        type_def = AgentTypeDefinition(
            name="test",
            description="Test",
            prompt_template="Template",
        )
        assert type_def.default_tools is None
        assert type_def.default_max_tokens == 50000
        assert type_def.default_max_time == 300
        assert type_def.default_model is None

    def test_full_definition(self) -> None:
        """Test definition with all fields."""
        type_def = AgentTypeDefinition(
            name="custom",
            description="Custom agent",
            prompt_template="Custom prompt",
            default_tools=["read", "write"],
            default_max_tokens=10000,
            default_max_time=60,
            default_model="claude-3-sonnet",
        )
        assert type_def.default_tools == ["read", "write"]
        assert type_def.default_max_tokens == 10000
        assert type_def.default_max_time == 60
        assert type_def.default_model == "claude-3-sonnet"

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        type_def = AgentTypeDefinition(
            name="test",
            description="Test agent",
            prompt_template="Template",
            default_tools=["read"],
        )
        d = type_def.to_dict()

        assert d["name"] == "test"
        assert d["description"] == "Test agent"
        assert d["prompt_template"] == "Template"
        assert d["default_tools"] == ["read"]


class TestBuiltinAgentTypes:
    """Tests for built-in agent type definitions."""

    def test_explore_agent(self) -> None:
        """Test EXPLORE_AGENT definition."""
        assert EXPLORE_AGENT.name == "explore"
        assert "explore" in EXPLORE_AGENT.description.lower()
        assert EXPLORE_AGENT.prompt_template != ""
        assert isinstance(EXPLORE_AGENT.default_tools, list)
        assert "glob" in EXPLORE_AGENT.default_tools
        assert "grep" in EXPLORE_AGENT.default_tools
        assert "read" in EXPLORE_AGENT.default_tools
        assert EXPLORE_AGENT.default_max_tokens == 30000
        assert EXPLORE_AGENT.default_max_time == 180

    def test_plan_agent(self) -> None:
        """Test PLAN_AGENT definition."""
        assert PLAN_AGENT.name == "plan"
        assert "plan" in PLAN_AGENT.description.lower()
        assert PLAN_AGENT.prompt_template != ""
        assert isinstance(PLAN_AGENT.default_tools, list)
        assert PLAN_AGENT.default_max_tokens == 40000
        assert PLAN_AGENT.default_max_time == 240

    def test_code_review_agent(self) -> None:
        """Test CODE_REVIEW_AGENT definition."""
        assert CODE_REVIEW_AGENT.name == "code-review"
        assert "review" in CODE_REVIEW_AGENT.description.lower()
        assert CODE_REVIEW_AGENT.prompt_template != ""
        assert isinstance(CODE_REVIEW_AGENT.default_tools, list)
        assert "bash" in CODE_REVIEW_AGENT.default_tools
        assert CODE_REVIEW_AGENT.default_max_tokens == 40000
        assert CODE_REVIEW_AGENT.default_max_time == 300

    def test_general_agent(self) -> None:
        """Test GENERAL_AGENT definition."""
        assert GENERAL_AGENT.name == "general"
        assert "general" in GENERAL_AGENT.description.lower()
        assert GENERAL_AGENT.prompt_template != ""
        assert GENERAL_AGENT.default_tools is None  # All tools
        assert GENERAL_AGENT.default_max_tokens == 50000
        assert GENERAL_AGENT.default_max_time == 300


class TestAgentTypeRegistry:
    """Tests for AgentTypeRegistry singleton."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        AgentTypeRegistry.reset_instance()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        AgentTypeRegistry.reset_instance()

    def test_singleton_instance(self) -> None:
        """Test get_instance returns singleton."""
        instance1 = AgentTypeRegistry.get_instance()
        instance2 = AgentTypeRegistry.get_instance()
        assert instance1 is instance2

    def test_reset_instance(self) -> None:
        """Test reset_instance creates new singleton."""
        instance1 = AgentTypeRegistry.get_instance()
        AgentTypeRegistry.reset_instance()
        instance2 = AgentTypeRegistry.get_instance()
        assert instance1 is not instance2

    def test_builtin_types_registered(self) -> None:
        """Test built-in types are auto-registered."""
        registry = AgentTypeRegistry.get_instance()
        types = registry.list_types()

        assert "explore" in types
        assert "plan" in types
        assert "code-review" in types
        assert "general" in types

    def test_get_existing_type(self) -> None:
        """Test get returns existing type."""
        registry = AgentTypeRegistry.get_instance()
        type_def = registry.get("explore")

        assert isinstance(type_def, AgentTypeDefinition)
        assert type_def.name == "explore"

    def test_get_nonexistent_type(self) -> None:
        """Test get returns None for unknown type."""
        registry = AgentTypeRegistry.get_instance()
        type_def = registry.get("nonexistent")
        assert type_def is None

    def test_exists_true(self) -> None:
        """Test exists returns True for registered type."""
        registry = AgentTypeRegistry.get_instance()
        assert registry.exists("explore") is True

    def test_exists_false(self) -> None:
        """Test exists returns False for unknown type."""
        registry = AgentTypeRegistry.get_instance()
        assert registry.exists("unknown") is False

    def test_register_custom_type(self) -> None:
        """Test registering custom type."""
        registry = AgentTypeRegistry.get_instance()
        custom = AgentTypeDefinition(
            name="custom",
            description="Custom agent",
            prompt_template="Template",
        )

        registry.register(custom)

        assert registry.exists("custom")
        assert registry.get("custom") == custom

    def test_register_duplicate_raises(self) -> None:
        """Test registering duplicate type raises error."""
        registry = AgentTypeRegistry.get_instance()

        with pytest.raises(ValueError, match="already registered"):
            registry.register(EXPLORE_AGENT)

    def test_unregister_existing(self) -> None:
        """Test unregistering existing type."""
        registry = AgentTypeRegistry.get_instance()
        custom = AgentTypeDefinition(
            name="to-remove",
            description="Test",
            prompt_template="Template",
        )
        registry.register(custom)

        result = registry.unregister("to-remove")

        assert result is True
        assert registry.exists("to-remove") is False

    def test_unregister_nonexistent(self) -> None:
        """Test unregistering nonexistent type."""
        registry = AgentTypeRegistry.get_instance()
        result = registry.unregister("nonexistent")
        assert result is False

    def test_list_types(self) -> None:
        """Test list_types returns all type names."""
        registry = AgentTypeRegistry.get_instance()
        types = registry.list_types()

        assert isinstance(types, list)
        assert len(types) >= 4  # At least built-in types
        assert all(isinstance(t, str) for t in types)

    def test_list_definitions(self) -> None:
        """Test list_definitions returns all definitions."""
        registry = AgentTypeRegistry.get_instance()
        defs = registry.list_definitions()

        assert isinstance(defs, list)
        assert len(defs) >= 4
        assert all(isinstance(d, AgentTypeDefinition) for d in defs)

    def test_thread_safety(self) -> None:
        """Test registry operations are thread-safe."""
        import threading

        registry = AgentTypeRegistry.get_instance()
        errors: list[Exception] = []

        def register_types(start: int) -> None:
            try:
                for i in range(start, start + 10):
                    try:
                        registry.register(AgentTypeDefinition(
                            name=f"thread-{start}-{i}",
                            description="Test",
                            prompt_template="Template",
                        ))
                    except ValueError:
                        pass  # Duplicate is OK
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_types, args=(i * 100,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
