"""
Agent lifecycle manager.

Handles spawning, tracking, and coordinating agents.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from uuid import UUID

from .base import Agent, AgentConfig, AgentContext, AgentState
from .result import AgentResult, AggregatedResult
from .types import AgentTypeRegistry

if TYPE_CHECKING:
    from .executor import AgentExecutor


logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent lifecycle.

    Singleton that handles spawning, tracking, and
    coordinating agents.

    Thread-safe implementation using locks.
    """

    _instance: AgentManager | None = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        executor: AgentExecutor | None = None,
        max_concurrent: int = 5,
    ) -> None:
        """Initialize manager.

        Args:
            executor: Agent executor (created lazily if None).
            max_concurrent: Maximum concurrent agents.
        """
        self._executor = executor
        self._max_concurrent = max_concurrent
        self._agents: dict[UUID, Agent] = {}
        self._tasks: dict[UUID, asyncio.Task[None]] = {}
        self._lock = threading.RLock()
        # Note: Semaphore is created lazily to avoid issues when
        # __init__ is called outside of an async context
        self._semaphore: asyncio.Semaphore | None = None
        self._on_complete: list[Callable[[Agent], None]] = []
        self._type_registry = AgentTypeRegistry.get_instance()

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the concurrency semaphore.

        Creates the semaphore lazily to avoid issues when the manager
        is instantiated outside of an async context.

        Returns:
            The asyncio semaphore for concurrency control.
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    @classmethod
    def get_instance(cls, **kwargs: Any) -> AgentManager:
        """Get singleton instance.

        Args:
            **kwargs: Arguments to pass to constructor if creating new instance.

        Returns:
            The singleton AgentManager instance.
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(**kwargs)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._instance_lock:
            if cls._instance:
                cls._instance.cancel_all()
            cls._instance = None

    def set_executor(self, executor: AgentExecutor) -> None:
        """Set the agent executor.

        Args:
            executor: The executor to use for running agents.
        """
        with self._lock:
            self._executor = executor

    async def spawn(
        self,
        agent_type: str,
        task: str,
        config: AgentConfig | None = None,
        context: AgentContext | None = None,
        wait: bool = False,
    ) -> Agent:
        """Spawn a new agent.

        Args:
            agent_type: Type of agent to spawn.
            task: Task description.
            config: Optional config override.
            context: Optional execution context.
            wait: If True, wait for completion.

        Returns:
            The spawned agent.

        Raises:
            RuntimeError: If no executor is configured.
        """
        # Build config from type if not provided
        if config is None:
            config = AgentConfig.for_type(agent_type)

        # Create agent instance
        agent = self._create_agent(agent_type, task, config, context)

        with self._lock:
            self._agents[agent.id] = agent

        # Start execution
        task_coro = self._run_agent(agent)
        async_task = asyncio.create_task(task_coro)

        with self._lock:
            self._tasks[agent.id] = async_task

        logger.info(f"Spawned agent {agent.id} ({agent_type})")

        if wait:
            await self.wait(agent.id)

        return agent

    async def spawn_parallel(
        self,
        tasks: list[tuple[str, str]],
    ) -> list[Agent]:
        """Spawn multiple agents in parallel.

        Args:
            tasks: List of (agent_type, task) tuples.

        Returns:
            List of spawned agents.
        """
        agents = []
        for agent_type, task in tasks:
            agent = await self.spawn(agent_type, task, wait=False)
            agents.append(agent)
        return agents

    def _create_agent(
        self,
        agent_type: str,
        task: str,
        config: AgentConfig,
        context: AgentContext | None,
    ) -> Agent:
        """Create an agent instance.

        Args:
            agent_type: Type identifier.
            task: Task description.
            config: Agent config.
            context: Execution context.

        Returns:
            Agent instance.
        """
        from .builtin import create_agent

        return create_agent(
            agent_type=agent_type,
            task=task,
            config=config,
            context=context,
        )

    async def _run_agent(self, agent: Agent) -> None:
        """Run an agent with semaphore control.

        Args:
            agent: Agent to run.
        """
        async with self._get_semaphore():
            if agent.is_cancelled:
                return

            try:
                if self._executor is None:
                    raise RuntimeError("No executor configured")

                await self._executor.execute(agent)

                # Notify completion callbacks
                for callback in self._on_complete:
                    try:
                        callback(agent)
                    except Exception as e:
                        logger.error(f"Completion callback error: {e}")

            except Exception as e:
                logger.error(f"Agent {agent.id} failed: {e}")

    def get_agent(self, agent_id: UUID) -> Agent | None:
        """Get agent by ID.

        Args:
            agent_id: ID of agent to retrieve.

        Returns:
            Agent if found, None otherwise.
        """
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(
        self,
        state: AgentState | None = None,
    ) -> list[Agent]:
        """List agents, optionally filtered by state.

        Args:
            state: Filter by state (None = all).

        Returns:
            List of matching agents.
        """
        with self._lock:
            agents = list(self._agents.values())

        if state is not None:
            agents = [a for a in agents if a.state == state]
        return agents

    async def wait(self, agent_id: UUID) -> AgentResult | None:
        """Wait for specific agent to complete.

        Args:
            agent_id: ID of agent to wait for.

        Returns:
            Agent result, or None if not found.
        """
        with self._lock:
            task = self._tasks.get(agent_id)

        if task is None:
            with self._lock:
                agent = self._agents.get(agent_id)
            return agent.result if agent else None

        with contextlib.suppress(asyncio.CancelledError):
            await task

        with self._lock:
            agent = self._agents.get(agent_id)
        return agent.result if agent else None

    async def wait_all(
        self,
        agent_ids: list[UUID] | None = None,
    ) -> AggregatedResult:
        """Wait for all specified agents.

        Args:
            agent_ids: IDs to wait for (None = all).

        Returns:
            Aggregated results.
        """
        # Capture all data atomically to prevent race conditions
        # where agent_ids could be modified by caller during await
        with self._lock:
            if agent_ids is None:
                tasks = list(self._tasks.values())
                ids_to_wait = list(self._agents.keys())
            else:
                # Make a copy to prevent caller modifications affecting results
                ids_to_wait = list(agent_ids)
                tasks = [
                    self._tasks[aid]
                    for aid in ids_to_wait
                    if aid in self._tasks
                ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        results = []
        with self._lock:
            for aid in ids_to_wait:
                agent = self._agents.get(aid)
                if agent and agent.result:
                    results.append(agent.result)

        return AggregatedResult(results=results)

    def cancel(self, agent_id: UUID) -> bool:
        """Cancel a running agent.

        Args:
            agent_id: ID of agent to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        with self._lock:
            agent = self._agents.get(agent_id)

        if agent is None:
            return False

        agent.cancel()

        with self._lock:
            task = self._tasks.get(agent_id)

        if task and not task.done():
            task.cancel()

        logger.info(f"Cancelled agent {agent_id}")
        return True

    def cancel_all(self) -> int:
        """Cancel all running agents.

        Returns:
            Number of agents cancelled.
        """
        count = 0
        with self._lock:
            agent_ids = list(self._agents.keys())

        for agent_id in agent_ids:
            if self.cancel(agent_id):
                count += 1
        return count

    def on_complete(self, callback: Callable[[Agent], None]) -> None:
        """Register completion callback.

        Args:
            callback: Function called when any agent completes.
        """
        with self._lock:
            self._on_complete.append(callback)

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics.

        Returns:
            Statistics dictionary.
        """
        with self._lock:
            agents = list(self._agents.values())

        by_state: dict[str, int] = {}
        for state in AgentState:
            by_state[state.value] = len([
                a for a in agents if a.state == state
            ])

        total_tokens = sum(a.usage.tokens_used for a in agents)
        total_time = sum(a.usage.time_seconds for a in agents)
        total_tool_calls = sum(a.usage.tool_calls for a in agents)

        return {
            "total_agents": len(agents),
            "by_state": by_state,
            "total_tokens": total_tokens,
            "total_time_seconds": total_time,
            "total_tool_calls": total_tool_calls,
            "max_concurrent": self._max_concurrent,
        }

    def cleanup_completed(self) -> int:
        """Remove completed agents from tracking.

        Returns:
            Number of agents cleaned up.
        """
        with self._lock:
            to_remove = [
                aid for aid, agent in self._agents.items()
                if agent.is_complete
            ]

            for aid in to_remove:
                del self._agents[aid]
                self._tasks.pop(aid, None)

        return len(to_remove)
