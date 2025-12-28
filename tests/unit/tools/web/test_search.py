"""Unit tests for WebSearchBaseTool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from code_forge.tools.base import ExecutionContext, ToolCategory
from code_forge.tools.web.search import WebSearchBaseTool
from code_forge.web.search import SearchError
from code_forge.web.types import SearchResponse, SearchResult


class TestWebSearchBaseToolProperties:
    """Test WebSearchBaseTool property methods."""

    def test_name_property(self) -> None:
        """WebSearchBaseTool.name returns 'WebSearch'."""
        tool = WebSearchBaseTool()
        assert tool.name == "WebSearch"

    def test_category_property(self) -> None:
        """WebSearchBaseTool.category returns ToolCategory.WEB."""
        tool = WebSearchBaseTool()
        assert tool.category == ToolCategory.WEB

    def test_description_property(self) -> None:
        """WebSearchBaseTool.description is informative."""
        tool = WebSearchBaseTool()
        assert "search" in tool.description.lower()
        assert "web" in tool.description.lower()

    def test_parameters_list(self) -> None:
        """get_parameters returns correct parameters."""
        tool = WebSearchBaseTool()
        params = tool.parameters
        param_names = [p.name for p in params]

        assert "query" in param_names
        assert "num_results" in param_names
        assert "provider" in param_names
        assert "allowed_domains" in param_names
        assert "blocked_domains" in param_names

    def test_query_parameter_is_required(self) -> None:
        """query parameter is required."""
        tool = WebSearchBaseTool()
        query_param = next(p for p in tool.parameters if p.name == "query")
        assert query_param.required is True

    def test_num_results_parameter_is_optional(self) -> None:
        """num_results parameter is optional with default."""
        tool = WebSearchBaseTool()
        num_results_param = next(
            p for p in tool.parameters if p.name == "num_results"
        )
        assert num_results_param.required is False
        assert num_results_param.default == 10


class TestWebSearchBaseToolExecution:
    """Test WebSearchBaseTool execution."""

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(working_dir="/test/dir")

    @pytest.fixture
    def mock_provider(self) -> MagicMock:
        """Create mock search provider."""
        provider = MagicMock()
        provider.search = AsyncMock(
            return_value=SearchResponse(
                query="test query",
                results=[
                    SearchResult(
                        title="Result 1",
                        url="https://example.com/1",
                        snippet="Snippet 1",
                    ),
                    SearchResult(
                        title="Result 2",
                        url="https://example.com/2",
                        snippet="Snippet 2",
                    ),
                ],
                provider="duckduckgo",
                total_results=2,
                search_time=0.5,
            )
        )
        provider.filter_results = MagicMock(
            side_effect=lambda r, a, b: r  # Pass through
        )
        return provider

    @pytest.mark.asyncio
    async def test_basic_search(
        self, mock_context: ExecutionContext, mock_provider: MagicMock
    ) -> None:
        """Performs basic search with query."""
        tool = WebSearchBaseTool(providers={"duckduckgo": mock_provider})

        result = await tool._execute(mock_context, query="test query")

        assert result.success
        assert result.metadata["query"] == "test query"
        assert result.metadata["result_count"] == 2
        mock_provider.search.assert_called_once_with("test query", 10)

    @pytest.mark.asyncio
    async def test_search_with_num_results(
        self, mock_context: ExecutionContext, mock_provider: MagicMock
    ) -> None:
        """Respects num_results parameter."""
        tool = WebSearchBaseTool(providers={"duckduckgo": mock_provider})

        await tool._execute(mock_context, query="test", num_results=5)

        mock_provider.search.assert_called_once_with("test", 5)

    @pytest.mark.asyncio
    async def test_search_unknown_provider(
        self, mock_context: ExecutionContext, mock_provider: MagicMock
    ) -> None:
        """Returns error for unknown provider."""
        tool = WebSearchBaseTool(providers={"duckduckgo": mock_provider})

        result = await tool._execute(
            mock_context, query="test", provider="unknown"
        )

        assert not result.success
        assert "Unknown search provider" in result.error
        assert "unknown" in result.error

    @pytest.mark.asyncio
    async def test_search_no_results(
        self, mock_context: ExecutionContext, mock_provider: MagicMock
    ) -> None:
        """Handles no results gracefully."""
        mock_provider.search = AsyncMock(
            return_value=SearchResponse(
                query="test",
                results=[],
                provider="duckduckgo",
                total_results=0,
                search_time=0.5,
            )
        )
        tool = WebSearchBaseTool(providers={"duckduckgo": mock_provider})

        result = await tool._execute(mock_context, query="xyznonexistent")

        assert result.success
        assert "No results found" in result.output
        assert result.metadata["result_count"] == 0

    @pytest.mark.asyncio
    async def test_search_error_handling(
        self, mock_context: ExecutionContext, mock_provider: MagicMock
    ) -> None:
        """Handles SearchError gracefully."""
        mock_provider.search = AsyncMock(
            side_effect=SearchError("Network error")
        )
        tool = WebSearchBaseTool(providers={"duckduckgo": mock_provider})

        result = await tool._execute(mock_context, query="test")

        assert not result.success
        assert "Search error" in result.error

    @pytest.mark.asyncio
    async def test_domain_filtering_called(
        self, mock_context: ExecutionContext, mock_provider: MagicMock
    ) -> None:
        """Domain filtering is applied."""
        tool = WebSearchBaseTool(providers={"duckduckgo": mock_provider})

        await tool._execute(
            mock_context,
            query="test",
            allowed_domains=["example.com"],
            blocked_domains=["spam.com"],
        )

        mock_provider.filter_results.assert_called_once()
        call_args = mock_provider.filter_results.call_args
        assert call_args[0][1] == ["example.com"]  # allowed
        assert call_args[0][2] == ["spam.com"]  # blocked


class TestWebSearchBaseToolValidation:
    """Test WebSearchBaseTool parameter validation."""

    def test_validate_missing_query(self) -> None:
        """Validation fails for missing query."""
        tool = WebSearchBaseTool()
        valid, error = tool.validate_params()
        assert not valid
        assert "query" in error

    def test_validate_complete_params(self) -> None:
        """Validation passes for complete params."""
        tool = WebSearchBaseTool()
        valid, error = tool.validate_params(query="test search")
        assert valid
        assert error is None

    def test_validate_num_results_range(self) -> None:
        """Validation respects num_results range."""
        tool = WebSearchBaseTool()

        # Below minimum
        valid, error = tool.validate_params(query="test", num_results=0)
        assert not valid

        # Above maximum
        valid, error = tool.validate_params(query="test", num_results=100)
        assert not valid

        # Valid range
        valid, error = tool.validate_params(query="test", num_results=20)
        assert valid
