"""Hook execution engine."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from code_forge.hooks.registry import Hook, HookRegistry

if TYPE_CHECKING:
    from code_forge.hooks.events import HookEvent

logger = logging.getLogger(__name__)


@dataclass
class HookResult:
    """
    Result of hook execution.

    Attributes:
        hook: The hook that was executed
        exit_code: Process exit code (0 = success)
        stdout: Captured standard output
        stderr: Captured standard error
        duration: Execution time in seconds
        timed_out: Whether the hook timed out
        error: Error message if execution failed
    """

    hook: Hook
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if hook executed successfully."""
        return self.exit_code == 0 and not self.timed_out and not self.error

    @property
    def should_continue(self) -> bool:
        """
        Check if operation should continue.

        For pre-execution hooks, returns False if:
        - Exit code is non-zero
        - Hook timed out
        - Hook had an error during execution
        """
        return self.exit_code == 0 and not self.timed_out and not self.error


class HookExecutor:
    """
    Executes hooks in response to events.

    Handles shell command execution with proper environment,
    timeout management, and result collection.

    Example:
        ```python
        executor = HookExecutor()
        event = HookEvent.tool_pre_execute("bash", {"command": "ls"})

        results = await executor.execute_hooks(event)
        for result in results:
            if not result.should_continue:
                raise HookBlockedError(result)
        ```
    """

    # Maximum number of results to keep per execute_hooks call
    MAX_RESULTS: ClassVar[int] = 100

    # Environment variables that hooks are not allowed to override
    # These can be used for privilege escalation or code injection
    DANGEROUS_ENV_VARS: ClassVar[frozenset[str]] = frozenset({
        # Dynamic linker - can inject arbitrary code
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        # Python - can inject code or change module loading
        "PYTHONPATH",
        "PYTHONSTARTUP",
        "PYTHONHOME",
        # Ruby
        "RUBYLIB",
        "RUBYOPT",
        # Perl
        "PERL5LIB",
        "PERL5OPT",
        # Node.js
        "NODE_PATH",
        "NODE_OPTIONS",
        # Shell startup - can inject code
        "BASH_ENV",
        "ENV",
        "ZDOTDIR",
        # Sudo/privilege escalation
        "SUDO_ASKPASS",
        # SSL/TLS - can enable MITM attacks
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        # Git - can inject hooks
        "GIT_EXEC_PATH",
        "GIT_TEMPLATE_DIR",
        # Other potentially dangerous
        "IFS",
        "CDPATH",
    })

    def __init__(
        self,
        registry: HookRegistry | None = None,
        default_timeout: float = 10.0,
        working_dir: Path | None = None,
    ) -> None:
        """
        Initialize executor.

        Args:
            registry: Hook registry (uses singleton if not provided)
            default_timeout: Default timeout for hooks
            working_dir: Default working directory
        """
        self.registry = registry or HookRegistry.get_instance()
        self.default_timeout = default_timeout
        self.working_dir = working_dir or Path.cwd()

    async def execute_hooks(
        self,
        event: HookEvent,
        *,
        stop_on_failure: bool = True,
        max_results: int | None = None,
    ) -> list[HookResult]:
        """
        Execute all matching hooks for an event.

        Args:
            event: The event to handle
            stop_on_failure: Stop after first failing hook
            max_results: Maximum results to return (default: MAX_RESULTS)

        Returns:
            List of hook execution results (bounded to max_results)
        """
        hooks = self.registry.get_hooks(event)

        if not hooks:
            return []

        max_results = max_results or self.MAX_RESULTS
        results: list[HookResult] = []

        for hook in hooks:
            try:
                result = await self._execute_hook(hook, event)
                results.append(result)

                # Log result
                if result.success:
                    logger.debug(
                        "Hook '%s' succeeded (exit=%d, %.2fs)",
                        hook.event_pattern,
                        result.exit_code,
                        result.duration,
                    )
                else:
                    logger.warning(
                        "Hook '%s' failed: exit=%d, timed_out=%s",
                        hook.event_pattern,
                        result.exit_code,
                        result.timed_out,
                    )

                # Check if we should stop
                if stop_on_failure and not result.should_continue:
                    logger.info("Hook blocked operation: %s", hook.event_pattern)
                    break

                # Check if we've hit the results limit
                if len(results) >= max_results:
                    logger.warning(
                        "Hook results limit reached (%d), skipping remaining hooks",
                        max_results,
                    )
                    break

            except asyncio.CancelledError:
                # Task was cancelled - log and re-raise to allow proper cleanup
                logger.debug("Hook '%s' cancelled", hook.event_pattern)
                raise

            except Exception as e:
                logger.error("Hook '%s' error: %s", hook.event_pattern, e)
                results.append(
                    HookResult(
                        hook=hook,
                        exit_code=-1,
                        stdout="",
                        stderr="",
                        duration=0.0,
                        error=str(e),
                    )
                )
                if stop_on_failure:
                    break

                # Also check limit after errors
                if len(results) >= max_results:
                    break

        return results

    async def _execute_hook(
        self,
        hook: Hook,
        event: HookEvent,
    ) -> HookResult:
        """
        Execute a single hook.

        Args:
            hook: The hook to execute
            event: The triggering event

        Returns:
            HookResult with execution details
        """
        start_time = time.time()

        # Build environment
        env = os.environ.copy()
        env.update(event.to_env())

        # Add working directory
        work_dir = hook.working_dir or str(self.working_dir)
        env["FORGE_WORKING_DIR"] = work_dir

        # Add hook-specific env vars (filtered for security)
        if hook.env:
            for key, value in hook.env.items():
                if key.upper() in self.DANGEROUS_ENV_VARS:
                    logger.warning(
                        "Hook '%s' attempted to set dangerous env var '%s' - blocked",
                        hook.event_pattern,
                        key,
                    )
                else:
                    env[key] = value

        # Determine timeout
        timeout = hook.timeout or self.default_timeout

        try:
            # Create subprocess - may raise OSError for invalid commands/paths
            process = await asyncio.create_subprocess_shell(
                hook.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env,
            )

            try:
                # Wait with timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                duration = time.time() - start_time

                return HookResult(
                    hook=hook,
                    exit_code=process.returncode or 0,
                    stdout=stdout_bytes.decode("utf-8", errors="replace"),
                    stderr=stderr_bytes.decode("utf-8", errors="replace"),
                    duration=duration,
                )

            except TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()

                duration = time.time() - start_time

                return HookResult(
                    hook=hook,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    duration=duration,
                    timed_out=True,
                    error=f"Hook timed out after {timeout}s",
                )

            except asyncio.CancelledError:
                # Task was cancelled - kill process and re-raise
                process.kill()
                await process.wait()
                raise

        except OSError as e:
            # Handle subprocess creation failures (invalid command, bad path, etc.)
            duration = time.time() - start_time
            return HookResult(
                hook=hook,
                exit_code=-1,
                stdout="",
                stderr="",
                duration=duration,
                error=f"Failed to execute hook: {e}",
            )

        except Exception as e:
            # Catch-all for unexpected errors
            duration = time.time() - start_time
            logger.exception("Unexpected error executing hook: %s", hook.event_pattern)
            return HookResult(
                hook=hook,
                exit_code=-1,
                stdout="",
                stderr="",
                duration=duration,
                error=f"Unexpected error: {e}",
            )


class HookBlockedError(Exception):
    """Raised when a hook blocks an operation."""

    def __init__(self, result: HookResult) -> None:
        self.result = result
        super().__init__(
            f"Operation blocked by hook '{result.hook.event_pattern}': "
            f"exit code {result.exit_code}"
        )


async def fire_event(
    event: HookEvent,
    *,
    executor: HookExecutor | None = None,
    stop_on_failure: bool = True,
) -> list[HookResult]:
    """
    Convenience function to fire an event.

    Args:
        event: Event to fire
        executor: Executor to use (creates default if not provided)
        stop_on_failure: Stop after first failing hook

    Returns:
        List of hook results
    """
    exec_instance = executor or HookExecutor()
    return await exec_instance.execute_hooks(event, stop_on_failure=stop_on_failure)
