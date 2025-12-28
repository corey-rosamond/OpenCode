"""Unit tests for WebFetchBaseTool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from code_forge.tools.base import ExecutionContext, ToolCategory
from code_forge.tools.web.fetch import WebFetchBaseTool
from code_forge.web.fetch import FetchError
from code_forge.web.types import FetchResponse


class TestWebFetchBaseToolProperties:
    """Test WebFetchBaseTool property methods."""

    def test_name_property(self) -> None:
        """WebFetchBaseTool.name returns 'WebFetch'."""
        tool = WebFetchBaseTool()
        assert tool.name == "WebFetch"

    def test_category_property(self) -> None:
        """WebFetchBaseTool.category returns ToolCategory.WEB."""
        tool = WebFetchBaseTool()
        assert tool.category == ToolCategory.WEB

    def test_description_property(self) -> None:
        """WebFetchBaseTool.description is informative."""
        tool = WebFetchBaseTool()
        assert "fetch" in tool.description.lower()
        assert "url" in tool.description.lower()

    def test_parameters_list(self) -> None:
        """get_parameters returns correct parameters."""
        tool = WebFetchBaseTool()
        params = tool.parameters
        param_names = [p.name for p in params]

        assert "url" in param_names
        assert "format" in param_names
        assert "use_cache" in param_names
        assert "timeout" in param_names

    def test_url_parameter_is_required(self) -> None:
        """url parameter is required."""
        tool = WebFetchBaseTool()
        url_param = next(p for p in tool.parameters if p.name == "url")
        assert url_param.required is True

    def test_format_parameter_is_optional(self) -> None:
        """format parameter is optional with default."""
        tool = WebFetchBaseTool()
        format_param = next(p for p in tool.parameters if p.name == "format")
        assert format_param.required is False
        assert format_param.default == "markdown"
        assert format_param.enum == ["markdown", "text", "raw"]


class TestWebFetchBaseToolExecution:
    """Test WebFetchBaseTool execution."""

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(working_dir="/test/dir")

    @pytest.fixture
    def mock_fetcher(self) -> MagicMock:
        """Create mock URL fetcher."""
        fetcher = MagicMock()
        fetcher.fetch = AsyncMock(
            return_value=FetchResponse(
                url="https://example.com",
                final_url="https://example.com",
                status_code=200,
                content_type="text/html",
                content="<html><body><h1>Hello</h1><p>World</p></body></html>",
                headers={},
                encoding="utf-8",
                fetch_time=0.5,
            )
        )
        return fetcher

    @pytest.fixture
    def mock_parser(self) -> MagicMock:
        """Create mock HTML parser."""
        parser = MagicMock()
        parser.to_markdown = MagicMock(return_value="# Hello\n\nWorld")
        parser.to_text = MagicMock(return_value="Hello\nWorld")
        return parser

    @pytest.mark.asyncio
    async def test_fetch_as_markdown(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Fetches and converts to markdown."""
        tool = WebFetchBaseTool(fetcher=mock_fetcher, parser=mock_parser)

        result = await tool._execute(
            mock_context, url="https://example.com", format="markdown"
        )

        assert result.success
        assert "Hello" in result.output
        mock_parser.to_markdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_as_text(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Fetches and converts to plain text."""
        tool = WebFetchBaseTool(fetcher=mock_fetcher, parser=mock_parser)

        result = await tool._execute(
            mock_context, url="https://example.com", format="text"
        )

        assert result.success
        mock_parser.to_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_as_raw(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Fetches raw HTML."""
        tool = WebFetchBaseTool(fetcher=mock_fetcher, parser=mock_parser)

        result = await tool._execute(
            mock_context, url="https://example.com", format="raw"
        )

        assert result.success
        assert "<html>" in result.output
        mock_parser.to_markdown.assert_not_called()
        mock_parser.to_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_error_handling(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Handles FetchError gracefully."""
        mock_fetcher.fetch = AsyncMock(
            side_effect=FetchError("Connection refused")
        )
        tool = WebFetchBaseTool(fetcher=mock_fetcher, parser=mock_parser)

        result = await tool._execute(mock_context, url="https://bad-url.com")

        assert not result.success
        assert "Fetch error" in result.error

    @pytest.mark.asyncio
    async def test_fetch_with_cache(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Uses cache when enabled and available."""
        mock_cache = MagicMock()
        mock_cache.generate_key = MagicMock(return_value="cache_key")
        cached_response = FetchResponse(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content="<html>Cached</html>",
            headers={},
            encoding="utf-8",
            fetch_time=0.0,
            from_cache=True,
        )
        mock_cache.get = MagicMock(return_value=cached_response)

        tool = WebFetchBaseTool(
            fetcher=mock_fetcher, parser=mock_parser, cache=mock_cache
        )

        result = await tool._execute(
            mock_context, url="https://example.com", use_cache=True
        )

        assert result.success
        assert result.metadata.get("from_cache") is True
        mock_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_bypasses_cache(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Bypasses cache when disabled."""
        mock_cache = MagicMock()

        tool = WebFetchBaseTool(
            fetcher=mock_fetcher, parser=mock_parser, cache=mock_cache
        )

        result = await tool._execute(
            mock_context, url="https://example.com", use_cache=False
        )

        assert result.success
        mock_cache.get.assert_not_called()
        mock_fetcher.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_with_timeout(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Applies timeout to request."""
        tool = WebFetchBaseTool(fetcher=mock_fetcher, parser=mock_parser)

        await tool._execute(
            mock_context, url="https://example.com", timeout=60
        )

        call_args = mock_fetcher.fetch.call_args
        options = call_args[0][1]  # Second positional arg is options
        assert options.timeout == 60

    @pytest.mark.asyncio
    async def test_adds_source_info(
        self,
        mock_context: ExecutionContext,
        mock_fetcher: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Adds source URL to output."""
        tool = WebFetchBaseTool(fetcher=mock_fetcher, parser=mock_parser)

        result = await tool._execute(mock_context, url="https://example.com")

        assert result.success
        assert "Source:" in result.output
        assert "example.com" in result.output


class TestWebFetchBaseToolValidation:
    """Test WebFetchBaseTool parameter validation."""

    def test_validate_missing_url(self) -> None:
        """Validation fails for missing url."""
        tool = WebFetchBaseTool()
        valid, error = tool.validate_params()
        assert not valid
        assert "url" in error

    def test_validate_complete_params(self) -> None:
        """Validation passes for complete params."""
        tool = WebFetchBaseTool()
        valid, error = tool.validate_params(url="https://example.com")
        assert valid
        assert error is None

    def test_validate_timeout_range(self) -> None:
        """Validation respects timeout range."""
        tool = WebFetchBaseTool()

        # Below minimum
        valid, error = tool.validate_params(
            url="https://example.com", timeout=2
        )
        assert not valid

        # Above maximum
        valid, error = tool.validate_params(
            url="https://example.com", timeout=200
        )
        assert not valid

        # Valid range
        valid, error = tool.validate_params(
            url="https://example.com", timeout=30
        )
        assert valid

    def test_validate_format_enum(self) -> None:
        """Validation respects format enum."""
        tool = WebFetchBaseTool()

        # Invalid format
        valid, error = tool.validate_params(
            url="https://example.com", format="invalid"
        )
        assert not valid

        # Valid formats
        for fmt in ["markdown", "text", "raw"]:
            valid, error = tool.validate_params(
                url="https://example.com", format=fmt
            )
            assert valid
