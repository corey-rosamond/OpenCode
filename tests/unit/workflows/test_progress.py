"""Tests for workflow progress tracking."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from code_forge.workflows.progress import (
    StepProgress,
    StepStatus,
    WorkflowProgress,
    WorkflowProgressTracker,
)


class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_values(self) -> None:
        """Test status values."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"


class TestStepProgress:
    """Tests for StepProgress dataclass."""

    def test_creation(self) -> None:
        """Test step progress creation."""
        step = StepProgress(step_id="step1", step_name="First Step")
        assert step.step_id == "step1"
        assert step.step_name == "First Step"
        assert step.status == StepStatus.PENDING

    def test_duration_not_started(self) -> None:
        """Test duration when not started."""
        step = StepProgress(step_id="step1", step_name="Test")
        assert step.duration_seconds is None

    def test_duration_running(self) -> None:
        """Test duration while running."""
        step = StepProgress(
            step_id="step1",
            step_name="Test",
            started_at=datetime.now() - timedelta(seconds=5),
        )
        duration = step.duration_seconds
        assert duration is not None
        assert duration >= 5

    def test_duration_completed(self) -> None:
        """Test duration when completed."""
        start = datetime.now() - timedelta(seconds=10)
        end = datetime.now() - timedelta(seconds=5)
        step = StepProgress(
            step_id="step1",
            step_name="Test",
            started_at=start,
            completed_at=end,
        )
        duration = step.duration_seconds
        assert duration is not None
        assert 4.5 <= duration <= 5.5

    def test_is_done_pending(self) -> None:
        """Test is_done for pending step."""
        step = StepProgress(step_id="step1", step_name="Test")
        assert not step.is_done

    def test_is_done_running(self) -> None:
        """Test is_done for running step."""
        step = StepProgress(
            step_id="step1",
            step_name="Test",
            status=StepStatus.RUNNING,
        )
        assert not step.is_done

    def test_is_done_completed(self) -> None:
        """Test is_done for completed step."""
        step = StepProgress(
            step_id="step1",
            step_name="Test",
            status=StepStatus.COMPLETED,
        )
        assert step.is_done

    def test_is_done_failed(self) -> None:
        """Test is_done for failed step."""
        step = StepProgress(
            step_id="step1",
            step_name="Test",
            status=StepStatus.FAILED,
        )
        assert step.is_done


class TestWorkflowProgress:
    """Tests for WorkflowProgress dataclass."""

    def test_creation(self) -> None:
        """Test workflow progress creation."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test Workflow",
            total_steps=3,
        )
        assert progress.workflow_id == "wf1"
        assert progress.workflow_name == "Test Workflow"
        assert progress.total_steps == 3

    def test_completed_steps_count(self) -> None:
        """Test counting completed steps."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=3,
            steps={
                "s1": StepProgress("s1", "Step 1", status=StepStatus.COMPLETED),
                "s2": StepProgress("s2", "Step 2", status=StepStatus.COMPLETED),
                "s3": StepProgress("s3", "Step 3", status=StepStatus.PENDING),
            },
        )
        assert progress.completed_steps == 2

    def test_failed_steps_count(self) -> None:
        """Test counting failed steps."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=3,
            steps={
                "s1": StepProgress("s1", "Step 1", status=StepStatus.COMPLETED),
                "s2": StepProgress("s2", "Step 2", status=StepStatus.FAILED),
                "s3": StepProgress("s3", "Step 3", status=StepStatus.FAILED),
            },
        )
        assert progress.failed_steps == 2

    def test_progress_percent(self) -> None:
        """Test progress percentage calculation."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=4,
            steps={
                "s1": StepProgress("s1", "Step 1", status=StepStatus.COMPLETED),
                "s2": StepProgress("s2", "Step 2", status=StepStatus.COMPLETED),
                "s3": StepProgress("s3", "Step 3", status=StepStatus.RUNNING),
                "s4": StepProgress("s4", "Step 4", status=StepStatus.PENDING),
            },
        )
        assert progress.progress_percent == 50.0

    def test_progress_percent_empty(self) -> None:
        """Test progress percentage with no steps."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=0,
        )
        assert progress.progress_percent == 100.0

    def test_current_step(self) -> None:
        """Test getting current running step."""
        step2 = StepProgress("s2", "Step 2", status=StepStatus.RUNNING)
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=3,
            steps={
                "s1": StepProgress("s1", "Step 1", status=StepStatus.COMPLETED),
                "s2": step2,
                "s3": StepProgress("s3", "Step 3", status=StepStatus.PENDING),
            },
        )
        assert progress.current_step == step2

    def test_current_step_none(self) -> None:
        """Test current step when none running."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=2,
            steps={
                "s1": StepProgress("s1", "Step 1", status=StepStatus.COMPLETED),
                "s2": StepProgress("s2", "Step 2", status=StepStatus.PENDING),
            },
        )
        assert progress.current_step is None

    def test_is_complete(self) -> None:
        """Test workflow completion check."""
        progress = WorkflowProgress(
            workflow_id="wf1",
            workflow_name="Test",
            total_steps=1,
            status=StepStatus.COMPLETED,
        )
        assert progress.is_complete

        progress.status = StepStatus.FAILED
        assert progress.is_complete

        progress.status = StepStatus.RUNNING
        assert not progress.is_complete


class TestWorkflowProgressTracker:
    """Tests for WorkflowProgressTracker."""

    @pytest.fixture
    def tracker(self) -> WorkflowProgressTracker:
        """Create a tracker instance."""
        return WorkflowProgressTracker()

    def test_start_workflow(self, tracker: WorkflowProgressTracker) -> None:
        """Test starting workflow tracking."""
        progress = tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test Workflow",
            step_ids=["s1", "s2", "s3"],
            step_names=["Step 1", "Step 2", "Step 3"],
        )
        assert progress.workflow_id == "wf1"
        assert progress.total_steps == 3
        assert len(progress.steps) == 3
        assert progress.status == StepStatus.RUNNING

    def test_start_step(self, tracker: WorkflowProgressTracker) -> None:
        """Test marking step as started."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1"],
        )
        tracker.start_step("s1", message="Starting...")

        progress = tracker.progress
        assert progress is not None
        assert progress.steps["s1"].status == StepStatus.RUNNING
        assert progress.steps["s1"].message == "Starting..."

    def test_update_step(self, tracker: WorkflowProgressTracker) -> None:
        """Test updating step message."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1"],
        )
        tracker.start_step("s1")
        tracker.update_step("s1", "Processing 50%...")

        progress = tracker.progress
        assert progress is not None
        assert progress.steps["s1"].message == "Processing 50%..."

    def test_complete_step(self, tracker: WorkflowProgressTracker) -> None:
        """Test completing a step."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1", "s2"],
        )
        tracker.start_step("s1")
        tracker.complete_step("s1", output={"result": "success"})

        progress = tracker.progress
        assert progress is not None
        assert progress.steps["s1"].status == StepStatus.COMPLETED
        assert progress.steps["s1"].output == {"result": "success"}

    def test_fail_step(self, tracker: WorkflowProgressTracker) -> None:
        """Test failing a step."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1"],
        )
        tracker.start_step("s1")
        tracker.fail_step("s1", error="Something went wrong")

        progress = tracker.progress
        assert progress is not None
        assert progress.steps["s1"].status == StepStatus.FAILED
        assert progress.steps["s1"].error == "Something went wrong"

    def test_skip_step(self, tracker: WorkflowProgressTracker) -> None:
        """Test skipping a step."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1"],
        )
        tracker.skip_step("s1", reason="Condition not met")

        progress = tracker.progress
        assert progress is not None
        assert progress.steps["s1"].status == StepStatus.SKIPPED
        assert "Condition not met" in progress.steps["s1"].message

    def test_workflow_auto_complete(self, tracker: WorkflowProgressTracker) -> None:
        """Test workflow auto-completes when all steps done."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1", "s2"],
        )
        tracker.start_step("s1")
        tracker.complete_step("s1")
        tracker.start_step("s2")
        tracker.complete_step("s2")

        progress = tracker.progress
        assert progress is not None
        assert progress.status == StepStatus.COMPLETED

    def test_workflow_fails_on_step_failure(self, tracker: WorkflowProgressTracker) -> None:
        """Test workflow marked failed when step fails."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test",
            step_ids=["s1"],
        )
        tracker.start_step("s1")
        tracker.fail_step("s1", error="Error")

        progress = tracker.progress
        assert progress is not None
        assert progress.status == StepStatus.FAILED

    def test_observer_notifications(self, tracker: WorkflowProgressTracker) -> None:
        """Test observer receives notifications."""
        events: list[str] = []

        class MockObserver:
            def on_workflow_started(self, progress: WorkflowProgress) -> None:
                events.append("started")

            def on_step_started(self, progress: WorkflowProgress, step: StepProgress) -> None:
                events.append(f"step_started:{step.step_id}")

            def on_step_completed(self, progress: WorkflowProgress, step: StepProgress) -> None:
                events.append(f"step_completed:{step.step_id}")

            def on_step_failed(self, progress: WorkflowProgress, step: StepProgress) -> None:
                events.append(f"step_failed:{step.step_id}")

            def on_workflow_completed(self, progress: WorkflowProgress) -> None:
                events.append("completed")

        tracker.add_observer(MockObserver())

        tracker.start_workflow("wf1", "Test", ["s1"])
        tracker.start_step("s1")
        tracker.complete_step("s1")

        assert "started" in events
        assert "step_started:s1" in events
        assert "step_completed:s1" in events
        assert "completed" in events

    def test_callback_registration(self, tracker: WorkflowProgressTracker) -> None:
        """Test callback registration and invocation."""
        called = []

        def on_start(p: WorkflowProgress) -> None:
            called.append("start")

        def on_complete(p: WorkflowProgress) -> None:
            called.append("complete")

        tracker.on("started", on_start)
        tracker.on("completed", on_complete)

        tracker.start_workflow("wf1", "Test", ["s1"])
        tracker.complete_step("s1")

        assert "start" in called
        assert "complete" in called

    def test_get_summary(self, tracker: WorkflowProgressTracker) -> None:
        """Test progress summary generation."""
        tracker.start_workflow(
            workflow_id="wf1",
            workflow_name="Test Workflow",
            step_ids=["s1", "s2"],
        )
        tracker.start_step("s1")
        tracker.complete_step("s1")
        tracker.start_step("s2")

        summary = tracker.get_summary()
        assert "Test Workflow" in summary
        assert "wf1" in summary
        assert "1/2" in summary or "50" in summary

    def test_get_summary_no_workflow(self, tracker: WorkflowProgressTracker) -> None:
        """Test summary when no workflow running."""
        summary = tracker.get_summary()
        assert "No workflow" in summary

    def test_remove_observer(self, tracker: WorkflowProgressTracker) -> None:
        """Test removing an observer."""
        calls = []

        class MockObserver:
            def on_workflow_started(self, progress: WorkflowProgress) -> None:
                calls.append("started")

        observer = MockObserver()
        tracker.add_observer(observer)
        tracker.remove_observer(observer)

        tracker.start_workflow("wf1", "Test", ["s1"])
        assert len(calls) == 0
