"""Unit tests for workflow data models."""

from datetime import datetime, timedelta

import pytest

from code_forge.agents.result import AgentResult
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
)


class TestWorkflowStep:
    """Tests for WorkflowStep model."""

    def test_create_minimal_step(self):
        """Given minimal required fields, creates WorkflowStep"""
        step = WorkflowStep(
            id="step1",
            agent="test-agent",
            description="Test step",
        )

        assert step.id == "step1"
        assert step.agent == "test-agent"
        assert step.description == "Test step"
        assert step.inputs == {}
        assert step.depends_on == []
        assert step.parallel_with == []
        assert step.condition is None
        assert step.timeout is None
        assert step.max_retries == 0

    def test_create_full_step(self):
        """Given all fields, creates complete WorkflowStep"""
        step = WorkflowStep(
            id="step2",
            agent="plan",
            description="Planning step",
            inputs={"task": "analyze code"},
            depends_on=["step1"],
            parallel_with=["step3"],
            condition="step1.success",
            timeout=300,
            max_retries=2,
        )

        assert step.id == "step2"
        assert step.agent == "plan"
        assert step.inputs == {"task": "analyze code"}
        assert step.depends_on == ["step1"]
        assert step.parallel_with == ["step3"]
        assert step.condition == "step1.success"
        assert step.timeout == 300
        assert step.max_retries == 2

    def test_reject_empty_id(self):
        """Given empty step ID, raises ValueError"""
        with pytest.raises(ValueError, match="Step ID cannot be empty"):
            WorkflowStep(id="", agent="test", description="Test")

    def test_reject_empty_agent(self):
        """Given empty agent type, raises ValueError"""
        with pytest.raises(ValueError, match="Agent type cannot be empty"):
            WorkflowStep(id="step1", agent="", description="Test")

    def test_reject_negative_retries(self):
        """Given negative max_retries, raises ValueError"""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            WorkflowStep(
                id="step1",
                agent="test",
                description="Test",
                max_retries=-1,
            )

    def test_reject_zero_timeout(self):
        """Given zero timeout, raises ValueError"""
        with pytest.raises(ValueError, match="timeout must be positive"):
            WorkflowStep(
                id="step1",
                agent="test",
                description="Test",
                timeout=0,
            )

    def test_reject_negative_timeout(self):
        """Given negative timeout, raises ValueError"""
        with pytest.raises(ValueError, match="timeout must be positive"):
            WorkflowStep(
                id="step1",
                agent="test",
                description="Test",
                timeout=-10,
            )


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition model."""

    def test_create_minimal_definition(self):
        """Given minimal required fields, creates WorkflowDefinition"""
        step = WorkflowStep(id="step1", agent="test", description="Test")
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[step],
        )

        assert definition.name == "test-workflow"
        assert definition.description == "Test workflow"
        assert definition.version == "1.0.0"
        assert len(definition.steps) == 1
        assert definition.author is None
        assert definition.metadata == {}

    def test_create_full_definition(self):
        """Given all fields, creates complete WorkflowDefinition"""
        steps = [
            WorkflowStep(id="step1", agent="plan", description="Plan"),
            WorkflowStep(id="step2", agent="review", description="Review"),
        ]
        definition = WorkflowDefinition(
            name="pr-review",
            description="PR review workflow",
            version="1.0.0",
            author="test-author",
            steps=steps,
            metadata={"category": "review"},
        )

        assert definition.name == "pr-review"
        assert definition.author == "test-author"
        assert len(definition.steps) == 2
        assert definition.metadata == {"category": "review"}

    def test_reject_empty_name(self):
        """Given empty workflow name, raises ValueError"""
        step = WorkflowStep(id="step1", agent="test", description="Test")
        with pytest.raises(ValueError, match="Workflow name cannot be empty"):
            WorkflowDefinition(
                name="",
                description="Test",
                version="1.0.0",
                steps=[step],
            )

    def test_reject_no_steps(self):
        """Given empty steps list, raises ValueError"""
        with pytest.raises(ValueError, match="Workflow must have at least one step"):
            WorkflowDefinition(
                name="test",
                description="Test",
                version="1.0.0",
                steps=[],
            )

    def test_reject_empty_version(self):
        """Given empty version, raises ValueError"""
        step = WorkflowStep(id="step1", agent="test", description="Test")
        with pytest.raises(ValueError, match="Workflow version cannot be empty"):
            WorkflowDefinition(
                name="test",
                description="Test",
                version="",
                steps=[step],
            )

    def test_reject_duplicate_step_ids(self):
        """Given duplicate step IDs, raises ValueError"""
        steps = [
            WorkflowStep(id="step1", agent="test", description="Test 1"),
            WorkflowStep(id="step1", agent="test", description="Test 2"),
        ]
        with pytest.raises(ValueError, match="Step IDs must be unique"):
            WorkflowDefinition(
                name="test",
                description="Test",
                version="1.0.0",
                steps=steps,
            )


class TestStepResult:
    """Tests for StepResult model."""

    def test_create_successful_result(self):
        """Given successful step execution, creates StepResult"""
        start = datetime.now()
        end = start + timedelta(seconds=5)
        agent_result = AgentResult.ok("Test output")

        result = StepResult(
            step_id="step1",
            agent_type="test",
            agent_result=agent_result,
            start_time=start,
            end_time=end,
            duration=5.0,
            success=True,
        )

        assert result.step_id == "step1"
        assert result.agent_type == "test"
        assert result.success is True
        assert result.error is None
        assert result.skipped is False
        assert result.retry_count == 0

    def test_create_failed_result(self):
        """Given failed step execution, creates StepResult with error"""
        start = datetime.now()
        end = start + timedelta(seconds=2)
        agent_result = AgentResult.fail("Test error")

        result = StepResult(
            step_id="step2",
            agent_type="test",
            agent_result=agent_result,
            start_time=start,
            end_time=end,
            duration=2.0,
            success=False,
            error="Test error",
        )

        assert result.success is False
        assert result.error == "Test error"

    def test_create_skipped_result(self):
        """Given skipped step, creates StepResult with skipped flag"""
        start = datetime.now()
        end = start

        result = StepResult(
            step_id="step3",
            agent_type="test",
            agent_result=None,
            start_time=start,
            end_time=end,
            duration=0.0,
            success=True,
            skipped=True,
        )

        assert result.skipped is True
        assert result.agent_result is None


class TestWorkflowState:
    """Tests for WorkflowState model."""

    @pytest.fixture
    def workflow_definition(self):
        """Creates a test workflow definition."""
        steps = [
            WorkflowStep(id="step1", agent="plan", description="Plan"),
            WorkflowStep(id="step2", agent="review", description="Review"),
        ]
        return WorkflowDefinition(
            name="test-workflow",
            description="Test",
            version="1.0.0",
            steps=steps,
        )

    def test_create_initial_state(self, workflow_definition):
        """Given workflow definition, creates initial WorkflowState"""
        start = datetime.now()
        state = WorkflowState(
            workflow_id="wf_123",
            definition=workflow_definition,
            status=WorkflowStatus.PENDING,
            start_time=start,
        )

        assert state.workflow_id == "wf_123"
        assert state.status == WorkflowStatus.PENDING
        assert state.current_step is None
        assert state.completed_steps == []
        assert state.failed_steps == []
        assert state.skipped_steps == []
        assert state.step_results == {}
        assert state.end_time is None

    def test_mark_step_completed(self, workflow_definition):
        """Given completed step, updates state correctly"""
        state = WorkflowState(
            workflow_id="wf_123",
            definition=workflow_definition,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
        )

        result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=AgentResult.ok("Done"),
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            success=True,
        )

        state.mark_step_completed("step1", result)

        assert "step1" in state.completed_steps
        assert "step1" in state.step_results
        assert state.step_results["step1"] == result
        assert state.current_step is None

    def test_mark_step_failed(self, workflow_definition):
        """Given failed step, updates state correctly"""
        state = WorkflowState(
            workflow_id="wf_123",
            definition=workflow_definition,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
        )

        result = StepResult(
            step_id="step2",
            agent_type="review",
            agent_result=AgentResult.fail("Error"),
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            success=False,
            error="Error",
        )

        state.mark_step_failed("step2", result)

        assert "step2" in state.failed_steps
        assert "step2" not in state.completed_steps
        assert state.step_results["step2"] == result

    def test_mark_step_skipped(self, workflow_definition):
        """Given skipped step, updates state correctly"""
        state = WorkflowState(
            workflow_id="wf_123",
            definition=workflow_definition,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
        )

        result = StepResult(
            step_id="step2",
            agent_type="review",
            agent_result=None,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0.0,
            success=True,
            skipped=True,
        )

        state.mark_step_skipped("step2", result)

        assert "step2" in state.skipped_steps
        assert "step2" not in state.completed_steps
        assert "step2" not in state.failed_steps


class TestWorkflowResult:
    """Tests for WorkflowResult model."""

    @pytest.fixture
    def completed_state(self):
        """Creates a completed workflow state."""
        steps = [
            WorkflowStep(id="step1", agent="plan", description="Plan"),
            WorkflowStep(id="step2", agent="review", description="Review"),
        ]
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test",
            version="1.0.0",
            steps=steps,
        )

        start = datetime.now()
        end = start + timedelta(seconds=10)

        state = WorkflowState(
            workflow_id="wf_123",
            definition=definition,
            status=WorkflowStatus.COMPLETED,
            start_time=start,
            end_time=end,
        )

        # Add step results
        result1 = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=AgentResult.ok("Done"),
            start_time=start,
            end_time=start + timedelta(seconds=5),
            duration=5.0,
            success=True,
        )
        result2 = StepResult(
            step_id="step2",
            agent_type="review",
            agent_result=AgentResult.ok("Done"),
            start_time=start + timedelta(seconds=5),
            end_time=end,
            duration=5.0,
            success=True,
        )

        state.mark_step_completed("step1", result1)
        state.mark_step_completed("step2", result2)

        return state

    def test_create_from_completed_state(self, completed_state):
        """Given completed WorkflowState, creates WorkflowResult"""
        result = WorkflowResult.from_state(completed_state)

        assert result.workflow_id == "wf_123"
        assert result.workflow_name == "test-workflow"
        assert result.success is True
        assert result.steps_completed == 2
        assert result.steps_failed == 0
        assert result.steps_skipped == 0
        assert len(result.step_results) == 2
        assert result.duration == 10.0
        assert result.error is None

    def test_reject_incomplete_state(self):
        """Given incomplete workflow state, raises ValueError"""
        steps = [WorkflowStep(id="step1", agent="test", description="Test")]
        definition = WorkflowDefinition(
            name="test",
            description="Test",
            version="1.0.0",
            steps=steps,
        )

        state = WorkflowState(
            workflow_id="wf_456",
            definition=definition,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            end_time=None,  # Not complete
        )

        with pytest.raises(ValueError, match="Cannot create result from incomplete workflow"):
            WorkflowResult.from_state(state)

    def test_create_from_failed_state(self):
        """Given failed WorkflowState, creates WorkflowResult with success=False"""
        steps = [WorkflowStep(id="step1", agent="test", description="Test")]
        definition = WorkflowDefinition(
            name="test",
            description="Test",
            version="1.0.0",
            steps=steps,
        )

        start = datetime.now()
        end = start + timedelta(seconds=5)

        state = WorkflowState(
            workflow_id="wf_789",
            definition=definition,
            status=WorkflowStatus.FAILED,
            start_time=start,
            end_time=end,
        )

        result = WorkflowResult.from_state(state)

        assert result.success is False
        assert result.error == "Workflow failed"
