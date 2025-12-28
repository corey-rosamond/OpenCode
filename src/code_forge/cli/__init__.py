"""CLI package for Code-Forge.

This package provides the command-line interface including:
- REPL (Read-Eval-Print Loop) for interactive sessions
- Status bar for runtime information display
- Theme support for customizable appearance
- Dependency injection for testability
"""

from code_forge.cli.context_adapter import ContextStatusAdapter
from code_forge.cli.dependencies import Dependencies
from code_forge.cli.main import main
from code_forge.cli.repl import InputHandler, CodeForgeREPL, OutputRenderer
from code_forge.cli.status import ContextWarningLevel, StatusBar, StatusBarObserver
from code_forge.cli.themes import (
    DARK_THEME,
    LIGHT_THEME,
    Theme,
    ThemeRegistry,
)

__all__ = [
    "ContextStatusAdapter",
    "ContextWarningLevel",
    "DARK_THEME",
    "Dependencies",
    "LIGHT_THEME",
    "InputHandler",
    "CodeForgeREPL",
    "OutputRenderer",
    "StatusBar",
    "StatusBarObserver",
    "Theme",
    "ThemeRegistry",
    "main",
]
