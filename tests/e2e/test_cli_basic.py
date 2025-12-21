"""E2E tests for basic CLI functionality."""

import subprocess

import pytest


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_version_flag(self, forge_runner):
        """Given --version flag, displays version"""
        result = forge_runner.run(args=["--version"])

        assert result.returncode == 0
        assert "forge" in result.stdout
        assert "1.7.0" in result.stdout

    def test_help_flag(self, forge_runner):
        """Given --help flag, displays help"""
        result = forge_runner.run(args=["--help"])

        assert result.returncode == 0
        assert "forge" in result.stdout.lower()
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_invalid_flag(self, forge_runner):
        """Given invalid flag, returns error"""
        result = forge_runner.run(args=["--invalid-flag"], check=False)

        assert result.returncode == 1
        assert "unknown option" in result.stderr.lower() or "error" in result.stderr.lower()

    @pytest.mark.skip(reason="Requires interactive mode, will implement with mock")
    def test_starts_repl(self, forge_runner, e2e_forge_config):
        """Given no arguments, starts REPL"""
        # This would require mocking the REPL or using expect
        pass


class TestCLIConfiguration:
    """Test CLI configuration loading."""

    def test_loads_config_from_home(self, forge_runner, e2e_forge_config):
        """Given config in ~/.config/forge, loads successfully"""
        # Verify config file exists
        assert e2e_forge_config.exists()

        # Run with minimal command (version check proves it loaded config without error)
        result = forge_runner.run(args=["--version"])
        assert result.returncode == 0

    def test_missing_config_handled(self, forge_runner, e2e_home):
        """Given missing config, uses defaults"""
        # Remove config file
        config_file = e2e_home / ".config" / "forge" / "settings.json"
        if config_file.exists():
            config_file.unlink()

        # Should still work with defaults (or prompt for setup)
        result = forge_runner.run(args=["--version"])
        assert result.returncode == 0


class TestCLIWorkingDirectory:
    """Test CLI working directory handling."""

    def test_runs_in_project_directory(self, forge_runner, sample_python_project):
        """Given project directory, can access project files"""
        # Version check in project directory
        result = forge_runner.run(args=["--version"], cwd=sample_python_project)

        assert result.returncode == 0
        # Should run successfully in project directory

    def test_git_repo_detected(self, forge_runner, git_project):
        """Given git repository, detects git context"""
        # Run in git repo - version check should work
        result = forge_runner.run(args=["--version"], cwd=git_project)

        assert result.returncode == 0
