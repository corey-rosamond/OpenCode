"""Visual presentation components for Code-Forge CLI.

This package provides visual enhancements including:
- Colored diff display for file edits
- Syntax-highlighted code suggestions
- File tree visualization
- Progress indicators
"""

from .diff import DiffPresenter, DiffStyle

__all__ = [
    "DiffPresenter",
    "DiffStyle",
]
