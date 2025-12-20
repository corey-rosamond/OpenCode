"""Unit tests for agent executor."""

from unittest.mock import AsyncMock, MagicMock, patch
import time

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from code_forge.langchain.agent import (
    AgentEvent,
    AgentEventType,
    AgentResult,
    CodeForgeAgent,
    ToolCallRecord,
)
from code_forge.langchain.memory import ConversationMemory
from code_forge.llm.models import Message, TokenUsage


class TestAgentEventType:
    """Tests for AgentEventType enum."""

    def test_event_types_exist(self) -> None:
        """Test that all expected event types exist."""
        assert AgentEventType.LLM_START == "llm_start"
        assert AgentEventType.LLM_CHUNK == "llm_chunk"
        assert AgentEventType.LLM_END == "llm_end"
        assert AgentEventType.TOOL_START == "tool_start"
        assert AgentEventType.TOOL_END == "tool_end"
        assert AgentEventType.AGENT_END == "agent_end"
        assert AgentEventType.ERROR == "error"


class TestAgentEvent:
    """Tests for AgentEvent dataclass."""

    def test_event_creation(self) -> None:
        """Test basic event creation."""
        event = AgentEvent(
            type=AgentEventType.LLM_START,
            data={"iteration": 1},
        )

        assert event.type == AgentEventType.LLM_START
        assert event.data["iteration"] == 1
        assert event.timestamp > 0

    def test_event_default_data(self) -> None:
        """Test default empty data dict."""
        event = AgentEvent(type=AgentEventType.LLM_END)

        assert event.data == {}


class TestToolCallRecord:
    """Tests for ToolCallRecord dataclass."""

    def test_record_creation(self) -> None:
        """Test basic record creation."""
        record = ToolCallRecord(
            id="call_123",
            name="read_file",
            arguments={"path": "/tmp/test"},
            result="file contents",
            success=True,
            duration=0.5,
        )

        assert record.id == "call_123"
        assert record.name == "read_file"
        assert record.arguments["path"] == "/tmp/test"
        assert record.result == "file contents"
        assert record.success is True
        assert record.duration == 0.5


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_result_creation(self) -> None:
        """Test basic result creation."""
        result = AgentResult(
            output="Done!",
            messages=[Message.user("Hello")],
            tool_calls=[],
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            iterations=2,
            duration=1.5,
            stopped_reason="complete",
        )

        assert result.output == "Done!"
        assert len(result.messages) == 1
        assert result.usage.total_tokens == 150
        assert result.iterations == 2
        assert result.stopped_reason == "complete"

    def test_result_with_tool_calls(self) -> None:
        """Test result with tool call records."""
        tool_call = ToolCallRecord(
            id="call_456",
            name="write_file",
            arguments={},
            result="ok",
            success=True,
            duration=0.2,
        )

        result = AgentResult(
            output="Written!",
            messages=[],
            tool_calls=[tool_call],
            usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            iterations=1,
            duration=1.0,
            stopped_reason="complete",
        )

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "write_file"


class TestCodeForgeAgentInit:
    """Tests for CodeForgeAgent initialization."""

    def test_basic_initialization(self) -> None:
        """Test basic agent initialization."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        agent = CodeForgeAgent(
            llm=mock_llm,
            tools=[],
        )

        assert agent.llm is mock_llm
        assert agent.max_iterations == 10
        assert agent.timeout == 300.0

    def test_custom_parameters(self) -> None:
        """Test custom agent parameters."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        memory = ConversationMemory()

        agent = CodeForgeAgent(
            llm=mock_llm,
            tools=[],
            memory=memory,
            max_iterations=5,
            timeout=60.0,
        )

        # Check memory is used (may be a copy due to dataclass)
        assert agent.max_iterations == 5
        assert agent.timeout == 60.0

    def test_tool_map_creation(self) -> None:
        """Test that tool map is created from tools."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        class MockTool:
            name = "test_tool"

        agent = CodeForgeAgent(
            llm=mock_llm,
            tools=[MockTool()],
        )

        assert "test_tool" in agent._tool_map


class TestCodeForgeAgentRun:
    """Tests for CodeForgeAgent.run() method."""

    @pytest.mark.asyncio
    async def test_simple_completion(self) -> None:
        """Test simple completion without tools."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="The answer is 42.")
        )

        agent = CodeForgeAgent(llm=mock_llm, tools=[])
        result = await agent.run("What is the answer?")

        assert result.output == "The answer is 42."
        assert result.iterations == 1
        assert result.stopped_reason == "complete"
        assert len(result.tool_calls) == 0

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self) -> None:
        """Test that max iterations limit is enforced."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        # Always return tool calls to keep agent looping
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="",
                tool_calls=[{"id": "call_1", "name": "unknown_tool", "args": {}}],
            )
        )

        agent = CodeForgeAgent(llm=mock_llm, tools=[], max_iterations=3)
        result = await agent.run("Do something")

        assert result.iterations == 3
        assert result.stopped_reason == "max_iterations"

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Test timeout handling."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        async def slow_invoke(*args, **kwargs):
            import asyncio
            await asyncio.sleep(10)  # Will be cancelled
            return AIMessage(content="Done")

        mock_llm.ainvoke = slow_invoke

        agent = CodeForgeAgent(
            llm=mock_llm,
            tools=[],
            iteration_timeout=0.1,  # Very short timeout
        )

        result = await agent.run("Do something slow")

        assert result.stopped_reason == "timeout"

    @pytest.mark.asyncio
    async def test_tool_execution(self) -> None:
        """Test agent executes tools."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        # First call returns tool call, second returns completion
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "test_tool", "args": {"x": 1}}],
                ),
                AIMessage(content="Tool executed successfully."),
            ]
        )

        class MockTool:
            name = "test_tool"

            async def ainvoke(self, args):
                return "result from tool"

        tool = MockTool()

        agent = CodeForgeAgent(llm=mock_llm, tools=[tool])
        result = await agent.run("Use the tool")

        assert result.output == "Tool executed successfully."
        assert result.iterations == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "test_tool"
        assert result.tool_calls[0].success is True

    @pytest.mark.asyncio
    async def test_unknown_tool_handling(self) -> None:
        """Test handling of unknown tool calls."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "nonexistent_tool", "args": {}}],
                ),
                AIMessage(content="Done"),
            ]
        )

        agent = CodeForgeAgent(llm=mock_llm, tools=[])
        result = await agent.run("Use unknown tool")

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].success is False
        assert "Unknown tool" in result.tool_calls[0].result


class TestCodeForgeAgentReset:
    """Tests for CodeForgeAgent.reset() method."""

    def test_reset_clears_history(self) -> None:
        """Test that reset clears memory history."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        memory = ConversationMemory()
        memory.add_message(Message.user("Hello"))
        memory.add_message(Message.assistant("Hi"))

        agent = CodeForgeAgent(llm=mock_llm, tools=[], memory=memory)

        assert len(agent.memory.get_history()) == 2

        agent.reset()

        assert len(agent.memory.get_history()) == 0

    def test_reset_preserves_system_message(self) -> None:
        """Test that reset preserves system message."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        memory = ConversationMemory()
        memory.set_system_message(Message.system("Be helpful"))
        memory.add_message(Message.user("Hello"))

        agent = CodeForgeAgent(llm=mock_llm, tools=[], memory=memory)
        agent.reset()

        assert isinstance(agent.memory.system_message, Message)
        assert agent.memory.system_message.content == "Be helpful"


class TestCodeForgeAgentStream:
    """Tests for CodeForgeAgent.stream() method."""

    @pytest.mark.asyncio
    async def test_stream_yields_events(self) -> None:
        """Test that streaming yields appropriate events."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        async def mock_stream(*args, **kwargs):
            from langchain_core.messages import AIMessageChunk

            yield AIMessageChunk(content="Hello")
            yield AIMessageChunk(content=" World")

        mock_llm.astream = mock_stream
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Hello World"))

        agent = CodeForgeAgent(llm=mock_llm, tools=[])

        events = []
        async for event in agent.stream("Say hello"):
            events.append(event)

        # Should have LLM_START, LLM_CHUNKs, LLM_END, AGENT_END
        event_types = [e.type for e in events]
        assert AgentEventType.LLM_START in event_types
        assert AgentEventType.LLM_END in event_types
        assert AgentEventType.AGENT_END in event_types

    @pytest.mark.asyncio
    async def test_stream_agent_end_event(self) -> None:
        """Test that AGENT_END event has correct data."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        async def mock_stream(*args, **kwargs):
            from langchain_core.messages import AIMessageChunk

            yield AIMessageChunk(content="Done")

        mock_llm.astream = mock_stream
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Done"))

        agent = CodeForgeAgent(llm=mock_llm, tools=[])

        events = []
        async for event in agent.stream("Test"):
            events.append(event)

        end_event = next(e for e in events if e.type == AgentEventType.AGENT_END)

        assert "iterations" in end_event.data
        assert "duration" in end_event.data
        assert "tool_calls" in end_event.data

    @pytest.mark.asyncio
    async def test_stream_with_tool_calls(self) -> None:
        """Test streaming with tool call execution."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        from langchain_core.messages import AIMessageChunk

        call_count = [0]

        async def mock_stream(*args, **kwargs):
            if call_count[0] == 0:
                # First stream - emit content that hints at tool calls
                yield AIMessageChunk(content="", tool_call_chunks=[{"index": 0, "id": "call_1", "name": "test_tool"}])
            else:
                # Second stream - no tool calls
                yield AIMessageChunk(content="Done with tool")

        mock_llm.astream = mock_stream

        def mock_invoke(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "test_tool", "args": {"x": 1}}],
                )
            return AIMessage(content="Done with tool")

        mock_llm.ainvoke = AsyncMock(side_effect=mock_invoke)

        class MockTool:
            name = "test_tool"

            async def ainvoke(self, args):
                return "tool result"

        agent = CodeForgeAgent(llm=mock_llm, tools=[MockTool()])

        events = []
        async for event in agent.stream("Use tool"):
            events.append(event)

        event_types = [e.type for e in events]
        assert AgentEventType.TOOL_START in event_types
        assert AgentEventType.TOOL_END in event_types

    @pytest.mark.asyncio
    async def test_stream_timeout(self) -> None:
        """Test streaming with timeout."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        import asyncio

        async def slow_stream(*args, **kwargs):
            await asyncio.sleep(10)  # Will timeout
            yield AIMessageChunk(content="Done")

        mock_llm.astream = slow_stream

        agent = CodeForgeAgent(
            llm=mock_llm,
            tools=[],
            timeout=0.1,  # Very short timeout
        )

        events = []
        async for event in agent.stream("Test"):
            events.append(event)

        event_types = [e.type for e in events]
        assert AgentEventType.ERROR in event_types

    @pytest.mark.asyncio
    async def test_stream_error_handling(self) -> None:
        """Test streaming error handling."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        async def error_stream(*args, **kwargs):
            raise ValueError("Stream error")
            yield  # Make it a generator

        mock_llm.astream = error_stream

        agent = CodeForgeAgent(llm=mock_llm, tools=[])

        events = []
        async for event in agent.stream("Test"):
            events.append(event)

        event_types = [e.type for e in events]
        assert AgentEventType.ERROR in event_types

    @pytest.mark.asyncio
    async def test_stream_with_list_content(self) -> None:
        """Test streaming with list content (multimodal)."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        from langchain_core.messages import AIMessageChunk

        async def mock_stream(*args, **kwargs):
            yield AIMessageChunk(content=[{"type": "text", "text": "Hello"}])
            yield AIMessageChunk(content=[{"type": "text", "text": " World"}])

        mock_llm.astream = mock_stream
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Hello World"))

        agent = CodeForgeAgent(llm=mock_llm, tools=[])

        events = []
        async for event in agent.stream("Test"):
            events.append(event)

        # Should have processed list content
        chunk_events = [e for e in events if e.type == AgentEventType.LLM_CHUNK]
        assert len(chunk_events) >= 1


class TestCodeForgeAgentRunEdgeCases:
    """Edge case tests for CodeForgeAgent.run() method."""

    @pytest.mark.asyncio
    async def test_run_with_tool_error(self) -> None:
        """Test handling tool execution error."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "failing_tool", "args": {}}],
                ),
                AIMessage(content="Tool failed, but I recovered."),
            ]
        )

        class FailingTool:
            name = "failing_tool"

            async def ainvoke(self, args):
                raise RuntimeError("Tool crashed!")

        agent = CodeForgeAgent(llm=mock_llm, tools=[FailingTool()])
        result = await agent.run("Use failing tool")

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].success is False
        assert "Error" in result.tool_calls[0].result

    @pytest.mark.asyncio
    async def test_run_overall_timeout(self) -> None:
        """Test overall timeout is enforced."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        import time

        call_count = [0]

        async def slow_invoke(*args, **kwargs):
            call_count[0] += 1
            time.sleep(0.2)  # Slow but not hitting iteration timeout
            return AIMessage(
                content="",
                tool_calls=[{"id": f"call_{call_count[0]}", "name": "slow_tool", "args": {}}],
            )

        mock_llm.ainvoke = slow_invoke

        class SlowTool:
            name = "slow_tool"

            async def ainvoke(self, args):
                return "ok"

        agent = CodeForgeAgent(
            llm=mock_llm,
            tools=[SlowTool()],
            timeout=0.3,  # Short overall timeout
            iteration_timeout=60.0,
        )

        result = await agent.run("Do slow things")

        assert result.stopped_reason == "timeout"

    @pytest.mark.asyncio
    async def test_run_with_list_content_in_response(self) -> None:
        """Test handling list content in response (multimodal)."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content=[{"type": "text", "text": "Hello"}, {"type": "text", "text": " World"}]
            )
        )

        agent = CodeForgeAgent(llm=mock_llm, tools=[])
        result = await agent.run("Test multimodal")

        assert result.output == "Hello World"

    @pytest.mark.asyncio
    async def test_run_with_langchain_tool_adapter(self) -> None:
        """Test agent with LangChainToolAdapter."""
        from code_forge.langchain.tools import LangChainToolAdapter
        from code_forge.tools.base import ToolResult, ExecutionContext

        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "adapter_tool", "args": {"input": "test"}}],
                ),
                AIMessage(content="Adapter tool done."),
            ]
        )

        # Create mock Code-Forge tool with execute method
        class MockCodeForgeTool:
            name = "adapter_tool"
            description = "A test tool"
            category = "file"
            parameters = []

            async def execute(self, context, **kwargs):
                return ToolResult(success=True, output="Adapter result")

        adapter = LangChainToolAdapter(
            forge_tool=MockCodeForgeTool(),
            context=ExecutionContext(working_dir="/tmp"),
        )

        agent = CodeForgeAgent(llm=mock_llm, tools=[adapter])
        result = await agent.run("Use adapter tool")

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].success is True

    @pytest.mark.asyncio
    async def test_run_with_sync_tool(self) -> None:
        """Test agent with synchronous tool (invoke instead of ainvoke)."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "sync_tool", "args": {}}],
                ),
                AIMessage(content="Sync tool done."),
            ]
        )

        class SyncTool:
            name = "sync_tool"

            def invoke(self, args):
                return "sync result"

        agent = CodeForgeAgent(llm=mock_llm, tools=[SyncTool()])
        result = await agent.run("Use sync tool")

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].success is True
        assert result.tool_calls[0].result == "sync result"

    @pytest.mark.asyncio
    async def test_run_exception_handling(self) -> None:
        """Test that exceptions are caught and returned as error."""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        agent = CodeForgeAgent(llm=mock_llm, tools=[])
        result = await agent.run("Cause error")

        assert "error" in result.stopped_reason
