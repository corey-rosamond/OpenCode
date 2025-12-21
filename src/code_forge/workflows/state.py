"""Workflow state management and checkpointing.

This module provides state persistence for workflows, enabling resume from
checkpoint after failure or interruption.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from code_forge.core.logging import get_logger
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowState,
    WorkflowStatus,
)

logger = get_logger(__name__)


class StateManagementError(Exception):
    """Error during state management operations."""

    pass


class CheckpointNotFoundError(StateManagementError):
    """Checkpoint file not found."""

    pass


class CheckpointCorruptedError(StateManagementError):
    """Checkpoint file is corrupted or invalid."""

    pass


class StateManager:
    """Manages workflow state during execution.

    Provides an in-memory state tracking for active workflows with
    integration to CheckpointManager for persistence.

    Attributes:
        workflow_id: Unique workflow identifier
        state: Current workflow state
    """

    def __init__(self, workflow_id: str, definition: WorkflowDefinition) -> None:
        """Initialize state manager.

        Args:
            workflow_id: Unique workflow identifier
            definition: Workflow definition
        """
        self.workflow_id = workflow_id
        self.state = WorkflowState(
            workflow_id=workflow_id,
            definition=definition,
            status=WorkflowStatus.PENDING,
            current_step=None,
            completed_steps=[],
            failed_steps=[],
            skipped_steps=[],
            step_results={},
            start_time=datetime.now(UTC),
            end_time=None,
        )

    def start_workflow(self) -> None:
        """Mark workflow as running."""
        self.state.status = WorkflowStatus.RUNNING
        self.state.start_time = datetime.now(UTC)
        logger.info(f"Workflow {self.workflow_id} started")

    def start_step(self, step_id: str) -> None:
        """Mark a step as currently executing.

        Args:
            step_id: Step identifier
        """
        self.state.current_step = step_id
        logger.debug(f"Step {step_id} started in workflow {self.workflow_id}")

    def complete_step(self, step_result: StepResult) -> None:
        """Record step completion.

        Args:
            step_result: Result of the completed step
        """
        step_id = step_result.step_id

        if step_result.success:
            # Remove from failed list if it was there (re-execution)
            if step_id in self.state.failed_steps:
                self.state.failed_steps.remove(step_id)

            # Add to completed if not already there
            if step_id not in self.state.completed_steps:
                self.state.completed_steps.append(step_id)

            logger.info(f"Step {step_id} completed successfully")
        else:
            # Remove from completed list if it was there (re-execution)
            if step_id in self.state.completed_steps:
                self.state.completed_steps.remove(step_id)

            # Add to failed if not already there
            if step_id not in self.state.failed_steps:
                self.state.failed_steps.append(step_id)

            logger.warning(f"Step {step_id} failed: {step_result.error}")

        self.state.step_results[step_id] = step_result
        self.state.current_step = None

    def skip_step(self, step_id: str, reason: str = "Condition not met") -> None:
        """Record step skip.

        Args:
            step_id: Step identifier
            reason: Reason for skipping
        """
        self.state.skipped_steps.append(step_id)
        logger.info(f"Step {step_id} skipped: {reason}")

    def fail_workflow(self, error: str) -> None:
        """Mark workflow as failed.

        Args:
            error: Error message
        """
        self.state.status = WorkflowStatus.FAILED
        self.state.end_time = datetime.now(UTC)
        logger.error(f"Workflow {self.workflow_id} failed: {error}")

    def complete_workflow(self) -> None:
        """Mark workflow as completed."""
        self.state.status = WorkflowStatus.COMPLETED
        self.state.end_time = datetime.now(UTC)
        logger.info(f"Workflow {self.workflow_id} completed successfully")

    def pause_workflow(self) -> None:
        """Mark workflow as paused."""
        self.state.status = WorkflowStatus.PAUSED
        logger.info(f"Workflow {self.workflow_id} paused")

    def get_step_result(self, step_id: str) -> StepResult | None:
        """Get result for a specific step.

        Args:
            step_id: Step identifier

        Returns:
            Step result if available, None otherwise
        """
        return self.state.step_results.get(step_id)

    def is_step_completed(self, step_id: str) -> bool:
        """Check if a step has completed successfully.

        Args:
            step_id: Step identifier

        Returns:
            True if step completed successfully
        """
        return step_id in self.state.completed_steps

    def is_step_failed(self, step_id: str) -> bool:
        """Check if a step has failed.

        Args:
            step_id: Step identifier

        Returns:
            True if step failed
        """
        return step_id in self.state.failed_steps

    def get_evaluation_context(self) -> dict[str, Any]:
        """Get context for condition evaluation.

        Returns:
            Dictionary mapping step IDs to their results for condition evaluation
        """
        context: dict[str, Any] = {}

        for step_id, result in self.state.step_results.items():
            # Add step result data for conditions like "step1.result.value"
            context[step_id] = {
                "success": result.success,
                "failed": not result.success,
                "result": result.agent_result.data if result.agent_result else {},
            }

        return context


class CheckpointManager:
    """Manages workflow checkpoint persistence.

    Handles saving and loading workflow state checkpoints to/from disk,
    enabling workflow resume after failure or interruption.

    Attributes:
        checkpoint_dir: Directory where checkpoints are stored
    """

    DEFAULT_DIR_NAME = "workflows"
    CHECKPOINT_EXTENSION = ".checkpoint.json"

    def __init__(self, checkpoint_dir: Path | str | None = None) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for checkpoint files. Uses default if None.
        """
        if checkpoint_dir is None:
            checkpoint_dir = self.get_default_dir()
        elif isinstance(checkpoint_dir, str):
            checkpoint_dir = Path(checkpoint_dir)

        self.checkpoint_dir = checkpoint_dir
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create checkpoint directory if it doesn't exist."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        # Set secure permissions (owner only)
        with contextlib.suppress(OSError):
            self.checkpoint_dir.chmod(0o700)

    @classmethod
    def get_default_dir(cls) -> Path:
        """Get the default checkpoint directory.

        Returns:
            Path to default checkpoint directory
        """
        # Use XDG_DATA_HOME if available, else ~/.local/share
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"

        return base / "forge" / cls.DEFAULT_DIR_NAME / "checkpoints"

    @classmethod
    def get_project_dir(cls, project_root: Path | str) -> Path:
        """Get the project-local checkpoint directory.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to project checkpoint directory
        """
        if isinstance(project_root, str):
            project_root = Path(project_root)
        return project_root / ".forge" / cls.DEFAULT_DIR_NAME / "checkpoints"

    def get_checkpoint_path(self, workflow_id: str) -> Path:
        """Get the file path for a checkpoint.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Path to the checkpoint file
        """
        return self.checkpoint_dir / f"{workflow_id}{self.CHECKPOINT_EXTENSION}"

    def save_checkpoint(self, state: WorkflowState) -> None:
        """Save workflow state to checkpoint.

        Uses atomic write with temporary file and rename to ensure consistency.

        Args:
            state: Workflow state to save

        Raises:
            StateManagementError: If checkpoint cannot be saved
        """
        checkpoint_path = self.get_checkpoint_path(state.workflow_id)

        try:
            # Serialize state
            checkpoint_data = self._serialize_state(state)

            # Atomic write using temp file
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.checkpoint_dir,
                delete=False,
                suffix=".tmp",
            ) as temp_file:
                json.dump(checkpoint_data, temp_file, indent=2)
                temp_path = Path(temp_file.name)

            # Atomic rename
            shutil.move(str(temp_path), str(checkpoint_path))

            # Set secure permissions
            with contextlib.suppress(OSError):
                checkpoint_path.chmod(0o600)

            logger.info(f"Checkpoint saved for workflow {state.workflow_id}")

        except (OSError, json.JSONEncodeError) as e:
            # Clean up temp file if it exists
            if "temp_path" in locals():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

            raise StateManagementError(
                f"Failed to save checkpoint for workflow {state.workflow_id}: {e}"
            ) from e

    def load_checkpoint(self, workflow_id: str) -> WorkflowState:
        """Load workflow state from checkpoint.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Restored workflow state

        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
            CheckpointCorruptedError: If checkpoint is corrupted
        """
        checkpoint_path = self.get_checkpoint_path(workflow_id)

        if not checkpoint_path.exists():
            raise CheckpointNotFoundError(
                f"No checkpoint found for workflow {workflow_id}"
            )

        try:
            with open(checkpoint_path, encoding="utf-8") as f:
                checkpoint_data = json.load(f)

            state = self._deserialize_state(checkpoint_data)
            logger.info(f"Checkpoint loaded for workflow {workflow_id}")
            return state

        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            raise CheckpointCorruptedError(
                f"Checkpoint corrupted for workflow {workflow_id}: {e}"
            ) from e

    def delete_checkpoint(self, workflow_id: str) -> None:
        """Delete checkpoint for a workflow.

        Args:
            workflow_id: Workflow identifier
        """
        checkpoint_path = self.get_checkpoint_path(workflow_id)

        with contextlib.suppress(OSError):
            checkpoint_path.unlink()
            logger.info(f"Checkpoint deleted for workflow {workflow_id}")

    def checkpoint_exists(self, workflow_id: str) -> bool:
        """Check if a checkpoint exists.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if checkpoint exists
        """
        return self.get_checkpoint_path(workflow_id).exists()

    def list_checkpoints(self) -> list[str]:
        """List all workflow IDs with checkpoints.

        Returns:
            List of workflow IDs
        """
        checkpoints = []
        for path in self.checkpoint_dir.glob(f"*{self.CHECKPOINT_EXTENSION}"):
            workflow_id = path.name.replace(self.CHECKPOINT_EXTENSION, "")
            checkpoints.append(workflow_id)
        return sorted(checkpoints)

    def _serialize_state(self, state: WorkflowState) -> dict[str, Any]:
        """Serialize workflow state to JSON-compatible dict.

        Args:
            state: Workflow state

        Returns:
            JSON-compatible dictionary
        """
        # Serialize definition
        definition_data = {
            "name": state.definition.name,
            "description": state.definition.description,
            "version": state.definition.version,
            "author": state.definition.author,
            "steps": [
                {
                    "id": step.id,
                    "agent": step.agent,
                    "description": step.description,
                    "inputs": step.inputs,
                    "depends_on": step.depends_on,
                    "parallel_with": step.parallel_with,
                    "condition": step.condition,
                    "timeout": step.timeout,
                    "max_retries": step.max_retries,
                }
                for step in state.definition.steps
            ],
            "metadata": state.definition.metadata,
        }

        # Serialize step results
        step_results_data = {}
        for step_id, result in state.step_results.items():
            step_results_data[step_id] = {
                "step_id": result.step_id,
                "agent_type": result.agent_type,
                "agent_result": {
                    "success": result.agent_result.success if result.agent_result else False,
                    "output": result.agent_result.output if result.agent_result else "",
                    "data": result.agent_result.data if result.agent_result else None,
                    "error": result.agent_result.error if result.agent_result else None,
                    "tokens_used": result.agent_result.tokens_used if result.agent_result else 0,
                    "time_seconds": result.agent_result.time_seconds if result.agent_result else 0.0,
                    "tool_calls": result.agent_result.tool_calls if result.agent_result else 0,
                    "metadata": result.agent_result.metadata if result.agent_result else {},
                },
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat(),
                "duration": result.duration,
                "success": result.success,
                "error": result.error,
            }

        return {
            "workflow_id": state.workflow_id,
            "definition": definition_data,
            "status": state.status.value,
            "current_step": state.current_step,
            "completed_steps": state.completed_steps,
            "failed_steps": state.failed_steps,
            "skipped_steps": state.skipped_steps,
            "step_results": step_results_data,
            "start_time": state.start_time.isoformat(),
            "end_time": state.end_time.isoformat() if state.end_time else None,
        }

    def _deserialize_state(self, data: dict[str, Any]) -> WorkflowState:
        """Deserialize workflow state from JSON-compatible dict.

        Args:
            data: JSON-compatible dictionary

        Returns:
            Workflow state

        Raises:
            ValueError: If data is invalid
        """
        from code_forge.workflows.models import WorkflowStep
        from code_forge.agents.result import AgentResult

        # Deserialize definition
        definition_data = data["definition"]
        steps = [
            WorkflowStep(
                id=step_data["id"],
                agent=step_data["agent"],
                description=step_data["description"],
                inputs=step_data.get("inputs", {}),
                depends_on=step_data.get("depends_on", []),
                parallel_with=step_data.get("parallel_with", []),
                condition=step_data.get("condition"),
                timeout=step_data.get("timeout"),
                max_retries=step_data.get("max_retries", 0),
            )
            for step_data in definition_data["steps"]
        ]

        definition = WorkflowDefinition(
            name=definition_data["name"],
            description=definition_data["description"],
            version=definition_data["version"],
            author=definition_data.get("author"),
            steps=steps,
            metadata=definition_data.get("metadata", {}),
        )

        # Deserialize step results
        step_results = {}
        for step_id, result_data in data.get("step_results", {}).items():
            agent_result_data = result_data["agent_result"]
            agent_result = AgentResult(
                success=agent_result_data["success"],
                output=agent_result_data.get("output", ""),
                data=agent_result_data.get("data"),
                error=agent_result_data.get("error"),
                tokens_used=agent_result_data.get("tokens_used", 0),
                time_seconds=agent_result_data.get("time_seconds", 0.0),
                tool_calls=agent_result_data.get("tool_calls", 0),
                metadata=agent_result_data.get("metadata", {}),
            )

            step_results[step_id] = StepResult(
                step_id=result_data["step_id"],
                agent_type=result_data["agent_type"],
                agent_result=agent_result,
                start_time=datetime.fromisoformat(result_data["start_time"]),
                end_time=datetime.fromisoformat(result_data["end_time"]),
                duration=result_data["duration"],
                success=result_data["success"],
                error=result_data.get("error"),
            )

        return WorkflowState(
            workflow_id=data["workflow_id"],
            definition=definition,
            status=WorkflowStatus(data["status"]),
            current_step=data.get("current_step"),
            completed_steps=data.get("completed_steps", []),
            failed_steps=data.get("failed_steps", []),
            skipped_steps=data.get("skipped_steps", []),
            step_results=step_results,
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
        )
