"""Git diff operations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository import GitRepository


@dataclass
class DiffFile:
    """Diff for a single file."""

    path: str
    old_path: str | None = None
    status: str = "M"  # A, M, D, R
    additions: int = 0
    deletions: int = 0
    content: str | None = None

    @property
    def is_rename(self) -> bool:
        """Check if this is a rename."""
        return self.status == "R" and self.old_path is not None


@dataclass
class GitDiff:
    """Complete diff result."""

    files: list[DiffFile] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    stat: str = ""

    @property
    def total_files(self) -> int:
        """Total number of files."""
        return len(self.files)

    def to_string(self, include_content: bool = True) -> str:
        """Format as string.

        Args:
            include_content: Include diff content

        Returns:
            Formatted diff string
        """
        lines = []

        # Summary
        if self.stat:
            lines.append(self.stat)
            lines.append("")

        if include_content:
            for file in self.files:
                if file.content:
                    lines.append(file.content)
                    lines.append("")

        return "\n".join(lines)

    def get_stat_summary(self) -> str:
        """Get short stat summary."""
        return (
            f"{self.total_files} file(s) changed, "
            f"{self.total_additions} insertion(s)(+), "
            f"{self.total_deletions} deletion(s)(-)"
        )


class GitDiffTool:
    """Git diff operations."""

    def __init__(self, repo: GitRepository) -> None:
        """Initialize diff tool.

        Args:
            repo: Git repository instance
        """
        self.repo = repo

    async def diff_working(
        self,
        path: str | None = None,
        staged: bool = False,
        context_lines: int = 3,
    ) -> GitDiff:
        """Diff working tree vs HEAD.

        Args:
            path: Filter by path
            staged: Diff staged changes only
            context_lines: Number of context lines

        Returns:
            GitDiff result
        """
        args = ["diff", f"-U{context_lines}"]
        if staged:
            args.append("--cached")
        if path:
            args.extend(["--", path])

        return await self._run_diff(args)

    async def diff_commits(
        self,
        from_ref: str,
        to_ref: str,
        path: str | None = None,
    ) -> GitDiff:
        """Diff between commits.

        Args:
            from_ref: Start commit
            to_ref: End commit
            path: Filter by path

        Returns:
            GitDiff result
        """
        args = ["diff", from_ref, to_ref]
        if path:
            args.extend(["--", path])

        return await self._run_diff(args)

    async def diff_branches(
        self,
        from_branch: str,
        to_branch: str,
    ) -> GitDiff:
        """Diff between branches.

        Args:
            from_branch: Source branch
            to_branch: Target branch

        Returns:
            GitDiff result
        """
        return await self.diff_commits(from_branch, to_branch)

    async def get_stat(
        self,
        from_ref: str = "HEAD",
        to_ref: str | None = None,
    ) -> str:
        """Get diff stat.

        Args:
            from_ref: Start reference
            to_ref: End reference (working tree if None)

        Returns:
            Stat output
        """
        args = ["diff", "--stat", from_ref]
        if to_ref:
            args.append(to_ref)

        out, _, _ = await self.repo.run_git(*args)
        return out

    async def get_name_only(
        self,
        from_ref: str = "HEAD",
        to_ref: str | None = None,
    ) -> list[str]:
        """Get list of changed file names.

        Args:
            from_ref: Start reference
            to_ref: End reference (working tree if None)

        Returns:
            List of file paths
        """
        args = ["diff", "--name-only", from_ref]
        if to_ref:
            args.append(to_ref)

        out, _, _ = await self.repo.run_git(*args)
        return [f for f in out.split("\n") if f.strip()]

    async def get_name_status(
        self,
        from_ref: str = "HEAD",
        to_ref: str | None = None,
    ) -> list[tuple[str, str]]:
        """Get list of changed files with status.

        Args:
            from_ref: Start reference
            to_ref: End reference (working tree if None)

        Returns:
            List of (status, path) tuples
        """
        args = ["diff", "--name-status", from_ref]
        if to_ref:
            args.append(to_ref)

        out, _, _ = await self.repo.run_git(*args)
        result = []
        for line in out.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                result.append((parts[0], parts[1]))
        return result

    async def _run_diff(self, args: list[str]) -> GitDiff:
        """Run diff command and parse output.

        Args:
            args: Git diff arguments

        Returns:
            Parsed GitDiff
        """
        # Get stat
        stat_args = args.copy()
        stat_args.insert(1, "--stat")
        stat_out, _, _ = await self.repo.run_git(*stat_args)

        # Get full diff
        diff_out, _, _ = await self.repo.run_git(*args)

        # Parse results
        diff = GitDiff(stat=stat_out)
        self._parse_stat(stat_out, diff)
        self._parse_diff_content(diff_out, diff)

        return diff

    def _parse_stat(self, stat: str, diff: GitDiff) -> None:
        """Parse stat output.

        Args:
            stat: Raw stat output
            diff: GitDiff to update
        """
        # Regex for partial renames like: dir/{old => new}/file or prefix/{old.txt => new.txt}
        PARTIAL_RENAME_PATTERN = re.compile(
            r"^(.*)?\{([^}]*) => ([^}]*)\}(.*)$"
        )
        # Regex for simple renames like: old.txt => new.txt
        SIMPLE_RENAME_PATTERN = re.compile(r"^(.+) => (.+)$")

        for line in stat.split("\n"):
            # Match file stat line: " path | N +++ ---"
            match = re.match(r"\s*(.+?)\s*\|\s*(\d+)", line)
            if match:
                path = match.group(1).strip()
                # Handle renames: "old => new"
                if " => " in path:
                    # Try partial rename pattern first (dir/{old => new}/file)
                    partial_match = PARTIAL_RENAME_PATTERN.match(path)
                    if partial_match:
                        prefix = partial_match.group(1) or ""
                        new_part = partial_match.group(3)
                        suffix = partial_match.group(4) or ""
                        path = prefix + new_part + suffix
                    else:
                        # Try simple rename pattern (old => new)
                        simple_match = SIMPLE_RENAME_PATTERN.match(path)
                        if simple_match:
                            path = simple_match.group(2)

                # Find or create file entry
                file_entry = None
                for f in diff.files:
                    if f.path == path:
                        file_entry = f
                        break
                if not file_entry:
                    file_entry = DiffFile(path=path)
                    diff.files.append(file_entry)

            # Match summary line
            summary = re.search(
                r"(\d+) insertions?\(\+\).*?(\d+) deletions?\(-\)",
                line,
            )
            if summary:
                diff.total_additions = int(summary.group(1))
                diff.total_deletions = int(summary.group(2))
            else:
                # Try matching just insertions or just deletions
                insert_only = re.search(r"(\d+) insertions?\(\+\)", line)
                delete_only = re.search(r"(\d+) deletions?\(-\)", line)
                if insert_only:
                    diff.total_additions = int(insert_only.group(1))
                if delete_only:
                    diff.total_deletions = int(delete_only.group(1))

    def _parse_diff_content(self, content: str, diff: GitDiff) -> None:
        """Parse diff content and attach to files.

        Args:
            content: Raw diff output
            diff: GitDiff to update
        """
        current_file: DiffFile | None = None
        current_content: list[str] = []

        for line in content.split("\n"):
            if line.startswith("diff --git"):
                # Save previous file content
                if current_file and current_content:
                    current_file.content = "\n".join(current_content)

                # Extract file path
                match = re.search(r"diff --git a/(.+) b/(.+)", line)
                if match:
                    old_path = match.group(1)
                    new_path = match.group(2)

                    # Find existing entry or create new
                    current_file = None
                    for f in diff.files:
                        if f.path == new_path:
                            current_file = f
                            break
                    if not current_file:
                        current_file = DiffFile(path=new_path)
                        diff.files.append(current_file)

                    if old_path != new_path:
                        current_file.old_path = old_path
                        current_file.status = "R"

                    current_content = [line]
            elif line.startswith("new file"):
                if current_file:
                    current_file.status = "A"
                current_content.append(line)
            elif line.startswith("deleted file"):
                if current_file:
                    current_file.status = "D"
                current_content.append(line)
            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    current_file.additions += 1
                current_content.append(line)
            elif line.startswith("-") and not line.startswith("---"):
                if current_file:
                    current_file.deletions += 1
                current_content.append(line)
            else:
                current_content.append(line)

        # Save last file
        if current_file and current_content:
            current_file.content = "\n".join(current_content)
