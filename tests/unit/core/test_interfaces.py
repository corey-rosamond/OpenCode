"""Tests for interface definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator

import pytest

from code_forge.core.interfaces import (
    IConfigLoader,
    IModelProvider,
    ISessionRepository,
    ITool,
)
from code_forge.core.types import (
    CompletionRequest,
    CompletionResponse,
    Session,
    SessionId,
    SessionSummary,
    ToolParameter,
    ToolResult,
)


class TestIToolInterface:
    """Tests for ITool abstract base class."""

    def test_itool_cannot_be_instantiated(self) -> None:
        """ITool should not be directly instantiable."""
        with pytest.raises(TypeError) as exc_info:
            ITool()  # type: ignore[abstract]
        assert "abstract" in str(exc_info.value).lower()

    def test_itool_concrete_implementation(self) -> None:
        """A concrete implementation of ITool should work."""

        class MockTool(ITool):
            @property
            def name(self) -> str:
                return "mock_tool"

            @property
            def description(self) -> str:
                return "A mock tool for testing"

            @property
            def parameters(self) -> list[ToolParameter]:
                return [
                    ToolParameter(
                        name="input",
                        type="string",
                        description="Input value",
                        required=True,
                    )
                ]

            async def execute(self, **kwargs: Any) -> ToolResult:
                return ToolResult(success=True, output=kwargs.get("input"))

        tool = MockTool()
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert len(tool.parameters) == 1

    def test_itool_validate_params_missing_required(self) -> None:
        """validate_params should detect missing required parameters."""

        class MockTool(ITool):
            @property
            def name(self) -> str:
                return "mock"

            @property
            def description(self) -> str:
                return "mock"

            @property
            def parameters(self) -> list[ToolParameter]:
                return [
                    ToolParameter(
                        name="required_param",
                        type="string",
                        description="Required",
                        required=True,
                    )
                ]

            async def execute(self, **kwargs: Any) -> ToolResult:
                return ToolResult(success=True, output=None)

        tool = MockTool()
        is_valid, error = tool.validate_params()
        assert is_valid is False
        assert isinstance(error, str)
        assert "required_param" in error

    def test_itool_validate_params_all_provided(self) -> None:
        """validate_params should pass when all required params provided."""

        class MockTool(ITool):
            @property
            def name(self) -> str:
                return "mock"

            @property
            def description(self) -> str:
                return "mock"

            @property
            def parameters(self) -> list[ToolParameter]:
                return [
                    ToolParameter(
                        name="param1",
                        type="string",
                        description="Required",
                        required=True,
                    )
                ]

            async def execute(self, **kwargs: Any) -> ToolResult:
                return ToolResult(success=True, output=None)

        tool = MockTool()
        is_valid, error = tool.validate_params(param1="value")
        assert is_valid is True
        assert error is None


class TestIModelProviderInterface:
    """Tests for IModelProvider abstract base class."""

    def test_imodelprovider_cannot_be_instantiated(self) -> None:
        """IModelProvider should not be directly instantiable."""
        with pytest.raises(TypeError) as exc_info:
            IModelProvider()  # type: ignore[abstract]
        assert "abstract" in str(exc_info.value).lower()

    def test_imodelprovider_concrete_implementation(self) -> None:
        """A concrete implementation of IModelProvider should work."""

        class MockProvider(IModelProvider):
            @property
            def name(self) -> str:
                return "mock_provider"

            @property
            def supports_tools(self) -> bool:
                return True

            async def complete(
                self, request: CompletionRequest
            ) -> CompletionResponse:
                return CompletionResponse(
                    content="response",
                    model=request.model,
                    finish_reason="stop",
                    usage={"prompt_tokens": 0, "completion_tokens": 0},
                )

            def stream(
                self, request: CompletionRequest
            ) -> AsyncIterator[str]:
                async def _stream() -> AsyncIterator[str]:
                    yield "token"

                return _stream()

            async def list_models(self) -> list[str]:
                return ["model-1", "model-2"]

        provider = MockProvider()
        assert provider.name == "mock_provider"
        assert provider.supports_tools is True


class TestIConfigLoaderInterface:
    """Tests for IConfigLoader abstract base class."""

    def test_iconfigloader_cannot_be_instantiated(self) -> None:
        """IConfigLoader should not be directly instantiable."""
        with pytest.raises(TypeError) as exc_info:
            IConfigLoader()  # type: ignore[abstract]
        assert "abstract" in str(exc_info.value).lower()

    def test_iconfigloader_concrete_implementation(self) -> None:
        """A concrete implementation of IConfigLoader should work."""

        class MockConfigLoader(IConfigLoader):
            def load(self, path: Path) -> dict[str, Any]:
                return {"key": "value"}

            def merge(
                self, base: dict[str, Any], override: dict[str, Any]
            ) -> dict[str, Any]:
                result = base.copy()
                result.update(override)
                return result

            def validate(
                self, config: dict[str, Any]
            ) -> tuple[bool, list[str]]:
                return True, []

        loader = MockConfigLoader()
        config = loader.load(Path("/test"))
        assert config == {"key": "value"}

        merged = loader.merge({"a": 1}, {"b": 2})
        assert merged == {"a": 1, "b": 2}

        is_valid, errors = loader.validate({})
        assert is_valid is True
        assert errors == []


class TestISessionRepositoryInterface:
    """Tests for ISessionRepository abstract base class."""

    def test_isessionrepository_cannot_be_instantiated(self) -> None:
        """ISessionRepository should not be directly instantiable."""
        with pytest.raises(TypeError) as exc_info:
            ISessionRepository()  # type: ignore[abstract]
        assert "abstract" in str(exc_info.value).lower()

    def test_isessionrepository_concrete_implementation(self) -> None:
        """A concrete implementation of ISessionRepository should work."""
        from datetime import datetime

        class MockSessionRepository(ISessionRepository):
            def __init__(self) -> None:
                self._sessions: dict[str, Session] = {}

            async def save(self, session: Session) -> None:
                self._sessions[session.id.value] = session

            async def load(self, session_id: SessionId) -> Session | None:
                return self._sessions.get(session_id.value)

            async def list_recent(
                self, limit: int = 10
            ) -> list[SessionSummary]:
                return []

            async def delete(self, session_id: SessionId) -> bool:
                if session_id.value in self._sessions:
                    del self._sessions[session_id.value]
                    return True
                return False

        repo = MockSessionRepository()
        # Just verify it can be instantiated
        assert isinstance(repo, ISessionRepository)
