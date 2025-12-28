"""Grep tool implementation."""

from __future__ import annotations

import asyncio
import glob as glob_module
import os
import re
from typing import Any, ClassVar

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


class GrepTool(BaseTool):
    """Search file contents with regular expressions.

    Inspired by ripgrep, supports context lines and multiple output modes.
    """

    MAX_FILE_SIZE: ClassVar[int] = 10 * 1024 * 1024  # 10MB
    DEFAULT_HEAD_LIMIT: ClassVar[int] = 100
    DEFAULT_TIMEOUT: ClassVar[float] = 60.0  # 60 seconds default timeout

    # Type to extension mapping
    TYPE_EXTENSIONS: ClassVar[dict[str, list[str]]] = {
        "py": ["*.py"],
        "js": ["*.js", "*.jsx"],
        "ts": ["*.ts", "*.tsx"],
        "rust": ["*.rs"],
        "go": ["*.go"],
        "java": ["*.java"],
        "c": ["*.c", "*.h"],
        "cpp": ["*.cpp", "*.hpp", "*.cc", "*.hh"],
        "md": ["*.md"],
        "json": ["*.json"],
        "yaml": ["*.yaml", "*.yml"],
    }

    @property
    def name(self) -> str:
        return "Grep"

    @property
    def description(self) -> str:
        return """A powerful search tool built on ripgrep.

Usage:
- Supports full regex syntax (e.g., "log.*Error", "function\\s+\\w+")
- Filter files with glob parameter (e.g., "*.js", "**/*.tsx")
- Output modes: "content" shows lines, "files_with_matches" shows paths, "count" shows counts
- Use -i for case-insensitive, -A/-B/-C for context lines"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                type="string",
                description="The regular expression pattern to search for",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="File or directory to search in. "
                "Defaults to current working directory.",
                required=False,
            ),
            ToolParameter(
                name="glob",
                type="string",
                description="Glob pattern to filter files (e.g., '*.py', '*.{ts,tsx}')",
                required=False,
            ),
            ToolParameter(
                name="type",
                type="string",
                description="File type to search (e.g., 'py', 'js', 'rust')",
                required=False,
            ),
            ToolParameter(
                name="output_mode",
                type="string",
                description="Output mode",
                required=False,
                default="files_with_matches",
                enum=["content", "files_with_matches", "count"],
            ),
            ToolParameter(
                name="-i",
                type="boolean",
                description="Case insensitive search",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="-n",
                type="boolean",
                description="Show line numbers in output (for content mode)",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="-A",
                type="integer",
                description="Number of lines to show after each match",
                required=False,
                minimum=0,
            ),
            ToolParameter(
                name="-B",
                type="integer",
                description="Number of lines to show before each match",
                required=False,
                minimum=0,
            ),
            ToolParameter(
                name="-C",
                type="integer",
                description="Number of lines to show before and after each match",
                required=False,
                minimum=0,
            ),
            ToolParameter(
                name="multiline",
                type="boolean",
                description="Enable multiline matching mode",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="head_limit",
                type="integer",
                description="Limit output to first N results",
                required=False,
            ),
            ToolParameter(
                name="offset",
                type="integer",
                description="Skip first N results",
                required=False,
                default=0,
            ),
            ToolParameter(
                name="timeout",
                type="number",
                description="Maximum time in seconds for the search (default: 60)",
                required=False,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        pattern = kwargs["pattern"]
        search_path = kwargs.get("path") or context.working_dir
        glob_filter = kwargs.get("glob")
        type_filter = kwargs.get("type")
        output_mode = kwargs.get("output_mode", "files_with_matches")
        case_insensitive = kwargs.get("-i", False)
        show_line_numbers = kwargs.get("-n", True)
        after_context = kwargs.get("-A", 0) or 0
        before_context = kwargs.get("-B", 0) or 0
        both_context = kwargs.get("-C", 0) or 0
        multiline = kwargs.get("multiline", False)
        # Use None check so head_limit=0 means unlimited, not default
        head_limit_val = kwargs.get("head_limit")
        head_limit = self.DEFAULT_HEAD_LIMIT if head_limit_val is None else head_limit_val
        offset = kwargs.get("offset") or 0
        timeout = kwargs.get("timeout") or self.DEFAULT_TIMEOUT

        # Context lines
        if both_context:
            after_context = both_context
            before_context = both_context

        try:
            # Compile regex
            flags = re.MULTILINE if multiline else 0
            if case_insensitive:
                flags |= re.IGNORECASE

            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult.fail(f"Invalid regex pattern: {e!s}")

            # Get files to search
            files = self._get_files(search_path, glob_filter, type_filter)

            # Search files with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._search_files_sync,
                        files,
                        regex,
                        output_mode,
                        show_line_numbers,
                        before_context,
                        after_context,
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                return ToolResult.fail(
                    f"Search timed out after {timeout} seconds. "
                    "Try narrowing the search path or pattern."
                )

            # Apply offset and limit
            total_results = len(results)
            results = results[offset:]
            if head_limit:
                results = results[:head_limit]

            # Format output
            output = self._format_output(results, output_mode)

            return ToolResult.ok(
                output,
                pattern=pattern,
                total_matches=total_results,
                returned_matches=len(results),
                offset=offset,
                head_limit=head_limit,
            )

        except OSError:
            # Don't expose detailed OS error - could leak filesystem info
            return ToolResult.fail("Error searching: unable to access files")

    def _search_files_sync(
        self,
        files: list[str],
        regex: re.Pattern[str],
        output_mode: str,
        show_line_numbers: bool,
        before_context: int,
        after_context: int,
    ) -> list[dict[str, Any]]:
        """Search files synchronously (called via asyncio.to_thread for timeout)."""
        results: list[dict[str, Any]] = []
        for file_path in files:
            file_results = self._search_file(
                file_path,
                regex,
                output_mode,
                show_line_numbers,
                before_context,
                after_context,
            )
            if file_results:
                results.extend(file_results)
        return results

    def _get_files(
        self,
        search_path: str,
        glob_filter: str | None,
        type_filter: str | None,
    ) -> list[str]:
        """Get list of files to search."""
        if os.path.isfile(search_path):
            return [search_path]

        files: list[str] = []

        if glob_filter:
            pattern = os.path.join(search_path, "**", glob_filter)
            files = glob_module.glob(pattern, recursive=True)
        elif type_filter and type_filter in self.TYPE_EXTENSIONS:
            for ext in self.TYPE_EXTENSIONS[type_filter]:
                pattern = os.path.join(search_path, "**", ext)
                files.extend(glob_module.glob(pattern, recursive=True))
        else:
            # Search all files
            for root, _, filenames in os.walk(search_path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))

        # Filter to readable text files
        return [f for f in files if os.path.isfile(f) and self._is_text_file(f)]

    def _is_text_file(self, file_path: str) -> bool:
        """Check if file appears to be text."""
        try:
            # Check file size
            if os.path.getsize(file_path) > self.MAX_FILE_SIZE:
                return False

            # Try to read first chunk
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                # Check for null bytes (binary indicator)
                return b"\x00" not in chunk
        except (OSError, PermissionError):
            return False

    def _search_file(
        self,
        file_path: str,
        regex: re.Pattern[str],
        output_mode: str,
        show_line_numbers: bool,
        before_context: int,
        after_context: int,
    ) -> list[dict[str, Any]]:
        """Search a single file for matches."""
        results: list[dict[str, Any]] = []

        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (OSError, PermissionError):
            return results

        match_count = 0

        for i, line in enumerate(lines):
            if regex.search(line):
                match_count += 1

                if output_mode == "files_with_matches":
                    # Just need to know this file matches
                    return [{"file": file_path}]
                elif output_mode == "count":
                    continue
                else:  # content
                    # Get context lines
                    start = max(0, i - before_context)
                    end = min(len(lines), i + after_context + 1)

                    context_lines = []
                    for j in range(start, end):
                        prefix = ">" if j == i else " "
                        line_num = f"{j + 1}:" if show_line_numbers else ""
                        context_lines.append(
                            f"{prefix}{line_num}{lines[j].rstrip()}"
                        )

                    results.append({
                        "file": file_path,
                        "line": i + 1,
                        "content": "\n".join(context_lines),
                    })

        if output_mode == "count" and match_count > 0:
            results.append({"file": file_path, "count": match_count})

        return results

    def _format_output(self, results: list[dict[str, Any]], output_mode: str) -> str:
        """Format search results for output."""
        if not results:
            return "No matches found"

        if output_mode == "files_with_matches":
            # Deduplicate and return file paths
            files = sorted({r["file"] for r in results})
            return "\n".join(files)

        elif output_mode == "count":
            lines = []
            for r in results:
                lines.append(f"{r['file']}: {r['count']}")
            return "\n".join(lines)

        else:  # content
            sections = []
            for r in results:
                sections.append(f"{r['file']}:{r['line']}\n{r['content']}")
            return "\n\n".join(sections)
