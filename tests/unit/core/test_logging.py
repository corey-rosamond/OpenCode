"""Tests for logging infrastructure."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest

from code_forge.core.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def teardown_method(self) -> None:
        """Clean up logging handlers after each test."""
        logger = logging.getLogger("Code-Forge")
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    def test_setup_logging_default(self) -> None:
        """setup_logging should configure DEBUG level on root logger.

        Root logger is DEBUG to allow file handler to capture everything.
        Console handler respects FORGE_LOG_LEVEL or default (WARNING).
        """
        setup_logging(file_logging=False)  # Disable file for test
        logger = logging.getLogger("Code-Forge")
        # Root logger is DEBUG so file handler can capture all
        assert logger.level == logging.DEBUG

    def test_setup_logging_custom_level(self) -> None:
        """setup_logging should accept custom log level for console."""
        setup_logging(level=logging.DEBUG, file_logging=False)
        logger = logging.getLogger("Code-Forge")
        # Root logger is always DEBUG
        assert logger.level == logging.DEBUG

    def test_setup_logging_with_file(self) -> None:
        """setup_logging should write to file when path provided."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False
        ) as f:
            log_path = Path(f.name)

        try:
            setup_logging(log_file=log_path, rich_console=False)
            logger = logging.getLogger("Code-Forge")

            # Check that file handler was added
            file_handlers = [
                h for h in logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) == 1

            # Write a log message
            logger.info("test message")

            # Verify it was written to file
            with open(log_path) as f:
                content = f.read()
            assert "test message" in content
        finally:
            log_path.unlink(missing_ok=True)

    def test_setup_logging_without_rich(self) -> None:
        """setup_logging should use StreamHandler when rich_console=False."""
        setup_logging(rich_console=False, file_logging=False)
        logger = logging.getLogger("Code-Forge")

        # Should have a StreamHandler, not RichHandler
        stream_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not h.__class__.__name__ == "RichHandler"
        ]
        assert len(stream_handlers) >= 1

    def test_setup_logging_clears_existing_handlers(self) -> None:
        """setup_logging should clear existing handlers to avoid duplicates."""
        setup_logging(file_logging=False)
        initial_count = len(logging.getLogger("Code-Forge").handlers)

        setup_logging(file_logging=False)
        final_count = len(logging.getLogger("Code-Forge").handlers)

        # Should not accumulate handlers
        assert final_count == initial_count


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self) -> None:
        """get_logger should return a Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_name_prefix(self) -> None:
        """get_logger should prefix name with 'Code-Forge.'."""
        logger = get_logger("mymodule")
        assert logger.name == "Code-Forge.mymodule"

    def test_get_logger_different_names(self) -> None:
        """get_logger should return different loggers for different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_get_logger_same_name_same_instance(self) -> None:
        """get_logger should return same logger for same name."""
        logger1 = get_logger("same")
        logger2 = get_logger("same")
        assert logger1 is logger2
