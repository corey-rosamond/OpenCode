"""Tests for workflow composer."""

from __future__ import annotations

import pytest

from code_forge.natural.intent import IntentType
from code_forge.workflows.composer import (
    ComposedWorkflow,
    StepTemplate,
    WorkflowComposer,
)


class TestComposedWorkflow:
    """Tests for ComposedWorkflow dataclass."""

    def test_creation(self) -> None:
        """Test workflow creation."""
        from code_forge.workflows.models import WorkflowStep

        steps = [
            WorkflowStep(id="step1", agent="general", description="Test step"),
        ]
        workflow = ComposedWorkflow(
            name="test-workflow",
            description="A test workflow",
            steps=steps,
            source_request="test request",
            confidence=0.9,
        )
        assert workflow.name == "test-workflow"
        assert len(workflow.steps) == 1
        assert workflow.confidence == 0.9

    def test_to_definition(self) -> None:
        """Test conversion to WorkflowDefinition."""
        from code_forge.workflows.models import WorkflowStep

        steps = [
            WorkflowStep(id="step1", agent="general", description="Test step"),
        ]
        workflow = ComposedWorkflow(
            name="test-workflow",
            description="A test workflow",
            steps=steps,
            source_request="test request",
            confidence=0.9,
        )
        definition = workflow.to_definition()
        assert definition.name == "test-workflow"
        assert len(definition.steps) == 1
        assert definition.metadata.get("auto_composed") is True


class TestStepTemplate:
    """Tests for StepTemplate dataclass."""

    def test_creation(self) -> None:
        """Test template creation."""
        template = StepTemplate(
            id_prefix="test",
            agent="general",
            description_template="Test {param}",
            input_template="Process {param}",
            timeout=600,
        )
        assert template.id_prefix == "test"
        assert template.agent == "general"
        assert template.timeout == 600

    def test_default_timeout(self) -> None:
        """Test default timeout value."""
        template = StepTemplate(
            id_prefix="test",
            agent="general",
            description_template="Test",
            input_template="Test",
        )
        assert template.timeout == 300


class TestWorkflowComposer:
    """Tests for WorkflowComposer."""

    @pytest.fixture
    def composer(self) -> WorkflowComposer:
        """Create a composer instance."""
        return WorkflowComposer()

    def test_compose_simple_request(self, composer: WorkflowComposer) -> None:
        """Test composing from simple request returns None."""
        # Simple requests shouldn't create workflows
        result = composer.compose("read config.py")
        assert result is None

    def test_compose_replace_all(self, composer: WorkflowComposer) -> None:
        """Test composing replace all workflow."""
        result = composer.compose("replace all oldValue with newValue across the project")
        assert result is not None
        assert len(result.steps) >= 2
        assert result.confidence >= 0.7

    def test_compose_refactor(self, composer: WorkflowComposer) -> None:
        """Test composing refactor workflow."""
        result = composer.compose("refactor the utils module")
        assert result is not None
        assert len(result.steps) >= 2

    def test_compose_sequence_with_then(self, composer: WorkflowComposer) -> None:
        """Test composing sequence with 'then'."""
        result = composer.compose("search for errors then fix them")
        assert result is not None
        assert len(result.steps) >= 2
        # Later steps should depend on earlier
        if len(result.steps) > 1:
            assert result.steps[1].depends_on is not None

    def test_compose_sequence_with_and_then(self, composer: WorkflowComposer) -> None:
        """Test composing sequence with 'and then'."""
        result = composer.compose("find the bug and then fix it and then run tests")
        assert result is not None
        assert len(result.steps) >= 2

    def test_compose_empty_string(self, composer: WorkflowComposer) -> None:
        """Test empty string returns None."""
        assert composer.compose("") is None
        assert composer.compose("   ") is None

    def test_compose_from_intents(self, composer: WorkflowComposer) -> None:
        """Test composing from explicit intents."""
        intents = [IntentType.SEARCH_CONTENT, IntentType.RUN_TESTS]
        parameters = {"query": "TODO", "target": "all tests"}
        result = composer.compose_from_intents(intents, parameters)
        assert result is not None
        assert len(result.steps) >= 2
        assert result.confidence > 0

    def test_compose_from_empty_intents(self, composer: WorkflowComposer) -> None:
        """Test composing from empty intents list."""
        result = composer.compose_from_intents([], {})
        assert result is not None
        assert len(result.steps) == 0
        assert result.confidence == 0.0

    def test_workflow_has_dependencies(self, composer: WorkflowComposer) -> None:
        """Test that multi-step workflows have proper dependencies."""
        result = composer.compose("replace all foo with bar then run tests")
        assert result is not None
        # Check that steps have dependencies
        has_dependencies = any(step.depends_on for step in result.steps[1:])
        assert has_dependencies or len(result.steps) <= 1

    def test_to_definition_preserves_metadata(self, composer: WorkflowComposer) -> None:
        """Test that conversion preserves metadata."""
        result = composer.compose("refactor the code then test it")
        assert result is not None
        definition = result.to_definition()
        assert definition.metadata.get("auto_composed") is True
        assert "source_request" in definition.metadata

    def test_get_suggested_agents_refactor(self, composer: WorkflowComposer) -> None:
        """Test getting suggested agents for refactor."""
        agents = composer.get_suggested_agents("refactor the module")
        assert len(agents) >= 1
        assert any("refactor" in a.lower() for a in agents)

    def test_get_suggested_agents_search(self, composer: WorkflowComposer) -> None:
        """Test getting suggested agents for search."""
        agents = composer.get_suggested_agents("search for TODO in codebase")
        assert len(agents) >= 1

    def test_get_suggested_agents_unknown(self, composer: WorkflowComposer) -> None:
        """Test getting suggested agents for unknown request."""
        agents = composer.get_suggested_agents("hello world")
        # Should return empty or general agents
        assert isinstance(agents, list)

    def test_workflow_name_generation(self, composer: WorkflowComposer) -> None:
        """Test that workflow names are generated sensibly."""
        result = composer.compose("find bugs then fix them")
        assert result is not None
        assert result.name is not None
        assert len(result.name) > 0
        assert "-" in result.name or result.name.isalnum()

    def test_workflow_description_generation(self, composer: WorkflowComposer) -> None:
        """Test that workflow descriptions are generated."""
        result = composer.compose("search for errors and then analyze them")
        assert result is not None
        assert "Auto-generated" in result.description or len(result.description) > 0


class TestWorkflowComposerEdgeCases:
    """Edge case tests for WorkflowComposer."""

    @pytest.fixture
    def composer(self) -> WorkflowComposer:
        """Create a composer instance."""
        return WorkflowComposer()

    def test_very_long_request(self, composer: WorkflowComposer) -> None:
        """Test handling very long requests."""
        long_request = "find all bugs " + "then fix them " * 50
        result = composer.compose(long_request)
        # Should handle gracefully (either compose or return None)
        assert result is None or isinstance(result, ComposedWorkflow)

    def test_special_characters(self, composer: WorkflowComposer) -> None:
        """Test handling special characters."""
        result = composer.compose("replace all @#$% with &*()")
        # Should not crash
        assert result is None or isinstance(result, ComposedWorkflow)

    def test_unicode_content(self, composer: WorkflowComposer) -> None:
        """Test handling unicode content."""
        result = composer.compose("replace all émoji with 文字")
        # Should not crash
        assert result is None or isinstance(result, ComposedWorkflow)
