"""Tests for git operations module."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from code_forge.git.operations import GitOperations, UnsafeOperationError
from code_forge.git.repository import GitCommit, GitError, GitRepository
from code_forge.git.safety import SafetyCheck


class TestGitOperations:
    """Tests for GitOperations class."""

    @pytest.fixture
    def mock_repo(self) -> GitRepository:
        """Create mock repository."""
        repo = GitRepository("/project")
        repo._root = "/project"
        repo._is_git_repo = True
        repo._current_branch_cache = "main"
        return repo

    @pytest.fixture
    def ops(self, mock_repo: GitRepository) -> GitOperations:
        """Create GitOperations instance."""
        return GitOperations(mock_repo)

    # === Staging Tests ===

    @pytest.mark.asyncio
    async def test_stage_files(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test staging files."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.stage(["file1.py", "file2.py"])

        assert "add" in calls[0]
        assert "file1.py" in calls[0]
        assert "file2.py" in calls[0]

    @pytest.mark.asyncio
    async def test_stage_empty_list(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test staging with empty list."""
        with patch.object(mock_repo, "run_git") as mock:
            await ops.stage([])
            mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_unstage_files(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test unstaging files."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.unstage(["file1.py"])

        assert "restore" in calls[0]
        assert "--staged" in calls[0]

    @pytest.mark.asyncio
    async def test_unstage_empty_list(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test unstaging with empty list."""
        with patch.object(mock_repo, "run_git") as mock:
            await ops.unstage([])
            mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_stage_all(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test staging all changes."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.stage_all()

        assert "add" in calls[0]
        assert "-A" in calls[0]

    @pytest.mark.asyncio
    async def test_discard_changes(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test discarding changes."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.discard(["file.py"])

        assert "restore" in calls[0]
        assert "file.py" in calls[0]

    # === Commit Tests ===

    @pytest.mark.asyncio
    async def test_commit_success(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test successful commit."""
        call_count = [0]

        async def mock_run_git(*args, **kwargs):
            call_count[0] += 1
            if "commit" in args:
                return ("", "", 0)
            elif "log" in args:
                return ("abc123\nabc\nAuthor\nauth@test.com\n2024-01-01\nTest", "", 0)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            commit = await ops.commit("feat: Test commit")

        assert commit.short_hash == "abc"
        assert commit.message == "feat: Test commit"

    @pytest.mark.asyncio
    async def test_commit_empty_message(self, ops: GitOperations) -> None:
        """Test commit with empty message."""
        with pytest.raises(GitError, match="empty"):
            await ops.commit("")

    @pytest.mark.asyncio
    async def test_commit_amend_safe(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test amend when safe."""
        async def mock_run_git(*args, **kwargs):
            if "branch" in args and "-r" in args:
                return ("", "", 0)  # Not pushed
            elif "log" in args:
                return ("abc123\nabc\nAuthor\nauth@test.com\n2024-01-01\nTest", "", 0)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            commit = await ops.commit("fix: Amend commit", amend=True)

        assert isinstance(commit, GitCommit)
        assert commit.hash == "abc123"

    @pytest.mark.asyncio
    async def test_commit_amend_unsafe(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test amend when unsafe (pushed)."""
        async def mock_run_git(*args, **kwargs):
            if "rev-parse" in args:
                return ("abc123", "", 0)
            elif "branch" in args and "-r" in args:
                return ("origin/main", "", 0)  # Is pushed
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            with pytest.raises(UnsafeOperationError, match="amend"):
                await ops.commit("fix: Amend", amend=True)

    @pytest.mark.asyncio
    async def test_commit_allow_empty(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test commit with allow_empty."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            if "log" in args:
                return ("abc\nabc\nA\na@t.com\n2024\nTest", "", 0)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.commit("chore: Empty commit", allow_empty=True)

        assert any("--allow-empty" in c for c in calls)

    # === Branch Tests ===

    @pytest.mark.asyncio
    async def test_create_branch(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test creating branch."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            branch = await ops.create_branch("feature-new")

        assert branch.name == "feature-new"
        assert "branch" in calls[0]
        assert "feature-new" in calls[0]

    @pytest.mark.asyncio
    async def test_create_branch_from_point(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test creating branch from start point."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.create_branch("hotfix", start_point="abc123")

        assert "abc123" in calls[0]

    @pytest.mark.asyncio
    async def test_switch_branch(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test switching branch."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.switch_branch("develop")

        assert "switch" in calls[-1]
        assert "develop" in calls[-1]

    @pytest.mark.asyncio
    async def test_checkout(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test checkout."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.checkout("feature")

        assert "checkout" in calls[-1]

    @pytest.mark.asyncio
    async def test_checkout_create(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test checkout with create."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.checkout("new-branch", create=True)

        assert any("-b" in c for c in calls)

    @pytest.mark.asyncio
    async def test_delete_branch(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test deleting branch."""
        mock_repo._current_branch_cache = "main"
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("main\nfeature", "", 0)  # feature is merged

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.delete_branch("feature")

        assert any("-d" in c for c in calls)

    @pytest.mark.asyncio
    async def test_delete_branch_force(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test force deleting branch."""
        mock_repo._current_branch_cache = "main"
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("main", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.delete_branch("feature", force=True)

        assert any("-D" in c for c in calls)

    @pytest.mark.asyncio
    async def test_delete_branch_protected(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test deleting protected branch."""
        mock_repo._current_branch_cache = "feature"

        with pytest.raises(UnsafeOperationError, match="protected"):
            await ops.delete_branch("main")

    # === Remote Tests ===

    @pytest.mark.asyncio
    async def test_fetch(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test fetch."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.fetch()

        assert "fetch" in calls[0]
        assert "origin" in calls[0]

    @pytest.mark.asyncio
    async def test_fetch_with_prune(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test fetch with prune."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.fetch(prune=True)

        assert "--prune" in calls[0]

    @pytest.mark.asyncio
    async def test_pull(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test pull."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.pull()

        assert "pull" in calls[0]

    @pytest.mark.asyncio
    async def test_pull_rebase(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test pull with rebase."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.pull(rebase=True)

        assert "--rebase" in calls[0]

    @pytest.mark.asyncio
    async def test_push(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test push."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.push()

        assert "push" in calls[0]

    @pytest.mark.asyncio
    async def test_push_set_upstream(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test push with set upstream."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.push(set_upstream=True)

        assert "-u" in calls[0]

    @pytest.mark.asyncio
    async def test_push_force_with_lease(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test push with force-with-lease."""
        mock_repo._current_branch_cache = "feature"
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.push(force_with_lease=True)

        assert "--force-with-lease" in calls[0]

    @pytest.mark.asyncio
    async def test_push_force_protected(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test force push to protected branch."""
        mock_repo._current_branch_cache = "main"

        with pytest.raises(UnsafeOperationError, match="force push"):
            await ops.push(force=True)

    # === Stash Tests ===

    @pytest.mark.asyncio
    async def test_stash(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test stash."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.stash()

        assert "stash" in calls[0]
        assert "push" in calls[0]

    @pytest.mark.asyncio
    async def test_stash_with_message(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test stash with message."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.stash(message="WIP: feature")

        assert "-m" in calls[0]
        assert "WIP: feature" in calls[0]

    @pytest.mark.asyncio
    async def test_stash_pop(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test stash pop."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.stash_pop()

        assert "stash" in calls[0]
        assert "pop" in calls[0]

    @pytest.mark.asyncio
    async def test_stash_list(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test stash list."""
        async def mock_run_git(*args, **kwargs):
            return ("stash@{0}: WIP\nstash@{1}: Feature", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            stashes = await ops.stash_list()

        assert len(stashes) == 2

    @pytest.mark.asyncio
    async def test_stash_list_empty(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test stash list when empty."""
        async def mock_run_git(*args, **kwargs):
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            stashes = await ops.stash_list()

        assert stashes == []

    @pytest.mark.asyncio
    async def test_stash_drop(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test stash drop."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.stash_drop(index=1)

        assert "drop" in calls[0]
        assert "stash@{1}" in calls[0]

    # === Tag Tests ===

    @pytest.mark.asyncio
    async def test_create_tag(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test creating tag."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.create_tag("v1.0.0")

        assert "tag" in calls[0]
        assert "v1.0.0" in calls[0]

    @pytest.mark.asyncio
    async def test_create_annotated_tag(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test creating annotated tag."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.create_tag("v1.0.0", message="Release 1.0.0")

        assert "-a" in calls[0]
        assert "-m" in calls[0]

    @pytest.mark.asyncio
    async def test_delete_tag(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test deleting tag."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.delete_tag("v1.0.0")

        assert "tag" in calls[0]
        assert "-d" in calls[0]

    @pytest.mark.asyncio
    async def test_list_tags(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test listing tags."""
        async def mock_run_git(*args, **kwargs):
            return ("v1.0.0\nv1.1.0\nv2.0.0", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            tags = await ops.list_tags()

        assert len(tags) == 3
        assert "v1.0.0" in tags

    # === Reset Tests ===

    @pytest.mark.asyncio
    async def test_reset_soft(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test soft reset."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.reset_soft("HEAD~1")

        assert "reset" in calls[0]
        assert "--soft" in calls[0]

    @pytest.mark.asyncio
    async def test_reset_mixed(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test mixed reset."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.reset_mixed()

        assert "reset" in calls[0]
        assert "--mixed" in calls[0]

    @pytest.mark.asyncio
    async def test_reset_hard_safe(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test hard reset when safe."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)  # Clean status

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.reset_hard()

        assert any("--hard" in c for c in calls)

    @pytest.mark.asyncio
    async def test_reset_hard_unsafe(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test hard reset with uncommitted changes."""
        async def mock_run_git(*args, **kwargs):
            return (" M file.py", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            with pytest.raises(UnsafeOperationError, match="hard reset"):
                await ops.reset_hard()

    # === Clean Tests ===

    @pytest.mark.asyncio
    async def test_clean(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test clean."""
        async def mock_run_git(*args, **kwargs):
            return ("Removing file1.py\nRemoving dir/", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            files = await ops.clean()

        assert len(files) == 2

    @pytest.mark.asyncio
    async def test_clean_dry_run(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test clean dry run."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("Would remove file.py", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            files = await ops.clean(dry_run=True)

        assert "-n" in calls[0]
        assert "-f" not in calls[0]

    @pytest.mark.asyncio
    async def test_clean_directories(self, ops: GitOperations, mock_repo: GitRepository) -> None:
        """Test clean with directories."""
        calls = []

        async def mock_run_git(*args, **kwargs):
            calls.append(args)
            return ("", "", 0)

        with patch.object(mock_repo, "run_git", side_effect=mock_run_git):
            await ops.clean(directories=True)

        assert "-d" in calls[0]
