"""Tests for URL fetcher and HTML parser."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from code_forge.web.fetch.fetcher import FetchError, URLFetcher
from code_forge.web.fetch.parser import HTMLParser
from code_forge.web.types import FetchOptions


class TestURLFetcher:
    """Tests for URLFetcher."""

    def test_initialization(self) -> None:
        """Test fetcher initialization."""
        fetcher = URLFetcher()
        assert isinstance(fetcher.default_options, FetchOptions)
        assert fetcher.default_options.timeout == 30

    def test_initialization_custom(self) -> None:
        """Test fetcher with custom options."""
        options = FetchOptions(timeout=60, max_size=1024)
        fetcher = URLFetcher(options)
        assert fetcher.default_options.timeout == 60
        assert fetcher.default_options.max_size == 1024

    @pytest.mark.asyncio
    async def test_fetch_success(self) -> None:
        """Test successful fetch."""
        fetcher = URLFetcher()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.url = "https://example.com"
        mock_resp.content_type = "text/html"
        mock_resp.charset = "utf-8"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.content = AsyncMock()
        mock_resp.content.iter_chunked = MagicMock(
            return_value=AsyncIterator([b"<html>test</html>"])
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("aiohttp.TCPConnector"):
                response = await fetcher.fetch("https://example.com")

        assert response.status_code == 200
        assert response.content == "<html>test</html>"

    @pytest.mark.asyncio
    async def test_fetch_http_to_https(self) -> None:
        """Test HTTP URL is upgraded to HTTPS."""
        fetcher = URLFetcher()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.url = "https://example.com"
        mock_resp.content_type = "text/html"
        mock_resp.charset = "utf-8"
        mock_resp.headers = {}
        mock_resp.content = AsyncMock()
        mock_resp.content.iter_chunked = MagicMock(
            return_value=AsyncIterator([b"test"])
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
            with patch("aiohttp.TCPConnector"):
                # Fetch with HTTP URL
                await fetcher.fetch("http://example.com")

    @pytest.mark.asyncio
    async def test_fetch_content_too_large_header(self) -> None:
        """Test rejection of large content from Content-Length header."""
        options = FetchOptions(max_size=100)
        fetcher = URLFetcher(options)

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Length": "1000"}

        # Create proper nested context manager mocks
        mock_resp_cm = MagicMock()
        mock_resp_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            with patch("aiohttp.TCPConnector"):
                with pytest.raises(FetchError, match="Content too large"):
                    await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_content_too_large_stream(self) -> None:
        """Test rejection of large content during streaming."""
        options = FetchOptions(max_size=10)
        fetcher = URLFetcher(options)

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {}
        mock_resp.content = AsyncMock()
        mock_resp.content.iter_chunked = MagicMock(
            return_value=AsyncIterator([b"x" * 100])
        )

        # Create proper nested context manager mocks
        mock_resp_cm = MagicMock()
        mock_resp_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            with patch("aiohttp.TCPConnector"):
                with pytest.raises(FetchError, match="exceeds max size"):
                    await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error_type,error_message,expected_match",
        [
            (TimeoutError, "timeout", "Timeout"),
            (TimeoutError, "request timeout", "Timeout"),
            (TimeoutError, "connection timeout", "Timeout"),
        ]
    )
    async def test_fetch_timeout(self, error_type, error_message: str, expected_match: str) -> None:
        """Test timeout handling."""
        fetcher = URLFetcher()

        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.side_effect = error_type(error_message)
            with patch("aiohttp.TCPConnector"):
                with pytest.raises(FetchError, match=expected_match):
                    await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error_message",
        [
            "connection failed",
            "network unreachable",
            "host not found",
            "connection refused",
        ]
    )
    async def test_fetch_network_error(self, error_message: str) -> None:
        """Test network error handling."""
        fetcher = URLFetcher()

        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.side_effect = aiohttp.ClientError(error_message)
            with patch("aiohttp.TCPConnector"):
                with pytest.raises(FetchError, match="Network error"):
                    await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_too_many_redirects(self) -> None:
        """Test redirect limit handling."""
        fetcher = URLFetcher()

        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.side_effect = aiohttp.TooManyRedirects(
                history=(), request_info=MagicMock()
            )
            with patch("aiohttp.TCPConnector"):
                with pytest.raises(FetchError, match="Too many redirects"):
                    await fetcher.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_binary_content(self) -> None:
        """Test fetching binary content."""
        fetcher = URLFetcher()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.url = "https://example.com/image.png"
        mock_resp.content_type = "image/png"
        mock_resp.charset = None
        mock_resp.headers = {}
        mock_resp.content = AsyncMock()
        mock_resp.content.iter_chunked = MagicMock(
            return_value=AsyncIterator([b"\x89PNG"])
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("aiohttp.TCPConnector"):
                response = await fetcher.fetch("https://example.com/image.png")

        assert isinstance(response.content, bytes)

    @pytest.mark.asyncio
    async def test_fetch_multiple(self) -> None:
        """Test fetching multiple URLs."""
        fetcher = URLFetcher()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.url = "https://example.com"
        mock_resp.content_type = "text/html"
        mock_resp.charset = "utf-8"
        mock_resp.headers = {}
        mock_resp.content = AsyncMock()
        mock_resp.content.iter_chunked = MagicMock(
            return_value=AsyncIterator([b"content"])
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("aiohttp.TCPConnector"):
                results = await fetcher.fetch_multiple(
                    ["https://a.com", "https://b.com"],
                    concurrency=2,
                )

        assert len(results) == 2


class TestURLFetcherStatusCodes:
    """Test handling of different HTTP status codes."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status_code",
        [
            200,  # OK
            201,  # Created
            204,  # No Content
            301,  # Moved Permanently
            302,  # Found
            304,  # Not Modified
        ]
    )
    async def test_successful_status_codes(self, status_code: int) -> None:
        """Test successful HTTP status codes."""
        fetcher = URLFetcher()

        mock_resp = AsyncMock()
        mock_resp.status = status_code
        mock_resp.url = "https://example.com"
        mock_resp.content_type = "text/html"
        mock_resp.charset = "utf-8"
        mock_resp.headers = {}
        mock_resp.content = AsyncMock()
        mock_resp.content.iter_chunked = MagicMock(
            return_value=AsyncIterator([b"content"])
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("aiohttp.TCPConnector"):
                response = await fetcher.fetch("https://example.com")

        assert response.status_code == status_code


class AsyncIterator:
    """Helper for async iteration in tests."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class TestHTMLParser:
    """Tests for HTMLParser."""

    def test_initialization(self) -> None:
        """Test parser initialization."""
        parser = HTMLParser()
        assert hasattr(parser, '_h2t')
        assert parser._h2t.__class__.__name__ == 'HTML2Text'

    def test_parse_basic(self) -> None:
        """Test basic HTML parsing."""
        parser = HTMLParser()
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test.</p>
        </body>
        </html>
        """
        content = parser.parse(html)

        assert content.title == "Test Page"
        assert "Hello World" in content.text
        assert "This is a test" in content.text

    def test_parse_extracts_links(self) -> None:
        """Test link extraction."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <a href="/page1">Link 1</a>
            <a href="https://example.com/page2">Link 2</a>
        </body>
        </html>
        """
        content = parser.parse(html, base_url="https://example.com")

        assert len(content.links) == 2
        assert content.links[0]["url"] == "https://example.com/page1"
        assert content.links[1]["url"] == "https://example.com/page2"

    def test_parse_extracts_images(self) -> None:
        """Test image extraction."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <img src="/image1.png" alt="Image 1">
            <img src="https://example.com/image2.png" alt="Image 2">
        </body>
        </html>
        """
        content = parser.parse(html, base_url="https://example.com")

        assert len(content.images) == 2
        assert content.images[0]["src"] == "https://example.com/image1.png"
        assert content.images[0]["alt"] == "Image 1"

    def test_parse_extracts_metadata(self) -> None:
        """Test metadata extraction."""
        parser = HTMLParser()
        html = """
        <html>
        <head>
            <meta name="description" content="Test description">
            <meta name="keywords" content="test, keywords">
            <meta property="og:title" content="OG Title">
        </head>
        <body></body>
        </html>
        """
        content = parser.parse(html)

        assert content.metadata["description"] == "Test description"
        assert content.metadata["keywords"] == "test, keywords"
        assert content.metadata["og:title"] == "OG Title"

    def test_to_text_removes_scripts(self) -> None:
        """Test that scripts are removed from text."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <script>alert('xss');</script>
            <p>Visible text</p>
            <style>.hidden { display: none; }</style>
        </body>
        </html>
        """
        text = parser.to_text(html)

        assert "alert" not in text
        assert "display: none" not in text
        assert "Visible text" in text

    def test_to_text_removes_nav_footer(self) -> None:
        """Test that nav and footer are removed."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <nav>Navigation links</nav>
            <main>Main content</main>
            <footer>Footer content</footer>
        </body>
        </html>
        """
        text = parser.to_text(html)

        assert "Navigation links" not in text
        assert "Footer content" not in text
        assert "Main content" in text

    def test_to_markdown(self) -> None:
        """Test HTML to Markdown conversion."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <h1>Heading 1</h1>
            <h2>Heading 2</h2>
            <p>Paragraph with <strong>bold</strong> and <em>italic</em>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
        </html>
        """
        markdown = parser.to_markdown(html)

        assert "# Heading 1" in markdown
        assert "## Heading 2" in markdown
        assert "**bold**" in markdown
        assert "_italic_" in markdown or "*italic*" in markdown

    def test_extract_main_content(self) -> None:
        """Test main content extraction."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <nav>Navigation</nav>
            <header>Header</header>
            <main>
                <article>
                    <h1>Article Title</h1>
                    <p>Article content.</p>
                </article>
            </main>
            <footer>Footer</footer>
        </body>
        </html>
        """
        main = parser.extract_main_content(html)

        assert "Navigation" not in main
        assert "Header" not in main
        assert "Footer" not in main
        assert "Article Title" in main
        assert "Article content" in main

    def test_extract_main_content_fallback(self) -> None:
        """Test fallback when no main element exists."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <div class="content">
                <p>Main content here.</p>
            </div>
        </body>
        </html>
        """
        main = parser.extract_main_content(html)
        assert "Main content here" in main

    def test_handles_malformed_html(self) -> None:
        """Test handling of malformed HTML."""
        parser = HTMLParser()
        html = """
        <html>
        <body>
            <div>Unclosed div
            <p>Nested paragraph
            <span>More nesting
        </body>
        """
        # Should not raise an error
        content = parser.parse(html)
        assert "Unclosed div" in content.text

    def test_parse_no_title(self) -> None:
        """Test parsing HTML without title."""
        parser = HTMLParser()
        html = "<html><body><p>No title</p></body></html>"
        content = parser.parse(html)
        assert content.title is None
