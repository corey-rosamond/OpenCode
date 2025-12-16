"""REPL (Read-Eval-Print Loop) for Code-Forge CLI.

This module implements the main interactive shell with input handling,
output rendering, and the core REPL loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from code_forge import __version__
from code_forge.cli.status import StatusBar
from code_forge.cli.themes import Theme, ThemeRegistry
from code_forge.core import get_logger

if TYPE_CHECKING:
    from code_forge.config import CodeForgeConfig

logger = get_logger("repl")


class CommandCompleter(Completer):
    """Provides tab completion for commands and their arguments."""

    def __init__(self) -> None:
        """Initialize completer with command data."""
        self._commands: list[str] = []
        self._model_aliases: dict[str, str] = {}
        self._load_completions()

    def _load_completions(self) -> None:
        """Load completion data from registries."""
        try:
            from code_forge.commands.registry import CommandRegistry
            from code_forge.llm.routing import MODEL_ALIASES

            registry = CommandRegistry.get_instance()
            self._commands = ["/" + name for name in registry.list_names()]
            self._model_aliases = MODEL_ALIASES
        except Exception:
            # Silently fail if registries aren't available yet
            pass

    def get_completions(
        self, document: Document, complete_event: Any
    ) -> Iterator[Completion]:
        """Get completions for the current input.

        Args:
            document: Current document state.
            complete_event: Completion event info.

        Yields:
            Completion objects for matching items.
        """
        text = document.text_before_cursor
        _ = document.get_word_before_cursor()  # Available for future use

        # Reload completions if empty (lazy load)
        if not self._commands:
            self._load_completions()

        # Complete commands
        if text.startswith("/") and " " not in text:
            for cmd in self._commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))

        # Complete model names for /model command
        elif text.startswith("/model "):
            prefix = text[7:]  # After "/model "
            # Complete aliases
            for alias in sorted(self._model_aliases.keys()):
                if alias.startswith(prefix):
                    yield Completion(alias, start_position=-len(prefix))
            # Complete full model IDs
            for full_id in sorted(set(self._model_aliases.values())):
                if full_id.startswith(prefix):
                    yield Completion(full_id, start_position=-len(prefix))


class InputHandler:
    """Handles user input with history and key bindings.

    Provides async input capture using prompt_toolkit with
    persistent history and customizable key bindings.
    """

    def __init__(
        self,
        history_path: Path,
        style: Style | None = None,
        vim_mode: bool = False,
        completer: Completer | None = None,
        on_thinking_toggle: Callable[[], None] | None = None,
    ) -> None:
        """Initialize input handler.

        Args:
            history_path: Path to history file.
            style: prompt_toolkit style.
            vim_mode: Enable vim key bindings.
            completer: Tab completion provider.
            on_thinking_toggle: Callback for thinking mode toggle.
        """
        self._history_path = history_path
        self._ensure_history_dir()
        self._history = FileHistory(str(history_path))
        self._on_thinking_toggle = on_thinking_toggle
        self._bindings = self._create_bindings()
        self._style = style
        self._vim_mode = vim_mode
        self._completer = completer
        self._session: PromptSession[str] | None = None

    def _ensure_history_dir(self) -> None:
        """Ensure history directory exists."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_bindings(self) -> KeyBindings:
        """Create key bindings."""
        kb = KeyBindings()

        @kb.add("escape")
        def handle_escape(event: Any) -> None:
            """Clear current input."""
            event.current_buffer.reset()

        @kb.add("c-l")
        def handle_clear(event: Any) -> None:
            """Clear screen."""
            event.app.renderer.clear()

        # Shift+Tab toggles thinking mode
        @kb.add("s-tab")
        def handle_thinking_toggle(event: Any) -> None:
            """Toggle extended thinking mode."""
            if self._on_thinking_toggle:
                self._on_thinking_toggle()
                # Force toolbar refresh
                event.app.invalidate()

        return kb

    def _get_session(self) -> PromptSession[str]:
        """Get or create prompt session.

        Returns:
            Configured PromptSession.
        """
        if self._session is None:
            self._session = PromptSession(
                history=self._history,
                key_bindings=self._bindings,
                enable_history_search=True,
                style=self._style,
                vi_mode=self._vim_mode,
                completer=self._completer,
                complete_while_typing=False,  # Only complete on Tab
            )
        return self._session

    async def get_input(
        self,
        prompt: str,
        multiline: bool = False,
        bottom_toolbar: Callable[[], str] | str | None = None,
    ) -> str | None:
        """Get input from user.

        Args:
            prompt: Prompt string to display.
            multiline: Enable multiline input.
            bottom_toolbar: Status bar content.

        Returns:
            User input string, or None on EOF (Ctrl+D).

        Raises:
            KeyboardInterrupt: On Ctrl+C.
        """
        try:
            session = self._get_session()
            return await session.prompt_async(
                prompt,
                multiline=multiline,
                bottom_toolbar=bottom_toolbar,
            )
        except EOFError:
            return None


class OutputRenderer:
    """Renders output to the terminal.

    Provides methods for printing various content types
    with consistent styling using Rich.
    """

    def __init__(self, console: Console, theme: Theme) -> None:
        """Initialize output renderer.

        Args:
            console: Rich console instance.
            theme: Color theme to use.
        """
        self._console = console
        self._theme = theme

    @property
    def console(self) -> Console:
        """Get the Rich console instance."""
        return self._console

    def print(self, content: str, style: str | None = None) -> None:
        """Print content to console.

        Args:
            content: Text to print.
            style: Optional Rich style string.
        """
        self._console.print(content, style=style)

    def print_markdown(self, content: str) -> None:
        """Print markdown content.

        Args:
            content: Markdown text to render.
        """
        self._console.print(Markdown(content))

    def print_code(
        self,
        code: str,
        language: str = "python",
        line_numbers: bool = True,
    ) -> None:
        """Print syntax-highlighted code.

        Args:
            code: Source code to display.
            language: Programming language for highlighting.
            line_numbers: Show line numbers.
        """
        syntax = Syntax(code, language, theme="monokai", line_numbers=line_numbers)
        self._console.print(syntax)

    def print_panel(self, content: str, title: str = "") -> None:
        """Print content in a panel.

        Args:
            content: Panel content.
            title: Panel title.
        """
        self._console.print(Panel(content, title=title))

    def print_error(self, message: str) -> None:
        """Print error message.

        Args:
            message: Error message.
        """
        self._console.print(f"[{self._theme.error}]Error:[/{self._theme.error}] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message.

        Args:
            message: Warning message.
        """
        self._console.print(f"[{self._theme.warning}]Warning:[/{self._theme.warning}] {message}")

    def print_success(self, message: str) -> None:
        """Print success message.

        Args:
            message: Success message.
        """
        self._console.print(f"[{self._theme.success}]{message}[/{self._theme.success}]")

    def print_dim(self, message: str) -> None:
        """Print dimmed/secondary message.

        Args:
            message: Message text.
        """
        self._console.print(f"[{self._theme.dim}]{message}[/{self._theme.dim}]")

    def clear(self) -> None:
        """Clear the screen."""
        self._console.clear()


# Type alias for input callbacks
InputCallback = Callable[[str], Awaitable[None] | None]


class CodeForgeREPL:
    """Main REPL application.

    Orchestrates input handling, output rendering, and the
    main read-eval-print loop.
    """

    def __init__(self, config: CodeForgeConfig) -> None:
        """Initialize REPL.

        Args:
            config: Application configuration.
        """
        self._config = config
        self._theme = ThemeRegistry.get(config.display.theme)
        self._console = Console(force_terminal=True)
        self._status = StatusBar(
            model=config.model.default,
            visible=config.display.status_line,
        )

        # Create prompt_toolkit style from theme
        pt_style = Style.from_dict(self._theme.to_prompt_toolkit_style())

        # Create completer for tab completion
        completer = CommandCompleter()

        self._input = InputHandler(
            history_path=self._get_history_path(),
            style=pt_style,
            vim_mode=config.display.vim_mode,
            completer=completer,
            on_thinking_toggle=self._toggle_thinking,
        )
        self._output = OutputRenderer(self._console, self._theme)
        self._running = False
        self._callbacks: list[InputCallback] = []

    def _get_history_path(self) -> Path:
        """Get path for command history file.

        Returns:
            Path to history file.
        """
        return Path.home() / ".forge" / "history"

    def _get_prompt(self) -> str:
        """Generate prompt string.

        Returns:
            Prompt string to display.
        """
        return "> "

    def _get_toolbar(self) -> str:
        """Get status bar content for bottom toolbar.

        Returns two lines: input hints and status bar.

        Returns:
            Formatted toolbar string.
        """
        hints = self._status.format_input_hints()
        status = self._status.format_for_prompt_toolkit()
        # Combine hints and status into two-line toolbar
        return f"{hints}\n{status}"

    def _toggle_thinking(self) -> None:
        """Toggle extended thinking mode."""
        new_state = self._status.toggle_thinking()
        state_text = "enabled" if new_state else "disabled"
        # No output here - the toolbar will update automatically

    def _show_welcome(self) -> None:
        """Display welcome message."""
        cwd = Path.cwd()
        welcome = f"""
[bold {self._theme.accent}]Code-Forge[/bold {self._theme.accent}] v{__version__}
AI-powered CLI Development Assistant

[{self._theme.dim}]Directory:[/{self._theme.dim}] {cwd}
[{self._theme.dim}]Type /help for commands, ? for shortcuts[/{self._theme.dim}]
"""
        self._output.print(welcome.strip())
        self._output.print("")

    def _show_shortcuts(self) -> None:
        """Display keyboard shortcuts."""
        shortcuts = f"""
[bold]Keyboard Shortcuts[/bold]

[{self._theme.accent}]Tab[/{self._theme.accent}]        Autocomplete commands
[{self._theme.accent}]Shift+Tab[/{self._theme.accent}]  Toggle extended thinking
[{self._theme.accent}]Esc[/{self._theme.accent}]        Cancel current input
[{self._theme.accent}]Ctrl+C[/{self._theme.accent}]     Interrupt operation
[{self._theme.accent}]Ctrl+D[/{self._theme.accent}]     Exit (on empty input)
[{self._theme.accent}]Ctrl+L[/{self._theme.accent}]     Clear screen
[{self._theme.accent}]Ctrl+R[/{self._theme.accent}]     Search history
[{self._theme.accent}]Up/Down[/{self._theme.accent}]    Navigate history

[bold]Quick Prefixes[/bold]

[{self._theme.accent}]/[/{self._theme.accent}]  Slash command (e.g., /help, /model)
[{self._theme.accent}]?[/{self._theme.accent}]  Show this help
"""
        self._output.print(shortcuts.strip())

    @property
    def status_bar(self) -> StatusBar:
        """Get the status bar instance.

        Returns:
            StatusBar instance.
        """
        return self._status

    @property
    def thinking_enabled(self) -> bool:
        """Check if extended thinking is enabled.

        Returns:
            True if thinking mode is on.
        """
        return self._status.thinking_enabled

    @property
    def output(self) -> OutputRenderer:
        """Get the output renderer.

        Returns:
            OutputRenderer instance.
        """
        return self._output

    @property
    def is_running(self) -> bool:
        """Check if REPL is running.

        Returns:
            True if REPL loop is active.
        """
        return self._running

    def on_input(self, callback: InputCallback) -> None:
        """Register callback for input processing.

        Callbacks are called in order of registration.
        Callbacks can be sync or async functions.

        Args:
            callback: Function to call with user input.
        """
        self._callbacks.append(callback)

    async def _process_input(self, text: str) -> None:
        """Process user input through callbacks.

        Args:
            text: User input text.
        """
        if not self._callbacks:
            # Default behavior: echo
            self._output.print_dim(f"Received: {text}")
            return

        for callback in self._callbacks:
            result = callback(text)
            if asyncio.iscoroutine(result):
                await result

    async def run(self) -> int:
        """Run the REPL loop.

        Returns:
            Exit code (0 for normal exit).
        """
        self._running = True
        self._show_welcome()

        while self._running:
            try:
                # Get input with status bar
                user_input = await self._input.get_input(
                    self._get_prompt(),
                    bottom_toolbar=self._get_toolbar,
                )

                if user_input is None:  # Ctrl+D / EOF
                    self._output.print_dim("\nGoodbye!")
                    break

                text = user_input.strip()
                if not text:
                    continue

                # Validate UTF-8 encoding (defense against binary/malformed input)
                try:
                    # Ensure text is valid UTF-8 by encoding and decoding
                    text.encode('utf-8').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError) as e:
                    self._output.print_error(
                        f"Invalid character encoding in input: {e}"
                    )
                    continue

                # Check for shortcuts help
                if text == "?":
                    self._show_shortcuts()
                    continue

                # Process input
                await self._process_input(text)

            except KeyboardInterrupt:
                self._output.print_dim("\nInterrupted")
                continue
            except Exception as e:
                logger.exception("REPL error")
                self._output.print_error(str(e))

        self._running = False
        return 0

    def stop(self) -> None:
        """Stop the REPL loop."""
        self._running = False
