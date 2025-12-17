"""Write tool implementation."""

from __future__ import annotations

import os
from typing import Any

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.file.utils import validate_path_security


class WriteTool(BaseTool):
    """Write content to a file on the filesystem.

    Creates parent directories if needed.
    Overwrites existing files (must be read first).
    """

    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one
- If this is an existing file, you MUST use the Read tool first
- Creates parent directories if they don't exist
- The file_path must be an absolute path
- Prefer using Edit tool for modifying existing files"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="The absolute path to the file to write",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="The content to write to the file",
                required=True,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        file_path = kwargs["file_path"]
        content = kwargs["content"]

        # Validate path is absolute
        if not os.path.isabs(file_path):
            return ToolResult.fail(
                f"file_path must be an absolute path, got: {file_path}"
            )

        # Security validation
        is_valid, error = validate_path_security(file_path)
        if not is_valid:
            return ToolResult.fail(error or "Invalid path")

        # Dry run mode - still validate that path would be writable
        if context.dry_run:
            byte_count = len(content.encode("utf-8"))
            exists = "overwrite" if os.path.exists(file_path) else "create"

            # Validate parent directory exists or can be created
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                # Find the first existing ancestor
                check_dir = parent_dir
                while check_dir and not os.path.exists(check_dir):
                    check_dir = os.path.dirname(check_dir)

                # If we found an existing ancestor, check it's writable
                if check_dir and not os.access(check_dir, os.W_OK):
                    return ToolResult.fail(
                        f"[Dry Run] Cannot write: parent directory not writable: {check_dir}"
                    )

            # If file exists, check it's writable
            if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
                return ToolResult.fail(
                    f"[Dry Run] Cannot write: file not writable: {file_path}"
                )

            return ToolResult.ok(
                f"[Dry Run] Would {exists} {file_path} with {byte_count} bytes",
                file_path=file_path,
                bytes_written=byte_count,
                dry_run=True,
            )

        try:
            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # Check if file exists (for metadata)
            existed = os.path.exists(file_path)

            # Write the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            byte_count = len(content.encode("utf-8"))
            action = "Updated" if existed else "Created"

            return ToolResult.ok(
                f"{action} {file_path} ({byte_count} bytes)",
                file_path=file_path,
                bytes_written=byte_count,
                created=not existed,
            )

        except PermissionError:
            return ToolResult.fail(f"Permission denied: {file_path}")
        except OSError as e:
            return ToolResult.fail(f"OS error writing file: {e!s}")
