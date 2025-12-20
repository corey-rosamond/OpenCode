"""Tests for GitHub pull request service."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from code_forge.github.pull_requests import (
    GitHubPullRequest,
    GitHubReview,
    GitHubReviewComment,
    GitHubCheckRun,
    GitHubPRFile,
    PullRequestService,
)
from code_forge.github.client import GitHubClient


class TestGitHubPullRequest:
    """Tests for GitHubPullRequest dataclass."""

    def test_from_api(self, sample_pr_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        pr = GitHubPullRequest.from_api(sample_pr_data)

        assert pr.number == 123
        assert pr.title == "Test PR"
        assert pr.state == "open"
        assert pr.draft is False
        assert pr.merged is False
        assert pr.mergeable is True
        assert pr.author.login == "testuser"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.additions == 100
        assert pr.deletions == 50
        assert pr.changed_files == 5

    def test_from_api_draft(self, sample_pr_data: dict[str, Any]) -> None:
        """Test creating draft PR."""
        data = {**sample_pr_data, "draft": True}
        pr = GitHubPullRequest.from_api(data)

        assert pr.draft is True

    def test_from_api_merged(
        self,
        sample_pr_data: dict[str, Any],
        sample_user_data: dict[str, Any],
    ) -> None:
        """Test creating merged PR."""
        data = {
            **sample_pr_data,
            "merged": True,
            "merged_at": "2024-01-02T00:00:00Z",
            "merged_by": sample_user_data,
        }
        pr = GitHubPullRequest.from_api(data)

        assert pr.merged is True
        assert pr.merged_at == "2024-01-02T00:00:00Z"
        assert pr.merged_by.login == "testuser"

    def test_from_api_no_head_repo(self, sample_pr_data: dict[str, Any]) -> None:
        """Test PR without head repo (deleted fork)."""
        data = {**sample_pr_data}
        data["head"] = {"ref": "feature", "sha": "abc123", "repo": None}
        pr = GitHubPullRequest.from_api(data)

        assert pr.head_repo is None


class TestGitHubReview:
    """Tests for GitHubReview dataclass."""

    def test_from_api(self, sample_review_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        review = GitHubReview.from_api(sample_review_data)

        assert review.id == 456
        assert review.body == "LGTM!"
        assert review.state == "APPROVED"
        assert review.author.login == "testuser"


class TestGitHubReviewComment:
    """Tests for GitHubReviewComment dataclass."""

    def test_from_api(self, sample_review_comment_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        comment = GitHubReviewComment.from_api(sample_review_comment_data)

        assert comment.id == 789
        assert comment.body == "Consider changing this"
        assert comment.path == "src/main.py"
        assert comment.line == 15


class TestGitHubCheckRun:
    """Tests for GitHubCheckRun dataclass."""

    def test_from_api(self, sample_check_run_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        check = GitHubCheckRun.from_api(sample_check_run_data)

        assert check.id == 999
        assert check.name == "CI"
        assert check.status == "completed"
        assert check.conclusion == "success"
        assert check.app_name == "GitHub Actions"

    def test_from_api_no_app(self, sample_check_run_data: dict[str, Any]) -> None:
        """Test check run without app."""
        data = {**sample_check_run_data}
        del data["app"]
        check = GitHubCheckRun.from_api(data)

        assert check.app_name is None


class TestGitHubPRFile:
    """Tests for GitHubPRFile dataclass."""

    def test_from_api(self, sample_pr_file_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        file = GitHubPRFile.from_api(sample_pr_file_data)

        assert file.filename == "src/main.py"
        assert file.status == "modified"
        assert file.additions == 10
        assert file.deletions == 5
        assert isinstance(file.patch, str)
        assert len(file.patch) > 0


class TestPullRequestService:
    """Tests for PullRequestService class."""

    @pytest.mark.asyncio
    async def test_list(
        self,
        pr_service: PullRequestService,
        sample_pr_data: dict[str, Any],
    ) -> None:
        """Test listing pull requests."""
        with patch.object(
            pr_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_pr_data]

            prs = await pr_service.list("testuser", "test-repo")

        assert len(prs) == 1
        assert prs[0].number == 123

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        pr_service: PullRequestService,
    ) -> None:
        """Test listing PRs with filters."""
        with patch.object(
            pr_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            await pr_service.list(
                "testuser", "test-repo",
                state="closed",
                head="feature-branch",
                base="main",
            )

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["state"] == "closed"
        assert call_kwargs["head"] == "feature-branch"
        assert call_kwargs["base"] == "main"

    @pytest.mark.asyncio
    async def test_get(
        self,
        pr_service: PullRequestService,
        sample_pr_data: dict[str, Any],
    ) -> None:
        """Test getting single PR."""
        with patch.object(
            pr_service.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_pr_data

            pr = await pr_service.get("testuser", "test-repo", 123)

        assert pr.number == 123

    @pytest.mark.asyncio
    async def test_create(
        self,
        pr_service: PullRequestService,
        sample_pr_data: dict[str, Any],
    ) -> None:
        """Test creating PR."""
        with patch.object(
            pr_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = sample_pr_data

            pr = await pr_service.create(
                "testuser", "test-repo",
                title="New PR",
                head="feature-branch",
                base="main",
                body="PR description",
            )

        assert pr.number == 123
        call_data = mock_post.call_args[0][1]
        assert call_data["title"] == "New PR"
        assert call_data["head"] == "feature-branch"
        assert call_data["base"] == "main"

    @pytest.mark.asyncio
    async def test_create_draft(
        self,
        pr_service: PullRequestService,
        sample_pr_data: dict[str, Any],
    ) -> None:
        """Test creating draft PR."""
        with patch.object(
            pr_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = {**sample_pr_data, "draft": True}

            await pr_service.create(
                "testuser", "test-repo",
                title="Draft PR",
                head="feature",
                base="main",
                draft=True,
            )

        call_data = mock_post.call_args[0][1]
        assert call_data["draft"] is True

    @pytest.mark.asyncio
    async def test_update(
        self,
        pr_service: PullRequestService,
        sample_pr_data: dict[str, Any],
    ) -> None:
        """Test updating PR."""
        with patch.object(
            pr_service.client, "patch", new_callable=AsyncMock
        ) as mock_patch:
            mock_patch.return_value = sample_pr_data

            await pr_service.update(
                "testuser", "test-repo", 123,
                title="Updated title",
            )

        call_data = mock_patch.call_args[0][1]
        assert call_data["title"] == "Updated title"

    @pytest.mark.asyncio
    async def test_get_diff(
        self,
        pr_service: PullRequestService,
    ) -> None:
        """Test getting PR diff."""
        with patch.object(
            pr_service.client, "get_raw", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = "diff --git a/file.py..."

            diff = await pr_service.get_diff("testuser", "test-repo", 123)

        assert "diff" in diff

    @pytest.mark.asyncio
    async def test_get_files(
        self,
        pr_service: PullRequestService,
        sample_pr_file_data: dict[str, Any],
    ) -> None:
        """Test getting PR files."""
        with patch.object(
            pr_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_pr_file_data]

            files = await pr_service.get_files("testuser", "test-repo", 123)

        assert len(files) == 1
        assert files[0].filename == "src/main.py"

    @pytest.mark.asyncio
    async def test_get_commits(
        self,
        pr_service: PullRequestService,
    ) -> None:
        """Test getting PR commits."""
        commit_data = [{"sha": "abc123", "commit": {"message": "Test"}}]

        with patch.object(
            pr_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = commit_data

            commits = await pr_service.get_commits("testuser", "test-repo", 123)

        assert len(commits) == 1
        assert commits[0]["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_list_reviews(
        self,
        pr_service: PullRequestService,
        sample_review_data: dict[str, Any],
    ) -> None:
        """Test listing PR reviews."""
        with patch.object(
            pr_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_review_data]

            reviews = await pr_service.list_reviews("testuser", "test-repo", 123)

        assert len(reviews) == 1
        assert reviews[0].state == "APPROVED"

    @pytest.mark.asyncio
    async def test_create_review_approve(
        self,
        pr_service: PullRequestService,
        sample_review_data: dict[str, Any],
    ) -> None:
        """Test creating approval review."""
        with patch.object(
            pr_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = sample_review_data

            review = await pr_service.create_review(
                "testuser", "test-repo", 123,
                body="LGTM!",
                event="APPROVE",
            )

        assert review.state == "APPROVED"
        call_data = mock_post.call_args[0][1]
        assert call_data["event"] == "APPROVE"

    @pytest.mark.asyncio
    async def test_create_review_request_changes(
        self,
        pr_service: PullRequestService,
        sample_review_data: dict[str, Any],
    ) -> None:
        """Test creating request changes review."""
        review_data = {**sample_review_data, "state": "CHANGES_REQUESTED"}

        with patch.object(
            pr_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = review_data

            await pr_service.create_review(
                "testuser", "test-repo", 123,
                body="Please fix X",
                event="REQUEST_CHANGES",
            )

        call_data = mock_post.call_args[0][1]
        assert call_data["event"] == "REQUEST_CHANGES"

    @pytest.mark.asyncio
    async def test_list_review_comments(
        self,
        pr_service: PullRequestService,
        sample_review_comment_data: dict[str, Any],
    ) -> None:
        """Test listing review comments."""
        with patch.object(
            pr_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_review_comment_data]

            comments = await pr_service.list_review_comments(
                "testuser", "test-repo", 123
            )

        assert len(comments) == 1
        assert comments[0].path == "src/main.py"

    @pytest.mark.asyncio
    async def test_get_checks(
        self,
        pr_service: PullRequestService,
        sample_check_run_data: dict[str, Any],
    ) -> None:
        """Test getting check runs."""
        with patch.object(
            pr_service.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {"check_runs": [sample_check_run_data]}

            checks = await pr_service.get_checks("testuser", "test-repo", "abc123")

        assert len(checks) == 1
        assert checks[0].name == "CI"

    @pytest.mark.asyncio
    async def test_get_combined_status(
        self,
        pr_service: PullRequestService,
    ) -> None:
        """Test getting combined status."""
        status_data = {
            "state": "success",
            "statuses": [{"context": "ci/test", "state": "success"}],
        }

        with patch.object(
            pr_service.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = status_data

            status = await pr_service.get_combined_status(
                "testuser", "test-repo", "abc123"
            )

        assert status["state"] == "success"

    @pytest.mark.asyncio
    async def test_merge(
        self,
        pr_service: PullRequestService,
    ) -> None:
        """Test merging PR."""
        with patch.object(
            pr_service.client, "put", new_callable=AsyncMock
        ) as mock_put:
            mock_put.return_value = {"merged": True, "sha": "abc123"}

            result = await pr_service.merge("testuser", "test-repo", 123)

        assert result["merged"] is True

    @pytest.mark.asyncio
    async def test_merge_squash(
        self,
        pr_service: PullRequestService,
    ) -> None:
        """Test squash merge."""
        with patch.object(
            pr_service.client, "put", new_callable=AsyncMock
        ) as mock_put:
            mock_put.return_value = {"merged": True}

            await pr_service.merge(
                "testuser", "test-repo", 123,
                merge_method="squash",
                commit_title="Squashed commit",
            )

        call_data = mock_put.call_args[0][1]
        assert call_data["merge_method"] == "squash"
        assert call_data["commit_title"] == "Squashed commit"

    @pytest.mark.asyncio
    async def test_request_reviewers(
        self,
        pr_service: PullRequestService,
        sample_pr_data: dict[str, Any],
    ) -> None:
        """Test requesting reviewers."""
        with patch.object(
            pr_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = sample_pr_data

            pr = await pr_service.request_reviewers(
                "testuser", "test-repo", 123,
                reviewers=["alice", "bob"],
            )

        call_data = mock_post.call_args[0][1]
        assert call_data["reviewers"] == ["alice", "bob"]
