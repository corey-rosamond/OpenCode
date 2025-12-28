"""Bash command execution tool."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.execution.shell_manager import ShellManager
from code_forge.undo.bash_detector import BashFileDetector

if TYPE_CHECKING:
    from code_forge.undo.manager import UndoManager


class BashTool(BaseTool):
    """Execute bash commands in a persistent shell session.

    Supports foreground execution with timeout and
    background execution for long-running commands.

    Timeout Units:
        - The `timeout` parameter uses MILLISECONDS (LLM API convention)
        - Internally converted to seconds for asyncio.wait_for()
        - ExecutionContext.timeout (seconds) provides an outer limit
        - DEFAULT_TIMEOUT_MS = 120000ms = 2 minutes (matches context default)
    """

    DEFAULT_TIMEOUT_MS: ClassVar[int] = 120000  # 2 minutes (120000ms = 120s)
    MAX_TIMEOUT_MS: ClassVar[int] = 600000  # 10 minutes (600000ms = 600s)
    MAX_OUTPUT_SIZE: ClassVar[int] = 30000  # characters

    # Patterns for dangerous commands
    # Note: Patterns use word boundaries and avoid end anchors ($) to catch
    # piped/chained variants like "rm -rf / | cat" or "rm -rf / && echo done"
    DANGEROUS_PATTERNS: ClassVar[list[str]] = [
        r"rm\s+(-[a-z]*r[a-z]*\s+)*-[a-z]*f[a-z]*\s+/(\s|;|\||&|$)",  # rm -rf / (any flag order)
        r"rm\s+(-[a-z]*f[a-z]*\s+)*-[a-z]*r[a-z]*\s+/(\s|;|\||&|$)",  # rm -fr / (any flag order)
        r"rm\s+-rf\s+/\*",  # rm -rf /*
        r"rm\s+-fr\s+/\*",  # rm -fr /*
        r"mkfs\.",  # Format filesystem
        r"dd\s+.*of=/dev/[sh]d",  # Direct disk write (sd* or hd*)
        r">\s*/dev/[sh]d",  # Write to disk device
        r"chmod\s+(-[a-z]*R[a-z]*\s+)*777\s+/(\s|;|\||&|$)",  # chmod -R 777 /
        r"chmod\s+777\s+(-[a-z]*R[a-z]*\s+)+/(\s|;|\||&|$)",  # chmod 777 -R /
        r":()\s*\{",  # Fork bomb start pattern
        r"mv\s+/\s",  # Move root
        r"chown\s+(-[a-z]*R[a-z]*\s+)*\S+\s+/(\s|;|\||&|$)",  # chown -R user /
        r"curl\s+.*\|\s*(ba)?sh",  # Pipe curl to shell
        r"wget\s+.*\|\s*(ba)?sh",  # Pipe wget to shell
    ]

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return """Executes a bash command in a persistent shell session with optional timeout.

IMPORTANT: This tool is for terminal operations like git, npm, docker, etc.
DO NOT use it for file operations - use specialized tools instead.

Usage notes:
- The command argument is required
- Timeout defaults to 120000ms (2 min), max 600000ms (10 min)
- Output exceeding 30000 characters will be truncated
- Use run_in_background=true for long-running commands
- Always quote file paths containing spaces with double quotes
- Use && to chain dependent commands
- Use ; when you don't care if earlier commands fail
- Avoid cd - use absolute paths instead"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.EXECUTION

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="The command to execute",
                required=True,
                min_length=1,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Clear, concise description of what this command does (5-10 words)",
                required=False,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Optional timeout in milliseconds (max 600000)",
                required=False,
                minimum=1000,
                maximum=600000,
            ),
            ToolParameter(
                name="run_in_background",
                type="boolean",
                description="Run command in background. Use BashOutput to read output later.",
                required=False,
                default=False,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any
    ) -> ToolResult:
        command = kwargs["command"]
        timeout_ms = kwargs.get("timeout", self.DEFAULT_TIMEOUT_MS)
        run_in_background = kwargs.get("run_in_background", False)

        # Validate timeout
        if timeout_ms > self.MAX_TIMEOUT_MS:
            return ToolResult.fail(f"Timeout exceeds maximum: {self.MAX_TIMEOUT_MS}ms")

        # Security check - dangerous command patterns
        security_error = self._check_dangerous_command(command)
        if security_error:
            return ToolResult.fail(security_error)

        # Security check - validate working directory
        working_dir_error = self._validate_working_dir(context.working_dir)
        if working_dir_error:
            return ToolResult.fail(working_dir_error)

        # Get undo manager if available
        undo_manager: UndoManager | None = context.metadata.get("undo_manager")

        # Detect files that may be modified by this command
        detected_files: list[str] = []
        if undo_manager:
            detected_files = BashFileDetector.detect_files(command, context.working_dir)
            # Capture existing files before execution
            for file_path in detected_files:
                if os.path.exists(file_path):
                    undo_manager.capture_before(file_path)

        # Execute
        if run_in_background:
            # For background commands, we can't reliably track undo
            # since we don't know when they complete
            if undo_manager and detected_files:
                undo_manager.discard_pending()
            return await self._run_background(command, context.working_dir)
        else:
            result = await self._run_foreground(command, context.working_dir, timeout_ms)

            # Commit or discard undo entry based on result
            if undo_manager and detected_files:
                if result.success:
                    # Truncate command for description
                    cmd_preview = command[:50] + "..." if len(command) > 50 else command
                    undo_manager.commit("Bash", f"Bash: {cmd_preview}", command=command)
                else:
                    undo_manager.discard_pending()

            return result

    async def _run_foreground(
        self, command: str, working_dir: str, timeout_ms: int
    ) -> ToolResult:
        """Run command in foreground with timeout.

        Args:
            command: Shell command to execute.
            working_dir: Working directory for execution.
            timeout_ms: Timeout in milliseconds (from LLM parameter).
                        Converted to seconds for asyncio.wait_for().
        """
        timeout_sec = timeout_ms / 1000  # Convert ms -> seconds for asyncio

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_sec
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult.fail(
                    f"Command timed out after {timeout_ms}ms",
                    command=command,
                    timeout_ms=timeout_ms,
                )

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Combine output
            output = stdout_str
            if stderr_str:
                output += f"\n[stderr]\n{stderr_str}"

            # Truncate if needed
            truncated = False
            if len(output) > self.MAX_OUTPUT_SIZE:
                output = output[: self.MAX_OUTPUT_SIZE]
                output += f"\n\n[Output truncated at {self.MAX_OUTPUT_SIZE} characters]"
                truncated = True

            # Determine success
            exit_code = process.returncode
            if exit_code == 0:
                return ToolResult.ok(
                    output,
                    command=command,
                    exit_code=exit_code,
                    truncated=truncated,
                )
            else:
                return ToolResult.fail(
                    f"Command failed with exit code {exit_code}\n{output}",
                    command=command,
                    exit_code=exit_code,
                    truncated=truncated,
                )

        except Exception as e:
            return ToolResult.fail(
                f"Failed to execute command: {e!s}",
                command=command,
            )

    async def _run_background(self, command: str, working_dir: str) -> ToolResult:
        """Run command in background."""
        try:
            shell = await ShellManager.create_shell(command, working_dir)

            return ToolResult.ok(
                f"Started background shell: {shell.id}\n"
                f"Command: {command}\n"
                f"Use BashOutput tool with bash_id='{shell.id}' to read output.",
                bash_id=shell.id,
                command=command,
            )
        except Exception as e:
            return ToolResult.fail(
                f"Failed to start background shell: {e!s}",
                command=command,
            )

    def _check_dangerous_command(self, command: str) -> str | None:
        """Check if command matches dangerous patterns.

        Returns error message if dangerous, None if safe.
        """
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return "Command blocked for security: matches dangerous pattern"
        return None

    def _validate_working_dir(self, working_dir: str) -> str | None:
        """Validate working directory for safe command execution.

        Returns error message if invalid, None if valid.
        """
        try:
            path = Path(working_dir)

            # Resolve to canonical path (follows symlinks, normalizes)
            resolved = path.resolve()

            # Check that it exists
            if not resolved.exists():
                return f"Working directory does not exist: {working_dir}"

            # Check that it's a directory
            if not resolved.is_dir():
                return f"Working directory is not a directory: {working_dir}"

            return None
        except (OSError, RuntimeError):
            # Don't expose detailed OS error - could leak filesystem info
            return f"Invalid working directory: cannot access {working_dir}"
