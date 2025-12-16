"""Search provider interface."""

import logging
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse

from ..types import SearchResponse, SearchResult

logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Search provider error."""

    pass


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
        """Execute search query.

        Args:
            query: Search query string
            num_results: Maximum results to return
            **kwargs: Provider-specific options

        Returns:
            SearchResponse with results
        """
        ...

    def filter_results(
        self,
        response: SearchResponse,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
    ) -> SearchResponse:
        """Filter results by domain.

        Args:
            response: Search response
            allowed_domains: Only include these domains
            blocked_domains: Exclude these domains

        Returns:
            Filtered SearchResponse
        """
        if not allowed_domains and not blocked_domains:
            return response

        def domain_matches(domain: str, pattern: str) -> bool:
            """Check if domain matches pattern (exact or subdomain).

            Proper suffix matching to prevent attacks like:
            - "github.com" should NOT match "github.com.attacker.com"
            - "github.com" SHOULD match "www.github.com" and "api.github.com"
            """
            pattern = pattern.lower().lstrip(".")
            # Exact match
            if domain == pattern:
                return True
            # Subdomain match (domain ends with .pattern)
            if domain.endswith("." + pattern):
                return True
            return False

        filtered: list[SearchResult] = []
        for result in response.results:
            domain = urlparse(result.url).netloc.lower()

            # Check blocked domains (using proper suffix matching)
            if blocked_domains and any(
                domain_matches(domain, d) for d in blocked_domains
            ):
                continue

            # Check allowed domains (using proper suffix matching)
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
