"""Permission checker for tool execution."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import TYPE_CHECKING, Any

from code_forge.permissions.models import (
    PermissionLevel,
    PermissionResult,
    PermissionRule,
)
from code_forge.permissions.rules import RuleSet

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class PermissionChecker:
    """
    Checks permissions for tool execution.

    Evaluates rules from multiple sources in order:
    1. Session rules (temporary, highest priority)
    2. Project rules (from .forge/permissions.json)
    3. Global rules (from user config)
    4. Default permission

    Example:
        ```python
        checker = PermissionChecker()
        result = checker.check("bash", {"command": "ls -la"})

        if result.allowed:
            # Execute immediately
            pass
        elif result.needs_confirmation:
            # Ask user
            pass
        else:  # result.denied
            # Block execution
            pass
        ```
    """

    # Rate limiting configuration
    MAX_DENIALS_PER_WINDOW = 10  # Maximum denials allowed in time window
    RATE_LIMIT_WINDOW_SECONDS = 60  # Time window in seconds
    RATE_LIMIT_BACKOFF_SECONDS = 300  # Backoff period when rate limited (5 min)

    def __init__(
        self,
        global_rules: RuleSet | None = None,
        project_rules: RuleSet | None = None,
        enable_rate_limiting: bool = True,
    ) -> None:
        """
        Initialize permission checker.

        Args:
            global_rules: Rules from user configuration
            project_rules: Rules from project configuration
            enable_rate_limiting: Enable rate limiting on denials (default: True)
        """
        self.global_rules = global_rules or RuleSet()
        self.project_rules = project_rules
        self.session_rules = RuleSet()
        # Lock protects session_rules from concurrent modification
        self._session_lock = threading.RLock()

        # Rate limiting state
        self.enable_rate_limiting = enable_rate_limiting
        self._denial_timestamps: deque[float] = deque()
        self._rate_limit_until: float | None = None
        self._rate_limit_lock = threading.Lock()

    def check(self, tool_name: str, arguments: dict[str, Any]) -> PermissionResult:
        """
        Check permission for a tool execution.

        Includes rate limiting on denials to prevent DoS attacks via
        repeated permission bypass attempts.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            PermissionResult with determined permission level

        Note:
            If rate limit is exceeded (>10 denials/minute), all requests
            are denied for 5 minutes with a clear error message.
        """
        # Check if rate limited
        if self.enable_rate_limiting and self._is_rate_limited():
            return PermissionResult(
                level=PermissionLevel.DENY,
                rule=None,
                reason=(
                    "Rate limit exceeded: Too many permission denials. "
                    f"Try again in {self._get_rate_limit_remaining():.0f} seconds."
                ),
            )

        # Check session rules first (highest priority)
        with self._session_lock:
            session_result = self.session_rules.evaluate(tool_name, arguments)
        if session_result.rule is not None:
            self._audit_log(tool_name, arguments, session_result, "session")
            self._track_result(session_result)
            return session_result

        # Check project rules
        if self.project_rules:
            project_result = self.project_rules.evaluate(tool_name, arguments)
            if project_result.rule is not None:
                self._audit_log(tool_name, arguments, project_result, "project")
                self._track_result(project_result)
                return project_result

        # Check global rules
        global_result = self.global_rules.evaluate(tool_name, arguments)
        if global_result.rule is not None:
            self._audit_log(tool_name, arguments, global_result, "global")
            self._track_result(global_result)
            return global_result

        # Use global default
        result = PermissionResult(
            level=self.global_rules.default,
            rule=None,
            reason=f"Using global default: {self.global_rules.default.value}",
        )
        self._audit_log(tool_name, arguments, result, "default")
        self._track_result(result)
        return result

    def _is_rate_limited(self) -> bool:
        """Check if currently rate limited.

        Returns:
            True if rate limited, False otherwise.
        """
        with self._rate_limit_lock:
            # Check if in backoff period
            if self._rate_limit_until is not None:
                if time.time() < self._rate_limit_until:
                    return True
                # Backoff period expired, reset
                self._rate_limit_until = None
                self._denial_timestamps.clear()
                logger.info("Rate limit backoff period expired, resetting counters")
                return False

            # Check sliding window of denials
            current_time = time.time()
            cutoff_time = current_time - self.RATE_LIMIT_WINDOW_SECONDS

            # Remove old timestamps outside the window
            while self._denial_timestamps and self._denial_timestamps[0] < cutoff_time:
                self._denial_timestamps.popleft()

            # Check if limit exceeded
            return len(self._denial_timestamps) >= self.MAX_DENIALS_PER_WINDOW

    def _get_rate_limit_remaining(self) -> float:
        """Get seconds remaining in rate limit backoff period.

        Returns:
            Seconds remaining, or 0 if not rate limited.
        """
        with self._rate_limit_lock:
            if self._rate_limit_until is None:
                return 0.0
            remaining = self._rate_limit_until - time.time()
            return max(0.0, remaining)

    def _track_result(self, result: PermissionResult) -> None:
        """Track permission result for rate limiting.

        Args:
            result: The permission result to track.
        """
        if not self.enable_rate_limiting:
            return

        with self._rate_limit_lock:
            # Only track denials
            if result.level == PermissionLevel.DENY:
                current_time = time.time()
                self._denial_timestamps.append(current_time)

                # Remove old timestamps
                cutoff_time = current_time - self.RATE_LIMIT_WINDOW_SECONDS
                while self._denial_timestamps and self._denial_timestamps[0] < cutoff_time:
                    self._denial_timestamps.popleft()

                # Check if limit exceeded
                if len(self._denial_timestamps) >= self.MAX_DENIALS_PER_WINDOW:
                    self._rate_limit_until = current_time + self.RATE_LIMIT_BACKOFF_SECONDS
                    logger.warning(
                        "Rate limit threshold exceeded: %d denials in %ds. "
                        "Blocking all requests for %ds.",
                        len(self._denial_timestamps),
                        self.RATE_LIMIT_WINDOW_SECONDS,
                        self.RATE_LIMIT_BACKOFF_SECONDS,
                    )

    def _audit_log(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: PermissionResult,
        source: str,
    ) -> None:
        """Log permission decision for audit trail.

        Args:
            tool_name: The tool being checked
            arguments: Tool arguments
            result: The permission result
            source: Where the rule came from (session, project, global, default)
        """
        # Use DEBUG level for ALLOW, INFO for ASK, WARNING for DENY
        level = result.level
        rule_pattern = result.rule.pattern if result.rule else "none"

        if level == PermissionLevel.DENY:
            logger.warning(
                "Permission DENIED for tool '%s' (source=%s, rule=%s)",
                tool_name,
                source,
                rule_pattern,
            )
        elif level == PermissionLevel.ASK:
            logger.info(
                "Permission ASK for tool '%s' (source=%s, rule=%s)",
                tool_name,
                source,
                rule_pattern,
            )
        else:  # ALLOW
            logger.debug(
                "Permission ALLOWED for tool '%s' (source=%s, rule=%s)",
                tool_name,
                source,
                rule_pattern,
            )

    def add_session_rule(self, rule: PermissionRule) -> None:
        """
        Add a temporary session rule.

        Session rules take highest priority and are cleared
        when the session ends.

        Thread-safe: Protected by internal lock.
        """
        with self._session_lock:
            # Remove existing rule with same pattern if any
            self.session_rules.remove_rule(rule.pattern)
            self.session_rules.add_rule(rule)

    def remove_session_rule(self, pattern: str) -> bool:
        """Remove a session rule by pattern.

        Thread-safe: Protected by internal lock.
        """
        with self._session_lock:
            return self.session_rules.remove_rule(pattern)

    def clear_session_rules(self) -> None:
        """Clear all session rules.

        Thread-safe: Protected by internal lock.
        """
        with self._session_lock:
            self.session_rules = RuleSet()

    def get_session_rules(self) -> list[PermissionRule]:
        """Get all session rules.

        Thread-safe: Returns a copy of the rules list.
        """
        with self._session_lock:
            return list(self.session_rules.rules)

    def allow_always(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> None:
        """
        Create session rule to always allow this tool/arguments.

        Args:
            tool_name: Tool to allow
            arguments: Optional specific arguments to allow
        """
        pattern = f"tool:{tool_name}"

        # If arguments specified, make more specific pattern
        if arguments:
            # Create pattern for first argument (most common case)
            for key, value in arguments.items():
                pattern += f",arg:{key}:{value}"
                break  # Just use first argument

        self.add_session_rule(
            PermissionRule(
                pattern=pattern,
                permission=PermissionLevel.ALLOW,
                description=f"Session allow: {pattern}",
                priority=100,  # High priority for session rules
            )
        )

    def deny_always(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> None:
        """
        Create session rule to always deny this tool/arguments.

        Args:
            tool_name: Tool to deny
            arguments: Optional specific arguments to deny
        """
        pattern = f"tool:{tool_name}"

        if arguments:
            for key, value in arguments.items():
                pattern += f",arg:{key}:{value}"
                break

        self.add_session_rule(
            PermissionRule(
                pattern=pattern,
                permission=PermissionLevel.DENY,
                description=f"Session deny: {pattern}",
                priority=100,
            )
        )

    @classmethod
    def from_config(cls, project_root: Path | None = None) -> PermissionChecker:
        """
        Create permission checker from configuration.

        Args:
            project_root: Optional project root path for project rules

        Returns:
            Configured PermissionChecker
        """
        from code_forge.permissions.config import PermissionConfig

        global_rules = PermissionConfig.load_global()
        project_rules = PermissionConfig.load_project(project_root)

        return cls(global_rules=global_rules, project_rules=project_rules)


class ToolPermissionError(Exception):
    """
    Raised when permission is denied for a tool execution.

    Note: Named ToolPermissionError to avoid shadowing the builtin
    PermissionError exception. Using the same name as the builtin would
    cause subtle bugs when code expects to catch OSError/PermissionError
    from file operations but accidentally catches this instead.
    """

    def __init__(
        self,
        result: PermissionResult,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> None:
        """
        Initialize permission error.

        Args:
            result: The permission check result
            tool_name: Name of the denied tool
            arguments: Tool arguments that were denied
        """
        self.result = result
        self.tool_name = tool_name
        self.arguments = arguments
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message."""
        return (
            f"Permission denied for tool '{self.tool_name}': {self.result.reason}"
        )
