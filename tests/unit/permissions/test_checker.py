"""Unit tests for permission checker."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from code_forge.permissions.models import (
    PermissionLevel,
    PermissionRule,
    PermissionResult,
)
from code_forge.permissions.rules import RuleSet
from code_forge.permissions.checker import (
    PermissionChecker,
    ToolPermissionError,
)


class TestPermissionChecker:
    """Tests for PermissionChecker class."""

    def test_creation_empty(self):
        """Test creating checker with no rules."""
        checker = PermissionChecker()
        assert isinstance(checker.global_rules, RuleSet)
        assert checker.project_rules is None
        assert len(checker.session_rules) == 0

    def test_creation_with_global_rules(self):
        """Test creating checker with global rules."""
        global_rules = RuleSet()
        global_rules.add_rule(PermissionRule(pattern="tool:read", permission=PermissionLevel.ALLOW))
        checker = PermissionChecker(global_rules=global_rules)
        assert len(checker.global_rules) == 1

    def test_creation_with_project_rules(self):
        """Test creating checker with project rules."""
        project_rules = RuleSet()
        project_rules.add_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.DENY))
        checker = PermissionChecker(project_rules=project_rules)
        assert isinstance(checker.project_rules, RuleSet)


class TestPermissionCheckerCheck:
    """Tests for PermissionChecker.check method."""

    def test_check_uses_global_rules(self):
        """Test that check uses global rules."""
        global_rules = RuleSet()
        global_rules.add_rule(PermissionRule(pattern="tool:read", permission=PermissionLevel.ALLOW))
        checker = PermissionChecker(global_rules=global_rules)

        result = checker.check("read", {})
        assert result.level == PermissionLevel.ALLOW

    def test_check_falls_through_to_default(self):
        """Test that check falls through to default when no rules match."""
        global_rules = RuleSet(default=PermissionLevel.ASK)
        checker = PermissionChecker(global_rules=global_rules)

        result = checker.check("unknown", {})
        assert result.level == PermissionLevel.ASK

    def test_session_rules_override_global(self):
        """Test that session rules override global rules."""
        global_rules = RuleSet()
        global_rules.add_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.ASK))

        checker = PermissionChecker(global_rules=global_rules)
        checker.add_session_rule(
            PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW, priority=100)
        )

        result = checker.check("bash", {})
        assert result.level == PermissionLevel.ALLOW

    def test_project_rules_override_global(self):
        """Test that project rules override global rules."""
        global_rules = RuleSet()
        global_rules.add_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW))

        project_rules = RuleSet()
        project_rules.add_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.DENY))

        checker = PermissionChecker(
            global_rules=global_rules, project_rules=project_rules
        )

        result = checker.check("bash", {})
        assert result.level == PermissionLevel.DENY

    def test_session_rules_override_project(self):
        """Test that session rules override project rules."""
        project_rules = RuleSet()
        project_rules.add_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.DENY))

        checker = PermissionChecker(project_rules=project_rules)
        checker.add_session_rule(
            PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW, priority=100)
        )

        result = checker.check("bash", {})
        assert result.level == PermissionLevel.ALLOW


class TestPermissionCheckerSessionRules:
    """Tests for session rule management."""

    def test_add_session_rule(self):
        """Test adding a session rule."""
        checker = PermissionChecker()
        rule = PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW, priority=100)
        checker.add_session_rule(rule)

        rules = checker.get_session_rules()
        assert len(rules) == 1
        assert rules[0].pattern == "tool:bash"

    def test_add_session_rule_replaces_same_pattern(self):
        """Test that adding session rule with same pattern replaces."""
        checker = PermissionChecker()
        checker.add_session_rule(
            PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW, priority=100)
        )
        checker.add_session_rule(
            PermissionRule(pattern="tool:bash", permission=PermissionLevel.DENY, priority=100)
        )

        rules = checker.get_session_rules()
        assert len(rules) == 1
        assert rules[0].permission == PermissionLevel.DENY

    def test_remove_session_rule(self):
        """Test removing a session rule."""
        checker = PermissionChecker()
        checker.add_session_rule(
            PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW)
        )

        assert checker.remove_session_rule("tool:bash") is True
        assert len(checker.get_session_rules()) == 0

    def test_remove_nonexistent_session_rule(self):
        """Test removing nonexistent session rule."""
        checker = PermissionChecker()
        assert checker.remove_session_rule("tool:bash") is False

    def test_clear_session_rules(self):
        """Test clearing all session rules."""
        checker = PermissionChecker()
        checker.add_session_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW))
        checker.add_session_rule(PermissionRule(pattern="tool:read", permission=PermissionLevel.ALLOW))

        checker.clear_session_rules()
        assert len(checker.get_session_rules()) == 0

    def test_get_session_rules_returns_copy(self):
        """Test that get_session_rules returns a copy."""
        checker = PermissionChecker()
        checker.add_session_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.ALLOW))

        rules = checker.get_session_rules()
        rules.clear()

        assert len(checker.get_session_rules()) == 1


class TestPermissionCheckerAllowDeny:
    """Tests for allow_always and deny_always methods."""

    def test_allow_always_creates_rule(self):
        """Test that allow_always creates an ALLOW session rule."""
        checker = PermissionChecker()
        checker.allow_always("bash", None)

        result = checker.check("bash", {})
        assert result.level == PermissionLevel.ALLOW

    def test_allow_always_with_arguments(self):
        """Test allow_always with specific arguments."""
        checker = PermissionChecker()
        checker.allow_always("bash", {"command": "ls"})

        rules = checker.get_session_rules()
        assert len(rules) == 1
        assert ",arg:" in rules[0].pattern

    def test_deny_always_creates_rule(self):
        """Test that deny_always creates a DENY session rule."""
        checker = PermissionChecker()
        checker.deny_always("bash", None)

        result = checker.check("bash", {})
        assert result.level == PermissionLevel.DENY

    def test_deny_always_with_arguments(self):
        """Test deny_always with specific arguments."""
        checker = PermissionChecker()
        checker.deny_always("bash", {"command": "rm"})

        rules = checker.get_session_rules()
        assert len(rules) == 1
        assert ",arg:" in rules[0].pattern


class TestPermissionCheckerFromConfig:
    """Tests for PermissionChecker.from_config."""

    @patch("code_forge.permissions.config.PermissionConfig.load_global")
    @patch("code_forge.permissions.config.PermissionConfig.load_project")
    def test_from_config_loads_rules(self, mock_load_project, mock_load_global):
        """Test that from_config loads global and project rules."""
        global_rules = RuleSet()
        global_rules.add_rule(PermissionRule(pattern="tool:read", permission=PermissionLevel.ALLOW))

        project_rules = RuleSet()
        project_rules.add_rule(PermissionRule(pattern="tool:bash", permission=PermissionLevel.DENY))

        mock_load_global.return_value = global_rules
        mock_load_project.return_value = project_rules

        checker = PermissionChecker.from_config(Path("/test/project"))

        assert len(checker.global_rules) == 1
        assert isinstance(checker.project_rules, RuleSet)
        assert len(checker.project_rules) == 1

    @patch("code_forge.permissions.config.PermissionConfig.load_global")
    @patch("code_forge.permissions.config.PermissionConfig.load_project")
    def test_from_config_no_project(self, mock_load_project, mock_load_global):
        """Test from_config when no project root specified."""
        global_rules = RuleSet()
        mock_load_global.return_value = global_rules
        mock_load_project.return_value = None

        checker = PermissionChecker.from_config(None)

        assert checker.project_rules is None


class TestToolPermissionError:
    """Tests for ToolPermissionError exception."""

    def test_creation(self):
        """Test creating permission error."""
        result = PermissionResult(
            level=PermissionLevel.DENY,
            reason="Blocked by security rule",
        )
        error = ToolPermissionError(result, "bash", {"command": "rm -rf /"})

        assert error.result == result
        assert error.tool_name == "bash"
        assert error.arguments == {"command": "rm -rf /"}

    def test_message_format(self):
        """Test error message format."""
        result = PermissionResult(
            level=PermissionLevel.DENY,
            reason="Dangerous command blocked",
        )
        error = ToolPermissionError(result, "bash", {})

        message = str(error)
        assert "Permission denied" in message
        assert "bash" in message
        assert "Dangerous command blocked" in message

    def test_can_be_raised_and_caught(self):
        """Test that error can be raised and caught."""
        result = PermissionResult(level=PermissionLevel.DENY, reason="Test")
        error = ToolPermissionError(result, "test", {})

        with pytest.raises(ToolPermissionError) as exc_info:
            raise error

        assert exc_info.value.tool_name == "test"

    def test_is_exception_subclass(self):
        """Test that ToolPermissionError is Exception subclass."""
        result = PermissionResult(level=PermissionLevel.DENY, reason="Test")
        error = ToolPermissionError(result, "test", {})

        assert isinstance(error, Exception)


class TestPermissionCheckerIntegration:
    """Integration tests for PermissionChecker."""

    def test_complete_permission_flow(self):
        """Test complete permission check flow."""
        # Setup global rules
        global_rules = RuleSet(default=PermissionLevel.ASK)
        global_rules.add_rule(
            PermissionRule(pattern="tool:read", permission=PermissionLevel.ALLOW)
        )
        global_rules.add_rule(
            PermissionRule(pattern="tool:bash", permission=PermissionLevel.ASK)
        )
        global_rules.add_rule(
            PermissionRule(
                pattern="tool:bash,arg:command:*rm -rf*",
                permission=PermissionLevel.DENY,
                priority=50,
            )
        )

        checker = PermissionChecker(global_rules=global_rules)

        # Read should be allowed
        result = checker.check("read", {"file_path": "/tmp/test.txt"})
        assert result.allowed

        # Normal bash should need confirmation
        result = checker.check("bash", {"command": "ls -la"})
        assert result.needs_confirmation

        # Dangerous command should be denied
        result = checker.check("bash", {"command": "rm -rf /"})
        assert result.denied

        # Unknown tool uses default
        result = checker.check("unknown", {})
        assert result.needs_confirmation

    def test_session_rule_lifetime(self):
        """Test that session rules persist until cleared."""
        checker = PermissionChecker()

        # Initially uses default
        result = checker.check("bash", {})
        assert result.level == PermissionLevel.ASK

        # Add session rule
        checker.allow_always("bash", None)

        # Now allowed
        result = checker.check("bash", {})
        assert result.level == PermissionLevel.ALLOW

        # Clear session rules
        checker.clear_session_rules()

        # Back to default
        result = checker.check("bash", {})
        assert result.level == PermissionLevel.ASK
