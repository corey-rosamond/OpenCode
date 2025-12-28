"""Tests for CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_forge import __version__
from code_forge.cli.main import main, print_help


class TestMainFunction:
    """Tests for main() function."""

    def test_version_flag(self) -> None:
        """--version should print version and return 0."""
        with patch.object(sys, "argv", ["forge", "--version"]):
            with patch("builtins.print") as mock_print:
                exit_code = main()
        assert exit_code == 0
        mock_print.assert_called_once()
        assert __version__ in mock_print.call_args[0][0]

    def test_version_short_flag(self) -> None:
        """-v should print version and return 0."""
        with patch.object(sys, "argv", ["forge", "-v"]):
            with patch("builtins.print") as mock_print:
                exit_code = main()
        assert exit_code == 0
        assert __version__ in mock_print.call_args[0][0]

    def test_help_flag(self) -> None:
        """--help should print help and return 0."""
        with patch.object(sys, "argv", ["forge", "--help"]):
            with patch("builtins.print") as mock_print:
                exit_code = main()
        assert exit_code == 0
        # Help should contain usage info
        output = mock_print.call_args[0][0]
        assert "Usage:" in output
        assert "Options:" in output

    def test_help_short_flag(self) -> None:
        """-h should print help and return 0."""
        with patch.object(sys, "argv", ["forge", "-h"]):
            with patch("builtins.print") as mock_print:
                exit_code = main()
        assert exit_code == 0

    def test_no_arguments_starts_repl(self) -> None:
        """Running without arguments should start the REPL."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.return_value = 0
                            exit_code = main()

        assert exit_code == 0
        mock_loader.assert_called_once()
        mock_run.assert_called_once()

    def test_config_load_error(self) -> None:
        """Config load error should return exit code 1."""
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.side_effect = Exception("Config error")
                    with patch("builtins.print"):
                        exit_code = main()

        assert exit_code == 1

    def test_repl_error(self) -> None:
        """REPL error should return exit code 1."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.side_effect = Exception("REPL error")
                            with patch("builtins.print"):
                                exit_code = main()

        assert exit_code == 1

    def test_keyboard_interrupt(self) -> None:
        """KeyboardInterrupt should return exit code 130."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.side_effect = KeyboardInterrupt()
                            with patch("builtins.print"):
                                exit_code = main()

        assert exit_code == 130

    def test_unknown_flag(self) -> None:
        """Unknown flags should return error code 1."""
        with patch.object(sys, "argv", ["forge", "--invalid-flag"]):
            with patch("builtins.print"):
                exit_code = main()
        assert exit_code == 1

    def test_unknown_flag_error_message(self) -> None:
        """Unknown flags should print error to stderr."""
        with patch.object(sys, "argv", ["forge", "--unknown"]):
            with patch("builtins.print") as mock_print:
                exit_code = main()

        # Find the stderr call
        stderr_calls = [
            call for call in mock_print.call_args_list
            if call.kwargs.get("file") == sys.stderr
        ]
        assert len(stderr_calls) > 0
        error_msg = str(stderr_calls[0])
        assert "--unknown" in error_msg


class TestPrintHelp:
    """Tests for print_help() function."""

    def test_help_contains_usage(self) -> None:
        """Help should contain usage information."""
        with patch("builtins.print") as mock_print:
            print_help()
        output = mock_print.call_args[0][0]
        assert "Usage:" in output

    def test_help_contains_options(self) -> None:
        """Help should list available options."""
        with patch("builtins.print") as mock_print:
            print_help()
        output = mock_print.call_args[0][0]
        assert "--version" in output
        assert "--help" in output
        assert "--continue" in output
        assert "--resume" in output
        assert "--print" in output

    def test_help_contains_short_flags(self) -> None:
        """Help should list short flags."""
        with patch("builtins.print") as mock_print:
            print_help()
        output = mock_print.call_args[0][0]
        assert "-v" in output
        assert "-h" in output
        assert "-p" in output

    def test_help_contains_output_options(self) -> None:
        """Help should list output format options."""
        with patch("builtins.print") as mock_print:
            print_help()
        output = mock_print.call_args[0][0]
        assert "--no-color" in output
        assert "-q" in output or "--quiet" in output
        assert "--json" in output


class TestOutputFormatFlags:
    """Tests for output format CLI flags."""

    def test_no_color_flag_accepted(self) -> None:
        """--no-color should be a valid flag."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_config.display.color = True
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge", "--no-color"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.return_value = 0
                            exit_code = main()

        assert exit_code == 0
        # Verify color was disabled on config
        assert mock_config.display.color is False

    def test_quiet_flag_accepted(self) -> None:
        """-q should be a valid flag."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_config.display.quiet = False
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge", "-q"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.return_value = 0
                            exit_code = main()

        assert exit_code == 0
        # Verify quiet was enabled on config
        assert mock_config.display.quiet is True

    def test_quiet_long_flag_accepted(self) -> None:
        """--quiet should be a valid flag."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_config.display.quiet = False
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge", "--quiet"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.return_value = 0
                            exit_code = main()

        assert exit_code == 0
        assert mock_config.display.quiet is True

    def test_json_flag_accepted(self) -> None:
        """--json should be a valid flag."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_config.display.json_output = False
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge", "--json"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.return_value = 0
                            exit_code = main()

        assert exit_code == 0
        assert mock_config.display.json_output is True

    def test_multiple_output_flags_combined(self) -> None:
        """Multiple output flags should work together."""
        mock_repl = MagicMock()
        mock_config = MagicMock()
        mock_config.model.default = "anthropic/claude-3.5-sonnet"
        mock_config.get_api_key.return_value = "test-api-key"
        mock_config.display.color = True
        mock_config.display.quiet = False
        mock_config.display.json_output = False
        mock_stdin = MagicMock()
        mock_stdin.read.return_value = ""
        mock_stdin.isatty.return_value = True

        with patch.object(sys, "argv", ["forge", "--no-color", "-q", "--json"]):
            with patch.object(sys, "stdin", mock_stdin):
                with patch("code_forge.cli.main.ConfigLoader") as mock_loader:
                    mock_loader.return_value.load_all.return_value = mock_config
                    with patch("code_forge.cli.main.CodeForgeREPL", return_value=mock_repl):
                        with patch("code_forge.cli.main.run_with_agent", new_callable=AsyncMock) as mock_run:
                            mock_run.return_value = 0
                            exit_code = main()

        assert exit_code == 0
        assert mock_config.display.color is False
        assert mock_config.display.quiet is True
        assert mock_config.display.json_output is True


class TestCLIIntegration:
    """Integration tests for CLI as subprocess."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Subprocess tests may behave differently on Windows",
    )
    def test_module_execution(self) -> None:
        """python -m code_forge --version should work."""
        import os
        from pathlib import Path

        # Get project root dynamically (tests/unit/cli -> project root)
        project_root = Path(__file__).parent.parent.parent.parent
        src_dir = project_root / "src"

        env = os.environ.copy()
        # PYTHONPATH should point to src directory for src layout
        env["PYTHONPATH"] = str(src_dir)
        result = subprocess.run(
            [sys.executable, "-m", "code_forge", "--version"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
        )
        assert result.returncode == 0
        assert __version__ in result.stdout
