"""Tests for agent base classes."""

from datetime import datetime
from uuid import UUID

import pytest

from code_forge.agents.base import (
    Agent,
    AgentConfig,
    AgentContext,
    AgentState,
    ResourceLimits,
    ResourceUsage,
)
from code_forge.agents.result import AgentResult


# Concrete implementation for testing
class ConcreteAgentForTesting(Agent):
    """Concrete Agent implementation for testing."""

    @property
    def agent_type(self) -> str:
        return "testable"

    async def execute(self) -> AgentResult:
        return AgentResult.ok("Test completed")


class TestAgentState:
    """Tests for AgentState enum."""

    def test_pending_value(self) -> None:
        """Test PENDING state value."""
        assert AgentState.PENDING.value == "pending"

    def test_running_value(self) -> None:
        """Test RUNNING state value."""
        assert AgentState.RUNNING.value == "running"

    def test_completed_value(self) -> None:
        """Test COMPLETED state value."""
        assert AgentState.COMPLETED.value == "completed"

    def test_failed_value(self) -> None:
        """Test FAILED state value."""
        assert AgentState.FAILED.value == "failed"

    def test_cancelled_value(self) -> None:
        """Test CANCELLED state value."""
        assert AgentState.CANCELLED.value == "cancelled"

    def test_all_states_exist(self) -> None:
        """Test all expected states exist."""
        states = [s.value for s in AgentState]
        assert "pending" in states
        assert "running" in states
        assert "completed" in states
        assert "failed" in states
        assert "cancelled" in states


class TestResourceLimits:
    """Tests for ResourceLimits dataclass."""

    def test_default_values(self) -> None:
        """Test default resource limits."""
        limits = ResourceLimits()
        assert limits.max_tokens == 50000
        assert limits.max_time_seconds == 300
        assert limits.max_tool_calls == 100
        assert limits.max_iterations == 50

    def test_custom_values(self) -> None:
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_tokens=10000,
            max_time_seconds=60,
            max_tool_calls=20,
            max_iterations=10,
        )
        assert limits.max_tokens == 10000
        assert limits.max_time_seconds == 60
        assert limits.max_tool_calls == 20
        assert limits.max_iterations == 10

    def test_invalid_max_tokens(self) -> None:
        """Test validation rejects non-positive max_tokens."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ResourceLimits(max_tokens=0)
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ResourceLimits(max_tokens=-1)

    def test_invalid_max_time(self) -> None:
        """Test validation rejects non-positive max_time_seconds."""
        with pytest.raises(ValueError, match="max_time_seconds must be positive"):
            ResourceLimits(max_time_seconds=0)

    def test_invalid_max_tool_calls(self) -> None:
        """Test validation rejects non-positive max_tool_calls."""
        with pytest.raises(ValueError, match="max_tool_calls must be positive"):
            ResourceLimits(max_tool_calls=-5)

    def test_invalid_max_iterations(self) -> None:
        """Test validation rejects non-positive max_iterations."""
        with pytest.raises(ValueError, match="max_iterations must be positive"):
            ResourceLimits(max_iterations=0)


class TestResourceUsage:
    """Tests for ResourceUsage dataclass."""

    def test_default_values(self) -> None:
        """Test default usage values."""
        usage = ResourceUsage()
        assert usage.tokens_used == 0
        assert usage.time_seconds == 0.0
        assert usage.tool_calls == 0
        assert usage.iterations == 0
        assert usage.cost_usd == 0.0

    def test_custom_values(self) -> None:
        """Test custom usage values."""
        usage = ResourceUsage(
            tokens_used=5000,
            time_seconds=30.5,
            tool_calls=15,
            iterations=8,
            cost_usd=0.05,
        )
        assert usage.tokens_used == 5000
        assert usage.time_seconds == 30.5
        assert usage.tool_calls == 15
        assert usage.iterations == 8
        assert usage.cost_usd == 0.05

    def test_exceeds_tokens(self) -> None:
        """Test exceeds detects token limit."""
        limits = ResourceLimits(max_tokens=1000)
        usage = ResourceUsage(tokens_used=1500)
        assert usage.exceeds(limits) == "max_tokens"

    def test_exceeds_time(self) -> None:
        """Test exceeds detects time limit."""
        limits = ResourceLimits(max_time_seconds=60)
        usage = ResourceUsage(time_seconds=90.0)
        assert usage.exceeds(limits) == "max_time_seconds"

    def test_exceeds_tool_calls(self) -> None:
        """Test exceeds detects tool call limit."""
        limits = ResourceLimits(max_tool_calls=10)
        usage = ResourceUsage(tool_calls=15)
        assert usage.exceeds(limits) == "max_tool_calls"

    def test_exceeds_iterations(self) -> None:
        """Test exceeds detects iteration limit."""
        limits = ResourceLimits(max_iterations=5)
        usage = ResourceUsage(iterations=10)
        assert usage.exceeds(limits) == "max_iterations"

    def test_within_limits(self) -> None:
        """Test exceeds returns None when within limits."""
        limits = ResourceLimits(
            max_tokens=10000,
            max_time_seconds=300,
            max_tool_calls=100,
            max_iterations=50,
        )
        usage = ResourceUsage(
            tokens_used=5000,
            time_seconds=100.0,
            tool_calls=50,
            iterations=25,
        )
        assert usage.exceeds(limits) is None

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        usage = ResourceUsage(
            tokens_used=1000,
            time_seconds=10.5,
            tool_calls=5,
            iterations=3,
            cost_usd=0.01,
        )
        d = usage.to_dict()
        assert d["tokens_used"] == 1000
        assert d["time_seconds"] == 10.5
        assert d["tool_calls"] == 5
        assert d["iterations"] == 3
        assert d["cost_usd"] == 0.01


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_minimal_config(self) -> None:
        """Test config with only required field."""
        config = AgentConfig(agent_type="test")
        assert config.agent_type == "test"
        assert config.description == ""
        assert config.prompt_addition == ""
        assert config.tools is None
        assert config.inherit_context is False
        assert isinstance(config.limits, ResourceLimits)
        assert config.model is None

    def test_full_config(self) -> None:
        """Test config with all fields."""
        limits = ResourceLimits(max_tokens=5000)
        config = AgentConfig(
            agent_type="explore",
            description="Test agent",
            prompt_addition="Extra prompt",
            tools=["read", "glob"],
            inherit_context=True,
            limits=limits,
            model="claude-3-sonnet",
        )
        assert config.agent_type == "explore"
        assert config.description == "Test agent"
        assert config.prompt_addition == "Extra prompt"
        assert config.tools == ["read", "glob"]
        assert config.inherit_context is True
        assert config.limits.max_tokens == 5000
        assert config.model == "claude-3-sonnet"

    def test_for_type_known_type(self) -> None:
        """Test for_type with known agent type."""
        config = AgentConfig.for_type("explore")
        assert config.agent_type == "explore"
        assert "explore" in config.description.lower() or config.description != ""

    def test_for_type_unknown_type(self) -> None:
        """Test for_type with unknown agent type."""
        config = AgentConfig.for_type("unknown-type")
        assert config.agent_type == "unknown-type"

    def test_for_type_with_overrides(self) -> None:
        """Test for_type with overrides."""
        config = AgentConfig.for_type("explore", model="custom-model")
        assert config.model == "custom-model"

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        config = AgentConfig(
            agent_type="test",
            description="Test",
            tools=["read"],
        )
        d = config.to_dict()
        assert d["agent_type"] == "test"
        assert d["description"] == "Test"
        assert d["tools"] == ["read"]
        assert "limits" in d


class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_default_values(self) -> None:
        """Test default context values."""
        context = AgentContext()
        assert context.parent_messages == []
        assert context.working_directory == "."
        assert context.environment == {}
        assert context.metadata == {}
        assert context.parent_id is None

    def test_custom_values(self) -> None:
        """Test custom context values."""
        from uuid import uuid4
        parent_id = uuid4()
        context = AgentContext(
            parent_messages=[{"role": "user", "content": "test"}],
            working_directory="/project",
            environment={"PATH": "/usr/bin"},
            metadata={"key": "value"},
            parent_id=parent_id,
        )
        assert len(context.parent_messages) == 1
        assert context.working_directory == "/project"
        assert context.environment["PATH"] == "/usr/bin"
        assert context.metadata["key"] == "value"
        assert context.parent_id == parent_id

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        context = AgentContext(working_directory="/test")
        d = context.to_dict()
        assert d["working_directory"] == "/test"
        assert d["parent_id"] is None


class TestAgent:
    """Tests for Agent base class."""

    def test_creation(self) -> None:
        """Test agent creation."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test task", config=config)

        assert isinstance(agent.id, UUID)
        assert agent.task == "Test task"
        assert agent.config == config
        assert agent.state == AgentState.PENDING
        assert isinstance(agent.created_at, datetime)
        assert agent.started_at is None
        assert agent.completed_at is None

    def test_creation_with_context(self) -> None:
        """Test agent creation with context."""
        config = AgentConfig(agent_type="testable")
        context = AgentContext(working_directory="/project")
        agent = ConcreteAgentForTesting(task="Test", config=config, context=context)

        assert agent.context == context
        assert agent.context.working_directory == "/project"

    def test_agent_type_property(self) -> None:
        """Test agent_type property."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)
        assert agent.agent_type == "testable"

    def test_cancel(self) -> None:
        """Test cancel method on pending agent."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        agent.cancel()
        assert agent.is_cancelled is True
        # Still pending because cancel only changes state if running
        assert agent.state == AgentState.PENDING

    def test_cancel_running_agent(self) -> None:
        """Test cancel method on running agent."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        agent._start_execution()
        assert agent.state == AgentState.RUNNING

        agent.cancel()
        assert agent.is_cancelled is True
        assert agent.state == AgentState.CANCELLED
        assert isinstance(agent.completed_at, datetime)

    def test_is_complete_states(self) -> None:
        """Test is_complete for different states."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        assert agent.is_complete is False

        agent.state = AgentState.RUNNING
        assert agent.is_complete is False

        agent.state = AgentState.COMPLETED
        assert agent.is_complete is True

        agent.state = AgentState.FAILED
        assert agent.is_complete is True

        agent.state = AgentState.CANCELLED
        assert agent.is_complete is True

    def test_is_running(self) -> None:
        """Test is_running property."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        assert agent.is_running is False

        agent.state = AgentState.RUNNING
        assert agent.is_running is True

    def test_result_property(self) -> None:
        """Test result property."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        assert agent.result is None

        result = AgentResult.ok("Done")
        agent._result = result
        assert agent.result == result

    def test_usage_property(self) -> None:
        """Test usage property."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        assert isinstance(agent.usage, ResourceUsage)
        assert agent.usage.tokens_used == 0

    def test_messages_property(self) -> None:
        """Test messages property returns copy."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        agent._messages = [{"role": "user", "content": "test"}]
        messages = agent.messages

        assert messages == [{"role": "user", "content": "test"}]
        # Modifying returned list shouldn't affect internal state
        messages.append({"role": "assistant", "content": "response"})
        assert len(agent._messages) == 1

    def test_on_progress_callback(self) -> None:
        """Test progress callback registration."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        progress_messages: list[str] = []
        agent.on_progress(progress_messages.append)

        agent._report_progress("Starting")
        agent._report_progress("Working")

        assert progress_messages == ["Starting", "Working"]

    def test_on_progress_callback_error_ignored(self) -> None:
        """Test progress callback errors are ignored."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        def failing_callback(msg: str) -> None:
            raise RuntimeError("Callback error")

        agent.on_progress(failing_callback)
        # Should not raise
        agent._report_progress("Test")

    def test_start_execution(self) -> None:
        """Test _start_execution method."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)

        agent._start_execution()

        assert agent.state == AgentState.RUNNING
        assert isinstance(agent.started_at, datetime)

    def test_complete_execution_success(self) -> None:
        """Test _complete_execution with success."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)
        result = AgentResult.ok("Done")

        agent._start_execution()
        agent._complete_execution(result, success=True)

        assert agent.state == AgentState.COMPLETED
        assert isinstance(agent.completed_at, datetime)
        assert agent.result == result

    def test_complete_execution_failure(self) -> None:
        """Test _complete_execution with failure."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)
        result = AgentResult.fail("Error")

        agent._start_execution()
        agent._complete_execution(result, success=False)

        assert agent.state == AgentState.FAILED
        assert agent.result == result

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test task", config=config)

        d = agent.to_dict()

        assert d["agent_type"] == "testable"
        assert d["task"] == "Test task"
        assert d["state"] == "pending"
        assert "id" in d
        assert "created_at" in d
        assert "usage" in d
        assert "config" in d
        assert "context" in d

    def test_to_dict_with_result(self) -> None:
        """Test serialization includes result when present."""
        config = AgentConfig(agent_type="testable")
        agent = ConcreteAgentForTesting(task="Test", config=config)
        agent._result = AgentResult.ok("Done")

        d = agent.to_dict()
        assert isinstance(d["result"], dict)
        assert d["result"]["success"] is True


@pytest.mark.asyncio
async def test_execute_method() -> None:
    """Test execute method."""
    config = AgentConfig(agent_type="testable")
    agent = ConcreteAgentForTesting(task="Test", config=config)

    result = await agent.execute()

    assert result.success is True
    assert result.output == "Test completed"
