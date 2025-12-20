"""Tests for GitHub authentication."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.github.auth import (
    GitHubAuth,
    GitHubAuthenticator,
    GitHubAuthError,
)


class TestGitHubAuth:
    """Tests for GitHubAuth dataclass."""

    def test_create_auth(self) -> None:
        """Test creating GitHubAuth instance."""
        auth = GitHubAuth(
            token="test_token",
            username="testuser",
            scopes=["repo", "workflow"],
            rate_limit=5000,
            rate_remaining=4999,
            rate_reset=1700000000,
        )

        assert auth.token == "test_token"
        assert auth.username == "testuser"
        assert auth.scopes == ["repo", "workflow"]
        assert auth.rate_limit == 5000
        assert auth.rate_remaining == 4999
        assert auth.rate_reset == 1700000000

    def test_rate_reset_time(self) -> None:
        """Test rate_reset_time property."""
        auth = GitHubAuth(
            token="test_token",
            username="testuser",
            rate_reset=1700000000,
        )

        reset_time = auth.rate_reset_time
        assert isinstance(reset_time, datetime)
        assert reset_time == datetime.fromtimestamp(1700000000)

    def test_is_rate_limited_false(self) -> None:
        """Test is_rate_limited when not limited."""
        auth = GitHubAuth(
            token="test_token",
            username="testuser",
            rate_remaining=100,
        )

        assert auth.is_rate_limited is False

    def test_is_rate_limited_true(self) -> None:
        """Test is_rate_limited when limited."""
        auth = GitHubAuth(
            token="test_token",
            username="testuser",
            rate_remaining=0,
        )

        assert auth.is_rate_limited is True

    def test_default_scopes(self) -> None:
        """Test default empty scopes."""
        auth = GitHubAuth(
            token="test_token",
            username="testuser",
        )

        assert auth.scopes == []


class TestGitHubAuthenticator:
    """Tests for GitHubAuthenticator class."""

    def test_init_with_token(self) -> None:
        """Test initialization with explicit token."""
        auth = GitHubAuthenticator(token="test_token")

        assert auth.has_token is True
        assert auth.is_authenticated is False

    def test_init_without_token(self) -> None:
        """Test initialization without token."""
        auth = GitHubAuthenticator()

        # Has token depends on environment
        assert auth.is_authenticated is False

    def test_init_from_github_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization from GITHUB_TOKEN env var."""
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        monkeypatch.delenv("GH_TOKEN", raising=False)

        auth = GitHubAuthenticator()

        assert auth.has_token is True

    def test_init_from_gh_token_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test initialization from GH_TOKEN fallback."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "gh_env_token")

        auth = GitHubAuthenticator()

        assert auth.has_token is True

    def test_github_token_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test GITHUB_TOKEN takes precedence over GH_TOKEN."""
        monkeypatch.setenv("GITHUB_TOKEN", "github_token")
        monkeypatch.setenv("GH_TOKEN", "gh_token")

        auth = GitHubAuthenticator()
        headers = auth.get_headers()

        assert "Bearer github_token" in headers["Authorization"]

    def test_has_token_true(self, mock_token: str) -> None:
        """Test has_token when token exists."""
        auth = GitHubAuthenticator(token=mock_token)

        assert auth.has_token is True

    def test_has_token_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test has_token when no token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)

        auth = GitHubAuthenticator()

        assert auth.has_token is False

    def test_is_authenticated_initial(self, mock_token: str) -> None:
        """Test is_authenticated before validation."""
        auth = GitHubAuthenticator(token=mock_token)

        assert auth.is_authenticated is False

    def test_get_headers_with_token(self, mock_token: str) -> None:
        """Test get_headers with token."""
        auth = GitHubAuthenticator(token=mock_token)
        headers = auth.get_headers()

        assert headers["Authorization"] == f"Bearer {mock_token}"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_get_headers_without_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_headers without token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)

        auth = GitHubAuthenticator()
        headers = auth.get_headers()

        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github+json"

    @pytest.mark.asyncio
    async def test_validate_success(self, mock_token: str) -> None:
        """Test successful validation."""
        auth = GitHubAuthenticator(token=mock_token)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "X-OAuth-Scopes": "repo, workflow",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.json = AsyncMock(
            return_value={"login": "testuser", "id": 12345}
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_session_class.return_value = mock_session

            result = await auth.validate()

        assert result.username == "testuser"
        assert "repo" in result.scopes
        assert "workflow" in result.scopes
        assert result.rate_limit == 5000
        assert result.rate_remaining == 4999
        assert auth.is_authenticated is True

    @pytest.mark.asyncio
    async def test_validate_no_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validation without token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)

        auth = GitHubAuthenticator()

        with pytest.raises(GitHubAuthError) as exc_info:
            await auth.validate()

        assert "GITHUB_TOKEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, mock_token: str) -> None:
        """Test validation with invalid token."""
        auth = GitHubAuthenticator(token=mock_token)

        mock_response = MagicMock()
        mock_response.status = 401

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_session_class.return_value = mock_session

            with pytest.raises(GitHubAuthError) as exc_info:
                await auth.validate()

        assert "Invalid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_forbidden(self, mock_token: str) -> None:
        """Test validation with forbidden response."""
        auth = GitHubAuthenticator(token=mock_token)

        mock_response = MagicMock()
        mock_response.status = 403

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_session_class.return_value = mock_session

            with pytest.raises(GitHubAuthError) as exc_info:
                await auth.validate()

        assert "permissions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_api_error(self, mock_token: str) -> None:
        """Test validation with API error."""
        auth = GitHubAuthenticator(token=mock_token)

        mock_response = MagicMock()
        mock_response.status = 500

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_session_class.return_value = mock_session

            with pytest.raises(GitHubAuthError) as exc_info:
                await auth.validate()

        assert "500" in str(exc_info.value)

    def test_update_rate_limit(
        self, authenticated_authenticator: GitHubAuthenticator
    ) -> None:
        """Test update_rate_limit."""
        authenticated_authenticator.update_rate_limit(
            limit=5000,
            remaining=4500,
            reset=1700001000,
        )

        auth_info = authenticated_authenticator.get_auth_info()
        assert isinstance(auth_info, GitHubAuth)
        assert auth_info.rate_limit == 5000
        assert auth_info.rate_remaining == 4500
        assert auth_info.rate_reset == 1700001000

    def test_update_rate_limit_no_auth_info(self, mock_token: str) -> None:
        """Test update_rate_limit when not authenticated."""
        auth = GitHubAuthenticator(token=mock_token)

        # Should not raise, just do nothing
        auth.update_rate_limit(limit=5000, remaining=4500, reset=1700001000)

    def test_get_auth_info_none(self, mock_token: str) -> None:
        """Test get_auth_info before validation."""
        auth = GitHubAuthenticator(token=mock_token)

        assert auth.get_auth_info() is None

    def test_get_auth_info_after_validation(
        self, authenticated_authenticator: GitHubAuthenticator
    ) -> None:
        """Test get_auth_info after validation."""
        auth_info = authenticated_authenticator.get_auth_info()

        assert isinstance(auth_info, GitHubAuth)
        assert auth_info.username == "testuser"


class TestGitHubAuthError:
    """Tests for GitHubAuthError exception."""

    def test_auth_error_message(self) -> None:
        """Test GitHubAuthError with message."""
        error = GitHubAuthError("Test error message")

        assert str(error) == "Test error message"

    def test_auth_error_inheritance(self) -> None:
        """Test GitHubAuthError inheritance."""
        error = GitHubAuthError("Test error")

        assert isinstance(error, Exception)
