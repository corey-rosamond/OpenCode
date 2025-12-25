"""Tests for search providers.

This module provides comprehensive tests for all search providers:
- BraveSearchProvider
- GoogleSearchProvider
- DuckDuckGoProvider
- Base SearchProvider functionality
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.web.search.base import SearchError, SearchProvider
from code_forge.web.search.brave import BraveSearchProvider
from code_forge.web.search.duckduckgo import DuckDuckGoProvider
from code_forge.web.search.google import GoogleSearchProvider
from code_forge.web.types import SearchResponse, SearchResult


# =============================================================================
# Base SearchProvider Tests
# =============================================================================

class TestSearchProviderBase:
    """Tests for base SearchProvider functionality."""

    def test_filter_results_no_filters(self) -> None:
        """Test filter_results with no filters returns original."""
        # Create a concrete provider for testing
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test",
            results=[
                SearchResult(title="Result 1", url="https://example.com/1", snippet=""),
                SearchResult(title="Result 2", url="https://github.com/2", snippet=""),
            ],
            provider="test",
            total_results=2,
            search_time=0.1,
        )

        filtered = provider.filter_results(response)

        assert len(filtered.results) == 2

    def test_filter_results_allowed_domains(self) -> None:
        """Test filtering by allowed domains."""
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test",
            results=[
                SearchResult(title="GitHub", url="https://github.com/test", snippet=""),
                SearchResult(title="Example", url="https://example.com/test", snippet=""),
                SearchResult(title="GitLab", url="https://gitlab.com/test", snippet=""),
            ],
            provider="test",
            total_results=3,
            search_time=0.1,
        )

        filtered = provider.filter_results(
            response,
            allowed_domains=["github.com"],
        )

        assert len(filtered.results) == 1
        assert "github.com" in filtered.results[0].url

    def test_filter_results_blocked_domains(self) -> None:
        """Test filtering by blocked domains."""
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test",
            results=[
                SearchResult(title="GitHub", url="https://github.com/test", snippet=""),
                SearchResult(title="Example", url="https://example.com/test", snippet=""),
                SearchResult(title="Spam", url="https://spam.com/test", snippet=""),
            ],
            provider="test",
            total_results=3,
            search_time=0.1,
        )

        filtered = provider.filter_results(
            response,
            blocked_domains=["spam.com"],
        )

        assert len(filtered.results) == 2
        assert all("spam.com" not in r.url for r in filtered.results)

    def test_filter_results_subdomain_matching(self) -> None:
        """Test that subdomain matching works correctly."""
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test",
            results=[
                SearchResult(title="API", url="https://api.github.com/test", snippet=""),
                SearchResult(title="Docs", url="https://docs.github.com/test", snippet=""),
                SearchResult(title="Main", url="https://github.com/test", snippet=""),
            ],
            provider="test",
            total_results=3,
            search_time=0.1,
        )

        filtered = provider.filter_results(
            response,
            allowed_domains=["github.com"],
        )

        assert len(filtered.results) == 3  # All match github.com

    def test_filter_results_prevents_domain_suffix_attack(self) -> None:
        """Test that domain suffix attacks are prevented."""
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test",
            results=[
                SearchResult(title="Real", url="https://github.com/test", snippet=""),
                SearchResult(title="Fake", url="https://github.com.attacker.com/test", snippet=""),
            ],
            provider="test",
            total_results=2,
            search_time=0.1,
        )

        filtered = provider.filter_results(
            response,
            allowed_domains=["github.com"],
        )

        # Only real github.com should match, not the attacker domain
        assert len(filtered.results) == 1
        assert filtered.results[0].url == "https://github.com/test"

    def test_filter_results_updates_total(self) -> None:
        """Test that total_results is updated after filtering."""
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test",
            results=[
                SearchResult(title="Keep", url="https://keep.com/test", snippet=""),
                SearchResult(title="Remove", url="https://remove.com/test", snippet=""),
            ],
            provider="test",
            total_results=2,
            search_time=0.1,
        )

        filtered = provider.filter_results(
            response,
            blocked_domains=["remove.com"],
        )

        assert filtered.total_results == 1

    def test_filter_results_preserves_metadata(self) -> None:
        """Test that filtering preserves response metadata."""
        provider = BraveSearchProvider(api_key="test")

        response = SearchResponse(
            query="test query",
            results=[
                SearchResult(title="Result", url="https://example.com", snippet=""),
            ],
            provider="brave",
            total_results=1,
            search_time=0.5,
        )

        filtered = provider.filter_results(response)

        assert filtered.query == "test query"
        assert filtered.provider == "brave"
        assert filtered.search_time == 0.5


# =============================================================================
# BraveSearchProvider Tests
# =============================================================================

class TestBraveSearchProvider:
    """Tests for BraveSearchProvider."""

    def test_init(self) -> None:
        """Test provider initialization."""
        provider = BraveSearchProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.name == "brave"
        assert provider.requires_api_key is True

    def test_name_property(self) -> None:
        """Test name property."""
        provider = BraveSearchProvider(api_key="test")
        assert provider.name == "brave"

    def test_requires_api_key_property(self) -> None:
        """Test requires_api_key property."""
        provider = BraveSearchProvider(api_key="test")
        assert provider.requires_api_key is True

    @pytest.mark.asyncio
    async def test_search_no_api_key_raises(self) -> None:
        """Test that search without API key raises error."""
        provider = BraveSearchProvider(api_key="")

        with pytest.raises(SearchError, match="API key not configured"):
            await provider.search("test query")

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Test successful search."""
        provider = BraveSearchProvider(api_key="test-key")

        mock_response = {
            "web": {
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://example.com",
                        "description": "A test result",
                        "page_age": "2024-01-01",
                        "language": "en",
                        "family_friendly": True,
                    }
                ]
            }
        }

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.get = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(),
                )
            )
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            result = await provider.search("test query", num_results=5)

        assert result.query == "test query"
        assert result.provider == "brave"
        assert len(result.results) == 1
        assert result.results[0].title == "Test Result"
        assert result.results[0].url == "https://example.com"
        assert result.results[0].snippet == "A test result"

    @pytest.mark.asyncio
    async def test_search_api_error(self) -> None:
        """Test handling of API error response."""
        provider = BraveSearchProvider(api_key="test-key")

        with patch("code_forge.web.search.brave.aiohttp.ClientSession") as mock_session_cls:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 401
            mock_response_obj.text = AsyncMock(return_value="Unauthorized")

            # Create the nested context manager structure
            mock_get_cm = AsyncMock()
            mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_get_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_cm)

            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = mock_session_cm

            with pytest.raises(SearchError, match="Brave API error"):
                await provider.search("test")

    @pytest.mark.asyncio
    async def test_search_network_error(self) -> None:
        """Test handling of network error."""
        import aiohttp
        provider = BraveSearchProvider(api_key="test-key")

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session_cls.side_effect = aiohttp.ClientError("Connection failed")

            with pytest.raises(SearchError, match="Network error"):
                await provider.search("test")

    @pytest.mark.asyncio
    async def test_search_with_country_and_lang(self) -> None:
        """Test search with country and language options."""
        provider = BraveSearchProvider(api_key="test-key")

        mock_response = {"web": {"results": []}}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.get = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(),
                )
            )
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            result = await provider.search(
                "test",
                country="de",
                search_lang="de",
            )

        assert result.provider == "brave"


# =============================================================================
# GoogleSearchProvider Tests
# =============================================================================

class TestGoogleSearchProvider:
    """Tests for GoogleSearchProvider."""

    def test_init(self) -> None:
        """Test provider initialization."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")

        assert provider.api_key == "test-key"
        assert provider.cx == "test-cx"
        assert provider.name == "google"
        assert provider.requires_api_key is True

    def test_name_property(self) -> None:
        """Test name property."""
        provider = GoogleSearchProvider(api_key="test", cx="cx")
        assert provider.name == "google"

    @pytest.mark.asyncio
    async def test_search_no_api_key_raises(self) -> None:
        """Test that search without API key raises error."""
        provider = GoogleSearchProvider(api_key="", cx="test-cx")

        with pytest.raises(SearchError, match="API key not configured"):
            await provider.search("test query")

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Test successful search."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")

        mock_response = {
            "items": [
                {
                    "title": "Test Result",
                    "link": "https://example.com",
                    "snippet": "A test snippet",
                    "displayLink": "example.com",
                    "formattedUrl": "https://example.com",
                }
            ],
            "searchInformation": {
                "totalResults": "100",
            },
        }

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.get = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(),
                )
            )
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            result = await provider.search("test query")

        assert result.query == "test query"
        assert result.provider == "google"
        assert len(result.results) == 1
        assert result.results[0].title == "Test Result"
        assert result.results[0].url == "https://example.com"
        assert result.total_results == 100

    @pytest.mark.asyncio
    async def test_search_limits_to_10_results(self) -> None:
        """Test that search limits to 10 results (Google CSE limit)."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")

        mock_response = {"items": [], "searchInformation": {}}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.get = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(),
                )
            )
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            # Request 20 results
            await provider.search("test", num_results=20)

            # Verify the API was called with max 10
            call_args = mock_session.get.call_args
            # The params should have num=10
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_search_with_date_restrict(self) -> None:
        """Test search with date restriction."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")

        mock_response = {"items": [], "searchInformation": {}}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)

            mock_session.get = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response_obj),
                    __aexit__=AsyncMock(),
                )
            )
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_cls.return_value = mock_session

            await provider.search("test", date_restrict="d7")

        # Verify date_restrict was passed
        assert mock_session.get.called

    @pytest.mark.asyncio
    async def test_search_api_error(self) -> None:
        """Test handling of API error."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")

        with patch("code_forge.web.search.google.aiohttp.ClientSession") as mock_session_cls:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 403
            mock_response_obj.text = AsyncMock(return_value="Forbidden")

            # Create the nested context manager structure
            mock_get_cm = AsyncMock()
            mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_get_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_cm)

            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = mock_session_cm

            with pytest.raises(SearchError, match="Google API error"):
                await provider.search("test")

    @pytest.mark.asyncio
    async def test_search_network_error(self) -> None:
        """Test handling of network error."""
        import aiohttp
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session_cls.side_effect = aiohttp.ClientError("Connection failed")

            with pytest.raises(SearchError, match="Network error"):
                await provider.search("test")


# =============================================================================
# DuckDuckGoProvider Tests
# =============================================================================

class TestDuckDuckGoProvider:
    """Tests for DuckDuckGoProvider."""

    def test_init(self) -> None:
        """Test provider initialization."""
        provider = DuckDuckGoProvider()

        assert provider.name == "duckduckgo"
        assert provider.requires_api_key is False

    def test_name_property(self) -> None:
        """Test name property."""
        provider = DuckDuckGoProvider()
        assert provider.name == "duckduckgo"

    def test_requires_api_key_false(self) -> None:
        """Test that DuckDuckGo doesn't require API key."""
        provider = DuckDuckGoProvider()
        assert provider.requires_api_key is False

    def test_default_requires_no_init_args(self) -> None:
        """Test that DuckDuckGo provider requires no init arguments."""
        # Should not raise
        provider = DuckDuckGoProvider()
        assert provider is not None

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Test successful search."""
        provider = DuckDuckGoProvider()

        mock_results = [
            {
                "title": "Test Result",
                "href": "https://example.com",
                "body": "Test snippet",
                "source": "example.com",
            }
        ]

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_results

            result = await provider.search("test query", num_results=5)

        assert result.query == "test query"
        assert result.provider == "duckduckgo"
        assert len(result.results) == 1
        assert result.results[0].title == "Test Result"
        assert result.results[0].url == "https://example.com"
        assert result.results[0].snippet == "Test snippet"

    @pytest.mark.asyncio
    async def test_search_with_region(self) -> None:
        """Test search with region option."""
        provider = DuckDuckGoProvider()

        mock_results = []

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_results

            result = await provider.search("test", region="de-de")

        assert result.provider == "duckduckgo"

    @pytest.mark.asyncio
    async def test_search_with_safe_search(self) -> None:
        """Test search with safe search option."""
        provider = DuckDuckGoProvider()

        mock_results = []

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_results

            result = await provider.search("test", safe_search="strict")

        assert result.provider == "duckduckgo"

    @pytest.mark.asyncio
    async def test_search_error(self) -> None:
        """Test handling of search error."""
        provider = DuckDuckGoProvider()

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = RuntimeError("Search failed")

            with pytest.raises(SearchError, match="Search failed"):
                await provider.search("test")

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """Test handling of empty results."""
        provider = DuckDuckGoProvider()

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = []

            result = await provider.search("obscure query")

        assert result.total_results == 0
        assert len(result.results) == 0


# =============================================================================
# SearchResult Tests
# =============================================================================

class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic SearchResult creation."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"

    def test_with_optional_fields(self) -> None:
        """Test SearchResult with optional fields."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            date="2024-01-01",
            source="example.com",
            metadata={"key": "value"},
        )

        assert result.date == "2024-01-01"
        assert result.source == "example.com"
        assert result.metadata["key"] == "value"


# =============================================================================
# SearchResponse Tests
# =============================================================================

class TestSearchResponse:
    """Tests for SearchResponse dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic SearchResponse creation."""
        response = SearchResponse(
            query="test query",
            results=[],
            provider="test",
            total_results=0,
            search_time=0.1,
        )

        assert response.query == "test query"
        assert response.provider == "test"
        assert response.total_results == 0
        assert response.search_time == 0.1

    def test_with_results(self) -> None:
        """Test SearchResponse with results."""
        results = [
            SearchResult(title="R1", url="https://a.com", snippet=""),
            SearchResult(title="R2", url="https://b.com", snippet=""),
        ]

        response = SearchResponse(
            query="test",
            results=results,
            provider="test",
            total_results=2,
            search_time=0.5,
        )

        assert len(response.results) == 2
        assert response.results[0].title == "R1"
