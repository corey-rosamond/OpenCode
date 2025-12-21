"""Unit tests for workflow commands."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.commands.executor import CommandContext
from code_forge.commands.parser import ParsedCommand
from code_forge.workflows.commands import (
    WorkflowCancelCommand,
    WorkflowCommand,
    WorkflowListCommand,
    WorkflowResumeCommand,
    WorkflowRunCommand,
    WorkflowStatusCommand,
)
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
)


@pytest.fixture
def command_context():
    """Create a command context for testing."""
    return CommandContext()


@pytest.fixture
def sample_workflow():
    """Create a sample workflow definition."""
    return WorkflowDefinition(
        name="test-workflow",
        description="Test workflow",
        version="1.0.0",
        steps=[
            WorkflowStep(id="step1", agent="general", description="Step 1"),
            WorkflowStep(id="step2", agent="general", description="Step 2"),
        ],
    )


class TestWorkflowListCommand:
    """Tests for WorkflowListCommand."""

    @pytest.mark.asyncio
    async def test_list_all_templates(self, command_context):
        """Given no query, lists all templates"""
        cmd = WorkflowListCommand()
        parsed = ParsedCommand(
            name="workflow-list",
            args=[],
            raw="workflow-list",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "Available workflow templates:" in result.output
        assert "pr-review" in result.output

    @pytest.mark.asyncio
    async def test_list_with_search_query(self, command_context):
        """Given search query, lists matching templates"""
        cmd = WorkflowListCommand()
        parsed = ParsedCommand(
            name="workflow-list",
            args=["security"],
            raw="workflow-list security",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "matching 'security'" in result.output
        assert "security-audit-full" in result.output

    @pytest.mark.asyncio
    async def test_list_no_matches(self, command_context):
        """Given query with no matches, returns appropriate message"""
        cmd = WorkflowListCommand()
        parsed = ParsedCommand(
            name="workflow-list",
            args=["nonexistent"],
            raw="workflow-list nonexistent",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "No workflow templates found" in result.output


class TestWorkflowRunCommand:
    """Tests for WorkflowRunCommand."""

    @pytest.mark.asyncio
    async def test_run_missing_template_name(self, command_context):
        """Given no template name, returns error"""
        cmd = WorkflowRunCommand()
        parsed = ParsedCommand(
            name="workflow-run",
            args=[],
            raw="workflow-run",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Template name is required" in result.error

    @pytest.mark.asyncio
    async def test_run_nonexistent_template(self, command_context):
        """Given non-existent template, returns error"""
        cmd = WorkflowRunCommand()
        parsed = ParsedCommand(
            name="workflow-run",
            args=["nonexistent"],
            raw="workflow-run nonexistent",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_run_successful_workflow(
        self, mock_executor_class, command_context, sample_workflow
    ):
        """Given valid template, runs workflow successfully"""
        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        # Mock successful result
        now = datetime.now()
        mock_result = WorkflowResult(
            workflow_id="wf-123",
            workflow_name="pr-review",
            success=True,
            steps_completed=5,
            steps_failed=0,
            steps_skipped=0,
            step_results={},
            duration=60.0,
            start_time=now,
            end_time=now,
        )
        mock_executor.execute = AsyncMock(return_value=mock_result)

        cmd = WorkflowRunCommand()
        parsed = ParsedCommand(
            name="workflow-run",
            args=["pr-review"],
            raw="workflow-run pr-review",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "completed successfully" in result.output
        assert "wf-123" in result.output


class TestWorkflowStatusCommand:
    """Tests for WorkflowStatusCommand."""

    @pytest.mark.asyncio
    async def test_status_missing_workflow_id(self, command_context):
        """Given no workflow ID, returns error"""
        cmd = WorkflowStatusCommand()
        parsed = ParsedCommand(
            name="workflow-status",
            args=[],
            raw="workflow-status",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Workflow ID is required" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_status_nonexistent_workflow(
        self, mock_executor_class, command_context
    ):
        """Given non-existent workflow ID, returns error"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.get_workflow_state.return_value = None

        cmd = WorkflowStatusCommand()
        parsed = ParsedCommand(
            name="workflow-status",
            args=["wf-nonexistent"],
            raw="workflow-status wf-nonexistent",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_status_running_workflow(
        self, mock_executor_class, command_context, sample_workflow
    ):
        """Given running workflow, returns status"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        # Mock workflow state
        now = datetime.now()
        mock_state = WorkflowState(
            workflow_id="wf-123",
            definition=sample_workflow,
            status=WorkflowStatus.RUNNING,
            start_time=now,
            current_step="step1",
            step_results={
                "step1": StepResult(
                    step_id="step1",
                    agent_type="general",
                    agent_result=None,
                    start_time=now,
                    end_time=now,
                    duration=0.0,
                    success=False,
                )
            },
        )
        mock_executor.get_workflow_state.return_value = mock_state

        cmd = WorkflowStatusCommand()
        parsed = ParsedCommand(
            name="workflow-status",
            args=["wf-123"],
            raw="workflow-status wf-123",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "test-workflow" in result.output
        assert "running" in result.output.lower()
        assert "Current step: step1" in result.output


class TestWorkflowResumeCommand:
    """Tests for WorkflowResumeCommand."""

    @pytest.mark.asyncio
    async def test_resume_missing_workflow_id(self, command_context):
        """Given no workflow ID, returns error"""
        cmd = WorkflowResumeCommand()
        parsed = ParsedCommand(
            name="workflow-resume",
            args=[],
            raw="workflow-resume",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Workflow ID is required" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_resume_nonexistent_workflow(
        self, mock_executor_class, command_context
    ):
        """Given non-existent workflow, returns error"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.get_workflow_state.return_value = None

        cmd = WorkflowResumeCommand()
        parsed = ParsedCommand(
            name="workflow-resume",
            args=["wf-123"],
            raw="workflow-resume wf-123",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_resume_invalid_status(
        self, mock_executor_class, command_context, sample_workflow
    ):
        """Given workflow with invalid status, returns error"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        mock_state = WorkflowState(
            workflow_id="wf-123",
            definition=sample_workflow,
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
        )
        mock_executor.get_workflow_state.return_value = mock_state

        cmd = WorkflowResumeCommand()
        parsed = ParsedCommand(
            name="workflow-resume",
            args=["wf-123"],
            raw="workflow-resume wf-123",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Cannot resume" in result.error


class TestWorkflowCancelCommand:
    """Tests for WorkflowCancelCommand."""

    @pytest.mark.asyncio
    async def test_cancel_missing_workflow_id(self, command_context):
        """Given no workflow ID, returns error"""
        cmd = WorkflowCancelCommand()
        parsed = ParsedCommand(
            name="workflow-cancel",
            args=[],
            raw="workflow-cancel",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Workflow ID is required" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_cancel_nonexistent_workflow(
        self, mock_executor_class, command_context
    ):
        """Given non-existent workflow, returns error"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.get_workflow_state.return_value = None

        cmd = WorkflowCancelCommand()
        parsed = ParsedCommand(
            name="workflow-cancel",
            args=["wf-123"],
            raw="workflow-cancel wf-123",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    @patch("code_forge.workflows.commands.WorkflowExecutor")
    async def test_cancel_successful(
        self, mock_executor_class, command_context, sample_workflow
    ):
        """Given running workflow, cancels successfully"""
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        mock_state = WorkflowState(
            workflow_id="wf-123",
            definition=sample_workflow,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
        )
        mock_executor.get_workflow_state.return_value = mock_state
        mock_executor.cancel = AsyncMock(return_value=True)

        cmd = WorkflowCancelCommand()
        parsed = ParsedCommand(
            name="workflow-cancel",
            args=["wf-123"],
            raw="workflow-cancel wf-123",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "cancelled" in result.output


class TestWorkflowCommand:
    """Tests for main WorkflowCommand with subcommands."""

    @pytest.mark.asyncio
    async def test_missing_subcommand(self, command_context):
        """Given no subcommand, returns error"""
        cmd = WorkflowCommand()
        parsed = ParsedCommand(
            name="workflow",
            args=[],
            raw="workflow",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Subcommand required" in result.error

    @pytest.mark.asyncio
    async def test_unknown_subcommand(self, command_context):
        """Given unknown subcommand, returns error"""
        cmd = WorkflowCommand()
        parsed = ParsedCommand(
            name="workflow",
            args=["unknown"],
            raw="workflow unknown",
        )

        result = await cmd.execute(parsed, command_context)

        assert not result.success
        assert "Unknown subcommand" in result.error

    @pytest.mark.asyncio
    async def test_delegates_to_list_subcommand(self, command_context):
        """Given 'list' subcommand, delegates to WorkflowListCommand"""
        cmd = WorkflowCommand()
        parsed = ParsedCommand(
            name="workflow",
            args=["list"],
            raw="workflow list",
        )

        result = await cmd.execute(parsed, command_context)

        assert result.success
        assert "workflow templates" in result.output.lower()
