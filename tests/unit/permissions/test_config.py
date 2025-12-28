"""Unit tests for permission configuration."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from code_forge.permissions.models import (
    PermissionLevel,
    PermissionRule,
)
from code_forge.permissions.rules import RuleSet
from code_forge.permissions.config import (
    PermissionConfig,
    DEFAULT_RULES,
)


class TestDefaultRules:
    """Tests for DEFAULT_RULES constant."""

    def test_default_rules_exist(self):
        """Test that default rules are defined."""
        assert len(DEFAULT_RULES) > 0

    def test_read_tools_allowed(self):
        """Test that read tools are ALLOW by default."""
        read_rules = [r for r in DEFAULT_RULES if r.pattern == "tool:read"]
        assert len(read_rules) == 1
        assert read_rules[0].permission == PermissionLevel.ALLOW

    def test_glob_tool_allowed(self):
        """Test that glob tool is ALLOW by default."""
        glob_rules = [r for r in DEFAULT_RULES if r.pattern == "tool:glob"]
        assert len(glob_rules) == 1
        assert glob_rules[0].permission == PermissionLevel.ALLOW

    def test_grep_tool_allowed(self):
        """Test that grep tool is ALLOW by default."""
        grep_rules = [r for r in DEFAULT_RULES if r.pattern == "tool:grep"]
        assert len(grep_rules) == 1
        assert grep_rules[0].permission == PermissionLevel.ALLOW

    def test_write_tool_ask(self):
        """Test that write tool is ASK by default."""
        write_rules = [r for r in DEFAULT_RULES if r.pattern == "tool:write"]
        assert len(write_rules) == 1
        assert write_rules[0].permission == PermissionLevel.ASK

    def test_bash_tool_ask(self):
        """Test that bash tool is ASK by default."""
        bash_rules = [
            r for r in DEFAULT_RULES
            if r.pattern == "tool:bash" and r.permission == PermissionLevel.ASK
        ]
        assert len(bash_rules) == 1

    def test_dangerous_commands_denied(self):
        """Test that dangerous commands are DENY."""
        deny_rules = [
            r for r in DEFAULT_RULES if r.permission == PermissionLevel.DENY
        ]
        assert len(deny_rules) > 0

        # Check rm -rf is blocked
        rm_rf_rules = [
            r for r in deny_rules if "*rm -rf*" in r.pattern
        ]
        assert len(rm_rf_rules) > 0

    def test_system_paths_protected(self):
        """Test that system paths are protected."""
        etc_rules = [
            r for r in DEFAULT_RULES
            if "/etc/*" in r.pattern and r.permission == PermissionLevel.DENY
        ]
        assert len(etc_rules) > 0

    def test_all_rules_have_description(self):
        """Test that all default rules have descriptions."""
        for rule in DEFAULT_RULES:
            assert rule.description, f"Rule {rule.pattern} has no description"


class TestPermissionConfigPaths:
    """Tests for PermissionConfig path methods."""

    def test_get_global_path(self):
        """Test getting global config path."""
        path = PermissionConfig.get_global_path()
        assert isinstance(path, Path)
        assert "permissions.json" in str(path)
        assert ".config" in str(path) or "forge" in str(path)

    def test_get_project_path_with_root(self):
        """Test getting project config path with root."""
        project_root = Path("/test/project")
        path = PermissionConfig.get_project_path(project_root)
        assert isinstance(path, Path)
        assert "permissions.json" in str(path)
        assert str(project_root) in str(path)

    def test_get_project_path_none_root(self):
        """Test getting project config path with None root."""
        path = PermissionConfig.get_project_path(None)
        assert path is None


class TestPermissionConfigLoadGlobal:
    """Tests for PermissionConfig.load_global."""

    def test_load_global_returns_defaults_when_no_file(self):
        """Test that load_global returns defaults when no file exists."""
        with patch.object(PermissionConfig, "get_global_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/path/permissions.json")
            rules = PermissionConfig.load_global()

        # Should return default rules
        assert len(rules) > 0
        assert rules.default == PermissionLevel.ASK

    def test_load_global_reads_file(self):
        """Test that load_global reads from file when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "permissions.json"
            config_data = {
                "default": "deny",
                "rules": [
                    {"pattern": "tool:custom", "permission": "allow"},
                ],
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            with patch.object(PermissionConfig, "get_global_path") as mock_path:
                mock_path.return_value = config_path
                rules = PermissionConfig.load_global()

            assert rules.default == PermissionLevel.DENY
            assert len(rules) == 1
            assert rules.rules[0].pattern == "tool:custom"

    def test_load_global_handles_corrupted_file(self):
        """Test that load_global handles corrupted JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "permissions.json"
            with open(config_path, "w") as f:
                f.write("not valid json {{{")

            with patch.object(PermissionConfig, "get_global_path") as mock_path:
                mock_path.return_value = config_path
                rules = PermissionConfig.load_global()

            # Should return defaults
            assert len(rules) > 0
            assert rules.default == PermissionLevel.ASK


class TestPermissionConfigLoadProject:
    """Tests for PermissionConfig.load_project."""

    def test_load_project_returns_none_when_no_file(self):
        """Test that load_project returns None when no file exists."""
        rules = PermissionConfig.load_project(Path("/nonexistent/project"))
        assert rules is None

    def test_load_project_returns_none_when_no_root(self):
        """Test that load_project returns None when no root specified."""
        rules = PermissionConfig.load_project(None)
        assert rules is None

    def test_load_project_reads_file(self):
        """Test that load_project reads from file when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".forge"
            config_dir.mkdir()
            config_path = config_dir / "permissions.json"

            config_data = {
                "default": "allow",
                "rules": [
                    {"pattern": "tool:project_tool", "permission": "deny"},
                ],
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            rules = PermissionConfig.load_project(project_root)

            assert isinstance(rules, RuleSet)
            assert rules.default == PermissionLevel.ALLOW
            assert len(rules) == 1

    def test_load_project_handles_corrupted_file(self):
        """Test that load_project handles corrupted JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".forge"
            config_dir.mkdir()
            config_path = config_dir / "permissions.json"

            with open(config_path, "w") as f:
                f.write("corrupted {{{")

            rules = PermissionConfig.load_project(project_root)

            assert rules is None


class TestPermissionConfigSave:
    """Tests for PermissionConfig save methods."""

    def test_save_global_creates_file(self):
        """Test that save_global creates file and directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "permissions.json"

            with patch.object(PermissionConfig, "get_global_path") as mock_path:
                mock_path.return_value = config_path

                rules = RuleSet(default=PermissionLevel.DENY)
                rules.add_rule(
                    PermissionRule(pattern="tool:custom", permission=PermissionLevel.ALLOW)
                )

                PermissionConfig.save_global(rules)

            assert config_path.exists()

            with open(config_path) as f:
                data = json.load(f)

            assert data["default"] == "deny"
            assert len(data["rules"]) == 1

    def test_save_project_creates_file(self):
        """Test that save_project creates file and directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            rules = RuleSet(default=PermissionLevel.ALLOW)
            rules.add_rule(
                PermissionRule(pattern="tool:project", permission=PermissionLevel.ASK)
            )

            PermissionConfig.save_project(project_root, rules)

            config_path = project_root / ".forge" / "permissions.json"
            assert config_path.exists()

            with open(config_path) as f:
                data = json.load(f)

            assert data["default"] == "allow"
            assert len(data["rules"]) == 1


class TestPermissionConfigDefaults:
    """Tests for PermissionConfig.get_default_rules and reset_to_defaults."""

    def test_get_default_rules(self):
        """Test getting default rules."""
        rules = PermissionConfig.get_default_rules()

        assert isinstance(rules, RuleSet)
        assert len(rules) == len(DEFAULT_RULES)
        assert rules.default == PermissionLevel.ASK

    def test_get_default_rules_returns_new_instance(self):
        """Test that get_default_rules returns new instance each time."""
        rules1 = PermissionConfig.get_default_rules()
        rules2 = PermissionConfig.get_default_rules()

        assert rules1 is not rules2

    def test_reset_to_defaults(self):
        """Test resetting to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "permissions.json"

            with patch.object(PermissionConfig, "get_global_path") as mock_path:
                mock_path.return_value = config_path

                # First save custom rules
                custom_rules = RuleSet(default=PermissionLevel.DENY)
                PermissionConfig.save_global(custom_rules)

                # Now reset
                PermissionConfig.reset_to_defaults()

                # Load and verify
                rules = PermissionConfig.load_global()

            assert rules.default == PermissionLevel.ASK
            assert len(rules) == len(DEFAULT_RULES)


class TestPermissionConfigRoundtrip:
    """Integration tests for save/load roundtrip."""

    def test_global_config_roundtrip(self):
        """Test saving and loading global config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "permissions.json"

            with patch.object(PermissionConfig, "get_global_path") as mock_path:
                mock_path.return_value = config_path

                # Create custom rules
                original = RuleSet(default=PermissionLevel.DENY)
                original.add_rule(
                    PermissionRule(
                        pattern="tool:bash,arg:command:*safe*",
                        permission=PermissionLevel.ALLOW,
                        description="Allow safe commands",
                        priority=50,
                    )
                )

                # Save
                PermissionConfig.save_global(original)

                # Load
                loaded = PermissionConfig.load_global()

            assert loaded.default == original.default
            assert len(loaded) == len(original)
            assert loaded.rules[0].pattern == original.rules[0].pattern
            assert loaded.rules[0].permission == original.rules[0].permission
            assert loaded.rules[0].description == original.rules[0].description
            assert loaded.rules[0].priority == original.rules[0].priority

    def test_project_config_roundtrip(self):
        """Test saving and loading project config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create custom rules
            original = RuleSet(default=PermissionLevel.ALLOW)
            original.add_rule(
                PermissionRule(
                    pattern="tool:project_specific",
                    permission=PermissionLevel.DENY,
                    description="Project-specific rule",
                )
            )

            # Save
            PermissionConfig.save_project(project_root, original)

            # Load
            loaded = PermissionConfig.load_project(project_root)

            assert isinstance(loaded, RuleSet)
            assert loaded.default == original.default
            assert len(loaded) == len(original)
            assert loaded.rules[0].pattern == original.rules[0].pattern


class TestDefaultRulesEvaluation:
    """Tests for evaluating default rules."""

    def test_default_rules_allow_read(self):
        """Test that default rules allow read operations."""
        rules = PermissionConfig.get_default_rules()
        result = rules.evaluate("read", {"file_path": "/tmp/test.txt"})
        assert result.level == PermissionLevel.ALLOW

    def test_default_rules_ask_for_bash(self):
        """Test that default rules ask for bash."""
        rules = PermissionConfig.get_default_rules()
        result = rules.evaluate("bash", {"command": "ls -la"})
        assert result.level == PermissionLevel.ASK

    def test_default_rules_deny_rm_rf(self):
        """Test that default rules deny rm -rf."""
        rules = PermissionConfig.get_default_rules()
        result = rules.evaluate("bash", {"command": "rm -rf /"})
        assert result.level == PermissionLevel.DENY

    def test_default_rules_deny_etc_write(self):
        """Test that default rules deny writing to /etc."""
        rules = PermissionConfig.get_default_rules()
        result = rules.evaluate("write", {"file_path": "/etc/passwd"})
        assert result.level == PermissionLevel.DENY

    def test_default_rules_allow_bash_output(self):
        """Test that default rules allow bash_output."""
        rules = PermissionConfig.get_default_rules()
        result = rules.evaluate("bash_output", {"shell_id": "123"})
        assert result.level == PermissionLevel.ALLOW
