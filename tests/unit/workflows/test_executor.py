"""Unit tests for workflow execution engine."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from code_forge.agents.base import Agent, AgentConfig, AgentContext, AgentState
from code_forge.agents.manager import AgentManager
from code_forge.agents.result import AgentResult
from code_forge.workflows.executor import StepExecutor, WorkflowExecutor
from code_forge.workflows.models import WorkflowDefinition, WorkflowStep
from code_forge.workflows.state import CheckpointManager


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, result: AgentResult):
        self.id = uuid4()
        self.result = result
        self.state = AgentState.COMPLETED if result.success else AgentState.FAILED


class MockAgentManager:
    """Mock agent manager for testing."""

    def __init__(self):
        self.spawned_agents: list[tuple[str, str]] = []
        self.results: dict[str, AgentResult] = {}

    def set_result(self, agent_type: str, result: AgentResult):
        """Set the result for a specific agent type."""
        self.results[agent_type] = result

    async def spawn(
        self,
        agent_type: str,
        task: str,
        config=None,
        context=None,
        wait=False,
    ) -> MockAgent:
        """Spawn a mock agent."""
        self.spawned_agents.append((agent_type, task))
        result = self.results.get(agent_type, AgentResult.ok("Default success"))
        return MockAgent(result)


class TestStepExecutor:
    """Tests for StepExecutor class."""

    @pytest.fixture
    def agent_manager(self):
        """Creates mock agent manager."""
        return MockAgentManager()

    @pytest.fixture
    def executor(self, agent_manager):
        """Creates step executor."""
        return StepExecutor(agent_manager)

    @pytest.mark.asyncio
    async def test_execute_successful_step(self, executor, agent_manager):
        """Given successful agent execution, returns success result"""
        step = WorkflowStep(
            id="step1",
            agent="plan",
            description="Planning step",
            inputs={"task": "Create a plan"},
        )

        agent_manager.set_result("plan", AgentResult.ok("Plan created", data={"plan": "test"}))

        result = await executor.execute(step, {})

        assert result.step_id == "step1"
        assert result.agent_type == "plan"
        assert result.success is True
        assert result.error is None
        assert len(agent_manager.spawned_agents) == 1
        assert agent_manager.spawned_agents[0] == ("plan", "Create a plan")

    @pytest.mark.asyncio
    async def test_execute_failed_step(self, executor, agent_manager):
        """Given failed agent execution, returns failure result"""
        step = WorkflowStep(
            id="step1",
            agent="plan",
            description="Planning step",
        )

        agent_manager.set_result("plan", AgentResult.fail("Plan failed"))

        result = await executor.execute(step, {})

        assert result.step_id == "step1"
        assert result.success is False
        assert result.error == "Plan failed"

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, executor, agent_manager):
        """Given failed step with retries, retries execution"""
        step = WorkflowStep(
            id="step1",
            agent="plan",
            description="Planning step",
            max_retries=2,
        )

        # Fail first two attempts, succeed on third
        call_count = 0

        async def spawn_with_retries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return MockAgent(AgentResult.fail("Temporary failure"))
            return MockAgent(AgentResult.ok("Success after retries"))

        agent_manager.spawn = spawn_with_retries

        result = await executor.execute(step, {})

        assert call_count == 3  # Original + 2 retries
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_retry_all_fail(self, executor, agent_manager):
        """Given failing step with retries, returns failure after all attempts"""
        step = WorkflowStep(
            id="step1",
            agent="plan",
            description="Planning step",
            max_retries=2,
        )

        agent_manager.set_result("plan", AgentResult.fail("Persistent failure"))

        result = await executor.execute(step, {})

        assert result.success is False
        assert len(agent_manager.spawned_agents) == 3  # Original + 2 retries

    @pytest.mark.asyncio
    async def test_execute_uses_default_task_from_description(self, executor, agent_manager):
        """Given step without task input, uses description as task"""
        step = WorkflowStep(
            id="step1",
            agent="plan",
            description="Planning step",
            inputs={},  # No task specified
        )

        agent_manager.set_result("plan", AgentResult.ok("Success"))

        await executor.execute(step, {})

        assert agent_manager.spawned_agents[0] == ("plan", "Planning step")


class TestWorkflowExecutor:
    """Tests for WorkflowExecutor class."""

    @pytest.fixture
    def agent_manager(self):
        """Creates mock agent manager."""
        return MockAgentManager()

    @pytest.fixture
    def checkpoint_dir(self, tmp_path):
        """Creates temporary checkpoint directory."""
        return tmp_path / "checkpoints"

    @pytest.fixture
    def checkpoint_manager(self, checkpoint_dir):
        """Creates checkpoint manager."""
        return CheckpointManager(checkpoint_dir)

    @pytest.fixture
    def executor(self, agent_manager, checkpoint_manager):
        """Creates workflow executor."""
        return WorkflowExecutor(agent_manager, checkpoint_manager)

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self, executor, agent_manager):
        """Given simple workflow, executes steps in order"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
                WorkflowStep(id="step2", agent="review", description="Review"),
            ],
        )

        agent_manager.set_result("plan", AgentResult.ok("Plan done"))
        agent_manager.set_result("review", AgentResult.ok("Review done"))

        result = await executor.execute(definition, workflow_id="test-123")

        assert result.success is True
        assert result.steps_completed == 2
        assert result.steps_failed == 0
        assert len(agent_manager.spawned_agents) == 2

    @pytest.mark.asyncio
    async def test_execute_workflow_with_dependencies(self, executor, agent_manager):
        """Given workflow with dependencies, respects execution order"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
                WorkflowStep(
                    id="step2",
                    agent="review",
                    description="Review",
                    depends_on=["step1"],
                ),
            ],
        )

        agent_manager.set_result("plan", AgentResult.ok("Plan done"))
        agent_manager.set_result("review", AgentResult.ok("Review done"))

        result = await executor.execute(definition, workflow_id="test-123")

        assert result.success is True
        # Step1 should execute before step2
        assert agent_manager.spawned_agents[0][0] == "plan"
        assert agent_manager.spawned_agents[1][0] == "review"

    @pytest.mark.asyncio
    async def test_execute_workflow_with_parallel_steps(self, executor, agent_manager):
        """Given workflow with parallel steps, executes concurrently"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
                WorkflowStep(
                    id="step2",
                    agent="review",
                    description="Review",
                    depends_on=["step1"],
                ),
                WorkflowStep(
                    id="step3",
                    agent="test",
                    description="Test",
                    depends_on=["step1"],
                    parallel_with=["step2"],
                ),
            ],
        )

        agent_manager.set_result("plan", AgentResult.ok("Plan done"))
        agent_manager.set_result("review", AgentResult.ok("Review done"))
        agent_manager.set_result("test", AgentResult.ok("Test done"))

        result = await executor.execute(definition, workflow_id="test-123")

        assert result.success is True
        assert result.steps_completed == 3

    @pytest.mark.asyncio
    async def test_execute_workflow_with_condition(self, executor, agent_manager):
        """Given workflow with condition, skips steps when condition not met"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
                WorkflowStep(
                    id="step2",
                    agent="review",
                    description="Review",
                    depends_on=["step1"],
                    condition="step1.success",
                ),
            ],
        )

        # Step1 fails, so step2 should be skipped
        agent_manager.set_result("plan", AgentResult.fail("Plan failed"))

        result = await executor.execute(definition, workflow_id="test-123")

        assert result.success is False
        assert result.steps_failed == 1
        assert result.steps_skipped == 1  # step2 skipped due to condition

    @pytest.mark.asyncio
    async def test_execute_workflow_saves_checkpoint(self, executor, agent_manager, checkpoint_manager):
        """Given workflow execution, saves checkpoints"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
            ],
        )

        agent_manager.set_result("plan", AgentResult.ok("Plan done"))

        await executor.execute(definition, workflow_id="test-123")

        # Checkpoint should exist during execution but be deleted on success
        assert not checkpoint_manager.checkpoint_exists("test-123")

    @pytest.mark.asyncio
    async def test_execute_workflow_failure_saves_checkpoint(self, executor, agent_manager, checkpoint_manager):
        """Given workflow failure, saves checkpoint for resume"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
            ],
        )

        agent_manager.set_result("plan", AgentResult.fail("Plan failed"))

        result = await executor.execute(definition, workflow_id="test-123")

        # Workflow should fail but not raise
        assert result.success is False

        # Checkpoint should exist for resume
        assert checkpoint_manager.checkpoint_exists("test-123")

    @pytest.mark.asyncio
    async def test_execute_workflow_resume_from_checkpoint(self, executor, agent_manager, checkpoint_manager):
        """Given saved checkpoint, resumes workflow execution"""
        definition = WorkflowDefinition(
            name="test-workflow",
            description="Test workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="step1", agent="plan", description="Plan"),
                WorkflowStep(
                    id="step2",
                    agent="review",
                    description="Review",
                    depends_on=["step1"],
                ),
            ],
        )

        # First execution: step1 succeeds, step2 fails
        agent_manager.set_result("plan", AgentResult.ok("Plan done"))
        agent_manager.set_result("review", AgentResult.fail("Review failed"))

        result = await executor.execute(definition, workflow_id="test-123")
        assert result.success is False

        # Clear spawned agents
        agent_manager.spawned_agents.clear()

        # Second execution: resume and fix step2
        agent_manager.set_result("review", AgentResult.ok("Review done"))

        result = await executor.execute(
            definition,
            workflow_id="test-123",
            resume_from_checkpoint=True,
        )

        # Should only re-execute step2 (step1 was already completed)
        assert result.success is True
        assert len(agent_manager.spawned_agents) == 1  # Only step2
        assert agent_manager.spawned_agents[0][0] == "review"
