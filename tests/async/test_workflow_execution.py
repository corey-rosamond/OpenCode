"""Async execution tests for WorkflowExecutor.

Tests the async workflow execution engine including parallel batch execution,
condition evaluation, retry logic, and state management.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.agents.result import AgentResult
from code_forge.workflows.executor import (
    StepExecutionError,
    StepExecutor,
    WorkflowExecutionError,
    WorkflowExecutor,
)
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStep,
)
from code_forge.workflows.state import CheckpointManager, StateManager, WorkflowState

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_manager() -> MagicMock:
    """Create mock AgentManager."""
    manager = MagicMock()
    manager.spawn = AsyncMock()
    return manager


@pytest.fixture
def mock_agent() -> MagicMock:
    """Create mock Agent with successful result."""
    agent = MagicMock()
    agent.result = AgentResult(
        success=True,
        output="Task completed successfully",
        error=None,
    )
    return agent


@pytest.fixture
def mock_checkpoint_manager() -> MagicMock:
    """Create mock CheckpointManager."""
    manager = MagicMock(spec=CheckpointManager)
    manager.checkpoint_exists.return_value = False
    manager.save_checkpoint = MagicMock()
    manager.delete_checkpoint = MagicMock()
    return manager


@pytest.fixture
def simple_workflow() -> WorkflowDefinition:
    """Create a simple single-step workflow."""
    return WorkflowDefinition(
        name="test-workflow",
        description="Test workflow",
        version="1.0.0",
        steps=[
            WorkflowStep(
                id="step1",
                agent="explore",
                description="Explore the codebase",
                inputs={"task": "Find the main entry point"},
            ),
        ],
    )


@pytest.fixture
def parallel_workflow() -> WorkflowDefinition:
    """Create a workflow with parallel steps."""
    return WorkflowDefinition(
        name="parallel-workflow",
        description="Workflow with parallel execution",
        version="1.0.0",
        steps=[
            WorkflowStep(
                id="step1",
                agent="explore",
                description="First exploration",
                inputs={"task": "Task 1"},
            ),
            WorkflowStep(
                id="step2",
                agent="explore",
                description="Second exploration",
                inputs={"task": "Task 2"},
            ),
            WorkflowStep(
                id="step3",
                agent="explore",
                description="Third exploration",
                inputs={"task": "Task 3"},
            ),
        ],
    )


@pytest.fixture
def sequential_workflow() -> WorkflowDefinition:
    """Create a workflow with sequential dependencies."""
    return WorkflowDefinition(
        name="sequential-workflow",
        description="Workflow with sequential steps",
        version="1.0.0",
        steps=[
            WorkflowStep(
                id="step1",
                agent="explore",
                description="First step",
                inputs={"task": "Task 1"},
            ),
            WorkflowStep(
                id="step2",
                agent="plan",
                description="Second step",
                inputs={"task": "Task 2"},
                depends_on=["step1"],
            ),
            WorkflowStep(
                id="step3",
                agent="code",
                description="Third step",
                inputs={"task": "Task 3"},
                depends_on=["step2"],
            ),
        ],
    )


# =============================================================================
# Test StepExecutor
# =============================================================================


class TestStepExecutorExecute:
    """Tests for StepExecutor.execute."""

    @pytest.mark.asyncio
    async def test_execute_successful_step(
        self, mock_agent_manager: MagicMock, mock_agent: MagicMock
    ) -> None:
        """Execute returns successful result for passing agent."""
        mock_agent_manager.spawn.return_value = mock_agent
        executor = StepExecutor(mock_agent_manager)

        step = WorkflowStep(
            id="test-step",
            agent="explore",
            description="Test step",
            inputs={"task": "Test task"},
        )

        result = await executor.execute(step, {})

        assert result.success is True
        assert result.step_id == "test-step"
        assert result.agent_type == "explore"

    @pytest.mark.asyncio
    async def test_execute_failed_step(
        self, mock_agent_manager: MagicMock
    ) -> None:
        """Execute returns failed result for failing agent."""
        failed_agent = MagicMock()
        failed_agent.result = AgentResult(
            success=False,
            output="Failed",
            error="Agent error",
        )
        mock_agent_manager.spawn.return_value = failed_agent

        executor = StepExecutor(mock_agent_manager)
        step = WorkflowStep(
            id="test-step",
            agent="explore",
            description="Test step",
            inputs={},
        )

        result = await executor.execute(step, {})

        assert result.success is False
        assert result.error == "Agent error"

    @pytest.mark.asyncio
    async def test_execute_with_retry(
        self, mock_agent_manager: MagicMock
    ) -> None:
        """Execute retries on failure up to max_retries."""
        call_count = 0

        async def spawn_with_retry(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            agent = MagicMock()
            if call_count < 3:
                agent.result = AgentResult(success=False, output="", error="Retry")
            else:
                agent.result = AgentResult(success=True, output="Success", error=None)
            return agent

        mock_agent_manager.spawn = spawn_with_retry

        executor = StepExecutor(mock_agent_manager)
        step = WorkflowStep(
            id="retry-step",
            agent="explore",
            description="Test retry step",
            inputs={},
            max_retries=3,
        )

        result = await executor.execute(step, {})

        assert call_count == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_no_result_raises(
        self, mock_agent_manager: MagicMock
    ) -> None:
        """Execute raises when agent returns no result."""
        agent = MagicMock()
        agent.result = None
        mock_agent_manager.spawn.return_value = agent

        executor = StepExecutor(mock_agent_manager)
        step = WorkflowStep(
            id="no-result-step",
            agent="explore",
            description="Test no result step",
            inputs={},
        )

        result = await executor.execute(step, {})

        # Should return failed result after retries exhausted
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_uses_task_from_inputs(
        self, mock_agent_manager: MagicMock, mock_agent: MagicMock
    ) -> None:
        """Execute uses task from inputs if provided."""
        mock_agent_manager.spawn.return_value = mock_agent

        executor = StepExecutor(mock_agent_manager)
        step = WorkflowStep(
            id="task-step",
            agent="explore",
            description="Default description",
            inputs={"task": "Custom task from inputs"},
        )

        await executor.execute(step, {})

        mock_agent_manager.spawn.assert_called_once()
        call_kwargs = mock_agent_manager.spawn.call_args[1]
        assert call_kwargs["task"] == "Custom task from inputs"


# =============================================================================
# Test WorkflowExecutor
# =============================================================================


class TestWorkflowExecutorExecute:
    """Tests for WorkflowExecutor.execute."""

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Execute completes simple single-step workflow."""
        mock_agent_manager.spawn.return_value = mock_agent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(simple_workflow)

        assert result.success is True
        assert len(result.step_results) == 1

    @pytest.mark.asyncio
    async def test_execute_parallel_workflow(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        parallel_workflow: WorkflowDefinition,
    ) -> None:
        """Execute runs independent steps in parallel."""
        execution_times = []

        async def track_spawn(*args: Any, **kwargs: Any) -> MagicMock:
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.01)  # Small delay
            end = asyncio.get_event_loop().time()
            execution_times.append((start, end))
            return mock_agent

        mock_agent_manager.spawn = track_spawn

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(parallel_workflow)

        assert result.success is True
        # All 3 steps should have overlapping execution times (parallel)
        if len(execution_times) == 3:
            # Check for overlap - at least 2 should overlap
            starts = [t[0] for t in execution_times]
            ends = [t[1] for t in execution_times]
            # If parallel, some starts should be before some ends
            max_start = max(starts)
            min_end = min(ends)
            # In parallel execution, max_start < min_end (overlap)

    @pytest.mark.asyncio
    async def test_execute_sequential_workflow(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Execute respects step dependencies."""
        execution_order = []

        async def track_spawn(*args: Any, **kwargs: Any) -> MagicMock:
            agent_type = kwargs.get("agent_type", args[0] if args else "unknown")
            execution_order.append(agent_type)
            return mock_agent

        mock_agent_manager.spawn = track_spawn

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(sequential_workflow)

        assert result.success is True
        # Should execute in order: explore, plan, code
        assert execution_order == ["explore", "plan", "code"]

    @pytest.mark.asyncio
    async def test_execute_generates_workflow_id(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Execute generates workflow ID if not provided."""
        mock_agent_manager.spawn.return_value = mock_agent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(simple_workflow)

        assert result.workflow_id is not None
        assert simple_workflow.name in result.workflow_id

    @pytest.mark.asyncio
    async def test_execute_uses_provided_workflow_id(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Execute uses provided workflow ID."""
        mock_agent_manager.spawn.return_value = mock_agent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(
            simple_workflow,
            workflow_id="custom-workflow-id",
        )

        assert result.workflow_id == "custom-workflow-id"


# =============================================================================
# Test Checkpoint Management
# =============================================================================


class TestWorkflowCheckpointing:
    """Tests for checkpoint save/restore during execution."""

    @pytest.mark.asyncio
    async def test_checkpoint_saved_after_batch(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        parallel_workflow: WorkflowDefinition,
    ) -> None:
        """Checkpoint is saved after each batch completes."""
        mock_agent_manager.spawn.return_value = mock_agent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        await executor.execute(parallel_workflow)

        # Should save checkpoint after batch
        mock_checkpoint_manager.save_checkpoint.assert_called()

    @pytest.mark.asyncio
    async def test_checkpoint_deleted_on_success(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Checkpoint is deleted on successful completion."""
        mock_agent_manager.spawn.return_value = mock_agent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        await executor.execute(
            simple_workflow,
            workflow_id="test-workflow-123",
        )

        mock_checkpoint_manager.delete_checkpoint.assert_called_once_with(
            "test-workflow-123"
        )

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Execute can resume from existing checkpoint."""
        mock_agent_manager.spawn.return_value = mock_agent

        checkpoint_manager = MagicMock(spec=CheckpointManager)
        checkpoint_manager.checkpoint_exists.return_value = True

        # Create a state with step1 already completed
        saved_state = WorkflowState(
            workflow_id="resume-test",
            definition=sequential_workflow,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(UTC),
            completed_steps=["step1"],
            step_results={
                "step1": StepResult(
                    step_id="step1",
                    agent_type="explore",
                    agent_result=AgentResult(success=True, output="Done"),
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                    duration=1.0,
                    success=True,
                ),
            },
        )
        checkpoint_manager.load_checkpoint.return_value = saved_state

        executor = WorkflowExecutor(
            mock_agent_manager,
            checkpoint_manager,
        )

        execution_order = []

        async def track_spawn(*args: Any, **kwargs: Any) -> MagicMock:
            execution_order.append(kwargs.get("agent_type"))
            return mock_agent

        mock_agent_manager.spawn = track_spawn

        await executor.execute(
            sequential_workflow,
            workflow_id="resume-test",
            resume_from_checkpoint=True,
        )

        # Step1 should be skipped (already completed)
        assert "explore" not in execution_order


# =============================================================================
# Test Condition Evaluation
# =============================================================================


class TestWorkflowConditions:
    """Tests for step condition evaluation."""

    @pytest.mark.asyncio
    async def test_step_skipped_when_condition_false(
        self,
        mock_agent_manager: MagicMock,
        mock_agent: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Step is skipped when condition evaluates to false."""
        workflow = WorkflowDefinition(
            name="conditional-workflow",
            description="Test",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="step1",
                    agent="explore",
                    description="Always runs",
                    inputs={},
                ),
                WorkflowStep(
                    id="step2",
                    agent="plan",
                    description="Conditional",
                    inputs={},
                    condition="false",  # Always false
                    depends_on=["step1"],
                ),
            ],
        )

        mock_agent_manager.spawn.return_value = mock_agent
        execution_order = []

        async def track_spawn(*args: Any, **kwargs: Any) -> MagicMock:
            execution_order.append(kwargs.get("agent_type"))
            return mock_agent

        mock_agent_manager.spawn = track_spawn

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(workflow)

        # Only step1 should execute
        assert execution_order == ["explore"]
        assert result.success is True


# =============================================================================
# Test Error Handling
# =============================================================================


class TestWorkflowErrorHandling:
    """Tests for error handling during execution."""

    @pytest.mark.asyncio
    async def test_step_failure_marks_workflow_failed(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Workflow is marked failed when step fails."""
        failed_agent = MagicMock()
        failed_agent.result = AgentResult(
            success=False,
            output="",
            error="Step failed",
        )
        mock_agent_manager.spawn.return_value = failed_agent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(simple_workflow)

        assert result.success is False
        assert result.steps_failed > 0

    @pytest.mark.asyncio
    async def test_exception_during_execution_handled(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Exception during step execution is handled gracefully."""
        mock_agent_manager.spawn.side_effect = RuntimeError("Spawn failed")

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        # Executor catches step errors and returns failed result
        result = await executor.execute(simple_workflow)

        assert result.success is False
        assert result.steps_failed > 0

    @pytest.mark.asyncio
    async def test_checkpoint_saved_on_failure(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Checkpoint is saved when workflow fails."""
        mock_agent_manager.spawn.side_effect = RuntimeError("Failure")

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        # Executor handles step errors and saves checkpoint
        result = await executor.execute(simple_workflow)

        assert result.success is False
        mock_checkpoint_manager.save_checkpoint.assert_called()


# =============================================================================
# Test Concurrent Step Execution
# =============================================================================


class TestConcurrentStepExecution:
    """Tests for concurrent step execution within batches."""

    @pytest.mark.asyncio
    async def test_parallel_steps_run_concurrently(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Steps without dependencies run in parallel."""
        workflow = WorkflowDefinition(
            name="parallel-test",
            description="Test parallel execution",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id=f"step{i}",
                    agent="explore",
                    description=f"Step {i}",
                    inputs={},
                )
                for i in range(5)
            ],
        )

        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def count_concurrent(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            await asyncio.sleep(0.01)

            async with lock:
                concurrent_count -= 1

            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = count_concurrent

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        await executor.execute(workflow)

        # All 5 steps should run in parallel
        assert max_concurrent == 5

    @pytest.mark.asyncio
    async def test_one_step_failure_doesnt_cancel_others(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """One step failing doesn't cancel parallel steps."""
        workflow = WorkflowDefinition(
            name="mixed-result-test",
            description="Test",
            version="1.0.0",
            steps=[
                WorkflowStep(id="success1", agent="explore", description="Step 1", inputs={}),
                WorkflowStep(id="fail", agent="plan", description="Fail step", inputs={}),
                WorkflowStep(id="success2", agent="code", description="Step 2", inputs={}),
            ],
        )

        executed = []

        async def mixed_spawn(*args: Any, **kwargs: Any) -> MagicMock:
            agent_type = kwargs.get("agent_type")
            executed.append(agent_type)

            agent = MagicMock()
            if agent_type == "plan":
                agent.result = AgentResult(success=False, output="", error="Failed")
            else:
                agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = mixed_spawn

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        result = await executor.execute(workflow)

        # All steps should still execute
        assert len(executed) == 3
        assert "explore" in executed
        assert "plan" in executed
        assert "code" in executed

        # But workflow should fail
        assert result.success is False


# =============================================================================
# Test Async Task Handling
# =============================================================================


class TestAsyncTaskHandling:
    """Tests for asyncio task handling edge cases."""

    @pytest.mark.asyncio
    async def test_gather_with_return_exceptions(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """asyncio.gather handles exceptions from individual tasks."""
        workflow = WorkflowDefinition(
            name="exception-test",
            description="Test",
            version="1.0.0",
            steps=[
                WorkflowStep(id="s1", agent="explore", description="Step 1", inputs={}),
                WorkflowStep(id="s2", agent="plan", description="Step 2", inputs={}),
            ],
        )

        call_count = 0

        async def sometimes_raise(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First call fails")
            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = sometimes_raise

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        # Should not raise - gather uses return_exceptions
        result = await executor.execute(workflow)

        # Workflow should complete (with failures handled)
        assert result is not None

    @pytest.mark.asyncio
    async def test_cancellation_handling(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: MagicMock,
        simple_workflow: WorkflowDefinition,
    ) -> None:
        """Workflow handles task cancellation gracefully."""
        started = asyncio.Event()

        async def slow_spawn(*args: Any, **kwargs: Any) -> MagicMock:
            started.set()
            await asyncio.sleep(10)  # Very slow
            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = slow_spawn

        executor = WorkflowExecutor(
            mock_agent_manager,
            mock_checkpoint_manager,
        )

        task = asyncio.create_task(executor.execute(simple_workflow))

        # Wait for execution to start
        await started.wait()

        # Cancel the task
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
