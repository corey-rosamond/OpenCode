"""Control commands for REPL operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import Command, CommandCategory, CommandResult

if TYPE_CHECKING:
    from ..executor import CommandContext
    from ..parser import ParsedCommand


class ClearCommand(Command):
    """Clear the screen and conversation context."""

    name = "clear"
    aliases = ["cls"]
    description = "Clear the screen and conversation context"
    usage = "/clear"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Clear screen and context."""
        # Clear context manager (conversation history)
        if context.context_manager:
            context.context_manager.reset()

        # ANSI escape code to clear screen and move cursor to top
        context.print("\033[2J\033[H")

        # Signal to reset token counter
        return CommandResult.ok(
            "Conversation cleared.",
            data={"action": "clear", "reset_tokens": True},
        )


class ExitCommand(Command):
    """Exit the application."""

    name = "exit"
    aliases = ["quit", "q"]
    description = "Exit the application"
    usage = "/exit"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Exit application."""
        # Save session if active
        if context.session_manager and context.session_manager.has_current:
            context.session_manager.close()

        # Return special result to signal exit
        return CommandResult.ok("Goodbye!", data={"action": "exit"})


class ResetCommand(Command):
    """Reset to fresh state."""

    name = "reset"
    description = "Reset to fresh state"
    usage = "/reset"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Reset state."""
        messages = []

        # Close current session
        if context.session_manager and context.session_manager.has_current:
            context.session_manager.close()
            messages.append("Previous session closed and saved.")

        # Reset context
        if context.context_manager:
            context.context_manager.reset()
            messages.append("Context cleared.")

        # Create new session
        if context.session_manager:
            session = context.session_manager.create()
            short_id = session.id[:8] if len(session.id) > 8 else session.id
            messages.append(f"Started new session: {short_id}...")

        if not messages:
            messages.append("Reset complete.")

        # Signal to reset token counter
        return CommandResult.ok(
            "\n".join(messages),
            data={"action": "reset", "reset_tokens": True},
        )


class StopCommand(Command):
    """Stop current operation."""

    name = "stop"
    aliases = ["cancel", "abort"]
    description = "Stop current operation"
    usage = "/stop"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Stop operation."""
        # Signal to stop any running operation
        return CommandResult.ok("Stopping...", data={"action": "stop"})


def get_commands() -> list[Command]:
    """Get all control commands."""
    return [
        ClearCommand(),
        ExitCommand(),
        ResetCommand(),
        StopCommand(),
    ]
