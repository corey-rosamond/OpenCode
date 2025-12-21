"""Unit tests for workflow parsers."""

from pathlib import Path

import pytest

from code_forge.workflows.parser import PythonWorkflowBuilder, YAMLWorkflowParser


class TestYAMLWorkflowParser:
    """Tests for YAMLWorkflowParser class."""

    @pytest.fixture
    def parser(self):
        """Creates a YAML parser instance."""
        return YAMLWorkflowParser()

    def test_parse_minimal_workflow(self, parser):
        """Given minimal valid YAML, parses to WorkflowDefinition"""
        yaml_content = """
name: test-workflow
description: Test workflow
version: 1.0.0
steps:
  - id: step1
    agent: test
    description: Test step
"""
        workflow = parser.parse(yaml_content)

        assert workflow.name == "test-workflow"
        assert workflow.description == "Test workflow"
        assert workflow.version == "1.0.0"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step1"

    def test_parse_complete_workflow(self, parser):
        """Given complete YAML with all features, parses correctly"""
        yaml_content = """
name: complex-workflow
description: Complex test workflow
version: 2.0.0
author: test-author
metadata:
  category: testing
  priority: high
steps:
  - id: step1
    agent: plan
    description: Planning step
    inputs:
      task: analyze code
    timeout: 300
    max_retries: 2

  - id: step2
    agent: review
    description: Review step
    depends_on:
      - step1
    condition: step1.success

  - id: step3
    agent: test
    description: Test step
    depends_on:
      - step1
    parallel_with:
      - step2
"""
        workflow = parser.parse(yaml_content)

        assert workflow.name == "complex-workflow"
        assert workflow.author == "test-author"
        assert workflow.metadata == {"category": "testing", "priority": "high"}
        assert len(workflow.steps) == 3

        # Check step 1
        step1 = workflow.steps[0]
        assert step1.id == "step1"
        assert step1.agent == "plan"
        assert step1.inputs == {"task": "analyze code"}
        assert step1.timeout == 300
        assert step1.max_retries == 2

        # Check step 2
        step2 = workflow.steps[1]
        assert step2.depends_on == ["step1"]
        assert step2.condition == "step1.success"

        # Check step 3
        step3 = workflow.steps[2]
        assert step3.parallel_with == ["step2"]

    def test_reject_empty_yaml(self, parser):
        """Given empty YAML, raises ValueError"""
        with pytest.raises(ValueError, match="Empty YAML content"):
            parser.parse("")

    def test_reject_invalid_yaml_syntax(self, parser):
        """Given invalid YAML syntax, raises ValueError"""
        yaml_content = """
name: test
  bad indent:
    - wrong
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse(yaml_content)

    def test_reject_missing_name(self, parser):
        """Given YAML without name, raises ValueError"""
        yaml_content = """
description: Test
version: 1.0.0
steps:
  - id: step1
    agent: test
    description: Test
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_missing_description(self, parser):
        """Given YAML without description, raises ValueError"""
        yaml_content = """
name: test
version: 1.0.0
steps:
  - id: step1
    agent: test
    description: Test
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_missing_version(self, parser):
        """Given YAML without version, raises ValueError"""
        yaml_content = """
name: test
description: Test
steps:
  - id: step1
    agent: test
    description: Test
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_empty_steps(self, parser):
        """Given YAML with empty steps list, raises ValueError"""
        yaml_content = """
name: test
description: Test
version: 1.0.0
steps: []
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_missing_step_id(self, parser):
        """Given step without ID, raises ValueError"""
        yaml_content = """
name: test
description: Test
version: 1.0.0
steps:
  - agent: test
    description: Test
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_missing_step_agent(self, parser):
        """Given step without agent, raises ValueError"""
        yaml_content = """
name: test
description: Test
version: 1.0.0
steps:
  - id: step1
    description: Test
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_negative_timeout(self, parser):
        """Given step with negative timeout, raises ValueError"""
        yaml_content = """
name: test
description: Test
version: 1.0.0
steps:
  - id: step1
    agent: test
    description: Test
    timeout: -10
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_reject_negative_retries(self, parser):
        """Given step with negative retries, raises ValueError"""
        yaml_content = """
name: test
description: Test
version: 1.0.0
steps:
  - id: step1
    agent: test
    description: Test
    max_retries: -1
"""
        with pytest.raises(ValueError, match="validation failed"):
            parser.parse(yaml_content)

    def test_parse_file_success(self, parser, tmp_path):
        """Given valid YAML file, parses successfully"""
        yaml_file = tmp_path / "workflow.yaml"
        yaml_file.write_text("""
name: file-workflow
description: Test workflow from file
version: 1.0.0
steps:
  - id: step1
    agent: test
    description: Test step
""")

        workflow = parser.parse_file(yaml_file)

        assert workflow.name == "file-workflow"
        assert len(workflow.steps) == 1

    def test_reject_nonexistent_file(self, parser, tmp_path):
        """Given non-existent file path, raises FileNotFoundError"""
        yaml_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            parser.parse_file(yaml_file)

    def test_reject_directory_as_file(self, parser, tmp_path):
        """Given directory path instead of file, raises ValueError"""
        with pytest.raises(ValueError, match="Not a file"):
            parser.parse_file(tmp_path)


class TestPythonWorkflowBuilder:
    """Tests for PythonWorkflowBuilder class."""

    def test_create_builder_with_name_version(self):
        """Given name and version, creates builder"""
        builder = PythonWorkflowBuilder("test-workflow", "1.0.0")

        assert builder._name == "test-workflow"
        assert builder._version == "1.0.0"

    def test_reject_empty_name(self):
        """Given empty name, raises ValueError"""
        with pytest.raises(ValueError, match="Workflow name cannot be empty"):
            PythonWorkflowBuilder("", "1.0.0")

    def test_reject_empty_version(self):
        """Given empty version, raises ValueError"""
        with pytest.raises(ValueError, match="Workflow version cannot be empty"):
            PythonWorkflowBuilder("test", "")

    def test_fluent_api_chains(self):
        """Given fluent API calls, returns self for chaining"""
        builder = PythonWorkflowBuilder("test", "1.0.0")

        result = builder.description("Test workflow")
        assert result is builder

        result = builder.author("Test Author")
        assert result is builder

        result = builder.metadata("key", "value")
        assert result is builder

    def test_add_single_step(self):
        """Given add_step call, adds step to workflow"""
        builder = PythonWorkflowBuilder("test", "1.0.0")
        builder.description("Test")
        builder.add_step("step1", "test", "Test step")

        assert len(builder._steps) == 1
        assert builder._steps[0].id == "step1"

    def test_add_step_with_all_options(self):
        """Given step with all options, creates complete step"""
        builder = PythonWorkflowBuilder("test", "1.0.0")
        builder.description("Test")
        builder.add_step(
            step_id="step1",
            agent="plan",
            description="Planning",
            inputs={"task": "analyze"},
            depends_on=["step0"],
            parallel_with=["step2"],
            condition="step0.success",
            timeout=300,
            max_retries=2,
        )

        step = builder._steps[0]
        assert step.id == "step1"
        assert step.agent == "plan"
        assert step.inputs == {"task": "analyze"}
        assert step.depends_on == ["step0"]
        assert step.parallel_with == ["step2"]
        assert step.condition == "step0.success"
        assert step.timeout == 300
        assert step.max_retries == 2

    def test_reject_duplicate_step_id(self):
        """Given duplicate step ID, raises ValueError"""
        builder = PythonWorkflowBuilder("test", "1.0.0")
        builder.description("Test")
        builder.add_step("step1", "test", "Test 1")

        with pytest.raises(ValueError, match="Step with ID 'step1' already exists"):
            builder.add_step("step1", "test", "Test 2")

    def test_build_minimal_workflow(self):
        """Given minimal builder setup, builds WorkflowDefinition"""
        builder = PythonWorkflowBuilder("test-workflow", "1.0.0")
        builder.description("Test workflow")
        builder.add_step("step1", "test", "Test step")

        workflow = builder.build()

        assert workflow.name == "test-workflow"
        assert workflow.version == "1.0.0"
        assert workflow.description == "Test workflow"
        assert len(workflow.steps) == 1

    def test_build_complete_workflow(self):
        """Given complete builder setup, builds full WorkflowDefinition"""
        builder = PythonWorkflowBuilder("complete-workflow", "2.0.0")
        builder.description("Complete test workflow")
        builder.author("Test Author")
        builder.metadata("category", "testing")
        builder.metadata("priority", "high")
        builder.add_step("step1", "plan", "Planning")
        builder.add_step("step2", "review", "Review", depends_on=["step1"])

        workflow = builder.build()

        assert workflow.author == "Test Author"
        assert workflow.metadata == {"category": "testing", "priority": "high"}
        assert len(workflow.steps) == 2

    def test_reject_build_without_description(self):
        """Given builder without description, build raises ValueError"""
        builder = PythonWorkflowBuilder("test", "1.0.0")
        builder.add_step("step1", "test", "Test")

        with pytest.raises(ValueError, match="Workflow description is required"):
            builder.build()

    def test_reject_build_without_steps(self):
        """Given builder without steps, build raises ValueError"""
        builder = PythonWorkflowBuilder("test", "1.0.0")
        builder.description("Test")

        with pytest.raises(ValueError, match="Workflow must have at least one step"):
            builder.build()

    def test_python_api_matches_yaml(self):
        """Given same workflow via Python and YAML, results match"""
        # Create via Python API
        python_builder = PythonWorkflowBuilder("test-workflow", "1.0.0")
        python_builder.description("Test workflow")
        python_builder.author("Test Author")
        python_builder.add_step("step1", "plan", "Planning step")
        python_builder.add_step(
            "step2",
            "review",
            "Review step",
            depends_on=["step1"],
            condition="step1.success",
        )
        python_workflow = python_builder.build()

        # Create via YAML
        yaml_content = """
name: test-workflow
description: Test workflow
version: 1.0.0
author: Test Author
steps:
  - id: step1
    agent: plan
    description: Planning step
  - id: step2
    agent: review
    description: Review step
    depends_on:
      - step1
    condition: step1.success
"""
        yaml_parser = YAMLWorkflowParser()
        yaml_workflow = yaml_parser.parse(yaml_content)

        # Compare results
        assert python_workflow.name == yaml_workflow.name
        assert python_workflow.description == yaml_workflow.description
        assert python_workflow.version == yaml_workflow.version
        assert python_workflow.author == yaml_workflow.author
        assert len(python_workflow.steps) == len(yaml_workflow.steps)

        for py_step, yaml_step in zip(python_workflow.steps, yaml_workflow.steps):
            assert py_step.id == yaml_step.id
            assert py_step.agent == yaml_step.agent
            assert py_step.description == yaml_step.description
            assert py_step.depends_on == yaml_step.depends_on
            assert py_step.condition == yaml_step.condition
