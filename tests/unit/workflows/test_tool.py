"""Unit tests for workflow tool."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.tools.base import ExecutionContext
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
)
from code_forge.workflows.tool import WorkflowTool


@pytest.fixture
def execution_context():
    """Create an execution context for testing."""
    return ExecutionContext(
        working_dir="/tmp/test",
        session_id="test-session",
    )


@pytest.fixture
def sample_workflow():
    """Create a sample workflow definition."""
    return WorkflowDefinition(
        name="test-workflow",
        description="Test workflow",
        version="1.0.0",
        author="Test",
        steps=[
            WorkflowStep(
                id="step1",
                agent="general",
                description="Step 1",
                timeout=300,
            ),
            WorkflowStep(
                id="step2",
                agent="general",
                description="Step 2",
                depends_on=["step1"],
                timeout=300,
            ),
        ],
    )


class TestWorkflowTool:
    """Tests for WorkflowTool class."""

    def test_tool_metadata(self):
        """Given tool, has correct metadata"""
        tool = WorkflowTool()

        assert tool.name == "Workflow"
        assert "workflow" in tool.description.lower()
        assert len(tool.parameters) == 4

    def test_tool_parameters(self):
        """Given tool, has correct parameters"""
        tool = WorkflowTool()

        param_names = {p.name for p in tool.parameters}
        assert "operation" in param_names
        assert "query" in param_names
        assert "template_name" in param_names
        assert "workflow_id" in param_names

        # Check operation parameter
        op_param = next(p for p in tool.parameters if p.name == "operation")
        assert op_param.required
        assert op_param.enum == ["list", "search", "info", "run", "status"]

    @pytest.mark.asyncio
    async def test_list_operation(self, execution_context):
        """Given list operation, returns all templates"""
        tool = WorkflowTool()

        result = await tool._execute(execution_context, operation="list")

        assert result.success
        assert isinstance(result.output, dict)
        assert "count" in result.output
        assert "templates" in result.output
        assert result.output["count"] >= 7  # Built-in templates

    @pytest.mark.asyncio
    async def test_search_operation(self, execution_context):
        """Given search operation, returns matching templates"""
        tool = WorkflowTool()

        result = await tool._execute(
            execution_context, operation="search", query="security"
        )

        assert result.success
        assert isinstance(result.output, dict)
        assert result.output["query"] == "security"
        assert "templates" in result.output
        # Should find security-audit-full template
        template_names = [t["name"] for t in result.output["templates"]]
        assert "security-audit-full" in template_names

    @pytest.mark.asyncio
    async def test_search_operation_missing_query(self, execution_context):
        """Given search without query, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(execution_context, operation="search")

        assert not result.success
        assert "Query is required" in result.error

    @pytest.mark.asyncio
    async def test_info_operation(self, execution_context):
        """Given info operation, returns template details"""
        tool = WorkflowTool()

        result = await tool._execute(
            execution_context, operation="info", template_name="pr-review"
        )

        assert result.success
        assert isinstance(result.output, dict)
        assert result.output["name"] == "pr-review"
        assert "description" in result.output
        assert "steps" in result.output
        assert result.output["total_steps"] > 0

    @pytest.mark.asyncio
    async def test_info_operation_missing_template_name(self, execution_context):
        """Given info without template_name, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(execution_context, operation="info")

        assert not result.success
        assert "template_name is required" in result.error

    @pytest.mark.asyncio
    async def test_info_operation_nonexistent_template(self, execution_context):
        """Given info for non-existent template, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(
            execution_context, operation="info", template_name="nonexistent"
        )

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.tool.WorkflowExecutor")
    async def test_run_operation(
        self, mock_executor_class, execution_context, sample_workflow
    ):
        """Given run operation, executes workflow"""
        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        # Mock successful result
        now = datetime.now()
        mock_result = WorkflowResult(
            workflow_id="wf-123",
            workflow_name="test-workflow",
            success=True,
            steps_completed=2,
            steps_failed=0,
            steps_skipped=0,
            step_results={
                "step1": StepResult(
                    step_id="step1",
                    agent_type="general",
                    agent_result=None,
                    start_time=now,
                    end_time=now,
                    duration=0.0,
                    success=True,
                ),
                "step2": StepResult(
                    step_id="step2",
                    agent_type="general",
                    agent_result=None,
                    start_time=now,
                    end_time=now,
                    duration=0.0,
                    success=True,
                ),
            },
            duration=1.0,
            start_time=now,
            end_time=now,
        )
        mock_executor.execute = AsyncMock(return_value=mock_result)

        tool = WorkflowTool()
        result = await tool._execute(
            execution_context, operation="run", template_name="pr-review"
        )

        assert result.success
        assert isinstance(result.output, dict)
        assert result.output["workflow_id"] == "wf-123"
        assert result.output["success"]
        assert result.output["steps_completed"] == 2
        assert result.output["steps_total"] == 2

    @pytest.mark.asyncio
    async def test_run_operation_missing_template_name(self, execution_context):
        """Given run without template_name, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(execution_context, operation="run")

        assert not result.success
        assert "template_name is required" in result.error

    @pytest.mark.asyncio
    async def test_run_operation_nonexistent_template(self, execution_context):
        """Given run for non-existent template, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(
            execution_context, operation="run", template_name="nonexistent"
        )

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.tool.WorkflowExecutor")
    async def test_status_operation(
        self, mock_executor_class, execution_context, sample_workflow
    ):
        """Given status operation, returns workflow state"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        # Mock workflow state
        now = datetime.now()
        mock_state = WorkflowState(
            workflow_id="wf-123",
            definition=sample_workflow,
            status=WorkflowStatus.RUNNING,
            start_time=now,
            current_step="step2",
            step_results={
                "step1": StepResult(
                    step_id="step1",
                    agent_type="general",
                    agent_result=None,
                    start_time=now,
                    end_time=now,
                    duration=0.5,
                    success=True,
                ),
                "step2": StepResult(
                    step_id="step2",
                    agent_type="general",
                    agent_result=None,
                    start_time=now,
                    end_time=now,
                    duration=0.0,
                    success=False,
                ),
            },
        )
        mock_executor.get_workflow_state.return_value = mock_state

        tool = WorkflowTool()
        result = await tool._execute(
            execution_context, operation="status", workflow_id="wf-123"
        )

        assert result.success
        assert isinstance(result.output, dict)
        assert result.output["workflow_id"] == "wf-123"
        assert result.output["workflow_name"] == "test-workflow"
        assert result.output["status"] == "running"
        assert result.output["current_step"] == "step2"
        assert len(result.output["steps"]) == 2

    @pytest.mark.asyncio
    async def test_status_operation_missing_workflow_id(self, execution_context):
        """Given status without workflow_id, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(execution_context, operation="status")

        assert not result.success
        assert "workflow_id is required" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.tool.WorkflowExecutor")
    async def test_status_operation_nonexistent_workflow(
        self, mock_executor_class, execution_context
    ):
        """Given status for non-existent workflow, returns error"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.get_workflow_state.return_value = None

        tool = WorkflowTool()
        result = await tool._execute(
            execution_context, operation="status", workflow_id="wf-nonexistent"
        )

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_unknown_operation(self, execution_context):
        """Given unknown operation, returns error"""
        tool = WorkflowTool()

        result = await tool._execute(execution_context, operation="invalid")

        assert not result.success
        assert "Unknown operation" in result.error

    @pytest.mark.asyncio
    async def test_full_execute_with_validation(self, execution_context):
        """Given execute method, validates parameters"""
        tool = WorkflowTool()

        # Test with valid parameters
        result = await tool.execute(execution_context, operation="list")
        assert result.success

        # Test with invalid operation (should fail validation)
        result = await tool.execute(execution_context, operation="invalid")
        assert not result.success
        assert "Invalid value" in result.error

    def test_tool_schema_generation(self):
        """Given tool, generates correct schemas"""
        tool = WorkflowTool()

        # Test OpenAI schema
        openai_schema = tool.to_openai_schema()
        assert openai_schema["type"] == "function"
        assert openai_schema["function"]["name"] == "Workflow"
        assert "operation" in openai_schema["function"]["parameters"]["properties"]

        # Test Anthropic schema
        anthropic_schema = tool.to_anthropic_schema()
        assert anthropic_schema["name"] == "Workflow"
        assert "operation" in anthropic_schema["input_schema"]["properties"]
