"""Workflow progress tracking.

This module provides real-time progress tracking for multi-step
workflow execution with status updates and event notifications.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Protocol


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepProgress:
    """Progress information for a single step.

    Attributes:
        step_id: Unique identifier for the step.
        step_name: Human-readable step name.
        status: Current step status.
        started_at: When the step started.
        completed_at: When the step completed.
        message: Current status message.
        error: Error message if failed.
        output: Step output data.
    """

    step_id: str
    step_name: str
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str = ""
    error: str = ""
    output: Any = None

    @property
    def duration_seconds(self) -> float | None:
        """Get step duration in seconds."""
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def is_done(self) -> bool:
        """Check if step is in a terminal state."""
        return self.status in (
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
        )


@dataclass
class WorkflowProgress:
    """Overall workflow progress.

    Attributes:
        workflow_id: Unique workflow execution ID.
        workflow_name: Name of the workflow.
        total_steps: Total number of steps.
        steps: Progress for each step.
        started_at: When the workflow started.
        completed_at: When the workflow completed.
        status: Overall workflow status.
    """

    workflow_id: str
    workflow_name: str
    total_steps: int
    steps: dict[str, StepProgress] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: StepStatus = StepStatus.PENDING

    @property
    def completed_steps(self) -> int:
        """Count of completed steps."""
        return sum(
            1 for s in self.steps.values()
            if s.status == StepStatus.COMPLETED
        )

    @property
    def failed_steps(self) -> int:
        """Count of failed steps."""
        return sum(
            1 for s in self.steps.values()
            if s.status == StepStatus.FAILED
        )

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage (0-100)."""
        if self.total_steps == 0:
            return 100.0
        done = sum(1 for s in self.steps.values() if s.is_done)
        return (done / self.total_steps) * 100

    @property
    def duration_seconds(self) -> float | None:
        """Get workflow duration in seconds."""
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def current_step(self) -> StepProgress | None:
        """Get the currently running step."""
        for step in self.steps.values():
            if step.status == StepStatus.RUNNING:
                return step
        return None

    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.status in (
            StepStatus.COMPLETED,
            StepStatus.FAILED,
        )


class ProgressObserver(Protocol):
    """Protocol for progress observers."""

    def on_workflow_started(self, progress: WorkflowProgress) -> None:
        """Called when workflow starts."""
        ...

    def on_step_started(self, progress: WorkflowProgress, step: StepProgress) -> None:
        """Called when a step starts."""
        ...

    def on_step_completed(self, progress: WorkflowProgress, step: StepProgress) -> None:
        """Called when a step completes."""
        ...

    def on_step_failed(self, progress: WorkflowProgress, step: StepProgress) -> None:
        """Called when a step fails."""
        ...

    def on_workflow_completed(self, progress: WorkflowProgress) -> None:
        """Called when workflow completes."""
        ...


class WorkflowProgressTracker:
    """Tracks and reports workflow progress.

    Thread-safe tracker that manages progress state and notifies
    observers of progress updates.
    """

    def __init__(self) -> None:
        """Initialize the tracker."""
        self._progress: WorkflowProgress | None = None
        self._observers: list[ProgressObserver] = []
        self._callbacks: dict[str, list[Callable[[WorkflowProgress], None]]] = {
            "started": [],
            "step_started": [],
            "step_completed": [],
            "step_failed": [],
            "completed": [],
            "update": [],
        }
        self._lock = threading.RLock()

    @property
    def progress(self) -> WorkflowProgress | None:
        """Get current progress."""
        with self._lock:
            return self._progress

    def start_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        step_ids: list[str],
        step_names: list[str] | None = None,
    ) -> WorkflowProgress:
        """Start tracking a new workflow.

        Args:
            workflow_id: Unique workflow ID.
            workflow_name: Workflow name.
            step_ids: List of step IDs in execution order.
            step_names: Optional human-readable step names.

        Returns:
            Created WorkflowProgress.
        """
        with self._lock:
            step_names = step_names or step_ids

            steps = {
                step_id: StepProgress(
                    step_id=step_id,
                    step_name=name,
                )
                for step_id, name in zip(step_ids, step_names)
            }

            self._progress = WorkflowProgress(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                total_steps=len(step_ids),
                steps=steps,
                started_at=datetime.now(),
                status=StepStatus.RUNNING,
            )

            self._notify_started()
            return self._progress

    def start_step(self, step_id: str, message: str = "") -> None:
        """Mark a step as started.

        Args:
            step_id: Step identifier.
            message: Optional status message.
        """
        with self._lock:
            if self._progress is None:
                return

            step = self._progress.steps.get(step_id)
            if step:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now()
                step.message = message

                self._notify_step_started(step)

    def update_step(self, step_id: str, message: str) -> None:
        """Update step status message.

        Args:
            step_id: Step identifier.
            message: New status message.
        """
        with self._lock:
            if self._progress is None:
                return

            step = self._progress.steps.get(step_id)
            if step:
                step.message = message
                self._notify_update()

    def complete_step(
        self,
        step_id: str,
        output: Any = None,
        message: str = "",
    ) -> None:
        """Mark a step as completed.

        Args:
            step_id: Step identifier.
            output: Step output data.
            message: Completion message.
        """
        with self._lock:
            if self._progress is None:
                return

            step = self._progress.steps.get(step_id)
            if step:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now()
                step.output = output
                step.message = message or "Completed"

                self._notify_step_completed(step)
                self._check_workflow_complete()

    def fail_step(
        self,
        step_id: str,
        error: str,
    ) -> None:
        """Mark a step as failed.

        Args:
            step_id: Step identifier.
            error: Error message.
        """
        with self._lock:
            if self._progress is None:
                return

            step = self._progress.steps.get(step_id)
            if step:
                step.status = StepStatus.FAILED
                step.completed_at = datetime.now()
                step.error = error
                step.message = f"Failed: {error}"

                self._notify_step_failed(step)
                self._check_workflow_complete()

    def skip_step(self, step_id: str, reason: str = "") -> None:
        """Mark a step as skipped.

        Args:
            step_id: Step identifier.
            reason: Skip reason.
        """
        with self._lock:
            if self._progress is None:
                return

            step = self._progress.steps.get(step_id)
            if step:
                step.status = StepStatus.SKIPPED
                step.completed_at = datetime.now()
                step.message = reason or "Skipped"

                self._check_workflow_complete()

    def complete_workflow(self, success: bool = True) -> None:
        """Mark the workflow as complete.

        Args:
            success: Whether the workflow completed successfully.
        """
        with self._lock:
            if self._progress is None:
                return

            self._progress.status = (
                StepStatus.COMPLETED if success else StepStatus.FAILED
            )
            self._progress.completed_at = datetime.now()

            self._notify_completed()

    def add_observer(self, observer: ProgressObserver) -> None:
        """Add a progress observer.

        Args:
            observer: Observer to add.
        """
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def remove_observer(self, observer: ProgressObserver) -> None:
        """Remove a progress observer.

        Args:
            observer: Observer to remove.
        """
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def on(
        self,
        event: str,
        callback: Callable[[WorkflowProgress], None],
    ) -> None:
        """Register an event callback.

        Args:
            event: Event name (started, step_started, step_completed,
                   step_failed, completed, update).
            callback: Callback function.
        """
        with self._lock:
            if event in self._callbacks:
                self._callbacks[event].append(callback)

    def _notify_started(self) -> None:
        """Notify observers of workflow start."""
        if self._progress is None:
            return

        for observer in self._observers:
            try:
                observer.on_workflow_started(self._progress)
            except Exception:
                pass

        for callback in self._callbacks.get("started", []):
            try:
                callback(self._progress)
            except Exception:
                pass

    def _notify_step_started(self, step: StepProgress) -> None:
        """Notify observers of step start."""
        if self._progress is None:
            return

        for observer in self._observers:
            try:
                observer.on_step_started(self._progress, step)
            except Exception:
                pass

        for callback in self._callbacks.get("step_started", []):
            try:
                callback(self._progress)
            except Exception:
                pass

    def _notify_step_completed(self, step: StepProgress) -> None:
        """Notify observers of step completion."""
        if self._progress is None:
            return

        for observer in self._observers:
            try:
                observer.on_step_completed(self._progress, step)
            except Exception:
                pass

        for callback in self._callbacks.get("step_completed", []):
            try:
                callback(self._progress)
            except Exception:
                pass

    def _notify_step_failed(self, step: StepProgress) -> None:
        """Notify observers of step failure."""
        if self._progress is None:
            return

        for observer in self._observers:
            try:
                observer.on_step_failed(self._progress, step)
            except Exception:
                pass

        for callback in self._callbacks.get("step_failed", []):
            try:
                callback(self._progress)
            except Exception:
                pass

    def _notify_completed(self) -> None:
        """Notify observers of workflow completion."""
        if self._progress is None:
            return

        for observer in self._observers:
            try:
                observer.on_workflow_completed(self._progress)
            except Exception:
                pass

        for callback in self._callbacks.get("completed", []):
            try:
                callback(self._progress)
            except Exception:
                pass

    def _notify_update(self) -> None:
        """Notify observers of progress update."""
        if self._progress is None:
            return

        for callback in self._callbacks.get("update", []):
            try:
                callback(self._progress)
            except Exception:
                pass

    def _check_workflow_complete(self) -> None:
        """Check if all steps are done and complete workflow if so."""
        if self._progress is None:
            return

        all_done = all(s.is_done for s in self._progress.steps.values())
        if all_done:
            has_failures = any(
                s.status == StepStatus.FAILED
                for s in self._progress.steps.values()
            )
            self.complete_workflow(success=not has_failures)

    def get_summary(self) -> str:
        """Get a text summary of progress.

        Returns:
            Summary string.
        """
        with self._lock:
            if self._progress is None:
                return "No workflow in progress"

            p = self._progress
            lines = [
                f"Workflow: {p.workflow_name} ({p.workflow_id})",
                f"Status: {p.status.value}",
                f"Progress: {p.completed_steps}/{p.total_steps} steps "
                f"({p.progress_percent:.1f}%)",
            ]

            if p.duration_seconds is not None:
                lines.append(f"Duration: {p.duration_seconds:.1f}s")

            if p.current_step:
                lines.append(f"Current: {p.current_step.step_name}")
                if p.current_step.message:
                    lines.append(f"  {p.current_step.message}")

            if p.failed_steps > 0:
                lines.append(f"Failed: {p.failed_steps} step(s)")

            return "\n".join(lines)
