"""RAG management commands.

This module provides CLI commands for RAG functionality:
- /rag index - Index the project
- /rag search <query> - Search for relevant content
- /rag status - Show RAG status
- /rag clear - Clear the index
- /rag config - Configure RAG settings

Example:
    /rag index           # Index the project
    /rag search auth     # Search for authentication code
    /rag status          # Show RAG status
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from code_forge.commands.base import (
    Command,
    CommandArgument,
    CommandCategory,
    CommandResult,
    SubcommandHandler,
)

if TYPE_CHECKING:
    from code_forge.commands.executor import CommandContext
    from code_forge.commands.parser import ParsedCommand

    from .manager import RAGManager


class RAGIndexCommand(Command):
    """Index the project for RAG."""

    name: ClassVar[str] = "index"
    description: ClassVar[str] = "Index the project for semantic search"
    usage: ClassVar[str] = "/rag index [--force]"

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Index the project."""
        # Get or create RAG manager
        manager = await _get_rag_manager(context)
        if manager is None:
            return CommandResult.fail("RAG is not available")

        if not manager.is_enabled:
            return CommandResult.fail(
                "RAG is disabled. Enable with: /rag config enable"
            )

        # Check for force flag
        force = "force" in parsed.flags or "-f" in parsed.flags

        try:
            context.print("Indexing project...")
            stats = await manager.index_project(force=force)

            lines = [
                "Indexing complete!",
                f"  Documents: {stats.total_documents}",
                f"  Chunks: {stats.total_chunks}",
                f"  Tokens: {stats.total_tokens:,}",
                f"  Model: {stats.embedding_model}",
            ]

            if stats.documents_by_type:
                lines.append("  By type:")
                for doc_type, count in sorted(stats.documents_by_type.items()):
                    lines.append(f"    {doc_type}: {count}")

            return CommandResult.ok("\n".join(lines))

        except Exception as e:
            return CommandResult.fail(f"Indexing failed: {e}")


class RAGSearchCommand(Command):
    """Search for relevant content."""

    name: ClassVar[str] = "search"
    description: ClassVar[str] = "Search for relevant content"
    usage: ClassVar[str] = "/rag search <query>"
    arguments: ClassVar[list[CommandArgument]] = [
        CommandArgument(
            name="query",
            description="Search query",
            required=True,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Search for content."""
        manager = await _get_rag_manager(context)
        if manager is None:
            return CommandResult.fail("RAG is not available")

        if not manager.is_enabled:
            return CommandResult.fail(
                "RAG is disabled. Enable with: /rag config enable"
            )

        # Get query from all remaining args
        query = " ".join(parsed.args) if parsed.args else ""
        if not query:
            return CommandResult.fail("Search query required")

        try:
            # Show scope indicator
            context.print(f"Searching indexed files in: {manager.project_root}")

            # Use hybrid search - falls back to text search when vector scores are low
            results, used_fallback = await manager.search_hybrid(query)

            if not results:
                return CommandResult.ok(
                    f"No matches found for: {query}\n\n"
                    f"Note: Only files within the project directory are indexed.\n"
                    f"Use `grep` or `glob` for files outside the index scope."
                )

            # Check for low confidence results (only if not using fallback)
            LOW_CONFIDENCE_THRESHOLD = 0.3
            max_score = max(r.score for r in results)
            low_confidence = not used_fallback and max_score < LOW_CONFIDENCE_THRESHOLD

            lines = [f"Found {len(results)} results for: {query}", ""]

            if used_fallback:
                lines.append(
                    "📝 **Text search used** - exact matches found via keyword search."
                )
                lines.append("")
            elif low_confidence:
                lines.append(
                    "⚠️  **Low confidence matches** - exact content may not exist in index."
                )
                lines.append(
                    "    These are semantically similar results, not exact matches."
                )
                lines.append("")

            for i, result in enumerate(results, 1):
                lines.append(
                    f"**{i}. {result.document.path}** "
                    f"(lines {result.chunk.start_line}-{result.chunk.end_line}, "
                    f"score: {result.score:.2f})"
                )
                # Show snippet preview (first 100 chars)
                snippet = result.snippet[:100]
                if len(result.snippet) > 100:
                    snippet += "..."
                lines.append(f"   {snippet}")
                lines.append("")

            return CommandResult.ok("\n".join(lines))

        except Exception as e:
            return CommandResult.fail(f"Search failed: {e}")


class RAGStatusCommand(Command):
    """Show RAG status."""

    name: ClassVar[str] = "status"
    description: ClassVar[str] = "Show RAG status"
    usage: ClassVar[str] = "/rag status"

    async def execute(
        self,
        _parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show status."""
        manager = await _get_rag_manager(context)
        if manager is None:
            return CommandResult.fail("RAG is not available")

        try:
            status = await manager.get_status()
            formatted = manager.format_status(status)
            return CommandResult.ok(formatted)

        except Exception as e:
            return CommandResult.fail(f"Failed to get status: {e}")


class RAGClearCommand(Command):
    """Clear the RAG index."""

    name: ClassVar[str] = "clear"
    description: ClassVar[str] = "Clear the RAG index"
    usage: ClassVar[str] = "/rag clear"

    async def execute(
        self,
        _parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Clear the index."""
        manager = await _get_rag_manager(context)
        if manager is None:
            return CommandResult.fail("RAG is not available")

        if not manager.is_enabled:
            return CommandResult.fail("RAG is disabled")

        try:
            count = await manager.clear_index()
            return CommandResult.ok(f"Cleared {count} chunks from index")

        except Exception as e:
            return CommandResult.fail(f"Failed to clear index: {e}")


class RAGConfigEnableCommand(Command):
    """Enable RAG."""

    name: ClassVar[str] = "enable"
    description: ClassVar[str] = "Enable RAG"
    usage: ClassVar[str] = "/rag config enable"

    async def execute(
        self,
        _parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Enable RAG."""
        if context.config is None:
            return CommandResult.fail("Configuration not available")

        context.config.rag.enabled = True
        return CommandResult.ok("RAG enabled. Run `/rag index` to index the project.")


class RAGConfigDisableCommand(Command):
    """Disable RAG."""

    name: ClassVar[str] = "disable"
    description: ClassVar[str] = "Disable RAG"
    usage: ClassVar[str] = "/rag config disable"

    async def execute(
        self,
        _parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Disable RAG."""
        if context.config is None:
            return CommandResult.fail("Configuration not available")

        context.config.rag.enabled = False
        return CommandResult.ok("RAG disabled.")


class RAGConfigShowCommand(Command):
    """Show RAG configuration."""

    name: ClassVar[str] = "show"
    description: ClassVar[str] = "Show RAG configuration"
    usage: ClassVar[str] = "/rag config show"

    async def execute(
        self,
        _parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show configuration."""
        if context.config is None:
            return CommandResult.fail("Configuration not available")

        rag_config = context.config.rag

        # Handle both string and enum types for provider/store
        provider = getattr(rag_config.embedding_provider, "value", rag_config.embedding_provider)
        store = getattr(rag_config.vector_store, "value", rag_config.vector_store)

        lines = [
            "### RAG Configuration",
            "",
            f"**Enabled:** {rag_config.enabled}",
            f"**Auto Index:** {rag_config.auto_index}",
            "",
            "**Embedding:**",
            f"  Provider: {provider}",
            f"  Model: {rag_config.embedding_model}",
            "",
            "**Vector Store:**",
            f"  Type: {store}",
            f"  Directory: {rag_config.index_directory}",
            "",
            "**Indexing:**",
            f"  Chunk Size: {rag_config.chunk_size} tokens",
            f"  Chunk Overlap: {rag_config.chunk_overlap} tokens",
            f"  Max File Size: {rag_config.max_file_size_kb} KB",
            f"  Respect .gitignore: {rag_config.respect_gitignore}",
            "",
            "**Retrieval:**",
            f"  Max Results: {rag_config.default_max_results}",
            f"  Min Score: {rag_config.default_min_score}",
            f"  Context Budget: {rag_config.context_token_budget} tokens",
        ]

        return CommandResult.ok("\n".join(lines))


class RAGConfigCommand(SubcommandHandler):
    """Configure RAG settings."""

    name: ClassVar[str] = "config"
    description: ClassVar[str] = "Configure RAG settings"
    usage: ClassVar[str] = "/rag config [subcommand]"
    subcommands: ClassVar[dict[str, Command]] = {
        "enable": RAGConfigEnableCommand(),
        "disable": RAGConfigDisableCommand(),
        "show": RAGConfigShowCommand(),
    }

    async def execute_default(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show config by default."""
        return await self.subcommands["show"].execute(parsed, context)


class RAGCommand(SubcommandHandler):
    """RAG management."""

    name: ClassVar[str] = "rag"
    aliases: ClassVar[list[str]] = ["r"]
    description: ClassVar[str] = "RAG (Retrieval-Augmented Generation) management"
    usage: ClassVar[str] = "/rag [subcommand]"
    category: ClassVar[CommandCategory] = CommandCategory.CONTEXT
    subcommands: ClassVar[dict[str, Command]] = {
        "index": RAGIndexCommand(),
        "search": RAGSearchCommand(),
        "status": RAGStatusCommand(),
        "clear": RAGClearCommand(),
        "config": RAGConfigCommand(),
    }

    async def execute_default(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Show status by default."""
        return await self.subcommands["status"].execute(parsed, context)


async def _get_rag_manager(context: CommandContext) -> RAGManager | None:
    """Get or create RAG manager from context.

    Args:
        context: Command context.

    Returns:
        RAG manager or None if not available.
    """
    from .config import RAGConfig as RAGConfigFull
    from .manager import RAGManager

    # Check if context has rag_manager attribute
    if hasattr(context, "rag_manager") and context.rag_manager is not None:
        manager: RAGManager = context.rag_manager
        return manager

    # Try to create from config
    if context.config is None:
        return None

    # Determine project root
    project_root = Path.cwd()

    # Convert lightweight config to full RAGConfig
    rag_config = context.config.rag
    full_config = RAGConfigFull(
        enabled=rag_config.enabled,
        auto_index=rag_config.auto_index,
        watch_files=rag_config.watch_files,
        embedding_model=rag_config.embedding_model,
        openai_embedding_model=rag_config.openai_embedding_model,
        index_directory=rag_config.index_directory,
        include_patterns=rag_config.include_patterns or [],
        exclude_patterns=rag_config.exclude_patterns or [],
        max_file_size_kb=rag_config.max_file_size_kb,
        respect_gitignore=rag_config.respect_gitignore,
        chunk_size=rag_config.chunk_size,
        chunk_overlap=rag_config.chunk_overlap,
        default_max_results=rag_config.default_max_results,
        default_min_score=rag_config.default_min_score,
        context_token_budget=rag_config.context_token_budget,
    )

    # Create manager
    manager = RAGManager(
        project_root=project_root,
        config=full_config,
    )

    # Store on context for reuse (if possible)
    if hasattr(context, "rag_manager"):
        context.rag_manager = manager

    return manager


def get_commands() -> list[Command]:
    """Get all RAG commands.

    Returns:
        List of RAG command instances.
    """
    return [RAGCommand()]
