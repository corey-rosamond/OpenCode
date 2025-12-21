"""Unit tests for workflow template registry."""

from pathlib import Path

import pytest

from code_forge.workflows.models import WorkflowDefinition, WorkflowStep
from code_forge.workflows.registry import WorkflowTemplateRegistry


class TestWorkflowTemplateRegistry:
    """Tests for WorkflowTemplateRegistry class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        WorkflowTemplateRegistry.reset_instance()
        yield
        WorkflowTemplateRegistry.reset_instance()

    def test_singleton_pattern(self):
        """Given multiple calls to get_instance, returns same instance"""
        registry1 = WorkflowTemplateRegistry.get_instance()
        registry2 = WorkflowTemplateRegistry.get_instance()

        assert registry1 is registry2

    def test_discover_builtin_templates(self):
        """Given built-in templates directory, discovers all templates"""
        registry = WorkflowTemplateRegistry.get_instance()

        # Should discover 7 built-in templates
        templates = registry.list_templates()
        assert len(templates) >= 7

        # Check for expected templates
        template_names = [name for name, _, _ in templates]
        assert "pr-review" in template_names
        assert "bug-fix" in template_names
        assert "feature-implementation" in template_names
        assert "security-audit-full" in template_names
        assert "code-quality-improvement" in template_names
        assert "code-migration" in template_names
        assert "parallel-analysis" in template_names

    def test_get_template_exists(self):
        """Given existing template name, returns workflow definition"""
        registry = WorkflowTemplateRegistry.get_instance()

        template = registry.get_template("pr-review")

        assert template is not None
        assert template.name == "pr-review"
        assert len(template.steps) > 0

    def test_get_template_not_found(self):
        """Given non-existent template name, returns None"""
        registry = WorkflowTemplateRegistry.get_instance()

        template = registry.get_template("nonexistent-template")

        assert template is None

    def test_list_templates_format(self):
        """Given templates, returns list of tuples with correct format"""
        registry = WorkflowTemplateRegistry.get_instance()

        templates = registry.list_templates()

        assert len(templates) > 0
        for name, description, source in templates:
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert isinstance(source, str)
            assert len(name) > 0
            assert len(description) > 0

    def test_search_templates_by_name(self):
        """Given search query matching name, returns matching templates"""
        registry = WorkflowTemplateRegistry.get_instance()

        results = registry.search_templates("review")

        assert len(results) >= 1
        names = [name for name, _, _ in results]
        assert "pr-review" in names

    def test_search_templates_by_description(self):
        """Given search query matching description, returns matching templates"""
        registry = WorkflowTemplateRegistry.get_instance()

        results = registry.search_templates("security")

        assert len(results) >= 1
        names = [name for name, _, _ in results]
        assert "security-audit-full" in names

    def test_search_templates_case_insensitive(self):
        """Given search query in different case, returns matches"""
        registry = WorkflowTemplateRegistry.get_instance()

        results_lower = registry.search_templates("review")
        results_upper = registry.search_templates("REVIEW")
        results_mixed = registry.search_templates("Review")

        assert len(results_lower) == len(results_upper)
        assert len(results_lower) == len(results_mixed)

    def test_search_templates_no_match(self):
        """Given search query with no matches, returns empty list"""
        registry = WorkflowTemplateRegistry.get_instance()

        results = registry.search_templates("xyznonexistent")

        assert len(results) == 0

    def test_instantiate_template(self):
        """Given template name, instantiates workflow definition"""
        registry = WorkflowTemplateRegistry.get_instance()

        workflow = registry.instantiate("pr-review")

        assert workflow.name == "pr-review"
        assert len(workflow.steps) > 0

    def test_instantiate_nonexistent_template(self):
        """Given non-existent template name, raises ValueError"""
        registry = WorkflowTemplateRegistry.get_instance()

        with pytest.raises(ValueError, match="Template .* not found"):
            registry.instantiate("nonexistent")

    def test_register_runtime_template(self):
        """Given workflow definition, registers template at runtime"""
        registry = WorkflowTemplateRegistry.get_instance()

        workflow = WorkflowDefinition(
            name="test-runtime-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="general", description="Test step"),
            ],
        )

        registry.register_template(workflow, source="test")

        # Should be retrievable
        retrieved = registry.get_template("test-runtime-workflow")
        assert retrieved is not None
        assert retrieved.name == "test-runtime-workflow"

    def test_unregister_template(self):
        """Given registered template, unregisters it"""
        registry = WorkflowTemplateRegistry.get_instance()

        # Register a template
        workflow = WorkflowDefinition(
            name="test-temp-workflow",
            description="Temporary",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="general", description="Test"),
            ],
        )
        registry.register_template(workflow)

        # Unregister it
        result = registry.unregister_template("test-temp-workflow")

        assert result is True
        assert registry.get_template("test-temp-workflow") is None

    def test_unregister_nonexistent_template(self):
        """Given non-existent template name, returns False"""
        registry = WorkflowTemplateRegistry.get_instance()

        result = registry.unregister_template("nonexistent")

        assert result is False

    def test_reload_templates(self):
        """Given reload call, reloads templates from disk"""
        registry = WorkflowTemplateRegistry.get_instance()

        # Register a runtime template
        workflow = WorkflowDefinition(
            name="test-runtime",
            description="Runtime",
            version="1.0.0",
            steps=[WorkflowStep(id="step1", agent="general", description="Test")],
        )
        registry.register_template(workflow)

        # Reload should clear runtime templates
        registry.reload()

        # Runtime template should be gone
        assert registry.get_template("test-runtime") is None
        # Built-in templates should still exist
        assert registry.get_template("pr-review") is not None

    def test_discover_user_templates(self, tmp_path):
        """Given user templates directory, discovers user templates"""
        # Create a user template
        user_dir = tmp_path / "user_workflows"
        user_dir.mkdir()

        user_template = user_dir / "my-custom-workflow.yaml"
        user_template.write_text("""
name: my-custom-workflow
description: Custom user workflow
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: Test step
""")

        # Temporarily patch USER_DIR
        original_user_dir = WorkflowTemplateRegistry.USER_DIR
        WorkflowTemplateRegistry.USER_DIR = user_dir

        try:
            registry = WorkflowTemplateRegistry.get_instance()
            registry.discover_templates()

            # Should find the custom template
            template = registry.get_template("my-custom-workflow")
            assert template is not None
            assert template.description == "Custom user workflow"

        finally:
            WorkflowTemplateRegistry.USER_DIR = original_user_dir

    def test_discover_project_templates(self, tmp_path):
        """Given project templates directory, discovers project templates"""
        # Create a project template
        project_root = tmp_path
        project_templates_dir = project_root / ".forge" / "workflows"
        project_templates_dir.mkdir(parents=True)

        project_template = project_templates_dir / "project-workflow.yaml"
        project_template.write_text("""
name: project-workflow
description: Project-specific workflow
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: Project step
""")

        registry = WorkflowTemplateRegistry.get_instance()
        registry.discover_templates(project_root=project_root)

        # Should find the project template
        template = registry.get_template("project-workflow")
        assert template is not None
        assert template.description == "Project-specific workflow"

    def test_template_precedence(self, tmp_path):
        """Given same template in multiple locations, project overrides user overrides built-in"""
        # Create conflicting templates
        user_dir = tmp_path / "user"
        user_dir.mkdir()

        project_dir = tmp_path / "project" / ".forge" / "workflows"
        project_dir.mkdir(parents=True)

        # User template
        (user_dir / "test-precedence.yaml").write_text("""
name: test-precedence
description: User version
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: User step
""")

        # Project template (should win)
        (project_dir / "test-precedence.yaml").write_text("""
name: test-precedence
description: Project version
version: 2.0.0
steps:
  - id: step1
    agent: general
    description: Project step
""")

        # Temporarily patch directories
        original_user_dir = WorkflowTemplateRegistry.USER_DIR
        WorkflowTemplateRegistry.USER_DIR = user_dir

        try:
            registry = WorkflowTemplateRegistry.get_instance()
            registry.discover_templates(project_root=tmp_path / "project")

            # Should get project version
            template = registry.get_template("test-precedence")
            assert template is not None
            assert template.description == "Project version"
            assert template.version == "2.0.0"

        finally:
            WorkflowTemplateRegistry.USER_DIR = original_user_dir
