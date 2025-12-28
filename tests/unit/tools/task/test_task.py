"""Unit tests for TaskTool."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from code_forge.agents.base import AgentState
from code_forge.agents.result import AgentResult
from code_forge.tools.base import ExecutionContext, ToolCategory
from code_forge.tools.task.task import TaskTool


class TestTaskToolProperties:
    """Test TaskTool property methods."""

    def test_name_property(self) -> None:
        """TaskTool.name returns 'Task'."""
        tool = TaskTool()
        assert tool.name == "Task"

    def test_category_property(self) -> None:
        """TaskTool.category returns ToolCategory.TASK."""
        tool = TaskTool()
        assert tool.category == ToolCategory.TASK

    def test_description_property(self) -> None:
        """TaskTool.description is informative."""
        tool = TaskTool()
        assert "agent" in tool.description.lower()
        assert "task" in tool.description.lower()

    def test_parameters_list(self) -> None:
        """get_parameters returns correct parameters."""
        tool = TaskTool()
        params = tool.parameters
        param_names = [p.name for p in params]

        assert "agent_type" in param_names
        assert "task" in param_names
        assert "wait" in param_names
        assert "use_rag" in param_names

    def test_agent_type_parameter_is_required(self) -> None:
        """agent_type parameter is required."""
        tool = TaskTool()
        agent_type_param = next(p for p in tool.parameters if p.name == "agent_type")
        assert agent_type_param.required is True

    def test_task_parameter_is_required(self) -> None:
        """task parameter is required."""
        tool = TaskTool()
        task_param = next(p for p in tool.parameters if p.name == "task")
        assert task_param.required is True

    def test_wait_parameter_is_optional(self) -> None:
        """wait parameter is optional with default True."""
        tool = TaskTool()
        wait_param = next(p for p in tool.parameters if p.name == "wait")
        assert wait_param.required is False
        assert wait_param.default is True

    def test_use_rag_parameter_is_optional(self) -> None:
        """use_rag parameter is optional with default True."""
        tool = TaskTool()
        use_rag_param = next(p for p in tool.parameters if p.name == "use_rag")
        assert use_rag_param.required is False
        assert use_rag_param.default is True


class TestTaskToolExecution:
    """Test TaskTool execution."""

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(working_dir="/test/dir")

    @pytest.fixture
    def mock_agent(self) -> MagicMock:
        """Create mock agent."""
        agent = MagicMock()
        agent.id = uuid4()
        agent.state = AgentState.COMPLETED
        agent.result = AgentResult(
            success=True,
            output="Agent completed successfully",
        )
        agent.usage.tokens_used = 100
        return agent

    @pytest.mark.asyncio
    async def test_unknown_agent_type_returns_error(
        self, mock_context: ExecutionContext
    ) -> None:
        """Returns error for unknown agent type."""
        tool = TaskTool()

        with patch(
            "code_forge.tools.task.task.AgentTypeRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get.return_value = None
            mock_registry.list_types.return_value = ["explore", "plan", "code-review"]
            mock_registry_class.get_instance.return_value = mock_registry

            result = await tool._execute(
                mock_context,
                agent_type="nonexistent",
                task="do something",
            )

        assert not result.success
        assert "Unknown agent type" in result.error
        assert "nonexistent" in result.error
        assert "explore" in result.error

    @pytest.mark.asyncio
    async def test_spawn_agent_success(
        self, mock_context: ExecutionContext, mock_agent: MagicMock
    ) -> None:
        """Successfully spawns agent and returns result."""
        tool = TaskTool()

        with (
            patch(
                "code_forge.tools.task.task.AgentTypeRegistry"
            ) as mock_registry_class,
            patch("code_forge.tools.task.task.AgentManager") as mock_manager_class,
        ):
            # Setup registry mock
            mock_registry = MagicMock()
            mock_registry.get.return_value = MagicMock()  # Type exists
            mock_registry_class.get_instance.return_value = mock_registry

            # Setup manager mock
            mock_manager = MagicMock()
            mock_manager.spawn = AsyncMock(return_value=mock_agent)
            mock_manager_class.get_instance.return_value = mock_manager

            result = await tool._execute(
                mock_context,
                agent_type="explore",
                task="find files",
                wait=True,
            )

        assert result.success
        assert "Agent completed successfully" in result.output
        assert result.metadata["agent_type"] == "explore"
        mock_manager.spawn.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_agent_background_mode(
        self, mock_context: ExecutionContext, mock_agent: MagicMock
    ) -> None:
        """Background mode returns immediately with agent ID."""
        tool = TaskTool()

        with (
            patch(
                "code_forge.tools.task.task.AgentTypeRegistry"
            ) as mock_registry_class,
            patch("code_forge.tools.task.task.AgentManager") as mock_manager_class,
        ):
            mock_registry = MagicMock()
            mock_registry.get.return_value = MagicMock()
            mock_registry_class.get_instance.return_value = mock_registry

            mock_manager = MagicMock()
            mock_manager.spawn = AsyncMock(return_value=mock_agent)
            mock_manager_class.get_instance.return_value = mock_manager

            result = await tool._execute(
                mock_context,
                agent_type="explore",
                task="find files",
                wait=False,
            )

        assert result.success
        assert "background" in result.output.lower()
        assert result.metadata.get("background") is True

    @pytest.mark.asyncio
    async def test_spawn_agent_runtime_error(
        self, mock_context: ExecutionContext
    ) -> None:
        """Handles RuntimeError from agent manager."""
        tool = TaskTool()

        with (
            patch(
                "code_forge.tools.task.task.AgentTypeRegistry"
            ) as mock_registry_class,
            patch("code_forge.tools.task.task.AgentManager") as mock_manager_class,
        ):
            mock_registry = MagicMock()
            mock_registry.get.return_value = MagicMock()
            mock_registry_class.get_instance.return_value = mock_registry

            mock_manager = MagicMock()
            mock_manager.spawn = AsyncMock(
                side_effect=RuntimeError("No executor configured")
            )
            mock_manager_class.get_instance.return_value = mock_manager

            result = await tool._execute(
                mock_context,
                agent_type="explore",
                task="find files",
            )

        assert not result.success
        assert "execution failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_rag_context_passed_when_enabled(
        self, mock_context: ExecutionContext, mock_agent: MagicMock
    ) -> None:
        """RAG context is passed to agent when use_rag=True."""
        tool = TaskTool()
        mock_rag = MagicMock()
        mock_context.metadata["rag_manager"] = mock_rag

        with (
            patch(
                "code_forge.tools.task.task.AgentTypeRegistry"
            ) as mock_registry_class,
            patch("code_forge.tools.task.task.AgentManager") as mock_manager_class,
        ):
            mock_registry = MagicMock()
            mock_registry.get.return_value = MagicMock()
            mock_registry_class.get_instance.return_value = mock_registry

            mock_manager = MagicMock()
            mock_manager.spawn = AsyncMock(return_value=mock_agent)
            mock_manager_class.get_instance.return_value = mock_manager

            await tool._execute(
                mock_context,
                agent_type="explore",
                task="find files",
                use_rag=True,
            )

        # Check that spawn was called with context containing rag_manager
        call_args = mock_manager.spawn.call_args
        agent_context = call_args.kwargs.get("context")
        assert agent_context is not None
        assert agent_context.metadata.get("rag_manager") == mock_rag


class TestTaskToolValidation:
    """Test TaskTool parameter validation."""

    def test_validate_missing_agent_type(self) -> None:
        """Validation fails for missing agent_type."""
        tool = TaskTool()
        valid, error = tool.validate_params(task="do something")
        assert not valid
        assert "agent_type" in error

    def test_validate_missing_task(self) -> None:
        """Validation fails for missing task."""
        tool = TaskTool()
        valid, error = tool.validate_params(agent_type="explore")
        assert not valid
        assert "task" in error

    def test_validate_complete_params(self) -> None:
        """Validation passes for complete params."""
        tool = TaskTool()
        valid, error = tool.validate_params(agent_type="explore", task="find files")
        assert valid
        assert error is None
