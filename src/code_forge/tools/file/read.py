"""Read tool implementation."""

from __future__ import annotations

import base64
import json
import mimetypes
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


class ReadTool(BaseTool):
    """Read contents of a file from the filesystem.

    Supports text files, images (returns base64), PDFs (extracts text),
    and Jupyter notebooks (returns formatted cells).
    """

    MAX_LINE_LENGTH = 2000
    DEFAULT_LIMIT = 2000
    MAX_LIMIT = 10000
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB limit for images
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB limit for PDFs
    MAX_NOTEBOOK_SIZE = 20 * 1024 * 1024  # 20MB limit for notebooks

    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return """Reads a file from the local filesystem.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning
- You can optionally specify a line offset and limit for long files
- Lines longer than 2000 characters will be truncated
- Results are returned with line numbers starting at 1
- Can read images (PNG, JPG), PDFs, and Jupyter notebooks (.ipynb)
- This tool can only read files, not directories"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="The absolute path to the file to read",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="offset",
                type="integer",
                description="The line number to start reading from (1-indexed). "
                "Only provide if the file is too large to read at once.",
                required=False,
                minimum=1,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="The number of lines to read. "
                "Only provide if the file is too large to read at once.",
                required=False,
                minimum=1,
                maximum=10000,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any  # noqa: ARG002
    ) -> ToolResult:
        file_path = kwargs["file_path"]
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit", self.DEFAULT_LIMIT)

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

        # Check it's not a directory
        if os.path.isdir(file_path):
            return ToolResult.fail(
                f"Cannot read directory: {file_path}. "
                "Use ls command via Bash tool to list directory contents."
            )

        # Detect file type
        mime_type, _ = mimetypes.guess_type(file_path)

        try:
            # Handle images
            if mime_type and mime_type.startswith("image/"):
                return await self._read_image(file_path, mime_type)

            # Handle PDFs
            if mime_type == "application/pdf" or file_path.endswith(".pdf"):
                return await self._read_pdf(file_path)

            # Handle Jupyter notebooks
            if file_path.endswith(".ipynb"):
                return await self._read_notebook(file_path)

            # Handle text files
            return await self._read_text(file_path, offset, limit)

        except PermissionError:
            return ToolResult.fail(f"Permission denied: {file_path}")
        except UnicodeDecodeError:
            return ToolResult.fail(
                f"Cannot decode file as text: {file_path}. "
                "It may be a binary file."
            )

    async def _read_text(
        self, file_path: str, offset: int, limit: int
    ) -> ToolResult:
        """Read a text file with line numbers."""
        lines: list[str] = []
        line_count = 0
        total_lines = 0

        with open(file_path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                total_lines = i

                # Skip lines before offset
                if i < offset:
                    continue

                # Stop after limit
                if line_count >= limit:
                    break

                # Truncate long lines
                clean_line = line.rstrip("\n\r")
                if len(clean_line) > self.MAX_LINE_LENGTH:
                    clean_line = clean_line[: self.MAX_LINE_LENGTH] + "..."

                # Format with line number
                lines.append(f"{i:6d}\t{clean_line}")
                line_count += 1

        content = "\n".join(lines)

        metadata: dict[str, Any] = {
            "file_path": file_path,
            "lines_read": line_count,
            "total_lines": total_lines,
            "offset": offset,
            "limit": limit,
        }

        if total_lines > offset + limit - 1:
            metadata["truncated"] = True
            metadata["remaining_lines"] = total_lines - (offset + limit - 1)

        return ToolResult.ok(content, **metadata)

    async def _read_image(self, file_path: str, mime_type: str) -> ToolResult:
        """Read an image file and return base64 encoded data."""
        # Check file size before reading to prevent memory issues
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_IMAGE_SIZE:
            return ToolResult.fail(
                f"Image file too large: {file_size / 1024 / 1024:.1f}MB "
                f"(max: {self.MAX_IMAGE_SIZE / 1024 / 1024:.0f}MB)"
            )

        with open(file_path, "rb") as f:
            data = f.read()

        encoded = base64.b64encode(data).decode("ascii")

        return ToolResult.ok(
            f"[Image: {mime_type}]\nBase64 data: {encoded[:100]}...",
            file_path=file_path,
            mime_type=mime_type,
            size_bytes=len(data),
            is_image=True,
            base64_data=encoded,
        )

    async def _read_pdf(self, file_path: str) -> ToolResult:
        """Read a PDF file and extract text content."""
        # Check file size before reading to prevent memory issues
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_PDF_SIZE:
            return ToolResult.fail(
                f"PDF file too large: {file_size / 1024 / 1024:.1f}MB "
                f"(max: {self.MAX_PDF_SIZE / 1024 / 1024:.0f}MB)"
            )

        try:
            import pypdf

            reader = pypdf.PdfReader(file_path)
            pages = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                pages.append(f"--- Page {i + 1} ---\n{text}")

            content = "\n\n".join(pages)

            return ToolResult.ok(
                content,
                file_path=file_path,
                page_count=len(reader.pages),
                is_pdf=True,
            )
        except ImportError:
            return ToolResult.fail(
                "pypdf library not installed. Install with: pip install pypdf"
            )

    async def _read_notebook(self, file_path: str) -> ToolResult:
        """Read a Jupyter notebook and format cells."""
        # Check file size before reading to prevent memory issues
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_NOTEBOOK_SIZE:
            return ToolResult.fail(
                f"Notebook file too large: {file_size / 1024 / 1024:.1f}MB "
                f"(max: {self.MAX_NOTEBOOK_SIZE / 1024 / 1024:.0f}MB)"
            )

        try:
            with open(file_path, encoding="utf-8") as f:
                notebook = json.load(f)
        except json.JSONDecodeError as e:
            return ToolResult.fail(
                f"Invalid notebook format: {file_path} is not valid JSON. "
                f"Error at line {e.lineno}, column {e.colno}: {e.msg}"
            )

        # Validate basic notebook structure
        if not isinstance(notebook, dict):
            return ToolResult.fail(
                f"Invalid notebook format: {file_path} is not a valid Jupyter notebook"
            )

        cells = []
        for i, cell in enumerate(notebook.get("cells", [])):
            cell_type = cell.get("cell_type", "unknown")
            source = "".join(cell.get("source", []))

            cells.append(f"--- Cell {i + 1} ({cell_type}) ---\n{source}")

            # Include outputs for code cells
            if cell_type == "code":
                outputs = cell.get("outputs", [])
                for output in outputs:
                    if "text" in output:
                        cells.append(f"Output:\n{''.join(output['text'])}")

        content = "\n\n".join(cells)

        return ToolResult.ok(
            content,
            file_path=file_path,
            cell_count=len(notebook.get("cells", [])),
            is_notebook=True,
        )
