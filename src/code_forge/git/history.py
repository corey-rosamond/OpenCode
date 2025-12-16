"""Git history and log operations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .repository import GitCommit, GitError, GitRepository


@dataclass
class LogEntry:
    """Single log entry with stats."""

    commit: GitCommit
    files_changed: int | None = None
    insertions: int | None = None
    deletions: int | None = None

    def to_string(self, verbose: bool = False) -> str:
        """Format as string.

        Args:
            verbose: Include full message

        Returns:
            Formatted string
        """
        lines = [
            f"commit {self.commit.short_hash}",
            f"Author: {self.commit.author} <{self.commit.author_email}>",
            f"Date:   {self.commit.date}",
            "",
            f"    {self.commit.subject}",
        ]

        if verbose and self.commit.message != self.commit.subject:
            for line in self.commit.message.split("\n")[1:]:
                lines.append(f"    {line}")

        if self.files_changed is not None:
            stats = f" {self.files_changed} file(s) changed"
            if self.insertions:
                stats += f", {self.insertions} insertion(s)"
            if self.deletions:
                stats += f", {self.deletions} deletion(s)"
            lines.append(stats)

        return "\n".join(lines)


class GitHistory:
    """Git history operations."""

    def __init__(self, repo: GitRepository) -> None:
        """Initialize history tool.

        Args:
            repo: Git repository instance
        """
        self.repo = repo

    async def get_log(
        self,
        count: int = 10,
        path: str | None = None,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
        branch: str | None = None,
        all_branches: bool = False,
    ) -> list[LogEntry]:
        """Get commit log.

        Args:
            count: Number of commits
            path: Filter by file path
            author: Filter by author
            since: Commits since date
            until: Commits until date
            branch: Specific branch
            all_branches: Show all branches

        Returns:
            List of log entries
        """
        # Use NULL byte as separator for reliable parsing
        # Start each commit with a unique marker to handle messages with blank lines
        COMMIT_MARKER = "\x1e"  # ASCII record separator
        format_str = f"{COMMIT_MARKER}%H%x00%h%x00%an%x00%ae%x00%ai%x00%s%x00%b%x00%P%x00"

        args = [
            "log",
            f"-{count}",
            f"--format={format_str}",
            "--shortstat",
        ]

        if author:
            args.append(f"--author={author}")
        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")
        if all_branches:
            args.append("--all")
        if branch:
            args.append(branch)
        if path:
            args.append("--")
            args.append(path)

        out, _, _ = await self.repo.run_git(*args)

        entries = []
        # Split by record separator marker (handles commit messages with blank lines)
        COMMIT_MARKER = "\x1e"
        commit_blocks = out.split(COMMIT_MARKER)

        for block in commit_blocks:
            if not block.strip():
                continue

            entry = self._parse_commit_block(block)
            if entry:
                entries.append(entry)

        return entries

    def _parse_commit_block(self, block: str) -> LogEntry | None:
        """Parse a commit block into LogEntry.

        Args:
            block: Raw commit block text

        Returns:
            LogEntry or None if parsing fails
        """
        # Split by NULL byte
        parts = block.split("\x00")
        if len(parts) < 6:
            return None

        # Parse commit info
        try:
            commit = GitCommit(
                hash=parts[0].strip(),
                short_hash=parts[1],
                author=parts[2],
                author_email=parts[3],
                date=parts[4],
                message=parts[5].strip(),
                parent_hashes=parts[7].split() if len(parts) > 7 and parts[7] else [],
            )
        except (IndexError, ValueError):
            return None

        # Parse stats from the block
        entry = LogEntry(commit=commit)
        self._parse_stats(block, entry)

        return entry

    def _parse_stats(self, block: str, entry: LogEntry) -> None:
        """Parse stat line from block.

        Args:
            block: Raw commit block
            entry: LogEntry to update
        """
        # Look for stat line pattern
        files_match = re.search(r"(\d+) files? changed", block)
        if files_match:
            entry.files_changed = int(files_match.group(1))

        insert_match = re.search(r"(\d+) insertions?\(\+\)", block)
        if insert_match:
            entry.insertions = int(insert_match.group(1))

        delete_match = re.search(r"(\d+) deletions?\(-\)", block)
        if delete_match:
            entry.deletions = int(delete_match.group(1))

    async def get_commit(self, ref: str) -> GitCommit:
        """Get single commit details.

        Args:
            ref: Commit reference (hash, branch, tag, etc.)

        Returns:
            GitCommit with full details

        Raises:
            GitError: If commit not found
        """
        format_str = "%H%n%h%n%an%n%ae%n%ai%n%B%n---PARENTS---%n%P"
        out, _, _ = await self.repo.run_git(
            "show", "-s", f"--format={format_str}", ref
        )

        lines = out.split("\n")
        if len(lines) < 6:
            raise GitError(f"Invalid commit: {ref}")

        # Find where parents section starts
        try:
            parents_idx = lines.index("---PARENTS---")
            message_lines = lines[5:parents_idx]
            parent_line = lines[parents_idx + 1] if parents_idx + 1 < len(lines) else ""
        except ValueError:
            message_lines = lines[5:]
            parent_line = ""

        return GitCommit(
            hash=lines[0],
            short_hash=lines[1],
            author=lines[2],
            author_email=lines[3],
            date=lines[4],
            message="\n".join(message_lines).strip(),
            parent_hashes=parent_line.split() if parent_line else [],
        )

    async def get_commit_files(self, ref: str) -> list[str]:
        """Get files changed in commit.

        Args:
            ref: Commit reference

        Returns:
            List of file paths
        """
        out, _, _ = await self.repo.run_git(
            "show", "--name-only", "--format=", ref
        )
        return [f for f in out.split("\n") if f.strip()]

    async def get_commit_diff(
        self,
        ref: str,
        path: str | None = None,
    ) -> str:
        """Get diff for commit.

        Args:
            ref: Commit reference
            path: Optional path filter

        Returns:
            Unified diff output
        """
        args = ["show", "--patch", ref]
        if path:
            args.extend(["--", path])

        out, _, _ = await self.repo.run_git(*args)
        return out

    async def get_recent_commits(self, count: int = 5) -> str:
        """Get formatted recent commits for context.

        Args:
            count: Number of commits

        Returns:
            Formatted commit list
        """
        entries = await self.get_log(count=count)

        lines = ["Recent commits:"]
        for entry in entries:
            lines.append(f"  {entry.commit.short_hash} {entry.commit.subject}")

        return "\n".join(lines)

    async def search_commits(
        self,
        query: str,
        count: int = 10,
    ) -> list[LogEntry]:
        """Search commits by message.

        Args:
            query: Search query
            count: Max results

        Returns:
            Matching log entries
        """
        format_str = "%H%x00%h%x00%an%x00%ae%x00%ai%x00%s%x00%b%x00%P%x00"

        args = [
            "log",
            f"-{count}",
            f"--format={format_str}",
            f"--grep={query}",
            "-i",  # Case insensitive
        ]

        out, _, _ = await self.repo.run_git(*args)

        entries = []
        for block in out.split("\x00\x00"):
            if not block.strip():
                continue
            entry = self._parse_commit_block(block)
            if entry:
                entries.append(entry)

        return entries
