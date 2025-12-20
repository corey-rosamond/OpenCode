"""Tests for web tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.web.cache import WebCache
from code_forge.web.fetch.fetcher import FetchError, URLFetcher
from code_forge.web.fetch.parser import HTMLParser
from code_forge.web.search.base import SearchError, SearchProvider
from code_forge.web.tools import WebFetchTool, WebSearchTool
from code_forge.web.types import FetchResponse, SearchResponse, SearchResult


class MockSearchProvider(SearchProvider):
    """Mock search provider for testing."""

    def __init__(self, name: str = "mock", results: list[SearchResult] | None = None):
        self._name = name
        self._results = results or []

    @property
    def name(self) -> str:
        return self._name

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs,
    ) -> SearchResponse:
        return SearchResponse(
            query=query,
            results=self._results[:num_results],
            provider=self.name,
            total_results=len(self._results),
        )


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    def test_initialization(self) -> None:
        """Test tool initialization."""
        providers = {"mock": MockSearchProvider()}
        tool = WebSearchTool(providers, "mock")
        assert tool.name == "web_search"
        assert tool.default_provider == "mock"

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful search execution."""
        results = [
            SearchResult(title="Result 1", url="https://a.com", snippet="Snippet 1"),
            SearchResult(title="Result 2", url="https://b.com", snippet="Snippet 2"),
        ]
        providers = {"mock": MockSearchProvider(results=results)}
        tool = WebSearchTool(providers, "mock")

        output = await tool.execute("test query", num_results=2)

        assert "## Search Results for: test query" in output
        assert "Result 1" in output
        assert "Result 2" in output

    @pytest.mark.asyncio
    async def test_execute_unknown_provider(self) -> None:
        """Test with unknown provider."""
        providers = {"mock": MockSearchProvider()}
        tool = WebSearchTool(providers, "mock")

        output = await tool.execute("test", provider="unknown")

        assert "Unknown provider: unknown" in output
        assert "mock" in output

    @pytest.mark.asyncio
    async def test_execute_no_results(self) -> None:
        """Test with no search results."""
        providers = {"mock": MockSearchProvider(results=[])}
        tool = WebSearchTool(providers, "mock")

        output = await tool.execute("obscure query")

        assert "No results found" in output

    @pytest.mark.asyncio
    async def test_execute_with_domain_filtering(self) -> None:
        """Test search with domain filtering."""
        results = [
            SearchResult(title="R1", url="https://example.com/page", snippet="S1"),
            SearchResult(title="R2", url="https://other.com/page", snippet="S2"),
        ]
        providers = {"mock": MockSearchProvider(results=results)}
        tool = WebSearchTool(providers, "mock")

        output = await tool.execute(
            "test",
            allowed_domains=["example.com"],
        )

        assert "example.com" in output
        assert "other.com" not in output

    @pytest.mark.asyncio
    async def test_execute_search_error(self) -> None:
        """Test handling of search errors."""
        mock_provider = AsyncMock(spec=SearchProvider)
        mock_provider.name = "error"
        mock_provider.search = AsyncMock(side_effect=SearchError("API error"))

        providers = {"error": mock_provider}
        tool = WebSearchTool(providers, "error")

        output = await tool.execute("test")

        assert "Search error" in output
        assert "API error" in output


class TestWebFetchTool:
    """Tests for WebFetchTool."""

    def test_initialization(self) -> None:
        """Test tool initialization."""
        fetcher = URLFetcher()
        parser = HTMLParser()
        cache = WebCache()
        tool = WebFetchTool(fetcher, parser, cache)

        assert tool.name == "web_fetch"
        assert tool.fetcher is fetcher
        assert tool.parser is parser
        assert tool.cache is cache

    def test_initialization_no_cache(self) -> None:
        """Test initialization without cache."""
        fetcher = URLFetcher()
        parser = HTMLParser()
        tool = WebFetchTool(fetcher, parser)

        assert tool.cache is None

    @pytest.mark.asyncio
    async def test_execute_success_markdown(self) -> None:
        """Test successful fetch with markdown format."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<html><body><h1>Title</h1><p>Content</p></body></html>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        parser = HTMLParser()
        tool = WebFetchTool(fetcher, parser)

        output = await tool.execute("https://example.com", format="markdown")

        assert "**Source:** https://example.com" in output
        assert "Title" in output

    @pytest.mark.asyncio
    async def test_execute_success_text(self) -> None:
        """Test fetch with text format."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<html><body><h1>Title</h1><p>Content</p></body></html>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        parser = HTMLParser()
        tool = WebFetchTool(fetcher, parser)

        output = await tool.execute("https://example.com", format="text")

        assert "**Source:**" in output
        assert "<html>" not in output

    @pytest.mark.asyncio
    async def test_execute_success_raw(self) -> None:
        """Test fetch with raw format."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<html><body>Raw HTML</body></html>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        tool = WebFetchTool(fetcher, HTMLParser())

        output = await tool.execute("https://example.com", format="raw")

        assert output == "<html><body>Raw HTML</body></html>"

    @pytest.mark.asyncio
    async def test_execute_with_cache_hit(self) -> None:
        """Test fetch with cache hit."""
        fetcher = AsyncMock(spec=URLFetcher)
        parser = HTMLParser()
        cache = WebCache()

        # Pre-populate cache
        cached_response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<p>Cached content</p>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        cache.set(cache.generate_key("https://example.com"), cached_response)

        tool = WebFetchTool(fetcher, parser, cache)

        output = await tool.execute("https://example.com", use_cache=True)

        # Should not call fetcher
        fetcher.fetch.assert_not_called()
        assert "[From cache]" in output

    @pytest.mark.asyncio
    async def test_execute_cache_bypass(self) -> None:
        """Test fetch with cache bypass."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<p>Fresh content</p>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        parser = HTMLParser()
        cache = WebCache()

        # Pre-populate cache
        cached_response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<p>Cached content</p>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        cache.set(cache.generate_key("https://example.com"), cached_response)

        tool = WebFetchTool(fetcher, parser, cache)

        output = await tool.execute("https://example.com", use_cache=False)

        # Should call fetcher
        fetcher.fetch.assert_called_once()
        assert "Fresh content" in output

    @pytest.mark.asyncio
    async def test_execute_caches_response(self) -> None:
        """Test that responses are cached."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<p>Content</p>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        cache = WebCache()
        tool = WebFetchTool(fetcher, HTMLParser(), cache)

        await tool.execute("https://example.com", use_cache=True)

        # Check cache was populated
        cached = cache.get(cache.generate_key("https://example.com"))
        assert isinstance(cached, FetchResponse)

    @pytest.mark.asyncio
    async def test_execute_fetch_error(self) -> None:
        """Test handling of fetch errors."""
        fetcher = AsyncMock(spec=URLFetcher)
        fetcher.fetch = AsyncMock(side_effect=FetchError("Connection failed"))

        tool = WebFetchTool(fetcher, HTMLParser())

        output = await tool.execute("https://example.com")

        assert "Fetch error" in output
        assert "Connection failed" in output

    @pytest.mark.asyncio
    async def test_execute_binary_content(self) -> None:
        """Test handling of binary content."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com/image.png",
            final_url="https://example.com/image.png",
            status_code=200,
            content_type="image/png",
            content=b"\x89PNG",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        tool = WebFetchTool(fetcher, HTMLParser())

        output = await tool.execute("https://example.com/image.png")

        assert "Binary content" in output
        assert "image/png" in output

    @pytest.mark.asyncio
    async def test_execute_non_html_content(self) -> None:
        """Test handling of non-HTML text content."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com/data.json",
            final_url="https://example.com/data.json",
            status_code=200,
            content_type="application/json",
            content='{"key": "value"}',
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        tool = WebFetchTool(fetcher, HTMLParser())

        output = await tool.execute("https://example.com/data.json")

        assert '{"key": "value"}' in output

    @pytest.mark.asyncio
    async def test_execute_truncates_long_content(self) -> None:
        """Test that long content is truncated."""
        fetcher = AsyncMock(spec=URLFetcher)
        long_content = "x" * 60000
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/plain",
            content=long_content,
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        tool = WebFetchTool(fetcher, HTMLParser())

        output = await tool.execute("https://example.com")

        assert "[Content truncated...]" in output
        assert len(output) < 60000

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self) -> None:
        """Test fetch with custom timeout."""
        fetcher = AsyncMock(spec=URLFetcher)
        response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<p>Content</p>",
            headers={},
            encoding="utf-8",
            fetch_time=0.1,
        )
        fetcher.fetch = AsyncMock(return_value=response)

        tool = WebFetchTool(fetcher, HTMLParser())

        await tool.execute("https://example.com", timeout=60)

        # Check that fetch was called with options (positional args)
        call_args = fetcher.fetch.call_args
        # Args are (url, options)
        assert call_args[0][1].timeout == 60
