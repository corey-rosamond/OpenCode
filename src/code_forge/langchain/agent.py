"""Agent executor for tool-calling workflows."""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage

from code_forge.core.logging import get_logger
from code_forge.langchain.memory import ConversationMemory
from code_forge.langchain.tools import LangChainToolAdapter

logger = get_logger("agent")

if TYPE_CHECKING:
    from code_forge.langchain.llm import OpenRouterLLM
    from code_forge.llm.models import Message, TokenUsage


class AgentEventType(str, Enum):
    """Types of events during agent execution."""

    LLM_START = "llm_start"
    LLM_CHUNK = "llm_chunk"
    LLM_END = "llm_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    AGENT_END = "agent_end"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Event during agent execution."""

    type: AgentEventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallRecord:
    """Record of a tool call during agent execution."""

    id: str
    name: str
    arguments: dict[str, Any]
    result: str
    success: bool
    duration: float


@dataclass
class AgentResult:
    """Result of agent execution."""

    output: str
    messages: list[Message]
    tool_calls: list[ToolCallRecord]
    usage: TokenUsage
    iterations: int
    duration: float
    stopped_reason: str  # "complete", "max_iterations", "timeout", "error"


class CodeForgeAgent:
    """
    Agent executor for tool-calling workflows.

    Implements a ReAct-style agent loop that:
    1. Sends messages to LLM with tool definitions
    2. Parses tool calls from response
    3. Executes tools
    4. Adds tool results to conversation
    5. Continues until done or limit reached

    Example:
        ```python
        from code_forge.langchain import OpenRouterLLM, CodeForgeAgent
        from code_forge.langchain.memory import ConversationMemory

        llm = OpenRouterLLM(client=client, model="anthropic/claude-3-opus")
        memory = ConversationMemory()
        tools = [ReadTool(), WriteTool(), BashTool()]

        agent = CodeForgeAgent(
            llm=llm,
            tools=tools,
            memory=memory,
            max_iterations=10,
        )

        result = await agent.run("Read the file at /tmp/test.txt")
        print(result.output)
        ```
    """

    def __init__(
        self,
        llm: OpenRouterLLM,
        tools: list[Any],
        memory: ConversationMemory | None = None,
        max_iterations: int = 10,
        timeout: float = 300.0,
        iteration_timeout: float = 60.0,
        tool_timeout: float = 30.0,
        tool_max_retries: int = 2,
    ) -> None:
        """
        Initialize agent.

        Args:
            llm: LLM to use for generation
            tools: List of tools available to the agent
            memory: Conversation memory (created if not provided)
            max_iterations: Maximum tool-calling iterations
            timeout: Overall timeout in seconds
            iteration_timeout: Timeout per iteration in seconds
            tool_timeout: Timeout for individual tool execution in seconds
            tool_max_retries: Max retries for transient tool failures (default 2)
        """
        self.llm = llm
        self.tools = tools
        self.memory = memory or ConversationMemory()
        self.max_iterations = max_iterations
        self.timeout = timeout
        self.iteration_timeout = iteration_timeout
        self.tool_timeout = tool_timeout
        self.tool_max_retries = tool_max_retries

        # Create tool lookup
        self._tool_map: dict[str, Any] = {}
        for tool in tools:
            if hasattr(tool, "name"):
                self._tool_map[tool.name] = tool

        # Bind tools to LLM
        self._bound_llm = self.llm.bind_tools(tools)

    async def _execute_tool_with_retry(
        self,
        tool: Any,
        tool_name: str,
        tool_args: dict,
    ) -> tuple[str, bool]:
        """Execute a tool with retry logic for transient failures.

        Args:
            tool: The tool to execute
            tool_name: Name of the tool (for error messages)
            tool_args: Arguments to pass to the tool

        Returns:
            Tuple of (result_string, success_bool)

        Retries on:
            - TimeoutError (transient network/resource issues)
            - OSError (transient system issues)
            - ConnectionError (network issues)

        Does NOT retry on:
            - ValueError, TypeError (argument/logic errors)
            - PermissionError (won't resolve with retry)
            - FileNotFoundError (won't resolve with retry)
        """
        import random

        last_error: Exception | None = None
        retryable_errors = (TimeoutError, OSError, ConnectionError)

        for attempt in range(self.tool_max_retries + 1):
            try:
                if isinstance(tool, LangChainToolAdapter):
                    result = await asyncio.wait_for(
                        tool._arun(**tool_args),
                        timeout=self.tool_timeout,
                    )
                elif hasattr(tool, "ainvoke"):
                    result = await asyncio.wait_for(
                        tool.ainvoke(tool_args),
                        timeout=self.tool_timeout,
                    )
                else:
                    # Sync tools run in executor with timeout
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, lambda: tool.invoke(tool_args)
                        ),
                        timeout=self.tool_timeout,
                    )
                return str(result), True

            except retryable_errors as e:
                last_error = e
                if attempt < self.tool_max_retries:
                    # Exponential backoff with jitter
                    wait_time = (0.5 * (2 ** attempt)) * random.uniform(0.5, 1.5)
                    logger.warning(
                        f"Tool {tool_name} failed (attempt {attempt + 1}), "
                        f"retrying in {wait_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                continue

            except TimeoutError:
                error_msg = f"Tool {tool_name} timed out after {self.tool_timeout}s"
                logger.error(error_msg)
                return error_msg, False

            except Exception as e:
                # Non-retryable error - log with full traceback for debugging
                error_msg = f"Error executing {tool_name}: {e}"
                logger.error(error_msg, exc_info=True)
                return error_msg, False

        # All retries exhausted
        error_msg = f"Tool {tool_name} failed after {self.tool_max_retries + 1} attempts: {last_error}"
        logger.error(error_msg)
        return error_msg, False

    async def run(
        self,
        input: str,
        *,
        callbacks: list[BaseCallbackHandler] | None = None,
    ) -> AgentResult:
        """
        Run the agent to completion.

        Args:
            input: User input to process
            callbacks: Optional callback handlers

        Returns:
            AgentResult with output and metadata
        """
        from code_forge.llm.models import Message, TokenUsage

        start_time = time.time()
        tool_call_records: list[ToolCallRecord] = []
        total_usage = TokenUsage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )
        iterations = 0
        stopped_reason = "complete"

        # Add user message
        self.memory.add_message(Message.user(input))

        try:
            while iterations < self.max_iterations:
                # Check overall timeout
                if time.time() - start_time > self.timeout:
                    stopped_reason = "timeout"
                    break

                iterations += 1

                # Get LLM response
                messages = self.memory.to_langchain_messages()

                try:
                    response = await asyncio.wait_for(
                        self._bound_llm.ainvoke(
                            messages,
                            config={"callbacks": callbacks} if callbacks else None,
                        ),
                        timeout=self.iteration_timeout,
                    )
                except TimeoutError:
                    stopped_reason = "timeout"
                    break

                # Track usage from response metadata
                if hasattr(response, "response_metadata"):
                    usage_data = response.response_metadata.get("usage", {})
                    total_usage.prompt_tokens += usage_data.get("prompt_tokens", 0)
                    total_usage.completion_tokens += usage_data.get(
                        "completion_tokens", 0
                    )
                    total_usage.total_tokens += usage_data.get("total_tokens", 0)

                # Check for tool calls
                if isinstance(response, AIMessage) and response.tool_calls:
                    # Add assistant message to memory
                    from code_forge.langchain.messages import langchain_to_forge

                    self.memory.add_message(langchain_to_forge(response))

                    # Execute tools
                    for tool_call in response.tool_calls:
                        tool_start = time.time()
                        tool_name = tool_call["name"]
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call["id"]

                        # Validate tool_args is a dict (security: LLM could send other types)
                        if not isinstance(tool_args, dict):
                            result = f"Invalid arguments for {tool_name}: expected dict, got {type(tool_args).__name__}"
                            success = False
                            tool_duration = time.time() - tool_start
                            tool_call_records.append(
                                ToolCallRecord(
                                    id=tool_id or "",
                                    name=tool_name,
                                    arguments={"_raw": str(tool_args)[:100]},
                                    result=result,
                                    success=success,
                                    duration=tool_duration,
                                )
                            )
                            self.memory.add_message(
                                Message.tool_result(tool_id or "", result)
                            )
                            continue

                        tool = self._tool_map.get(tool_name)
                        if tool:
                            # Validate arguments against tool schema (if available)
                            if isinstance(tool, LangChainToolAdapter) and tool.args_schema:
                                try:
                                    # Pydantic validation
                                    tool.args_schema(**tool_args)
                                except Exception as validation_error:
                                    result = f"Invalid arguments for {tool_name}: {validation_error}"
                                    success = False
                                    tool_duration = time.time() - tool_start
                                    tool_call_records.append(
                                        ToolCallRecord(
                                            id=tool_id or "",
                                            name=tool_name,
                                            arguments=tool_args,
                                            result=result,
                                            success=success,
                                            duration=tool_duration,
                                        )
                                    )
                                    self.memory.add_message(
                                        Message.tool_result(tool_id or "", result)
                                    )
                                    continue

                            # Execute tool with retry logic
                            result, success = await self._execute_tool_with_retry(
                                tool, tool_name, tool_args
                            )
                        else:
                            result = f"Unknown tool: {tool_name}"
                            success = False
                            logger.error(f"Unknown tool requested: {tool_name}")

                        tool_duration = time.time() - tool_start

                        # Log tool result
                        if success:
                            logger.debug(
                                f"Tool {tool_name} completed in {tool_duration:.1f}s"
                            )
                        else:
                            logger.error(
                                f"Tool {tool_name} failed after {tool_duration:.1f}s: {result}"
                            )

                        # Record tool call
                        tool_call_records.append(
                            ToolCallRecord(
                                id=tool_id or "",
                                name=tool_name,
                                arguments=tool_args,
                                result=result,
                                success=success,
                                duration=tool_duration,
                            )
                        )

                        # Add tool result to memory
                        self.memory.add_message(
                            Message.tool_result(tool_id or "", result)
                        )

                else:
                    # No tool calls - agent is done
                    content = (
                        response.content
                        if hasattr(response, "content")
                        else str(response)
                    )
                    # Ensure content is string for Message.assistant
                    if isinstance(content, list):
                        content = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                    self.memory.add_message(Message.assistant(str(content) if content else ""))
                    break

            else:
                # Max iterations reached
                stopped_reason = "max_iterations"

        except Exception as e:
            stopped_reason = f"error: {e}"

        # Get final output
        all_messages = self.memory.get_messages()
        output = ""
        if all_messages:
            last_msg = all_messages[-1]
            if last_msg.content:
                msg_content: Any = last_msg.content
                if isinstance(msg_content, list):
                    output = "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in msg_content
                    )
                else:
                    output = str(msg_content)

        return AgentResult(
            output=output,
            messages=all_messages,
            tool_calls=tool_call_records,
            usage=total_usage,
            iterations=iterations,
            duration=time.time() - start_time,
            stopped_reason=stopped_reason,
        )

    def _assemble_tool_calls(self, chunks: list[dict]) -> list[dict]:
        """Assemble complete tool calls from streamed chunks.

        Tool call chunks arrive with an index indicating which tool call they belong to.
        Each chunk may contain partial name and/or args that need to be concatenated.

        Args:
            chunks: List of tool call chunks from streaming

        Returns:
            List of complete tool calls with name, args, and id
        """
        import json
        import uuid

        if not chunks:
            return []

        # Group chunks by index
        by_index: dict[int, list[dict]] = {}
        for chunk in chunks:
            idx = chunk.get("index", 0)
            if idx not in by_index:
                by_index[idx] = []
            by_index[idx].append(chunk)

        # Assemble each tool call
        tool_calls = []
        for idx in sorted(by_index.keys()):
            tool_chunks = by_index[idx]

            name = ""
            args_str = ""
            tool_id = None

            for chunk in tool_chunks:
                # Tool name comes as a single value, not streamed in pieces
                # Use first non-empty name found (don't concatenate)
                if chunk.get("name") and not name:
                    raw_name = chunk["name"]

                    # Validate tool name format - should be alphanumeric with underscores
                    # Valid examples: "Bash", "read_file", "WebSearch2"
                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", raw_name):
                        # Log warning for malformed tool names
                        logger.warning(
                            f"Malformed tool name received: {raw_name!r}. "
                            f"Attempting to extract valid name."
                        )
                        # Try to extract a valid tool name from malformed data
                        # e.g., 'Bash" description="...' -> 'Bash'
                        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)", raw_name)
                        if match:
                            name = match.group(1)
                            logger.debug(f"Extracted tool name: {name!r}")
                        else:
                            logger.error(
                                f"Could not extract valid tool name from: {raw_name!r}. "
                                f"Skipping this tool call."
                            )
                            continue
                    else:
                        name = raw_name.strip()
                # Args are streamed as JSON string pieces, need concatenation
                if chunk.get("args"):
                    args_str += chunk["args"]
                # ID comes as single value
                if chunk.get("id") and not tool_id:
                    tool_id = chunk["id"]

            # Parse args JSON
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse tool args as JSON for '{name}': {e}. "
                    f"Storing as raw string."
                )
                args = {"raw": args_str}

            if name:
                tool_calls.append({
                    "name": name,
                    "args": args,
                    "id": tool_id or f"call_{uuid.uuid4().hex[:8]}",
                })

        return tool_calls

    async def stream(
        self,
        input: str,
        *,
        callbacks: list[BaseCallbackHandler] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        Stream agent execution with events.

        Args:
            input: User input to process
            callbacks: Optional callback handlers

        Yields:
            AgentEvent for each significant occurrence
        """
        from code_forge.llm.models import Message

        start_time = time.time()
        tool_call_records: list[ToolCallRecord] = []
        iterations = 0
        # Track totals across ALL iterations
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # Add user message
        self.memory.add_message(Message.user(input))

        try:
            while iterations < self.max_iterations:
                # Check timeout
                if time.time() - start_time > self.timeout:
                    yield AgentEvent(
                        type=AgentEventType.ERROR,
                        data={"error": "timeout", "iterations": iterations},
                    )
                    break

                iterations += 1

                # Track per-iteration usage (take LAST value, don't accumulate within iteration)
                # Some providers send cumulative usage on every chunk
                iteration_prompt_tokens = 0
                iteration_completion_tokens = 0

                # Yield LLM start event
                yield AgentEvent(
                    type=AgentEventType.LLM_START,
                    data={"iteration": iterations},
                )

                # Stream LLM response
                messages = self.memory.to_langchain_messages()
                accumulated_content = ""
                accumulated_reasoning = ""
                tool_call_chunks: list[dict] = []

                async for chunk in self._bound_llm.astream(
                    messages,
                    config={"callbacks": callbacks} if callbacks else None,
                ):
                    # Accumulate reasoning content (DeepSeek/Kimi thinking tokens)
                    reasoning_content = None
                    if hasattr(chunk, "additional_kwargs"):
                        reasoning_content = chunk.additional_kwargs.get("reasoning_content")
                    if reasoning_content:
                        accumulated_reasoning += str(reasoning_content)
                        yield AgentEvent(
                            type=AgentEventType.LLM_CHUNK,
                            data={"content": reasoning_content, "is_reasoning": True},
                        )

                    # Accumulate content
                    if hasattr(chunk, "content") and chunk.content:
                        chunk_content = chunk.content
                        if isinstance(chunk_content, list):
                            chunk_content = "".join(
                                p.get("text", "") if isinstance(p, dict) else str(p)
                                for p in chunk_content
                            )
                        accumulated_content += str(chunk_content)
                        yield AgentEvent(
                            type=AgentEventType.LLM_CHUNK,
                            data={"content": chunk_content},
                        )

                    # Accumulate tool call chunks
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        tool_call_chunks.extend(chunk.tool_call_chunks)

                    # Track token usage from streaming chunks
                    # IMPORTANT: Take LAST value, don't accumulate within iteration
                    # Some providers (DeepSeek, Kimi) send cumulative usage on every chunk
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        usage = chunk.usage_metadata
                        # Handle both dict and object access patterns
                        if isinstance(usage, dict):
                            # Replace, don't add - usage is cumulative within the iteration
                            iteration_prompt_tokens = usage.get("input_tokens", 0)
                            iteration_completion_tokens = usage.get("output_tokens", 0)
                        else:
                            if hasattr(usage, "input_tokens"):
                                iteration_prompt_tokens = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                iteration_completion_tokens = usage.output_tokens

                # Add this iteration's final usage to the totals
                total_prompt_tokens += iteration_prompt_tokens
                total_completion_tokens += iteration_completion_tokens

                # Yield LLM end event
                yield AgentEvent(
                    type=AgentEventType.LLM_END,
                    data={
                        "content": accumulated_content,
                        "reasoning": accumulated_reasoning,
                    },
                )

                # Assemble tool calls from streamed chunks (avoids duplicate API call)
                assembled_tool_calls = self._assemble_tool_calls(tool_call_chunks)

                # Combine reasoning and content for the full response
                # (reasoning comes first as the model's thinking process)
                full_content = accumulated_content
                if accumulated_reasoning and not accumulated_content:
                    # If only reasoning but no content, use reasoning as content
                    full_content = accumulated_reasoning

                # Build response message from streamed content
                response = AIMessage(
                    content=full_content,
                    tool_calls=assembled_tool_calls,
                )

                if assembled_tool_calls:
                    from code_forge.langchain.messages import langchain_to_forge

                    self.memory.add_message(langchain_to_forge(response))

                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        tool_id = tool_call["id"]

                        yield AgentEvent(
                            type=AgentEventType.TOOL_START,
                            data={"name": tool_name, "arguments": tool_args},
                        )

                        tool_start = time.time()
                        tool = self._tool_map.get(tool_name)

                        if tool:
                            # Execute tool with retry logic
                            result, success = await self._execute_tool_with_retry(
                                tool, tool_name, tool_args
                            )
                        else:
                            result = f"Unknown tool: {tool_name}"
                            success = False
                            logger.error(f"Unknown tool requested: {tool_name}")

                        tool_duration = time.time() - tool_start

                        # Log tool result
                        if success:
                            logger.debug(
                                f"Tool {tool_name} completed in {tool_duration:.1f}s"
                            )
                        else:
                            logger.error(
                                f"Tool {tool_name} failed after {tool_duration:.1f}s: {result}"
                            )

                        yield AgentEvent(
                            type=AgentEventType.TOOL_END,
                            data={
                                "name": tool_name,
                                "result": result,
                                "success": success,
                                "duration": tool_duration,
                            },
                        )

                        tool_call_records.append(
                            ToolCallRecord(
                                id=tool_id or "",
                                name=tool_name,
                                arguments=tool_args,
                                result=result,
                                success=success,
                                duration=tool_duration,
                            )
                        )

                        self.memory.add_message(
                            Message.tool_result(tool_id or "", result)
                        )
                else:
                    # No tool calls - done
                    self.memory.add_message(Message.assistant(full_content))
                    break

            # Yield completion event
            yield AgentEvent(
                type=AgentEventType.AGENT_END,
                data={
                    "iterations": iterations,
                    "tool_calls": len(tool_call_records),
                    "duration": time.time() - start_time,
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens,
                    "total_tokens": total_prompt_tokens + total_completion_tokens,
                },
            )

        except Exception as e:
            logger.error(f"Agent stream error: {e}", exc_info=True)
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"error": str(e)},
            )

    def reset(self) -> None:
        """Reset agent state (clears memory history)."""
        self.memory.clear_history()
