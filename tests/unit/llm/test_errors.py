"""Unit tests for LLM error classes."""

import pytest

from code_forge.core.errors import CodeForgeError
from code_forge.llm.errors import (
    AuthenticationError,
    ContentPolicyError,
    ContextLengthError,
    LLMError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)


class TestLLMError:
    """Tests for LLMError base class."""

    def test_inherits_from_forge_error(self) -> None:
        assert issubclass(LLMError, CodeForgeError)

    def test_basic_message(self) -> None:
        err = LLMError("Something went wrong")
        assert str(err) == "Something went wrong"


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_inherits_from_llm_error(self) -> None:
        assert issubclass(AuthenticationError, LLMError)

    def test_default_message(self) -> None:
        err = AuthenticationError()
        assert "Invalid or missing API key" in str(err)

    def test_custom_message(self) -> None:
        err = AuthenticationError("Invalid key provided")
        assert "Invalid key provided" in str(err)

    def test_can_be_caught_as_llm_error(self) -> None:
        with pytest.raises(LLMError):
            raise AuthenticationError()


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_inherits_from_llm_error(self) -> None:
        assert issubclass(RateLimitError, LLMError)

    def test_default_message(self) -> None:
        err = RateLimitError()
        assert "Rate limit exceeded" in str(err)

    def test_retry_after_attribute(self) -> None:
        err = RateLimitError("Too many requests", retry_after=30.0)
        assert err.retry_after == 30.0

    def test_retry_after_none_by_default(self) -> None:
        err = RateLimitError()
        assert err.retry_after is None


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_inherits_from_llm_error(self) -> None:
        assert issubclass(ModelNotFoundError, LLMError)

    def test_model_id_in_message(self) -> None:
        err = ModelNotFoundError("fake/model")
        assert "fake/model" in str(err)
        assert "not found" in str(err).lower()

    def test_model_id_attribute(self) -> None:
        err = ModelNotFoundError("test/model-123")
        assert err.model_id == "test/model-123"


class TestContextLengthError:
    """Tests for ContextLengthError."""

    def test_inherits_from_llm_error(self) -> None:
        assert issubclass(ContextLengthError, LLMError)

    def test_default_message(self) -> None:
        err = ContextLengthError()
        assert "Context length exceeded" in str(err)

    def test_with_token_info(self) -> None:
        err = ContextLengthError(
            "Too many tokens", max_tokens=8192, requested_tokens=10000
        )
        assert err.max_tokens == 8192
        assert err.requested_tokens == 10000

    def test_token_attributes_none_by_default(self) -> None:
        err = ContextLengthError()
        assert err.max_tokens is None
        assert err.requested_tokens is None


class TestContentPolicyError:
    """Tests for ContentPolicyError."""

    def test_inherits_from_llm_error(self) -> None:
        assert issubclass(ContentPolicyError, LLMError)

    def test_default_message(self) -> None:
        err = ContentPolicyError()
        assert "Content violates policy" in str(err)

    def test_custom_message(self) -> None:
        err = ContentPolicyError("Content flagged for violence")
        assert "Content flagged for violence" in str(err)


class TestProviderError:
    """Tests for ProviderError."""

    def test_inherits_from_llm_error(self) -> None:
        assert issubclass(ProviderError, LLMError)

    def test_message_and_provider(self) -> None:
        err = ProviderError("Upstream timeout", provider="anthropic")
        assert "Upstream timeout" in str(err)
        assert err.provider == "anthropic"

    def test_provider_none_by_default(self) -> None:
        err = ProviderError("Generic error")
        assert err.provider is None


class TestErrorHierarchy:
    """Tests for error hierarchy relationships."""

    @pytest.mark.parametrize(
        "error_class,args",
        [
            (AuthenticationError, ()),
            (RateLimitError, ()),
            (ModelNotFoundError, ("test",)),
            (ContextLengthError, ()),
            (ContentPolicyError, ()),
            (ProviderError, ("test",)),
        ]
    )
    def test_all_errors_catchable_as_llm_error(self, error_class, args) -> None:
        err = error_class(*args)
        assert isinstance(err, LLMError)

    @pytest.mark.parametrize(
        "error_class,args",
        [
            (AuthenticationError, ()),
            (RateLimitError, ()),
            (ModelNotFoundError, ("test",)),
            (ContextLengthError, ()),
            (ContentPolicyError, ()),
            (ProviderError, ("test",)),
        ]
    )
    def test_all_errors_catchable_as_forge_error(self, error_class, args) -> None:
        err = error_class(*args)
        assert isinstance(err, CodeForgeError)


class TestLLMErrorMessages:
    """Test error messages for various scenarios."""

    @pytest.mark.parametrize(
        "error_class,message,expected_substring",
        [
            (AuthenticationError, "Invalid API key", "Invalid API key"),
            (RateLimitError, "Too many requests", "Too many requests"),
            (ModelNotFoundError, "gpt-5", "gpt-5"),
            (ContextLengthError, "Token limit exceeded", "Token limit exceeded"),
            (ContentPolicyError, "Harmful content", "Harmful content"),
            (ProviderError, "Service unavailable", "Service unavailable"),
        ]
    )
    def test_custom_error_messages(self, error_class, message: str, expected_substring: str) -> None:
        if error_class == ModelNotFoundError:
            err = error_class(message)
        else:
            err = error_class(message)
        assert expected_substring in str(err)
