"""Centralized constants for Code-Forge.

This module contains commonly used constants that were previously
scattered across the codebase as magic numbers. Centralizing them here:
- Makes values easy to find and modify
- Ensures consistency across modules
- Documents the purpose of each value

Note: Not all modules have been migrated to use these constants yet.
New code should use these constants where applicable.
"""

# =============================================================================
# Timeouts (in seconds unless noted otherwise)
# =============================================================================

# Default timeout for general operations
DEFAULT_TIMEOUT: float = 120.0

# Tool execution timeout (seconds)
TOOL_TIMEOUT: float = 120.0

# Command execution timeout (seconds)
COMMAND_TIMEOUT: float = 30.0

# LLM API request timeout (seconds)
LLM_TIMEOUT: int = 60

# Hook execution timeout (seconds)
HOOK_TIMEOUT: float = 10.0

# Web fetch timeout (seconds)
WEB_FETCH_TIMEOUT: int = 30

# Git operation timeout (seconds)
GIT_TIMEOUT: int = 10

# GitHub API timeout (seconds)
GITHUB_TIMEOUT: int = 30

# Headless mode timeout (seconds)
HEADLESS_TIMEOUT: int = 300

# File lock acquisition timeout (seconds)
FILE_LOCK_TIMEOUT: float = 10.0

# =============================================================================
# Retries
# =============================================================================

# Default maximum retry attempts
DEFAULT_MAX_RETRIES: int = 3

# Default delay between retries (seconds)
DEFAULT_RETRY_DELAY: float = 1.0

# Hook retry attempts
HOOK_MAX_RETRIES: int = 2

# =============================================================================
# Size Limits
# =============================================================================

# Maximum output size for tool results (bytes)
MAX_OUTPUT_SIZE: int = 100_000

# Maximum file size for operations (bytes) - 10MB
MAX_FILE_SIZE: int = 10 * 1024 * 1024

# Web fetch maximum size (bytes) - 5MB
WEB_FETCH_MAX_SIZE: int = 5 * 1024 * 1024

# Web cache maximum size (bytes) - 100MB
WEB_CACHE_MAX_SIZE: int = 100 * 1024 * 1024

# Shell read buffer size (bytes)
SHELL_BUFFER_SIZE: int = 4096

# =============================================================================
# Context and Token Limits
# =============================================================================

# Default context window limit (tokens)
DEFAULT_CONTEXT_LIMIT: int = 128_000

# Default maximum tokens for LLM response
DEFAULT_MAX_TOKENS: int = 4096

# =============================================================================
# Iteration Limits
# =============================================================================

# Maximum tool iterations per request
MAX_ITERATIONS: int = 10

# Maximum redirects for web fetch
MAX_REDIRECTS: int = 5

# =============================================================================
# Cache Settings
# =============================================================================

# Web cache TTL (seconds) - 15 minutes
WEB_CACHE_TTL: int = 900
