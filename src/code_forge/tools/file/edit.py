"""Edit tool implementation."""

from __future__ import annotations

import logging
import os
from typing import Any

import chardet

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.file.utils import validate_path_security

logger = logging.getLogger(__name__)


def detect_file_encoding(file_path: str) -> tuple[str, float]:
    """Detect the encoding of a file.

    Args:
        file_path: Path to the file to detect encoding for.

    Returns:
        Tuple of (encoding, confidence) where encoding is the detected
        encoding name and confidence is a float between 0 and 1.
        Falls back to UTF-8 if detection fails.
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()

        if not raw_data:
            # Empty file, default to UTF-8
            return "utf-8", 1.0

        # Check for BOM markers first (chardet sometimes misses these)
        if raw_data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig", 1.0
        if raw_data.startswith(b"\xff\xfe"):
            return "utf-16-le", 1.0
        if raw_data.startswith(b"\xfe\xff"):
            return "utf-16-be", 1.0

        # Use chardet for detection
        result = chardet.detect(raw_data)
        encoding = result.get("encoding")
        confidence = result.get("confidence", 0.0)

        if encoding:
            # Normalize encoding name
            encoding = encoding.lower()
            # Map some common chardet names to Python codec names
            encoding_map = {
                "ascii": "utf-8",  # ASCII is subset of UTF-8
                "iso-8859-1": "latin-1",
                "windows-1252": "cp1252",
            }
            encoding = encoding_map.get(encoding, encoding)
            return encoding, confidence

        # Fallback to UTF-8
        return "utf-8", 0.0

    except OSError:
        # Can't read file, fall back to UTF-8
        return "utf-8", 0.0


class EditTool(BaseTool):
    """Edit a file by performing exact string replacements.

    The old_string must be found exactly in the file.
    Without replace_all, the old_string must be unique.
    """

    @property
    def name(self) -> str:
        return "Edit"

    @property
    def description(self) -> str:
        return """Performs exact string replacements in files.

Usage:
- You must use the Read tool first before editing
- The edit will FAIL if old_string is not found in the file
- The edit will FAIL if old_string appears multiple times (without replace_all)
- Use replace_all=true to replace all occurrences
- Preserves file encoding and line endings
- new_string must be different from old_string"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="The absolute path to the file to modify",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="old_string",
                type="string",
                description="The text to replace (must be found exactly)",
                required=True,
            ),
            ToolParameter(
                name="new_string",
                type="string",
                description="The text to replace it with (must differ from old_string)",
                required=True,
            ),
            ToolParameter(
                name="replace_all",
                type="boolean",
                description="Replace all occurrences (default: false)",
                required=False,
                default=False,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        file_path = kwargs["file_path"]
        old_string = kwargs["old_string"]
        new_string = kwargs["new_string"]
        replace_all = kwargs.get("replace_all", False)

        # Validate path is absolute
        if not os.path.isabs(file_path):
            return ToolResult.fail(
                f"file_path must be an absolute path, got: {file_path}"
            )

        # Security validation
        is_valid, error = validate_path_security(file_path)
        if not is_valid:
            return ToolResult.fail(error or "Invalid path")

        # Check file exists
        if not os.path.exists(file_path):
            return ToolResult.fail(f"File not found: {file_path}")

        # Check old != new
        if old_string == new_string:
            return ToolResult.fail(
                "new_string must be different from old_string"
            )

        return self._perform_replacement(
            file_path, old_string, new_string, replace_all, context
        )

    def _perform_replacement(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool,
        context: ExecutionContext,  # noqa: ARG002
    ) -> ToolResult:
        """Perform the actual replacement operation."""
        try:
            # Detect file encoding to preserve it
            encoding, confidence = detect_file_encoding(file_path)
            logger.debug(
                "Detected encoding %s (confidence: %.2f) for %s",
                encoding, confidence, file_path
            )

            # Read with detected encoding
            with open(file_path, encoding=encoding) as f:
                content = f.read()

            count = content.count(old_string)

            if count == 0:
                return ToolResult.fail(
                    f"old_string not found in {file_path}. "
                    "Make sure you've read the file first and the string "
                    "matches exactly (including whitespace and indentation)."
                )

            if count > 1 and not replace_all:
                lines_with_match = [
                    i for i, line in enumerate(content.splitlines(), 1)
                    if old_string in line
                ]
                return ToolResult.fail(
                    f"old_string found {count} times (lines: {lines_with_match}). "
                    "Either:\n"
                    "1. Provide more surrounding context to make it unique\n"
                    "2. Use replace_all=true to replace all occurrences"
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back with same encoding
            with open(file_path, "w", encoding=encoding) as f:
                f.write(new_content)

            return ToolResult.ok(
                f"Replaced {replacements} occurrence(s) in {file_path}",
                file_path=file_path,
                replacements=replacements,
                encoding=encoding,
            )

        except PermissionError:
            return ToolResult.fail(f"Permission denied: {file_path}")
        except UnicodeDecodeError:
            return ToolResult.fail(
                f"Cannot read file as text: {file_path}. It may be a binary file."
            )
