"""Workflow rollback support using the undo system.

This module provides rollback capabilities for multi-step workflows,
allowing entire workflows to be undone in case of failure or user request.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from code_forge.undo.manager import UndoManager
    from code_forge.workflows.models import WorkflowDefinition

logger = logging.getLogger(__name__)


@dataclass
class WorkflowCheckpoint:
    """A checkpoint within a workflow execution.

    Attributes:
        step_id: Step that created this checkpoint.
        step_name: Human-readable step name.
        undo_ids: List of undo entry IDs created during this step.
        timestamp: When the checkpoint was created.
        metadata: Additional checkpoint metadata.
    """

    step_id: str
    step_name: str
    undo_ids: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRollbackState:
    """State of a workflow for rollback purposes.

    Attributes:
        workflow_id: Unique workflow execution ID.
        workflow_name: Name of the workflow.
        checkpoints: List of checkpoints in execution order.
        started_at: When the workflow started.
        can_rollback: Whether rollback is possible.
    """

    workflow_id: str
    workflow_name: str
    checkpoints: list[WorkflowCheckpoint] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    can_rollback: bool = True

    @property
    def total_undos(self) -> int:
        """Total number of undo operations available."""
        return sum(len(cp.undo_ids) for cp in self.checkpoints)

    @property
    def step_count(self) -> int:
        """Number of steps with checkpoints."""
        return len(self.checkpoints)


class WorkflowRollback:
    """Manages workflow rollback using the undo system.

    Integrates with UndoManager to provide:
    - Checkpoint creation during workflow execution
    - Full workflow rollback on failure
    - Partial rollback to specific steps
    - Rollback history tracking
    """

    def __init__(self, undo_manager: UndoManager | None = None) -> None:
        """Initialize the rollback manager.

        Args:
            undo_manager: Optional undo manager instance.
        """
        self._undo_manager = undo_manager
        self._active_workflow: WorkflowRollbackState | None = None
        self._history: list[WorkflowRollbackState] = []
        self._max_history = 10

    @property
    def active_workflow(self) -> WorkflowRollbackState | None:
        """Get the active workflow state."""
        return self._active_workflow

    @property
    def can_rollback(self) -> bool:
        """Check if rollback is possible."""
        if self._active_workflow is None:
            return False
        if not self._active_workflow.can_rollback:
            return False
        return self._active_workflow.total_undos > 0

    def start_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
    ) -> WorkflowRollbackState:
        """Start tracking a new workflow for rollback.

        Args:
            workflow_id: Unique workflow ID.
            workflow_name: Workflow name.

        Returns:
            Created rollback state.
        """
        # Archive previous workflow if exists
        if self._active_workflow:
            self._archive_workflow()

        self._active_workflow = WorkflowRollbackState(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
        )

        logger.debug(f"Started tracking workflow {workflow_id} for rollback")
        return self._active_workflow

    def checkpoint(
        self,
        step_id: str,
        step_name: str,
        undo_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowCheckpoint:
        """Create a checkpoint after a step.

        Args:
            step_id: Step identifier.
            step_name: Human-readable step name.
            undo_ids: List of undo entry IDs from this step.
            metadata: Additional checkpoint data.

        Returns:
            Created checkpoint.

        Raises:
            RuntimeError: If no active workflow.
        """
        if self._active_workflow is None:
            raise RuntimeError("No active workflow for checkpoint")

        checkpoint = WorkflowCheckpoint(
            step_id=step_id,
            step_name=step_name,
            undo_ids=undo_ids or [],
            metadata=metadata or {},
        )

        self._active_workflow.checkpoints.append(checkpoint)
        logger.debug(
            f"Created checkpoint for step {step_id} with "
            f"{len(checkpoint.undo_ids)} undo entries"
        )

        return checkpoint

    def get_undo_ids_since_step(self, step_id: str) -> list[str]:
        """Get all undo IDs created since a specific step.

        Args:
            step_id: Step to start from (exclusive).

        Returns:
            List of undo entry IDs.
        """
        if self._active_workflow is None:
            return []

        undo_ids: list[str] = []
        found_step = False

        for checkpoint in self._active_workflow.checkpoints:
            if found_step:
                undo_ids.extend(checkpoint.undo_ids)
            if checkpoint.step_id == step_id:
                found_step = True

        return undo_ids

    def get_all_undo_ids(self) -> list[str]:
        """Get all undo IDs from the current workflow.

        Returns:
            List of all undo entry IDs in reverse order (newest first).
        """
        if self._active_workflow is None:
            return []

        undo_ids: list[str] = []
        for checkpoint in reversed(self._active_workflow.checkpoints):
            undo_ids.extend(reversed(checkpoint.undo_ids))

        return undo_ids

    def rollback_step(self, step_id: str) -> int:
        """Rollback a specific step.

        Args:
            step_id: Step to rollback.

        Returns:
            Number of undo operations performed.

        Raises:
            RuntimeError: If no undo manager or no active workflow.
        """
        if self._undo_manager is None:
            raise RuntimeError("No undo manager configured")

        if self._active_workflow is None:
            raise RuntimeError("No active workflow")

        # Find the checkpoint for this step
        checkpoint = next(
            (cp for cp in self._active_workflow.checkpoints if cp.step_id == step_id),
            None,
        )

        if checkpoint is None:
            logger.warning(f"No checkpoint found for step {step_id}")
            return 0

        # Undo in reverse order
        count = 0
        for undo_id in reversed(checkpoint.undo_ids):
            if self._undo_manager.undo():
                count += 1
            else:
                logger.warning(f"Failed to undo entry {undo_id}")

        # Remove the checkpoint
        self._active_workflow.checkpoints = [
            cp for cp in self._active_workflow.checkpoints
            if cp.step_id != step_id
        ]

        logger.info(f"Rolled back step {step_id} with {count} undo operations")
        return count

    def rollback_to_step(self, step_id: str) -> int:
        """Rollback all steps after a specific step.

        Args:
            step_id: Step to rollback to (exclusive - this step is kept).

        Returns:
            Number of undo operations performed.

        Raises:
            RuntimeError: If no undo manager or no active workflow.
        """
        if self._undo_manager is None:
            raise RuntimeError("No undo manager configured")

        if self._active_workflow is None:
            raise RuntimeError("No active workflow")

        undo_ids = self.get_undo_ids_since_step(step_id)

        count = 0
        for _ in undo_ids:
            if self._undo_manager.undo():
                count += 1

        # Remove checkpoints after the target step
        found = False
        new_checkpoints: list[WorkflowCheckpoint] = []
        for cp in self._active_workflow.checkpoints:
            if not found:
                new_checkpoints.append(cp)
            if cp.step_id == step_id:
                found = True

        self._active_workflow.checkpoints = new_checkpoints

        logger.info(f"Rolled back to step {step_id} with {count} undo operations")
        return count

    def rollback_workflow(self) -> int:
        """Rollback the entire workflow.

        Returns:
            Number of undo operations performed.

        Raises:
            RuntimeError: If no undo manager or no active workflow.
        """
        if self._undo_manager is None:
            raise RuntimeError("No undo manager configured")

        if self._active_workflow is None:
            raise RuntimeError("No active workflow")

        undo_ids = self.get_all_undo_ids()

        count = 0
        for _ in undo_ids:
            if self._undo_manager.undo():
                count += 1

        workflow_name = self._active_workflow.workflow_name
        self._active_workflow.checkpoints.clear()
        self._active_workflow.can_rollback = False

        logger.info(f"Rolled back entire workflow '{workflow_name}' with {count} operations")
        return count

    def complete_workflow(self, success: bool = True) -> None:
        """Mark the workflow as complete.

        Args:
            success: Whether the workflow succeeded.
        """
        if self._active_workflow is None:
            return

        if success:
            logger.info(
                f"Workflow '{self._active_workflow.workflow_name}' completed "
                f"with {self._active_workflow.step_count} checkpoints"
            )
        else:
            logger.warning(
                f"Workflow '{self._active_workflow.workflow_name}' failed "
                f"- rollback may be needed"
            )

        self._archive_workflow()

    def discard_workflow(self) -> None:
        """Discard the current workflow without archiving."""
        if self._active_workflow:
            logger.debug(f"Discarding workflow {self._active_workflow.workflow_id}")
            self._active_workflow = None

    def get_rollback_summary(self) -> str:
        """Get a summary of available rollback operations.

        Returns:
            Summary string.
        """
        if self._active_workflow is None:
            return "No active workflow"

        wf = self._active_workflow
        lines = [
            f"Workflow: {wf.workflow_name} ({wf.workflow_id})",
            f"Steps: {wf.step_count}",
            f"Total undo operations: {wf.total_undos}",
            f"Can rollback: {'Yes' if wf.can_rollback else 'No'}",
        ]

        if wf.checkpoints:
            lines.append("\nCheckpoints:")
            for cp in wf.checkpoints:
                lines.append(f"  - {cp.step_name}: {len(cp.undo_ids)} operations")

        return "\n".join(lines)

    def _archive_workflow(self) -> None:
        """Archive the current workflow to history."""
        if self._active_workflow is not None:
            self._history.append(self._active_workflow)
            # Trim history if needed
            while len(self._history) > self._max_history:
                self._history.pop(0)
            self._active_workflow = None
