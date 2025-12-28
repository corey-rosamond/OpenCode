"""Web fetch tool implementation as BaseTool.

Wraps the existing web fetch functionality to expose it to the LLM
via the tool registry.
"""

from __future__ import annotations

from typing import Any

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.web.cache import WebCache
from code_forge.web.fetch import FetchError, HTMLParser, URLFetcher
from code_forge.web.types import FetchOptions, FetchResponse


class WebFetchBaseTool(BaseTool):
    """Fetch and process content from a URL.

    Fetches web pages and converts them to markdown or plain text
    for easy consumption. Supports caching for repeated requests.
    """

    def __init__(
        self,
        fetcher: URLFetcher | None = None,
        parser: HTMLParser | None = None,
        cache: WebCache | None = None,
    ) -> None:
        """Initialize web fetch tool.

        Args:
            fetcher: URL fetcher (creates default if None).
            parser: HTML parser (creates default if None).
            cache: Web cache (optional).
        """
        self._fetcher = fetcher or URLFetcher()
        self._parser = parser or HTMLParser()
        self._cache = cache

    @property
    def name(self) -> str:
        """Return unique tool identifier."""
        return "WebFetch"

    @property
    def description(self) -> str:
        """Return human-readable description for LLM."""
        return (
            "Fetch content from a URL and convert it to markdown or text. "
            "Use this to read documentation pages, articles, or any web content. "
            "HTTP URLs are automatically upgraded to HTTPS."
        )

    @property
    def category(self) -> ToolCategory:
        """Return tool category for grouping."""
        return ToolCategory.WEB

    @property
    def parameters(self) -> list[ToolParameter]:
        """Return list of accepted parameters."""
        return [
            ToolParameter(
                name="url",
                type="string",
                description="The URL to fetch content from.",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="format",
                type="string",
                description="Output format: markdown, text, or raw (default: markdown).",
                required=False,
                default="markdown",
                enum=["markdown", "text", "raw"],
            ),
            ToolParameter(
                name="use_cache",
                type="boolean",
                description="Use cached content if available (default: true).",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Request timeout in seconds (default: 30).",
                required=False,
                default=30,
                minimum=5,
                maximum=120,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        """Execute the URL fetch.

        Args:
            context: Execution context.
            **kwargs: Tool parameters (url, format, use_cache, timeout).

        Returns:
            ToolResult with fetched content or error message.
        """
        url = kwargs["url"]
        output_format = kwargs.get("format", "markdown")
        use_cache = kwargs.get("use_cache", True)
        timeout = kwargs.get("timeout", 30)

        # Check cache
        cache_key: str | None = None
        if use_cache and self._cache:
            cache_key = self._cache.generate_key(url)
            cached = self._cache.get(cache_key)
            if cached:
                content = self._format_response(cached, output_format)
                return ToolResult.ok(
                    content,
                    url=url,
                    from_cache=True,
                )

        try:
            # Create fetch options with timeout
            options = FetchOptions(timeout=timeout)

            # Fetch URL
            response = await self._fetcher.fetch(url, options)

            # Cache response
            if use_cache and self._cache and cache_key:
                self._cache.set(cache_key, response)

            # Format and return
            content = self._format_response(response, output_format)

            return ToolResult.ok(
                content,
                url=url,
                final_url=response.final_url,
                status_code=response.status_code,
                content_type=response.content_type,
                from_cache=False,
            )

        except FetchError as e:
            return ToolResult.fail(f"Fetch error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Unexpected fetch error: {e}")

    def _format_response(
        self, response: FetchResponse, output_format: str
    ) -> str:
        """Format the fetch response based on format option.

        Args:
            response: Fetch response to format.
            output_format: Format type (markdown, text, raw).

        Returns:
            Formatted content string.
        """
        if not isinstance(response.content, str):
            return f"[Binary content: {response.content_type}]"

        if output_format == "raw":
            return response.content

        # Parse HTML content
        if response.is_html:
            if output_format == "text":
                content = self._parser.to_text(response.content)
            else:
                content = self._parser.to_markdown(response.content)
        else:
            content = response.content

        # Truncate if too long
        max_len = 50000
        if len(content) > max_len:
            content = content[:max_len] + "\n\n[Content truncated...]"

        # Add source info
        result = f"**Source:** {response.final_url}\n\n{content}"

        if response.from_cache:
            result = "[From cache]\n\n" + result

        return result
