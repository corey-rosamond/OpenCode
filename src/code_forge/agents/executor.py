"""
Agent execution engine.

Handles the actual execution of agent tasks using LangChain.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from .result import AgentResult

if TYPE_CHECKING:
    from code_forge.langchain import OpenRouterLLM
    from code_forge.tools import ToolRegistry

    from .base import Agent


logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """Error during agent execution."""

    pass


class AgentExecutor:
    """Executes agent tasks.

    Manages the LLM interaction loop, tool execution,
    and resource tracking for agents.
    """

    def __init__(
        self,
        llm: OpenRouterLLM,
        tool_registry: ToolRegistry,
    ) -> None:
        """Initialize executor.

        Args:
            llm: LLM client for API calls.
            tool_registry: Registry of available tools.
        """
        self.llm = llm
        self.tool_registry = tool_registry

    async def execute(self, agent: Agent) -> AgentResult:
        """Execute an agent task.

        Args:
            agent: Agent to execute.

        Returns:
            AgentResult with execution outcome.
        """
        agent._start_execution()
        start_time = time.time()

        try:
            # Build agent prompt and tools
            system_prompt = self._build_prompt(agent)
            tools = self._filter_tools(agent)

            # Initialize messages
            messages = self._init_messages(agent, system_prompt)

            # Execute agent loop
            result = await self._run_agent_loop(
                agent=agent,
                messages=messages,
                tools=tools,
                start_time=start_time,
            )

            # Update usage and complete
            agent._usage.time_seconds = time.time() - start_time
            agent._complete_execution(result, success=result.success)

            return result

        except asyncio.CancelledError:
            agent._usage.time_seconds = time.time() - start_time
            result = AgentResult.cancelled(
                output=self._get_partial_output(agent._messages)
            )
            agent._complete_execution(result, success=False)
            return result

        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            agent._usage.time_seconds = time.time() - start_time
            result = AgentResult.fail(
                str(e),
                output=self._get_partial_output(agent._messages),
            )
            agent._complete_execution(result, success=False)
            return result

    async def _run_agent_loop(
        self,
        agent: Agent,
        messages: list[dict[str, Any]],
        tools: list[Any],
        start_time: float,
    ) -> AgentResult:
        """Run the agent execution loop.

        Args:
            agent: Agent being executed.
            messages: Message history.
            tools: Available tools.
            start_time: Execution start time.

        Returns:
            AgentResult from execution.
        """
        limits = agent.config.limits
        final_response = ""

        while not agent.is_cancelled:
            # Check resource limits
            agent._usage.time_seconds = time.time() - start_time
            exceeded = agent._usage.exceeds(limits)
            if exceeded:
                return AgentResult.fail(
                    f"Resource limit exceeded: {exceeded}",
                    output=final_response,
                    tokens_used=agent._usage.tokens_used,
                    time_seconds=agent._usage.time_seconds,
                    tool_calls=agent._usage.tool_calls,
                )

            # Increment iteration count
            agent._usage.iterations += 1

            # Call LLM
            response = await self._call_llm(
                messages=messages,
                tools=tools,
                agent=agent,
            )

            # Store messages for history
            agent._messages = messages.copy()

            # Process response
            if response.get("tool_calls"):
                # Handle tool calls
                tool_results = await self._execute_tools(
                    response["tool_calls"],
                    agent,
                )

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": response["tool_calls"],
                })

                # Add tool results
                messages.extend(tool_results)

                agent._report_progress(
                    f"Executed {len(response['tool_calls'])} tool(s)"
                )

            elif response.get("content"):
                # Final response
                final_response = response["content"]
                messages.append({
                    "role": "assistant",
                    "content": final_response,
                })
                break

            else:
                # No content or tools - shouldn't happen
                logger.warning("LLM response had no content or tool calls")
                break

        # Check if cancelled during loop
        if agent.is_cancelled:
            return AgentResult.cancelled(output=final_response)

        # Build successful result
        return AgentResult.ok(
            output=final_response,
            tokens_used=agent._usage.tokens_used,
            time_seconds=agent._usage.time_seconds,
            tool_calls=agent._usage.tool_calls,
        )

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any],
        agent: Agent,
    ) -> dict[str, Any]:
        """Make LLM API call.

        Args:
            messages: Message history.
            tools: Available tools.
            agent: Agent for tracking.

        Returns:
            LLM response dict with content and/or tool_calls.
        """
        model = agent.config.model

        # Convert messages to format expected by LLM
        # The OpenRouterLLM expects LangChain message format
        from langchain_core.messages import (
            AIMessage,
            BaseMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        lc_messages: list[BaseMessage] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    # Convert to LangChain tool call format
                    lc_tool_calls = []
                    for tc in tool_calls:
                        lc_tool_calls.append({
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "args": tc.get("arguments", {}),
                        })
                    lc_messages.append(AIMessage(
                        content=content,
                        tool_calls=lc_tool_calls,
                    ))
                else:
                    lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                ))

        # Bind tools if available
        llm = self.llm
        if tools:
            llm = llm.bind_tools(tools)

        # Make the call
        if model:
            # Override model if specified
            response = await llm.ainvoke(lc_messages, model=model)
        else:
            response = await llm.ainvoke(lc_messages)

        # Track token usage if available
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            agent._usage.tokens_used += usage.get("total_tokens", 0)
        else:
            # Fallback: estimate tokens from content length (rough ~4 chars/token)
            content = response.content if hasattr(response, "content") else ""
            if isinstance(content, str):
                estimated_tokens = len(content) // 4
                agent._usage.tokens_used += estimated_tokens

        # Convert response back to dict format
        result: dict[str, Any] = {"content": response.content}

        if hasattr(response, "tool_calls") and response.tool_calls:
            result["tool_calls"] = []
            for tc in response.tool_calls:
                result["tool_calls"].append({
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "arguments": tc.get("args", {}),
                })

        return result

    async def _execute_tools(
        self,
        tool_calls: list[dict[str, Any]],
        agent: Agent,
    ) -> list[dict[str, Any]]:
        """Execute tool calls.

        Args:
            tool_calls: Tool calls from LLM.
            agent: Agent for tracking.

        Returns:
            Tool result messages.
        """
        results = []

        for call in tool_calls:
            agent._usage.tool_calls += 1

            tool_name = call.get("name", "")
            tool_args = call.get("arguments", {})
            tool_id = call.get("id", "")

            # Track execution timing and status
            start_time = time.time()
            success = False
            error_msg: str | None = None

            try:
                tool = self.tool_registry.get(tool_name)
                if tool is None:
                    result = f"Tool not found: {tool_name}"
                    error_msg = "Tool not found"
                else:
                    # Execute the tool
                    tool_result = await tool.execute(**tool_args)
                    if hasattr(tool_result, "output"):
                        result = tool_result.output
                    else:
                        result = str(tool_result)
                    success = True
            except Exception as e:
                logger.warning(f"Tool execution error for {tool_name}: {e}")
                result = f"Tool error: {e}"
                error_msg = str(e)

            duration = time.time() - start_time

            results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": str(result),
                # Metadata for debugging
                "_metadata": {
                    "tool_name": tool_name,
                    "success": success,
                    "duration_ms": round(duration * 1000, 2),
                    "error": error_msg,
                },
            })

        return results

    def _build_prompt(self, agent: Agent) -> str:
        """Build system prompt for agent.

        Args:
            agent: Agent to build prompt for.

        Returns:
            Complete system prompt.
        """
        parts = [
            f"You are a {agent.config.agent_type} agent.",
            f"Task: {agent.task}",
        ]

        if agent.config.prompt_addition:
            parts.append(agent.config.prompt_addition)

        parts.append(
            "Work autonomously to complete this task. "
            "When finished, provide a clear summary of your findings or actions."
        )

        return "\n\n".join(parts)

    def _filter_tools(self, agent: Agent) -> list[Any]:
        """Get tools available to agent.

        Args:
            agent: Agent to filter tools for.

        Returns:
            List of tool definitions.
        """
        all_tools = self.tool_registry.list_all()

        if agent.config.tools is None:
            # All tools allowed
            return list(all_tools)

        # Filter to allowed tools
        allowed = set(agent.config.tools)
        return [t for t in all_tools if t.name in allowed]

    def _init_messages(
        self,
        agent: Agent,
        system_prompt: str,
    ) -> list[dict[str, Any]]:
        """Initialize message history.

        Args:
            agent: Agent to init for.
            system_prompt: System prompt to use.

        Returns:
            Initial message list.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Include parent context if configured
        if agent.config.inherit_context and agent.context.parent_messages:
            # Add summary of parent context
            summary = self._summarize_context(agent.context.parent_messages)
            messages.append({
                "role": "system",
                "content": f"Parent context summary:\n{summary}",
            })

        # Add the task as user message
        messages.append({
            "role": "user",
            "content": agent.task,
        })

        return messages

    def _summarize_context(self, messages: list[dict[str, Any]]) -> str:
        """Summarize parent context messages.

        Args:
            messages: Parent messages.

        Returns:
            Summary text.
        """
        # Simple summary - just last few messages
        recent = messages[-5:] if len(messages) > 5 else messages
        parts = []

        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            parts.append(f"[{role}]: {content}")

        return "\n".join(parts)

    def _get_partial_output(self, messages: list[dict[str, Any]]) -> str:
        """Extract partial output from messages.

        Args:
            messages: Message history.

        Returns:
            Last assistant content or empty string.
        """
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                content = msg["content"]
                return str(content) if content else ""
        return ""
