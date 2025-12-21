"""E2E tests for workflow system."""

import pytest


class TestWorkflowTemplateDiscovery:
    """E2E tests for workflow template discovery."""

    def test_discovers_builtin_templates(self):
        """Given builtin templates, discovers all 7 templates"""
        from code_forge.workflows.registry import WorkflowTemplateRegistry

        registry = WorkflowTemplateRegistry.get_instance()
        templates = registry.list_templates()

        # Should have at least 7 built-in templates
        assert len(templates) >= 7

        template_names = [name for name, _, _ in templates]
        assert "pr-review" in template_names
        assert "bug-fix" in template_names
        assert "feature-implementation" in template_names
        assert "security-audit-full" in template_names
        assert "code-quality-improvement" in template_names
        assert "code-migration" in template_names
        assert "parallel-analysis" in template_names

    def test_instantiates_template(self):
        """Given template name, instantiates workflow definition"""
        from code_forge.workflows.registry import WorkflowTemplateRegistry

        registry = WorkflowTemplateRegistry.get_instance()
        workflow = registry.instantiate("pr-review")

        assert workflow is not None
        assert workflow.name == "pr-review"
        assert len(workflow.steps) > 0

    def test_searches_templates(self):
        """Given search query, finds matching templates"""
        from code_forge.workflows.registry import WorkflowTemplateRegistry

        registry = WorkflowTemplateRegistry.get_instance()
        results = registry.search_templates("security")

        assert len(results) > 0
        names = [name for name, _, _ in results]
        assert "security-audit-full" in names


class TestWorkflowParsing:
    """E2E tests for workflow YAML parsing."""

    def test_parses_simple_workflow(self, temp_dir):
        """Given simple YAML workflow, parses correctly"""
        from code_forge.workflows.parser import YAMLWorkflowParser

        workflow_file = temp_dir / "simple.yaml"
        workflow_file.write_text("""
name: simple-test
description: Simple workflow for testing
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: First step
  - id: step2
    agent: general
    description: Second step
    depends_on: [step1]
""")

        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(workflow_file)

        assert workflow.name == "simple-test"
        assert len(workflow.steps) == 2
        assert workflow.steps[0].id == "step1"
        assert workflow.steps[1].id == "step2"
        assert workflow.steps[1].depends_on == ["step1"]

    def test_parses_complex_workflow(self, temp_dir):
        """Given complex workflow with conditions and parallel, parses correctly"""
        from code_forge.workflows.parser import YAMLWorkflowParser

        workflow_file = temp_dir / "complex.yaml"
        workflow_file.write_text("""
name: complex-test
description: Complex workflow with all features
version: 1.0.0
author: Test
metadata:
  category: testing
steps:
  - id: setup
    agent: general
    description: Setup step
    timeout: 300

  - id: test1
    agent: qa-manual
    description: First test
    depends_on: [setup]

  - id: test2
    agent: qa-manual
    description: Second test (parallel)
    depends_on: [setup]
    parallel_with: [test1]

  - id: verify
    agent: general
    description: Verify results
    depends_on: [test1, test2]
    condition: "test1.success AND test2.success"
""")

        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(workflow_file)

        assert workflow.name == "complex-test"
        assert len(workflow.steps) == 4
        assert workflow.steps[2].parallel_with == ["test1"]
        assert workflow.steps[3].condition == "test1.success AND test2.success"

    def test_validates_workflow(self, temp_dir):
        """Given workflow with cycle, raises validation error"""
        from code_forge.workflows.parser import YAMLWorkflowParser
        from code_forge.workflows.graph import WorkflowGraph, GraphValidator

        workflow_file = temp_dir / "invalid.yaml"
        workflow_file.write_text("""
name: invalid-cycle
description: Invalid workflow with cycle
version: 1.0.0
steps:
  - id: step1
    agent: general
    description: First step
    depends_on: [step2]

  - id: step2
    agent: general
    description: Second step
    depends_on: [step1]
""")

        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(workflow_file)

        # Parsing succeeds, but validation should fail
        graph = WorkflowGraph.from_definition(workflow)
        validator = GraphValidator(graph)

        with pytest.raises(ValueError, match="cycle"):
            validator.validate()


class TestWorkflowExecution:
    """E2E tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_executes_simple_workflow(self, temp_project):
        """Given simple workflow, executes all steps successfully"""
        from unittest.mock import AsyncMock, MagicMock
        from code_forge.workflows.models import WorkflowDefinition, WorkflowStep
        from code_forge.workflows.executor import WorkflowExecutor
        from code_forge.agents.result import AgentResult

        # Create simple workflow
        workflow = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="step1",
                    agent="general",
                    description="First step",
                ),
                WorkflowStep(
                    id="step2",
                    agent="general",
                    description="Second step",
                    depends_on=["step1"],
                ),
            ],
        )

        # Mock agent execution
        mock_agent_result = AgentResult(
            success=True,
            message="Step completed",
            data={},
        )

        with pytest.mock.patch("code_forge.workflows.executor.AgentManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.execute_task = AsyncMock(return_value=mock_agent_result)

            # Execute workflow
            executor = WorkflowExecutor(working_dir=str(temp_project))
            result = await executor.execute(workflow)

            assert result.success
            assert result.steps_completed == 2
            assert result.steps_failed == 0

    @pytest.mark.asyncio
    async def test_executes_workflow_with_failure(self, temp_project):
        """Given workflow where step fails, stops execution and returns result"""
        from unittest.mock import AsyncMock, MagicMock
        from code_forge.workflows.models import WorkflowDefinition, WorkflowStep
        from code_forge.workflows.executor import WorkflowExecutor
        from code_forge.agents.result import AgentResult

        workflow = WorkflowDefinition(
            name="test-failure",
            description="Test failure handling",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="general", description="First step"),
                WorkflowStep(id="step2", agent="general", description="Failing step", depends_on=["step1"]),
                WorkflowStep(id="step3", agent="general", description="Third step", depends_on=["step2"]),
            ],
        )

        # Mock: step1 succeeds, step2 fails
        def mock_execute(agent_type, task, **kwargs):
            if task == "First step":
                return AgentResult(success=True, message="Success", data={})
            else:
                return AgentResult(success=False, message="Failed", data={})

        with pytest.mock.patch("code_forge.workflows.executor.AgentManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.execute_task = AsyncMock(side_effect=mock_execute)

            executor = WorkflowExecutor(working_dir=str(temp_project))
            result = await executor.execute(workflow)

            assert not result.success
            assert result.steps_completed == 1
            assert result.steps_failed == 1
            assert result.steps_skipped == 1  # step3 skipped

    @pytest.mark.asyncio
    async def test_executes_parallel_steps(self, temp_project):
        """Given workflow with parallel steps, executes them concurrently"""
        from unittest.mock import AsyncMock, MagicMock
        from code_forge.workflows.models import WorkflowDefinition, WorkflowStep
        from code_forge.workflows.executor import WorkflowExecutor
        from code_forge.agents.result import AgentResult

        workflow = WorkflowDefinition(
            name="test-parallel",
            description="Test parallel execution",
            version="1.0.0",
            steps=[
                WorkflowStep(id="setup", agent="general", description="Setup"),
                WorkflowStep(id="test1", agent="general", description="Test 1", depends_on=["setup"]),
                WorkflowStep(id="test2", agent="general", description="Test 2", depends_on=["setup"], parallel_with=["test1"]),
            ],
        )

        mock_result = AgentResult(success=True, message="Done", data={})

        with pytest.mock.patch("code_forge.workflows.executor.AgentManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.execute_task = AsyncMock(return_value=mock_result)

            executor = WorkflowExecutor(working_dir=str(temp_project))
            result = await executor.execute(workflow)

            assert result.success
            assert result.steps_completed == 3


class TestWorkflowCommands:
    """E2E tests for workflow slash commands."""

    @pytest.mark.asyncio
    async def test_workflow_list_command(self):
        """Given /workflow list command, lists all templates"""
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext
        from code_forge.workflows.commands import WorkflowListCommand

        cmd = WorkflowListCommand()
        parsed = ParsedCommand(name="workflow-list", args=[], raw="workflow-list")
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert result.success
        assert "workflow templates" in result.output.lower()
        assert "pr-review" in result.output

    @pytest.mark.asyncio
    async def test_workflow_list_with_search(self):
        """Given /workflow list with query, searches templates"""
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext
        from code_forge.workflows.commands import WorkflowListCommand

        cmd = WorkflowListCommand()
        parsed = ParsedCommand(name="workflow-list", args=["security"], raw="workflow-list security")
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert result.success
        assert "security" in result.output.lower()


class TestWorkflowTool:
    """E2E tests for workflow LLM tool."""

    @pytest.mark.asyncio
    async def test_workflow_tool_list(self, execution_context):
        """Given Workflow tool list operation, returns templates"""
        from code_forge.workflows.tool import WorkflowTool

        tool = WorkflowTool()
        result = await tool._execute(execution_context, operation="list")

        assert result.success
        assert isinstance(result.output, dict)
        assert "templates" in result.output
        assert result.output["count"] >= 7

    @pytest.mark.asyncio
    async def test_workflow_tool_search(self, execution_context):
        """Given Workflow tool search operation, finds templates"""
        from code_forge.workflows.tool import WorkflowTool

        tool = WorkflowTool()
        result = await tool._execute(execution_context, operation="search", query="security")

        assert result.success
        assert isinstance(result.output, dict)
        assert result.output["query"] == "security"
        assert len(result.output["templates"]) > 0

    @pytest.mark.asyncio
    async def test_workflow_tool_info(self, execution_context):
        """Given Workflow tool info operation, returns template details"""
        from code_forge.workflows.tool import WorkflowTool

        tool = WorkflowTool()
        result = await tool._execute(execution_context, operation="info", template_name="pr-review")

        assert result.success
        assert isinstance(result.output, dict)
        assert result.output["name"] == "pr-review"
        assert "steps" in result.output
        assert result.output["total_steps"] > 0
