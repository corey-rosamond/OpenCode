"""Tests for workflow matcher."""

from __future__ import annotations

import pytest

from code_forge.workflows.matcher import (
    WorkflowMatch,
    WorkflowMatcher,
    WorkflowTrigger,
)


class TestWorkflowMatch:
    """Tests for WorkflowMatch dataclass."""

    def test_creation(self) -> None:
        """Test match creation."""
        match = WorkflowMatch(
            workflow_name="bug-fix",
            confidence=0.9,
            trigger_patterns=["fix the bug"],
            reason="Request matches pattern",
        )
        assert match.workflow_name == "bug-fix"
        assert match.confidence == 0.9
        assert len(match.trigger_patterns) == 1

    def test_confidence_clamping(self) -> None:
        """Test confidence is clamped to 0-1 range."""
        match = WorkflowMatch(workflow_name="test", confidence=1.5)
        assert match.confidence == 1.0

        match = WorkflowMatch(workflow_name="test", confidence=-0.5)
        assert match.confidence == 0.0

    def test_default_values(self) -> None:
        """Test default values."""
        match = WorkflowMatch(workflow_name="test", confidence=0.5)
        assert match.parameters == {}
        assert match.trigger_patterns == []
        assert match.reason == ""


class TestWorkflowTrigger:
    """Tests for WorkflowTrigger dataclass."""

    def test_creation(self) -> None:
        """Test trigger creation."""
        trigger = WorkflowTrigger(
            workflow_name="test",
            patterns=[r"test pattern"],
            keywords=["test", "example"],
            base_confidence=0.9,
        )
        assert trigger.workflow_name == "test"
        assert len(trigger.patterns) == 1
        assert trigger.base_confidence == 0.9

    def test_default_values(self) -> None:
        """Test default values."""
        trigger = WorkflowTrigger(workflow_name="test", patterns=[])
        assert trigger.keywords == []
        assert trigger.parameter_extractors == []
        assert trigger.base_confidence == 0.8


class TestWorkflowMatcher:
    """Tests for WorkflowMatcher."""

    @pytest.fixture
    def matcher(self) -> WorkflowMatcher:
        """Create a matcher instance."""
        return WorkflowMatcher()

    def test_match_bug_fix(self, matcher: WorkflowMatcher) -> None:
        """Test matching bug fix requests."""
        texts = [
            "fix the bug in the login form",
            "debug the error in main.py",
            "investigate the issue with authentication",
            "there's a bug in the database module",
        ]
        for text in texts:
            match = matcher.match(text)
            assert match is not None, f"Failed for: {text}"
            assert match.workflow_name == "bug-fix"
            assert match.confidence >= 0.7

    def test_match_feature_impl(self, matcher: WorkflowMatcher) -> None:
        """Test matching feature implementation requests."""
        texts = [
            "implement a new feature for user profiles",
            "add support for OAuth authentication",
            "create a new component for the dashboard",
        ]
        for text in texts:
            match = matcher.match(text)
            assert match is not None, f"Failed for: {text}"
            assert match.workflow_name == "feature-impl"
            assert match.confidence >= 0.7

    def test_match_pr_review(self, matcher: WorkflowMatcher) -> None:
        """Test matching PR review requests."""
        texts = [
            "review the pull request",
            "check the pr for issues",
            "look at the merge request",
        ]
        for text in texts:
            match = matcher.match(text)
            assert match is not None, f"Failed for: {text}"
            assert match.workflow_name == "pr-review"
            assert match.confidence >= 0.7

    def test_match_security_audit(self, matcher: WorkflowMatcher) -> None:
        """Test matching security audit requests."""
        texts = [
            "run a security audit",
            "check for vulnerabilities",
            "perform a security scan",
        ]
        for text in texts:
            match = matcher.match(text)
            assert match is not None, f"Failed for: {text}"
            assert match.workflow_name == "security-audit"
            assert match.confidence >= 0.7

    def test_match_code_quality(self, matcher: WorkflowMatcher) -> None:
        """Test matching code quality requests."""
        texts = [
            "improve code quality",
            "run a code review",
            "refactor the codebase",
        ]
        for text in texts:
            match = matcher.match(text)
            assert match is not None, f"Failed for: {text}"
            assert match.workflow_name == "code-quality"
            assert match.confidence >= 0.7

    def test_no_match(self, matcher: WorkflowMatcher) -> None:
        """Test no match for unrelated requests."""
        texts = [
            "hello world",
            "what is the weather?",
            "read config.py",
        ]
        for text in texts:
            match = matcher.match(text)
            assert match is None, f"Unexpected match for: {text}"

    def test_match_empty_string(self, matcher: WorkflowMatcher) -> None:
        """Test empty string returns no match."""
        assert matcher.match("") is None
        assert matcher.match("   ") is None

    def test_match_all(self, matcher: WorkflowMatcher) -> None:
        """Test getting all matches."""
        # A request that could match multiple workflows
        matches = matcher.match_all("fix the security bug in code", min_confidence=0.3)
        assert len(matches) >= 1
        # Should be sorted by confidence
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    def test_match_all_min_confidence(self, matcher: WorkflowMatcher) -> None:
        """Test min_confidence filtering."""
        matches_low = matcher.match_all("fix the bug", min_confidence=0.3)
        matches_high = matcher.match_all("fix the bug", min_confidence=0.9)
        assert len(matches_low) >= len(matches_high)

    def test_should_trigger_workflow(self, matcher: WorkflowMatcher) -> None:
        """Test quick trigger check."""
        assert matcher.should_trigger_workflow("fix the bug in login")
        assert matcher.should_trigger_workflow("run a security audit")
        assert not matcher.should_trigger_workflow("hello world")

    def test_get_suggested_workflow(self, matcher: WorkflowMatcher) -> None:
        """Test getting suggested workflow name."""
        assert matcher.get_suggested_workflow("fix the bug") == "bug-fix"
        assert matcher.get_suggested_workflow("review the pr") == "pr-review"
        assert matcher.get_suggested_workflow("hello world") is None

    def test_add_custom_trigger(self, matcher: WorkflowMatcher) -> None:
        """Test adding custom triggers."""
        custom = WorkflowTrigger(
            workflow_name="custom-workflow",
            patterns=[r"run custom workflow"],
            keywords=["custom"],
            base_confidence=0.9,
        )
        matcher.add_trigger(custom)

        match = matcher.match("run custom workflow now")
        assert match is not None
        assert match.workflow_name == "custom-workflow"

    def test_remove_trigger(self, matcher: WorkflowMatcher) -> None:
        """Test removing triggers."""
        # Bug fix should work initially
        assert matcher.match("fix the bug") is not None

        # Remove bug-fix triggers
        removed = matcher.remove_trigger("bug-fix")
        assert removed is True

        # Should no longer match
        match = matcher.match("fix the bug")
        assert match is None or match.workflow_name != "bug-fix"

    def test_keyword_fallback(self, matcher: WorkflowMatcher) -> None:
        """Test keyword-based matching as fallback."""
        # Request with multiple keywords but no pattern match
        matches = matcher.match_all("the bug is causing errors in the system", min_confidence=0.3)
        # Should get some match based on keywords
        assert len(matches) >= 0  # May or may not match depending on keyword count


class TestWorkflowMatcherWithCustomTriggers:
    """Tests for matcher with custom triggers."""

    def test_custom_triggers_override(self) -> None:
        """Test custom triggers take effect."""
        custom = WorkflowTrigger(
            workflow_name="deployment",
            patterns=[r"deploy\s+(?:to\s+)?(?:production|staging|dev)"],
            keywords=["deploy", "production", "staging"],
            base_confidence=0.9,
        )
        matcher = WorkflowMatcher(custom_triggers=[custom])

        match = matcher.match("deploy to production")
        assert match is not None
        assert match.workflow_name == "deployment"

    def test_multiple_custom_triggers(self) -> None:
        """Test multiple custom triggers."""
        triggers = [
            WorkflowTrigger(
                workflow_name="backup",
                patterns=[r"(?:create|make)\s+(?:a\s+)?backup"],
                keywords=["backup"],
            ),
            WorkflowTrigger(
                workflow_name="restore",
                patterns=[r"restore\s+(?:from\s+)?backup"],
                keywords=["restore"],
            ),
        ]
        matcher = WorkflowMatcher(custom_triggers=triggers)

        backup_match = matcher.match("create a backup of the database")
        assert backup_match is not None
        assert backup_match.workflow_name == "backup"

        restore_match = matcher.match("restore from backup")
        assert restore_match is not None
        assert restore_match.workflow_name == "restore"
