"""Tests for GitHub API client."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

from code_forge.github.auth import GitHubAuthenticator, GitHubAuthError
from code_forge.github.client import (
    GitHubClient,
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubNotFoundError,
)


class TestGitHubClient:
    """Tests for GitHubClient class."""

    def test_init(self, authenticated_authenticator: GitHubAuthenticator) -> None:
        """Test client initialization."""
        client = GitHubClient(auth=authenticated_authenticator)

        assert client.auth == authenticated_authenticator
        assert client.max_retries == 3
        assert client._session is None

    def test_init_custom_settings(
        self, authenticated_authenticator: GitHubAuthenticator
    ) -> None:
        """Test client initialization with custom settings."""
        client = GitHubClient(
            auth=authenticated_authenticator,
            timeout=60,
            max_retries=5,
        )

        assert client.max_retries == 5
        assert client.timeout.total == 60

    def test_build_url_simple(
        self, client: GitHubClient
    ) -> None:
        """Test URL building without params."""
        url = client._build_url("/repos/owner/repo")

        assert url == "https://api.github.com/repos/owner/repo"

    def test_build_url_with_params(
        self, client: GitHubClient
    ) -> None:
        """Test URL building with params."""
        url = client._build_url("/repos/owner/repo", state="open", page=1)

        assert "state=open" in url
        assert "page=1" in url

    def test_build_url_filters_none(
        self, client: GitHubClient
    ) -> None:
        """Test URL building filters out None values."""
        url = client._build_url("/repos/owner/repo", state="open", label=None)

        assert "state=open" in url
        assert "label" not in url

    @pytest.mark.asyncio
    async def test_get_success(
        self, client: GitHubClient
    ) -> None:
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.json = AsyncMock(return_value={"name": "test-repo"})

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            result = await client.get("/repos/owner/repo")

        assert result["name"] == "test-repo"

    @pytest.mark.asyncio
    async def test_get_raw(
        self, client: GitHubClient
    ) -> None:
        """Test get_raw for text content."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "Content-Type": "text/plain",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.text = AsyncMock(return_value="Raw content")

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            result = await client.get_raw("/repos/owner/repo/readme")

        assert result == "Raw content"

    @pytest.mark.asyncio
    async def test_post_success(
        self, client: GitHubClient
    ) -> None:
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.json = AsyncMock(return_value={"number": 42})

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            result = await client.post(
                "/repos/owner/repo/issues",
                {"title": "Test"}
            )

        assert isinstance(result, dict)
        assert result["number"] == 42

    @pytest.mark.asyncio
    async def test_patch_success(
        self, client: GitHubClient
    ) -> None:
        """Test successful PATCH request."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.json = AsyncMock(return_value={"number": 42})

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            result = await client.patch(
                "/repos/owner/repo/issues/42",
                {"title": "Updated"}
            )

        assert isinstance(result, dict)
        assert result["number"] == 42

    @pytest.mark.asyncio
    async def test_put_success(
        self, client: GitHubClient
    ) -> None:
        """Test successful PUT request."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.json = AsyncMock(return_value={"merged": True})

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            result = await client.put(
                "/repos/owner/repo/pulls/123/merge",
                {"merge_method": "squash"}
            )

        assert isinstance(result, dict)
        assert result["merged"] is True

    @pytest.mark.asyncio
    async def test_delete_success(
        self, client: GitHubClient
    ) -> None:
        """Test successful DELETE request."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            await client.delete("/repos/owner/repo/issues/42")

    @pytest.mark.asyncio
    async def test_get_not_found(
        self, client: GitHubClient
    ) -> None:
        """Test 404 Not Found error."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            with pytest.raises(GitHubNotFoundError) as exc_info:
                await client.get("/repos/owner/nonexistent")

        assert exc_info.value.status == 404

    @pytest.mark.asyncio
    async def test_get_rate_limited(
        self, client: GitHubClient
    ) -> None:
        """Test rate limit error."""
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1700000000",
        }

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            with pytest.raises(GitHubRateLimitError):
                await client.get("/repos/owner/repo")

    @pytest.mark.asyncio
    async def test_get_forbidden_not_rate_limited(
        self, client: GitHubClient
    ) -> None:
        """Test 403 without rate limit."""
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get("/repos/owner/repo")

        assert exc_info.value.status == 403

    @pytest.mark.asyncio
    async def test_get_unauthorized(
        self, client: GitHubClient
    ) -> None:
        """Test 401 Unauthorized error."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            with pytest.raises(GitHubAuthError):
                await client.get("/repos/owner/repo")

    @pytest.mark.asyncio
    async def test_get_api_error(
        self, client: GitHubClient
    ) -> None:
        """Test generic API error."""
        mock_response = MagicMock()
        mock_response.status = 422
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        }
        mock_response.json = AsyncMock(
            return_value={"message": "Validation failed"}
        )

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ))
            mock_get_session.return_value = mock_session

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get("/repos/owner/repo")

        assert "Validation failed" in str(exc_info.value)
        assert exc_info.value.status == 422

    @pytest.mark.asyncio
    async def test_get_paginated(
        self, client: GitHubClient
    ) -> None:
        """Test paginated request."""
        # Page 1: Return full page (30 items) so it checks for next link
        page1_items = [{"number": i} for i in range(1, 31)]
        page1_response = MagicMock()
        page1_response.status = 200
        page1_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
            "Link": '<https://api.github.com/repos/owner/repo/issues?page=2>; rel="next"',
        }
        page1_response.json = AsyncMock(return_value=page1_items)

        # Page 2: Return partial page (10 items) which signals end
        page2_items = [{"number": i} for i in range(31, 41)]
        page2_response = MagicMock()
        page2_response.status = 200
        page2_response.headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4998",
            "X-RateLimit-Reset": "1700000000",
        }
        page2_response.json = AsyncMock(return_value=page2_items)

        call_count = 0

        def make_response(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            response = page1_response if call_count == 1 else page2_response
            return MagicMock(
                __aenter__=AsyncMock(return_value=response),
                __aexit__=AsyncMock(return_value=None),
            )

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(side_effect=make_response)
            mock_get_session.return_value = mock_session

            result = await client.get_paginated("/repos/owner/repo/issues")

        # 30 from page 1 + 10 from page 2 = 40 total
        assert len(result) == 40
        assert result[0]["number"] == 1
        assert result[29]["number"] == 30
        assert result[30]["number"] == 31
        assert result[39]["number"] == 40

    @pytest.mark.asyncio
    async def test_get_paginated_max_pages(
        self, client: GitHubClient
    ) -> None:
        """Test paginated request with max_pages limit."""
        # Create responses that always have a next page
        def make_response(*args: Any, **kwargs: Any) -> Any:
            response = MagicMock()
            response.status = 200
            response.headers = {
                "Content-Type": "application/json",
                "X-RateLimit-Limit": "5000",
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": "1700000000",
                "Link": '<https://api.github.com/repos/owner/repo/issues?page=99>; rel="next"',
            }
            # Return full page of items
            response.json = AsyncMock(
                return_value=[{"number": i} for i in range(30)]
            )
            return MagicMock(
                __aenter__=AsyncMock(return_value=response),
                __aexit__=AsyncMock(return_value=None),
            )

        with patch.object(client, "_get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(side_effect=make_response)
            mock_get_session.return_value = mock_session

            result = await client.get_paginated(
                "/repos/owner/repo/issues",
                max_pages=2,
            )

        # Should have 2 pages * 30 items
        assert len(result) == 60

    @pytest.mark.asyncio
    async def test_close(
        self, client: GitHubClient
    ) -> None:
        """Test closing the client session."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        client._session = mock_session

        await client.close()

        mock_session.close.assert_called_once()


class TestGitHubAPIError:
    """Tests for GitHubAPIError exception."""

    def test_api_error_with_message(self) -> None:
        """Test GitHubAPIError with message only."""
        error = GitHubAPIError("Test error")

        assert str(error) == "Test error"
        assert error.status is None
        assert error.response is None

    def test_api_error_with_status(self) -> None:
        """Test GitHubAPIError with status."""
        error = GitHubAPIError("Test error", status=404)

        assert error.status == 404

    def test_api_error_with_response(self) -> None:
        """Test GitHubAPIError with response data."""
        response = {"message": "Not found", "errors": []}
        error = GitHubAPIError("Test error", status=404, response=response)

        assert error.response == response


class TestGitHubRateLimitError:
    """Tests for GitHubRateLimitError exception."""

    def test_rate_limit_error(self) -> None:
        """Test GitHubRateLimitError."""
        error = GitHubRateLimitError("Rate limit exceeded", status=403)

        assert isinstance(error, GitHubAPIError)
        assert error.status == 403


class TestGitHubNotFoundError:
    """Tests for GitHubNotFoundError exception."""

    def test_not_found_error(self) -> None:
        """Test GitHubNotFoundError."""
        error = GitHubNotFoundError("Resource not found", status=404)

        assert isinstance(error, GitHubAPIError)
        assert error.status == 404
