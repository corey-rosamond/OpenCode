"""Session management commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import Command, CommandCategory, CommandResult, SubcommandHandler

if TYPE_CHECKING:
    from ..executor import CommandContext
    from ..parser import ParsedCommand


class SessionListCommand(Command):
    """List all sessions."""

    name = "list"
    description = "List all sessions"
    usage = "/session list [--limit N]"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """List sessions."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        limit_str = parsed.get_kwarg("limit", "20")
        if limit_str is None:
            limit_str = "20"
        try:
            limit = int(limit_str)
        except ValueError:
            return CommandResult.fail(f"Invalid limit: {limit_str}")

        sessions = context.session_manager.list_sessions(limit=limit)

        if not sessions:
            return CommandResult.ok("No sessions found.")

        lines = [f"Sessions ({len(sessions)}):", ""]

        for s in sessions:
            session_id = s.id[:8] if len(s.id) > 8 else s.id
            title = s.title or "(untitled)"
            lines.append(f"  {session_id}... | {title}")
            lines.append(f"           {s.message_count} msgs | {s.total_tokens} tokens")
            lines.append(f"           Updated: {s.updated_at}")
            lines.append("")

        return CommandResult.ok("\n".join(lines))


class SessionNewCommand(Command):
    """Create new session."""

    name = "new"
    description = "Create a new session"
    usage = "/session new [--title <title>]"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Create new session."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        title = parsed.get_kwarg("title", "")

        # Close current session if any
        if context.session_manager.has_current:
            context.session_manager.close()

        session = context.session_manager.create(title=title if title else "")
        session_id = session.id[:8] if len(session.id) > 8 else session.id

        return CommandResult.ok(f"Created new session: {session_id}...")


class SessionResumeCommand(Command):
    """Resume a session."""

    name = "resume"
    description = "Resume a session"
    usage = "/session resume [id]"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Resume session."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        session_id = parsed.get_arg(0)

        if session_id:
            # Find matching session
            sessions = context.session_manager.list_sessions()
            for s in sessions:
                if s.id.startswith(session_id):
                    if context.session_manager.has_current:
                        context.session_manager.close()
                    resumed = context.session_manager.resume(s.id)
                    if resumed:
                        display_name = resumed.title or resumed.id[:8]
                        return CommandResult.ok(f"Resumed session: {display_name}")
                    return CommandResult.fail(f"Failed to resume session: {s.id}")
            return CommandResult.fail(f"Session not found: {session_id}")
        else:
            # Resume latest
            latest = context.session_manager.resume_latest()
            if latest:
                display_name = latest.title or latest.id[:8]
                return CommandResult.ok(f"Resumed session: {display_name}")
            return CommandResult.fail("No sessions to resume")


class SessionDeleteCommand(Command):
    """Delete a session."""

    name = "delete"
    description = "Delete a session"
    usage = "/session delete <id>"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Delete session."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        session_id = parsed.get_arg(0)
        if not session_id:
            return CommandResult.fail("Session ID required")

        # Find matching session
        sessions = context.session_manager.list_sessions()
        for s in sessions:
            if s.id.startswith(session_id):
                if context.session_manager.delete(s.id):
                    short_id = s.id[:8] if len(s.id) > 8 else s.id
                    return CommandResult.ok(f"Deleted session: {short_id}...")
                return CommandResult.fail("Failed to delete session")

        return CommandResult.fail(f"Session not found: {session_id}")


class SessionTitleCommand(Command):
    """Set session title."""

    name = "title"
    description = "Set session title"
    usage = "/session title <text>"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Set title."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        if not context.session_manager.has_current:
            return CommandResult.fail("No active session")

        title = " ".join(parsed.args)
        if not title:
            return CommandResult.fail("Title required")

        context.session_manager.set_title(title)
        return CommandResult.ok(f"Title set: {title}")


class SessionTagCommand(Command):
    """Add tag to session."""

    name = "tag"
    description = "Add tag to session"
    usage = "/session tag <name>"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Add tag."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        if not context.session_manager.has_current:
            return CommandResult.fail("No active session")

        tag = parsed.get_arg(0)
        if not tag:
            return CommandResult.fail("Tag name required")

        session = context.session_manager.current_session
        if session:
            if tag not in session.tags:
                session.tags.append(tag)
                context.session_manager.save()
            return CommandResult.ok(f"Tag added: {tag}")
        return CommandResult.fail("No active session")


class SessionUntagCommand(Command):
    """Remove tag from session."""

    name = "untag"
    description = "Remove tag from session"
    usage = "/session untag <name>"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Remove tag."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        if not context.session_manager.has_current:
            return CommandResult.fail("No active session")

        tag = parsed.get_arg(0)
        if not tag:
            return CommandResult.fail("Tag name required")

        session = context.session_manager.current_session
        if session:
            if tag in session.tags:
                session.tags.remove(tag)
                context.session_manager.save()
                return CommandResult.ok(f"Tag removed: {tag}")
            return CommandResult.fail(f"Tag not found: {tag}")
        return CommandResult.fail("No active session")


class SessionCleanupCommand(Command):
    """Clean up old sessions and backups."""

    name = "cleanup"
    description = "Remove old sessions and backup files"
    usage = "/session cleanup [--days N] [--keep N]"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Clean up old sessions and backups."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        # Parse options
        days_str = parsed.get_kwarg("days", "30")
        keep_str = parsed.get_kwarg("keep", "10")

        try:
            max_age_days = int(days_str) if days_str else 30
        except ValueError:
            return CommandResult.fail(f"Invalid days value: {days_str}")

        try:
            keep_minimum = int(keep_str) if keep_str else 10
        except ValueError:
            return CommandResult.fail(f"Invalid keep value: {keep_str}")

        # Run cleanup
        storage = context.session_manager.storage
        deleted_sessions = storage.cleanup_old_sessions(
            max_age_days=max_age_days,
            keep_minimum=keep_minimum,
        )
        deleted_backups = storage.cleanup_old_backups()

        lines = ["Session cleanup complete:"]
        lines.append(f"  Sessions removed: {len(deleted_sessions)}")
        lines.append(f"  Backups removed: {deleted_backups}")

        if deleted_sessions:
            lines.append("")
            lines.append("Deleted session IDs:")
            for sid in deleted_sessions[:5]:  # Show first 5
                lines.append(f"  - {sid[:8]}...")
            if len(deleted_sessions) > 5:
                lines.append(f"  ... and {len(deleted_sessions) - 5} more")

        return CommandResult.ok("\n".join(lines))


class SessionCommand(SubcommandHandler):
    """Session management."""

    name = "session"
    aliases = ["sess", "s"]
    description = "Session management"
    usage = "/session [subcommand]"
    category = CommandCategory.SESSION
    subcommands = {
        "list": SessionListCommand(),
        "new": SessionNewCommand(),
        "resume": SessionResumeCommand(),
        "delete": SessionDeleteCommand(),
        "title": SessionTitleCommand(),
        "tag": SessionTagCommand(),
        "untag": SessionUntagCommand(),
        "cleanup": SessionCleanupCommand(),
    }

    async def execute_default(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show current session info."""
        if context.session_manager is None:
            return CommandResult.fail("Session manager not available")

        if not context.session_manager.has_current:
            return CommandResult.ok("No active session. Use /session new to create one.")

        session = context.session_manager.current_session
        if session is None:
            return CommandResult.ok("No active session. Use /session new to create one.")

        lines = [
            f"Session: {session.id}",
            f"Title: {session.title or '(untitled)'}",
            f"Messages: {session.message_count}",
            f"Tokens: {session.total_tokens}",
            f"Created: {session.created_at}",
            f"Updated: {session.updated_at}",
        ]

        if session.tags:
            lines.append(f"Tags: {', '.join(session.tags)}")

        return CommandResult.ok("\n".join(lines))


def get_commands() -> list[Command]:
    """Get all session commands."""
    return [SessionCommand()]
