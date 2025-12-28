"""Tool for killing background shells."""

from __future__ import annotations

from typing import Any

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.execution.shell_manager import ShellManager


class KillShellTool(BaseTool):
    """Kill a running background bash shell by its ID."""

    @property
    def name(self) -> str:
        return "KillShell"

    @property
    def description(self) -> str:
        return """Kills a running background bash shell by its ID.

Usage:
- Takes a shell_id parameter identifying the shell to kill
- Returns success or failure status
- Use this to terminate long-running commands
- Shell IDs can be found from BashTool output or /tasks command"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.EXECUTION

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="shell_id",
                type="string",
                description="The ID of the background shell to kill",
                required=True,
            ),
        ]

    async def _execute(
        self, context: ExecutionContext, **kwargs: Any  # noqa: ARG002
    ) -> ToolResult:
        shell_id = kwargs["shell_id"]

        # Get shell
        shell = ShellManager.get_shell(shell_id)
        if shell is None:
            return ToolResult.fail(
                f"Shell not found: {shell_id}. "
                "The shell may have already completed or been killed."
            )

        # Check if already stopped
        if not shell.is_running:
            return ToolResult.ok(
                f"Shell {shell_id} already stopped (status: {shell.status.value})",
                shell_id=shell_id,
                status=shell.status.value,
                already_stopped=True,
            )

        # Kill the shell
        try:
            shell.kill()

            return ToolResult.ok(
                f"Shell {shell_id} terminated",
                shell_id=shell_id,
                command=shell.command,
                duration_ms=shell.duration_ms,
            )
        except Exception:
            # Don't expose detailed error - could leak process info
            return ToolResult.fail(f"Failed to kill shell {shell_id}")
