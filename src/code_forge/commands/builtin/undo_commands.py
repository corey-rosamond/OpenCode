"""Undo/redo commands for file operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import (
    ArgumentType,
    Command,
    CommandArgument,
    CommandCategory,
    CommandResult,
)

if TYPE_CHECKING:
    from ..executor import CommandContext
    from ..parser import ParsedCommand


class UndoCommand(Command):
    """Undo the last file operation."""

    name = "undo"
    aliases = ["u"]
    description = "Undo the last file operation (Edit, Write, or Bash)"
    usage = "/undo"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Undo the last operation."""
        if context.undo_manager is None:
            return CommandResult.fail("Undo system is not available")

        if not context.undo_manager.enabled:
            return CommandResult.fail("Undo is disabled in configuration")

        if not context.undo_manager.can_undo:
            return CommandResult.fail("Nothing to undo")

        # Get description before undoing for display
        description = context.undo_manager.get_undo_description()

        success, message = context.undo_manager.undo()

        if success:
            return CommandResult.ok(f"Undone: {description}")
        else:
            return CommandResult.fail(message)


class RedoCommand(Command):
    """Redo the last undone operation."""

    name = "redo"
    aliases = []  # Avoid conflicts
    description = "Redo the last undone file operation"
    usage = "/redo"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Redo the last undone operation."""
        if context.undo_manager is None:
            return CommandResult.fail("Undo system is not available")

        if not context.undo_manager.enabled:
            return CommandResult.fail("Undo is disabled in configuration")

        if not context.undo_manager.can_redo:
            return CommandResult.fail("Nothing to redo")

        # Get description before redoing for display
        description = context.undo_manager.get_redo_description()

        success, message = context.undo_manager.redo()

        if success:
            return CommandResult.ok(f"Redone: {description}")
        else:
            return CommandResult.fail(message)


class UndoHistoryCommand(Command):
    """Show undo history."""

    name = "undo-history"
    aliases = ["undos"]  # Avoid conflicts with history command
    description = "Show undo/redo history"
    usage = "/undo-history [limit]"
    category = CommandCategory.CONTROL
    arguments = [
        CommandArgument(
            name="limit",
            description="Maximum number of entries to show (default: 10)",
            required=False,
            default="10",
            type=ArgumentType.INTEGER,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show undo history."""
        if context.undo_manager is None:
            return CommandResult.fail("Undo system is not available")

        if not context.undo_manager.enabled:
            return CommandResult.fail("Undo is disabled in configuration")

        # Parse limit argument
        limit_str = parsed.get_arg(0) or "10"
        try:
            limit = int(limit_str)
        except ValueError:
            limit = 10

        # Get undo history
        undo_history = context.undo_manager.get_undo_history(limit=limit)
        redo_count = context.undo_manager.redo_count

        if not undo_history and redo_count == 0:
            return CommandResult.ok("No undo history")

        lines = ["Undo History:"]
        lines.append("-" * 40)

        if undo_history:
            for i, entry in enumerate(undo_history):
                prefix = ">>> " if i == 0 else "    "
                lines.append(f"{prefix}{entry['description']}")
                lines.append(f"    {entry['tool']} | {entry['files']} file(s) | {entry['timestamp']}")
        else:
            lines.append("  (no undo entries)")

        if redo_count > 0:
            lines.append("")
            lines.append(f"Redo available: {redo_count} operation(s)")

        # Add stats
        stats = context.undo_manager.get_stats()
        lines.append("")
        lines.append(f"Total: {stats['undo_count']} undo, {stats['redo_count']} redo")
        size_mb = stats['total_size_bytes'] / (1024 * 1024)
        lines.append(f"Size: {size_mb:.2f} MB")

        return CommandResult.ok("\n".join(lines))


class UndoClearCommand(Command):
    """Clear undo history."""

    name = "undo-clear"
    description = "Clear all undo/redo history"
    usage = "/undo-clear"
    category = CommandCategory.CONTROL

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Clear undo history."""
        if context.undo_manager is None:
            return CommandResult.fail("Undo system is not available")

        # Get counts before clearing
        undo_count = context.undo_manager.undo_count
        redo_count = context.undo_manager.redo_count

        context.undo_manager.clear()

        total = undo_count + redo_count
        return CommandResult.ok(f"Cleared {total} undo/redo entries")


def get_commands() -> list[Command]:
    """Get all undo commands."""
    return [
        UndoCommand(),
        RedoCommand(),
        UndoHistoryCommand(),
        UndoClearCommand(),
    ]
