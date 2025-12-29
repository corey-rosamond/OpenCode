"""Logging infrastructure for Code-Forge."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

# Log level mapping for environment variable
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Default log file location
DEFAULT_LOG_DIR = Path.home() / ".forge" / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "forge.log"

# Log file settings
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 5  # Keep 5 backup files


def get_log_level_from_env() -> int:
    """Get logging level from FORGE_LOG_LEVEL environment variable.

    Returns:
        Logging level constant. Defaults to WARNING if not set or invalid.
    """
    level_str = os.environ.get("FORGE_LOG_LEVEL", "WARNING").upper()
    return LOG_LEVEL_MAP.get(level_str, logging.WARNING)


def get_default_log_file() -> Path:
    """Get the default log file path, creating directory if needed.

    Returns:
        Path to the log file.
    """
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_LOG_FILE


def setup_logging(
    level: int | None = None,
    log_file: Path | None = None,
    console_output: bool = True,
    rich_console: bool = True,
    file_logging: bool = True,
) -> None:
    """Configure logging for Code-Forge.

    Logging is configured based on:
    1. Explicit level parameter (highest priority)
    2. FORGE_LOG_LEVEL environment variable
    3. Default level (WARNING)

    By default, logs are written to both console and ~/.forge/logs/forge.log.
    File logging uses rotation to prevent unbounded growth.

    Args:
        level: Logging level. If None, uses env var or default (WARNING).
        log_file: Custom file path for log output. If None, uses default.
        console_output: Show logs on console (default: True).
        rich_console: Use Rich for console formatting (default: True).
        file_logging: Write logs to file (default: True).
    """
    handlers: list[logging.Handler] = []

    # Determine log level
    if level is None:
        level = get_log_level_from_env()

    # File handler with rotation (always enabled by default)
    if file_logging:
        if log_file is None:
            log_file = get_default_log_file()

        # Ensure parent directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        # File handler always logs at DEBUG level to capture everything
        file_handler.setLevel(logging.DEBUG)
        handlers.append(file_handler)

    # Console handler (optional, respects log level)
    if console_output:
        if rich_console:
            console_handler = RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
                level=level,  # Console respects configured level
            )
        else:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            console_handler.setLevel(level)
        handlers.append(console_handler)

    # Configure root logger for Code-Forge
    root_logger = logging.getLogger("Code-Forge")
    # Set root logger to DEBUG so file handler captures everything
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    for handler in handlers:
        root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: The name for the logger (will be prefixed with 'Code-Forge.').

    Returns:
        A configured Logger instance.
    """
    return logging.getLogger(f"Code-Forge.{name}")
