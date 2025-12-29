"""LangChain LLM wrapper for OpenRouter client."""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import PrivateAttr

from code_forge.langchain.messages import (
    langchain_messages_to_forge,
    forge_to_langchain,
)

if TYPE_CHECKING:
    from code_forge.llm.models import CompletionRequest


class OpenRouterLLM(BaseChatModel):
    """
    LangChain chat model wrapper for OpenRouter API.

    This class bridges LangChain's BaseChatModel interface with
    Code-Forge's OpenRouterClient, enabling use of OpenRouter's
    400+ models through LangChain's ecosystem.

    Example:
        ```python
        from code_forge.llm import OpenRouterClient
        from code_forge.langchain import OpenRouterLLM

        client = OpenRouterClient(api_key="sk-or-xxx")
        llm = OpenRouterLLM(client=client, model="anthropic/claude-3-opus")

        response = llm.invoke([HumanMessage(content="Hello!")])
        ```
    """

    # Pydantic fields
    client: Any  # OpenRouterClient - use Any to avoid Pydantic issues
    model: str
    temperature: float = 1.0
    max_tokens: int | None = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None

    # Internal state - use PrivateAttr to avoid mutable default issues
    _bound_tools: list[Any] = PrivateAttr(default_factory=list)

    # Maximum number of tools that can be bound
    MAX_BOUND_TOOLS: ClassVar[int] = 64

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type."""
        return "openrouter"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        """Return parameters that identify this LLM configuration."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }

    def _build_request(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> CompletionRequest:
        """Build a CompletionRequest from LangChain messages."""
        from code_forge.llm.models import CompletionRequest

        forge_messages = langchain_messages_to_forge(messages)

        # Merge stop sequences (clearer than list() + extend())
        all_stops = list(self.stop or []) + list(stop or [])

        # Build tools list if bound
        tools = None
        if self._bound_tools:
            tools = [
                t.to_dict() if hasattr(t, "to_dict") else t for t in self._bound_tools
            ]

        return CompletionRequest(
            model=self.model,
            messages=forge_messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            top_p=kwargs.get("top_p", self.top_p),
            frequency_penalty=kwargs.get("frequency_penalty", self.frequency_penalty),
            presence_penalty=kwargs.get("presence_penalty", self.presence_penalty),
            stop=all_stops if all_stops else None,
            tools=tools,
            stream=stream,
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Generate a response synchronously.

        Args:
            messages: List of messages to send
            stop: Optional stop sequences
            run_manager: Callback manager
            **kwargs: Additional parameters

        Returns:
            ChatResult with generated response

        Note:
            Uses asyncio.run() for Python 3.10+ compatibility, with fallback
            to get_event_loop() for nested event loop scenarios.
        """
        try:
            # Prefer asyncio.run() - cleaner and handles loop lifecycle
            return asyncio.run(
                self._agenerate(messages, stop, run_manager, **kwargs)  # type: ignore[arg-type]
            )
        except RuntimeError:
            # Fallback for nested event loops (e.g., in Jupyter)
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self._agenerate(messages, stop, run_manager, **kwargs)  # type: ignore[arg-type]
            )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Generate a response asynchronously.

        Args:
            messages: List of messages to send
            stop: Optional stop sequences
            run_manager: Callback manager
            **kwargs: Additional parameters

        Returns:
            ChatResult with generated response
        """
        request = self._build_request(messages, stop, stream=False, **kwargs)
        response = await self.client.complete(request)

        # Convert response to LangChain format
        generations = []
        for choice in response.choices:
            lc_message = forge_to_langchain(choice.message)
            generations.append(
                ChatGeneration(
                    message=lc_message,
                    generation_info={
                        "finish_reason": choice.finish_reason,
                    },
                )
            )

        return ChatResult(
            generations=generations,
            llm_output={
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            },
        )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """
        Stream response synchronously.

        Args:
            messages: List of messages to send
            stop: Optional stop sequences
            run_manager: Callback manager
            **kwargs: Additional parameters

        Yields:
            ChatGenerationChunk for each streamed piece

        Note:
            Sync streaming from async requires special handling.
            Uses a queue-based approach for proper async-to-sync bridging.
        """
        result_queue: queue.Queue[ChatGenerationChunk | Exception | None] = (
            queue.Queue()
        )

        async def _producer() -> None:
            """Async producer that puts chunks into the queue."""
            try:
                async for chunk in self._astream(
                    messages, stop, run_manager, **kwargs  # type: ignore[arg-type]
                ):
                    result_queue.put(chunk)
            except Exception as e:
                result_queue.put(e)
            finally:
                result_queue.put(None)  # Sentinel to signal completion

        def _run_producer() -> None:
            """Run the async producer in a new event loop."""
            asyncio.run(_producer())

        # Start producer in background thread
        producer_thread = threading.Thread(target=_run_producer, daemon=True)
        producer_thread.start()

        # Consume from queue
        while True:
            item = result_queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

        # Wait for producer thread to complete with reasonable timeout
        # 10 seconds should be enough for any in-flight network cleanup
        producer_thread.join(timeout=10.0)

        # Warn if thread is still running (potential resource leak)
        if producer_thread.is_alive():
            logger.warning(
                "Producer thread did not complete within timeout. "
                "Thread may be orphaned due to slow network or blocking I/O. "
                "This is a daemon thread and will be cleaned up on process exit."
            )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """
        Stream response asynchronously.

        Args:
            messages: List of messages to send
            stop: Optional stop sequences
            run_manager: Callback manager
            **kwargs: Additional parameters

        Yields:
            ChatGenerationChunk for each streamed piece
        """
        request = self._build_request(messages, stop, stream=True, **kwargs)

        async for chunk in self.client.stream(request):
            # Convert delta to message chunk
            content = chunk.delta.content or ""
            reasoning_content = chunk.delta.reasoning_content or ""
            tool_call_chunks = []

            if chunk.delta.tool_calls:
                for tc in chunk.delta.tool_calls:
                    tool_call_chunks.append(
                        {
                            "index": tc.get("index", 0),
                            "id": tc.get("id"),
                            "name": tc.get("function", {}).get("name"),
                            "args": tc.get("function", {}).get("arguments", ""),
                        }
                    )

            # Build usage metadata if available (OpenRouter sends on final chunk)
            usage_metadata = None
            if chunk.usage:
                usage_metadata = {
                    "input_tokens": chunk.usage.prompt_tokens,
                    "output_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }

            # Include reasoning_content in additional_kwargs for models like DeepSeek/Kimi
            additional_kwargs = {}
            if reasoning_content:
                additional_kwargs["reasoning_content"] = reasoning_content

            message_chunk = AIMessageChunk(
                content=content,
                tool_call_chunks=tool_call_chunks if tool_call_chunks else [],  # type: ignore[arg-type]
                usage_metadata=usage_metadata,  # type: ignore[arg-type]
                additional_kwargs=additional_kwargs if additional_kwargs else {},
            )

            yield ChatGenerationChunk(
                message=message_chunk,
                generation_info={
                    "finish_reason": chunk.finish_reason,
                    "usage": usage_metadata,
                    "reasoning_content": reasoning_content if reasoning_content else None,
                },
            )

            if run_manager:
                # Report both content and reasoning content as new tokens
                token_text = content + reasoning_content
                if token_text:
                    await run_manager.on_llm_new_token(token_text)

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> OpenRouterLLM:
        """
        Bind tools to this LLM instance.

        Args:
            tools: Tools to bind (Code-Forge ToolDefinition or LangChain tools)
            tool_choice: How to choose tools ("auto", "none", or specific)
            **kwargs: Additional parameters

        Returns:
            New OpenRouterLLM instance with tools bound

        Raises:
            ValueError: If too many tools are provided (max: MAX_BOUND_TOOLS)
        """
        from code_forge.llm.models import ToolDefinition

        # Check tool count limit
        if len(tools) > self.MAX_BOUND_TOOLS:
            raise ValueError(
                f"Too many tools: {len(tools)} exceeds maximum of {self.MAX_BOUND_TOOLS}. "
                f"Consider using fewer tools or splitting into multiple requests."
            )

        # Convert tools to ToolDefinition format
        converted_tools = []
        for tool in tools:
            if isinstance(tool, ToolDefinition):
                converted_tools.append(tool)
            elif hasattr(tool, "to_openai_schema"):
                # Code-Forge BaseTool
                converted_tools.append(tool.to_openai_schema())
            elif hasattr(tool, "name") and hasattr(tool, "description"):
                # LangChain-style tool
                schema = getattr(tool, "args_schema", None)
                params: dict[str, Any] = {}
                if schema:
                    params = schema.model_json_schema()
                converted_tools.append(
                    ToolDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters=params,
                    )
                )
            else:
                raise ValueError(f"Cannot convert tool: {tool}")

        # Create new instance with tools bound
        new_llm = self.model_copy()
        new_llm._bound_tools = converted_tools
        return new_llm

    def with_structured_output(
        self,
        schema: type | dict[str, Any],
        *,
        method: str = "json_mode",
        **kwargs: Any,
    ) -> OpenRouterLLM:
        """
        Configure LLM for structured output.

        Args:
            schema: Pydantic model or JSON schema
            method: Output method ("json_mode" or "function_calling")
            **kwargs: Additional parameters

        Returns:
            Configured LLM instance
        """
        # For now, just bind as a tool if using function calling
        if method == "function_calling":
            from code_forge.llm.models import ToolDefinition

            if isinstance(schema, type) and hasattr(schema, "model_json_schema"):
                # Pydantic model
                json_schema = schema.model_json_schema()
                name = schema.__name__
            elif isinstance(schema, dict):
                # Dict schema
                json_schema = schema
                name = schema.get("title", "structured_output")
            else:
                # Fallback
                json_schema = {}
                name = "structured_output"

            tool = ToolDefinition(
                name=name,
                description=f"Output structured data as {name}",
                parameters=json_schema,
            )
            return self.bind_tools(
                [tool], tool_choice={"type": "function", "function": {"name": name}}
            )

        # JSON mode requires response_format parameter support
        # This would need to be passed through to the API request
        raise NotImplementedError(
            "json_mode is not yet implemented. Use method='function_calling' instead, "
            "or configure JSON mode directly on the API request."
        )
