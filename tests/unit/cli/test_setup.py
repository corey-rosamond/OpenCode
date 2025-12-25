"""Tests for CLI setup wizard.

This module provides comprehensive tests for the first-time setup wizard,
including:
- Interactive wizard flow (mocked input)
- API key validation (format, prefix)
- Configuration file saving
- File permission handling
- Error recovery scenarios
- Environment variable handling
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_forge.cli.setup import (
    check_api_key_configured,
    run_setup_wizard,
    save_api_key,
)


class TestSaveApiKey:
    """Tests for the save_api_key function."""

    def test_save_to_new_file(self, tmp_path: Path) -> None:
        """Test saving API key to a new configuration file."""
        config_dir = tmp_path / ".forge"
        api_key = "sk-or-v1-test-key-12345"

        save_api_key(api_key, config_dir)

        config_file = config_dir / "settings.json"
        assert config_file.exists()

        with config_file.open() as f:
            data = json.load(f)
        assert data["api_key"] == api_key

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_api_key creates the config directory if needed."""
        config_dir = tmp_path / ".forge" / "nested" / "path"
        api_key = "sk-or-v1-test-key"

        save_api_key(api_key, config_dir)

        assert config_dir.exists()
        assert (config_dir / "settings.json").exists()

    def test_save_merges_with_existing_config(self, tmp_path: Path) -> None:
        """Test that save_api_key merges with existing configuration."""
        config_dir = tmp_path / ".forge"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "settings.json"

        # Create existing config with other settings
        existing_config = {
            "theme": "dark",
            "model": "gpt-4",
            "timeout": 30,
        }
        with config_file.open("w") as f:
            json.dump(existing_config, f)

        # Save new API key
        api_key = "sk-or-v1-new-key"
        save_api_key(api_key, config_dir)

        # Verify merge
        with config_file.open() as f:
            data = json.load(f)

        assert data["api_key"] == api_key
        assert data["theme"] == "dark"
        assert data["model"] == "gpt-4"
        assert data["timeout"] == 30

    def test_save_overwrites_existing_api_key(self, tmp_path: Path) -> None:
        """Test that save_api_key overwrites existing API key."""
        config_dir = tmp_path / ".forge"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "settings.json"

        # Create existing config with old API key
        with config_file.open("w") as f:
            json.dump({"api_key": "old-key"}, f)

        # Save new API key
        new_key = "sk-or-v1-new-key"
        save_api_key(new_key, config_dir)

        with config_file.open() as f:
            data = json.load(f)
        assert data["api_key"] == new_key

    def test_save_recovers_from_corrupted_json(self, tmp_path: Path) -> None:
        """Test that save_api_key recovers from corrupted JSON."""
        config_dir = tmp_path / ".forge"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "settings.json"

        # Create corrupted JSON file
        with config_file.open("w") as f:
            f.write("{invalid json here")

        # Should not raise, should start fresh
        api_key = "sk-or-v1-test-key"
        save_api_key(api_key, config_dir)

        with config_file.open() as f:
            data = json.load(f)
        assert data["api_key"] == api_key

    def test_save_sets_restrictive_permissions(self, tmp_path: Path) -> None:
        """Test that save_api_key sets restrictive file permissions."""
        config_dir = tmp_path / ".forge"
        api_key = "sk-or-v1-secret-key"

        save_api_key(api_key, config_dir)

        config_file = config_dir / "settings.json"

        # Check permissions (Unix only - Windows doesn't support chmod)
        if os.name != "nt":
            mode = config_file.stat().st_mode
            # Should be readable/writable by owner only (0o600)
            assert mode & 0o777 == 0o600

    def test_save_with_empty_existing_file(self, tmp_path: Path) -> None:
        """Test saving when existing file is empty."""
        config_dir = tmp_path / ".forge"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "settings.json"

        # Create empty file
        config_file.touch()

        api_key = "sk-or-v1-test-key"
        save_api_key(api_key, config_dir)

        with config_file.open() as f:
            data = json.load(f)
        assert data["api_key"] == api_key

    def test_save_uses_default_config_dir(self) -> None:
        """Test that save_api_key uses ~/.forge by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock Path.home() to return our temp directory
            mock_home = Path(tmpdir)
            with patch.object(Path, "home", return_value=mock_home):
                save_api_key("sk-or-v1-test")

                expected_file = mock_home / ".forge" / "settings.json"
                assert expected_file.exists()


class TestCheckApiKeyConfigured:
    """Tests for the check_api_key_configured function."""

    def test_returns_true_when_env_var_set(self) -> None:
        """Test returns True when OPENROUTER_API_KEY env var is set."""
        mock_config = MagicMock()
        mock_config.get_api_key.return_value = None

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-env-key"}):
            assert check_api_key_configured(mock_config) is True

    def test_returns_true_when_config_has_key(self) -> None:
        """Test returns True when config has API key."""
        mock_config = MagicMock()
        mock_config.get_api_key.return_value = "sk-or-v1-config-key"

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENROUTER_API_KEY", None)
            assert check_api_key_configured(mock_config) is True

    def test_returns_false_when_no_key(self) -> None:
        """Test returns False when no API key is configured."""
        mock_config = MagicMock()
        mock_config.get_api_key.return_value = None

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENROUTER_API_KEY", None)
            assert check_api_key_configured(mock_config) is False

    def test_env_var_takes_priority(self) -> None:
        """Test that environment variable is checked first."""
        mock_config = MagicMock()
        # Config should not be checked if env var exists
        mock_config.get_api_key.return_value = None

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key"}):
            result = check_api_key_configured(mock_config)

            assert result is True
            # get_api_key should not be called since env var exists
            mock_config.get_api_key.assert_not_called()


class TestRunSetupWizard:
    """Tests for the run_setup_wizard interactive function."""

    def test_successful_setup_flow(self, tmp_path: Path) -> None:
        """Test successful setup wizard flow."""
        config_dir = tmp_path / ".forge"
        api_key = "sk-or-v1-test-key"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            mock_prompt.ask.return_value = api_key

            result = run_setup_wizard(config_dir)

        assert result == api_key
        assert (config_dir / "settings.json").exists()

    def test_accepts_non_standard_key_with_confirmation(self, tmp_path: Path) -> None:
        """Test accepting non-standard API key format with confirmation."""
        config_dir = tmp_path / ".forge"
        non_standard_key = "my-custom-api-key"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            mock_prompt.ask.return_value = non_standard_key
            # User confirms to use the non-standard key
            mock_confirm.ask.return_value = True

            result = run_setup_wizard(config_dir)

        assert result == non_standard_key

    def test_rejects_non_standard_key_without_confirmation(self, tmp_path: Path) -> None:
        """Test rejecting non-standard API key format without confirmation."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            # First attempt: non-standard key, rejected
            # Second attempt: valid key
            mock_prompt.ask.side_effect = ["custom-key", "sk-or-v1-valid"]
            # Reject first, then not asked again
            mock_confirm.ask.return_value = False

            result = run_setup_wizard(config_dir)

        assert result == "sk-or-v1-valid"

    def test_empty_key_prompts_retry_or_exit(self, tmp_path: Path) -> None:
        """Test empty key handling with retry/exit option."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            # First attempt: empty, user chooses to exit
            mock_prompt.ask.return_value = ""
            mock_confirm.ask.return_value = True  # Yes, exit

            result = run_setup_wizard(config_dir)

        assert result is None

    def test_empty_key_retry_succeeds(self, tmp_path: Path) -> None:
        """Test empty key followed by successful retry."""
        config_dir = tmp_path / ".forge"
        valid_key = "sk-or-v1-valid-key"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            # First empty, then valid key
            mock_prompt.ask.side_effect = ["", valid_key]
            mock_confirm.ask.return_value = False  # Don't exit, retry

            result = run_setup_wizard(config_dir)

        assert result == valid_key

    def test_whitespace_only_key_treated_as_empty(self, tmp_path: Path) -> None:
        """Test that whitespace-only key is treated as empty."""
        config_dir = tmp_path / ".forge"
        valid_key = "sk-or-v1-valid"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            # First whitespace, then valid
            mock_prompt.ask.side_effect = ["   \t\n  ", valid_key]
            mock_confirm.ask.return_value = False  # Don't exit

            result = run_setup_wizard(config_dir)

        assert result == valid_key

    def test_key_whitespace_stripped(self, tmp_path: Path) -> None:
        """Test that whitespace around key is stripped."""
        config_dir = tmp_path / ".forge"
        key_with_whitespace = "  sk-or-v1-test  \n"
        expected_key = "sk-or-v1-test"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm"), \
             patch("code_forge.cli.setup.console"):

            mock_prompt.ask.return_value = key_with_whitespace

            result = run_setup_wizard(config_dir)

        assert result == expected_key

        # Verify saved key is also stripped
        with (config_dir / "settings.json").open() as f:
            data = json.load(f)
        assert data["api_key"] == expected_key

    def test_permission_error_returns_none(self, tmp_path: Path) -> None:
        """Test that PermissionError during save returns None."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm"), \
             patch("code_forge.cli.setup.console"), \
             patch("code_forge.cli.setup.save_api_key") as mock_save:

            mock_prompt.ask.return_value = "sk-or-v1-test"
            mock_save.side_effect = PermissionError("Access denied")

            result = run_setup_wizard(config_dir)

        assert result is None

    def test_general_error_returns_none(self, tmp_path: Path) -> None:
        """Test that general exception during save returns None."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm"), \
             patch("code_forge.cli.setup.console"), \
             patch("code_forge.cli.setup.save_api_key") as mock_save:

            mock_prompt.ask.return_value = "sk-or-v1-test"
            mock_save.side_effect = IOError("Disk full")

            result = run_setup_wizard(config_dir)

        assert result is None

    def test_uses_default_config_dir(self) -> None:
        """Test that wizard uses ~/.forge by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home = Path(tmpdir)

            with patch.object(Path, "home", return_value=mock_home), \
                 patch("code_forge.cli.setup.Prompt") as mock_prompt, \
                 patch("code_forge.cli.setup.Confirm"), \
                 patch("code_forge.cli.setup.console"):

                mock_prompt.ask.return_value = "sk-or-v1-test"

                result = run_setup_wizard()

            assert result == "sk-or-v1-test"
            assert (mock_home / ".forge" / "settings.json").exists()


class TestApiKeyValidation:
    """Tests for API key format validation."""

    @pytest.mark.parametrize(
        "api_key",
        [
            "sk-or-v1-abc123",
            "sk-or-v1-0000000000000000000000000000000000000000",
            "sk-or-live-xyz789",
            "sk-or-test-key",
        ],
    )
    def test_valid_openrouter_key_formats(self, api_key: str, tmp_path: Path) -> None:
        """Test that valid OpenRouter key formats are accepted without warning."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            mock_prompt.ask.return_value = api_key

            result = run_setup_wizard(config_dir)

            # Should not ask for confirmation for valid format
            # (Confirm.ask is only called for empty key exit or non-standard format)
            assert result == api_key

    @pytest.mark.parametrize(
        "api_key",
        [
            "sk-abc123",           # OpenAI format
            "test-key",            # Generic
            "my-api-key-12345",    # Custom
            "OPENROUTER_KEY",      # Not a key at all
        ],
    )
    def test_non_standard_key_triggers_warning(self, api_key: str, tmp_path: Path) -> None:
        """Test that non-standard key formats trigger a warning."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console") as mock_console:

            mock_prompt.ask.return_value = api_key
            mock_confirm.ask.return_value = True  # Accept anyway

            run_setup_wizard(config_dir)

            # Should have printed a warning
            warning_printed = any(
                "sk-or-" in str(call)
                for call in mock_console.print.call_args_list
            )
            assert warning_printed


class TestCrossPlatformCompatibility:
    """Tests for cross-platform file handling."""

    def test_path_with_spaces(self, tmp_path: Path) -> None:
        """Test handling of paths with spaces."""
        config_dir = tmp_path / "path with spaces" / ".forge"

        save_api_key("sk-or-v1-test", config_dir)

        assert (config_dir / "settings.json").exists()

    def test_path_with_unicode(self, tmp_path: Path) -> None:
        """Test handling of paths with unicode characters."""
        config_dir = tmp_path / "配置目录" / ".forge"

        save_api_key("sk-or-v1-test", config_dir)

        assert (config_dir / "settings.json").exists()

    def test_windows_style_path_handling(self, tmp_path: Path) -> None:
        """Test that paths work regardless of separator style."""
        # This should work on any platform
        config_dir = tmp_path / ".forge"

        save_api_key("sk-or-v1-test", config_dir)

        # Should be readable regardless of how path was created
        with (config_dir / "settings.json").open() as f:
            data = json.load(f)
        assert data["api_key"] == "sk-or-v1-test"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_none_api_key_input(self, tmp_path: Path) -> None:
        """Test handling of None input from Prompt."""
        config_dir = tmp_path / ".forge"

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm") as mock_confirm, \
             patch("code_forge.cli.setup.console"):

            # Simulate None return (shouldn't happen but be defensive)
            mock_prompt.ask.side_effect = [None, "sk-or-v1-valid"]
            mock_confirm.ask.return_value = False  # Retry

            result = run_setup_wizard(config_dir)

        assert result == "sk-or-v1-valid"

    def test_very_long_api_key(self, tmp_path: Path) -> None:
        """Test handling of very long API key."""
        config_dir = tmp_path / ".forge"
        long_key = "sk-or-v1-" + "x" * 1000

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm"), \
             patch("code_forge.cli.setup.console"):

            mock_prompt.ask.return_value = long_key

            result = run_setup_wizard(config_dir)

        assert result == long_key
        with (config_dir / "settings.json").open() as f:
            data = json.load(f)
        assert data["api_key"] == long_key

    def test_special_characters_in_api_key(self, tmp_path: Path) -> None:
        """Test handling of special characters in API key."""
        config_dir = tmp_path / ".forge"
        special_key = 'sk-or-v1-test-key-with-"quotes"-and-\\backslash'

        with patch("code_forge.cli.setup.Prompt") as mock_prompt, \
             patch("code_forge.cli.setup.Confirm"), \
             patch("code_forge.cli.setup.console"):

            mock_prompt.ask.return_value = special_key

            result = run_setup_wizard(config_dir)

        assert result == special_key
        # Verify it's properly JSON encoded
        with (config_dir / "settings.json").open() as f:
            data = json.load(f)
        assert data["api_key"] == special_key

    def test_readonly_parent_directory(self, tmp_path: Path) -> None:
        """Test handling of read-only parent directory."""
        if os.name == "nt":
            pytest.skip("Read-only directory test not reliable on Windows")

        config_dir = tmp_path / "readonly" / ".forge"
        readonly_parent = tmp_path / "readonly"
        readonly_parent.mkdir()

        # Make parent read-only
        readonly_parent.chmod(0o444)

        try:
            with pytest.raises(OSError):
                save_api_key("sk-or-v1-test", config_dir)
        finally:
            # Restore permissions for cleanup
            readonly_parent.chmod(0o755)

    def test_config_file_as_directory(self, tmp_path: Path) -> None:
        """Test handling when settings.json is actually a directory."""
        config_dir = tmp_path / ".forge"
        config_dir.mkdir(parents=True)

        # Create settings.json as a directory (edge case)
        (config_dir / "settings.json").mkdir()

        with pytest.raises(OSError):
            save_api_key("sk-or-v1-test", config_dir)
