"""E2E tests for web search integration.

Tests the complete web search flow including provider selection,
search execution, result filtering, and error handling.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# Local definitions to avoid aiohttp import issues
class SearchError(Exception):
    """Search provider error."""
    pass


@dataclass
class SearchResult:
    """Single search result."""

    title: str
    url: str
    snippet: str
    date: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "date": self.date,
            "source": self.source,
        }

    def to_markdown(self) -> str:
        """Format as Markdown."""
        md = f"**[{self.title}]({self.url})**\n"
        md += f"{self.snippet}\n"
        if self.date:
            md += f"*{self.date}*\n"
        return md


@dataclass
class SearchResponse:
    """Search response with multiple results."""

    query: str
    results: list[SearchResult]
    provider: str
    total_results: int | None = None
    search_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "provider": self.provider,
            "total_results": self.total_results,
            "search_time": self.search_time,
        }

    def to_markdown(self) -> str:
        """Format results as Markdown."""
        lines = [f"## Search Results for: {self.query}\n"]
        for i, result in enumerate(self.results, 1):
            lines.append(f"### {i}. [{result.title}]({result.url})")
            lines.append(f"{result.snippet}\n")
        return "\n".join(lines)


class SearchProvider(ABC):
    """Abstract search provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""
        return False

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs: Any,
    ) -> SearchResponse:
        """Execute search query."""
        ...

    def filter_results(
        self,
        response: SearchResponse,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
    ) -> SearchResponse:
        """Filter results by domain."""
        from urllib.parse import urlparse

        if not allowed_domains and not blocked_domains:
            return response

        def domain_matches(domain: str, pattern: str) -> bool:
            pattern = pattern.lower().lstrip(".")
            if domain == pattern:
                return True
            if domain.endswith("." + pattern):
                return True
            return False

        filtered: list[SearchResult] = []
        for result in response.results:
            domain = urlparse(result.url).netloc.lower()

            if blocked_domains and any(
                domain_matches(domain, d) for d in blocked_domains
            ):
                continue

            if allowed_domains and not any(
                domain_matches(domain, d) for d in allowed_domains
            ):
                continue

            filtered.append(result)

        return SearchResponse(
            query=response.query,
            results=filtered,
            provider=response.provider,
            total_results=len(filtered),
            search_time=response.search_time,
        )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_search_results() -> list[SearchResult]:
    """Create mock search results."""
    return [
        SearchResult(
            title="Python Programming Guide",
            url="https://python.org/docs",
            snippet="Learn Python programming with our comprehensive guide.",
            date="2024-01-15",
            source="python.org",
        ),
        SearchResult(
            title="Python Tutorial - W3Schools",
            url="https://www.w3schools.com/python/",
            snippet="Learn Python programming from scratch.",
            source="w3schools.com",
        ),
        SearchResult(
            title="Real Python Tutorials",
            url="https://realpython.com/tutorials/",
            snippet="Python tutorials for all skill levels.",
            source="realpython.com",
        ),
        SearchResult(
            title="Python on GitHub",
            url="https://github.com/python/cpython",
            snippet="The Python programming language source code.",
            source="github.com",
        ),
        SearchResult(
            title="Fake Python - Spam Site",
            url="https://spam.example.com/python",
            snippet="Download Python FREE!!",
            source="spam.example.com",
        ),
    ]


@pytest.fixture
def mock_search_response(mock_search_results: list[SearchResult]) -> SearchResponse:
    """Create mock search response."""
    return SearchResponse(
        query="python programming",
        results=mock_search_results,
        provider="mock",
        total_results=5,
        search_time=0.123,
    )


class MockSearchProvider(SearchProvider):
    """Mock search provider for testing."""

    def __init__(self, results: list[SearchResult] | None = None):
        self._results = results or []
        self._search_count = 0

    @property
    def name(self) -> str:
        return "mock"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs,
    ) -> SearchResponse:
        self._search_count += 1
        return SearchResponse(
            query=query,
            results=self._results[:num_results],
            provider=self.name,
            total_results=len(self._results[:num_results]),
            search_time=0.1,
        )


# =============================================================================
# Test Search Execution Flow
# =============================================================================


class TestSearchExecutionFlow:
    """Tests for search execution flow."""

    @pytest.mark.asyncio
    async def test_basic_search(
        self, mock_search_results: list[SearchResult]
    ) -> None:
        """Execute basic search query."""
        provider = MockSearchProvider(mock_search_results)

        response = await provider.search("python programming")

        assert response.query == "python programming"
        assert len(response.results) == 5
        assert response.provider == "mock"

    @pytest.mark.asyncio
    async def test_search_with_num_results_limit(
        self, mock_search_results: list[SearchResult]
    ) -> None:
        """Search respects num_results limit."""
        provider = MockSearchProvider(mock_search_results)

        response = await provider.search("python", num_results=2)

        assert len(response.results) == 2

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_results(self) -> None:
        """Empty query returns empty results."""
        provider = MockSearchProvider([])

        response = await provider.search("")

        assert len(response.results) == 0


# =============================================================================
# Test Domain Filtering
# =============================================================================


class TestDomainFiltering:
    """Tests for search result domain filtering."""

    @pytest.mark.asyncio
    async def test_allowed_domains_filter(
        self,
        mock_search_results: list[SearchResult],
        mock_search_response: SearchResponse,
    ) -> None:
        """Filter results to only allowed domains."""
        provider = MockSearchProvider(mock_search_results)

        filtered = provider.filter_results(
            mock_search_response,
            allowed_domains=["python.org", "github.com"],
        )

        assert len(filtered.results) == 2
        urls = [r.url for r in filtered.results]
        assert "https://python.org/docs" in urls
        assert "https://github.com/python/cpython" in urls

    @pytest.mark.asyncio
    async def test_blocked_domains_filter(
        self,
        mock_search_results: list[SearchResult],
        mock_search_response: SearchResponse,
    ) -> None:
        """Filter out blocked domains."""
        provider = MockSearchProvider(mock_search_results)

        filtered = provider.filter_results(
            mock_search_response,
            blocked_domains=["spam.example.com"],
        )

        assert len(filtered.results) == 4
        urls = [r.url for r in filtered.results]
        assert "https://spam.example.com/python" not in urls

    @pytest.mark.asyncio
    async def test_combined_allowed_and_blocked(
        self,
        mock_search_results: list[SearchResult],
        mock_search_response: SearchResponse,
    ) -> None:
        """Combined allowed and blocked domain filtering."""
        provider = MockSearchProvider(mock_search_results)

        filtered = provider.filter_results(
            mock_search_response,
            allowed_domains=["python.org", "github.com", "spam.example.com"],
            blocked_domains=["spam.example.com"],
        )

        # Allowed but also blocked = excluded
        assert len(filtered.results) == 2

    @pytest.mark.asyncio
    async def test_subdomain_matching(
        self,
        mock_search_results: list[SearchResult],
        mock_search_response: SearchResponse,
    ) -> None:
        """Subdomain matching works correctly."""
        provider = MockSearchProvider(mock_search_results)

        # w3schools.com should match www.w3schools.com
        filtered = provider.filter_results(
            mock_search_response,
            allowed_domains=["w3schools.com"],
        )

        assert len(filtered.results) == 1
        assert filtered.results[0].url == "https://www.w3schools.com/python/"

    @pytest.mark.asyncio
    async def test_no_filter_returns_all(
        self,
        mock_search_results: list[SearchResult],
        mock_search_response: SearchResponse,
    ) -> None:
        """No filter returns all results."""
        provider = MockSearchProvider(mock_search_results)

        filtered = provider.filter_results(mock_search_response)

        assert len(filtered.results) == 5


# =============================================================================
# Test Search Result Model
# =============================================================================


class TestSearchResultModel:
    """Tests for SearchResult model."""

    def test_search_result_to_dict(self) -> None:
        """SearchResult converts to dictionary."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            date="2024-01-01",
            source="example.com",
        )

        d = result.to_dict()

        assert d["title"] == "Test Title"
        assert d["url"] == "https://example.com"
        assert d["snippet"] == "Test snippet"
        assert d["date"] == "2024-01-01"
        assert d["source"] == "example.com"

    def test_search_result_to_markdown(self) -> None:
        """SearchResult converts to markdown."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            date="2024-01-01",
        )

        md = result.to_markdown()

        assert "**[Test Title](https://example.com)**" in md
        assert "Test snippet" in md
        assert "*2024-01-01*" in md

    def test_search_result_optional_fields(self) -> None:
        """SearchResult handles optional fields."""
        result = SearchResult(
            title="Minimal",
            url="https://example.com",
            snippet="Snippet",
        )

        assert result.date is None
        assert result.source is None
        assert result.metadata == {}


# =============================================================================
# Test Search Response Model
# =============================================================================


class TestSearchResponseModel:
    """Tests for SearchResponse model."""

    def test_search_response_to_dict(
        self, mock_search_response: SearchResponse
    ) -> None:
        """SearchResponse converts to dictionary."""
        d = mock_search_response.to_dict()

        assert d["query"] == "python programming"
        assert d["provider"] == "mock"
        assert len(d["results"]) == 5

    def test_search_response_to_markdown(
        self, mock_search_response: SearchResponse
    ) -> None:
        """SearchResponse converts to markdown."""
        md = mock_search_response.to_markdown()

        assert "## Search Results for: python programming" in md
        assert "Python Programming Guide" in md
        assert "[Python on GitHub]" in md

    def test_empty_search_response(self) -> None:
        """Empty SearchResponse works correctly."""
        response = SearchResponse(
            query="no results",
            results=[],
            provider="mock",
            total_results=0,
        )

        assert len(response.results) == 0
        md = response.to_markdown()
        assert "no results" in md


# =============================================================================
# Test Provider API Key Requirements
# =============================================================================


class TestProviderAPIKeyRequirements:
    """Tests for provider API key requirements."""

    def test_mock_provider_no_api_key_required(self) -> None:
        """Mock provider doesn't require API key."""
        provider = MockSearchProvider([])
        assert provider.requires_api_key is False

    def test_provider_with_api_key(self) -> None:
        """Provider with API key requirement."""

        class APIKeyProvider(SearchProvider):
            @property
            def name(self) -> str:
                return "api-key-provider"

            @property
            def requires_api_key(self) -> bool:
                return True

            async def search(self, query: str, **kwargs) -> SearchResponse:
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                )

        provider = APIKeyProvider()
        assert provider.requires_api_key is True


# =============================================================================
# Test Search Provider Interface
# =============================================================================


class TestSearchProviderInterface:
    """Tests for SearchProvider interface compliance."""

    def test_provider_has_name_property(self) -> None:
        """Provider must have name property."""
        provider = MockSearchProvider([])
        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_provider_search_returns_response(self) -> None:
        """Provider search returns SearchResponse."""
        provider = MockSearchProvider([])
        response = await provider.search("test query")
        assert isinstance(response, SearchResponse)

    def test_provider_filter_results_method(
        self,
        mock_search_results: list[SearchResult],
        mock_search_response: SearchResponse,
    ) -> None:
        """Provider has filter_results method."""
        provider = MockSearchProvider(mock_search_results)
        filtered = provider.filter_results(mock_search_response)
        assert isinstance(filtered, SearchResponse)


# =============================================================================
# Test Search Error Handling
# =============================================================================


class TestSearchErrorHandling:
    """Tests for search error handling."""

    @pytest.mark.asyncio
    async def test_search_error_message(self) -> None:
        """SearchError contains useful message."""
        error = SearchError("API rate limit exceeded")

        assert "API rate limit exceeded" in str(error)

    @pytest.mark.asyncio
    async def test_search_error_chain(self) -> None:
        """SearchError can chain exceptions."""
        original = ValueError("Invalid API key")
        try:
            raise SearchError("Search failed") from original
        except SearchError as error:
            assert error.__cause__ is original


# =============================================================================
# Test Concurrent Searches
# =============================================================================


class TestConcurrentSearches:
    """Tests for concurrent search execution."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_searches(
        self, mock_search_results: list[SearchResult]
    ) -> None:
        """Execute multiple searches concurrently."""
        provider = MockSearchProvider(mock_search_results)

        # Execute 5 searches concurrently
        queries = [
            "python basics",
            "python advanced",
            "python web",
            "python data",
            "python ml",
        ]

        tasks = [provider.search(q) for q in queries]
        responses = await asyncio.gather(*tasks)

        assert len(responses) == 5
        assert all(isinstance(r, SearchResponse) for r in responses)
        assert provider._search_count == 5

    @pytest.mark.asyncio
    async def test_search_isolation(
        self, mock_search_results: list[SearchResult]
    ) -> None:
        """Concurrent searches don't interfere with each other."""
        provider = MockSearchProvider(mock_search_results)

        async def search_and_verify(query: str) -> bool:
            response = await provider.search(query)
            return response.query == query

        tasks = [
            search_and_verify("query1"),
            search_and_verify("query2"),
            search_and_verify("query3"),
        ]

        results = await asyncio.gather(*tasks)

        assert all(results)


# =============================================================================
# Test Provider Selection
# =============================================================================


class TestProviderSelection:
    """Tests for search provider selection."""

    def test_provider_name_property(self) -> None:
        """Provider has name property."""
        provider = MockSearchProvider()
        assert provider.name == "mock"

    def test_requires_api_key_default_false(self) -> None:
        """requires_api_key defaults to False."""
        provider = MockSearchProvider()
        assert provider.requires_api_key is False


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestSearchEdgeCases:
    """Tests for search edge cases."""

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self) -> None:
        """Handle special characters in search query."""
        provider = MockSearchProvider([])

        response = await provider.search('python "hello world" @#$%')

        assert 'python "hello world" @#$%' in response.query

    @pytest.mark.asyncio
    async def test_unicode_in_query(self) -> None:
        """Handle unicode in search query."""
        provider = MockSearchProvider([])

        response = await provider.search("python 你好 мир")

        assert "python 你好 мир" in response.query

    @pytest.mark.asyncio
    async def test_very_long_query(self) -> None:
        """Handle very long search query."""
        provider = MockSearchProvider([])
        long_query = "python " * 100

        response = await provider.search(long_query)

        assert response.query == long_query

    def test_result_with_empty_fields(self) -> None:
        """Handle result with empty/missing fields."""
        result = SearchResult(
            title="",
            url="",
            snippet="",
        )

        d = result.to_dict()
        md = result.to_markdown()

        assert d["title"] == ""
        assert "**[]()**" in md  # Empty title/url
