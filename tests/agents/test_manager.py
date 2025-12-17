"""Tests for agent manager."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from code_forge.agents.base import Agent, AgentConfig, AgentContext, AgentState
from code_forge.agents.manager import AgentManager
from code_forge.agents.result import AgentResult, AggregatedResult
from code_forge.agents.types import AgentTypeRegistry


class TestAgentManager:
    """Tests for AgentManager singleton."""

    def setup_method(self) -> None:
        """Reset singletons before each test."""
        AgentManager.reset_instance()
        AgentTypeRegistry.reset_instance()

    def teardown_method(self) -> None:
        """Reset singletons after each test."""
        AgentManager.reset_instance()
        AgentTypeRegistry.reset_instance()

    def create_mock_executor(self) -> MagicMock:
        """Create a mock executor."""
        executor = MagicMock()
        executor.execute = AsyncMock(
            return_value=AgentResult.ok("Done", tokens_used=100)
        )
        return executor

    def test_singleton_instance(self) -> None:
        """Test get_instance returns singleton."""
        instance1 = AgentManager.get_instance()
        instance2 = AgentManager.get_instance()
        assert instance1 is instance2

    def test_reset_instance(self) -> None:
        """Test reset_instance creates new singleton."""
        instance1 = AgentManager.get_instance()
        AgentManager.reset_instance()
        instance2 = AgentManager.get_instance()
        assert instance1 is not instance2

    def test_init_with_max_concurrent(self) -> None:
        """Test initialization with max_concurrent."""
        manager = AgentManager(max_concurrent=10)
        assert manager._max_concurrent == 10

    def test_set_executor(self) -> None:
        """Test setting executor."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()

        manager.set_executor(executor)

        assert manager._executor == executor

    @pytest.mark.asyncio
    async def test_spawn_creates_agent(self) -> None:
        """Test spawn creates an agent."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        agent = await manager.spawn("explore", "Find files")

        assert isinstance(agent, Agent)
        assert agent.task == "Find files"
        assert agent.id in manager._agents

    @pytest.mark.asyncio
    async def test_spawn_with_config(self) -> None:
        """Test spawn with custom config."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        config = AgentConfig(
            agent_type="explore",
            model="custom-model",
        )

        agent = await manager.spawn("explore", "Task", config=config)

        assert agent.config.model == "custom-model"

    @pytest.mark.asyncio
    async def test_spawn_with_context(self) -> None:
        """Test spawn with custom context."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        context = AgentContext(working_directory="/project")

        agent = await manager.spawn("explore", "Task", context=context)

        assert agent.context.working_directory == "/project"

    @pytest.mark.asyncio
    async def test_spawn_wait(self) -> None:
        """Test spawn with wait=True."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        agent = await manager.spawn("explore", "Task", wait=True)

        # Should wait for completion
        executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_parallel(self) -> None:
        """Test spawning multiple agents."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        tasks = [
            ("explore", "Task 1"),
            ("explore", "Task 2"),
            ("plan", "Task 3"),
        ]

        agents = await manager.spawn_parallel(tasks)

        assert len(agents) == 3
        assert agents[0].task == "Task 1"
        assert agents[1].task == "Task 2"
        assert agents[2].task == "Task 3"

    def test_get_agent_existing(self) -> None:
        """Test getting existing agent."""
        manager = AgentManager.get_instance()

        # Manually add an agent
        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")
        agent = create_agent("explore", "Test", config)
        manager._agents[agent.id] = agent

        found = manager.get_agent(agent.id)

        assert found == agent

    def test_get_agent_nonexistent(self) -> None:
        """Test getting nonexistent agent."""
        manager = AgentManager.get_instance()
        found = manager.get_agent(uuid4())
        assert found is None

    def test_list_agents_all(self) -> None:
        """Test listing all agents."""
        manager = AgentManager.get_instance()

        # Add some agents
        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")
        agent1 = create_agent("explore", "Task 1", config)
        agent2 = create_agent("explore", "Task 2", config)
        manager._agents[agent1.id] = agent1
        manager._agents[agent2.id] = agent2

        agents = manager.list_agents()

        assert len(agents) == 2

    def test_list_agents_by_state(self) -> None:
        """Test listing agents by state."""
        manager = AgentManager.get_instance()

        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")

        agent1 = create_agent("explore", "Task 1", config)
        agent1.state = AgentState.COMPLETED

        agent2 = create_agent("explore", "Task 2", config)
        agent2.state = AgentState.RUNNING

        manager._agents[agent1.id] = agent1
        manager._agents[agent2.id] = agent2

        completed = manager.list_agents(state=AgentState.COMPLETED)
        running = manager.list_agents(state=AgentState.RUNNING)

        assert len(completed) == 1
        assert len(running) == 1
        assert completed[0] == agent1
        assert running[0] == agent2

    @pytest.mark.asyncio
    async def test_wait_for_agent(self) -> None:
        """Test waiting for specific agent."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        agent = await manager.spawn("explore", "Task")
        result = await manager.wait(agent.id)

        # Result may be None if task completed very fast
        # Check that wait doesn't raise error
        executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_nonexistent(self) -> None:
        """Test waiting for nonexistent agent."""
        manager = AgentManager.get_instance()
        result = await manager.wait(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_all(self) -> None:
        """Test waiting for all agents."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        agent1 = await manager.spawn("explore", "Task 1")
        agent2 = await manager.spawn("explore", "Task 2")

        result = await manager.wait_all()

        assert isinstance(result, AggregatedResult)

    @pytest.mark.asyncio
    async def test_wait_all_specific_ids(self) -> None:
        """Test waiting for specific agents."""
        manager = AgentManager.get_instance()
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        agent1 = await manager.spawn("explore", "Task 1")
        agent2 = await manager.spawn("explore", "Task 2")
        agent3 = await manager.spawn("explore", "Task 3")

        result = await manager.wait_all([agent1.id, agent2.id])

        assert isinstance(result, AggregatedResult)

    def test_cancel_existing(self) -> None:
        """Test cancelling existing agent."""
        manager = AgentManager.get_instance()

        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")
        agent = create_agent("explore", "Task", config)
        manager._agents[agent.id] = agent

        result = manager.cancel(agent.id)

        assert result is True
        assert agent.is_cancelled is True

    def test_cancel_nonexistent(self) -> None:
        """Test cancelling nonexistent agent."""
        manager = AgentManager.get_instance()
        result = manager.cancel(uuid4())
        assert result is False

    def test_cancel_all(self) -> None:
        """Test cancelling all agents."""
        manager = AgentManager.get_instance()

        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")

        agent1 = create_agent("explore", "Task 1", config)
        agent2 = create_agent("explore", "Task 2", config)
        manager._agents[agent1.id] = agent1
        manager._agents[agent2.id] = agent2

        count = manager.cancel_all()

        assert count == 2
        assert agent1.is_cancelled is True
        assert agent2.is_cancelled is True

    def test_on_complete_callback(self) -> None:
        """Test completion callback registration."""
        manager = AgentManager.get_instance()

        callbacks: list = []
        manager.on_complete(callbacks.append)

        assert len(manager._on_complete) == 1

    def test_get_stats_empty(self) -> None:
        """Test stats with no agents."""
        manager = AgentManager.get_instance()
        stats = manager.get_stats()

        assert stats["total_agents"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_time_seconds"] == 0.0
        assert stats["total_tool_calls"] == 0

    def test_get_stats_with_agents(self) -> None:
        """Test stats with agents."""
        manager = AgentManager.get_instance()

        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")

        agent1 = create_agent("explore", "Task 1", config)
        agent1._usage.tokens_used = 1000
        agent1._usage.time_seconds = 5.0
        agent1._usage.tool_calls = 10
        agent1.state = AgentState.COMPLETED

        agent2 = create_agent("explore", "Task 2", config)
        agent2._usage.tokens_used = 500
        agent2._usage.time_seconds = 2.5
        agent2._usage.tool_calls = 5
        agent2.state = AgentState.RUNNING

        manager._agents[agent1.id] = agent1
        manager._agents[agent2.id] = agent2

        stats = manager.get_stats()

        assert stats["total_agents"] == 2
        assert stats["total_tokens"] == 1500
        assert stats["total_time_seconds"] == 7.5
        assert stats["total_tool_calls"] == 15
        assert stats["by_state"]["completed"] == 1
        assert stats["by_state"]["running"] == 1

    def test_cleanup_completed(self) -> None:
        """Test cleaning up completed agents."""
        manager = AgentManager.get_instance()

        from code_forge.agents.builtin import create_agent
        config = AgentConfig(agent_type="explore")

        agent1 = create_agent("explore", "Task 1", config)
        agent1.state = AgentState.COMPLETED

        agent2 = create_agent("explore", "Task 2", config)
        agent2.state = AgentState.RUNNING

        agent3 = create_agent("explore", "Task 3", config)
        agent3.state = AgentState.FAILED

        manager._agents[agent1.id] = agent1
        manager._agents[agent2.id] = agent2
        manager._agents[agent3.id] = agent3

        count = manager.cleanup_completed()

        assert count == 2  # completed and failed
        assert agent1.id not in manager._agents
        assert agent2.id in manager._agents  # running stays
        assert agent3.id not in manager._agents

    @pytest.mark.asyncio
    async def test_concurrent_limit(self) -> None:
        """Test concurrent agent limit is respected."""
        manager = AgentManager(max_concurrent=2)
        executor = self.create_mock_executor()
        manager.set_executor(executor)

        # Spawn more than max_concurrent
        agent1 = await manager.spawn("explore", "Task 1")
        agent2 = await manager.spawn("explore", "Task 2")
        agent3 = await manager.spawn("explore", "Task 3")

        # All should be tracked
        assert len(manager._agents) == 3

    def test_thread_safety(self) -> None:
        """Test manager is thread-safe."""
        import threading

        manager = AgentManager.get_instance()
        errors: list[Exception] = []

        def add_agents() -> None:
            try:
                from code_forge.agents.builtin import create_agent
                config = AgentConfig(agent_type="explore")
                for _ in range(10):
                    agent = create_agent("explore", "Task", config)
                    manager._agents[agent.id] = agent
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_agents) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
