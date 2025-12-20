"""Unit tests for OpenRouterClient."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from code_forge.llm.client import OpenRouterClient
from code_forge.llm.errors import (
    AuthenticationError,
    ContentPolicyError,
    ContextLengthError,
    LLMError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from code_forge.llm.models import CompletionRequest, Message


class TestOpenRouterClientInit:
    """Tests for OpenRouterClient initialization."""

    def test_default_values(self) -> None:
        client = OpenRouterClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.base_url == "https://openrouter.ai/api/v1"
        assert client.app_name == "Code-Forge"
        assert client.timeout == 120.0
        assert client.max_retries == 3
        assert client.retry_delay == 1.0

    def test_custom_values(self) -> None:
        client = OpenRouterClient(
            api_key="test-key",
            base_url="https://custom.api",
            app_name="MyApp",
            app_url="https://myapp.com",
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0,
        )
        assert client.base_url == "https://custom.api"
        assert client.app_name == "MyApp"
        assert client.app_url == "https://myapp.com"
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.retry_delay == 2.0


class TestOpenRouterClientHeaders:
    """Tests for header generation."""

    def test_headers_include_authorization(self) -> None:
        client = OpenRouterClient(api_key="sk-test-12345")
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-test-12345"

    def test_headers_include_app_info(self) -> None:
        client = OpenRouterClient(
            api_key="test", app_name="TestApp", app_url="https://test.com"
        )
        headers = client._get_headers()
        assert headers["X-Title"] == "TestApp"
        assert headers["HTTP-Referer"] == "https://test.com"

    def test_headers_include_content_type(self) -> None:
        client = OpenRouterClient(api_key="test")
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"


class TestOpenRouterClientUsage:
    """Tests for usage tracking."""

    def test_initial_usage_is_zero(self) -> None:
        client = OpenRouterClient(api_key="test")
        usage = client.get_usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_reset_usage(self) -> None:
        client = OpenRouterClient(api_key="test")
        # Manually set some values
        client._total_prompt_tokens = 100
        client._total_completion_tokens = 50
        client._total_requests = 5

        client.reset_usage()

        usage = client.get_usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestOpenRouterClientComplete:
    """Tests for complete() method."""

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        mock_response_data = {
            "id": "gen-test",
            "model": "test/model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Test response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "created": 1705312345,
        }

        client = OpenRouterClient(api_key="test")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_response_data
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            request = CompletionRequest(
                model="test/model", messages=[Message.user("Hello")]
            )

            response = await client.complete(request)

            assert response.id == "gen-test"
            assert response.choices[0].message.content == "Test response"
            assert response.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_complete_tracks_usage(self) -> None:
        mock_response_data = {
            "id": "gen-test",
            "model": "test/model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            "created": 1705312345,
        }

        client = OpenRouterClient(api_key="test")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_response_data
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            request = CompletionRequest(
                model="test/model", messages=[Message.user("Hello")]
            )

            await client.complete(request)

            usage = client.get_usage()
            assert usage.prompt_tokens == 20
            assert usage.completion_tokens == 10
            assert usage.total_tokens == 30

    @pytest.mark.asyncio
    async def test_complete_resolves_alias(self) -> None:
        mock_response_data = {
            "id": "gen-test",
            "model": "anthropic/claude-3-opus",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hi"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            "created": 1705312345,
        }

        client = OpenRouterClient(api_key="test")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_response_data
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            request = CompletionRequest(
                model="claude-3-opus",  # alias
                messages=[Message.user("Hello")],
            )

            await client.complete(request)

            # The model should be resolved
            assert request.model == "anthropic/claude-3-opus"


class TestOpenRouterClientErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_authentication_error(self) -> None:
        client = OpenRouterClient(api_key="invalid")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {
            "error": {"message": "Invalid API key", "code": "invalid_api_key"}
        }

        with pytest.raises(AuthenticationError):
            await client._check_response(mock_response)

    @pytest.mark.asyncio
    async def test_rate_limit_error(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_response.headers = {"Retry-After": "30"}
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }

        with pytest.raises(RateLimitError) as exc_info:
            await client._check_response(mock_response)

        assert exc_info.value.retry_after == 30.0

    @pytest.mark.asyncio
    async def test_model_not_found_error(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {
            "error": {"message": "Model not found: fake/model"}
        }

        with pytest.raises(ModelNotFoundError):
            await client._check_response(mock_response)

    @pytest.mark.asyncio
    async def test_context_length_error(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {
            "error": {"message": "Context length exceeded"}
        }

        with pytest.raises(ContextLengthError):
            await client._check_response(mock_response)

    @pytest.mark.asyncio
    async def test_content_policy_error(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {
            "error": {"message": "Content violates policy"}
        }

        with pytest.raises(ContentPolicyError):
            await client._check_response(mock_response)

    @pytest.mark.asyncio
    async def test_provider_error(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {
            "error": {"message": "Upstream provider error"}
        }

        with pytest.raises(ProviderError):
            await client._check_response(mock_response)

    @pytest.mark.asyncio
    async def test_json_decode_error_in_response(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.json.side_effect = json.JSONDecodeError("test", "doc", 0)

        with pytest.raises(ProviderError):
            await client._check_response(mock_response)


class TestOpenRouterClientLifecycle:
    """Tests for client lifecycle management."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        async with OpenRouterClient(api_key="test") as client:
            assert client._closed is False

        assert client._closed is True

    @pytest.mark.asyncio
    async def test_close_method(self) -> None:
        client = OpenRouterClient(api_key="test")
        # Create a mock client
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        await client.close()

        assert client._closed is True
        mock_http_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_idempotent(self) -> None:
        client = OpenRouterClient(api_key="test")
        client._client = AsyncMock()

        await client.close()
        await client.close()  # Should not raise

        assert client._closed is True

    @pytest.mark.asyncio
    async def test_get_client_after_close_raises(self) -> None:
        client = OpenRouterClient(api_key="test")
        await client.close()

        with pytest.raises(RuntimeError, match="Client is closed"):
            await client._get_client()


class TestOpenRouterClientRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self) -> None:
        client = OpenRouterClient(api_key="test", max_retries=3, retry_delay=0.01)

        mock_http_client = AsyncMock()

        # First call: rate limit error
        rate_limit_response = MagicMock()
        rate_limit_response.is_success = False
        rate_limit_response.status_code = 429
        rate_limit_response.text = "Rate limited"
        rate_limit_response.headers = {"Retry-After": "0.01"}
        rate_limit_response.json.return_value = {"error": {"message": "Rate limited"}}

        # Second call: success
        success_response = MagicMock()
        success_response.is_success = True
        success_response.json.return_value = {"data": "success"}

        mock_http_client.request = AsyncMock(
            side_effect=[rate_limit_response, success_response]
        )

        result = await client._make_request(
            mock_http_client, "POST", "/test", {"test": "data"}
        )

        assert result == {"data": "success"}
        assert mock_http_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        client = OpenRouterClient(api_key="test", max_retries=2, retry_delay=0.01)

        mock_http_client = AsyncMock()

        # All calls fail with rate limit
        rate_limit_response = MagicMock()
        rate_limit_response.is_success = False
        rate_limit_response.status_code = 429
        rate_limit_response.text = "Rate limited"
        rate_limit_response.headers = {}
        rate_limit_response.json.return_value = {"error": {"message": "Rate limited"}}

        mock_http_client.request = AsyncMock(return_value=rate_limit_response)

        with pytest.raises(RateLimitError):
            await client._make_request(
                mock_http_client, "POST", "/test", {"test": "data"}
            )

        assert mock_http_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        client = OpenRouterClient(api_key="test", max_retries=3, retry_delay=0.01)

        mock_http_client = AsyncMock()

        # First call: timeout
        # Second call: success
        success_response = MagicMock()
        success_response.is_success = True
        success_response.json.return_value = {"data": "success"}

        mock_http_client.request = AsyncMock(
            side_effect=[httpx.TimeoutException("Timeout"), success_response]
        )

        result = await client._make_request(
            mock_http_client, "POST", "/test", {"test": "data"}
        )

        assert result == {"data": "success"}
        assert mock_http_client.request.call_count == 2


class TestOpenRouterClientListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_success(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_models_data = {
            "data": [
                {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"},
                {"id": "openai/gpt-4", "name": "GPT-4"},
            ]
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_models_data
            mock_http_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            with patch.object(client, "_check_response", new_callable=AsyncMock):
                models = await client.list_models()

            assert len(models) == 2
            assert models[0]["id"] == "anthropic/claude-3-opus"
            assert models[1]["id"] == "openai/gpt-4"


class TestOpenRouterClientHttpErrors:
    """Tests for HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_error_not_retried(self) -> None:
        client = OpenRouterClient(api_key="test", max_retries=3, retry_delay=0.01)

        mock_http_client = AsyncMock()

        # HTTP error should not be retried
        mock_http_client.request = AsyncMock(
            side_effect=httpx.HTTPError("Connection failed")
        )

        with pytest.raises(LLMError, match="HTTP error"):
            await client._make_request(
                mock_http_client, "POST", "/test", {"test": "data"}
            )

        # Should only try once (HTTP errors are not retried)
        assert mock_http_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_without_retry_after(self) -> None:
        client = OpenRouterClient(api_key="test")

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_response.headers = {}  # No Retry-After header
        mock_response.json.return_value = {"error": {"message": "Rate limited"}}

        with pytest.raises(RateLimitError) as exc_info:
            await client._check_response(mock_response)

        assert exc_info.value.retry_after is None


class TestOpenRouterClientGetClient:
    """Tests for _get_client method."""

    @pytest.mark.asyncio
    async def test_creates_client_when_none(self) -> None:
        client = OpenRouterClient(api_key="test")
        assert client._client is None

        http_client = await client._get_client()

        assert isinstance(http_client, httpx.AsyncClient)

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_reuses_existing_client(self) -> None:
        client = OpenRouterClient(api_key="test")

        http_client1 = await client._get_client()
        http_client2 = await client._get_client()

        assert http_client1 is http_client2

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_creates_new_client_when_closed(self) -> None:
        client = OpenRouterClient(api_key="test")

        http_client1 = await client._get_client()
        await http_client1.aclose()  # Manually close the HTTP client

        # Should create a new one since the old one is closed
        http_client2 = await client._get_client()

        assert http_client2 is not http_client1

        # Cleanup
        await client.close()
