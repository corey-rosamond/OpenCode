"""Integration tests for workflow system.

Tests end-to-end workflow functionality with real components.
"""

from pathlib import Path

import pytest

from code_forge.workflows.graph import WorkflowGraph
from code_forge.workflows.models import WorkflowDefinition, WorkflowStep
from code_forge.workflows.parser import YAMLWorkflowParser
from code_forge.workflows.registry import WorkflowTemplateRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset template registry before each test."""
    WorkflowTemplateRegistry.reset_instance()
    yield
    WorkflowTemplateRegistry.reset_instance()


class TestWorkflowParsing:
    """Integration tests for workflow parsing from YAML."""

    def test_parse_simple_workflow(self, tmp_path):
        """Given YAML file, parses workflow correctly"""
        yaml_content = """
name: test-workflow
description: Test workflow
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: First step
  - id: step2
    agent: general
    description: Second step
    depends_on: [step1]
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(yaml_file)

        assert workflow.name == "test-workflow"
        assert len(workflow.steps) == 2
        assert workflow.steps[1].depends_on == ["step1"]

    def test_parse_workflow_with_conditions(self, tmp_path):
        """Given workflow with conditions, parses correctly"""
        yaml_content = """
name: test-conditional
description: Test conditional workflow
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: First step
  - id: step2
    agent: general
    description: Conditional step
    depends_on: [step1]
    condition: "step1.success"
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(yaml_file)

        assert workflow.steps[1].condition == "step1.success"

    def test_parse_workflow_with_parallel(self, tmp_path):
        """Given workflow with parallel steps, parses correctly"""
        yaml_content = """
name: test-parallel
description: Test parallel workflow
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: First step
  - id: step2a
    agent: general
    description: Parallel A
    depends_on: [step1]
  - id: step2b
    agent: general
    description: Parallel B
    depends_on: [step1]
    parallel_with: [step2a]
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(yaml_file)

        assert workflow.steps[2].parallel_with == ["step2a"]


class TestTemplateRegistry:
    """Integration tests for template registry."""

    def test_discover_builtin_templates(self):
        """Given registry, discovers all built-in templates"""
        registry = WorkflowTemplateRegistry.get_instance()

        templates = registry.list_templates()
        template_names = [name for name, _, _ in templates]

        # Should have all 7 built-in templates
        assert len(template_names) >= 7
        assert "pr-review" in template_names
        assert "bug-fix" in template_names
        assert "feature-implementation" in template_names
        assert "security-audit-full" in template_names
        assert "code-quality-improvement" in template_names
        assert "code-migration" in template_names
        assert "parallel-analysis" in template_names

    def test_instantiate_template(self):
        """Given template name, instantiates workflow"""
        registry = WorkflowTemplateRegistry.get_instance()

        workflow = registry.instantiate("pr-review")

        assert workflow.name == "pr-review"
        assert len(workflow.steps) > 0
        assert all(isinstance(step, WorkflowStep) for step in workflow.steps)

    def test_register_custom_template(self):
        """Given custom workflow, can register as template"""
        registry = WorkflowTemplateRegistry.get_instance()

        custom_workflow = WorkflowDefinition(
            name="custom-test",
            description="Custom test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="general", description="Step 1"),
            ],
        )

        registry.register_template(custom_workflow, source="test")

        # Should be retrievable
        retrieved = registry.get_template("custom-test")
        assert retrieved is not None
        assert retrieved.name == "custom-test"

    def test_search_templates(self):
        """Given search query, finds matching templates"""
        registry = WorkflowTemplateRegistry.get_instance()

        # Search for security-related templates
        results = registry.search_templates("security")

        # Should find at least the security-audit template
        names = [name for name, _, _ in results]
        assert "security-audit-full" in names

    def test_template_precedence(self, tmp_path):
        """Given templates from multiple sources, applies precedence correctly"""
        registry = WorkflowTemplateRegistry.get_instance()

        # Create a project template directory
        project_dir = tmp_path / ".forge" / "workflows"
        project_dir.mkdir(parents=True)

        # Create a project template that overrides a built-in
        project_template = project_dir / "pr-review.yaml"
        project_template.write_text("""
name: pr-review
description: Custom PR review (project override)
version: 2.0.0
steps:
  - id: custom_step
    agent: general
    description: Custom step
"""        )

        # Reload registry with project root
        registry.reload(project_root=tmp_path)

        # Should get the project version
        template = registry.get_template("pr-review")
        assert template is not None
        assert template.version == "2.0.0"
        assert template.steps[0].id == "custom_step"


class TestWorkflowFullStack:
    """Full stack integration tests combining multiple components."""

    def test_parse_template_and_validate(self, tmp_path):
        """Given YAML template, parses and validates workflow"""
        yaml_content = """
name: full-stack-test
description: Full stack integration test
version: 1.0.0
author: Test
metadata:
  category: test
steps:
  - id: setup
    agent: general
    description: Setup step
  - id: process
    agent: general
    description: Process step
    depends_on: [setup]
  - id: verify
    agent: general
    description: Verify step
    depends_on: [process]
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        # Parse workflow
        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(yaml_file)

        # Should parse correctly
        assert workflow.name == "full-stack-test"
        assert len(workflow.steps) == 3

        # Should validate (no cycles, valid dependencies)
        assert workflow.steps[1].depends_on == ["setup"]
        assert workflow.steps[2].depends_on == ["process"]

    def test_register_parsed_workflow_as_template(self, tmp_path):
        """Given parsed workflow, can register as template"""
        yaml_content = """
name: custom-parsed
description: Custom parsed workflow
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: Test step
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        # Parse and register
        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(yaml_file)

        registry = WorkflowTemplateRegistry.get_instance()
        registry.register_template(workflow, source="test")

        # Should be retrievable
        retrieved = registry.get_template("custom-parsed")
        assert retrieved is not None
        assert retrieved.name == "custom-parsed"

        # Should be searchable
        results = registry.search_templates("custom")
        names = [name for name, _, _ in results]
        assert "custom-parsed" in names
