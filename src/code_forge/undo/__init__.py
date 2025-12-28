"""Undo system for file operations.

This package provides undo/redo functionality for file modifications
made by Code-Forge tools (Edit, Write, Bash).

Example:
    from code_forge.undo import UndoManager, FileSnapshot

    # Create manager
    manager = UndoManager()

    # Before modifying a file
    manager.capture_before("/path/to/file.py")

    # After modification
    manager.commit("Edit", "Edit file.py", ["/path/to/file.py"])

    # Undo
    success, message = manager.undo()

    # Redo
    success, message = manager.redo()
"""

from code_forge.undo.bash_detector import BashFileDetector
from code_forge.undo.manager import UndoManager
from code_forge.undo.models import FileSnapshot, UndoEntry, UndoHistory

__all__ = [
    "BashFileDetector",
    "FileSnapshot",
    "UndoEntry",
    "UndoHistory",
    "UndoManager",
]
