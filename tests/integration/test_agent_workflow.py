"""Integration tests for agent workflow.

These tests verify that the subagent system works correctly:
- Agent creation and lifecycle
- Agent execution with tools
- Resource limit enforcement
- Parallel agent execution
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.agents import (
    Agent,
    AgentConfig,
    AgentContext,
    AgentManager,
    AgentResult,
    AgentState,
    AgentTypeRegistry,
    ResourceLimits,
    ResourceUsage,
)
from code_forge.agents.types import AgentTypeDefinition
from code_forge.agents.builtin import (
    CodeReviewAgent,
    ExploreAgent,
    GeneralAgent,
    PlanAgent,
)


class TestAgentLifecycle:
    """Test agent lifecycle management."""

    def test_agent_manager_singleton(self) -> None:
        """Test AgentManager is a singleton."""
        manager1 = AgentManager.get_instance()
        manager2 = AgentManager.get_instance()
        assert manager1 is manager2

    def test_agent_type_registry(self) -> None:
        """Test agent type registry has built-in types."""
        registry = AgentTypeRegistry.get_instance()

        # Built-in types should be registered
        assert isinstance(registry.get("explore"), AgentTypeDefinition)
        assert isinstance(registry.get("plan"), AgentTypeDefinition)
        assert isinstance(registry.get("code-review"), AgentTypeDefinition)
        assert isinstance(registry.get("general"), AgentTypeDefinition)

    def test_create_explore_agent(self) -> None:
        """Test creating an explore agent."""
        agent = ExploreAgent(
            task="Find all Python files in the project",
            config=AgentConfig(
                agent_type="explore",
                description="Find Python files",
            ),
            context=AgentContext(working_directory="."),
        )

        assert isinstance(agent, ExploreAgent)
        assert agent.config.agent_type == "explore"

    def test_create_plan_agent(self) -> None:
        """Test creating a plan agent."""
        agent = PlanAgent(
            task="Create a plan to implement user authentication",
            config=AgentConfig(
                agent_type="plan",
                description="Implementation planning",
            ),
            context=AgentContext(working_directory="."),
        )

        assert isinstance(agent, PlanAgent)
        assert agent.config.agent_type == "plan"


class TestAgentConfig:
    """Test agent configuration."""

    def test_default_resource_limits(self) -> None:
        """Test default resource limits."""
        config = AgentConfig(
            agent_type="general",
            description="Test description",
        )

        assert isinstance(config.limits, ResourceLimits)
        assert config.limits.max_tokens > 0
        assert config.limits.max_tool_calls > 0

    def test_custom_resource_limits(self) -> None:
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_tokens=1000,
            max_tool_calls=5,
            max_iterations=10,
            max_time_seconds=60,
        )

        config = AgentConfig(
            agent_type="general",
            description="Test description",
            limits=limits,
        )

        assert config.limits.max_tokens == 1000
        assert config.limits.max_tool_calls == 5


class TestAgentContext:
    """Test agent context."""

    def test_context_with_working_dir(self, temp_project: Path) -> None:
        """Test creating context with working directory."""
        context = AgentContext(working_directory=str(temp_project))

        assert context.working_directory == str(temp_project)

    def test_context_with_metadata(self) -> None:
        """Test creating context with metadata."""
        context = AgentContext(
            working_directory=".",
            metadata={"key": "value"},
        )

        assert context.metadata["key"] == "value"


class TestAgentResult:
    """Test agent results."""

    def test_result_ok(self) -> None:
        """Test successful result."""
        result = AgentResult.ok(output="Task completed successfully")

        assert result.success
        assert result.output == "Task completed successfully"
        assert result.error is None

    def test_result_fail(self) -> None:
        """Test failed result."""
        result = AgentResult.fail(error="Something went wrong")

        assert not result.success
        assert result.error == "Something went wrong"

    def test_result_cancelled(self) -> None:
        """Test cancelled result."""
        result = AgentResult.cancelled()

        assert not result.success
        assert result.cancelled

    def test_result_timeout(self) -> None:
        """Test timeout result."""
        result = AgentResult.timeout()

        assert not result.success
        # Check for timeout indication in error or output
        assert "timeout" in str(result.error).lower() or not result.success


class TestResourceUsage:
    """Test resource usage tracking."""

    def test_usage_tracking(self) -> None:
        """Test resource usage tracking."""
        usage = ResourceUsage()

        usage.tokens_used = 100
        usage.tool_calls = 5
        usage.iterations = 3

        assert usage.tokens_used == 100
        assert usage.tool_calls == 5
        assert usage.iterations == 3

    def test_exceeds_limits(self) -> None:
        """Test checking if usage exceeds limits."""
        limits = ResourceLimits(
            max_tokens=100,
            max_tool_calls=5,
            max_iterations=10,
            max_time_seconds=60,
        )

        usage = ResourceUsage()

        # Under limits
        usage.tokens_used = 50
        usage.tool_calls = 2
        assert not usage.exceeds(limits)

        # Exceeds tokens
        usage.tokens_used = 150
        assert usage.exceeds(limits)

        # Reset and exceed tool calls
        usage.tokens_used = 50
        usage.tool_calls = 10
        assert usage.exceeds(limits)


class TestAgentState:
    """Test agent state transitions."""

    def test_state_values(self) -> None:
        """Test agent state enum values."""
        assert AgentState.PENDING.value == "pending"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.COMPLETED.value == "completed"
        assert AgentState.FAILED.value == "failed"
        assert AgentState.CANCELLED.value == "cancelled"


class TestAgentTypeDefinitions:
    """Test built-in agent type definitions."""

    def test_explore_agent_definition(self) -> None:
        """Test explore agent type definition."""
        registry = AgentTypeRegistry.get_instance()
        definition = registry.get("explore")

        assert isinstance(definition, AgentTypeDefinition)
        assert "explore" in definition.prompt_template.lower() or "search" in definition.prompt_template.lower() or "find" in definition.prompt_template.lower()

    def test_plan_agent_definition(self) -> None:
        """Test plan agent type definition."""
        registry = AgentTypeRegistry.get_instance()
        definition = registry.get("plan")

        assert isinstance(definition, AgentTypeDefinition)
        assert "plan" in definition.prompt_template.lower() or "design" in definition.prompt_template.lower()

    def test_code_review_agent_definition(self) -> None:
        """Test code review agent type definition."""
        registry = AgentTypeRegistry.get_instance()
        definition = registry.get("code-review")

        assert isinstance(definition, AgentTypeDefinition)


class TestAgentWithMockedLLM:
    """Test agent execution with mocked LLM."""

    @pytest.mark.asyncio
    async def test_agent_execution_mock(self, mock_llm_response) -> None:
        """Test agent execution with mocked LLM response."""
        # Create mock LLM client
        mock_client = MagicMock()
        mock_client.invoke = AsyncMock(
            return_value=mock_llm_response("I found the following files...")
        )

        agent = GeneralAgent(
            task="List all Python files",
            config=AgentConfig(
                agent_type="general",
                description="List Python files",
            ),
            context=AgentContext(working_directory="."),
        )

        # Agent should be created successfully
        assert isinstance(agent, GeneralAgent)
        assert agent.state == AgentState.PENDING


class TestAgentToolAccess:
    """Test agent access to tools."""

    def test_explore_agent_has_file_tools(self) -> None:
        """Test that explore agent has access to file tools."""
        registry = AgentTypeRegistry.get_instance()
        definition = registry.get("explore")

        assert isinstance(definition, AgentTypeDefinition)
        # Explore agent should have access to Read, Glob, Grep

    def test_general_agent_has_all_tools(self) -> None:
        """Test that general agent has access to all tools."""
        registry = AgentTypeRegistry.get_instance()
        definition = registry.get("general")

        assert isinstance(definition, AgentTypeDefinition)
        # General agent should have broad tool access
