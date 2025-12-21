"""Unit tests for workflow state management."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from code_forge.agents.result import AgentResult
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStep,
)
from code_forge.workflows.state import (
    CheckpointCorruptedError,
    CheckpointManager,
    CheckpointNotFoundError,
    StateManager,
)


class TestStateManager:
    """Tests for StateManager class."""

    @pytest.fixture
    def definition(self):
        """Creates a simple workflow definition."""
        return WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Planning"),
                WorkflowStep(id="step2", agent="review", description="Review"),
            ],
        )

    @pytest.fixture
    def manager(self, definition):
        """Creates a state manager instance."""
        return StateManager("test-workflow-123", definition)

    def test_initialize_state_manager(self, manager, definition):
        """Given workflow ID and definition, initializes state manager"""
        assert manager.workflow_id == "test-workflow-123"
        assert manager.state.workflow_id == "test-workflow-123"
        assert manager.state.definition == definition
        assert manager.state.status == WorkflowStatus.PENDING
        assert manager.state.current_step is None
        assert manager.state.completed_steps == []
        assert manager.state.failed_steps == []
        assert manager.state.skipped_steps == []

    def test_start_workflow(self, manager):
        """Given state manager, starts workflow"""
        manager.start_workflow()

        assert manager.state.status == WorkflowStatus.RUNNING
        assert manager.state.start_time is not None

    def test_start_step(self, manager):
        """Given step ID, marks step as current"""
        manager.start_step("step1")

        assert manager.state.current_step == "step1"

    def test_complete_step_success(self, manager):
        """Given successful step result, records completion"""
        agent_result = AgentResult(
            success=True,
            output="Success",
            data={"result": "completed"},
        )
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.0,
            success=True,
            error=None,
        )

        manager.start_step("step1")
        manager.complete_step(step_result)

        assert "step1" in manager.state.completed_steps
        assert "step1" not in manager.state.failed_steps
        assert manager.state.current_step is None
        assert manager.state.step_results["step1"] == step_result

    def test_complete_step_failure(self, manager):
        """Given failed step result, records failure"""
        agent_result = AgentResult(
            success=False,
            output="Failed",
            error="Test error",
        )
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.0,
            success=False,
            error="Test error",
        )

        manager.start_step("step1")
        manager.complete_step(step_result)

        assert "step1" not in manager.state.completed_steps
        assert "step1" in manager.state.failed_steps
        assert manager.state.current_step is None
        assert manager.state.step_results["step1"] == step_result

    def test_skip_step(self, manager):
        """Given step ID, records skip"""
        manager.skip_step("step1", reason="Condition not met")

        assert "step1" in manager.state.skipped_steps
        assert "step1" not in manager.state.completed_steps
        assert "step1" not in manager.state.failed_steps

    def test_fail_workflow(self, manager):
        """Given error message, marks workflow as failed"""
        manager.start_workflow()
        manager.fail_workflow("Critical error")

        assert manager.state.status == WorkflowStatus.FAILED
        assert manager.state.end_time is not None

    def test_complete_workflow(self, manager):
        """Given completed workflow, marks as completed"""
        manager.start_workflow()
        manager.complete_workflow()

        assert manager.state.status == WorkflowStatus.COMPLETED
        assert manager.state.end_time is not None

    def test_pause_workflow(self, manager):
        """Given running workflow, pauses it"""
        manager.start_workflow()
        manager.pause_workflow()

        assert manager.state.status == WorkflowStatus.PAUSED

    def test_get_step_result(self, manager):
        """Given completed step, retrieves result"""
        agent_result = AgentResult(success=True, output="Done")
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.0,
            success=True,
            error=None,
        )

        manager.complete_step(step_result)
        retrieved = manager.get_step_result("step1")

        assert retrieved == step_result

    def test_get_step_result_nonexistent(self, manager):
        """Given nonexistent step ID, returns None"""
        result = manager.get_step_result("nonexistent")

        assert result is None

    def test_is_step_completed(self, manager):
        """Given completed step, returns True"""
        agent_result = AgentResult(success=True, output="Done")
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.0,
            success=True,
            error=None,
        )

        manager.complete_step(step_result)

        assert manager.is_step_completed("step1") is True
        assert manager.is_step_completed("step2") is False

    def test_is_step_failed(self, manager):
        """Given failed step, returns True"""
        agent_result = AgentResult(success=False, output="Failed", error="Error")
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.0,
            success=False,
            error="Error",
        )

        manager.complete_step(step_result)

        assert manager.is_step_failed("step1") is True
        assert manager.is_step_failed("step2") is False

    def test_get_evaluation_context(self, manager):
        """Given step results, builds evaluation context"""
        agent_result = AgentResult(
            success=True,
            output="Done",
            data={"count": 5, "status": "complete"},
        )
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.0,
            success=True,
            error=None,
        )

        manager.complete_step(step_result)
        context = manager.get_evaluation_context()

        assert "step1" in context
        assert context["step1"]["success"] is True
        assert context["step1"]["failed"] is False
        assert context["step1"]["result"]["count"] == 5
        assert context["step1"]["result"]["status"] == "complete"


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    @pytest.fixture
    def checkpoint_dir(self, tmp_path):
        """Creates temporary checkpoint directory."""
        return tmp_path / "checkpoints"

    @pytest.fixture
    def manager(self, checkpoint_dir):
        """Creates checkpoint manager instance."""
        return CheckpointManager(checkpoint_dir)

    @pytest.fixture
    def workflow_state(self):
        """Creates a workflow state for testing."""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            author="Test Author",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Planning"),
                WorkflowStep(
                    id="step2",
                    agent="review",
                    description="Review",
                    depends_on=["step1"],
                ),
            ],
            metadata={"category": "test"},
        )

        state_manager = StateManager("test-wf-123", definition)
        state_manager.start_workflow()

        # Add a completed step
        agent_result = AgentResult(
            success=True,
            output="Done",
            data={"result": "completed"},
        )
        step_result = StepResult(
            step_id="step1",
            agent_type="plan",
            agent_result=agent_result,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration=1.5,
            success=True,
            error=None,
        )
        state_manager.complete_step(step_result)

        return state_manager.state

    def test_initialize_checkpoint_manager(self, manager, checkpoint_dir):
        """Given checkpoint directory, initializes manager"""
        assert manager.checkpoint_dir == checkpoint_dir
        assert checkpoint_dir.exists()

    def test_get_checkpoint_path(self, manager):
        """Given workflow ID, returns checkpoint path"""
        path = manager.get_checkpoint_path("test-workflow-123")

        assert path.name == "test-workflow-123.checkpoint.json"
        assert path.parent == manager.checkpoint_dir

    def test_save_checkpoint(self, manager, workflow_state):
        """Given workflow state, saves checkpoint"""
        manager.save_checkpoint(workflow_state)

        checkpoint_path = manager.get_checkpoint_path(workflow_state.workflow_id)
        assert checkpoint_path.exists()

    def test_load_checkpoint(self, manager, workflow_state):
        """Given saved checkpoint, loads state"""
        # Save first
        manager.save_checkpoint(workflow_state)

        # Load
        loaded_state = manager.load_checkpoint(workflow_state.workflow_id)

        # Verify
        assert loaded_state.workflow_id == workflow_state.workflow_id
        assert loaded_state.definition.name == workflow_state.definition.name
        assert loaded_state.status == workflow_state.status
        assert loaded_state.completed_steps == workflow_state.completed_steps
        assert len(loaded_state.step_results) == len(workflow_state.step_results)

    def test_load_nonexistent_checkpoint(self, manager):
        """Given nonexistent checkpoint, raises CheckpointNotFoundError"""
        with pytest.raises(CheckpointNotFoundError):
            manager.load_checkpoint("nonexistent")

    def test_load_corrupted_checkpoint(self, manager, checkpoint_dir):
        """Given corrupted checkpoint file, raises CheckpointCorruptedError"""
        # Create corrupted file
        corrupted_path = checkpoint_dir / "corrupted.checkpoint.json"
        corrupted_path.write_text("{ invalid json }")

        with pytest.raises(CheckpointCorruptedError):
            manager.load_checkpoint("corrupted")

    def test_delete_checkpoint(self, manager, workflow_state):
        """Given saved checkpoint, deletes it"""
        # Save first
        manager.save_checkpoint(workflow_state)
        checkpoint_path = manager.get_checkpoint_path(workflow_state.workflow_id)
        assert checkpoint_path.exists()

        # Delete
        manager.delete_checkpoint(workflow_state.workflow_id)

        assert not checkpoint_path.exists()

    def test_delete_nonexistent_checkpoint(self, manager):
        """Given nonexistent checkpoint, delete succeeds silently"""
        # Should not raise
        manager.delete_checkpoint("nonexistent")

    def test_checkpoint_exists(self, manager, workflow_state):
        """Given checkpoint file, returns True"""
        assert manager.checkpoint_exists(workflow_state.workflow_id) is False

        manager.save_checkpoint(workflow_state)

        assert manager.checkpoint_exists(workflow_state.workflow_id) is True

    def test_list_checkpoints(self, manager, workflow_state):
        """Given multiple checkpoints, lists all workflow IDs"""
        # Create multiple checkpoints
        manager.save_checkpoint(workflow_state)

        # Create another state
        definition2 = WorkflowDefinition(
            name="workflow-2",
            description="Second workflow",
            version="1.0.0",
            steps=[WorkflowStep(id="step1", agent="test", description="Test")],
        )
        state_manager2 = StateManager("test-wf-456", definition2)
        manager.save_checkpoint(state_manager2.state)

        # List
        checkpoints = manager.list_checkpoints()

        assert len(checkpoints) == 2
        assert "test-wf-123" in checkpoints
        assert "test-wf-456" in checkpoints

    def test_checkpoint_preserves_all_fields(self, manager, workflow_state):
        """Given complex workflow state, preserves all fields on save/load"""
        # Add more complexity - manually add a skipped step
        workflow_state.skipped_steps.append("step2")

        # Save and load
        manager.save_checkpoint(workflow_state)
        loaded = manager.load_checkpoint(workflow_state.workflow_id)

        # Verify all fields
        assert loaded.workflow_id == workflow_state.workflow_id
        assert loaded.status == workflow_state.status
        assert loaded.current_step == workflow_state.current_step
        assert loaded.completed_steps == workflow_state.completed_steps
        assert loaded.failed_steps == workflow_state.failed_steps
        assert loaded.skipped_steps == workflow_state.skipped_steps
        assert loaded.start_time == workflow_state.start_time
        assert loaded.end_time == workflow_state.end_time

        # Verify definition
        assert loaded.definition.name == workflow_state.definition.name
        assert loaded.definition.version == workflow_state.definition.version
        assert loaded.definition.author == workflow_state.definition.author
        assert loaded.definition.metadata == workflow_state.definition.metadata
        assert len(loaded.definition.steps) == len(workflow_state.definition.steps)

    def test_checkpoint_serializes_step_results(self, manager, workflow_state):
        """Given step results, serializes and deserializes correctly"""
        manager.save_checkpoint(workflow_state)
        loaded = manager.load_checkpoint(workflow_state.workflow_id)

        assert "step1" in loaded.step_results
        step_result = loaded.step_results["step1"]

        assert step_result.step_id == "step1"
        assert step_result.agent_type == "plan"
        assert step_result.success is True
        assert step_result.error is None
        assert step_result.duration == 1.5
        assert step_result.agent_result.success is True
        assert step_result.agent_result.data["result"] == "completed"

    def test_get_default_dir(self):
        """Given no arguments, returns default checkpoint directory"""
        default_dir = CheckpointManager.get_default_dir()

        assert "forge" in str(default_dir)
        assert "workflows" in str(default_dir)
        assert "checkpoints" in str(default_dir)

    def test_get_project_dir(self, tmp_path):
        """Given project root, returns project checkpoint directory"""
        project_root = tmp_path / "my-project"
        project_dir = CheckpointManager.get_project_dir(project_root)

        assert project_dir == project_root / ".forge" / "workflows" / "checkpoints"
