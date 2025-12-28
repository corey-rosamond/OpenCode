"""Web search tool implementation as BaseTool.

Wraps the existing web search functionality to expose it to the LLM
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
from code_forge.web.search import (
    DuckDuckGoProvider,
    SearchError,
    SearchProvider,
)


class WebSearchBaseTool(BaseTool):
    """Search the web for information.

    Uses available search providers (DuckDuckGo by default) to find
    relevant information on the web. Results include titles, URLs,
    and snippets.
    """

    def __init__(
        self,
        providers: dict[str, SearchProvider] | None = None,
        default_provider: str = "duckduckgo",
    ) -> None:
        """Initialize web search tool.

        Args:
            providers: Available search providers (creates DuckDuckGo if None).
            default_provider: Default provider name.
        """
        if providers is None:
            providers = {"duckduckgo": DuckDuckGoProvider()}
        self._providers = providers
        self._default_provider = default_provider

    @property
    def name(self) -> str:
        """Return unique tool identifier."""
        return "WebSearch"

    @property
    def description(self) -> str:
        """Return human-readable description for LLM."""
        return (
            "Search the web for information. Returns search results with "
            "titles, URLs, and snippets. Use this to find documentation, "
            "examples, articles, or any web content."
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
                name="query",
                type="string",
                description="The search query to execute.",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="Number of results to return (default: 10).",
                required=False,
                default=10,
                minimum=1,
                maximum=50,
            ),
            ToolParameter(
                name="provider",
                type="string",
                description="Search provider to use (default: duckduckgo).",
                required=False,
                enum=["duckduckgo", "brave", "google"],
            ),
            ToolParameter(
                name="allowed_domains",
                type="array",
                description="Only include results from these domains.",
                required=False,
            ),
            ToolParameter(
                name="blocked_domains",
                type="array",
                description="Exclude results from these domains.",
                required=False,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        """Execute the web search.

        Args:
            context: Execution context.
            **kwargs: Tool parameters (query, num_results, etc.).

        Returns:
            ToolResult with search results or error message.
        """
        query = kwargs["query"]
        num_results = kwargs.get("num_results", 10)
        provider_name = kwargs.get("provider", self._default_provider)
        allowed_domains = kwargs.get("allowed_domains")
        blocked_domains = kwargs.get("blocked_domains")

        # Get provider
        provider = self._providers.get(provider_name)
        if not provider:
            available = ", ".join(self._providers.keys())
            return ToolResult.fail(
                f"Unknown search provider: '{provider_name}'. "
                f"Available: {available}"
            )

        try:
            # Execute search
            response = await provider.search(query, num_results)

            # Apply domain filtering
            response = provider.filter_results(
                response, allowed_domains, blocked_domains
            )

            if not response.results:
                return ToolResult.ok(
                    f"No results found for: {query}",
                    query=query,
                    provider=provider_name,
                    result_count=0,
                )

            # Format results as markdown
            output = response.to_markdown()

            return ToolResult.ok(
                output,
                query=query,
                provider=provider_name,
                result_count=len(response.results),
            )

        except SearchError as e:
            return ToolResult.fail(f"Search error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Unexpected search error: {e}")
