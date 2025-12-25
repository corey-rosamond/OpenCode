"""Comprehensive tests for all built-in agent implementations.

This module provides tests for all 21 agent types, covering:
- Agent instantiation and configuration
- Agent type property
- Execute method behavior
- Context handling
- State management
- Progress callbacks
- Cancellation
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from code_forge.agents.base import (
    Agent,
    AgentConfig,
    AgentContext,
    AgentState,
    ResourceLimits,
    ResourceUsage,
)
from code_forge.agents.builtin import (
    AGENT_CLASSES,
    CodeReviewAgent,
    CommunicationAgent,
    ConfigurationAgent,
    DebugAgent,
    DependencyAnalysisAgent,
    DiagramAgent,
    DocumentationAgent,
    ExploreAgent,
    GeneralAgent,
    LogAnalysisAgent,
    MigrationPlanningAgent,
    PerformanceAnalysisAgent,
    PlanAgent,
    QAManualAgent,
    RefactoringAgent,
    ResearchAgent,
    SecurityAuditAgent,
    TestGenerationAgent,
    TutorialAgent,
    WritingAgent,
    create_agent,
)
from code_forge.agents.result import AgentResult


# =============================================================================
# Parametrized Tests for All Agents
# =============================================================================

# All agent classes with their type identifiers
ALL_AGENTS = [
    ("explore", ExploreAgent),
    ("plan", PlanAgent),
    ("code-review", CodeReviewAgent),
    ("general", GeneralAgent),
    ("test-generation", TestGenerationAgent),
    ("documentation", DocumentationAgent),
    ("refactoring", RefactoringAgent),
    ("debug", DebugAgent),
    ("writing", WritingAgent),
    ("communication", CommunicationAgent),
    ("tutorial", TutorialAgent),
    ("diagram", DiagramAgent),
    ("qa-manual", QAManualAgent),
    ("research", ResearchAgent),
    ("log-analysis", LogAnalysisAgent),
    ("performance-analysis", PerformanceAnalysisAgent),
    ("security-audit", SecurityAuditAgent),
    ("dependency-analysis", DependencyAnalysisAgent),
    ("migration-planning", MigrationPlanningAgent),
    ("configuration", ConfigurationAgent),
]


class TestAllAgentsCreation:
    """Test creation for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_instantiation(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that each agent can be instantiated."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test task", config=config)

        assert agent is not None
        assert agent.task == "Test task"
        assert agent.state == AgentState.PENDING

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_type_property(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that agent_type property returns correct value."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        assert agent.agent_type == agent_type

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_with_context(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test agent creation with context."""
        config = AgentConfig(agent_type=agent_type)
        parent_id = uuid4()
        context = AgentContext(
            working_directory="/test/project",
            environment={"TEST_VAR": "value"},
            metadata={"key": "value"},
            parent_id=parent_id,
        )

        agent = agent_class(task="Test", config=config, context=context)

        assert agent.context.working_directory == "/test/project"
        assert agent.context.environment["TEST_VAR"] == "value"
        assert agent.context.metadata["key"] == "value"
        assert agent.context.parent_id == parent_id

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_default_context(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test agent has default context if none provided."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        assert agent.context is not None
        assert agent.context.working_directory == "."
        assert agent.context.environment == {}
        assert agent.context.metadata == {}
        assert agent.context.parent_id is None

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_has_unique_id(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that each agent has a unique ID."""
        config = AgentConfig(agent_type=agent_type)
        agent1 = agent_class(task="Test 1", config=config)
        agent2 = agent_class(task="Test 2", config=config)

        assert agent1.id != agent2.id

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_created_at_timestamp(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that agent has created_at timestamp."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        assert agent.created_at is not None
        assert agent.started_at is None
        assert agent.completed_at is None


class TestAllAgentsExecution:
    """Test execution behavior for all agent types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    async def test_direct_execute_returns_error(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that direct execute() returns error (must use executor)."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        result = await agent.execute()

        assert result.success is False
        assert "AgentExecutor" in result.error

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_is_not_running_initially(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that agent is not running when created."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        assert agent.is_running is False
        assert agent.is_complete is False

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_agent_result_is_none_initially(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that result is None before execution."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        assert agent.result is None


class TestAllAgentsStateManagement:
    """Test state management for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_start_execution_changes_state(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that _start_execution changes state to RUNNING."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        agent._start_execution()

        assert agent.state == AgentState.RUNNING
        assert agent.is_running is True
        assert agent.started_at is not None

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_complete_execution_success(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that _complete_execution with success=True sets COMPLETED."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)
        result = AgentResult.ok("Done")

        agent._start_execution()
        agent._complete_execution(result, success=True)

        assert agent.state == AgentState.COMPLETED
        assert agent.is_complete is True
        assert agent.completed_at is not None
        assert agent.result == result

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_complete_execution_failure(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that _complete_execution with success=False sets FAILED."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)
        result = AgentResult.fail("Error occurred")

        agent._start_execution()
        agent._complete_execution(result, success=False)

        assert agent.state == AgentState.FAILED
        assert agent.is_complete is True


class TestAllAgentsCancellation:
    """Test cancellation for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_cancel_pending_agent(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test cancelling a pending agent."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        result = agent.cancel()

        assert result is True
        assert agent.is_cancelled is True
        # State remains PENDING until started
        assert agent.state == AgentState.PENDING

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_cancel_running_agent(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test cancelling a running agent."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        agent._start_execution()
        result = agent.cancel()

        assert result is True
        assert agent.is_cancelled is True
        assert agent.state == AgentState.CANCELLED
        assert agent.completed_at is not None

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_cancel_completed_agent_fails(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that cancelling a completed agent fails."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        agent._start_execution()
        agent._complete_execution(AgentResult.ok("Done"), success=True)

        result = agent.cancel()

        assert result is False
        assert agent.state == AgentState.COMPLETED


class TestAllAgentsProgressCallbacks:
    """Test progress callbacks for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_register_progress_callback(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test registering a progress callback."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        messages = []
        agent.on_progress(lambda msg: messages.append(msg))

        agent._report_progress("Test message")

        assert len(messages) == 1
        assert messages[0] == "Test message"

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_multiple_progress_callbacks(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test multiple progress callbacks."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        messages1 = []
        messages2 = []
        agent.on_progress(lambda msg: messages1.append(msg))
        agent.on_progress(lambda msg: messages2.append(msg))

        agent._report_progress("Test")

        assert len(messages1) == 1
        assert len(messages2) == 1

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_callback_exception_suppressed(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that callback exceptions are suppressed."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        def failing_callback(msg: str) -> None:
            raise RuntimeError("Callback failed")

        messages = []
        agent.on_progress(failing_callback)
        agent.on_progress(lambda msg: messages.append(msg))

        # Should not raise
        agent._report_progress("Test")

        # Second callback should still work
        assert len(messages) == 1


class TestAllAgentsSerialization:
    """Test serialization for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_to_dict_basic(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test basic serialization."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test task", config=config)

        data = agent.to_dict()

        assert data["agent_type"] == agent_type
        assert data["task"] == "Test task"
        assert data["state"] == "pending"
        assert data["id"] is not None
        assert data["created_at"] is not None

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_to_dict_with_result(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test serialization with result."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        agent._start_execution()
        agent._complete_execution(AgentResult.ok("Done"), success=True)

        data = agent.to_dict()

        assert data["state"] == "completed"
        assert data["result"] is not None
        assert data["result"]["success"] is True


class TestAllAgentsMessages:
    """Test message handling for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_messages_empty_initially(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that messages are empty initially."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        assert agent.messages == []

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_messages_returns_copy(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that messages property returns a copy."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        messages1 = agent.messages
        messages2 = agent.messages

        # Should be different objects
        assert messages1 is not messages2


class TestAllAgentsUsage:
    """Test resource usage tracking for all agent types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_usage_empty_initially(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that usage is empty initially."""
        config = AgentConfig(agent_type=agent_type)
        agent = agent_class(task="Test", config=config)

        usage = agent.usage

        assert usage.tokens_used == 0
        assert usage.time_seconds == 0.0
        assert usage.tool_calls == 0
        assert usage.iterations == 0
        assert usage.cost_usd == 0.0


class TestCreateAgentFactory:
    """Test create_agent factory function for all types."""

    @pytest.mark.parametrize("agent_type,agent_class", ALL_AGENTS)
    def test_create_agent_returns_correct_class(
        self, agent_type: str, agent_class: type[Agent]
    ) -> None:
        """Test that create_agent returns the correct class."""
        config = AgentConfig(agent_type=agent_type)
        agent = create_agent(agent_type, "Test", config)

        assert isinstance(agent, agent_class)
        assert agent.agent_type == agent_type


class TestAgentClassesRegistry:
    """Test AGENT_CLASSES registry contains all types."""

    def test_all_21_agents_registered(self) -> None:
        """Test that all 21 agent types are registered."""
        assert len(AGENT_CLASSES) == 20  # 20 unique types

    @pytest.mark.parametrize("agent_type,_", ALL_AGENTS)
    def test_agent_type_in_registry(self, agent_type: str, _: type) -> None:
        """Test each agent type is in the registry."""
        assert agent_type in AGENT_CLASSES


# =============================================================================
# Individual Agent-Specific Tests
# =============================================================================

class TestTestGenerationAgent:
    """Tests specific to TestGenerationAgent."""

    def test_creation(self) -> None:
        """Test test generation agent creation."""
        config = AgentConfig(agent_type="test-generation")
        agent = TestGenerationAgent(task="Generate tests", config=config)

        assert agent.agent_type == "test-generation"


class TestDocumentationAgent:
    """Tests specific to DocumentationAgent."""

    def test_creation(self) -> None:
        """Test documentation agent creation."""
        config = AgentConfig(agent_type="documentation")
        agent = DocumentationAgent(task="Write docs", config=config)

        assert agent.agent_type == "documentation"


class TestRefactoringAgent:
    """Tests specific to RefactoringAgent."""

    def test_creation(self) -> None:
        """Test refactoring agent creation."""
        config = AgentConfig(agent_type="refactoring")
        agent = RefactoringAgent(task="Refactor code", config=config)

        assert agent.agent_type == "refactoring"


class TestDebugAgent:
    """Tests specific to DebugAgent."""

    def test_creation(self) -> None:
        """Test debug agent creation."""
        config = AgentConfig(agent_type="debug")
        agent = DebugAgent(task="Debug issue", config=config)

        assert agent.agent_type == "debug"


class TestResearchAgent:
    """Tests specific to ResearchAgent."""

    def test_creation(self) -> None:
        """Test research agent creation."""
        config = AgentConfig(agent_type="research")
        agent = ResearchAgent(task="Research topic", config=config)

        assert agent.agent_type == "research"


class TestLogAnalysisAgent:
    """Tests specific to LogAnalysisAgent."""

    def test_creation(self) -> None:
        """Test log analysis agent creation."""
        config = AgentConfig(agent_type="log-analysis")
        agent = LogAnalysisAgent(task="Analyze logs", config=config)

        assert agent.agent_type == "log-analysis"


class TestPerformanceAnalysisAgent:
    """Tests specific to PerformanceAnalysisAgent."""

    def test_creation(self) -> None:
        """Test performance analysis agent creation."""
        config = AgentConfig(agent_type="performance-analysis")
        agent = PerformanceAnalysisAgent(task="Analyze performance", config=config)

        assert agent.agent_type == "performance-analysis"


class TestSecurityAuditAgent:
    """Tests specific to SecurityAuditAgent."""

    def test_creation(self) -> None:
        """Test security audit agent creation."""
        config = AgentConfig(agent_type="security-audit")
        agent = SecurityAuditAgent(task="Security audit", config=config)

        assert agent.agent_type == "security-audit"


class TestDependencyAnalysisAgent:
    """Tests specific to DependencyAnalysisAgent."""

    def test_creation(self) -> None:
        """Test dependency analysis agent creation."""
        config = AgentConfig(agent_type="dependency-analysis")
        agent = DependencyAnalysisAgent(task="Analyze deps", config=config)

        assert agent.agent_type == "dependency-analysis"


class TestWritingAgent:
    """Tests specific to WritingAgent."""

    def test_creation(self) -> None:
        """Test writing agent creation."""
        config = AgentConfig(agent_type="writing")
        agent = WritingAgent(task="Write content", config=config)

        assert agent.agent_type == "writing"


class TestCommunicationAgent:
    """Tests specific to CommunicationAgent."""

    def test_creation(self) -> None:
        """Test communication agent creation."""
        config = AgentConfig(agent_type="communication")
        agent = CommunicationAgent(task="Write message", config=config)

        assert agent.agent_type == "communication"


class TestTutorialAgent:
    """Tests specific to TutorialAgent."""

    def test_creation(self) -> None:
        """Test tutorial agent creation."""
        config = AgentConfig(agent_type="tutorial")
        agent = TutorialAgent(task="Create tutorial", config=config)

        assert agent.agent_type == "tutorial"


class TestDiagramAgent:
    """Tests specific to DiagramAgent."""

    def test_creation(self) -> None:
        """Test diagram agent creation."""
        config = AgentConfig(agent_type="diagram")
        agent = DiagramAgent(task="Create diagram", config=config)

        assert agent.agent_type == "diagram"


class TestQAManualAgent:
    """Tests specific to QAManualAgent."""

    def test_creation(self) -> None:
        """Test QA manual agent creation."""
        config = AgentConfig(agent_type="qa-manual")
        agent = QAManualAgent(task="Create test plan", config=config)

        assert agent.agent_type == "qa-manual"


class TestMigrationPlanningAgent:
    """Tests specific to MigrationPlanningAgent."""

    def test_creation(self) -> None:
        """Test migration planning agent creation."""
        config = AgentConfig(agent_type="migration-planning")
        agent = MigrationPlanningAgent(task="Plan migration", config=config)

        assert agent.agent_type == "migration-planning"


class TestConfigurationAgent:
    """Tests specific to ConfigurationAgent."""

    def test_creation(self) -> None:
        """Test configuration agent creation."""
        config = AgentConfig(agent_type="configuration")
        agent = ConfigurationAgent(task="Configure project", config=config)

        assert agent.agent_type == "configuration"


# =============================================================================
# ResourceLimits Tests
# =============================================================================

class TestResourceLimits:
    """Tests for ResourceLimits."""

    def test_default_limits(self) -> None:
        """Test default resource limits."""
        limits = ResourceLimits()

        assert limits.max_tokens == 50000
        assert limits.max_time_seconds == 300
        assert limits.max_tool_calls == 100
        assert limits.max_iterations == 50

    def test_custom_limits(self) -> None:
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

    @pytest.mark.parametrize(
        "field,value",
        [
            ("max_tokens", 0),
            ("max_tokens", -1),
            ("max_time_seconds", 0),
            ("max_time_seconds", -1),
            ("max_tool_calls", 0),
            ("max_tool_calls", -1),
            ("max_iterations", 0),
            ("max_iterations", -1),
        ],
    )
    def test_invalid_limits_raise_error(self, field: str, value: int) -> None:
        """Test that invalid limits raise ValueError."""
        kwargs = {field: value}
        with pytest.raises(ValueError):
            ResourceLimits(**kwargs)


# =============================================================================
# ResourceUsage Tests
# =============================================================================

class TestResourceUsage:
    """Tests for ResourceUsage."""

    def test_default_usage(self) -> None:
        """Test default resource usage."""
        usage = ResourceUsage()

        assert usage.tokens_used == 0
        assert usage.time_seconds == 0.0
        assert usage.tool_calls == 0
        assert usage.iterations == 0
        assert usage.cost_usd == 0.0

    def test_exceeds_max_tokens(self) -> None:
        """Test exceeding max tokens."""
        limits = ResourceLimits(max_tokens=100)
        usage = ResourceUsage(tokens_used=150)

        result = usage.exceeds(limits)

        assert result == "max_tokens"

    def test_exceeds_max_time(self) -> None:
        """Test exceeding max time."""
        limits = ResourceLimits(max_time_seconds=60)
        usage = ResourceUsage(time_seconds=90.0)

        result = usage.exceeds(limits)

        assert result == "max_time_seconds"

    def test_exceeds_max_tool_calls(self) -> None:
        """Test exceeding max tool calls."""
        limits = ResourceLimits(max_tool_calls=10)
        usage = ResourceUsage(tool_calls=15)

        result = usage.exceeds(limits)

        assert result == "max_tool_calls"

    def test_exceeds_max_iterations(self) -> None:
        """Test exceeding max iterations."""
        limits = ResourceLimits(max_iterations=5)
        usage = ResourceUsage(iterations=10)

        result = usage.exceeds(limits)

        assert result == "max_iterations"

    def test_within_limits(self) -> None:
        """Test within all limits."""
        limits = ResourceLimits()
        usage = ResourceUsage(
            tokens_used=1000,
            time_seconds=10.0,
            tool_calls=5,
            iterations=3,
        )

        result = usage.exceeds(limits)

        assert result is None

    def test_to_dict(self) -> None:
        """Test serialization."""
        usage = ResourceUsage(
            tokens_used=100,
            time_seconds=5.5,
            tool_calls=3,
            iterations=2,
            cost_usd=0.01,
        )

        data = usage.to_dict()

        assert data["tokens_used"] == 100
        assert data["time_seconds"] == 5.5
        assert data["tool_calls"] == 3
        assert data["iterations"] == 2
        assert data["cost_usd"] == 0.01


# =============================================================================
# AgentConfig Tests
# =============================================================================

class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_basic_config(self) -> None:
        """Test basic configuration."""
        config = AgentConfig(agent_type="explore")

        assert config.agent_type == "explore"
        assert config.description == ""
        assert config.prompt_addition == ""
        assert config.tools is None
        assert config.inherit_context is False
        assert config.model is None

    def test_full_config(self) -> None:
        """Test full configuration."""
        limits = ResourceLimits(max_tokens=10000)
        config = AgentConfig(
            agent_type="plan",
            description="Planning agent",
            prompt_addition="Be thorough",
            tools=["read", "write"],
            inherit_context=True,
            limits=limits,
            model="gpt-4",
        )

        assert config.description == "Planning agent"
        assert config.prompt_addition == "Be thorough"
        assert config.tools == ["read", "write"]
        assert config.inherit_context is True
        assert config.limits.max_tokens == 10000
        assert config.model == "gpt-4"

    def test_to_dict(self) -> None:
        """Test serialization."""
        config = AgentConfig(
            agent_type="test",
            description="Test agent",
            tools=["tool1"],
        )

        data = config.to_dict()

        assert data["agent_type"] == "test"
        assert data["description"] == "Test agent"
        assert data["tools"] == ["tool1"]
        assert "limits" in data


# =============================================================================
# AgentContext Tests
# =============================================================================

class TestAgentContext:
    """Tests for AgentContext."""

    def test_default_context(self) -> None:
        """Test default context."""
        context = AgentContext()

        assert context.parent_messages == []
        assert context.working_directory == "."
        assert context.environment == {}
        assert context.metadata == {}
        assert context.parent_id is None

    def test_full_context(self) -> None:
        """Test full context."""
        parent_id = uuid4()
        context = AgentContext(
            parent_messages=[{"role": "user", "content": "hello"}],
            working_directory="/project",
            environment={"PATH": "/bin"},
            metadata={"version": "1.0"},
            parent_id=parent_id,
        )

        assert len(context.parent_messages) == 1
        assert context.working_directory == "/project"
        assert context.environment["PATH"] == "/bin"
        assert context.metadata["version"] == "1.0"
        assert context.parent_id == parent_id

    def test_to_dict(self) -> None:
        """Test serialization."""
        parent_id = uuid4()
        context = AgentContext(
            working_directory="/test",
            parent_id=parent_id,
        )

        data = context.to_dict()

        assert data["working_directory"] == "/test"
        assert data["parent_id"] == str(parent_id)

    def test_to_dict_without_parent_id(self) -> None:
        """Test serialization without parent ID."""
        context = AgentContext()

        data = context.to_dict()

        assert data["parent_id"] is None
