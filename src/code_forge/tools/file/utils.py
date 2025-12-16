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
    - Path traversal attacks (../)
    - Symlinks escaping allowed directory (always rejected for security)
    - Absolute path requirements

    Note: Symlinks are always rejected to prevent directory escape attacks.
    The resolved path is checked to ensure it stays within base_dir if specified.

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

    # Check for symlinks first (security: symlinks can escape directory restrictions)
    if Path(file_path).is_symlink():
        return False, "Symlinks not allowed for security reasons"

    # Resolve to canonical path (resolves .., symlinks, etc.)
    try:
        resolved = Path(file_path).resolve()
    except (OSError, RuntimeError) as e:
        return False, f"Invalid path: {e}"

    # Check for path traversal by comparing resolved vs original
    # If resolved path differs significantly, there may be traversal
    original_parts = Path(file_path).parts
    if ".." in original_parts:
        return False, "Path traversal not allowed (contains ..)"

    # Check base directory restriction
    if base_dir:
        base_resolved = Path(base_dir).resolve()
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
