"""Context management commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import (
    Command,
    CommandArgument,
    CommandCategory,
    CommandResult,
    SubcommandHandler,
)

if TYPE_CHECKING:
    from ..executor import CommandContext
    from ..parser import ParsedCommand


class ContextCompactCommand(Command):
    """Compact context via summarization."""

    name = "compact"
    description = "Compact context via summarization"
    usage = "/context compact"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Compact context."""
        if context.context_manager is None:
            return CommandResult.fail("Context manager not available")

        try:
            stats_before = context.context_manager.get_stats()
            msgs_before = stats_before.get("message_count", 0)
            tokens_before = stats_before.get("token_usage", 0)

            # Use threshold of 0.0 to always compact
            compacted = await context.context_manager.compact_if_needed(threshold=0.0)

            if compacted:
                stats_after = context.context_manager.get_stats()
                msgs_after = stats_after.get("message_count", 0)
                tokens_after = stats_after.get("token_usage", 0)

                tokens_saved = tokens_before - tokens_after
                msgs_removed = msgs_before - msgs_after

                lines = [
                    "Context compacted.",
                    f"  Messages: {msgs_before} -> {msgs_after} ({msgs_removed} summarized)",
                    f"  Tokens: {tokens_before:,} -> {tokens_after:,}",
                    f"  Saved: {tokens_saved:,} tokens",
                ]
            else:
                lines = ["Context already compact or no compactor available."]

            return CommandResult.ok("\n".join(lines))
        except Exception as e:
            return CommandResult.fail(f"Compaction failed: {e}")


class ContextResetCommand(Command):
    """Reset context to empty state."""

    name = "reset"
    description = "Clear all context"
    usage = "/context reset"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Reset context."""
        if context.context_manager is None:
            return CommandResult.fail("Context manager not available")

        context.context_manager.reset()
        return CommandResult.ok("Context cleared.\nMessages: 0\nTokens: 0")


class ContextModeCommand(Command):
    """Set truncation mode."""

    name = "mode"
    description = "Set truncation mode"
    usage = "/context mode <mode>"
    arguments = [
        CommandArgument(
            name="mode",
            description="Truncation mode (sliding_window, token_budget, smart, summarize)",
            required=True,
        ),
    ]

    VALID_MODES = ["sliding_window", "token_budget", "smart", "summarize"]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Set mode."""
        if context.context_manager is None:
            return CommandResult.fail("Context manager not available")

        mode = parsed.get_arg(0)
        if not mode:
            return CommandResult.fail("Mode required")

        if mode not in self.VALID_MODES:
            valid_modes = ", ".join(self.VALID_MODES)
            return CommandResult.fail(
                f'Invalid mode: "{mode}". Valid options: {valid_modes}'
            )

        try:
            from code_forge.context.manager import TruncationMode, get_strategy

            # Convert string to TruncationMode enum
            mode_enum = TruncationMode(mode)
            context.context_manager.mode = mode_enum
            context.context_manager.strategy = get_strategy(mode_enum)
            return CommandResult.ok(f"Truncation mode set to: {mode}")
        except ValueError:
            valid_modes = ", ".join(self.VALID_MODES)
            return CommandResult.fail(f'Invalid mode: "{mode}". Valid: {valid_modes}')
        except Exception as e:
            return CommandResult.fail(f"Failed to set mode: {e}")


class ContextCommand(SubcommandHandler):
    """Context management."""

    name = "context"
    aliases = ["ctx", "c"]
    description = "Context management"
    usage = "/context [subcommand]"
    category = CommandCategory.CONTEXT
    subcommands = {
        "compact": ContextCompactCommand(),
        "reset": ContextResetCommand(),
        "mode": ContextModeCommand(),
    }

    async def execute_default(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show context status with compression visibility."""
        if context.context_manager is None:
            return CommandResult.fail("Context manager not available")

        try:
            stats = context.context_manager.get_stats()
            mgr = context.context_manager

            lines = [
                "Context Status:",
                f"  Model: {stats.get('model', 'unknown')}",
                f"  Mode: {stats.get('mode', 'unknown')}",
                f"  Messages: {stats.get('message_count', 0)}",
            ]

            # Token usage with correct key
            token_usage = stats.get("token_usage", 0)
            max_tokens = stats.get("effective_limit", stats.get("max_tokens", 0))
            available = stats.get("available_tokens", 0)
            usage_pct = stats.get("usage_percentage", 0.0)

            if max_tokens > 0:
                lines.append(
                    f"  Token Usage: {token_usage:,} / {max_tokens:,} ({usage_pct:.1f}%)"
                )
                lines.append(f"  Available: {available:,} tokens")

                # Warning indicator
                if usage_pct >= 90:
                    lines.append("  Status: [CRITICAL] Context near limit!")
                elif usage_pct >= 80:
                    lines.append("  Status: [CAUTION] Approaching context limit")
                else:
                    lines.append("  Status: Normal")
            else:
                lines.append(f"  Tokens: {token_usage:,}")

            # Cache stats if available
            cache_stats = mgr.get_cache_stats()
            if cache_stats:
                lines.append("")
                lines.append("Token Cache:")
                lines.append(f"  Size: {cache_stats.get('size', 0)} entries")
                lines.append(f"  Hit Rate: {cache_stats.get('hit_rate_percent', 0):.1f}%")

            lines.append("")
            lines.append("Commands:")
            lines.append("  /context compact  - Summarize older messages")
            lines.append("  /context reset    - Clear all context")
            lines.append("  /context mode <m> - Set truncation mode")

            return CommandResult.ok("\n".join(lines))
        except Exception as e:
            return CommandResult.fail(f"Failed to get context stats: {e}")


def get_commands() -> list[Command]:
    """Get all context commands."""
    return [ContextCommand()]
