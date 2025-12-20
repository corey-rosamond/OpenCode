"""Tests for git repository module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge.git.repository import (
    GitBranch,
    GitCommit,
    GitError,
    GitRemote,
    GitRepository,
    RepositoryInfo,
)


class TestGitRemote:
    """Tests for GitRemote dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic remote creation."""
        remote = GitRemote(name="origin", url="https://github.com/user/repo.git")
        assert remote.name == "origin"
        assert remote.url == "https://github.com/user/repo.git"
        assert remote.fetch_url is None
        assert remote.push_url is None

    def test_full_creation(self) -> None:
        """Test full remote creation."""
        remote = GitRemote(
            name="origin",
            url="https://github.com/user/repo.git",
            fetch_url="https://github.com/user/repo.git",
            push_url="git@github.com:user/repo.git",
        )
        assert remote.fetch_url == "https://github.com/user/repo.git"
        assert remote.push_url == "git@github.com:user/repo.git"


class TestGitBranch:
    """Tests for GitBranch dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic branch creation."""
        branch = GitBranch(name="main")
        assert branch.name == "main"
        assert branch.is_current is False
        assert branch.tracking is None
        assert branch.ahead == 0
        assert branch.behind == 0
        assert branch.commit is None

    def test_current_branch(self) -> None:
        """Test current branch flag."""
        branch = GitBranch(name="feature", is_current=True)
        assert branch.is_current is True

    def test_tracking_branch(self) -> None:
        """Test tracking branch info."""
        branch = GitBranch(
            name="main",
            tracking="origin/main",
            ahead=2,
            behind=1,
        )
        assert branch.tracking == "origin/main"
        assert branch.ahead == 2
        assert branch.behind == 1


class TestGitCommit:
    """Tests for GitCommit dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic commit creation."""
        commit = GitCommit(
            hash="abc123def456",
            short_hash="abc123",
            author="Test Author",
            author_email="test@example.com",
            date="2024-01-15 10:30:00 +0000",
            message="Test commit message",
        )
        assert commit.hash == "abc123def456"
        assert commit.short_hash == "abc123"
        assert commit.author == "Test Author"
        assert commit.author_email == "test@example.com"
        assert commit.date == "2024-01-15 10:30:00 +0000"
        assert commit.message == "Test commit message"
        assert commit.parent_hashes == []

    def test_subject_single_line(self) -> None:
        """Test subject extraction from single-line message."""
        commit = GitCommit(
            hash="abc",
            short_hash="abc",
            author="",
            author_email="",
            date="",
            message="Single line message",
        )
        assert commit.subject == "Single line message"

    def test_subject_multiline(self) -> None:
        """Test subject extraction from multi-line message."""
        commit = GitCommit(
            hash="abc",
            short_hash="abc",
            author="",
            author_email="",
            date="",
            message="Subject line\n\nBody paragraph here.",
        )
        assert commit.subject == "Subject line"

    def test_parent_hashes(self) -> None:
        """Test parent hashes."""
        commit = GitCommit(
            hash="abc",
            short_hash="abc",
            author="",
            author_email="",
            date="",
            message="Merge commit",
            parent_hashes=["def456", "ghi789"],
        )
        assert len(commit.parent_hashes) == 2


class TestRepositoryInfo:
    """Tests for RepositoryInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic info creation."""
        info = RepositoryInfo(
            root=Path("/project"),
            is_git_repo=True,
            current_branch="main",
            head_commit=None,
            is_dirty=False,
        )
        assert info.root == Path("/project")
        assert info.is_git_repo is True
        assert info.current_branch == "main"
        assert info.head_commit is None
        assert info.is_dirty is False
        assert info.remotes == []

    def test_with_commit_and_remotes(self) -> None:
        """Test info with commit and remotes."""
        commit = GitCommit(
            hash="abc",
            short_hash="abc",
            author="Test",
            author_email="test@test.com",
            date="2024-01-01",
            message="Test",
        )
        remote = GitRemote(name="origin", url="https://github.com/test/repo")

        info = RepositoryInfo(
            root=Path("/project"),
            is_git_repo=True,
            current_branch="main",
            head_commit=commit,
            is_dirty=True,
            remotes=[remote],
        )
        assert isinstance(info.head_commit, CommitInfo)
        assert info.head_commit.sha == "abc123"
        assert len(info.remotes) == 1


class TestGitError:
    """Tests for GitError exception."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = GitError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.returncode == 1
        assert error.stderr == ""

    def test_error_with_details(self) -> None:
        """Test error with returncode and stderr."""
        error = GitError("Command failed", returncode=128, stderr="fatal: not a git repository")
        assert error.returncode == 128
        assert error.stderr == "fatal: not a git repository"


class TestGitRepository:
    """Tests for GitRepository class."""

    def test_init_default_path(self) -> None:
        """Test initialization with default path."""
        with patch.object(Path, "cwd", return_value=Path("/current")):
            repo = GitRepository()
            assert repo._path == Path("/current")

    def test_init_with_path(self) -> None:
        """Test initialization with explicit path."""
        repo = GitRepository("/project")
        assert repo._path == Path("/project")

    def test_init_with_path_object(self) -> None:
        """Test initialization with Path object."""
        repo = GitRepository(Path("/project"))
        assert repo._path == Path("/project")

    def test_invalidate_cache(self) -> None:
        """Test cache invalidation."""
        repo = GitRepository("/project")
        repo._current_branch_cache = "main"
        repo._dirty_cache = True

        repo.invalidate_cache()

        assert repo._current_branch_cache is None
        assert repo._dirty_cache is None

    def test_is_git_repo_true(self) -> None:
        """Test is_git_repo when in a repo."""
        repo = GitRepository("/project")
        with patch.object(repo, "_run_git_sync", return_value=".git"):
            assert repo.is_git_repo is True

    def test_is_git_repo_false(self) -> None:
        """Test is_git_repo when not in a repo."""
        repo = GitRepository("/project")
        with patch.object(repo, "_run_git_sync", return_value=""):
            assert repo.is_git_repo is False

    def test_is_git_repo_cached(self) -> None:
        """Test is_git_repo caching."""
        repo = GitRepository("/project")
        repo._is_git_repo = True

        # Should not call _run_git_sync
        with patch.object(repo, "_run_git_sync") as mock:
            assert repo.is_git_repo is True
            mock.assert_not_called()

    def test_root_property(self) -> None:
        """Test root property."""
        repo = GitRepository("/project/src")
        repo._is_git_repo = True
        with patch.object(repo, "_run_git_sync", return_value="/project"):
            assert repo.root == Path("/project")

    def test_root_not_git_repo(self) -> None:
        """Test root property when not a git repo."""
        repo = GitRepository("/project")
        repo._is_git_repo = False
        with pytest.raises(GitError, match="Not a git repository"):
            _ = repo.root

    def test_current_branch(self) -> None:
        """Test current_branch property."""
        repo = GitRepository("/project")
        repo._is_git_repo = True
        with patch.object(repo, "_run_git_sync", return_value="main"):
            assert repo.current_branch == "main"

    def test_current_branch_not_repo(self) -> None:
        """Test current_branch when not a repo."""
        repo = GitRepository("/project")
        repo._is_git_repo = False
        assert repo.current_branch is None

    def test_current_branch_detached(self) -> None:
        """Test current_branch in detached HEAD state."""
        repo = GitRepository("/project")
        repo._is_git_repo = True
        with patch.object(repo, "_run_git_sync", return_value=""):
            assert repo.current_branch is None

    def test_is_dirty_true(self) -> None:
        """Test is_dirty when dirty."""
        repo = GitRepository("/project")
        repo._is_git_repo = True
        with patch.object(repo, "_run_git_sync", return_value=" M file.py"):
            assert repo.is_dirty is True

    def test_is_dirty_false(self) -> None:
        """Test is_dirty when clean."""
        repo = GitRepository("/project")
        repo._is_git_repo = True
        with patch.object(repo, "_run_git_sync", return_value=""):
            assert repo.is_dirty is False

    def test_is_dirty_not_repo(self) -> None:
        """Test is_dirty when not a repo."""
        repo = GitRepository("/project")
        repo._is_git_repo = False
        assert repo.is_dirty is False

    @pytest.mark.asyncio
    async def test_run_git_success(self) -> None:
        """Test run_git with successful command."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            stdout, stderr, code = await repo.run_git("status")
            assert stdout == "output"
            assert stderr == ""
            assert code == 0

    @pytest.mark.asyncio
    async def test_run_git_failure(self) -> None:
        """Test run_git with failed command."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error message"))
        mock_proc.returncode = 128

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(GitError) as exc_info:
                await repo.run_git("invalid")
            assert exc_info.value.returncode == 128

    @pytest.mark.asyncio
    async def test_run_git_no_check(self) -> None:
        """Test run_git with check=False."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"warning"))
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            stdout, stderr, code = await repo.run_git("status", check=False)
            assert code == 1
            assert stderr == "warning"

    def test_run_git_sync_success(self) -> None:
        """Test _run_git_sync success."""
        repo = GitRepository("/project")

        result = MagicMock()
        result.stdout = "output\n"

        with patch("subprocess.run", return_value=result):
            output = repo._run_git_sync("status")
            assert output == "output"

    def test_run_git_sync_error(self) -> None:
        """Test _run_git_sync error handling."""
        repo = GitRepository("/project")

        with patch("subprocess.run", side_effect=subprocess.SubprocessError):
            output = repo._run_git_sync("status")
            assert output == ""

    @pytest.mark.asyncio
    async def test_get_info_not_repo(self) -> None:
        """Test get_info when not a repo."""
        repo = GitRepository("/project")
        repo._is_git_repo = False

        info = await repo.get_info()

        assert info.is_git_repo is False
        assert info.current_branch is None
        assert info.head_commit is None

    @pytest.mark.asyncio
    async def test_get_info_success(self) -> None:
        """Test get_info success."""
        repo = GitRepository("/project")
        repo._is_git_repo = True
        repo._root = Path("/project")

        async def mock_run_git(*args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "branch":
                return ("main", "", 0)
            elif cmd == "log":
                return ("abc123\nabc\nAuthor\nauthor@test.com\n2024-01-01\nTest\nparent1", "", 0)
            elif cmd == "status":
                return ("", "", 0)
            elif cmd == "remote":
                return ("origin\thttps://github.com/test/repo (fetch)\norigin\thttps://github.com/test/repo (push)", "", 0)
            return ("", "", 0)

        with patch.object(repo, "run_git", side_effect=mock_run_git):
            info = await repo.get_info()

        assert info.is_git_repo is True
        assert info.current_branch == "main"
        assert info.is_dirty is False

    @pytest.mark.asyncio
    async def test_get_remotes(self) -> None:
        """Test get_remotes."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        async def mock_run_git(*args, **kwargs):
            return (
                "origin\thttps://github.com/user/repo.git (fetch)\n"
                "origin\tgit@github.com:user/repo.git (push)\n"
                "upstream\thttps://github.com/upstream/repo.git (fetch)\n"
                "upstream\thttps://github.com/upstream/repo.git (push)",
                "",
                0,
            )

        with patch.object(repo, "run_git", side_effect=mock_run_git):
            remotes = await repo.get_remotes()

        assert len(remotes) == 2
        origin = next(r for r in remotes if r.name == "origin")
        assert origin.fetch_url == "https://github.com/user/repo.git"
        assert origin.push_url == "git@github.com:user/repo.git"

    @pytest.mark.asyncio
    async def test_get_remotes_empty(self) -> None:
        """Test get_remotes with no remotes."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        with patch.object(repo, "run_git", return_value=("", "", 0)):
            remotes = await repo.get_remotes()
            assert remotes == []

    @pytest.mark.asyncio
    async def test_get_branches(self) -> None:
        """Test get_branches."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        async def mock_run_git(*args, **kwargs):
            return (
                "* main abc123 Latest commit\n"
                "  feature def456 Feature work\n"
                "  develop ghi789 Development",
                "",
                0,
            )

        with patch.object(repo, "run_git", side_effect=mock_run_git):
            branches = await repo.get_branches()

        assert len(branches) == 3
        main = next(b for b in branches if b.name == "main")
        assert main.is_current is True
        assert main.commit == "abc123"

    @pytest.mark.asyncio
    async def test_get_branches_all(self) -> None:
        """Test get_branches with all=True."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        calls = []
        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("* main abc123 Latest", "", 0)

        with patch.object(repo, "run_git", side_effect=mock_run_git):
            await repo.get_branches(all=True)

        assert "-a" in calls[0]

    @pytest.mark.asyncio
    async def test_get_branches_remote(self) -> None:
        """Test get_branches with remote=True."""
        repo = GitRepository("/project")
        repo._root = Path("/project")

        calls = []
        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("  origin/main abc123 Latest", "", 0)

        with patch.object(repo, "run_git", side_effect=mock_run_git):
            await repo.get_branches(remote=True)

        assert "-r" in calls[0]
