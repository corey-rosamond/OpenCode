"""Git status operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from code_forge.core import get_logger

if TYPE_CHECKING:
    from .repository import GitRepository

logger = get_logger("git.status")


@dataclass
class FileStatus:
    """Status of a single file."""

    path: str
    status: str  # M, A, D, R, C, U, ?
    staged: bool
    original_path: str | None = None

    @property
    def status_name(self) -> str:
        """Human-readable status name."""
        names = {
            "M": "modified",
            "A": "added",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "U": "unmerged",
            "?": "untracked",
        }
        return names.get(self.status, "unknown")


@dataclass
class GitStatus:
    """Complete git status."""

    branch: str | None = None
    tracking: str | None = None
    ahead: int = 0
    behind: int = 0
    staged: list[FileStatus] = field(default_factory=list)
    unstaged: list[FileStatus] = field(default_factory=list)
    untracked: list[FileStatus] = field(default_factory=list)
    conflicts: list[FileStatus] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        return not (
            self.staged or self.unstaged or self.untracked or self.conflicts
        )

    @property
    def total_changes(self) -> int:
        """Total number of changed files."""
        return (
            len(self.staged)
            + len(self.unstaged)
            + len(self.untracked)
            + len(self.conflicts)
        )

    def to_string(self) -> str:
        """Format as human-readable string."""
        lines = []

        # Branch info
        if self.branch:
            branch_line = f"On branch {self.branch}"
            if self.tracking:
                if self.ahead and self.behind:
                    branch_line += f" (ahead {self.ahead}, behind {self.behind})"
                elif self.ahead:
                    branch_line += f" (ahead {self.ahead})"
                elif self.behind:
                    branch_line += f" (behind {self.behind})"
            lines.append(branch_line)
            lines.append("")

        # Staged changes
        if self.staged:
            lines.append("Changes to be committed:")
            for f in self.staged:
                lines.append(f"  {f.status_name}: {f.path}")
            lines.append("")

        # Unstaged changes
        if self.unstaged:
            lines.append("Changes not staged for commit:")
            for f in self.unstaged:
                lines.append(f"  {f.status_name}: {f.path}")
            lines.append("")

        # Untracked files
        if self.untracked:
            lines.append("Untracked files:")
            for f in self.untracked:
                lines.append(f"  {f.path}")
            lines.append("")

        # Conflicts
        if self.conflicts:
            lines.append("Unmerged paths:")
            for f in self.conflicts:
                lines.append(f"  {f.path}")
            lines.append("")

        if self.is_clean:
            lines.append("Nothing to commit, working tree clean")

        return "\n".join(lines)


class GitStatusTool:
    """Git status operations."""

    def __init__(self, repo: GitRepository) -> None:
        """Initialize status tool.

        Args:
            repo: Git repository instance
        """
        self.repo = repo

    async def get_status(self) -> GitStatus:
        """Get current git status."""
        # Get branch info
        branch_out, _, _ = await self.repo.run_git(
            "status", "-b", "--porcelain=v2"
        )

        status = GitStatus()

        # Parse porcelain v2 output
        for line in branch_out.split("\n"):
            if line.startswith("# branch.head "):
                status.branch = line.split(" ", 2)[2]
            elif line.startswith("# branch.upstream "):
                status.tracking = line.split(" ", 2)[2]
            elif line.startswith("# branch.ab "):
                parts = line.split(" ")
                for part in parts[2:]:
                    if part.startswith("+"):
                        status.ahead = int(part[1:])
                    elif part.startswith("-"):
                        status.behind = int(part[1:])
            elif line.startswith("1 ") or line.startswith("2 "):
                # Changed files
                self._parse_changed_file(line, status)
            elif line.startswith("? "):
                # Untracked file
                path = line[2:]
                status.untracked.append(
                    FileStatus(path=path, status="?", staged=False)
                )
            elif line.startswith("u "):
                # Unmerged file
                parts = line.split("\t")
                path = parts[-1] if parts else line[2:]
                status.conflicts.append(
                    FileStatus(path=path, status="U", staged=False)
                )

        return status

    def _parse_changed_file(self, line: str, status: GitStatus) -> None:
        """Parse a changed file line from porcelain v2.

        Args:
            line: Line from git status --porcelain=v2
            status: GitStatus to update
        """
        parts = line.split(" ", 8)
        if len(parts) < 9:
            # Log unexpected format - could indicate git porcelain format changed
            logger.warning(
                "Unexpected git status line format (expected 9 parts, got %d): %s",
                len(parts),
                line[:100],  # Truncate for safety
            )
            return

        xy = parts[1]
        # The path is the last field, may contain tabs for renames
        path_part = parts[8]

        original_path = None

        # For type 2 (renames/copies), the format includes score: "R100 path\torigPath"
        # Strip the score prefix (e.g., "R100 " or "C075 ")
        if (
            line.startswith("2 ")
            and path_part
            and len(path_part) > 4
            and path_part[0] in ("R", "C")
        ):
            # Find the space after the score
            space_idx = path_part.find(" ")
            if space_idx > 0:
                path_part = path_part[space_idx + 1 :]

        # Handle renames which have format: new_path\told_path
        if "\t" in path_part:
            path_parts = path_part.split("\t")
            path = path_parts[0]
            original_path = path_parts[1] if len(path_parts) > 1 else None
        else:
            path = path_part

        # Check staged changes (index vs HEAD)
        if xy[0] != ".":
            status.staged.append(
                FileStatus(
                    path=path,
                    status=xy[0],
                    staged=True,
                    original_path=original_path,
                )
            )

        # Check unstaged changes (worktree vs index)
        if xy[1] != ".":
            status.unstaged.append(
                FileStatus(path=path, status=xy[1], staged=False)
            )

    async def get_staged_diff(self) -> str:
        """Get diff of staged changes."""
        out, _, _ = await self.repo.run_git("diff", "--cached")
        return out

    async def get_unstaged_diff(self) -> str:
        """Get diff of unstaged changes."""
        out, _, _ = await self.repo.run_git("diff")
        return out

    async def get_short_status(self) -> str:
        """Get short status summary."""
        status = await self.get_status()

        parts = []
        if status.staged:
            parts.append(f"{len(status.staged)} staged")
        if status.unstaged:
            parts.append(f"{len(status.unstaged)} modified")
        if status.untracked:
            parts.append(f"{len(status.untracked)} untracked")

        if not parts:
            return "clean"
        return ", ".join(parts)
