"""Tests for CLI REPL."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from code_forge.cli.repl import InputHandler, CodeForgeREPL, OutputRenderer
from code_forge.cli.status import StatusBar
from code_forge.cli.themes import DARK_THEME, ThemeRegistry
from code_forge.config import CodeForgeConfig

if TYPE_CHECKING:
    from collections.abc import Generator


class TestInputHandler:
    """Tests for InputHandler class."""

    @pytest.fixture
    def temp_history_path(self, tmp_path: Path) -> Path:
        """Create temporary history file path."""
        return tmp_path / ".forge" / "history"

    def test_init_creates_history_dir(self, temp_history_path: Path) -> None:
        """Test that init creates history directory."""
        InputHandler(temp_history_path)
        assert temp_history_path.parent.exists()

    def test_init_with_style(self, temp_history_path: Path) -> None:
        """Test init with custom style."""
        from prompt_toolkit.styles import Style

        style = Style.from_dict({"": "fg:white"})
        handler = InputHandler(temp_history_path, style=style)
        assert handler._style == style

    def test_init_with_vim_mode(self, temp_history_path: Path) -> None:
        """Test init with vim mode enabled."""
        handler = InputHandler(temp_history_path, vim_mode=True)
        assert handler._vim_mode is True

    def test_bindings_created(self, temp_history_path: Path) -> None:
        """Test that key bindings are created."""
        from prompt_toolkit.key_binding import KeyBindings

        handler = InputHandler(temp_history_path)
        bindings = handler._bindings
        assert isinstance(bindings, KeyBindings)

    @pytest.mark.asyncio
    async def test_get_input_returns_none_on_eof(self, temp_history_path: Path) -> None:
        """Test that get_input returns None on EOF."""
        handler = InputHandler(temp_history_path)

        with patch.object(handler, "_get_session") as mock_session:
            session = MagicMock()
            session.prompt_async = AsyncMock(side_effect=EOFError())
            mock_session.return_value = session

            result = await handler.get_input("> ")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_input_returns_text(self, temp_history_path: Path) -> None:
        """Test that get_input returns user input."""
        handler = InputHandler(temp_history_path)

        with patch.object(handler, "_get_session") as mock_session:
            session = MagicMock()
            session.prompt_async = AsyncMock(return_value="hello world")
            mock_session.return_value = session

            result = await handler.get_input("> ")
            assert result == "hello world"

    @pytest.mark.asyncio
    async def test_get_input_raises_keyboard_interrupt(
        self, temp_history_path: Path
    ) -> None:
        """Test that get_input propagates KeyboardInterrupt."""
        handler = InputHandler(temp_history_path)

        with patch.object(handler, "_get_session") as mock_session:
            session = MagicMock()
            session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt())
            mock_session.return_value = session

            with pytest.raises(KeyboardInterrupt):
                await handler.get_input("> ")

    def test_session_lazy_creation(self, temp_history_path: Path) -> None:
        """Test that session is created lazily."""
        from prompt_toolkit import PromptSession

        handler = InputHandler(temp_history_path)
        assert handler._session is None
        session = handler._get_session()
        assert isinstance(session, PromptSession)
        assert handler._session is session


class TestOutputRenderer:
    """Tests for OutputRenderer class."""

    @pytest.fixture
    def console(self) -> Console:
        """Create test console."""
        return Console(force_terminal=True, record=True, width=80)

    @pytest.fixture
    def renderer(self, console: Console) -> OutputRenderer:
        """Create test renderer."""
        return OutputRenderer(console, DARK_THEME)

    def test_console_property(self, renderer: OutputRenderer, console: Console) -> None:
        """Test console property returns console instance."""
        assert renderer.console is console

    def test_print(self, renderer: OutputRenderer) -> None:
        """Test basic print."""
        renderer.print("Hello, World!")
        output = renderer.console.export_text()
        assert "Hello, World!" in output

    def test_print_with_style(self, renderer: OutputRenderer) -> None:
        """Test print with style."""
        renderer.print("Styled text", style="bold")
        # Just verify no exception

    def test_print_markdown(self, renderer: OutputRenderer) -> None:
        """Test markdown printing."""
        renderer.print_markdown("# Heading\n\nParagraph text")
        output = renderer.console.export_text()
        assert "Heading" in output

    def test_print_code(self, renderer: OutputRenderer) -> None:
        """Test code printing."""
        renderer.print_code("print('hello')", language="python")
        output = renderer.console.export_text()
        assert "print" in output

    def test_print_code_no_line_numbers(self, renderer: OutputRenderer) -> None:
        """Test code printing without line numbers."""
        renderer.print_code("x = 1", language="python", line_numbers=False)
        # Just verify no exception

    def test_print_panel(self, renderer: OutputRenderer) -> None:
        """Test panel printing."""
        renderer.print_panel("Content", title="Title")
        output = renderer.console.export_text()
        assert "Content" in output

    def test_print_error(self, renderer: OutputRenderer) -> None:
        """Test error message printing."""
        renderer.print_error("Something went wrong")
        output = renderer.console.export_text()
        assert "Error" in output
        assert "Something went wrong" in output

    def test_print_warning(self, renderer: OutputRenderer) -> None:
        """Test warning message printing."""
        renderer.print_warning("Be careful")
        output = renderer.console.export_text()
        assert "Warning" in output
        assert "Be careful" in output

    def test_print_success(self, renderer: OutputRenderer) -> None:
        """Test success message printing."""
        renderer.print_success("Operation completed")
        output = renderer.console.export_text()
        assert "Operation completed" in output

    def test_print_dim(self, renderer: OutputRenderer) -> None:
        """Test dim message printing."""
        renderer.print_dim("Secondary info")
        output = renderer.console.export_text()
        assert "Secondary info" in output

    def test_clear(self, renderer: OutputRenderer) -> None:
        """Test screen clearing."""
        # Just verify no exception
        renderer.clear()


class TestCodeForgeREPL:
    """Tests for CodeForgeREPL class."""

    @pytest.fixture
    def config(self) -> CodeForgeConfig:
        """Create test configuration."""
        return CodeForgeConfig()

    @pytest.fixture
    def repl(self, config: CodeForgeConfig) -> Generator[CodeForgeREPL, None, None]:
        """Create test REPL instance."""
        with patch("code_forge.cli.repl.InputHandler._ensure_history_dir"):
            repl = CodeForgeREPL(config)
            yield repl

    def test_init(self, repl: CodeForgeREPL) -> None:
        """Test REPL initialization."""
        from code_forge.cli.themes import Theme

        assert isinstance(repl._config, CodeForgeConfig)
        assert isinstance(repl._theme, Theme)
        assert isinstance(repl._console, Console)
        assert isinstance(repl._status, StatusBar)
        assert isinstance(repl._input, InputHandler)
        assert isinstance(repl._output, OutputRenderer)
        assert repl._running is False

    def test_status_bar_property(self, repl: CodeForgeREPL) -> None:
        """Test status_bar property."""
        assert repl.status_bar is repl._status
        assert isinstance(repl.status_bar, StatusBar)

    def test_output_property(self, repl: CodeForgeREPL) -> None:
        """Test output property."""
        assert repl.output is repl._output
        assert isinstance(repl.output, OutputRenderer)

    def test_is_running_property(self, repl: CodeForgeREPL) -> None:
        """Test is_running property."""
        assert repl.is_running is False

    def test_stop(self, repl: CodeForgeREPL) -> None:
        """Test stopping the REPL."""
        repl._running = True
        repl.stop()
        assert repl._running is False

    def test_get_prompt(self, repl: CodeForgeREPL) -> None:
        """Test prompt generation."""
        prompt = repl._get_prompt()
        assert prompt == "> "

    def test_get_history_path(self, repl: CodeForgeREPL) -> None:
        """Test history path generation."""
        path = repl._get_history_path()
        assert isinstance(path, Path)
        assert "forge" in str(path)
        assert "history" in str(path)

    def test_on_input_registers_callback(self, repl: CodeForgeREPL) -> None:
        """Test registering input callback."""
        callback = MagicMock()
        repl.on_input(callback)
        assert callback in repl._callbacks

    def test_on_input_multiple_callbacks(self, repl: CodeForgeREPL) -> None:
        """Test registering multiple callbacks."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        repl.on_input(callback1)
        repl.on_input(callback2)
        assert len(repl._callbacks) == 2

    def test_theme_from_config(self, config: CodeForgeConfig) -> None:
        """Test that REPL uses theme from config."""
        config.display.theme = "light"
        with patch("code_forge.cli.repl.InputHandler._ensure_history_dir"):
            repl = CodeForgeREPL(config)
            assert repl._theme == ThemeRegistry.get("light")

    def test_status_bar_from_config(self, config: CodeForgeConfig) -> None:
        """Test that status bar uses config values."""
        config.model.default = "test-model"
        config.display.status_line = False
        with patch("code_forge.cli.repl.InputHandler._ensure_history_dir"):
            repl = CodeForgeREPL(config)
            assert repl._status.model == "test-model"
            assert repl._status.visible is False


class TestCodeForgeREPLAsync:
    """Async tests for CodeForgeREPL."""

    @pytest.fixture
    def config(self) -> CodeForgeConfig:
        """Create test configuration."""
        return CodeForgeConfig()

    @pytest.fixture
    def repl(self, config: CodeForgeConfig) -> Generator[CodeForgeREPL, None, None]:
        """Create test REPL instance."""
        with patch("code_forge.cli.repl.InputHandler._ensure_history_dir"):
            repl = CodeForgeREPL(config)
            yield repl

    @pytest.mark.asyncio
    async def test_process_input_no_callbacks(self, repl: CodeForgeREPL) -> None:
        """Test processing input with no callbacks echoes."""
        with patch.object(repl._output, "print_dim") as mock_print:
            await repl._process_input("test input")
            mock_print.assert_called_once()
            assert "test input" in str(mock_print.call_args)

    @pytest.mark.asyncio
    async def test_process_input_sync_callback(self, repl: CodeForgeREPL) -> None:
        """Test processing input with sync callback."""
        callback = MagicMock()
        repl.on_input(callback)
        await repl._process_input("test")
        callback.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_process_input_async_callback(self, repl: CodeForgeREPL) -> None:
        """Test processing input with async callback."""
        callback = AsyncMock()
        repl.on_input(callback)
        await repl._process_input("test")
        callback.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_process_input_multiple_callbacks(self, repl: CodeForgeREPL) -> None:
        """Test processing input calls all callbacks."""
        callback1 = MagicMock()
        callback2 = AsyncMock()
        repl.on_input(callback1)
        repl.on_input(callback2)
        await repl._process_input("test")
        callback1.assert_called_once_with("test")
        callback2.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_run_exits_on_eof(self, repl: CodeForgeREPL) -> None:
        """Test that REPL exits on EOF."""
        with patch.object(repl._input, "get_input", new=AsyncMock(return_value=None)):
            with patch.object(repl._output, "print"):
                with patch.object(repl._output, "print_dim"):
                    result = await repl.run()
                    assert result == 0
                    assert repl._running is False

    @pytest.mark.asyncio
    async def test_run_shows_welcome(self, repl: CodeForgeREPL) -> None:
        """Test that REPL shows welcome on start."""
        call_count = 0

        async def fake_input(*args: object, **kwargs: object) -> str | None:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return None
            return ""

        with patch.object(repl._input, "get_input", new=fake_input):
            with patch.object(repl, "_show_welcome") as mock_welcome:
                with patch.object(repl._output, "print_dim"):
                    await repl.run()
                    mock_welcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_shows_shortcuts_on_question_mark(
        self, repl: CodeForgeREPL
    ) -> None:
        """Test that ? shows shortcuts."""
        inputs = iter(["?", None])

        async def fake_input(*args: object, **kwargs: object) -> str | None:
            return next(inputs, None)

        with patch.object(repl._input, "get_input", new=fake_input):
            with patch.object(repl, "_show_shortcuts") as mock_shortcuts:
                with patch.object(repl._output, "print"):
                    with patch.object(repl._output, "print_dim"):
                        await repl.run()
                        mock_shortcuts.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_skips_empty_input(self, repl: CodeForgeREPL) -> None:
        """Test that empty input is skipped."""
        inputs = iter(["", "   ", "\n", None])

        async def fake_input(*args: object, **kwargs: object) -> str | None:
            return next(inputs, None)

        callback = MagicMock()
        repl.on_input(callback)

        with patch.object(repl._input, "get_input", new=fake_input):
            with patch.object(repl._output, "print"):
                with patch.object(repl._output, "print_dim"):
                    await repl.run()
                    callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_handles_keyboard_interrupt(self, repl: CodeForgeREPL) -> None:
        """Test that KeyboardInterrupt is handled gracefully."""
        call_count = 0

        async def fake_input(*args: object, **kwargs: object) -> str | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise KeyboardInterrupt()
            return None

        with patch.object(repl._input, "get_input", new=fake_input):
            with patch.object(repl._output, "print"):
                with patch.object(repl._output, "print_dim") as mock_dim:
                    result = await repl.run()
                    assert result == 0
                    # Should have printed interrupted message
                    assert any("Interrupt" in str(c) for c in mock_dim.call_args_list)

    @pytest.mark.asyncio
    async def test_run_handles_exception(self, repl: CodeForgeREPL) -> None:
        """Test that exceptions are handled and displayed."""
        call_count = 0

        async def fake_input(*args: object, **kwargs: object) -> str | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "test"
            return None

        def failing_callback(text: str) -> None:
            raise ValueError("Test error")

        repl.on_input(failing_callback)

        with patch.object(repl._input, "get_input", new=fake_input):
            with patch.object(repl._output, "print"):
                with patch.object(repl._output, "print_dim"):
                    with patch.object(repl._output, "print_error") as mock_error:
                        result = await repl.run()
                        assert result == 0
                        mock_error.assert_called_once()
                        assert "Test error" in str(mock_error.call_args)


class TestCodeForgeREPLIntegration:
    """Integration tests for CodeForgeREPL."""

    @pytest.fixture
    def config(self) -> CodeForgeConfig:
        """Create test configuration."""
        return CodeForgeConfig()

    def test_full_initialization(self, config: CodeForgeConfig) -> None:
        """Test that all components are properly initialized."""
        with patch("code_forge.cli.repl.InputHandler._ensure_history_dir"):
            repl = CodeForgeREPL(config)
            assert repl._theme == ThemeRegistry.get(config.display.theme)
            assert repl._status.model == config.model.default
            assert repl._status.visible == config.display.status_line
