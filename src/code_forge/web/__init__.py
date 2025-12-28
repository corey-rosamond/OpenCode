"""Web tools for Code-Forge."""

from .cache import WebCache
from .fetch.fetcher import FetchError, URLFetcher
from .fetch.parser import HTMLParser
from .search.base import SearchError, SearchProvider
from .search.brave import BraveSearchProvider
from .search.duckduckgo import DuckDuckGoProvider
from .search.google import GoogleSearchProvider
from .tools import WebFetchTool, WebSearchTool
from .types import (
    FetchOptions,
    FetchResponse,
    ParsedContent,
    SearchResponse,
    SearchResult,
)

__all__ = [
    "BraveSearchProvider",
    "DuckDuckGoProvider",
    "FetchError",
    "FetchOptions",
    "FetchResponse",
    "GoogleSearchProvider",
    "HTMLParser",
    "ParsedContent",
    "SearchError",
    "SearchProvider",
    "SearchResponse",
    "SearchResult",
    "URLFetcher",
    "WebCache",
    "WebFetchTool",
    "WebSearchTool",
]
