"""Tests for workflow rollback."""

from __future__ import annotations

import pytest

from code_forge.workflows.rollback import (
    WorkflowCheckpoint,
    WorkflowRollback,
    WorkflowRollbackState,
)


class TestWorkflowCheckpoint:
    """Tests for WorkflowCheckpoint dataclass."""

    def test_creation(self) -> None:
        """Test checkpoint creation."""
        checkpoint = WorkflowCheckpoint(
            step_id="step1",
            step_name="First Step",
            undo_ids=["undo1", "undo2"],
        )
        assert checkpoint.step_id == "step1"
        assert checkpoint.step_name == "First Step"
        assert len(checkpoint.undo_ids) == 2

    def test_default_values(self) -> None:
        """Test default values."""
        checkpoint = WorkflowCheckpoint(step_id="s1", step_name="Step")
        assert checkpoint.undo_ids == []
        assert checkpoint.metadata == {}
        assert checkpoint.timestamp is not None


class TestWorkflowRollbackState:
    """Tests for WorkflowRollbackState dataclass."""

    def test_creation(self) -> None:
        """Test state creation."""
        state = WorkflowRollbackState(
            workflow_id="wf1",
            workflow_name="Test Workflow",
        )
        assert state.workflow_id == "wf1"
        assert state.workflow_name == "Test Workflow"
        assert state.can_rollback is True

    def test_total_undos(self) -> None:
        """Test total undo count."""
        state = WorkflowRollbackState(
            workflow_id="wf1",
            workflow_name="Test",
            checkpoints=[
                WorkflowCheckpoint("s1", "Step 1", undo_ids=["u1", "u2"]),
                WorkflowCheckpoint("s2", "Step 2", undo_ids=["u3"]),
            ],
        )
        assert state.total_undos == 3

    def test_step_count(self) -> None:
        """Test step count."""
        state = WorkflowRollbackState(
            workflow_id="wf1",
            workflow_name="Test",
            checkpoints=[
                WorkflowCheckpoint("s1", "Step 1"),
                WorkflowCheckpoint("s2", "Step 2"),
                WorkflowCheckpoint("s3", "Step 3"),
            ],
        )
        assert state.step_count == 3


class TestWorkflowRollback:
    """Tests for WorkflowRollback."""

    @pytest.fixture
    def rollback(self) -> WorkflowRollback:
        """Create a rollback instance without undo manager."""
        return WorkflowRollback()

    @pytest.fixture
    def mock_undo_manager(self):
        """Create a mock undo manager."""
        class MockUndoManager:
            def __init__(self):
                self.undo_count = 0
                self.can_undo_value = True

            def undo(self) -> bool:
                if self.can_undo_value:
                    self.undo_count += 1
                    return True
                return False

            def can_undo(self) -> bool:
                return self.can_undo_value

        return MockUndoManager()

    def test_start_workflow(self, rollback: WorkflowRollback) -> None:
        """Test starting workflow tracking."""
        state = rollback.start_workflow("wf1", "Test Workflow")
        assert state.workflow_id == "wf1"
        assert state.workflow_name == "Test Workflow"
        assert rollback.active_workflow == state

    def test_checkpoint(self, rollback: WorkflowRollback) -> None:
        """Test creating checkpoints."""
        rollback.start_workflow("wf1", "Test")
        checkpoint = rollback.checkpoint(
            step_id="s1",
            step_name="Step 1",
            undo_ids=["u1", "u2"],
        )
        assert checkpoint.step_id == "s1"
        assert len(checkpoint.undo_ids) == 2

        state = rollback.active_workflow
        assert state is not None
        assert len(state.checkpoints) == 1

    def test_checkpoint_no_workflow_raises(self, rollback: WorkflowRollback) -> None:
        """Test checkpoint without workflow raises error."""
        with pytest.raises(RuntimeError, match="No active workflow"):
            rollback.checkpoint("s1", "Step")

    def test_can_rollback(self, rollback: WorkflowRollback) -> None:
        """Test can_rollback property."""
        assert not rollback.can_rollback

        rollback.start_workflow("wf1", "Test")
        assert not rollback.can_rollback  # No undo IDs yet

        rollback.checkpoint("s1", "Step", undo_ids=["u1"])
        assert rollback.can_rollback

    def test_get_all_undo_ids(self, rollback: WorkflowRollback) -> None:
        """Test getting all undo IDs."""
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1", undo_ids=["u1", "u2"])
        rollback.checkpoint("s2", "Step 2", undo_ids=["u3"])

        undo_ids = rollback.get_all_undo_ids()
        assert len(undo_ids) == 3
        # Should be in reverse order (newest first)
        assert undo_ids == ["u3", "u2", "u1"]

    def test_get_undo_ids_since_step(self, rollback: WorkflowRollback) -> None:
        """Test getting undo IDs since a step."""
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1", undo_ids=["u1"])
        rollback.checkpoint("s2", "Step 2", undo_ids=["u2"])
        rollback.checkpoint("s3", "Step 3", undo_ids=["u3"])

        # IDs after step 1
        undo_ids = rollback.get_undo_ids_since_step("s1")
        assert "u2" in undo_ids
        assert "u3" in undo_ids
        assert "u1" not in undo_ids

    def test_rollback_step(self, mock_undo_manager) -> None:
        """Test rolling back a single step."""
        rollback = WorkflowRollback(undo_manager=mock_undo_manager)
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1", undo_ids=["u1", "u2"])
        rollback.checkpoint("s2", "Step 2", undo_ids=["u3"])

        count = rollback.rollback_step("s1")
        assert count == 2
        assert mock_undo_manager.undo_count == 2

        # Step checkpoint should be removed
        state = rollback.active_workflow
        assert state is not None
        assert len(state.checkpoints) == 1

    def test_rollback_to_step(self, mock_undo_manager) -> None:
        """Test rolling back to a step."""
        rollback = WorkflowRollback(undo_manager=mock_undo_manager)
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1", undo_ids=["u1"])
        rollback.checkpoint("s2", "Step 2", undo_ids=["u2"])
        rollback.checkpoint("s3", "Step 3", undo_ids=["u3"])

        count = rollback.rollback_to_step("s1")
        assert count == 2  # u2 and u3

        state = rollback.active_workflow
        assert state is not None
        assert len(state.checkpoints) == 1
        assert state.checkpoints[0].step_id == "s1"

    def test_rollback_workflow(self, mock_undo_manager) -> None:
        """Test rolling back entire workflow."""
        rollback = WorkflowRollback(undo_manager=mock_undo_manager)
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1", undo_ids=["u1"])
        rollback.checkpoint("s2", "Step 2", undo_ids=["u2", "u3"])

        count = rollback.rollback_workflow()
        assert count == 3

        state = rollback.active_workflow
        assert state is not None
        assert len(state.checkpoints) == 0
        assert not state.can_rollback

    def test_rollback_no_undo_manager_raises(self, rollback: WorkflowRollback) -> None:
        """Test rollback without undo manager raises error."""
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step", undo_ids=["u1"])

        with pytest.raises(RuntimeError, match="No undo manager"):
            rollback.rollback_step("s1")

    def test_complete_workflow(self, rollback: WorkflowRollback) -> None:
        """Test completing a workflow."""
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1")

        rollback.complete_workflow(success=True)
        assert rollback.active_workflow is None

    def test_discard_workflow(self, rollback: WorkflowRollback) -> None:
        """Test discarding a workflow."""
        rollback.start_workflow("wf1", "Test")
        rollback.checkpoint("s1", "Step 1")

        rollback.discard_workflow()
        assert rollback.active_workflow is None

    def test_get_rollback_summary(self, rollback: WorkflowRollback) -> None:
        """Test rollback summary generation."""
        rollback.start_workflow("wf1", "Test Workflow")
        rollback.checkpoint("s1", "Step 1", undo_ids=["u1"])
        rollback.checkpoint("s2", "Step 2", undo_ids=["u2", "u3"])

        summary = rollback.get_rollback_summary()
        assert "Test Workflow" in summary
        assert "wf1" in summary
        assert "Steps: 2" in summary
        assert "3" in summary  # Total undos
        assert "Step 1" in summary
        assert "Step 2" in summary

    def test_get_rollback_summary_no_workflow(self, rollback: WorkflowRollback) -> None:
        """Test summary when no workflow."""
        summary = rollback.get_rollback_summary()
        assert "No active workflow" in summary

    def test_workflow_history(self, rollback: WorkflowRollback) -> None:
        """Test workflow history tracking."""
        rollback.start_workflow("wf1", "First")
        rollback.complete_workflow()

        rollback.start_workflow("wf2", "Second")
        rollback.complete_workflow()

        # History should have both
        assert len(rollback._history) == 2

    def test_workflow_history_limit(self, rollback: WorkflowRollback) -> None:
        """Test workflow history limit."""
        rollback._max_history = 3

        for i in range(5):
            rollback.start_workflow(f"wf{i}", f"Workflow {i}")
            rollback.complete_workflow()

        assert len(rollback._history) == 3

    def test_new_workflow_archives_previous(self, rollback: WorkflowRollback) -> None:
        """Test starting new workflow archives previous."""
        rollback.start_workflow("wf1", "First")
        rollback.checkpoint("s1", "Step")

        rollback.start_workflow("wf2", "Second")

        assert rollback.active_workflow is not None
        assert rollback.active_workflow.workflow_id == "wf2"
        assert len(rollback._history) == 1
        assert rollback._history[0].workflow_id == "wf1"
