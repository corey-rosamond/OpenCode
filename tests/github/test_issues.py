"""Tests for GitHub issue service."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from code_forge.github.issues import (
    GitHubUser,
    GitHubLabel,
    GitHubMilestone,
    GitHubIssue,
    GitHubComment,
    IssueService,
)
from code_forge.github.client import GitHubClient


class TestGitHubUser:
    """Tests for GitHubUser dataclass."""

    def test_from_api(self, sample_user_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        user = GitHubUser.from_api(sample_user_data)

        assert user.login == "testuser"
        assert user.id == 12345
        assert "avatars" in user.avatar_url
        assert user.type == "User"


class TestGitHubLabel:
    """Tests for GitHubLabel dataclass."""

    def test_from_api(self, sample_label_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        label = GitHubLabel.from_api(sample_label_data)

        assert label.name == "bug"
        assert label.color == "d73a4a"
        assert label.description == "Something isn't working"

    def test_from_api_no_description(self) -> None:
        """Test creating label without description."""
        data = {"name": "help wanted", "color": "008672"}
        label = GitHubLabel.from_api(data)

        assert label.name == "help wanted"
        assert label.description is None


class TestGitHubMilestone:
    """Tests for GitHubMilestone dataclass."""

    def test_from_api(self, sample_milestone_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        milestone = GitHubMilestone.from_api(sample_milestone_data)

        assert milestone.number == 1
        assert milestone.title == "v1.0"
        assert milestone.state == "open"
        assert milestone.due_on == "2024-01-01T00:00:00Z"


class TestGitHubIssue:
    """Tests for GitHubIssue dataclass."""

    def test_from_api(self, sample_issue_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        issue = GitHubIssue.from_api(sample_issue_data)

        assert issue.number == 42
        assert issue.title == "Test issue"
        assert issue.body == "This is a test issue"
        assert issue.state == "open"
        assert issue.author.login == "testuser"
        assert len(issue.assignees) == 1
        assert len(issue.labels) == 1
        assert issue.labels[0].name == "bug"
        assert issue.milestone.title == "v1.0"
        assert issue.comments_count == 5
        assert issue.is_pull_request is False

    def test_from_api_minimal(self, sample_user_data: dict[str, Any]) -> None:
        """Test creating from minimal API response."""
        data = {
            "number": 1,
            "title": "Test",
            "body": None,
            "state": "open",
            "user": sample_user_data,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "url": "https://api.github.com/repos/test/test/issues/1",
            "html_url": "https://github.com/test/test/issues/1",
        }

        issue = GitHubIssue.from_api(data)

        assert issue.number == 1
        assert issue.body is None
        assert issue.milestone is None
        assert len(issue.labels) == 0

    def test_from_api_pull_request(self, sample_user_data: dict[str, Any]) -> None:
        """Test detecting PR in issues endpoint."""
        data = {
            "number": 1,
            "title": "Test PR",
            "body": None,
            "state": "open",
            "user": sample_user_data,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "url": "https://api.github.com/repos/test/test/issues/1",
            "html_url": "https://github.com/test/test/pull/1",
            "pull_request": {"url": "https://api.github.com/repos/test/test/pulls/1"},
        }

        issue = GitHubIssue.from_api(data)

        assert issue.is_pull_request is True


class TestGitHubComment:
    """Tests for GitHubComment dataclass."""

    def test_from_api(self, sample_comment_data: dict[str, Any]) -> None:
        """Test creating from API response."""
        comment = GitHubComment.from_api(sample_comment_data)

        assert comment.id == 12345
        assert comment.body == "This is a test comment"
        assert comment.author.login == "testuser"


class TestIssueService:
    """Tests for IssueService class."""

    @pytest.mark.asyncio
    async def test_list(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test listing issues."""
        with patch.object(
            issue_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_issue_data]

            issues = await issue_service.list("testuser", "test-repo")

        assert len(issues) == 1
        assert issues[0].number == 42

    @pytest.mark.asyncio
    async def test_list_filters_out_prs(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
        sample_user_data: dict[str, Any],
    ) -> None:
        """Test that listing issues filters out PRs."""
        pr_data = {
            **sample_issue_data,
            "number": 99,
            "pull_request": {"url": "..."},
        }

        with patch.object(
            issue_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_issue_data, pr_data]

            issues = await issue_service.list("testuser", "test-repo")

        assert len(issues) == 1
        assert issues[0].number == 42

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        issue_service: IssueService,
    ) -> None:
        """Test listing issues with filters."""
        with patch.object(
            issue_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            await issue_service.list(
                "testuser", "test-repo",
                state="closed",
                labels=["bug", "urgent"],
                assignee="alice",
                creator="bob",
                milestone="1",
            )

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["state"] == "closed"
        assert call_kwargs["labels"] == "bug,urgent"
        assert call_kwargs["assignee"] == "alice"
        assert call_kwargs["creator"] == "bob"
        assert call_kwargs["milestone"] == "1"

    @pytest.mark.asyncio
    async def test_get(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test getting single issue."""
        with patch.object(
            issue_service.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_issue_data

            issue = await issue_service.get("testuser", "test-repo", 42)

        assert issue.number == 42
        mock_get.assert_called_once_with("/repos/testuser/test-repo/issues/42")

    @pytest.mark.asyncio
    async def test_create(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test creating issue."""
        with patch.object(
            issue_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = sample_issue_data

            issue = await issue_service.create(
                "testuser", "test-repo",
                title="New issue",
                body="Issue description",
                labels=["bug"],
                assignees=["alice"],
            )

        assert issue.number == 42
        call_args = mock_post.call_args[0]
        call_data = call_args[1]
        assert call_data["title"] == "New issue"
        assert call_data["body"] == "Issue description"
        assert call_data["labels"] == ["bug"]

    @pytest.mark.asyncio
    async def test_update(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test updating issue."""
        updated_data = {**sample_issue_data, "title": "Updated title"}

        with patch.object(
            issue_service.client, "patch", new_callable=AsyncMock
        ) as mock_patch:
            mock_patch.return_value = updated_data

            issue = await issue_service.update(
                "testuser", "test-repo", 42,
                title="Updated title",
            )

        assert issue.title == "Updated title"

    @pytest.mark.asyncio
    async def test_close(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test closing issue."""
        closed_data = {
            **sample_issue_data,
            "state": "closed",
            "state_reason": "completed",
        }

        with patch.object(
            issue_service.client, "patch", new_callable=AsyncMock
        ) as mock_patch:
            mock_patch.return_value = closed_data

            issue = await issue_service.close("testuser", "test-repo", 42)

        assert issue.state == "closed"

    @pytest.mark.asyncio
    async def test_reopen(
        self,
        issue_service: IssueService,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test reopening issue."""
        with patch.object(
            issue_service.client, "patch", new_callable=AsyncMock
        ) as mock_patch:
            mock_patch.return_value = sample_issue_data

            issue = await issue_service.reopen("testuser", "test-repo", 42)

        call_data = mock_patch.call_args[0][1]
        assert call_data["state"] == "open"

    @pytest.mark.asyncio
    async def test_list_comments(
        self,
        issue_service: IssueService,
        sample_comment_data: dict[str, Any],
    ) -> None:
        """Test listing issue comments."""
        with patch.object(
            issue_service.client, "get_paginated", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [sample_comment_data]

            comments = await issue_service.list_comments(
                "testuser", "test-repo", 42
            )

        assert len(comments) == 1
        assert comments[0].id == 12345

    @pytest.mark.asyncio
    async def test_add_comment(
        self,
        issue_service: IssueService,
        sample_comment_data: dict[str, Any],
    ) -> None:
        """Test adding comment."""
        with patch.object(
            issue_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = sample_comment_data

            comment = await issue_service.add_comment(
                "testuser", "test-repo", 42,
                body="New comment",
            )

        assert comment.id == 12345
        call_data = mock_post.call_args[0][1]
        assert call_data["body"] == "New comment"

    @pytest.mark.asyncio
    async def test_update_comment(
        self,
        issue_service: IssueService,
        sample_comment_data: dict[str, Any],
    ) -> None:
        """Test updating comment."""
        with patch.object(
            issue_service.client, "patch", new_callable=AsyncMock
        ) as mock_patch:
            mock_patch.return_value = sample_comment_data

            comment = await issue_service.update_comment(
                "testuser", "test-repo", 12345,
                body="Updated comment",
            )

        assert comment.id == 12345

    @pytest.mark.asyncio
    async def test_delete_comment(
        self,
        issue_service: IssueService,
    ) -> None:
        """Test deleting comment."""
        with patch.object(
            issue_service.client, "delete", new_callable=AsyncMock
        ) as mock_delete:
            await issue_service.delete_comment("testuser", "test-repo", 12345)

        mock_delete.assert_called_once_with(
            "/repos/testuser/test-repo/issues/comments/12345"
        )

    @pytest.mark.asyncio
    async def test_add_labels(
        self,
        issue_service: IssueService,
        sample_label_data: dict[str, Any],
    ) -> None:
        """Test adding labels."""
        with patch.object(
            issue_service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = [sample_label_data]

            labels = await issue_service.add_labels(
                "testuser", "test-repo", 42,
                labels=["bug", "urgent"],
            )

        assert len(labels) == 1
        assert labels[0].name == "bug"

    @pytest.mark.asyncio
    async def test_remove_label(
        self,
        issue_service: IssueService,
    ) -> None:
        """Test removing label."""
        with patch.object(
            issue_service.client, "delete", new_callable=AsyncMock
        ) as mock_delete:
            await issue_service.remove_label(
                "testuser", "test-repo", 42, "bug"
            )

        mock_delete.assert_called_once_with(
            "/repos/testuser/test-repo/issues/42/labels/bug"
        )
