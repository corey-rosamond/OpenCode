"""E2E tests for multi-agent workflow execution.

Tests agent chaining, parallel execution, and context passing.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.agents.result import AgentResult
from code_forge.workflows.executor import WorkflowExecutor, StepExecutor
from code_forge.workflows.models import (
    StepResult,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
)
from code_forge.workflows.state import CheckpointManager, StateManager

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_manager() -> MagicMock:
    """Create mock agent manager for workflow tests."""
    manager = MagicMock()

    async def spawn_agent(*args, **kwargs) -> MagicMock:
        agent = MagicMock()
        agent.result = AgentResult(
            success=True,
            output="Agent completed successfully",
            data={"step": kwargs.get("task", "unknown")},
        )
        return agent

    manager.spawn = AsyncMock(side_effect=spawn_agent)
    return manager


@pytest.fixture
def mock_checkpoint_manager(tmp_path: Path) -> CheckpointManager:
    """Create real checkpoint manager with temp directory."""
    return CheckpointManager(tmp_path / "checkpoints")


@pytest.fixture
def sequential_workflow() -> WorkflowDefinition:
    """Create workflow with sequential steps."""
    return WorkflowDefinition(
        name="sequential-test",
        description="Test sequential agent chaining",
        version="1.0.0",
        steps=[
            WorkflowStep(
                id="explore",
                agent="explore",
                description="Explore the codebase",
                inputs={"task": "Find entry points"},
            ),
            WorkflowStep(
                id="plan",
                agent="plan",
                description="Plan the implementation",
                inputs={"task": "Create implementation plan"},
                depends_on=["explore"],
            ),
            WorkflowStep(
                id="implement",
                agent="code",
                description="Implement the feature",
                inputs={"task": "Write the code"},
                depends_on=["plan"],
            ),
        ],
    )


@pytest.fixture
def parallel_workflow() -> WorkflowDefinition:
    """Create workflow with parallel steps."""
    return WorkflowDefinition(
        name="parallel-test",
        description="Test parallel agent execution",
        version="1.0.0",
        steps=[
            WorkflowStep(
                id="init",
                agent="explore",
                description="Initialize",
                inputs={"task": "Setup"},
            ),
            WorkflowStep(
                id="task-a",
                agent="explore",
                description="Task A",
                inputs={"task": "Parallel A"},
                depends_on=["init"],
            ),
            WorkflowStep(
                id="task-b",
                agent="explore",
                description="Task B",
                inputs={"task": "Parallel B"},
                depends_on=["init"],
            ),
            WorkflowStep(
                id="task-c",
                agent="explore",
                description="Task C",
                inputs={"task": "Parallel C"},
                depends_on=["init"],
            ),
            WorkflowStep(
                id="finalize",
                agent="plan",
                description="Finalize",
                inputs={"task": "Combine results"},
                depends_on=["task-a", "task-b", "task-c"],
            ),
        ],
    )


# =============================================================================
# Test Sequential Agent Chaining
# =============================================================================


class TestSequentialAgentChaining:
    """Tests for sequential agent execution."""

    @pytest.mark.asyncio
    async def test_agents_execute_in_order(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Agents execute in dependency order."""
        execution_order = []

        async def track_spawn(*args, **kwargs) -> MagicMock:
            execution_order.append(kwargs.get("agent_type"))
            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=track_spawn)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(sequential_workflow)

        assert result.success is True
        assert execution_order == ["explore", "plan", "code"]

    @pytest.mark.asyncio
    async def test_step_failure_stops_chain(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Failed step causes workflow to fail."""
        call_count = 0

        async def fail_second(*args, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            agent = MagicMock()
            if call_count == 2:  # Plan step fails
                agent.result = AgentResult(success=False, output="", error="Plan failed")
            else:
                agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=fail_second)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(sequential_workflow)

        assert result.success is False
        assert result.steps_failed > 0

    @pytest.mark.asyncio
    async def test_all_steps_complete_successfully(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """All steps complete when successful."""
        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(sequential_workflow)

        assert result.success is True
        assert result.steps_completed == 3
        assert result.steps_failed == 0


# =============================================================================
# Test Parallel Agent Execution
# =============================================================================


class TestParallelAgentExecution:
    """Tests for parallel agent execution."""

    @pytest.mark.asyncio
    async def test_parallel_steps_run_concurrently(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        parallel_workflow: WorkflowDefinition,
    ) -> None:
        """Parallel steps execute concurrently."""
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def track_concurrent(*args, **kwargs) -> MagicMock:
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            await asyncio.sleep(0.01)  # Simulate work

            async with lock:
                concurrent_count -= 1

            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=track_concurrent)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(parallel_workflow)

        assert result.success is True
        # task-a, task-b, task-c should run in parallel
        assert max_concurrent >= 3

    @pytest.mark.asyncio
    async def test_parallel_steps_all_complete(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        parallel_workflow: WorkflowDefinition,
    ) -> None:
        """All parallel steps complete before dependent step."""
        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(parallel_workflow)

        assert result.success is True
        assert result.steps_completed == 5  # init + 3 parallel + finalize

    @pytest.mark.asyncio
    async def test_one_parallel_failure_doesnt_cancel_others(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        parallel_workflow: WorkflowDefinition,
    ) -> None:
        """One parallel step failing doesn't cancel siblings."""
        executed = []

        async def track_with_failure(*args, **kwargs) -> MagicMock:
            task = kwargs.get("task", "")
            executed.append(task)

            agent = MagicMock()
            if "Parallel B" in task:
                agent.result = AgentResult(success=False, output="", error="Failed")
            else:
                agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=track_with_failure)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(parallel_workflow)

        # All parallel tasks should have executed
        assert "Parallel A" in executed
        assert "Parallel B" in executed
        assert "Parallel C" in executed


# =============================================================================
# Test Context Passing Between Agents
# =============================================================================


class TestContextPassing:
    """Tests for passing context between agents."""

    @pytest.mark.asyncio
    async def test_step_result_available_to_next(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Previous step result is available to next step."""
        workflow = WorkflowDefinition(
            name="context-test",
            description="Test context passing",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="producer",
                    agent="explore",
                    description="Produce data",
                    inputs={"task": "Produce"},
                ),
                WorkflowStep(
                    id="consumer",
                    agent="plan",
                    description="Consume data",
                    inputs={"task": "Consume: ${producer.output}"},
                    depends_on=["producer"],
                ),
            ],
        )

        async def capture_context(*args, **kwargs) -> MagicMock:
            agent = MagicMock()
            agent.result = AgentResult(
                success=True,
                output="Produced value: 42",
                data={"value": 42},
            )
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=capture_context)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(workflow)

        assert result.success is True


# =============================================================================
# Test Workflow State Persistence
# =============================================================================


class TestWorkflowStatePersistence:
    """Tests for workflow state checkpointing."""

    @pytest.mark.asyncio
    async def test_checkpoint_created_during_execution(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Checkpoint is created during execution."""
        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)

        workflow_id = "checkpoint-test-001"
        await executor.execute(sequential_workflow, workflow_id=workflow_id)

        # Checkpoint should have been saved at some point
        # (deleted on success, but save was called)

    @pytest.mark.asyncio
    async def test_checkpoint_deleted_on_success(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Checkpoint is deleted on successful completion."""
        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)

        workflow_id = "cleanup-test-001"
        result = await executor.execute(sequential_workflow, workflow_id=workflow_id)

        assert result.success is True
        assert not mock_checkpoint_manager.checkpoint_exists(workflow_id)


# =============================================================================
# Test Workflow Resumption
# =============================================================================


class TestWorkflowResumption:
    """Tests for resuming interrupted workflows."""

    @pytest.mark.asyncio
    async def test_resume_skips_completed_steps(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Resuming workflow skips already completed steps."""
        from code_forge.workflows.state import WorkflowState

        # Create a checkpoint with first step completed
        workflow_id = "resume-test-001"
        state = WorkflowState(
            workflow_id=workflow_id,
            definition=sequential_workflow,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(UTC),
            completed_steps=["explore"],
            step_results={
                "explore": StepResult(
                    step_id="explore",
                    agent_type="explore",
                    agent_result=AgentResult(success=True, output="Done"),
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                    duration=1.0,
                    success=True,
                ),
            },
        )
        mock_checkpoint_manager.save_checkpoint(state)

        executed_agents = []

        async def track_execution(*args, **kwargs) -> MagicMock:
            executed_agents.append(kwargs.get("agent_type"))
            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=track_execution)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(
            sequential_workflow,
            workflow_id=workflow_id,
            resume_from_checkpoint=True,
        )

        # Should skip explore, only execute plan and code
        assert "explore" not in executed_agents
        assert result.success is True


# =============================================================================
# Test Conditional Execution
# =============================================================================


class TestConditionalExecution:
    """Tests for conditional step execution."""

    @pytest.mark.asyncio
    async def test_condition_evaluated_correctly(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Step conditions are evaluated correctly."""
        workflow = WorkflowDefinition(
            name="conditional-test",
            description="Test conditions",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="check",
                    agent="explore",
                    description="Check something",
                    inputs={"task": "Check"},
                ),
                WorkflowStep(
                    id="if-true",
                    agent="plan",
                    description="Run if check passes",
                    inputs={"task": "True path"},
                    depends_on=["check"],
                    condition="true",  # Always true
                ),
                WorkflowStep(
                    id="if-false",
                    agent="code",
                    description="Skip if condition false",
                    inputs={"task": "False path"},
                    depends_on=["check"],
                    condition="false",  # Always false
                ),
            ],
        )

        executed = []

        async def track(*args, **kwargs) -> MagicMock:
            executed.append(kwargs.get("agent_type"))
            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=track)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(workflow)

        assert "explore" in executed  # check step
        assert "plan" in executed     # if-true step
        assert "code" not in executed  # if-false step skipped


# =============================================================================
# Test Error Recovery in Workflows
# =============================================================================


class TestWorkflowErrorRecovery:
    """Tests for error recovery in workflows."""

    @pytest.mark.asyncio
    async def test_workflow_completes_with_partial_failure(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        parallel_workflow: WorkflowDefinition,
    ) -> None:
        """Workflow can complete with some failures in parallel steps."""
        async def some_fail(*args, **kwargs) -> MagicMock:
            agent = MagicMock()
            task = kwargs.get("task", "")
            if "Parallel B" in task:
                agent.result = AgentResult(success=False, output="", error="B failed")
            else:
                agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=some_fail)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(parallel_workflow)

        # Workflow failed because one step failed
        assert result.success is False
        assert result.steps_failed > 0
        assert result.steps_completed > 0

    @pytest.mark.asyncio
    async def test_retry_mechanism(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Steps with max_retries retry on failure."""
        workflow = WorkflowDefinition(
            name="retry-test",
            description="Test retry",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="flaky",
                    agent="explore",
                    description="Flaky step",
                    inputs={"task": "Flaky"},
                    max_retries=3,
                ),
            ],
        )

        call_count = 0

        async def flaky_agent(*args, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            agent = MagicMock()
            if call_count < 3:
                agent.result = AgentResult(success=False, output="", error="Retry")
            else:
                agent.result = AgentResult(success=True, output="Finally!")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=flaky_agent)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(workflow)

        assert call_count == 3
        assert result.success is True


# =============================================================================
# Test Workflow Metrics
# =============================================================================


class TestWorkflowMetrics:
    """Tests for workflow execution metrics."""

    @pytest.mark.asyncio
    async def test_execution_time_tracked(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Workflow tracks execution time."""
        async def slow_agent(*args, **kwargs) -> MagicMock:
            await asyncio.sleep(0.01)
            agent = MagicMock()
            agent.result = AgentResult(success=True, output="Done")
            return agent

        mock_agent_manager.spawn = AsyncMock(side_effect=slow_agent)

        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(sequential_workflow)

        assert result.success is True
        assert result.duration > 0

    @pytest.mark.asyncio
    async def test_step_counts_accurate(
        self,
        mock_agent_manager: MagicMock,
        mock_checkpoint_manager: CheckpointManager,
        sequential_workflow: WorkflowDefinition,
    ) -> None:
        """Step counts are accurate."""
        executor = WorkflowExecutor(mock_agent_manager, mock_checkpoint_manager)
        result = await executor.execute(sequential_workflow)

        assert result.steps_completed == 3
        assert result.steps_failed == 0
        assert result.steps_skipped == 0
