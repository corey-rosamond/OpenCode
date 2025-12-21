"""Workflow execution engine.

This module provides the core workflow orchestration logic for executing
multi-step agent workflows with dependencies, conditions, and parallel execution.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from code_forge.agents.manager import AgentManager
from code_forge.agents.result import AgentResult
from code_forge.core.logging import get_logger
from code_forge.workflows.conditions import ConditionEvaluator
from code_forge.workflows.graph import TopologicalSorter, WorkflowGraph
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from code_forge.workflows.state import CheckpointManager, StateManager

logger = get_logger(__name__)


class WorkflowExecutionError(Exception):
    """Error during workflow execution."""

    pass


class StepExecutionError(Exception):
    """Error during step execution."""

    pass


class StepExecutor:
    """Executes a single workflow step.

    Handles agent execution, retry logic, and result collection for
    individual workflow steps.

    Attributes:
        agent_manager: Manager for agent instances
        max_retries: Maximum retry attempts for failed steps
    """

    def __init__(self, agent_manager: AgentManager, max_retries: int = 0) -> None:
        """Initialize step executor.

        Args:
            agent_manager: Agent manager instance
            max_retries: Default maximum retry attempts
        """
        self.agent_manager = agent_manager
        self.max_retries = max_retries

    async def execute(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a single workflow step.

        Args:
            step: Step definition to execute
            context: Execution context with previous step results

        Returns:
            Step execution result

        Raises:
            StepExecutionError: If step execution fails after retries
        """
        max_attempts = step.max_retries + 1  # Original attempt + retries
        last_error = None

        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    logger.info(f"Retrying step {step.id} (attempt {attempt + 1}/{max_attempts})")

                start_time = datetime.now(UTC)

                # Prepare task description from inputs
                task = step.inputs.get("task", step.description)

                # Spawn agent for this step
                agent = await self.agent_manager.spawn(
                    agent_type=step.agent,
                    task=task,
                    wait=True,  # Wait for completion
                )

                # Get the agent result
                agent_result = agent.result
                if agent_result is None:
                    raise StepExecutionError(f"Agent {step.agent} returned no result")

                end_time = datetime.now(UTC)
                duration = (end_time - start_time).total_seconds()

                # Check if agent execution succeeded
                if not agent_result.success:
                    # Agent failed - trigger retry if attempts remaining
                    if attempt < max_attempts - 1:
                        last_error = agent_result.error or "Agent execution failed"
                        logger.warning(f"Step {step.id} failed (attempt {attempt + 1})")
                        continue

                # Create step result (success or final failure)
                return StepResult(
                    step_id=step.id,
                    agent_type=step.agent,
                    agent_result=agent_result,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    success=agent_result.success,
                    error=agent_result.error if not agent_result.success else None,
                )

            except Exception as e:
                last_error = str(e)
                logger.error(f"Step {step.id} failed: {e} (attempt {attempt + 1})")
                if attempt < max_attempts - 1:
                    continue

        # All attempts failed
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        return StepResult(
            step_id=step.id,
            agent_type=step.agent,
            agent_result=AgentResult(
                success=False,
                output=f"Step failed after {max_attempts} attempts",
                error=last_error,
            ),
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=False,
            error=last_error,
        )

    def _prepare_inputs(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare step inputs by resolving context references.

        Args:
            inputs: Raw input dictionary
            context: Execution context

        Returns:
            Resolved inputs
        """
        # For now, just pass inputs as-is
        # Future: Add template variable resolution like ${step1.result.value}
        return inputs.copy()


class WorkflowExecutor:
    """Executes workflow definitions.

    Orchestrates multi-step workflow execution with dependency resolution,
    conditional execution, parallel execution, and state management.

    Attributes:
        agent_manager: Manager for agent instances
        checkpoint_manager: Manager for workflow checkpoints
        step_executor: Executor for individual steps
    """

    def __init__(
        self,
        agent_manager: AgentManager,
        checkpoint_manager: CheckpointManager | None = None,
    ) -> None:
        """Initialize workflow executor.

        Args:
            agent_manager: Agent manager instance
            checkpoint_manager: Optional checkpoint manager for persistence
        """
        self.agent_manager = agent_manager
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.step_executor = StepExecutor(agent_manager)

    async def execute(
        self,
        definition: WorkflowDefinition,
        workflow_id: str | None = None,
        resume_from_checkpoint: bool = False,
    ) -> WorkflowResult:
        """Execute a workflow definition.

        Args:
            definition: Workflow definition to execute
            workflow_id: Optional workflow ID (generated if not provided)
            resume_from_checkpoint: Whether to resume from existing checkpoint

        Returns:
            Workflow execution result

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        # Generate workflow ID if not provided
        if workflow_id is None:
            workflow_id = f"{definition.name}-{datetime.now(UTC).timestamp()}"

        # Initialize or resume state
        if resume_from_checkpoint and self.checkpoint_manager.checkpoint_exists(workflow_id):
            logger.info(f"Resuming workflow {workflow_id} from checkpoint")
            state = self.checkpoint_manager.load_checkpoint(workflow_id)
            state_manager = StateManager(workflow_id, definition)
            state_manager.state = state
        else:
            logger.info(f"Starting new workflow {workflow_id}")
            state_manager = StateManager(workflow_id, definition)
            state_manager.start_workflow()

        try:
            # Build and validate workflow graph
            graph = WorkflowGraph.from_definition(definition)

            # Get execution batches (topologically sorted with parallelism)
            sorter = TopologicalSorter(graph)
            batches = sorter.get_execution_batches()

            logger.info(f"Executing workflow with {len(batches)} batches")

            # Execute batches sequentially, steps within batch in parallel
            for batch_idx, batch in enumerate(batches):
                logger.info(f"Executing batch {batch_idx + 1}/{len(batches)} with {len(batch)} steps")

                # Filter out already completed steps (for resume)
                pending_steps = [
                    step_id for step_id in batch
                    if not state_manager.is_step_completed(step_id)
                ]

                if not pending_steps:
                    logger.info(f"Batch {batch_idx + 1} already completed, skipping")
                    continue

                # Execute steps in parallel
                await self._execute_batch(
                    pending_steps,
                    definition,
                    state_manager,
                )

                # Save checkpoint after each batch
                if self.checkpoint_manager:
                    self.checkpoint_manager.save_checkpoint(state_manager.state)

            # Check if any steps failed
            if state_manager.state.failed_steps:
                state_manager.fail_workflow(
                    f"{len(state_manager.state.failed_steps)} step(s) failed"
                )
                # Save checkpoint on failure for potential resume
                if self.checkpoint_manager:
                    self.checkpoint_manager.save_checkpoint(state_manager.state)
            else:
                state_manager.complete_workflow()

            # Create final result
            result = WorkflowResult.from_state(state_manager.state)

            # Clean up checkpoint on success
            if result.success and self.checkpoint_manager:
                self.checkpoint_manager.delete_checkpoint(workflow_id)

            return result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            state_manager.fail_workflow(str(e))

            # Save checkpoint on failure for potential resume
            if self.checkpoint_manager:
                self.checkpoint_manager.save_checkpoint(state_manager.state)

            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e

    async def _execute_batch(
        self,
        step_ids: list[str],
        definition: WorkflowDefinition,
        state_manager: StateManager,
    ) -> None:
        """Execute a batch of steps in parallel.

        Args:
            step_ids: List of step IDs to execute
            definition: Workflow definition
            state_manager: State manager for this workflow
        """
        # Get step definitions
        steps = [
            step for step in definition.steps
            if step.id in step_ids
        ]

        # Execute steps in parallel
        tasks = [
            self._execute_step(step, state_manager)
            for step in steps
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_step(
        self,
        step: WorkflowStep,
        state_manager: StateManager,
    ) -> None:
        """Execute a single step with condition evaluation.

        Args:
            step: Step definition
            state_manager: State manager for this workflow
        """
        try:
            # Check if step should be skipped due to condition
            if step.condition:
                should_execute = await self._evaluate_condition(
                    step.condition,
                    state_manager,
                )
                if not should_execute:
                    logger.info(f"Step {step.id} skipped due to condition: {step.condition}")
                    state_manager.skip_step(step.id, reason="Condition not met")
                    return

            # Mark step as started
            state_manager.start_step(step.id)

            # Execute step
            logger.info(f"Executing step {step.id} ({step.agent})")
            context = state_manager.get_evaluation_context()
            result = await self.step_executor.execute(step, context)

            # Record result
            state_manager.complete_step(result)

            if result.success:
                logger.info(f"Step {step.id} completed successfully")
            else:
                logger.error(f"Step {step.id} failed: {result.error}")

        except Exception as e:
            logger.error(f"Unexpected error executing step {step.id}: {e}")
            # Create failed result
            result = StepResult(
                step_id=step.id,
                agent_type=step.agent,
                agent_result=AgentResult(
                    success=False,
                    output="Unexpected error",
                    error=str(e),
                ),
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration=0.0,
                success=False,
                error=str(e),
            )
            state_manager.complete_step(result)

    async def _evaluate_condition(
        self,
        condition: str,
        state_manager: StateManager,
    ) -> bool:
        """Evaluate a step condition.

        Args:
            condition: Condition expression
            state_manager: State manager for context

        Returns:
            True if condition is met
        """
        try:
            context = state_manager.get_evaluation_context()
            evaluator = ConditionEvaluator(context)
            return evaluator.evaluate(condition)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}, defaulting to False")
            return False
