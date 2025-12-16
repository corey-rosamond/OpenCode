"""Security utilities for file operations."""

from __future__ import annotations

import os
from pathlib import Path


def validate_path_security(
    file_path: str,
    base_dir: str | None = None,
) -> tuple[bool, str | None]:
    """Validate a file path for security issues.

    Checks for:
    - Absolute path requirement
    - Symlinks (rejected for security - can escape directory restrictions)
    - Path traversal via canonical path resolution and base_dir comparison

    Security Model:
    - The resolved (canonical) path is compared against the base directory
    - This handles all forms of path traversal including ../ and symlinks
    - Explicit symlink check provides defense-in-depth against obvious attacks

    Args:
        file_path: Path to validate.
        base_dir: Optional base directory to restrict access.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    # Must be absolute
    if not os.path.isabs(file_path):
        return False, f"Path must be absolute: {file_path}"

    path = Path(file_path)

    # Check for symlink at the specified path (defense-in-depth)
    # Note: This only catches symlinks at the final path component
    try:
        if path.is_symlink():
            return False, "Symlinks not allowed for security reasons"
    except OSError:
        pass  # Path doesn't exist yet, continue with other checks

    # Resolve to canonical path (handles .., symlinks in parent dirs, etc.)
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as e:
        return False, f"Invalid path: {e}"

    # Check base directory restriction - this is the primary security boundary
    # The resolved path must be within the base directory
    if base_dir:
        try:
            base_resolved = Path(base_dir).resolve()
        except (OSError, RuntimeError) as e:
            return False, f"Invalid base directory: {e}"

        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            return False, f"Path must be within {base_dir}"

    return True, None


def is_safe_filename(filename: str) -> bool:
    """Check if a filename is safe (no path separators).

    Args:
        filename: Filename to check.

    Returns:
        True if safe.
    """
    return os.path.sep not in filename and "/" not in filename and "\\" not in filename
