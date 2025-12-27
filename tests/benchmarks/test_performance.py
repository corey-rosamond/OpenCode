"""Performance benchmarks for Code-Forge core operations.

These tests verify that critical operations complete within acceptable time bounds.
Run with: pytest tests/benchmarks/ -v --tb=short

Performance thresholds are intentionally generous to avoid flaky tests while
still catching significant regressions.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from code_forge.agents.base import Agent, AgentConfig, AgentContext
from code_forge.agents.builtin import create_agent, AGENT_CLASSES
from code_forge.agents.types import AgentTypeRegistry
from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.registry import ToolRegistry
from code_forge.tools.executor import ToolExecutor


# =============================================================================
# Performance Test Helpers
# =============================================================================


def measure_time(func, *args, **kwargs):
    """Measure execution time of a function."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, end - start


async def measure_time_async(coro):
    """Measure execution time of a coroutine."""
    start = time.perf_counter()
    result = await coro
    end = time.perf_counter()
    return result, end - start


# =============================================================================
# Tool Registry Benchmarks
# =============================================================================


class DummyTool(BaseTool):
    """Minimal tool for benchmarking."""

    def __init__(self, name: str = "Dummy"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A dummy tool for testing"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="Input value",
                required=True,
            )
        ]

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(kwargs.get("input", ""))


class TestToolRegistryPerformance:
    """Benchmarks for tool registry operations."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        ToolRegistry.reset()
        yield
        ToolRegistry.reset()

    def test_register_100_tools_under_100ms(self) -> None:
        """Test that registering 100 tools completes quickly."""
        registry = ToolRegistry()

        start = time.perf_counter()
        for i in range(100):
            registry.register(DummyTool(f"Tool{i}"))
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"Registration took {elapsed:.3f}s, expected < 0.1s"
        assert len(registry.list_names()) == 100

    def test_tool_lookup_under_1ms(self) -> None:
        """Test that tool lookup is fast."""
        registry = ToolRegistry()
        for i in range(50):
            registry.register(DummyTool(f"Tool{i}"))

        # Warm up
        registry.get("Tool25")

        # Measure
        _, elapsed = measure_time(registry.get, "Tool25")

        assert elapsed < 0.001, f"Lookup took {elapsed*1000:.3f}ms, expected < 1ms"

    def test_schema_generation_under_50ms(self) -> None:
        """Test that generating schemas for 50 tools is fast."""
        registry = ToolRegistry()
        for i in range(50):
            registry.register(DummyTool(f"Tool{i}"))

        executor = ToolExecutor(registry)

        _, elapsed = measure_time(executor.get_all_schemas, "openai")

        assert elapsed < 0.05, f"Schema generation took {elapsed*1000:.1f}ms, expected < 50ms"

    def test_category_filtering_under_10ms(self) -> None:
        """Test that filtering by category is fast."""
        registry = ToolRegistry()
        for i in range(100):
            registry.register(DummyTool(f"Tool{i}"))

        _, elapsed = measure_time(registry.list_by_category, ToolCategory.OTHER)

        assert elapsed < 0.01, f"Filtering took {elapsed*1000:.1f}ms, expected < 10ms"


# =============================================================================
# Agent Creation Benchmarks
# =============================================================================


class TestAgentCreationPerformance:
    """Benchmarks for agent creation and initialization."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset agent type registry before each test."""
        AgentTypeRegistry.reset_instance()
        yield
        AgentTypeRegistry.reset_instance()

    def test_create_agent_under_5ms(self) -> None:
        """Test that creating a single agent is fast."""
        config = AgentConfig(agent_type="explore")

        _, elapsed = measure_time(create_agent, "explore", "Test task", config)

        assert elapsed < 0.005, f"Agent creation took {elapsed*1000:.1f}ms, expected < 5ms"

    def test_create_all_agent_types_under_100ms(self) -> None:
        """Test that creating one of each agent type is fast."""
        start = time.perf_counter()

        for agent_type in AGENT_CLASSES.keys():
            config = AgentConfig(agent_type=agent_type)
            create_agent(agent_type, "Test task", config)

        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"Creating 20 agents took {elapsed*1000:.1f}ms, expected < 100ms"

    def test_agent_with_context_under_5ms(self) -> None:
        """Test that creating agent with context is fast."""
        config = AgentConfig(agent_type="plan")
        context = AgentContext(
            working_directory="/test/project",
            environment={"VAR1": "value1", "VAR2": "value2"},
            metadata={"key": "value"},
        )

        _, elapsed = measure_time(create_agent, "plan", "Test task", config, context)

        assert elapsed < 0.005, f"Agent creation took {elapsed*1000:.1f}ms, expected < 5ms"

    def test_agent_serialization_under_1ms(self) -> None:
        """Test that agent serialization is fast."""
        config = AgentConfig(agent_type="general")
        agent = create_agent("general", "Test task", config)

        _, elapsed = measure_time(agent.to_dict)

        assert elapsed < 0.001, f"Serialization took {elapsed*1000:.3f}ms, expected < 1ms"


# =============================================================================
# Agent Type Registry Benchmarks
# =============================================================================


class TestAgentTypeRegistryPerformance:
    """Benchmarks for agent type registry operations."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        AgentTypeRegistry.reset_instance()
        yield
        AgentTypeRegistry.reset_instance()

    def test_registry_initialization_under_10ms(self) -> None:
        """Test that registry initialization with all types is fast."""
        AgentTypeRegistry.reset_instance()

        _, elapsed = measure_time(AgentTypeRegistry.get_instance)

        assert elapsed < 0.01, f"Init took {elapsed*1000:.1f}ms, expected < 10ms"

    def test_type_lookup_under_100us(self) -> None:
        """Test that type lookup is very fast."""
        registry = AgentTypeRegistry.get_instance()

        # Warm up
        registry.get("explore")

        # Measure
        _, elapsed = measure_time(registry.get, "explore")

        assert elapsed < 0.0001, f"Lookup took {elapsed*1000000:.1f}us, expected < 100us"

    def test_list_types_under_100us(self) -> None:
        """Test that listing types is fast."""
        registry = AgentTypeRegistry.get_instance()

        _, elapsed = measure_time(registry.list_types)

        assert elapsed < 0.0001, f"Listing took {elapsed*1000000:.1f}us, expected < 100us"


# =============================================================================
# Tool Execution Benchmarks
# =============================================================================


class TestToolExecutionPerformance:
    """Benchmarks for tool execution operations."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        ToolRegistry.reset()
        yield
        ToolRegistry.reset()

    @pytest.mark.asyncio
    async def test_tool_execution_overhead_under_5ms(self) -> None:
        """Test that tool execution overhead is minimal."""
        registry = ToolRegistry()
        registry.register(DummyTool())
        executor = ToolExecutor(registry)
        context = ExecutionContext(working_dir="/tmp")

        # Warm up
        await executor.execute("Dummy", context, input="test")

        # Measure
        _, elapsed = await measure_time_async(
            executor.execute("Dummy", context, input="test")
        )

        assert elapsed < 0.005, f"Execution took {elapsed*1000:.1f}ms, expected < 5ms"

    @pytest.mark.asyncio
    async def test_100_tool_executions_under_500ms(self) -> None:
        """Test that many sequential executions are reasonably fast."""
        registry = ToolRegistry()
        registry.register(DummyTool())
        executor = ToolExecutor(registry)
        context = ExecutionContext(working_dir="/tmp")

        start = time.perf_counter()
        for i in range(100):
            await executor.execute("Dummy", context, input=f"test{i}")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"100 executions took {elapsed:.2f}s, expected < 0.5s"

    @pytest.mark.asyncio
    async def test_concurrent_tool_executions(self) -> None:
        """Test that concurrent tool executions scale well."""
        registry = ToolRegistry()
        registry.register(DummyTool())
        executor = ToolExecutor(registry)
        context = ExecutionContext(working_dir="/tmp")

        async def run_tool(i: int):
            return await executor.execute("Dummy", context, input=f"test{i}")

        start = time.perf_counter()
        tasks = [run_tool(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert all(r.success for r in results)
        assert elapsed < 0.5, f"50 concurrent executions took {elapsed:.2f}s, expected < 0.5s"


# =============================================================================
# Memory and Scalability Benchmarks
# =============================================================================


class TestMemoryAndScalability:
    """Benchmarks for memory usage and scalability."""

    @pytest.fixture(autouse=True)
    def reset_registries(self):
        """Reset all registries before each test."""
        ToolRegistry.reset()
        AgentTypeRegistry.reset_instance()
        yield
        ToolRegistry.reset()
        AgentTypeRegistry.reset_instance()

    def test_large_tool_registry_performance(self) -> None:
        """Test registry performance with many tools."""
        registry = ToolRegistry()

        # Register 500 tools
        start = time.perf_counter()
        for i in range(500):
            registry.register(DummyTool(f"Tool{i}"))
        register_time = time.perf_counter() - start

        # Lookup should still be fast
        _, lookup_time = measure_time(registry.get, "Tool250")

        assert register_time < 0.5, f"Registering 500 tools took {register_time:.2f}s"
        assert lookup_time < 0.001, f"Lookup in 500-tool registry took {lookup_time*1000:.2f}ms"

    def test_agent_creation_scaling(self) -> None:
        """Test that agent creation scales linearly."""
        times = []

        for count in [10, 50, 100]:
            start = time.perf_counter()
            for i in range(count):
                config = AgentConfig(agent_type="general")
                create_agent("general", f"Task {i}", config)
            elapsed = time.perf_counter() - start
            times.append(elapsed / count)  # Time per agent

        # Time per agent should be relatively constant (within 3x)
        assert max(times) / min(times) < 3, (
            f"Agent creation doesn't scale linearly: {times}"
        )


# =============================================================================
# Stress Tests
# =============================================================================


@pytest.mark.slow
class TestStressPerformance:
    """Stress tests for performance under load."""

    @pytest.fixture(autouse=True)
    def reset_registries(self):
        """Reset all registries."""
        ToolRegistry.reset()
        yield
        ToolRegistry.reset()

    def test_registry_stress_1000_tools(self) -> None:
        """Stress test: register and lookup 1000 tools."""
        registry = ToolRegistry()

        # Register 1000 tools
        for i in range(1000):
            registry.register(DummyTool(f"Tool{i}"))

        # Perform 1000 lookups
        start = time.perf_counter()
        for i in range(1000):
            registry.get(f"Tool{i % 1000}")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"1000 lookups took {elapsed:.2f}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_concurrent_stress(self) -> None:
        """Stress test: many concurrent operations."""
        registry = ToolRegistry()
        registry.register(DummyTool())
        executor = ToolExecutor(registry)
        context = ExecutionContext(working_dir="/tmp")

        async def run_batch(batch_id: int):
            results = []
            for i in range(10):
                result = await executor.execute("Dummy", context, input=f"batch{batch_id}_{i}")
                results.append(result)
            return results

        start = time.perf_counter()
        batches = [run_batch(i) for i in range(20)]
        all_results = await asyncio.gather(*batches)
        elapsed = time.perf_counter() - start

        total_ops = sum(len(r) for r in all_results)
        assert total_ops == 200
        assert elapsed < 1.0, f"200 concurrent ops took {elapsed:.2f}s, expected < 1s"
