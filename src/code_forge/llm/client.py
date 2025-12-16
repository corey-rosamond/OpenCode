"""OpenRouter API client."""

from __future__ import annotations

import asyncio
import json
import threading
import warnings
import weakref
from collections.abc import AsyncIterator
from typing import Any

import httpx

from code_forge.core.logging import get_logger
from code_forge.llm.errors import (
    AuthenticationError,
    ContentPolicyError,
    ContextLengthError,
    LLMError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from code_forge.llm.models import (
    CompletionRequest,
    CompletionResponse,
    StreamChunk,
    TokenUsage,
)
from code_forge.llm.routing import resolve_model_alias

logger = get_logger("llm")


class OpenRouterClient:
    """
    Client for the OpenRouter API.

    Provides unified access to 400+ AI models through OpenRouter's
    OpenAI-compatible API interface.

    IMPORTANT: This client manages HTTP connections that must be closed.
    Always use as an async context manager or call close() explicitly:

        # Recommended: async context manager
        async with OpenRouterClient(api_key) as client:
            response = await client.complete(request)

        # Alternative: explicit close
        client = OpenRouterClient(api_key)
        try:
            response = await client.complete(request)
        finally:
            await client.close()
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    # Track all active clients for cleanup at exit
    _active_clients: weakref.WeakSet[OpenRouterClient] | None = None

    @classmethod
    def _get_active_clients(cls) -> weakref.WeakSet[OpenRouterClient]:
        """Get or create the weak set of active clients."""
        if cls._active_clients is None:
            cls._active_clients = weakref.WeakSet()
        return cls._active_clients

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        app_name: str = "Code-Forge",
        app_url: str = "https://github.com/forge",
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            base_url: Override API base URL
            app_name: Application name for rankings
            app_url: Application URL for rankings
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Initial delay between retries
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.app_name = app_name
        self.app_url = app_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._client: httpx.AsyncClient | None = None
        self._closed = False

        # Usage tracking (protected by lock for thread safety)
        self._usage_lock = threading.Lock()
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_requests = 0

        # Register for tracking
        self._get_active_clients().add(self)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._closed:
            raise RuntimeError("Client is closed")
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.app_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json",
        }

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Send a chat completion request.

        Args:
            request: The completion request

        Returns:
            CompletionResponse with the model's response

        Raises:
            LLMError: On API errors
        """
        # Resolve model alias
        request.model = resolve_model_alias(request.model)
        request.stream = False

        client = await self._get_client()
        payload = request.to_dict()

        logger.debug(f"Completion request: model={request.model}")

        response_data = await self._make_request(
            client, "POST", "/chat/completions", payload
        )

        response = CompletionResponse.from_dict(response_data)

        # Track usage (thread-safe)
        with self._usage_lock:
            self._total_prompt_tokens += response.usage.prompt_tokens
            self._total_completion_tokens += response.usage.completion_tokens
            self._total_requests += 1

        logger.debug(f"Completion response: tokens={response.usage.total_tokens}")

        return response

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """
        Send a streaming chat completion request.

        Args:
            request: The completion request

        Yields:
            StreamChunk for each piece of the response

        Raises:
            LLMError: On API errors
        """
        # Resolve model alias
        request.model = resolve_model_alias(request.model)
        request.stream = True

        client = await self._get_client()
        payload = request.to_dict()

        logger.debug(f"Streaming request: model={request.model}")

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            await self._check_response(response)

            # Track streaming stats for error detection
            chunks_received = 0
            parse_errors = 0

            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data)
                        chunk = StreamChunk.from_dict(chunk_data)
                        chunks_received += 1

                        # Track final usage (thread-safe)
                        if chunk.usage:
                            with self._usage_lock:
                                self._total_prompt_tokens += chunk.usage.prompt_tokens
                                self._total_completion_tokens += chunk.usage.completion_tokens
                                self._total_requests += 1

                        yield chunk
                    except json.JSONDecodeError as e:
                        parse_errors += 1
                        logger.warning(
                            f"Failed to parse streaming chunk {chunks_received + parse_errors}: "
                            f"{e} - data: {data[:100]}..."
                        )
                    except (KeyError, TypeError) as e:
                        parse_errors += 1
                        logger.warning(
                            f"Invalid chunk structure at position {chunks_received + parse_errors}: "
                            f"{e} - data: {data[:100]}..."
                        )

            # Log summary if there were errors (visible indicator of incomplete stream)
            if parse_errors > 0:
                error_rate = parse_errors / max(1, chunks_received + parse_errors) * 100
                logger.error(
                    f"Streaming completed with {parse_errors} parse error(s) "
                    f"({error_rate:.1f}% error rate). "
                    f"Response may be incomplete. Received {chunks_received} valid chunks."
                )

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model information dicts
        """
        client = await self._get_client()
        response = await client.get("/models")
        await self._check_response(response)
        data: dict[str, Any] = response.json()
        result: list[dict[str, Any]] = data.get("data", [])
        return result

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Make a request with retry logic.

        Args:
            client: HTTP client
            method: HTTP method
            path: API path
            payload: Request payload

        Returns:
            Response JSON data

        Raises:
            LLMError: On unrecoverable errors
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, path, json=payload)
                await self._check_response(response)
                result: dict[str, Any] = response.json()
                return result

            except RateLimitError as e:
                last_error = e
                wait_time = e.retry_after or (self.retry_delay * (2**attempt))
                logger.warning(
                    f"Rate limited, retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)

            except httpx.TimeoutException as e:
                last_error = LLMError(f"Request timeout: {e!s}")
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    f"Timeout, retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)

            except httpx.HTTPError as e:
                last_error = LLMError(f"HTTP error: {e!s}")
                break

        raise last_error or LLMError("Request failed after retries")

    async def _check_response(self, response: httpx.Response) -> None:
        """
        Check response for errors.

        Args:
            response: HTTP response

        Raises:
            Appropriate LLMError subclass
        """
        if response.is_success:
            return

        # For streaming responses, we must read the content first
        # before accessing .text or .json()
        try:
            await response.aread()
        except Exception:
            pass  # Already read or other issue, continue with what we have

        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except (json.JSONDecodeError, Exception):
            error_msg = response.text or "Unknown error"

        status = response.status_code

        if status == 401:
            raise AuthenticationError(error_msg)
        elif status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                error_msg,
                retry_after=float(retry_after) if retry_after else None,
            )
        elif status == 404:
            raise ModelNotFoundError(error_msg)
        elif status == 400 and "context" in error_msg.lower():
            raise ContextLengthError(error_msg)
        elif status == 400 and "content" in error_msg.lower():
            raise ContentPolicyError(error_msg)
        else:
            raise ProviderError(error_msg)

    def get_usage(self) -> TokenUsage:
        """Get cumulative token usage (thread-safe)."""
        with self._usage_lock:
            return TokenUsage(
                prompt_tokens=self._total_prompt_tokens,
                completion_tokens=self._total_completion_tokens,
                total_tokens=self._total_prompt_tokens + self._total_completion_tokens,
            )

    def reset_usage(self) -> None:
        """Reset usage counters (thread-safe)."""
        with self._usage_lock:
            self._total_prompt_tokens = 0
            self._total_completion_tokens = 0
            self._total_requests = 0

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._closed:
            await self._client.aclose()
            self._client = None
        self._closed = True

    async def __aenter__(self) -> OpenRouterClient:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    def __del__(self) -> None:
        """Destructor: warn if client wasn't closed properly.

        Note: We can't await close() in __del__, so we just log a warning.
        Users should use the async context manager or call close() explicitly.
        """
        if not self._closed and self._client is not None and not self._client.is_closed:
            warnings.warn(
                "OpenRouterClient was not closed properly. "
                "Use 'async with' or call 'await client.close()' explicitly.",
                ResourceWarning,
                stacklevel=2,
            )
